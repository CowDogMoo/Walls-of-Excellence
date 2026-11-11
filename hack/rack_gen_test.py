"""Tests for hack/rack-gen.py. Run: python3 -I hack/rack_gen_test.py"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

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


class ParserTest(unittest.TestCase):
    def test_scalars_comments_and_flow_maps(self):
        data = rack_gen.parse_yaml(SAMPLE)
        self.assertEqual(data["rack"], {"name": "test-rack", "height_u": 10})
        self.assertEqual(data["devices"][2]["name"], "Bridge #1")
        self.assertIs(data["devices"][4]["in_rack"], False)
        self.assertEqual(data["cables"][0]["a"], {"device": "Core Switch", "port": 1})
        self.assertIsNone(data["cables"][0]["color"])

    def test_strings_that_look_like_other_things(self):
        data = rack_gen.parse_yaml("a: 192.168.10.1\nb: it's fine\nc: \"x: y # z\"\nd: 1.5\ne:\n")
        self.assertEqual(data, {"a": "192.168.10.1", "b": "it's fine", "c": "x: y # z", "d": 1.5, "e": None})

    def test_nested_lists_and_maps(self):
        data = rack_gen.parse_yaml("top:\n  notes:\n    - one\n    - \"two: 2\"\n  power:\n    source:\n    outlet: 4\n")
        self.assertEqual(data, {"top": {"notes": ["one", "two: 2"], "power": {"source": None, "outlet": 4}}})

    def test_unsupported_yaml_is_rejected_with_a_line_number(self):
        with self.assertRaisesRegex(rack_gen.RackError, "line 2"):
            rack_gen.parse_yaml("a: 1\nb: |\n  text\n")
        with self.assertRaisesRegex(rack_gen.RackError, "line 1"):
            rack_gen.parse_yaml("a: { b: 1\n")


class ModelTest(unittest.TestCase):
    def test_mac_is_lowercased(self):
        self.assertEqual(model()["devices"]["Core Switch"]["mac"], "aa:bb:cc:00:00:01")

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

    def assert_rejected(self, old, new, message):
        self.assertIn(old, SAMPLE)
        with self.assertRaisesRegex(rack_gen.RackError, message):
            model(SAMPLE.replace(old, new))

    def test_mistakes_are_rejected(self):
        self.assert_rejected("b: { device: Host }", "b: { device: Nobody }", "not a listed device")
        self.assert_rejected("port: 8 }", "port: 9 }", "has 8 ports")
        self.assert_rejected("u: 5", "u: 9", "overlap")
        self.assert_rejected("u: 9", "u: 11", "above the 10U rack")
        self.assert_rejected('"aa:bb:cc:00:00:03"', '"aa:bb:cc:00:00:02"', "is on both")
        self.assert_rejected("    through: Host\n", "", "two cables")
        self.assert_rejected("kind: bridge", "kind: toaster", "kind must be one of")


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

    def test_faceplate_has_one_cell_per_port(self):
        for ports in (5, 6, 8, 11, 52):
            _, _, cells = rack_gen.faceplate_cells(ports)
            self.assertEqual(sorted(cells), list(range(1, ports + 1)))
            self.assertEqual(len(set(cells.values())), ports)


class OutputTest(unittest.TestCase):
    def test_outputs_are_deterministic_and_well_formed(self):
        first, second = rack_gen.generate(SAMPLE), rack_gen.generate(SAMPLE)
        self.assertEqual(first, second)
        configmap = first[rack_gen.DASH_OUT]
        body = configmap.split("  server-rack.json: |\n", 1)[1]
        dashboard = json.loads("\n".join(line[4:] for line in body.splitlines()))
        self.assertEqual(dashboard["uid"], "server-rack")
        ids = [p["id"] for p in dashboard["panels"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('grafana_dashboard: "1"', configmap)
        self.assertIn('grafana_folder: "Network"', configmap)
        rule = first[rack_gen.RULE_OUT]
        self.assertEqual(rule.count("- record: rack_port_info"), 6)
        self.assertIn("- alert: RackCableMoved", rule)

    def test_committed_files_match_rack_yaml(self):
        outputs = rack_gen.generate(rack_gen.FACTS.read_text(encoding="utf-8"))
        for path, body in outputs.items():
            self.assertEqual(path.read_text(encoding="utf-8"), body, f"{path.name} is stale")


if __name__ == "__main__":
    sys.exit(unittest.main())
