"""Synthetic contract tests only; no ROS, simulator, GPU, or production writes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "static_latched_preflight", Path(__file__).with_name("static_latched_preflight.py"))
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def layout():
    return dict(width=p.EXPECTED_POINTS, height=1, point_step=32, row_step=p.EXPECTED_BYTES,
                is_dense=True, is_bigendian=False,
                fields=[dict(name=n, offset=o, datatype=7, count=1)
                        for n, o in (("x", 0), ("y", 4), ("z", 8), ("intensity", 16))])


def baseline(stamp):
    return dict(publications=1, points=p.EXPECTED_POINTS, bytes=p.EXPECTED_BYTES,
                stamp_ns=stamp, timers_created=0, poll_callbacks=0)


def cloud(stamp):
    return dict(p.EXPECTED_GEOMETRY, stamp_ns=stamp, elapsed_s=1.0)


def log_text(stamp):
    fields = " ".join(f"{key}={value}" for key, value in baseline(stamp).items())
    return (
        "[INFO] [100.000000000] [sim]: [STATIC_PC_DURABLE_SETTINGS] enabled=1 actual_qos=1 "
        "reliability=reliable durability=transient_local history=keep_last depth=1 "
        "intra_process=disabled publication_schedule=latched_once other_qos_unchanged=1\n"
        "[INFO] [100.000000000] [sim]: [STATIC_PC_POLL_SETTINGS] poll_ms=0 bootstrap_once=1 complete_geometry=1 qos_unchanged=0\n"
        "[INFO] [100.000000000] [sim]: [STATIC_PC_LATCHED_SERIALIZATION] point_step=32 tail_zeroed_bytes=12 declared_fields_and_homogeneous_bytes_unchanged=1\n"
        f"[INFO] [100.000000000] [sim]: [STATIC_PC_LATCHED_PUBLICATION] {fields} complete_geometry=1\n"
        f"[INFO] [105.000000000] [sim]: [STATIC_PC_LATCHED_SUMMARY] enabled=1 {fields}\n"
        "[INFO] [105.000000000] [sim]: [SENSOR_CADENCE_SUMMARY] frames=50 span_s=4.9 hz=10.0\n"
        f"[INFO] [110.000000000] [sim]: [STATIC_PC_LATCHED_SUMMARY] enabled=1 {fields}\n"
        "[INFO] [110.000000000] [sim]: [SENSOR_CADENCE_SUMMARY] frames=100 span_s=9.9 hz=10.0\n")


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="latched_manifest_test_")
        self.root = Path(self.temp.name)
        paths = {}
        for name in p.BINDING_PATHS:
            path = self.root / "bindings" / name
            path.parent.mkdir(exist_ok=True)
            # Installed and source viewer files must have exactly equal bytes.
            content_name = name.replace("installed_view_", "runtime_view_")
            path.write_text(content_name + "\n")
            paths[name] = path
        self.binding_patch = patch.object(p, "BINDING_PATHS", paths)
        self.binding_patch.start()
        self.transports = []
        for i, (mode, sequence) in enumerate(sorted(p.PAIRS)):
            folder = self.root / (mode + "_" + sequence)
            folder.mkdir()
            path = folder / "result.json"
            stamp = 1800000000000000000 + i
            (folder / "simulator.log").write_text(log_text(stamp))
            phases = ["one_shot_geometry_published"] + (
                ["reader_first_static_geometry", "reader_first_steady_no_republish"] if sequence == "reader-first" else
                ["one_shot_without_subscribers", "late_subscriber_0_to_1"]) + [
                "subscriber_1_to_2", "subscriber_2_to_1_retained_without_republish", "subscriber_1_to_0_to_1"]
            data = dict(valid=True, composition=mode, sequence=sequence, latched_once=True, durable=True,
                        reader_qos="durable", poll_ms=1, effective_poll_ms=0, two_phase=False,
                        fixture_publishes_no_goals_or_commands=True, exact_child_reaped=True,
                        expected_sha256=p.EXPECTED_SHA256, no_fsm=mode == "standalone", ros_domain_id="190",
                        simulator_exit_code=0, publisher_actual_qos=p.QOS,
                        command=[str(paths["binary_" + mode]), "--ros-args", "-p",
                                 "config_name:=seed1.yaml" if mode == "standalone" else "drone_config:=seed1.yaml"],
                        graph_qos_verified=dict(reliability=True, durability=True, history=False, depth=False),
                        offered_qos=dict(reliability=1, durability=1, history=0, depth=0),
                        latched_once_audit=dict(valid=True, checks=dict.fromkeys(p.AUDIT_CHECKS, True),
                            initial=baseline(stamp), publication_count=1, summary_count=2,
                            observation_before_shutdown_s=11.0, steady_summary_span_s=5.0,
                            one_publication=True, no_static_timers=True, no_static_poll_callbacks=True,
                            all_readers_same_stamp=True),
                        clouds={phase: [cloud(stamp)] for phase in ("first", "second", "reconnected")},
                        geometry_sha256=p.EXPECTED_SHA256, geometry_validated_clouds=3,
                        latched_geometry_stamp_ns=stamp, geometry_layout=layout(), phases=phases,
                        no_flight_observation=dict(command_messages=0, odom_messages=1000,
                            initial_position=[0.0, 0.0, 1.5], max_position_delta_m=0.0,
                            first_odom_receipt_ns=1000000000, last_odom_receipt_ns=11000000000),
                        sensor_cadence_hz=[10.0, 10.0])
            if sequence == "reader-first":
                data.update(reader_first_geometry_valid=True, reader_first_geometry_sha256=p.EXPECTED_SHA256)
            save(path, data)
            self.transports.append(path)

        folder = self.root / "rviz"
        folder.mkdir()
        self.rviz = folder / "result.json"
        stamp = 1900000000000000000
        (folder / "simulator.log").write_text(log_text(stamp))
        self.probes = {}
        for phase in ("late", "reconnected"):
            screenshot = folder / (phase + ".png")
            screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(64))
            (folder / (phase + ".log")).write_text("RVIZ_STATIC_MAP valid=1\n")
            config = paths["installed_view_watch_sector"]
            geometry = dict(cloud(stamp), **layout())
            geometry["stamp_ns"] = str(stamp)
            probe = dict(valid=True, actual_rviz_display=True, extra_map_subscription=False,
                         screenshot_method="rviz_render_window_capture",
                         test_only_subscription_deferred=True, rviz_received_messages=1, own_global_pc_endpoints=1,
                         expected_sha256=p.EXPECTED_SHA256, expected_points=p.EXPECTED_POINTS,
                         geometry=geometry, configured_reader_qos=p.QOS,
                         requested_qos_graph=dict(reliability=1, durability=1, history=0, depth=0,
                                                 history_known=False, depth_known=False),
                         display_statuses=[dict(name="Points", level=0, value="Showing [241490] points from [1] messages")],
                         config=str(config), config_sha256=p.file_sha256(config), screenshot=str(screenshot))
            save(folder / (phase + ".json"), probe)
            self.probes[phase] = probe
        self.rviz_data = dict(valid=True, schema="static-latched-rviz-v1", reader_restarts=1,
            probes=[dict(self.probes[phase], phase=phase) for phase in ("late", "reconnected")],
            **self.probes, publisher_no_republish=True, no_fsm=True, no_goals_or_commands_published=True,
            actual_rviz=True, ros_domain_id=191, expected_sha256=p.EXPECTED_SHA256,
            expected_points=p.EXPECTED_POINTS, simulator_command=[str(paths["binary_standalone"]),
                "--ros-args", "-p", "config_name:=seed1.yaml"], publication_counters=baseline(stamp),
            latched_summary=dict(baseline(stamp), enabled="1"), steady_summary_span_s=5.0,
            observation_before_shutdown_s=11.0, viewer_cleanup=dict(forced=False, exit_code=0),
            simulator_cleanup=dict(forced=False, exit_code=0), phases=["one_shot_before_any_viewer",
                "late_actual_rviz_full_sha_display", "late_viewer_disconnected",
                "reconnected_actual_rviz_full_sha_display", "reconnected_viewer_disconnected"])
        save(self.rviz, self.rviz_data)
        self.manifest = self.root / "manifest.json"
        self.assertTrue(p.create_manifest(self.transports, self.rviz, self.manifest)["valid"])

    def tearDown(self):
        self.binding_patch.stop()
        self.temp.cleanup()

    def mutate_json(self, path, mutation):
        data = p.read_json(path)
        mutation(data)
        save(path, data)
        document = p.read_json(self.manifest)
        for record in document["transports"]:
            if record["result"]["path"] == str(path):
                record["result"] = p.file_record(path)
        if path == self.rviz:
            document["rviz"]["result"] = p.file_record(path)
        save(self.manifest, document)

    def assert_invalid(self):
        result = p.validate_manifest(self.manifest)
        self.assertFalse(result["valid"], result)
        self.assertTrue(result["errors"])
        return result

    def test_valid_exact_complete_contract(self):
        result = p.validate_manifest(self.manifest)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["schema"], "static-latched-contract-v1")
        self.assertEqual(result["manifest_sha256"], p.file_sha256(self.manifest))
        self.assertEqual(len(result["evidence_sha256"]), 20)
        self.assertEqual(set(result["runtime_sha256"]), set(p.BINDING_PATHS))

    def test_missing_malformed_manifest(self):
        self.assertFalse(p.validate_manifest(self.root / "missing.json")["valid"])
        for text in ("{", "[]", '{"schema":"x","schema":"x"}', '{"value":NaN}'):
            with self.subTest(text=text):
                self.manifest.write_text(text)
                self.assert_invalid()

    def test_wrong_schema(self):
        self.mutate_json(self.manifest, lambda d: d.update(schema="old"))
        self.assert_invalid()

    def test_manifest_reference_cannot_change(self):
        self.mutate_json(self.manifest, lambda d: d["expected_geometry"].update(sha256="0" * 64))
        self.assert_invalid()

    def test_missing_and_duplicate_transport_cases(self):
        original = self.manifest.read_text()
        for change in (lambda d: d["transports"].pop(),
                       lambda d: d["transports"].__setitem__(0, copy.deepcopy(d["transports"][1]))):
            self.manifest.write_text(original)
            self.mutate_json(self.manifest, change)
            self.assert_invalid()

    def test_case_label_cannot_lie(self):
        self.mutate_json(self.manifest, lambda d: d["transports"][0].update(case=["standalone", "late"]))
        self.assert_invalid()

    def test_evidence_hash_mismatch(self):
        self.transports[0].write_text(self.transports[0].read_text() + " ")
        self.assert_invalid()

    def test_log_hash_mismatch(self):
        log = self.transports[0].parent / "simulator.log"
        log.write_text(log.read_text() + "unbound change\n")
        self.assert_invalid()

    def test_runtime_hash_mismatch(self):
        p.BINDING_PATHS["runtime_model"].write_text("modified runtime\n")
        self.assert_invalid()

    def test_binding_cannot_redirect_to_arbitrary_same_bytes_file(self):
        original = p.BINDING_PATHS["runtime_model"]
        copied = self.root / "fake_model"
        copied.write_bytes(original.read_bytes())
        self.mutate_json(self.manifest, lambda d: d["bindings"].__setitem__("runtime_model", p.file_record(copied)))
        self.assert_invalid()

    def test_missing_binding_and_installed_source_mismatch(self):
        original = self.manifest.read_text()
        self.mutate_json(self.manifest, lambda d: d["bindings"].pop("binary_full"))
        self.assert_invalid()
        self.manifest.write_text(original)
        installed = p.BINDING_PATHS["installed_view_fpv"]
        installed.write_text("old installed config")
        self.mutate_json(self.manifest, lambda d: d["bindings"].__setitem__("installed_view_fpv", p.file_record(installed)))
        self.assert_invalid()

    def test_detailed_transport_rejections_even_when_valid_true(self):
        cases = [
            lambda d: d.update(valid=False),
            lambda d: d.update(valid=1),
            lambda d: d.update(error="ignored problem"),
            lambda d: d.update(latched_once=False),
            lambda d: d.update(effective_poll_ms=1),
            lambda d: d.update(two_phase=True),
            lambda d: d.update(reader_qos="legacy"),
            lambda d: d.update(exact_child_reaped=False),
            lambda d: d.update(forced_cleanup=True),
            lambda d: d.update(simulator_exit_code=-9),
            lambda d: d.update(simulator_exit_code=False),
            lambda d: d["command"].__setitem__(0, "/wrong/binary"),
            lambda d: d["command"].__setitem__(-1, "drone_config:=seed2.yaml"),
            lambda d: d["publisher_actual_qos"].update(durability="volatile"),
            lambda d: d["graph_qos_verified"].update(reliability=False),
            lambda d: d["latched_once_audit"].update(valid=False),
            lambda d: d["latched_once_audit"]["checks"].pop("exact_sha256"),
            lambda d: d["latched_once_audit"].update(summary_count=1),
            lambda d: d["latched_once_audit"].update(observation_before_shutdown_s=4.99),
            lambda d: d["latched_once_audit"].update(steady_summary_span_s=4.99),
            lambda d: d["latched_once_audit"]["initial"].update(publications=True),
            lambda d: d["clouds"]["reconnected"][0].update(stamp_ns=1),
            lambda d: d["clouds"]["first"][0].update(sha256="0" * 64),
            lambda d: d["clouds"]["second"][0].update(bytes=32),
            lambda d: d["clouds"]["second"].append(copy.deepcopy(d["clouds"]["second"][0])),
            lambda d: d["clouds"].pop("reconnected"),
            lambda d: d["geometry_layout"].update(row_step=1),
            lambda d: d["geometry_layout"]["fields"][3].update(offset=12),
            lambda d: d["phases"].pop(),
            lambda d: d["no_flight_observation"].update(command_messages=1),
            lambda d: d["no_flight_observation"].update(max_position_delta_m=0.01),
            lambda d: d["no_flight_observation"].update(odom_messages=1),
            lambda d: d["sensor_cadence_hz"].__setitem__(-1, 8.0),
        ]
        original_result = self.transports[0].read_text()
        original_manifest = self.manifest.read_text()
        for i, mutation in enumerate(cases):
            with self.subTest(case=i):
                self.transports[0].write_text(original_result)
                self.manifest.write_text(original_manifest)
                self.mutate_json(self.transports[0], mutation)
                self.assert_invalid()

    def test_publisher_raw_log_details_not_just_asserted_checks(self):
        log = self.transports[0].parent / "simulator.log"
        original_log = log.read_text()
        original_manifest = self.manifest.read_text()
        changes = [
            lambda s: s.replace("publications=1", "publications=2"),
            lambda s: s.replace("poll_callbacks=0", "poll_callbacks=1"),
            lambda s: s.replace("timers_created=0", "timers_created=1"),
            lambda s: s.replace("poll_ms=0", "poll_ms=1"),
            lambda s: s.replace("[110.000000000]", "[109.999999999]"),
            lambda s: s.replace("[110.000000000]", "[104.000000000]"),
            lambda s: s.replace("hz=10.0", "hz=8.0"),
            lambda s: s + "Publish global map size: 241490\n",
            lambda s: s.replace("intra_process=disabled", "intra_process=node_default"),
            lambda s: s.replace("complete_geometry=1", "complete_geometry=0"),
            lambda s: s.replace("durability=transient_local", "durability=volatile"),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                self.manifest.write_text(original_manifest)
                log.write_text(change(original_log))
                self.mutate_json(self.manifest, lambda d: d["transports"][0].__setitem__("log", p.file_record(log)))
                self.assert_invalid()

    def test_rviz_detailed_rejections(self):
        cases = [lambda d: d.update(valid=False), lambda d: d.update(actual_rviz=False),
                 lambda d: d.update(no_fsm=False), lambda d: d.update(reader_restarts=0),
                 lambda d: d["viewer_cleanup"].update(exit_code=1),
                 lambda d: d["simulator_cleanup"].update(forced=True),
                 lambda d: d.update(publisher_no_republish=False),
                 lambda d: d.update(observation_before_shutdown_s=4.99),
                 lambda d: d["phases"].pop(), lambda d: d["probes"].pop(),
                 lambda d: d["late"]["geometry"].update(stamp_ns="1")]
        original = self.rviz.read_text()
        original_manifest = self.manifest.read_text()
        for i, mutation in enumerate(cases):
            with self.subTest(case=i):
                self.rviz.write_text(original)
                self.manifest.write_text(original_manifest)
                self.mutate_json(self.rviz, mutation)
                self.assert_invalid()

    def test_rviz_plugin_proof_not_substitute_subscriber(self):
        original_probe = copy.deepcopy(self.probes["late"])
        mutations = [lambda d: d.update(extra_map_subscription=True),
                     lambda d: d.update(actual_rviz_display=False),
                     lambda d: d.update(rviz_received_messages=2),
                     lambda d: d.update(own_global_pc_endpoints=2),
                     lambda d: d["display_statuses"][0].update(level=2),
                     lambda d: d["display_statuses"][0].update(value="Showing [4] points from [1] messages"),
                     lambda d: d["requested_qos_graph"].update(durability=2),
                     lambda d: d.update(config_sha256="0" * 64)]
        bindings = p.read_json(self.manifest)["bindings"]
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i):
                probe = copy.deepcopy(original_probe)
                mutate(probe)
                with self.assertRaises(p.InvalidEvidence):
                    p.validate_probe(probe, baseline(1900000000000000000), bindings)

    def test_missing_or_invalid_png(self):
        path = self.rviz.parent / "late.png"
        path.write_text("not an image")
        self.mutate_json(self.manifest, lambda d: d["rviz"]["probes"]["late"].__setitem__("screenshot", p.file_record(path)))
        self.assert_invalid()

    def test_existing_output_preserved(self):
        before = self.manifest.read_bytes()
        with self.assertRaises(p.InvalidEvidence):
            p.create_manifest(self.transports, self.rviz, self.manifest)
        self.assertEqual(before, self.manifest.read_bytes())

    def test_failed_create_does_not_leave_manifest(self):
        path = self.root / "failed.json"
        self.mutate_json(self.transports[0], lambda d: d.update(valid=False))
        with self.assertRaises(p.InvalidEvidence):
            p.create_manifest(self.transports, self.rviz, path)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
