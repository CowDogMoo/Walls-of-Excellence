"""Generate the server rack dashboard and its expected-cable rules.

Reads   kubernetes/apps/observability/grafana/app/rack/rack.yaml
Writes  .../rack/rack-prometheusrule.yaml  (static "expected" series)
        .../rack/rack-dashboard.yaml       (Grafana dashboard ConfigMap)

Usage:
    python3 -I hack/rack-gen.py           regenerate both files
    python3 -I hack/rack-gen.py --check   fail if the committed files are stale

Needs PyYAML. The rack-gen pre-commit hook installs its own copy.
"""

import json
import math
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
RACK_DIR = REPO / "kubernetes/apps/observability/grafana/app/rack"
FACTS = RACK_DIR / "rack.yaml"
RULE_OUT = RACK_DIR / "rack-prometheusrule.yaml"
DASH_OUT = RACK_DIR / "rack-dashboard.yaml"

DS = {"type": "prometheus", "uid": "prometheus"}
UNSET = "not set"

# Kinds UniFi manages itself. They never show up as a client on a switch
# port, so their cables can only be checked by link state.
UNIFI_KINDS = {"switch", "gateway", "access-point"}
# Kinds with nothing to poll: drawn in a neutral colour.
PASSIVE_KINDS = {
    "pdu", "fan", "light", "patch-panel", "shelf", "power-supply", "space",
    "isp", "other",
}
KINDS = UNIFI_KINDS | PASSIVE_KINDS | {
    "node", "nas", "ups", "amp", "hub", "bridge", "client", "camera",
}

COLOR_UP = "#299c46"
COLOR_DOWN = "#c4162a"
COLOR_PASSIVE = "#3d4654"
COLOR_SHELF = "#22262e"
COLOR_SPACE = "#181b1f"
COLOR_PORT_DOWN = "#2f343c"
COLOR_TEXT = "#ffffff"
COLOR_MUTED = "#9aa3b2"
COLOR_POE = "#ffffff"
SPEED_STEPS = [
    {"color": "#e0752d", "value": None},
    {"color": "#cca300", "value": 100_000_000},
    {"color": COLOR_UP, "value": 1_000_000_000},
    {"color": "#3274d9", "value": 10_000_000_000},
]


class RackError(Exception):
    """A problem in rack.yaml that the person editing it can fix."""


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")

_TOP_KEYS = {"rack", "discrepancies", "networks", "devices", "cables"}
_RACK_KEYS = {"name", "model", "height_u", "notes"}
_NETWORK_KEYS = {"name", "vlan", "cidr", "gateway"}
_DEVICE_KEYS = {
    "name", "kind", "model", "role", "mac", "ip", "ports", "in_rack", "order", "u", "height_u",
    "shelf", "mount", "quantity", "watts", "power", "always_on", "notes",
}
_POWER_KEYS = {"source", "outlet"}
_CABLE_KEYS = {"a", "b", "through", "unifi_label", "type", "patch_panel", "label", "color"}
_END_KEYS = {"device", "port"}


def _text(value, what):
    """A free-text fact, which YAML must have read as text.

    Unquoted, YAML turns 1:12, 012, 4, on and yes into numbers and booleans,
    and the dashboard would show the converted value.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise RackError(
            f"{what} was read by YAML as {value!r}, not as text. "
            'Put it in double quotes, for example patch_panel: "1:12"'
        )
    return value


def _known_keys(raw, keys, what):
    unknown = sorted(str(key) for key in raw if key not in keys)
    if unknown:
        raise RackError(f"{what}: unknown key {', '.join(unknown)}; the keys are {', '.join(sorted(keys))}")


def _list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise RackError(f"{what} must be a list of '- ' items, got {value!r}")
    return value


def _flag(value, what):
    if value is not None and not isinstance(value, bool):
        raise RackError(f"{what} must be true, false or blank, got {value!r}")
    return value


def _positive_int(value, what):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RackError(f"{what} must be a whole number of 1 or more, got {value!r}")
    return value


def load_model(text):
    """Validate rack.yaml and return the model the generators work from."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RackError(f"not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RackError("rack.yaml must be a map with rack, devices and cables")
    _known_keys(data, _TOP_KEYS, "rack.yaml")
    rack = data.get("rack") or {}
    if not isinstance(rack, dict) or not _text(rack.get("name"), "rack.name"):
        raise RackError("rack.name is required")
    _known_keys(rack, _RACK_KEYS, "rack")
    rack_h = _positive_int(rack.get("height_u"), "rack.height_u")

    networks = []
    for raw in _list(data.get("networks"), "networks"):
        if not isinstance(raw, dict):
            raise RackError(f"bad network entry: {raw!r}")
        _known_keys(raw, _NETWORK_KEYS, "network")
        name = _text(raw.get("name"), "a network's name")
        vlan = raw.get("vlan")
        if not isinstance(vlan, str):
            vlan = _positive_int(vlan, f"network {name!r}: vlan")
        networks.append({
            "name": name,
            "vlan": vlan,
            "cidr": _text(raw.get("cidr"), f"network {name!r}: cidr"),
            "gateway": _text(raw.get("gateway"), f"network {name!r}: gateway"),
        })

    devices = {}
    for raw in _list(data.get("devices"), "devices"):
        name = _text(raw.get("name"), "a device's name") if isinstance(raw, dict) else ""
        if not name:
            raise RackError(f"every device needs a name: {raw!r}")
        if name in devices:
            raise RackError(f"device {name!r} is listed twice")
        what = f"device {name!r}"
        _known_keys(raw, _DEVICE_KEYS, what)
        kind = raw.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:
            raise RackError(f"{what}: kind must be one of {sorted(KINDS)}, got {kind!r}")
        mac = raw.get("mac")
        if mac is not None:
            mac = str(mac).lower()
            if not _MAC_RE.match(mac):
                raise RackError(f"{what}: mac {raw['mac']!r} is not aa:bb:cc:dd:ee:ff")
        mount = raw.get("mount")
        if mount not in (None, "rear"):
            raise RackError(f"{what}: mount must be rear or blank, got {mount!r}")
        watts = raw.get("watts")
        if watts is not None and (isinstance(watts, bool) or not isinstance(watts, (int, float))):
            raise RackError(f"{what}: watts must be a number, got {watts!r}")
        power = raw.get("power") or {}
        if not isinstance(power, dict):
            raise RackError(f"{what}: power must have source and outlet")
        _known_keys(power, _POWER_KEYS, f"{what}: power")
        devices[name] = {
            "name": name,
            "kind": kind,
            "model": _text(raw.get("model"), f"{what}: model"),
            "role": _text(raw.get("role"), f"{what}: role"),
            "mac": mac,
            "ip": _text(raw.get("ip"), f"{what}: ip"),
            "ports": _switch_ports(name, raw.get("ports")),
            "in_rack": _flag(raw.get("in_rack"), f"{what}: in_rack"),
            "order": _positive_int(raw.get("order"), f"{what}: order"),
            "u": _positive_int(raw.get("u"), f"{what}: u"),
            "height_u": _positive_int(raw.get("height_u"), f"{what}: height_u"),
            "shelf": _text(raw.get("shelf"), f"{what}: shelf") or None,
            "mount": mount,
            "quantity": _positive_int(raw.get("quantity"), f"{what}: quantity"),
            "watts": watts,
            "power_source": _text(power.get("source"), f"{what}: power.source"),
            "power_outlet": _text(power.get("outlet"), f"{what}: power.outlet"),
            "has_power": "power" in raw,
            "always_on": _flag(raw.get("always_on"), f"{what}: always_on") is not False,
            "notes": _text(raw.get("notes"), f"{what}: notes"),
        }

    macs = {}
    for dev in devices.values():
        if dev["mac"]:
            if dev["mac"] in macs:
                raise RackError(f"mac {dev['mac']} is on both {macs[dev['mac']]!r} and {dev['name']!r}")
            macs[dev["mac"]] = dev["name"]
        shelf = dev["shelf"]
        if shelf is not None and (shelf not in devices or devices[shelf]["kind"] != "shelf"):
            raise RackError(f"device {dev['name']!r}: shelf {shelf!r} is not a device of kind shelf")
        position = [key for key in ("shelf", "mount", "order", "u", "height_u") if dev[key] is not None]
        if dev["in_rack"] is False and position:
            raise RackError(
                f"device {dev['name']!r}: in_rack is false, so it has no place in the rack; "
                f"remove {', '.join(position)}"
            )
        if position and position[0] in ("shelf", "mount") and position[1:]:
            raise RackError(
                f"device {dev['name']!r}: {position[0]} already says where it is; "
                f"remove {', '.join(position[1:])}"
            )
        if dev["u"] is not None:
            if rack_h is None:
                raise RackError(f"device {dev['name']!r} has a u but rack.height_u is blank")
            top = dev["u"] + (dev["height_u"] or 1) - 1
            if top > rack_h:
                raise RackError(f"device {dev['name']!r}: u {dev['u']} to {top} is above the {rack_h}U rack")

    placed = sorted((d for d in devices.values() if d["u"] is not None), key=lambda d: d["u"])
    for low, high in zip(placed, placed[1:]):
        if low["u"] + (low["height_u"] or 1) - 1 >= high["u"]:
            raise RackError(f"{low['name']!r} and {high['name']!r} overlap in the rack")

    cables = []
    direct = {}
    for raw in _list(data.get("cables"), "cables"):
        if not isinstance(raw, dict):
            raise RackError(f"bad cable entry: {raw!r}")
        a, b = raw.get("a"), raw.get("b")
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise RackError(f"cable needs a: {{device, port}} and b: {{device}}: {raw!r}")
        for end in (a, b):
            _known_keys(end, _END_KEYS, "cable end")
            if _text(end.get("device"), "a cable end's device") not in devices:
                raise RackError(f"cable end {end.get('device')!r} is not a listed device")
        _check_port(devices, a, required=True)
        _check_port(devices, b, required=False)
        what = f"cable from {a['device']} port {a['port']} to {b['device']}"
        _known_keys(raw, _CABLE_KEYS, what)
        through = _text(raw.get("through"), f"{what}: through") or None
        if through is not None and through not in devices:
            raise RackError(f"cable through {through!r} is not a listed device")
        cable = {
            "a": (a["device"], a["port"]),
            "b": (b["device"], b.get("port")),
            "through": through,
            "unifi_label": _text(raw.get("unifi_label"), f"{what}: unifi_label"),
            "type": _text(raw.get("type"), f"{what}: type"),
            "patch_panel": _text(raw.get("patch_panel"), f"{what}: patch_panel"),
            "label": _text(raw.get("label"), f"{what}: label"),
            "color": _text(raw.get("color"), f"{what}: color"),
        }
        if through is None:
            for end in (cable["a"], cable["b"]):
                if end[1] is None:
                    continue
                if end in direct:
                    raise RackError(
                        f"{end[0]} port {end[1]} has two cables; mark the extra one with 'through:'"
                    )
                direct[end] = cable
        cables.append(cable)
    for cable in cables:
        if cable["through"] is not None and cable["a"] not in direct:
            raise RackError(
                f"{cable['b'][0]!r} goes through {cable['through']!r} on {cable['a'][0]} port "
                f"{cable['a'][1]}, but that port has no direct cable"
            )

    return {
        "rack": {
            "name": rack["name"],
            "model": _text(rack.get("model"), "rack.model"),
            "height_u": rack_h,
            "notes": [_text(n, "a rack.notes entry") for n in _list(rack.get("notes"), "rack.notes")],
        },
        "discrepancies": [
            _text(n, "a discrepancies entry") for n in _list(data.get("discrepancies"), "discrepancies")
        ],
        "networks": networks,
        "devices": devices,
        "cables": cables,
    }


_PLAIN_NAME_RE = re.compile(r"^[A-Za-z0-9 _-]+$")


def _switch_ports(name, ports):
    ports = _positive_int(ports, f"device {name!r}: ports")
    if ports is not None and not _PLAIN_NAME_RE.match(name):
        raise RackError(
            f"device {name!r}: a device with ports is matched by name in queries, "
            "so its name may only use letters, digits, spaces, '-' and '_'"
        )
    return ports


def _check_port(devices, end, required):
    dev = devices[end["device"]]
    port = end.get("port")
    if port is None:
        if required:
            raise RackError(f"cable end a on {dev['name']!r} needs a port")
        return
    _positive_int(port, f"cable port on {dev['name']!r}")
    if dev["ports"] is None:
        raise RackError(f"cable names port {port} on {dev['name']!r}, which has no 'ports:' count")
    if port > dev["ports"]:
        raise RackError(f"{dev['name']!r} has {dev['ports']} ports; cable names port {port}")


def port_expectations(model):
    """One row per (switch port, expected far end)."""
    devices = model["devices"]
    rows = []
    for cable in model["cables"]:
        ends = [(cable["a"], cable["b"], cable["unifi_label"])]
        if cable["b"][1] is not None:
            ends.append((cable["b"], cable["a"], ""))
        for (switch, port), (far, far_port), unifi_label in ends:
            dev = devices[far]
            by_mac = bool(dev["mac"]) and dev["kind"] not in UNIFI_KINDS
            if not by_mac:
                check = "link" if cable["through"] is None else "none"
            elif dev["always_on"]:
                check = "mac"
            else:
                check = "mac-when-on"
            # A device reached through another shares that device's cable.
            shared = "shared" if cable["through"] is not None else ""
            rows.append({
                "cable": f"{switch} {port} > {far}",
                "switch": switch,
                "port": str(port),
                "device": far if far_port is None else f"{far} port {far_port}",
                "mac": dev["mac"] if by_mac else "",
                "kind": dev["kind"],
                "check": check,
                "through": cable["through"] or "",
                "unifi_label": unifi_label,
                "cable_type": cable["type"],
                "cable_label": cable["label"] or shared,
                "cable_color": cable["color"] or shared,
                "patch_panel": cable["patch_panel"] or shared,
            })
    rows.sort(key=lambda r: (r["switch"], int(r["port"]), r["through"] != "", r["device"]))
    seen = set()
    for row in rows:
        if row["cable"] in seen:
            raise RackError(f"{row['cable']!r} is listed twice")
        seen.add(row["cable"])
    return rows


# --------------------------------------------------------------------------
# PrometheusRule
# --------------------------------------------------------------------------

_SEEN_EXPR = (
    'label_replace(label_replace(label_replace('
    'max by (sw_name, sw_port, mac, name, ip, vlan) (unpoller_client_uptime_seconds{wired="true"} * 0 + 1), '
    '"switch", "$1", "sw_name", "(.+)"), "port", "$1", "sw_port", "(.+)"), "client", "$1", "name", "(.+)")'
)


def _q(value):
    return json.dumps(value, ensure_ascii=False)


def build_rule(model):
    rows = port_expectations(model)
    out = [
        "---",
        "# Generated by hack/rack-gen.py from rack.yaml. Do not edit: change rack.yaml and regenerate.",
        "# yaml-language-server: $schema=https://kubernetes-schemas.pages.dev/monitoring.coreos.com/prometheusrule_v1.json",
        "apiVersion: monitoring.coreos.com/v1",
        "kind: PrometheusRule",
        "metadata:",
        "  name: rack-rules",
        "  namespace: observability",
        "spec:",
        "  groups:",
        "    # What rack.yaml says should be on each switch port, as constant series.",
        "    - name: rack.expected",
        "      interval: 1m",
        "      rules:",
    ]
    for row in rows:
        out += ["        - record: rack_port_info", "          expr: vector(1)", "          labels:"]
        out += [f"            {key}: {_q(value)}" for key, value in row.items() if value != ""]
    for dev in model["devices"].values():
        if not dev["mac"] or dev["kind"] in UNIFI_KINDS or dev["kind"] == "node":
            continue
        if dev["in_rack"] is False:
            continue
        out += [
            "        - record: rack_device_info",
            "          expr: vector(1)",
            "          labels:",
            f"            device: {_q(dev['name'])}",
            f"            kind: {_q(dev['kind'])}",
            f"            mac: {_q(dev['mac'])}",
        ]
    out += [
        "    # What UniFi reports, reshaped to the same switch and port labels.",
        "    - name: rack.live",
        "      interval: 1m",
        "      rules:",
        "        - record: rack:port_client:info",
        "          expr: >-",
        "            max by (switch, port, mac, client, ip, vlan) (",
        f"            {_SEEN_EXPR})",
        "        - record: rack:port_link:bps",
        "          expr: >-",
        '            label_replace(label_replace(max by (name, port_num) (unpoller_device_port_port_speed_bps > 0),',
        '            "switch", "$1", "name", "(.+)"), "port", "$1", "port_num", "(.+)")',
        "        - record: rack:port_poe:watts",
        "          expr: >-",
        '            label_replace(label_replace(max by (name, port_num) (unpoller_device_port_poe_watts),',
        '            "switch", "$1", "name", "(.+)"), "port", "$1", "port_num", "(.+)")',
    ]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# Canvas helpers
# --------------------------------------------------------------------------

def _box(name, text, top, left, width, height, background, *, border=None,
         border_width=0, size=12, color=COLOR_TEXT, align="center", valign="middle"):
    """One canvas rectangle. Positions are percentages of the panel."""
    return {
        "type": "rectangle",
        "name": name,
        "config": {
            "text": {"mode": "fixed", "fixed": text},
            "color": {"fixed": color},
            "align": align,
            "valign": valign,
            "size": size,
        },
        "background": {"color": background},
        "border": {"color": border or {"fixed": "transparent"}, "width": border_width},
        "constraint": {"horizontal": "scale", "vertical": "scale"},
        "placement": {
            "top": round(top, 3),
            "left": round(left, 3),
            "bottom": round(100 - top - height, 3),
            "right": round(100 - left - width, 3),
        },
    }


def _canvas(panel_id, title, description, grid, elements, targets, defaults, overrides=None):
    return {
        "id": panel_id,
        "type": "canvas",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": grid,
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
        "options": {
            "inlineEditing": False,
            "showAdvancedTypes": False,
            "panZoom": False,
            "infinitePan": False,
            "root": {
                "type": "frame",
                "name": "root",
                "elements": elements,
                "background": {"color": {"fixed": "transparent"}},
                "border": {"color": {"fixed": "transparent"}},
                "constraint": {"horizontal": "left", "vertical": "top"},
                "placement": {"top": 0, "left": 0, "width": 100, "height": 100},
            },
        },
    }


def _target(ref, expr, legend=None, table=False):
    target = {"refId": ref, "expr": expr, "instant": True, "range": False, "datasource": DS}
    if table:
        target["format"] = "table"
    else:
        target["format"] = "time_series"
        target["legendFormat"] = legend
    return target


# --------------------------------------------------------------------------
# Rack elevation
# --------------------------------------------------------------------------

def _label(dev):
    return dev["name"] + (f" ×{dev['quantity']}" if dev["quantity"] else "")


def _state_color(dev):
    """Background colour: live state where there is something to poll."""
    if dev["kind"] == "shelf":
        return {"fixed": COLOR_SHELF}
    if dev["kind"] == "space":
        return {"fixed": COLOR_SPACE}
    if not (dev["kind"] in UNIFI_KINDS or dev["kind"] == "node" or dev["mac"]):
        return {"fixed": COLOR_PASSIVE}
    return {"field": dev["name"], "fixed": COLOR_DOWN}


def elevation_layout(model):
    """Work out what the rack drawing shows.

    Returns (mode, slots, rear, unplaced, children). mode is "scale" when
    every positioned item has a u and a height_u, otherwise "order".
    Anything not known to be outside the rack and without a position lands
    in unplaced, so a blank never fails the build. An ISP hand-off is only
    drawn once in_rack is true.
    """
    devices = [d for d in model["devices"].values() if d["in_rack"] is not False]
    slots, rear, unplaced, children = [], [], [], {}
    for dev in devices:
        if dev["shelf"] is not None:
            continue
        if dev["mount"] == "rear":
            rear.append(dev)
        elif dev["u"] is not None or dev["order"] is not None:
            slots.append(dev)
        elif dev["kind"] != "isp" or dev["in_rack"] is True:
            unplaced.append(dev)
    drawn_shelves = {d["name"] for d in slots}
    for dev in devices:
        if dev["shelf"] in drawn_shelves:
            children.setdefault(dev["shelf"], []).append(dev)
        elif dev["shelf"] is not None:
            unplaced.append(dev)
    to_scale = (
        bool(slots)
        and model["rack"]["height_u"] is not None
        and all(d["u"] is not None and d["height_u"] is not None for d in slots)
    )
    if to_scale:
        slots.sort(key=lambda d: -d["u"])
    else:
        slots.sort(key=lambda d: (d["order"] if d["order"] is not None else 10_000 - d["u"]))
    return ("scale" if to_scale else "order"), slots, rear, unplaced, children


def build_elevation(model, panel_id, grid):
    mode, slots, rear, unplaced, children = elevation_layout(model)
    rack = model["rack"]
    cols, row_units = 6, 1.9
    segments = []  # (kind, device or None, units, label)

    def shelf_units(dev):
        kids = len(children.get(dev["name"], []))
        return 1.0 + row_units * max(1, math.ceil(kids / cols))

    if mode == "scale":
        cursor = rack["height_u"]
        for dev in slots:
            top_u = dev["u"] + dev["height_u"] - 1
            if cursor > top_u:
                segments.append(("gap", None, float(cursor - top_u), ""))
            label = f"U{dev['u']}" if dev["height_u"] == 1 else f"U{top_u}-{dev['u']}"
            segments.append(("slot", dev, float(dev["height_u"]), label))
            cursor = dev["u"] - 1
        if cursor > 0:
            segments.append(("gap", None, float(cursor), ""))
    else:
        for dev in slots:
            if dev["kind"] == "shelf":
                units = shelf_units(dev)
            else:
                units = float(min(dev["height_u"] or 1, 3))
            label = f"U{dev['u']}" if dev["u"] is not None else f"#{dev['order']}"
            segments.append(("slot", dev, units, label))

    extras = []
    if rear:
        extras.append(("Back of rack", rear))
    if unplaced:
        extras.append(("Unplaced: no position recorded yet", unplaced))
    extra_units = sum(1.0 + row_units * math.ceil(len(devs) / cols) + 0.5 for _, devs in extras)

    header_units = 1.6
    total = header_units + sum(s[2] for s in segments) + extra_units + 0.4
    unit = 100.0 / total
    elements = []

    size = f"{rack['height_u']}U" if rack["height_u"] else "height not recorded"
    how = "to scale" if mode == "scale" else "top-to-bottom order, not to scale (U positions not recorded)"
    elements.append(_box(
        "rack title", f"{rack['name']} · {size} · {how}",
        0, 0, 100, header_units * unit * 0.9,
        {"fixed": "transparent"}, size=13, color=COLOR_MUTED, align="left",
    ))

    gutter, left, width = 9.0, 10.0, 89.0
    top = header_units * unit

    def child_grid(devs, top_pct, height_pct, left_pct, width_pct):
        rows = max(1, math.ceil(len(devs) / cols))
        cell_w = width_pct / cols
        cell_h = height_pct / rows
        for index, kid in enumerate(devs):
            row, col = divmod(index, cols)
            elements.append(_box(
                f"device {kid['name']}", _label(kid),
                top_pct + row * cell_h + cell_h * 0.08, left_pct + col * cell_w + cell_w * 0.03,
                cell_w * 0.94, cell_h * 0.84,
                _state_color(kid), size=10,
            ))

    for kind, dev, units, label in segments:
        height = units * unit
        if kind == "gap":
            elements.append(_box(
                f"gap {len(elements)}", "", top + height * 0.04, left, width, height * 0.92,
                {"fixed": COLOR_SPACE},
            ))
            top += height
            continue
        elements.append(_box(
            f"position {dev['name']}", label, top, 0, gutter, height,
            {"fixed": "transparent"}, size=10, color=COLOR_MUTED, align="right",
        ))
        kids = children.get(dev["name"], [])
        if dev["kind"] == "shelf":
            elements.append(_box(
                f"device {dev['name']}", "", top + height * 0.03, left, width, height * 0.94,
                _state_color(dev),
            ))
            head = min(unit, height * 0.4)
            caption = dev["name"] + (f": {dev['role']}" if dev["role"] else "")
            elements.append(_box(
                f"caption {dev['name']}", caption, top + height * 0.03, left + 1, width - 2, head,
                {"fixed": "transparent"}, size=10, color=COLOR_MUTED, align="left",
            ))
            if kids:
                child_grid(kids, top + head, height * 0.97 - head - height * 0.03, left + 1, width - 2)
        else:
            elements.append(_box(
                f"device {dev['name']}", _label(dev), top + height * 0.04, left, width, height * 0.92,
                _state_color(dev), size=12 if dev["kind"] != "space" else 10,
                color=COLOR_TEXT if dev["kind"] != "space" else COLOR_MUTED,
            ))
        top += height

    for caption, devs in extras:
        top += 0.5 * unit
        elements.append(_box(
            f"caption {caption}", caption, top, left, width, unit,
            {"fixed": "transparent"}, size=11, color=COLOR_MUTED, align="left",
        ))
        rows = math.ceil(len(devs) / cols)
        child_grid(devs, top + unit, row_units * rows * unit, left, width)
        top += (1.0 + row_units * rows) * unit

    targets = [
        _target("A", "max by (name) (unpoller_device_uptime_seconds > bool 0)", "{{name}}"),
        _target("B", 'max by (node) (kube_node_status_condition{condition="Ready", status="true"})', "{{node}}"),
        _target(
            "C",
            "max by (device) (rack_device_info * on (mac) group_left ()"
            " max by (mac) (unpoller_client_uptime_seconds > bool 0))",
            "{{device}}",
        ),
    ]
    defaults = {
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": [{"color": COLOR_DOWN, "value": None}, {"color": COLOR_UP, "value": 1}],
        },
    }
    description = (
        "Generated from rack.yaml. Green: UniFi sees the device (or the K3s node is Ready). "
        "Red: expected but not seen. Grey: nothing to poll (shelves, fans, power, patch panels)."
    )
    return _canvas(panel_id, "Rack elevation", description, grid, elements, targets, defaults)


# --------------------------------------------------------------------------
# Switch faceplates
# --------------------------------------------------------------------------

def faceplate_cells(ports):
    """Return (rows, columns, {port: (row, column)}) for a switch faceplate."""
    if ports >= 48:
        copper = 48
        cells = {p: ((p - 1) % 2, (p - 1) // 2) for p in range(1, copper + 1)}
        for i, p in enumerate(range(copper + 1, ports + 1)):
            cells[p] = (i % 2, copper // 2 + 0.5 + i // 2)
        return 2, copper // 2 + 0.5 + math.ceil((ports - copper) / 2), cells
    return 1, ports, {p: (0, p - 1) for p in range(1, ports + 1)}


def build_faceplate(dev, panel_id, grid):
    name, ports = dev["name"], dev["ports"]
    rows, columns, cells = faceplate_cells(ports)
    legend_h = 26.0 if rows == 1 else 22.0
    cell_w = 100.0 / columns
    cell_h = (100.0 - legend_h) / rows
    elements = []
    for port, (row, col) in cells.items():
        elements.append(_box(
            f"port {port}", str(port),
            row * cell_h + cell_h * 0.08, col * cell_w + cell_w * 0.08,
            cell_w * 0.84, cell_h * 0.84,
            {"field": f"p{port}", "fixed": COLOR_PORT_DOWN},
            border={"field": f"poe{port}", "fixed": "transparent"}, border_width=2, size=11,
        ))
    key = [
        ("down", COLOR_PORT_DOWN), ("10M", SPEED_STEPS[0]["color"]), ("100M", SPEED_STEPS[1]["color"]),
        ("1G", SPEED_STEPS[2]["color"]), ("10G", SPEED_STEPS[3]["color"]),
    ]
    key_w = min(9.0, 100.0 / (len(key) + 2))
    for index, (text, color) in enumerate(key):
        elements.append(_box(
            f"key {text}", text, 100 - legend_h * 0.8, index * (key_w + 1), key_w, legend_h * 0.6,
            {"fixed": color}, size=10,
        ))
    elements.append(_box(
        "key poe", "PoE", 100 - legend_h * 0.8, len(key) * (key_w + 1), key_w, legend_h * 0.6,
        {"fixed": COLOR_PORT_DOWN}, border={"fixed": COLOR_POE}, border_width=2, size=10,
    ))
    targets = [
        _target("A", f'max by (port_num) (unpoller_device_port_port_speed_bps{{name="{name}"}} > 0)', "p{{port_num}}"),
        _target("B", f'max by (port_num) (unpoller_device_port_poe_watts{{name="{name}"}} > 0)', "poe{{port_num}}"),
    ]
    defaults = {
        "color": {"mode": "thresholds"},
        "thresholds": {"mode": "absolute", "steps": SPEED_STEPS},
    }
    overrides = [{
        "matcher": {"id": "byRegexp", "options": "^poe\\d+$"},
        "properties": [{
            "id": "thresholds",
            "value": {"mode": "absolute", "steps": [{"color": COLOR_POE, "value": None}]},
        }],
    }]
    description = (
        "One cell per port, coloured by live link speed from UniFi. "
        "A white outline means the port is delivering PoE."
    )
    title = f"{name} ({dev['model']})" if dev["model"] else name
    return _canvas(panel_id, title, description, grid, elements, targets, defaults, overrides)


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

def _regex(names):
    return "|".join(names)


def _fill(expr, labels):
    """Give absent fact labels a visible placeholder so their columns always exist."""
    for label in labels:
        expr = f'label_replace({expr}, "{label}", "{UNSET}", "{label}", "^$")'
    return expr


_FACT_COLUMNS = ["patch_panel", "cable_label", "cable_color"]


def _organize(order, renames, extra_hidden=()):
    hidden = {"Time": True, "__name__": True, "Value #A": True, "cable": True}
    hidden.update({name: True for name in extra_hidden})
    return {
        "id": "organize",
        "options": {
            "excludeByName": hidden,
            "indexByName": {name: index for index, name in enumerate(order)},
            "renameByName": renames,
        },
    }


def _unset_override():
    return {
        "matcher": {"id": "byRegexp", "options": "^(Patch panel|Cable label|Colour)$"},
        "properties": [
            {"id": "mappings", "value": [{
                "type": "value",
                "options": {UNSET: {"color": "orange", "index": 0}},
            }]},
            {"id": "custom.cellOptions", "value": {"type": "color-text"}},
        ],
    }


def _table(panel_id, title, description, grid, targets, transformations, overrides, sort_by, no_value="-"):
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": grid,
        "targets": targets,
        "transformations": transformations,
        "fieldConfig": {
            "defaults": {"custom": {"align": "auto", "filterable": True}, "noValue": no_value},
            "overrides": overrides,
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "footer": {"show": False},
            "sortBy": [{"displayName": name, "desc": False} for name in sort_by],
        },
    }


def build_cable_table(panel_id, title, description, grid, switches):
    sel = f'switch=~"{_regex(switches)}"'
    info = f"rack_port_info{{{sel}}}"
    targets = [
        _target("A", _fill(info, _FACT_COLUMNS), table=True),
        _target(
            "B",
            f"max by (cable, client, ip, vlan) ({info} * on (switch, port, mac)"
            " group_left (client, ip, vlan) topk by (switch, port, mac) (1, rack:port_client:info))",
            table=True,
        ),
        _target("C", f"max by (cable) ({info} * on (switch, port) group_left () rack:port_link:bps)", table=True),
        _target("D", f"max by (cable) ({info} * on (switch, port) group_left () rack:port_poe:watts)", table=True),
    ]
    order = [
        "switch", "port", "device", "kind", "through", "check", "client", "ip", "vlan", "Value #C", "Value #D",
        "unifi_label", "cable_type", "patch_panel", "cable_label", "cable_color", "mac",
    ]
    renames = {
        "switch": "Switch", "port": "Port", "device": "Expected device", "kind": "Kind", "through": "Through",
        "check": "Check", "client": "Seen as", "ip": "IP", "vlan": "VLAN", "Value #C": "Link",
        "Value #D": "PoE", "unifi_label": "UniFi label", "cable_type": "Cable type",
        "patch_panel": "Patch panel", "cable_label": "Cable label", "cable_color": "Colour",
        "mac": "Expected MAC",
    }
    transformations = [
        {"id": "joinByField", "options": {"byField": "cable", "mode": "outer"}},
        _organize(order, renames, ["Time 1", "Time 2", "Time 3", "Time 4", "Value #B"]),
        {"id": "convertFieldType", "options": {"conversions": [
            {"targetField": "Port", "destinationType": "number"},
        ]}},
    ]
    overrides = [
        {"matcher": {"id": "byName", "options": "Link"}, "properties": [
            {"id": "unit", "value": "bps"},
            {"id": "noValue", "value": "down"},
        ]},
        {"matcher": {"id": "byName", "options": "PoE"}, "properties": [
            {"id": "unit", "value": "watt"},
            {"id": "decimals", "value": 1},
        ]},
        {"matcher": {"id": "byName", "options": "Port"}, "properties": [{"id": "custom.width", "value": 80}]},
        _unset_override(),
    ]
    return _table(panel_id, title, description, grid, targets, transformations, overrides, ["Switch", "Port"])


# Expected MAC cables whose device is seen, but on another switch port.
MOVED_EXPR = (
    '(rack_port_info{check=~"mac|mac-when-on"} unless on (switch, port, mac) rack:port_client:info)'
    ' * on (mac) group_left (seen_switch, seen_port)'
    ' label_replace(label_replace(topk by (mac) (1, max by (mac, switch, port) (rack:port_client:info)),'
    ' "seen_switch", "$1", "switch", "(.+)"), "seen_port", "$1", "port", "(.+)")'
)


def build_moved_table(panel_id, grid):
    missing = (
        '(rack_port_info{check="mac"} unless on (switch, port, mac) rack:port_client:info)'
        ' or (rack_port_info{check="link"} unless on (switch, port) rack:port_link:bps)'
        f" or ({MOVED_EXPR})"
    )
    targets = [
        _target("A", f"max by (cable, switch, port, device, check, mac) ({missing})", table=True),
        _target("B", f"max by (cable, seen_switch, seen_port) ({MOVED_EXPR})", table=True),
    ]
    order = ["switch", "port", "device", "check", "mac", "seen_switch", "seen_port"]
    renames = {
        "switch": "Switch", "port": "Port", "device": "Expected device", "check": "Check",
        "mac": "Expected MAC", "seen_switch": "Seen on switch", "seen_port": "Seen on port",
    }
    transformations = [
        {"id": "joinByField", "options": {"byField": "cable", "mode": "outer"}},
        _organize(order, renames, ["Time 1", "Time 2", "Value #B"]),
    ]
    overrides = [
        {"matcher": {"id": "byRegexp", "options": "^Seen on (switch|port)$"}, "properties": [
            {"id": "noValue", "value": "nowhere"},
        ]},
        {"matcher": {"id": "byName", "options": "Expected MAC"}, "properties": [
            {"id": "noValue", "value": "-"},
        ]},
    ]
    description = (
        "Cables where rack.yaml and the network disagree: the expected device is on another port, "
        "an always-on device is not seen at all, or a switch-to-switch or uplink port has no link. "
        "Devices marked always_on: false are only listed when seen on the wrong port. "
        "Empty means everything matches."
    )
    return _table(panel_id, "Moved or missing", description, grid, targets, transformations, overrides,
                  ["Switch", "Port"], no_value="Nothing moved or missing")


def build_unexpected_table(panel_id, grid, switches):
    sel = f'switch=~"{_regex(switches)}"'
    expr = (
        f"max by (switch, port, client, mac, ip, vlan) (rack:port_client:info{{{sel}}}"
        " unless on (switch, port, mac) rack_port_info)"
    )
    order = ["switch", "port", "client", "mac", "ip", "vlan"]
    renames = {"switch": "Switch", "port": "Port", "client": "Seen as", "mac": "MAC", "ip": "IP", "vlan": "VLAN"}
    description = (
        "Wired devices UniFi sees on a switch port that rack.yaml does not list there. "
        "Add them to rack.yaml, or find out what was plugged in."
    )
    return _table(panel_id, "Not in rack.yaml", description, grid, [_target("A", expr, table=True)],
                  [_organize(order, renames, ["Value"])], [], ["Switch", "Port"], no_value="Nothing unexpected")


# --------------------------------------------------------------------------
# PoE and text panels
# --------------------------------------------------------------------------

def build_poe_gauge(panel_id, grid):
    return {
        "id": panel_id,
        "type": "gauge",
        "title": "PoE budget used",
        "description": "PoE watts delivered across all ports, as a share of each switch's PoE budget.",
        "datasource": DS,
        "gridPos": grid,
        "targets": [_target(
            "A",
            "sum by (name) (unpoller_device_port_poe_watts)"
            " / on (name) max by (name) (unpoller_device_max_power_total > 0)",
            "{{name}}",
        )],
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit", "min": 0, "max": 1, "decimals": 0,
                "thresholds": {"mode": "absolute", "steps": [
                    {"color": "green", "value": None},
                    {"color": "yellow", "value": 0.7},
                    {"color": "red", "value": 0.9},
                ]},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
        },
    }


def build_poe_stat(panel_id, grid):
    return {
        "id": panel_id,
        "type": "stat",
        "title": "PoE watts",
        "description": "Watts delivered now, and the budget, per PoE switch.",
        "datasource": DS,
        "gridPos": grid,
        "targets": [
            _target("A", "sum by (name) (unpoller_device_port_poe_watts) > 0", "{{name}} used"),
            _target("B", "max by (name) (unpoller_device_max_power_total > 0)", "{{name}} budget"),
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "watt", "decimals": 0, "color": {"mode": "fixed", "fixedColor": "text"},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "none", "graphMode": "none", "justifyMode": "auto",
            "textMode": "value_and_name", "orientation": "horizontal",
        },
    }


def build_poe_ports(panel_id, grid):
    return {
        "id": panel_id,
        "type": "bargauge",
        "title": "PoE by port",
        "description": "Ports delivering PoE right now, by switch port and UniFi port label.",
        "datasource": DS,
        "gridPos": grid,
        "targets": [_target(
            "A",
            "sort_desc(max by (name, port_num, port_name) (unpoller_device_port_poe_watts > 0))",
            "{{name}} {{port_num}} · {{port_name}}",
        )],
        "fieldConfig": {
            "defaults": {
                "unit": "watt", "decimals": 1, "min": 0, "max": 30,
                "color": {"mode": "fixed", "fixedColor": "#3274d9"},
            },
            "overrides": [],
        },
        "options": {
            "displayMode": "basic", "orientation": "horizontal", "showUnfilled": True,
            "valueMode": "color", "namePlacement": "left",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        },
    }


def _cell(value):
    text = ("" if value is None else str(value)).replace("|", "\\|").replace("\n", " ")
    return text if text else " "


def _md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    out += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def _position(dev):
    if dev["shelf"] is not None:
        return f"on {dev['shelf']}"
    if dev["mount"] == "rear":
        return "back of rack"
    if dev["order"] is not None:
        return f"#{dev['order']}"
    return ""


_BLANK = "**?**"
_DEVICE_HEADERS = ["Kind", "MAC", "IP", "Rated", "Power source", "Outlet", "In rack", "Notes"]


def _device_cells(dev):
    """The cells both inventory tables end with, in _DEVICE_HEADERS order."""
    return [
        dev["kind"],
        dev["mac"],
        dev["ip"],
        "" if dev["watts"] is None else f"{dev['watts']} W",
        (dev["power_source"] or _BLANK) if dev["has_power"] else "",
        (dev["power_outlet"] or _BLANK) if dev["has_power"] else "",
        {True: "yes", False: "no", None: _BLANK}[dev["in_rack"]],
        dev["notes"],
    ]


def _rack_items(model):
    """Everything on the rack drawing, in drawing order."""
    _, slots, rear, unplaced, children = elevation_layout(model)
    ordered = []
    for dev in slots:
        ordered.append(dev)
        ordered += children.get(dev["name"], [])
    return ordered + rear + unplaced


def inventory_markdown(model):
    """The rack's own contents as a markdown table, in drawing order."""
    rows = []
    for dev in _rack_items(model):
        placed = dev["shelf"] is not None or dev["mount"] == "rear"
        rows.append([
            _position(dev),
            _label(dev),
            dev["model"],
            dev["role"],
            "" if placed else (f"U{dev['u']}" if dev["u"] is not None else _BLANK),
            "" if placed else (dev["height_u"] if dev["height_u"] is not None else _BLANK),
            *_device_cells(dev),
        ])
    headers = ["Position", "Item", "Model", "Role", "U", "Height (U)", *_DEVICE_HEADERS]
    return (
        f"**{model['rack']['name']}**: {model['rack']['model'] or 'model not recorded'}. "
        "Position counts from the top of the rack; U counts from the bottom. MAC and IP are the "
        "addresses recorded in `rack.yaml`. "
        "**?** marks a fact still to be recorded in `rack.yaml`.\n\n" + _md_table(headers, rows)
    )


def outside_markdown(model):
    """The listed devices that are not on the rack drawing, or "" when there are none."""
    drawn = {dev["name"] for dev in _rack_items(model)}
    rows = [
        [_label(dev), dev["model"], dev["role"], *_device_cells(dev)]
        for dev in model["devices"].values() if dev["name"] not in drawn
    ]
    if not rows:
        return ""
    return (
        "Devices listed in `rack.yaml` that are outside the rack, and ISP hand-offs not yet confirmed "
        "to be in it. MAC and IP are the addresses recorded in `rack.yaml`. "
        "**?** marks a fact still to be recorded in `rack.yaml`.\n\n"
        + _md_table(["Item", "Model", "Role", *_DEVICE_HEADERS], rows)
    )


def notes_markdown(model):
    parts = []
    if model["rack"]["notes"]:
        parts.append("#### Rack notes\n\n" + "\n".join(f"- {n}" for n in model["rack"]["notes"]))
    if model["networks"]:
        rows = [
            [n.get("name"), n.get("vlan") or "**?**", n.get("cidr") or "**?**", n.get("gateway") or "**?**"]
            for n in model["networks"]
        ]
        parts.append("#### Networks\n\n" + _md_table(["Network", "VLAN", "Range", "Gateway"], rows))
    if model["discrepancies"]:
        parts.append(
            "#### Where the documents and the network disagree\n\n"
            + "\n".join(f"- {n}" for n in model["discrepancies"])
        )
    return "\n\n".join(parts)


def _text_panel(panel_id, title, grid, content):
    return {
        "id": panel_id,
        "type": "text",
        "title": title,
        "gridPos": grid,
        "options": {"mode": "markdown", "content": content},
    }


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

def build_dashboard(model):
    devices = model["devices"]
    with_ports = [d for d in devices.values() if d["ports"]]
    rack_switches = [d for d in with_ports if d["in_rack"] is not False]
    room_switches = [d for d in with_ports if d["in_rack"] is False]
    rack_names = [d["name"] for d in rack_switches]
    room_names = [d["name"] for d in room_switches]

    panels = []
    ids = iter(range(1, 1000))
    left_w, right_x, right_w = 8, 8, 16
    y = 0
    big = sorted(rack_switches, key=lambda d: -d["ports"])
    for dev in big:
        if dev["ports"] >= 48:
            panels.append(build_faceplate(dev, next(ids), {"h": 6, "w": right_w, "x": right_x, "y": y}))
            y += 6
    small = [d for d in big if d["ports"] < 48]
    for index, dev in enumerate(small):
        width = right_w // max(1, len(small))
        panels.append(build_faceplate(dev, next(ids), {"h": 4, "w": width, "x": right_x + index * width, "y": y}))
    if small:
        y += 4
    panels.append(build_poe_gauge(next(ids), {"h": 7, "w": 5, "x": right_x, "y": y}))
    panels.append(build_poe_stat(next(ids), {"h": 7, "w": 4, "x": right_x + 5, "y": y}))
    panels.append(build_poe_ports(next(ids), {"h": 7, "w": 7, "x": right_x + 9, "y": y}))
    y += 7
    panels.append(build_moved_table(next(ids), {"h": 7, "w": right_w, "x": right_x, "y": y}))
    y += 7
    panels.append(build_unexpected_table(
        next(ids), {"h": 7, "w": right_w, "x": right_x, "y": y}, rack_names + room_names,
    ))
    y += 7
    panels.insert(0, build_elevation(model, next(ids), {"h": y, "w": left_w, "x": 0, "y": 0}))

    panels.append(build_cable_table(
        next(ids), "Cables",
        "Every cable on the rack's switches: what rack.yaml expects on each port next to what UniFi sees "
        "there now. 'Check' is how a cable is verified: mac (the device must be seen on the port), "
        "mac-when-on (same, but the device may sleep), link (UniFi gear or a device with no MAC, so only "
        "link state is checked), none (such a device reached through another one, so nothing is checked). "
        "Orange 'not set' cells are facts to record in rack.yaml. VLAN is the "
        "VLAN of the device seen on the port.",
        {"h": 16, "w": 24, "x": 0, "y": y}, rack_names,
    ))
    y += 16
    if room_names:
        panels.append(build_cable_table(
            next(ids), "Room switches",
            "The small switches fed from the rack, with the same expected-against-seen columns.",
            {"h": 9, "w": 24, "x": 0, "y": y}, room_names,
        ))
        y += 9
    panels.append(_text_panel(next(ids), "Rack inventory", {"h": 22, "w": 24, "x": 0, "y": y},
                              inventory_markdown(model)))
    y += 22
    outside = outside_markdown(model)
    if outside:
        panels.append(_text_panel(next(ids), "Not in the rack", {"h": 14, "w": 24, "x": 0, "y": y}, outside))
        y += 14
    panels.append(_text_panel(next(ids), "Notes, networks and open questions",
                              {"h": 16, "w": 24, "x": 0, "y": y}, notes_markdown(model)))

    return {
        "uid": "server-rack",
        "title": "Server Rack",
        "description": "Generated by hack/rack-gen.py from rack.yaml. Edit rack.yaml, not this dashboard.",
        "tags": ["network", "unifi", "rack"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "editable": False,
        "refresh": "5m",
        "time": {"from": "now-1h", "to": "now"},
        "links": [],
        "panels": panels,
    }


def build_configmap(model):
    body = json.dumps(build_dashboard(model), indent=2, ensure_ascii=False)
    out = [
        "---",
        "# Generated by hack/rack-gen.py from rack.yaml. Do not edit: change rack.yaml and regenerate.",
        "# yamllint disable rule:line-length",
        "apiVersion: v1",
        "kind: ConfigMap",
        "metadata:",
        "  name: server-rack-dashboard",
        "  namespace: observability",
        "  labels:",
        '    grafana_dashboard: "1"',
        "  annotations:",
        '    grafana_folder: "Network"',
        "    kustomize.toolkit.fluxcd.io/substitute: disabled",
        "data:",
        "  server-rack.json: |",
    ]
    out += ["    " + line for line in body.splitlines()]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def generate(text):
    model = load_model(text)
    return {RULE_OUT: build_rule(model), DASH_OUT: build_configmap(model)}


def main(argv):
    if argv not in ([], ["--check"]):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        outputs = generate(FACTS.read_text(encoding="utf-8"))
    except RackError as exc:
        print(f"rack.yaml: {exc}", file=sys.stderr)
        return 1
    if argv:
        stale = [p for p, body in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != body]
        for path in stale:
            print(f"stale: {path.relative_to(REPO)}", file=sys.stderr)
        if stale:
            print("Run: python3 -I hack/rack-gen.py   and commit the result.", file=sys.stderr)
            return 1
        return 0
    for path, body in outputs.items():
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
