"""Log every Sonos playback change as one JSON line on stdout.

Each speaker is asked to push its transport state here (a UPnP event
subscription), and an event is printed whenever what a group is doing
changes: started, stopped, a new track, a new source. The lines are shipped
to Loki as {job="sonos-events"}.

Sonos closes the connection after every request, so asking every speaker
three questions every two seconds cost about a thousand connections a
minute. Pushes cost none while the house is quiet. A slow poll stays as a
safety net, and a speaker whose pushes do not arrive is polled at the old
pace instead, so the log never depends on the callback path working.

A speaker cannot name the Spotify account driving it, so the useful signal
for "who started this" is the pair (source, session): a Spotify Connect
session id the household did not start is somebody else's app.
"""

import concurrent.futures
import html
import http.client
import http.server
import json
import os
import queue
import re
import signal
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

SEEDS = [s.strip() for s in os.environ["SONOS_SEEDS"].split(",") if s.strip()]
# How often a speaker is polled while its pushes are not arriving.
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
# How often every speaker is polled regardless, to catch a push that was lost.
SAFETY_POLL_SECONDS = float(os.environ.get("SAFETY_POLL_SECONDS", "60"))
TOPOLOGY_SECONDS = float(os.environ.get("TOPOLOGY_SECONDS", "60"))
TIMEOUT = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "4"))
# The address speakers call back on. Without it nothing is subscribed and
# every speaker is polled every POLL_SECONDS.
CALLBACK_HOST = os.environ.get("CALLBACK_HOST", "")
CALLBACK_PORT = int(os.environ.get("CALLBACK_PORT", "14000"))
SUBSCRIPTION_SECONDS = int(os.environ.get("SUBSCRIPTION_SECONDS", "600"))
# A speaker sends its whole state the moment it accepts a subscription. If
# that has not arrived after this long, its pushes are not reaching us.
CONFIRM_SECONDS = float(os.environ.get("CONFIRM_SECONDS", "10"))
# How long to leave a speaker alone after it refused or missed a subscription.
RETRY_SECONDS = float(os.environ.get("RETRY_SECONDS", "60"))

ENVELOPE = (
    '<?xml version="1.0"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
    '<u:{action} xmlns:u="urn:schemas-upnp-org:service:{service}:1">{args}'
    "</u:{action}></s:Body></s:Envelope>"
)
INSTANCE = "<InstanceID>0</InstanceID>"
PLAYING = {"PLAYING", "TRANSITIONING"}
EVENT_PATH = "/MediaRenderer/AVTransport/Event"
# The pushed state variables that carry what the three polled calls return.
PUSHED = ("TransportState", "AVTransportURI", "CurrentTrackURI", "CurrentTrackMetaData")
MAX_NOTIFY_BYTES = 512 * 1024


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
    """Return (groups, players) from any seed.

    groups is {coordinator_uuid: {"ip", "room", "members"}} and players is
    {uuid: {"ip", "room"}} for every visible speaker.
    """
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
        players = {}
        for group in state.iter("ZoneGroup"):
            coordinator = group.get("Coordinator")
            # Invisible members are the satellites of a bonded set; the room
            # is already represented by its visible player.
            members = [m for m in group.findall("ZoneGroupMember") if m.get("Invisible") != "1"]
            lead = next((m for m in members if m.get("UUID") == coordinator), None)
            if lead is None:
                continue
            for member in members:
                players[member.get("UUID")] = {
                    "ip": re.search(r"//([^:/]+)", member.get("Location")).group(1),
                    "room": member.get("ZoneName"),
                }
            groups[coordinator] = {
                "ip": players[coordinator]["ip"],
                "room": lead.get("ZoneName"),
                "members": sorted(m.get("ZoneName") for m in members),
            }
        return groups, players
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


def snapshot(group, state, uri, track_uri, metadata):
    """What a group is doing, in the same shape whether pushed or polled."""
    source, session = classify(uri, track_uri)
    return {
        "room": group["room"],
        "ip": group["ip"],
        "group": group["members"] if len(group["members"]) > 1 else None,
        "playing": state in PLAYING,
        "state": state.lower(),
        "source": source,
        "session": session,
        "stream_host": stream_host(uri, track_uri) if source == "stream" else "",
        "title": didl(metadata, "dc:title"),
        "artist": didl(metadata, "dc:creator"),
        "album": didl(metadata, "upnp:album"),
    }


def read(group):
    ip = group["ip"]
    transport = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetTransportInfo", INSTANCE)
    media = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetMediaInfo", INSTANCE)
    position = soap(ip, "/MediaRenderer/AVTransport/Control", "AVTransport", "GetPositionInfo", INSTANCE)
    return snapshot(
        group,
        tag(transport, "CurrentTransportState"),
        tag(media, "CurrentURI"),
        tag(position, "TrackURI"),
        tag(position, "TrackMetaData"),
    )


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


def parse_notify(body):
    """Return the pushed state variables in a speaker's NOTIFY body."""
    change = next((el.text for el in ET.fromstring(body).iter() if el.tag.endswith("LastChange")), None)
    if not change:
        return {}
    variables = {}
    for instance in ET.fromstring(change):
        for variable in instance:
            name = variable.tag.rsplit("}", 1)[-1]
            if name in PUSHED:
                variables[name] = variable.get("val") or ""
    return variables


def subscription(ip, method, headers):
    """Send SUBSCRIBE or UNSUBSCRIBE and return (status, sid, granted seconds)."""
    connection = http.client.HTTPConnection(ip, 1400, timeout=TIMEOUT)
    try:
        connection.request(method, EVENT_PATH, headers=headers)
        response = connection.getresponse()
        response.read()
        granted = re.search(r"\d+", response.getheader("TIMEOUT") or "")
        return (
            response.status,
            response.getheader("SID"),
            int(granted.group()) if granted else SUBSCRIPTION_SECONDS,
        )
    finally:
        connection.close()


def subscribe(uuid, ip):
    return subscription(
        ip,
        "SUBSCRIBE",
        {
            "CALLBACK": f"<http://{CALLBACK_HOST}:{CALLBACK_PORT}/notify/{uuid}>",
            "NT": "upnp:event",
            "TIMEOUT": f"Second-{SUBSCRIPTION_SECONDS}",
        },
    )


def renew(sid, ip):
    return subscription(ip, "SUBSCRIBE", {"SID": sid, "TIMEOUT": f"Second-{SUBSCRIPTION_SECONDS}"})


class Exporter:
    """Owns all state. Only the main thread touches it; pushes arrive by queue."""

    def __init__(self):
        self.push = bool(CALLBACK_HOST)
        self.groups = {}
        self.players = {}
        self.last = {}
        self.unreachable = set()
        # uuid -> {"sid", "ip", "renew_at", "confirm_by", "confirmed"}. A
        # record with no sid is a speaker waiting for its next attempt.
        self.subscriptions = {}
        # Speakers already reported as push_unavailable.
        self.silent = set()
        # uuid -> the latest pushed value of each variable in PUSHED
        self.pushed = {}
        self.inbox = queue.Queue()
        self.wake = threading.Event()
        self.stopping = False
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=16)
        self.next_topology = 0.0
        # The first topology pass polls every speaker it finds.
        self.next_safety = time.monotonic() + SAFETY_POLL_SECONDS
        self.next_fast = 0.0

    # -- reporting --------------------------------------------------------

    def report(self, uuid, now):
        for event in compare(self.last.get(uuid), now):
            emit(event, **describe(now))
        self.last[uuid] = now

    def report_poll(self, uuid, now):
        before = self.last.get(uuid)
        if before and self.pushing(uuid):
            # While pushes are arriving they are the authority on the track.
            # A poll that agrees on what is playing must not re-announce it
            # just because the two views word the metadata differently.
            if all(now[k] == before[k] for k in ("playing", "source", "session")):
                now = {**now, **{k: before[k] for k in ("title", "artist", "album")}}
        self.report(uuid, now)

    # -- pushes -----------------------------------------------------------

    def pushing(self, uuid):
        return self.subscriptions.get(uuid, {}).get("confirmed", False)

    def without_push(self, uuid, now):
        """True once a speaker is known not to be pushing, so it must be polled."""
        if not self.push:
            return True
        held = self.subscriptions.get(uuid)
        return held is None or (not held["confirmed"] and now >= held["confirm_by"])

    def apply_push(self, uuid, sid, variables):
        held = self.subscriptions.get(uuid)
        # Anything on the network can reach the callback port; only a NOTIFY
        # carrying the id the speaker itself issued is believed.
        if not held or not sid or held["sid"] != sid:
            return
        held["confirmed"] = True
        if uuid in self.silent:
            self.silent.discard(uuid)
            player = self.players.get(uuid, {})
            emit("push_restored", room=player.get("room"), ip=player.get("ip"))
        state = self.pushed.setdefault(uuid, {})
        state.update(variables)
        if not all(name in state for name in PUSHED):
            return
        follows = state["AVTransportURI"].startswith("x-rincon:")
        if follows == (uuid in self.groups):
            # A speaker that follows another is not a coordinator, and one
            # that plays for itself is. The grouping changed under us.
            self.next_topology = 0.0
            return
        if uuid in self.groups:
            self.report(
                uuid,
                snapshot(
                    self.groups[uuid],
                    state["TransportState"],
                    state["AVTransportURI"],
                    state["CurrentTrackURI"],
                    state["CurrentTrackMetaData"],
                ),
            )

    def drain(self):
        pending = []
        while True:
            try:
                pending.append(self.inbox.get_nowait())
            except queue.Empty:
                return pending

    # -- subscriptions ----------------------------------------------------

    def maintain_subscriptions(self, now):
        if not self.push:
            return
        for uuid in set(self.subscriptions) - set(self.players):
            self.forget(uuid)
        jobs = {}
        for uuid, player in self.players.items():
            held = self.subscriptions.get(uuid)
            if held and held["ip"] != player["ip"]:
                self.forget(uuid)
                held = None
            if held is None or (now >= held["renew_at"] and not held["confirmed"]):
                # Never subscribed, or subscribed and silent. Only a fresh
                # subscription makes a speaker send its state, which is the
                # proof that its pushes reach us.
                jobs[uuid] = (True, self.pool.submit(subscribe, uuid, player["ip"]))
            elif now >= held["renew_at"]:
                jobs[uuid] = (False, self.pool.submit(renew, held["sid"], held["ip"]))
        for uuid, (fresh, job) in jobs.items():
            try:
                status, sid, granted = job.result()
            except (OSError, http.client.HTTPException):
                status, sid, granted = 0, None, 0
            ip = self.players[uuid]["ip"]
            if status == 200 and not fresh:
                self.subscriptions[uuid]["renew_at"] = now + granted / 2
                continue
            self.pushed.pop(uuid, None)
            if status == 200 and sid:
                self.subscriptions[uuid] = {
                    "sid": sid,
                    "ip": ip,
                    "renew_at": now + granted / 2,
                    "confirm_by": now + CONFIRM_SECONDS,
                    "confirmed": False,
                }
            elif fresh:
                # Refused or unreachable: poll it, and try again later.
                self.subscriptions[uuid] = {
                    "sid": None,
                    "ip": ip,
                    "renew_at": now + RETRY_SECONDS,
                    "confirm_by": now,
                    "confirmed": False,
                }
            else:
                # The speaker forgot a working subscription (it restarted, or
                # one push to us failed). Subscribe afresh on the next pass.
                self.subscriptions[uuid] = {
                    "sid": None,
                    "ip": ip,
                    "renew_at": now,
                    "confirm_by": now + CONFIRM_SECONDS,
                    "confirmed": False,
                }
        for uuid, held in self.subscriptions.items():
            if not held["confirmed"] and now >= held["confirm_by"] and uuid not in self.silent:
                self.silent.add(uuid)
                player = self.players.get(uuid, {})
                emit("push_unavailable", room=player.get("room"), ip=player.get("ip"))

    def forget(self, uuid):
        self.subscriptions.pop(uuid, None)
        self.pushed.pop(uuid, None)
        self.silent.discard(uuid)

    def unsubscribe_all(self):
        jobs = [
            self.pool.submit(subscription, held["ip"], "UNSUBSCRIBE", {"SID": held["sid"]})
            for held in self.subscriptions.values()
            if held["sid"]
        ]
        for job in jobs:
            try:
                job.result()
            except (OSError, http.client.HTTPException):
                pass

    # -- polling ----------------------------------------------------------

    def poll(self, uuids):
        jobs = {uuid: self.pool.submit(read, self.groups[uuid]) for uuid in uuids}
        results = {}
        for uuid, job in jobs.items():
            group = self.groups[uuid]
            try:
                results[uuid] = job.result()
            except (OSError, ET.ParseError) as error:
                if uuid not in self.unreachable:
                    self.unreachable.add(uuid)
                    emit("speaker_unreachable", room=group["room"], ip=group["ip"], error=str(error))
                continue
            if uuid in self.unreachable:
                self.unreachable.discard(uuid)
                emit("speaker_reachable", room=group["room"], ip=group["ip"])
        # A push that landed while the poll was in flight is newer than the
        # poll's answer for that speaker.
        pending = self.drain()
        overtaken = {uuid for uuid, _, _ in pending}
        for uuid, now in results.items():
            if uuid not in overtaken:
                self.report_poll(uuid, now)
        for uuid, sid, variables in pending:
            self.apply_push(uuid, sid, variables)

    def refresh_topology(self):
        found = topology()
        if found is None:
            emit("topology_unreachable", seeds=SEEDS)
            return
        groups, players = found
        if sorted(g["room"] for g in groups.values()) != sorted(g["room"] for g in self.groups.values()):
            emit("topology", rooms=sorted(g["room"] for g in groups.values()))
        arrived = set(groups) - set(self.groups)
        self.groups, self.players = groups, players
        for gone in set(self.last) - set(groups):
            del self.last[gone]
        self.unreachable &= set(groups)
        # A speaker that just became a coordinator has no history here yet.
        if arrived:
            self.poll(arrived)

    # -- main loop --------------------------------------------------------

    def step(self):
        now = time.monotonic()
        if now >= self.next_topology:
            self.next_topology = now + TOPOLOGY_SECONDS
            self.refresh_topology()
        self.maintain_subscriptions(now)
        for uuid, sid, variables in self.drain():
            self.apply_push(uuid, sid, variables)
        if now >= self.next_safety:
            self.next_safety = now + SAFETY_POLL_SECONDS
            self.next_fast = now + POLL_SECONDS
            self.poll(set(self.groups))
        elif now >= self.next_fast:
            self.next_fast = now + POLL_SECONDS
            unpushed = {uuid for uuid in self.groups if self.without_push(uuid, now)}
            if unpushed:
                self.poll(unpushed)

    def wait(self):
        now = time.monotonic()
        due = [self.next_topology, self.next_safety, self.next_fast]
        for held in self.subscriptions.values():
            due.append(held["renew_at"])
            if not held["confirmed"] and held["confirm_by"] > now:
                due.append(held["confirm_by"])
        self.wake.wait(max(0.05, min(due) - now))
        self.wake.clear()

    def run(self):
        while not self.stopping:
            self.step()
            self.wait()
        self.unsubscribe_all()


def serve(exporter):
    class Callback(http.server.BaseHTTPRequestHandler):
        def do_NOTIFY(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if 0 < length <= MAX_NOTIFY_BYTES else b""
            self.send_response(200 if body else 400)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                variables = parse_notify(body) if body else {}
            except ET.ParseError:
                return
            exporter.inbox.put((self.path.rsplit("/", 1)[-1], self.headers.get("SID"), variables))
            exporter.wake.set()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("0.0.0.0", CALLBACK_PORT), Callback)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main():
    exporter = Exporter()

    def stop(*_):
        exporter.stopping = True
        exporter.wake.set()

    # As PID 1 in a container Python ignores SIGTERM unless it is handled,
    # and the speakers should be told to stop pushing before we go.
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if exporter.push:
        try:
            serve(exporter)
        except OSError as error:
            # Without the listener nothing can be pushed; poll as before.
            exporter.push = False
            emit("callback_unavailable", port=CALLBACK_PORT, error=str(error))
    emit(
        "exporter_started",
        seeds=SEEDS,
        poll_seconds=POLL_SECONDS,
        safety_poll_seconds=SAFETY_POLL_SECONDS,
        callback=f"{CALLBACK_HOST}:{CALLBACK_PORT}" if exporter.push else None,
    )
    exporter.run()


if __name__ == "__main__":
    main()
    sys.exit(0)
