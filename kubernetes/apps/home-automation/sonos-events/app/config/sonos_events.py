"""Log every Sonos playback change as one JSON line on stdout.

Polls each speaker group's coordinator over the local UPnP API and prints an
event whenever what it is doing changes: started, stopped, a new track, a new
source. The lines are shipped to Loki as {job="sonos-events"}.

A speaker cannot name the Spotify account driving it, so the useful signal
for "who started this" is the pair (source, session): a Spotify Connect
session id the household did not start is somebody else's app.
"""

import concurrent.futures
import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

SEEDS = [s.strip() for s in os.environ["SONOS_SEEDS"].split(",") if s.strip()]
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
TOPOLOGY_SECONDS = float(os.environ.get("TOPOLOGY_SECONDS", "60"))
TIMEOUT = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "4"))

ENVELOPE = (
    '<?xml version="1.0"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
    '<u:{action} xmlns:u="urn:schemas-upnp-org:service:{service}:1">{args}'
    "</u:{action}></s:Body></s:Envelope>"
)
INSTANCE = "<InstanceID>0</InstanceID>"
PLAYING = {"PLAYING", "TRANSITIONING"}


def emit(event, **fields):
    record = {"event": event}
    record.update({k: v for k, v in fields.items() if v not in (None, "", [])})
    print(json.dumps(record, ensure_ascii=False), flush=True)


def soap(ip, path, service, action, args=""):
    request = urllib.request.Request(
        f"http://{ip}:1400{path}",
        data=ENVELOPE.format(action=action, service=service, args=args).encode(),
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPACTION": f'"urn:schemas-upnp-org:service:{service}:1#{action}"',
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def tag(body, name):
    match = re.search(rf"<{name}>(.*?)</{name}>", body, re.S)
    return html.unescape(match.group(1)) if match else ""


def didl(metadata, name):
    match = re.search(rf"<{name}[^>]*>(.*?)</{name}>", metadata, re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def topology():
    """Return {coordinator_uuid: {"ip", "room", "members"}} from any seed."""
    for seed in SEEDS:
        try:
            body = soap(
                seed,
                "/ZoneGroupTopology/Control",
                "ZoneGroupTopology",
                "GetZoneGroupState",
            )
        except OSError:
            continue
        state = ET.fromstring(tag(body, "ZoneGroupState"))
        groups = {}
        for group in state.iter("ZoneGroup"):
            coordinator = group.get("Coordinator")
            # Invisible members are the satellites of a bonded set; the room
            # is already represented by its visible player.
            members = [m for m in group.findall("ZoneGroupMember") if m.get("Invisible") != "1"]
            lead = next((m for m in members if m.get("UUID") == coordinator), None)
            if lead is None:
                continue
            groups[coordinator] = {
                "ip": re.search(r"//([^:/]+)", lead.get("Location")).group(1),
                "room": lead.get("ZoneName"),
                "members": sorted(m.get("ZoneName") for m in members),
            }
        return groups
    return None


def classify(uri, track_uri):
    """Name where the audio comes from, and the session id if it has one."""
    connect = re.match(r"x-sonos-vli:[^,]*,(spotify|airplay):?(.*)", uri)
    if connect:
        kind = "spotify_connect" if connect.group(1) == "spotify" else "airplay"
        return kind, connect.group(2)
    if uri.startswith("x-rincon-queue:"):
        # The Sonos app's own queue; the track says which service fills it.
        if track_uri.startswith("x-sonos-spotify:"):
            return "sonos_app_spotify", ""
        if track_uri.startswith(("http://", "https://")):
            return "stream", ""
        return "sonos_app_queue", ""
    if uri.startswith("x-sonos-htastream:"):
        return "tv", ""
    if uri.startswith("x-rincon-stream:"):
        return "line_in", ""
    if uri.startswith(("x-sonosapi-", "x-rincon-mp3radio:", "aac:", "hls-radio:")):
        return "radio", ""
    if uri.startswith(("http://", "https://")):
        return "stream", ""
    if not uri:
        return "none", ""
    return "other", ""


def stream_host(*uris):
    for uri in uris:
        match = re.match(r"https?://([^/:]+)", uri)
        if match:
            return match.group(1)
    return ""


def read(group):
    ip = group["ip"]
    transport = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetTransportInfo", INSTANCE)
    media = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetMediaInfo", INSTANCE)
    position = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetPositionInfo", INSTANCE)
    uri = tag(media, "CurrentURI")
    track_uri = tag(position, "TrackURI")
    metadata = tag(position, "TrackMetaData")
    source, session = classify(uri, track_uri)
    return {
        "room": group["room"],
        "ip": ip,
        "group": group["members"] if len(group["members"]) > 1 else None,
        "playing": tag(transport, "CurrentTransportState") in PLAYING,
        "state": tag(transport, "CurrentTransportState").lower(),
        "source": source,
        "session": session,
        "stream_host": stream_host(uri, track_uri) if source == "stream" else "",
        "title": didl(metadata, "dc:title"),
        "artist": didl(metadata, "dc:creator"),
        "album": didl(metadata, "upnp:album"),
    }


def describe(now):
    return {k: now[k] for k in ("room", "ip", "group", "state", "source", "session", "stream_host", "title", "artist", "album")}


def compare(before, now):
    """Yield the event names that turn `before` into `now`."""
    if before is None:
        if now["playing"]:
            yield "playback_started"
        return
    if now["playing"] and not before["playing"]:
        yield "playback_started"
    elif before["playing"] and not now["playing"]:
        yield "playback_stopped"
    elif now["playing"]:
        if (now["source"], now["session"]) != (before["source"], before["session"]):
            yield "source_changed"
        elif now["title"] and (now["title"], now["artist"]) != (before["title"], before["artist"]):
            yield "track_changed"
    # A new Connect session on an idle speaker is the moment somebody's app
    # took hold of it, which can precede the first audible second.
    if now["session"] and now["session"] != before["session"]:
        yield "session_started"


def main():
    groups = {}
    last = {}
    unreachable = set()
    next_topology = 0.0
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=16)
    emit("exporter_started", seeds=SEEDS, poll_seconds=POLL_SECONDS)
    while True:
        started = time.monotonic()
        if started >= next_topology:
            found = topology()
            if found is None:
                emit("topology_unreachable", seeds=SEEDS)
            else:
                if sorted(g["room"] for g in found.values()) != sorted(g["room"] for g in groups.values()):
                    emit("topology", rooms=sorted(g["room"] for g in found.values()))
                groups = found
                for gone in set(last) - set(groups):
                    del last[gone]
            next_topology = started + TOPOLOGY_SECONDS

        futures = {uuid: pool.submit(read, group) for uuid, group in groups.items()}
        for uuid, future in futures.items():
            try:
                now = future.result()
            except (OSError, ET.ParseError) as error:
                if uuid not in unreachable:
                    unreachable.add(uuid)
                    emit("speaker_unreachable", room=groups[uuid]["room"], ip=groups[uuid]["ip"], error=str(error))
                continue
            if uuid in unreachable:
                unreachable.discard(uuid)
                emit("speaker_reachable", room=now["room"], ip=now["ip"])
            for event in compare(last.get(uuid), now):
                emit(event, **describe(now))
            last[uuid] = now

        time.sleep(max(0.0, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
