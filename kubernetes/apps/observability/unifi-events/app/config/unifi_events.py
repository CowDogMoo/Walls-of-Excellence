#!/usr/bin/env python3
"""Export UniFi traffic flows and client events as JSON lines.

The controller keeps both in a shallow store that only its local API can
read: a few hours of flows, queried by the Network UI itself. This polls the
same two endpoints and prints one line per new record, so the history lives
in Loki and carries what the syslog export leaves out: the client MAC, both
ports, the destination domain and the firewall policy that matched.

Stdlib only, so it runs on a stock python image with a read-only filesystem.
"""

import json
import os
import signal
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

URL = os.environ["UNIFI_URL"].rstrip("/")
API_KEY = os.environ["UNIFI_API_KEY"]
SITE = os.environ.get("UNIFI_SITE", "default")
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "60"))
# A record shows up in the API up to a minute after it happened, and a flow's
# counters keep changing for a while after that. Each poll therefore re-reads
# the last LOOKBACK_SECONDS and skips what it already printed, and it leaves
# the newest SETTLE_SECONDS for the next poll.
LOOKBACK_SECONDS = int(os.environ.get("LOOKBACK_SECONDS", "300"))
SETTLE_SECONDS = int(os.environ.get("SETTLE_SECONDS", "90"))
PAGE_SIZE = int(os.environ.get("PAGE_SIZE", "500"))
MAX_PAGES = int(os.environ.get("MAX_PAGES", "40"))
# all | local | none. "local" keeps allowed flows between the home networks
# and drops allowed flows to the internet, which are most of the volume.
ALLOWED_FLOWS = os.environ.get("ALLOWED_FLOWS", "all")
# Loki refuses lines far behind the newest one in a stream, so the timestamp
# handed to the pipeline is never older than this. The true time stays in
# the "time" field.
MAX_TS_LAG_SECONDS = int(os.environ.get("MAX_TS_LAG_SECONDS", "1500"))

API = f"{URL}/proxy/network/v2/api/site/{SITE}"
# The gateway serves a self-signed certificate for its LAN address.
TLS = ssl.create_default_context()
TLS.check_hostname = False
TLS.verify_mode = ssl.CERT_NONE


def iso(ms):
    return (
        datetime.fromtimestamp(ms / 1000, timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def emit(kind, when_ms, **fields):
    floor_ms = int((time.time() - MAX_TS_LAG_SECONDS) * 1000)
    line = {"ts": iso(max(when_ms, floor_ms)), "time": iso(when_ms), "kind": kind}
    line.update({k: v for k, v in fields.items() if v not in (None, "", [], {})})
    print(json.dumps(line, separators=(",", ":"), sort_keys=True), flush=True)


def post(path, body):
    request = urllib.request.Request(
        f"{API}/{path}",
        data=json.dumps(body).encode(),
        headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30, context=TLS) as response:
        return json.load(response)


def pages(path, start_ms, end_ms, extra):
    """Yield every record in the window, oldest page last as the API returns it."""
    for page in range(MAX_PAGES):
        body = {
            "timestampFrom": start_ms,
            "timestampTo": end_ms,
            "pageNumber": page,
            "pageSize": PAGE_SIZE,
        }
        body.update(extra)
        rows = post(path, body).get("data") or []
        yield from rows
        if len(rows) < PAGE_SIZE:
            return
    emit(
        "exporter",
        int(time.time() * 1000),
        event="window_truncated",
        path=path,
        pages=MAX_PAGES,
    )


def flow_line(row):
    action = row.get("action")
    direction = row.get("direction")
    if action != "blocked":
        if ALLOWED_FLOWS == "none":
            return None
        if ALLOWED_FLOWS == "local" and direction != "local":
            return None
    src = row.get("source") or {}
    dst = row.get("destination") or {}
    traffic = row.get("traffic_data") or {}
    domains = dst.get("domains") or []
    policies = [p.get("name") for p in row.get("policies") or [] if p.get("name")]
    return {
        "id": row.get("id"),
        "action": action,
        "direction": direction,
        "protocol": row.get("protocol"),
        "service": row.get("service"),
        "risk": row.get("risk"),
        "policy": ", ".join(policies),
        "src_name": src.get("client_name") or src.get("host_name"),
        "src_mac": src.get("mac"),
        "src_ip": src.get("ip"),
        "src_port": src.get("port"),
        "src_network": src.get("network_name") or src.get("zone_name"),
        "dst_name": dst.get("client_name") or dst.get("host_name"),
        "dst_mac": dst.get("mac"),
        "dst_ip": dst.get("ip"),
        "dst_port": dst.get("port"),
        "dst_network": dst.get("network_name") or dst.get("zone_name"),
        "dst_domain": domains[0] if domains else None,
        "dst_region": dst.get("region"),
        "bytes": traffic.get("bytes_total"),
        "bytes_tx": traffic.get("bytes_tx"),
        "bytes_rx": traffic.get("bytes_rx"),
        "packets": traffic.get("packets_total"),
        "count": row.get("count"),
        "duration_ms": row.get("duration_milliseconds"),
    }


def label(value):
    """A system-log parameter is an object naming a client, device or value."""
    if isinstance(value, dict):
        return value.get("name") or value.get("hostname") or value.get("id")
    return value


def client_event_line(row):
    # Firewall blocks also appear here, but the flow records carry them with
    # ports and MACs, so printing them again would only double the volume.
    if row.get("category") == "SECURITY":
        return None
    params = row.get("parameters") or {}
    client = params.get("CLIENT") if isinstance(params.get("CLIENT"), dict) else {}
    message = row.get("message_raw") or ""
    for name, value in params.items():
        message = message.replace("{" + name + "}", str(label(value)))
    detail = {
        name.lower(): label(value)
        for name, value in params.items()
        if name not in ("CLIENT", "CONSOLE_NAME", "INITIATOR_ID")
    }
    return {
        "id": row.get("id"),
        "event": row.get("event"),
        "category": row.get("category"),
        "severity": row.get("severity"),
        "client_name": client.get("name") or client.get("hostname"),
        "client_mac": client.get("id"),
        "client_ip": client.get("ip"),
        "message": message.strip(),
        **detail,
    }


SUMMED = ("bytes", "bytes_tx", "bytes_rx", "packets", "count")


def collapse(fresh):
    """Fold repeats of one conversation within a poll into a single line.

    A poller that opens a new connection every two seconds would otherwise
    print thirty near-identical lines a minute for each device it talks to.
    The first line of a group is kept, its counters are summed and
    "last_time" marks the newest repeat, so who talked to what, how often
    and from when until when all survive.
    """
    groups = {}
    for when_ms, fields in fresh:
        fields["count"] = fields.get("count") or 1
        key = (
            fields.get("src_mac") or fields.get("src_ip"),
            fields.get("dst_ip"),
            fields.get("dst_port"),
            fields.get("protocol"),
            fields.get("action"),
            fields.get("direction"),
            fields.get("policy"),
        )
        group = groups.get(key)
        if group is None:
            groups[key] = [when_ms, when_ms, fields]
            continue
        group[1] = max(group[1], when_ms)
        if when_ms < group[0]:
            group[0] = when_ms
        for name in SUMMED:
            if fields.get(name) is not None:
                group[2][name] = (group[2].get(name) or 0) + fields[name]
    collapsed = []
    for first_ms, last_ms, fields in groups.values():
        if last_ms != first_ms:
            fields["last_time"] = iso(last_ms)
        collapsed.append((first_ms, fields))
    return collapsed


SOURCES = (
    # (kind, path, extra request fields, record time field, formatter, fold)
    ("flow", "traffic-flows", {}, "time", flow_line, collapse),
    (
        "client_event",
        "system-log/all",
        {"searchText": ""},
        "timestamp",
        client_event_line,
        None,
    ),
)


def poll(seen, now_ms):
    start_ms = now_ms - LOOKBACK_SECONDS * 1000
    end_ms = now_ms - SETTLE_SECONDS * 1000
    for kind, path, extra, time_field, formatter, fold in SOURCES:
        fresh = []
        for row in pages(path, start_ms, end_ms, extra):
            key = (kind, row.get("id"))
            when_ms = row.get(time_field)
            if key in seen or not isinstance(when_ms, int):
                continue
            seen[key] = when_ms
            fields = formatter(row)
            if fields:
                fresh.append((when_ms, fields))
        if fold:
            fresh = fold(fresh)
        for when_ms, fields in sorted(fresh, key=lambda item: item[0]):
            emit(kind, when_ms, **fields)
    # Anything older than two windows can no longer be returned by a poll.
    horizon = now_ms - 2 * LOOKBACK_SECONDS * 1000
    for key in [key for key, when_ms in seen.items() if when_ms < horizon]:
        del seen[key]


def main():
    # As PID 1 in a container Python ignores SIGTERM unless it is handled.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    emit(
        "exporter",
        int(time.time() * 1000),
        event="exporter_started",
        poll_seconds=POLL_SECONDS,
        lookback_seconds=LOOKBACK_SECONDS,
        allowed_flows=ALLOWED_FLOWS,
    )
    seen = {}
    healthy = True
    while True:
        started = time.monotonic()
        now_ms = int(time.time() * 1000)
        try:
            poll(seen, now_ms)
            if not healthy:
                emit("exporter", now_ms, event="poll_recovered")
            healthy = True
        except (urllib.error.URLError, OSError, ValueError) as error:
            # Say it once per outage; the gap in the records shows the rest.
            if healthy:
                emit("exporter", now_ms, event="poll_failed", error=str(error)[:300])
            healthy = False
        time.sleep(max(1.0, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
