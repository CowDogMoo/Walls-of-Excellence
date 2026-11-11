# Server rack dashboard

The **Server Rack** dashboard (Grafana, folder _Network_) shows what is in the
rack, what is plugged into every switch port, and where the cabling no longer
matches what is written down.

Everything hand-entered lives in one file, [`rack.yaml`](rack.yaml). The other
two YAML files in this directory are generated from it and must not be edited:

- `rack.yaml`: the facts (rack, devices, cables). Edit this.
- `rack-dashboard.yaml`: generated. The dashboard ConfigMap Grafana loads.
- `rack-prometheusrule.yaml`: generated. The expected cables as Prometheus
  series.

## Changing something

1. Edit `rack.yaml`.
2. Regenerate: `python3 -I hack/rack-gen.py`
3. Commit all three files. Flux deploys them with the `grafana` app.

The generator needs PyYAML (`python3 -m pip install pyyaml`).

A pre-commit hook (`rack-gen`) fails the commit if the generated files are
stale. It installs its own PyYAML, so it does not depend on yours. The
generator also rejects mistakes it can see: a cable to a device that is not
listed, a port number the switch does not have, two devices in the same rack
unit, a MAC address on two devices, a misspelt key, a value of the wrong
kind.

Put free-text values in double quotes when they could be read as something
else. YAML turns an unquoted `1:12`, `012`, `4`, `on` or `yes` into a number
or true/false, so write `patch_panel: "1:12"`, `label: "012"` and
`outlet: "4"`. The generator stops with an error naming the field when one is
left unquoted.

The generator has its own tests: `python3 -I hack/rack_gen_test.py`.

Do not put passwords, keys or other secrets in `rack.yaml`. This repository is
public.

## What to fill in at the rack

`rack.yaml` is pre-filled from UniFi, the cluster and the two home network
documents. A blank value is a fact nobody has recorded yet. On the dashboard
these show as **?** in _Rack inventory_ and as orange `not set` in _Cables_.

Devices (`devices:`):

- **`u`**: the lowest rack unit each item occupies, counting U1 at the bottom.
  None are recorded. Until every positioned item has both `u` and `height_u`,
  the rack is drawn in top-to-bottom order and not to scale. Once they all do,
  it is drawn to scale with empty units shown.
- **`height_u`**: missing for the front power strip, the six shelves and the
  TRO.Y.
- **`power.source` and `power.outlet`**: which strip or UPS feeds each device
  and which outlet. Only the PoE-powered nodes are filled in. k8s7 draws no
  PoE, so record what powers it.
- **`in_rack`**: blank for Hue Bridge #2 and #3, the Lutron shade buttons and
  the two ISP hand-offs. Set `true` or `false`.
- **Patch panel 2**: its model is assumed to match patch panel 1.
- **White box** on shelf 2: say what it is.
- **Basement office switch**: the unmanaged switch assumed to sit behind
  US XG 6 PoE port 4. Record its model and location, or correct the cabling.
- **Google Fiber and CenturyLink**: what the two WAN ports plug into.
- **serpent**: which Mac hosts it.
- Anything in the rack that is not listed yet. A device with no position goes
  in the drawing's _Unplaced_ area; it never breaks the build.

Cables (`cables:`):

- **`patch_panel`**: the panel and port each run passes through.
- **`label`** and **`color`**: if the cables are labelled or colour-coded.

## What the dashboard shows

- **Rack elevation**: positions from `rack.yaml`; green or red from UniFi and
  K3s node state.
- **Switch faceplates**: live link speed per port, with a white outline where
  the port delivers PoE.
- **PoE budget and ports**: live PoE watts against each switch's budget.
- **Moved or missing**: cables where the expected device is elsewhere or
  absent, or the link is down.
- **Not in rack.yaml**: wired devices seen on a port that `rack.yaml` does not
  list.
- **Cables**: the expected device and cable facts per port, next to the device
  seen there now.
- **Room switches**: the same, for the small switches fed from the rack.
- **Rack inventory**: every rack item with model, role, size, rated watts and
  power feed.
- **Notes**: rack notes, networks, and where the documents and the network
  disagree.

Link state, speed, PoE draw and the device on each port refresh from unpoller.
Positions, power, patch panel and cable details change only when `rack.yaml`
does.

## Known mismatches left as they are

Two port labels in UniFi are swapped on the 48-port switch: port 26 is
labelled `k8s6` but carries k8s5, and port 43 is labelled `k8s5` but carries
k8s6. `rack.yaml` records what is really connected, with the UniFi label in
`unifi_label`, so the dashboard shows both. The labels have not been changed
in UniFi.

The other differences between the documents and the live network are listed
under `discrepancies:` in `rack.yaml` and shown on the dashboard.

## Not covered yet

- UPS load, runtime and battery: the UPS has a network card but nothing
  collects from it.
- NAS health: there is no exporter for it, only an NFS port probe.
- unpoller does not export a port's configured VLAN, so the VLAN column is
  the VLAN of the device seen on the port.
