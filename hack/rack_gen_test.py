"""Tests for hack/rack-gen.py. Run: python3 -I hack/rack_gen_test.py"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # rack-gen.py is a script; leave no __pycache__
_spec = importlib.util.spec_from_file_location("rack_gen", HERE / "rack-gen.py")
rack_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rack_gen)

SAMPLE = """
rack:
  name: test-rack
  height_u: 10
devices:
  - name: Core Switch
    kind: switch
    mac: "AA:bb:cc:00:00:01"
    ports: 8
    in_rack: true
    u: 9
    height_u: 1
  - name: Shelf A
    kind: shelf
    in_rack: true
    u: 5
    height_u: 2
  - name: "Bridge #1"   # quoted because of the hash
    kind: bridge
    mac: "aa:bb:cc:00:00:02"
    in_rack: true
    shelf: Shelf A
  - name: Host
    kind: other
    mac: "aa:bb:cc:00:00:03"
    in_rack: true
  - name: VM
    kind: node
    mac: "aa:bb:cc:00:00:04"
    in_rack: false
  - name: Laptop
    kind: client
    mac: "aa:bb:cc:00:00:05"
    in_rack: false
    always_on: false
  - name: Edge Switch
    kind: switch
    ports: 5
    in_rack: false
cables:
  - a: { device: Core Switch, port: 1 }
    b: { device: "Bridge #1" }
    label: B-1
    color:
  - a: { device: Core Switch, port: 2 }
    b: { device: Host }
  - a: { device: Core Switch, port: 2 }
    b: { device: VM }
    through: Host
  - a: { device: Core Switch, port: 3 }
    b: { device: Laptop }
  - a: { device: Core Switch, port: 8 }
    b: { device: Edge Switch, port: 1 }
"""


def model(text=SAMPLE):
    return rack_gen.load_model(text)


def drawn(text=SAMPLE):
    """The names of the elements on the rack elevation."""
    panel = rack_gen.build_elevation(model(text), 1, {"h": 1, "w": 1, "x": 0, "y": 0})
    return [element["name"] for element in panel["options"]["root"]["elements"]]


def inventory(text=SAMPLE):
    """The Rack inventory table as {item: {column: cell}}."""
    table = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in rack_gen.inventory_markdown(model(text)).splitlines()
        if line.startswith("|")
    ]
    return {row[1]: dict(zip(table[0], row)) for row in table[2:]}


class ModelTest(unittest.TestCase):
    def test_mac_is_lowercased(self):
        self.assertEqual(model()["devices"]["Core Switch"]["mac"], "aa:bb:cc:00:00:01")

    def test_every_yaml_spelling_of_false_is_read_as_false(self):
        for word in ("False", "no", "off"):
            text = SAMPLE.replace("always_on: false", f"always_on: {word}")
            rows = {r["cable"]: r for r in rack_gen.port_expectations(model(text))}
            self.assertEqual(rows["Core Switch 3 > Laptop"]["check"], "mac-when-on", word)

    def test_broken_yaml_is_reported_with_a_line_number(self):
        with self.assertRaisesRegex(rack_gen.RackError, "line 1"):
            model("rack: { name: test-rack\n")

    def test_expectations_cover_both_ends_and_pick_the_check(self):
        rows = {r["cable"]: r for r in rack_gen.port_expectations(model())}
        self.assertEqual(rows["Core Switch 1 > Bridge #1"]["check"], "mac")
        self.assertEqual(rows["Core Switch 1 > Bridge #1"]["cable_label"], "B-1")
        self.assertEqual(rows["Core Switch 2 > VM"]["through"], "Host")
        self.assertEqual(rows["Core Switch 2 > VM"]["patch_panel"], "shared")
        self.assertEqual(rows["Core Switch 3 > Laptop"]["check"], "mac-when-on")
        self.assertEqual(rows["Core Switch 8 > Edge Switch"]["check"], "link")
        self.assertEqual(rows["Edge Switch 1 > Core Switch"]["device"], "Core Switch port 8")
        self.assertEqual(rows["Edge Switch 1 > Core Switch"]["mac"], "")

    def test_through_cable_to_a_device_without_a_mac_is_still_listed(self):
        text = SAMPLE.replace('    mac: "aa:bb:cc:00:00:04"\n', "")
        rows = {r["cable"]: r for r in rack_gen.port_expectations(model(text))}
        self.assertEqual(rows["Core Switch 2 > VM"]["check"], "none")
        self.assertEqual(rows["Core Switch 2 > VM"]["mac"], "")

    def test_quoted_free_text_is_kept_as_typed(self):
        text = SAMPLE.replace("    label: B-1\n", '    label: "012"\n    patch_panel: "1:12"\n')
        rows = {r["cable"]: r for r in rack_gen.port_expectations(model(text))}
        self.assertEqual(rows["Core Switch 1 > Bridge #1"]["cable_label"], "012")
        self.assertEqual(rows["Core Switch 1 > Bridge #1"]["patch_panel"], "1:12")

    def assert_rejected(self, old, new, message):
        self.assertIn(old, SAMPLE)
        with self.assertRaisesRegex(rack_gen.RackError, message):
            model(SAMPLE.replace(old, new))

    def test_unquoted_free_text_that_yaml_retypes_is_rejected(self):
        self.assert_rejected(
            "    label: B-1\n", "    patch_panel: 1:12\n", "patch_panel was read by YAML as 72.*double quotes"
        )
        for old, new in (
            ("    label: B-1\n", "    label: 012\n"),
            ("    color:\n", "    color: on\n"),
            ("    kind: other\n", "    kind: other\n    model: yes\n"),
            ("    kind: other\n", "    kind: other\n    power: { outlet: 4 }\n"),
            ("  height_u: 10\n", "  height_u: 10\n  notes:\n    - 2:07\n"),
            ("devices:\n", "discrepancies:\n  - 12\ndevices:\n"),
            ("devices:\n", "networks:\n  - name: on\ndevices:\n"),
        ):
            with self.subTest(new=new):
                self.assert_rejected(old, new, "double quotes")

    def test_mistakes_are_rejected(self):
        self.assert_rejected("b: { device: Host }", "b: { device: Nobody }", "not a listed device")
        self.assert_rejected("port: 8 }", "port: 9 }", "has 8 ports")
        self.assert_rejected("u: 5", "u: 9", "overlap")
        self.assert_rejected("u: 9", "u: 11", "above the 10U rack")
        self.assert_rejected('"aa:bb:cc:00:00:03"', '"aa:bb:cc:00:00:02"', "is on both")
        self.assert_rejected("    through: Host\n", "", "two cables")
        self.assert_rejected("kind: bridge", "kind: toaster", "kind must be one of")
        self.assert_rejected("always_on: false", "always_on: sometimes", "always_on must be true, false or blank")
        self.assert_rejected("in_rack: true\n    u: 9", "in_rack: 0\n    u: 9", "in_rack must be true, false or blank")
        self.assert_rejected("    kind: other\n", "    kind: other\n    mount: Rear\n", "mount must be rear or blank")
        self.assert_rejected("    kind: other\n", "    kind: other\n    watts: lots\n", "watts must be a number")
        self.assert_rejected("  height_u: 10\n", "  height_u: 10\n  notes: one line\n", "rack.notes must be a list")
        self.assert_rejected("devices:\n", "discrepancies: one line\ndevices:\n", "discrepancies must be a list")
        self.assert_rejected("devices:\n", "networks:\n  - Main\ndevices:\n", "bad network entry")

    def test_misspelt_keys_are_rejected(self):
        for old, new in (
            ("    height_u: 2\n", "    heigth_u: 2\n"),
            ("    label: B-1\n", "    lable: B-1\n"),
            ("  height_u: 10\n", "  heigth_u: 10\n"),
            ("device: Core Switch, port: 1 }", "device: Core Switch, prot: 1 }"),
            ("    kind: other\n", "    kind: other\n    power: { sorce: UPS }\n"),
            ("devices:\n", "networks:\n  - nmae: Main\ndevices:\n"),
            ("cables:\n", "cabels:\n"),
        ):
            with self.subTest(new=new):
                self.assert_rejected(old, new, "unknown key")


class LayoutTest(unittest.TestCase):
    def test_device_without_a_position_is_unplaced_not_an_error(self):
        mode, slots, _, unplaced, children = rack_gen.elevation_layout(model())
        self.assertEqual(mode, "scale")
        self.assertEqual([d["name"] for d in slots], ["Core Switch", "Shelf A"])
        self.assertEqual([d["name"] for d in unplaced], ["Host"])
        self.assertEqual([d["name"] for d in children["Shelf A"]], ["Bridge #1"])

    def test_missing_u_falls_back_to_order(self):
        text = SAMPLE.replace("    u: 9\n", "    order: 1\n").replace("    u: 5\n", "    order: 2\n")
        mode, slots, _, _, _ = rack_gen.elevation_layout(model(text))
        self.assertEqual(mode, "order")
        self.assertEqual([d["name"] for d in slots], ["Core Switch", "Shelf A"])

    def test_every_rack_device_is_drawn_once(self):
        panel = rack_gen.build_elevation(model(), 1, {"h": 1, "w": 1, "x": 0, "y": 0})
        names = [e["name"] for e in panel["options"]["root"]["elements"]]
        for device in ("Core Switch", "Shelf A", "Bridge #1", "Host"):
            self.assertEqual(names.count(f"device {device}"), 1)
        self.assertNotIn("device VM", names)
        for element in panel["options"]["root"]["elements"]:
            for edge in element["placement"].values():
                self.assertTrue(-0.01 <= edge <= 100.01, element)

    def test_isp_is_drawn_once_it_is_confirmed_in_the_rack(self):
        for in_rack, expected in (("true", ["Host", "Fibre"]), ("", ["Host"])):
            text = SAMPLE.replace("cables:\n", f"  - name: Fibre\n    kind: isp\n    in_rack: {in_rack}\ncables:\n")
            _, _, _, unplaced, _ = rack_gen.elevation_layout(model(text))
            self.assertEqual([d["name"] for d in unplaced], expected, in_rack)

    def test_device_marked_outside_the_rack_is_not_on_its_shelf(self):
        text = SAMPLE.replace("in_rack: true\n    shelf: Shelf A", "in_rack: false\n    shelf: Shelf A")
        self.assertNotIn("device Bridge #1", drawn(text))
        self.assertNotIn("Bridge #1", inventory(text))

    def test_device_on_a_shelf_with_no_position_is_still_shown(self):
        text = SAMPLE.replace("    u: 5\n", "")
        self.assertEqual(drawn(text).count("device Bridge #1"), 1)
        self.assertEqual(inventory(text)["Bridge #1"]["Position"], "on Shelf A")

    def test_inventory_position_never_holds_a_rack_unit(self):
        row = inventory()["Core Switch"]
        self.assertEqual((row["Position"], row["U"]), ("", "U9"))
        text = SAMPLE.replace("    u: 9\n", "    order: 1\n").replace("    u: 5\n", "    order: 2\n")
        self.assertEqual(inventory(text)["Core Switch"]["Position"], "#1")

    def test_faceplate_has_one_cell_per_port(self):
        for ports in (5, 6, 8, 11, 52):
            _, _, cells = rack_gen.faceplate_cells(ports)
            self.assertEqual(sorted(cells), list(range(1, ports + 1)))
            self.assertEqual(len(set(cells.values())), ports)


class OutputTest(unittest.TestCase):
    def test_outputs_are_deterministic_and_well_formed(self):
        first, second = rack_gen.generate(SAMPLE), rack_gen.generate(SAMPLE)
        self.assertEqual(first, second)
        configmap = yaml.safe_load(first[rack_gen.DASH_OUT])
        self.assertEqual(configmap["kind"], "ConfigMap")
        self.assertEqual(configmap["metadata"]["labels"], {"grafana_dashboard": "1"})
        self.assertEqual(
            configmap["metadata"]["annotations"],
            {"grafana_folder": "Network", "kustomize.toolkit.fluxcd.io/substitute": "disabled"},
        )
        dashboard = json.loads(configmap["data"]["server-rack.json"])
        self.assertEqual(dashboard["uid"], "server-rack")
        ids = [p["id"] for p in dashboard["panels"]]
        self.assertEqual(len(ids), len(set(ids)))
        rule = yaml.safe_load(first[rack_gen.RULE_OUT])
        self.assertEqual(rule["kind"], "PrometheusRule")
        groups = {group["name"]: group["rules"] for group in rule["spec"]["groups"]}
        self.assertEqual(
            sorted(r["labels"]["cable"] for r in groups["rack.expected"] if r["record"] == "rack_port_info"),
            sorted(r["cable"] for r in rack_gen.port_expectations(model())),
        )
        self.assertEqual([r for rules in groups.values() for r in rules if "alert" in r], [])

    def test_committed_files_match_rack_yaml(self):
        outputs = rack_gen.generate(rack_gen.FACTS.read_text(encoding="utf-8"))
        for path, body in outputs.items():
            self.assertEqual(path.read_text(encoding="utf-8"), body, f"{path.name} is stale")


if __name__ == "__main__":
    sys.exit(unittest.main())
