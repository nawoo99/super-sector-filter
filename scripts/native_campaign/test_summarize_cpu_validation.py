import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

import summarize_cpu_validation as report


class NumericTests(unittest.TestCase):
    def test_missing_and_nonfinite_are_not_zero(self):
        for value in (None, "", "nan", float("inf"), "not applicable"):
            self.assertIsNone(report.numeric(value))
        self.assertEqual(report.numeric(False), 0)
        self.assertEqual(report.numeric("True"), 1)
        stats = report.distribution([1, 3, None, "nan"])
        self.assertEqual(stats["n"], 2)
        self.assertEqual(stats["mean"], 2)
        self.assertAlmostEqual(stats["sd"], math.sqrt(2))
        self.assertIsNone(report.distribution([1])["sd"])
        self.assertIsNone(report.distribution([])["mean"])

    def test_nearest_rank(self):
        self.assertEqual(report.nearest_rank(range(1, 21), .95), 19)
        self.assertIsNone(report.nearest_rank([], .95))

    def test_numeric_flatten_does_not_align_event_lists(self):
        self.assertEqual(report.flatten_numeric({"a": {"n": 2}, "events": [{"id": 7}]}), {"a.n": 2})

    def test_numeric_inventory_retains_nonfinite_fields(self):
        self.assertTrue(report.is_numeric_field("nan"))
        self.assertTrue(report.is_numeric_field("inf"))
        self.assertFalse(report.is_numeric_field("file.csv"))

    def test_source_log_scope_detects_sampling_gaps(self):
        values = report.source_log_metrics({"source_acquisition": {"frames": [
            {"frame": 1, "full": 0, "width": 225, "conversion_rays": 28800},
            {"frame": 50, "full": 1, "width": 900, "conversion_rays": 115200}]}})
        self.assertEqual(values["source_logged.frames"], 2)
        self.assertEqual(values["source_logged.contiguous_unique_ids"], 0)
        self.assertEqual(values["source_logged.width.mean"], 562.5)
        self.assertEqual(values["source_logged.full_frame_fraction_pct"], 50)
        self.assertIsNone(values["source_logged.sector_to_full_count"])
        self.assertNotIn("mission_full_duty_pct", values)

    def test_source_log_actual_direction_changes_not_legacy_counters(self):
        values = report.source_log_metrics({"source_acquisition": {"frames": [
            {"frame": index + 1, "full": flag} for index, flag in enumerate([0, 0, 1, 1, 0])]}})
        self.assertEqual(values["source_logged.sector_to_full_count"], 1)
        self.assertEqual(values["source_logged.full_to_sector_count"], 1)
        self.assertEqual(values["source_logged.direction_change_count"], 2)


def make_run(mode, mean, run="1", profile=False, success=True, **metrics):
    return dict(candidate="c19", map="seed1", cpu_profile=profile, mode=mode, run=run,
                source=f"/tmp/{run}/raw.csv", summary_source="/tmp/summary.json",
                protocol_fingerprint="same", scopes={}, metrics={
                    "end_to_end_cpu_cores_mean": mean, "success": float(success),
                    "run_valid": 1, "safety_collisions": 0, **metrics})


class AggregateTests(unittest.TestCase):
    def test_profiles_never_mix_and_failures_remain(self):
        runs = [make_run("full", 1), make_run("full", 3, "2"),
                make_run("adaptive", 1, success=False), make_run("adaptive", 2, "2"),
                make_run("full", 100, "3", profile=True)]
        cohorts = report.aggregate(runs)
        primary = next(c for c in cohorts if c["profile"] == "unprofiled_primary")
        full = primary["modes"]["full"]
        adaptive = primary["modes"]["adaptive"]
        self.assertEqual(full["metrics"]["end_to_end_cpu_cores_mean"]["mean"], 2)
        self.assertEqual(adaptive["metrics"]["end_to_end_cpu_cores_mean"]["reduction_vs_full_pct"], 25)
        self.assertEqual(adaptive["successes"], 1)
        self.assertEqual(adaptive["attempts"], 2)
        self.assertFalse(primary["all_modes_completed_all_attempts"])
        self.assertEqual(len(cohorts), 2)

    def test_missing_scope_and_zero_denominator(self):
        cohorts = report.aggregate([make_run("full", 0, extra=None),
                                    make_run("adaptive", 1, extra=2)])
        values = cohorts[0]["modes"]
        self.assertIsNone(values["adaptive"]["metrics"]["end_to_end_cpu_cores_mean"]["reduction_vs_full_pct"])
        self.assertEqual(values["full"]["metrics"]["extra"]["n_missing"], 1)
        self.assertIsNone(values["adaptive"]["metrics"]["extra"]["reduction_vs_full_pct"])

    def test_different_maps_and_candidates_remain_separate(self):
        a, b, c = make_run("full", 1), make_run("full", 2), make_run("full", 3)
        b["map"] = "seed2"
        c["candidate"] = "not_c19"
        self.assertEqual(len(report.aggregate([a, b, c])), 3)

    def test_mixed_protocol_not_silently_pooled(self):
        a, b = make_run("full", 1), make_run("adaptive", .5)
        b["protocol_fingerprint"] = "different"
        with self.assertRaisesRegex(ValueError, "Mixed protocol fingerprints"):
            report.aggregate([a, b])


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "r1"
        self.folder.mkdir()
        self.plan = {"candidate": "c19", "cpu_profile": False, "logical_cpus": 20, "run": 1}
        (self.folder / "plan.json").write_text(json.dumps(self.plan))
        self.row = dict(map="seed1", run="1", mode="full", success="True", run_valid="True",
                        safety_collisions="0", end_to_end_cpu_cores_mean="0.5", end_to_end_cpu_core_s="21",
                        mission_time_s="40", cgroup_cpu_duration_s="42", perf_window_valid="True",
                        perf_trace_csv="p.csv", perf_row_start="1", perf_row_end="3", unavailable="nan")
        self.write_raw([self.row])
        (self.folder / "p.csv").write_text("Total, Raycast, PointCloudNumber\n0.9, 0.8, 999\n0.01, 0.007, 10\n0.02, 0.015, 20\n0.9, 0.8, 999\n")
        (self.folder / "full_summary.json").write_text(json.dumps({"map": "seed1", "run": 1, "mode": "full", "cpu_profile": False}))

    def write_raw(self, rows):
        with (self.folder / "raw.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_perf_uses_declared_slice_not_full_file(self):
        metrics, warning = report.perf_metrics(self.row, self.folder, self.root)
        self.assertIsNone(warning)
        self.assertEqual(metrics["performance.Total.ms.mean"], 15)
        self.assertEqual(metrics["performance.Total.ms.sum"], 30)
        self.assertEqual(metrics["performance.PointCloudNumber.value.sum"], 30)

    def test_invalid_perf_window_not_silently_used(self):
        self.row["perf_row_end"] = "50"
        metrics, warning = report.perf_metrics(self.row, self.folder, self.root)
        self.assertEqual(metrics, {})
        self.assertIn("bounds invalid", warning)

    def test_missing_nonfinite_fractional_perf_bounds_rejected(self):
        for value in (None, "", "nan", "inf", "1.5"):
            with self.subTest(value=value):
                self.row["perf_row_end"] = value
                metrics, warning = report.perf_metrics(self.row, self.folder, self.root)
                self.assertEqual(metrics, {})
                self.assertIn("bounds missing", warning)

    def test_zero_end_is_empty_not_entire_trace(self):
        self.row.update(perf_row_start="0", perf_row_end="0")
        metrics, warning = report.perf_metrics(self.row, self.folder, self.root)
        self.assertEqual(metrics, {})
        self.assertIn("slice is empty", warning)

    def test_cpu_normalized_by_cores_not_mission_time(self):
        runs, warnings = report.load_runs([self.root], self.root)
        self.assertEqual(warnings, [])
        metric = runs[0]["metrics"]
        self.assertEqual(metric["end_to_end_host_capacity_pct_mean"], 2.5)
        self.assertEqual(metric["end_to_end_cpu_core_s"], 21)
        self.assertIsNone(metric["autonomy_only_cpu_cores_mean"])
        self.assertIn("unavailable", metric)
        self.assertIsNone(metric["unavailable"])

    def test_summary_identity_mismatch_rejected(self):
        (self.folder / "full_summary.json").write_text(json.dumps({"mode": "adaptive"}))
        with self.assertRaisesRegex(ValueError, "Mismatched mode"):
            report.load_runs([self.root], self.root)

    def test_summary_profiling_mismatch_rejected(self):
        (self.folder / "full_summary.json").write_text(json.dumps({"cpu_profile": True}))
        with self.assertRaisesRegex(ValueError, "Profiling state mismatch"):
            report.load_runs([self.root], self.root)

    def test_duplicate_record_rejected(self):
        self.write_raw([self.row, self.row])
        with self.assertRaisesRegex(ValueError, "Duplicate recorded run"):
            report.load_runs([self.root], self.root)

    def test_duplicate_identity_in_another_folder_rejected(self):
        second = self.root / "duplicate"
        second.mkdir()
        (second / "plan.json").write_text((self.folder / "plan.json").read_text())
        (second / "raw.csv").write_text((self.folder / "raw.csv").read_text())
        with self.assertRaisesRegex(ValueError, "Duplicate recorded run"):
            report.load_runs([self.root], self.root)

    def test_planned_five_not_satisfied_by_one_per_mode(self):
        (self.root / "plan.json").write_text(json.dumps({"map": "seed1", "unprofiled_runs_per_mode": 5}))
        cohorts = report.aggregate([make_run(mode, 1) for mode in report.MODES])
        report.planned_coverage(cohorts, [self.root])
        self.assertEqual(cohorts[0]["planned_attempts_per_mode"], 5)
        self.assertFalse(cohorts[0]["planned_slots_observed"])
        self.assertTrue(cohorts[0]["all_modes_completed_all_attempts"])

    def test_unknown_logical_cpu_count_not_assumed_twenty(self):
        self.plan.pop("logical_cpus")
        (self.folder / "plan.json").write_text(json.dumps(self.plan))
        runs, _ = report.load_runs([self.root], self.root)
        self.assertIsNone(runs[0]["metrics"]["end_to_end_host_capacity_pct_mean"])

    def test_cli_outputs_csv_json_and_markdown(self):
        output = self.root / "comparison"
        report.main(["--campaign", str(self.root), "--output", str(output), "--repo", str(self.root)])
        for name in ("comparison.json", "all_metrics.csv", "run_metrics.csv", "metric_inventory.csv", "README.md", "profiled_stages.csv", "summary_ko.md"):
            self.assertTrue((output / name).is_file())
        parsed = json.loads((output / "comparison.json").read_text())
        self.assertEqual(len(parsed["runs"]), 1)
        self.assertIn("measurement-window", (output / "README.md").read_text())

    def test_korean_summary_separates_whole_host_and_experiment(self):
        output = self.root / "ko"
        output.mkdir()
        cohorts = report.aggregate([make_run(mode, 1) for mode in report.MODES])
        report.write_korean_summary(output, cohorts)
        content = (output / "summary_ko.md").read_text()
        self.assertIn("주행 중 컴퓨터 전체 CPU (배경 포함, %)", content)
        self.assertIn("주행 전 baseline 컴퓨터 전체 CPU", content)
        self.assertIn("인과적 CPU 비용이 되지는 않습니다", content)
        self.assertIn("RSS 표본 최대", content)
        self.assertIn("PSS 표본 최대", content)

    def test_known_process_roles_not_pid_aligned(self):
        result = report.process_metrics({"processes": [
            {"name": "perfect_drone_full_node", "pid": 123, "cpu_pct_one_core": {"mean": 50}}]})
        self.assertEqual(result["process.composed_simulator_frontend_planner.cpu_pct_one_core.mean"], 50)

    def test_telemetry_active_mode_only_and_gpu_memory_util(self):
        samples = [{"mode": "full", "campaign_active": False, "gpu_memory_util_pct": 99},
                   {"mode": "full", "campaign_active": True, "gpu_memory_util_pct": 10,
                    "host_per_logical_cpu_pct": [1, 2]},
                   {"mode": "adaptive", "campaign_active": True, "gpu_memory_util_pct": 80}]
        result = report.telemetry_metrics(samples, "full")
        self.assertEqual(result["telemetry.gpu_memory_util_pct.mean"], 10)
        self.assertEqual(result["telemetry.host_logical_cpu1_pct.mean"], 2)


if __name__ == "__main__":
    unittest.main()
