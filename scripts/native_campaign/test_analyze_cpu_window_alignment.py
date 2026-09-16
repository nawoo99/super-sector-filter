"""Small offline accounting tests; no production files, ROS, or binaries."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "analyze_cpu_window_alignment", Path(__file__).with_name("analyze_cpu_window_alignment.py"))
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def telemetry():
    return [dict(monotonic_s=float(i), interval_s=1.0, mode="full", campaign_active=True,
                 cgroup_paths=["/experiment"], cgroup_interval_cores=0.5,
                 experiment_processes=[dict(pid=10, name="sim", scope="algorithm", cpu_pct_one_core=40.),
                                       dict(pid=11, name="mission", scope="stack", cpu_pct_one_core=10.)])
            for i in range(8)]


def raw_telemetry():
    rows = telemetry()
    for i, row in enumerate(rows):
        row.update(raw_cpu_counters_version=1,
                   cgroup_cpu_cumulative=[dict(path="/experiment", usage_usec=i * 500000,
                       read_monotonic_start_s=i + .01, read_monotonic_end_s=i + .02)],
                   experiment_process_cumulative=[
                       dict(pid=pid, name=name, scope=scope, create_time=created,
                            cpu_user_s=i * cores, cpu_system_s=0., cpu_total_s=i * cores,
                            read_monotonic_start_s=i + offset, read_monotonic_end_s=i + offset + .01)
                       for pid, name, scope, created, cores, offset in (
                           (10, "sim", "algorithm", 100., .4, .03),
                           (11, "mission", "stack", 101., .1, .05))])
    return rows


class AlignmentTest(unittest.TestCase):
    def test_raw_precise_reads_override_percentages_without_interpolation(self):
        rows = raw_telemetry()
        # Corrupted legacy percentages cannot affect raw-counter accounting.
        for row in rows:
            row["experiment_processes"][0]["cpu_pct_one_core"] = 999999.
            row["cgroup_interval_cores"] = 999999.
        for scope, expected, first, last in (
                ("composed_process", .4, .03, .04),
                ("noncomposed_processes", .1, .05, .06),
                ("experiment_process_sum", .5, .03, .06),
                ("experiment_cgroup", .5, .01, .02)):
            with self.subTest(scope=scope):
                values, missing = a.telemetry_intervals(rows, "full", 10, scope)
                conservative, _ = a.telemetry_intervals(rows, "full", 10, scope, bracket_reads=True)
                self.assertEqual(values, conservative)
                self.assertFalse(missing)
                self.assertEqual(len(values), len(rows) - 1)  # no next-row workaround
                self.assertAlmostEqual(values[0]["cpu_core_s"], expected)
                self.assertAlmostEqual(values[0]["start_earliest"], first)
                self.assertAlmostEqual(values[0]["start_latest"], last)
                self.assertAlmostEqual(values[0]["end_earliest"], 1 + first)
                self.assertAlmostEqual(values[0]["end_latest"], 1 + last)
                self.assertEqual(values[0]["counter_source"], "raw_cumulative_actual_read_brackets")
                bounds = a.bound_intervals(values, 1.5, 4.5)
                self.assertAlmostEqual(bounds["lower_cpu_core_s"], expected * 2)
                self.assertAlmostEqual(bounds["upper_cpu_core_s"], expected * 4)
                self.assertFalse(bounds["interpolation_used"])

    def test_raw_missing_process_or_counter_creates_gap_not_percent_fallback(self):
        for mutation, scope in (
                (lambda r: r.update(experiment_process_cumulative=[]), "composed_process"),
                (lambda r: r.pop("experiment_process_cumulative"), "composed_process"),
                (lambda r: r["cgroup_cpu_cumulative"][0].update(usage_usec=None), "experiment_cgroup"),
                (lambda r: r.update(raw_cpu_counters_version=2), "composed_process"),
                (lambda r: r.update(raw_cpu_counters_version=True), "composed_process"),
                (lambda r: r.pop("raw_cpu_counters_version"), "composed_process")):
            with self.subTest(scope=scope, mutation=mutation):
                rows = raw_telemetry()
                mutation(rows[3])
                values, missing = a.telemetry_intervals(rows, "full", 10, scope)
                self.assertEqual(len(missing), 2)
                self.assertTrue(all(v["percentage_fallback_prohibited"] for v in missing))
                self.assertIsNone(a.bound_intervals(values, 2.5, 5.5)["upper_cpu_core_s"])

    def test_raw_pid_reuse_even_same_name_and_scope_rejects_delta(self):
        rows = raw_telemetry()
        rows[3]["experiment_process_cumulative"][0]["create_time"] = 200.
        values, missing = a.telemetry_intervals(rows, "full", 10, "composed_process")
        self.assertEqual(len(missing), 2)
        self.assertTrue(all("PID reused" in v["reason"] for v in missing))
        self.assertIsNone(a.bound_intervals(values, 2.5, 5.5)["upper_cpu_core_s"])

    def test_raw_reset_rejected_not_clamped_or_fallback(self):
        for scope, key in (("composed_process", "experiment_process_cumulative"),
                           ("experiment_cgroup", "cgroup_cpu_cumulative")):
            rows = raw_telemetry()
            item = rows[3][key][0]
            if scope == "composed_process":
                item.update(cpu_user_s=.1, cpu_system_s=0., cpu_total_s=.1)
            else:
                item["usage_usec"] = 1
            with self.subTest(scope=scope), self.assertRaisesRegex(ValueError, "reset/decrease"):
                a.telemetry_intervals(rows, "full", 10, scope)

    def test_raw_inconsistent_counter_or_invalid_bracket_rejected(self):
        for mutation in (
                lambda v: v.update(cpu_total_s=999.),
                lambda v: v.update(read_monotonic_start_s=2.9),
                lambda v: v.update(read_monotonic_end_s=3.01),
                lambda v: v.update(read_monotonic_end_s=float("nan")),
                lambda v: v.pop("create_time")):
            rows = raw_telemetry()
            mutation(rows[3]["experiment_process_cumulative"][0])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                a.telemetry_intervals(rows, "full", 10, "composed_process")
        rows = raw_telemetry()
        rows[2]["experiment_process_cumulative"][0]["read_monotonic_end_s"] = 3.5
        with self.assertRaisesRegex(ValueError, "overlap/backtrack"):
            a.telemetry_intervals(rows, "full", 10, "composed_process")

    def test_raw_scope_membership_change_and_duplicate_identity(self):
        rows = raw_telemetry()
        rows[3]["experiment_process_cumulative"].pop()
        values, missing = a.telemetry_intervals(rows, "full", 10, "experiment_process_sum")
        self.assertEqual(len(missing), 2)
        self.assertIsNone(a.bound_intervals(values, 2.5, 5.5)["upper_cpu_core_s"])
        # Missing another process must not invalidate this composed process.
        _, missing = a.telemetry_intervals(rows, "full", 10, "composed_process")
        self.assertFalse(missing)
        rows = raw_telemetry()
        rows[3]["experiment_process_cumulative"].append(copy.deepcopy(rows[3]["experiment_process_cumulative"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a.telemetry_intervals(rows, "full", 10, "composed_process")
        rows = raw_telemetry()
        rows[3]["cgroup_paths"] = ["/wrong"]
        _, missing = a.telemetry_intervals(rows, "full", 10, "experiment_cgroup")
        self.assertEqual(len(missing), 2)

    def test_nominal_wholly_enclosed_lower_full_boundary_upper(self):
        values = [a.interval(i, i + 1, i + 1) for i in range(5)]
        result = a.bound_intervals(values, .5, 3.5)
        self.assertTrue(result["complete_counter_chain"])
        self.assertEqual(result["lower_cpu_core_s"], 5)
        self.assertEqual(result["upper_cpu_core_s"], 10)
        self.assertEqual(result["wholly_enclosed_intervals"], 2)
        self.assertEqual(result["boundary_intervals"], 2)
        self.assertFalse(result["interpolation_used"])
        self.assertAlmostEqual(result["lower_mean_cores"], 5 / 3)

    def test_exact_nominal_boundaries_have_no_boundary_uncertainty(self):
        result = a.bound_intervals([a.interval(i, i + 1, 2.) for i in range(5)], 1., 4.)
        self.assertEqual(result["lower_cpu_core_s"], 6.)
        self.assertEqual(result["upper_cpu_core_s"], 6.)
        self.assertEqual(result["boundary_intervals"], 0)

    def test_actual_counter_read_brackets_widen_not_interpolate(self):
        values = [a.interval(i, i + 1, i + 1, next_start=i + 2) for i in range(6)]
        result = a.bound_intervals(values, 1.5, 4.5)
        self.assertTrue(result["complete_counter_chain"])
        self.assertEqual(result["lower_cpu_core_s"], 3.)
        self.assertEqual(result["upper_cpu_core_s"], 15.)
        self.assertEqual(result["boundary_intervals"], 4)

    def test_gap_does_not_fabricate_finite_upper_bound(self):
        result = a.bound_intervals([a.interval(0, 1, 1), a.interval(2, 3, 1), a.interval(3, 4, 1)], .5, 3.5)
        self.assertFalse(result["complete_counter_chain"])
        self.assertIsNone(result["upper_cpu_core_s"])
        self.assertEqual(result["lower_cpu_core_s"], 1.)
        self.assertTrue(result["missing_chain_edges"])

    def test_missing_outer_sample_is_unbounded(self):
        result = a.bound_intervals([a.interval(1, 2, 1), a.interval(2, 3, 1)], .5, 2.5)
        self.assertFalse(result["complete_counter_chain"])
        self.assertIsNone(result["upper_mean_cores"])

    def test_nonoverlap_is_not_counted(self):
        result = a.bound_intervals([a.interval(0, 1, 100), a.interval(1, 2, 3), a.interval(2, 3, 100)], 1, 2)
        self.assertEqual(result["lower_cpu_core_s"], 3.)
        self.assertEqual(result["upper_cpu_core_s"], 3.)

    def test_invalid_interval_window_and_nonfinite_rejected(self):
        for args in ((0, 0, 1), (2, 1, 1), (0, 1, -1), (0, 1, float("nan")), (True, 1, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                a.interval(*args)
        with self.assertRaises(ValueError):
            a.interval(0, 1, 1, next_start=1)
        with self.assertRaises(ValueError):
            a.bound_intervals([], 1, 1)

    def test_process_and_cgroup_are_separate_scopes(self):
        rows = telemetry()
        expected = {"composed_process": .4, "noncomposed_processes": .1,
                    "experiment_process_sum": .5, "experiment_cgroup": .5}
        for scope, cores in expected.items():
            with self.subTest(scope=scope):
                values, _ = a.telemetry_intervals(rows, "full", 10, scope)
                result = a.bound_intervals(values, 2, 5)
                self.assertAlmostEqual(result["lower_cpu_core_s"], cores * 3)
                self.assertAlmostEqual(result["upper_cpu_core_s"], cores * 3)
        with self.assertRaises(ValueError):
            a.telemetry_intervals(rows, "full", 10, "inclusive_plus_cgroup")

    def test_sample_dt_disagreement_rejected(self):
        rows = telemetry()
        rows[3]["interval_s"] = .5
        with self.assertRaises(ValueError):
            a.telemetry_intervals(rows, "full", 10, "composed_process")

    def test_missing_pid_or_identity_does_not_fill_zero(self):
        rows = telemetry()
        rows[3]["experiment_processes"] = []
        values, missing = a.telemetry_intervals(rows, "full", 10, "composed_process")
        result = a.bound_intervals(values, 2.5, 5.5)
        self.assertTrue(missing)
        self.assertIsNone(result["upper_cpu_core_s"])
        rows = telemetry()
        rows[3]["experiment_processes"][0]["name"] = "other"
        _, missing = a.telemetry_intervals(rows, "full", 10, "composed_process")
        self.assertEqual(len(missing), 2)

    def test_cgroup_identity_change_creates_gap(self):
        rows = telemetry()
        rows[4]["cgroup_paths"] = ["/different"]
        values, missing = a.telemetry_intervals(rows, "full", 10, "experiment_cgroup")
        self.assertEqual(len(missing), 2)
        self.assertIsNone(a.bound_intervals(values, 2, 6)["upper_cpu_core_s"])

    def test_duplicate_pid_rejected(self):
        rows = telemetry()
        rows[3]["experiment_processes"].append(copy.deepcopy(rows[3]["experiment_processes"][0]))
        with self.assertRaises(ValueError):
            a.telemetry_intervals(rows, "full", 10, "composed_process")

    def test_report_exclusive_only_not_inclusive_double_count(self):
        process = dict(first_report_monotonic_s=1., last_report_monotonic_s=11., duration_s=10.,
                       sum_exclusive_mean_cores=.4, stages=[
                           dict(stage="parent", exclusive_cpu_s=1., inclusive_cpu_s=4., calls=1, clock_errors=0),
                           dict(stage="child", exclusive_cpu_s=3., inclusive_cpu_s=3., calls=1, clock_errors=0)])
        result = a.stage_accounting(process)
        self.assertEqual(result["exclusive_cpu_core_s"], 4.)
        self.assertEqual(result["exclusive_mean_cores"], .4)
        for mutation in (lambda d: d.update(duration_s=9.),
                         lambda d: d.update(sum_exclusive_mean_cores=.7),
                         lambda d: d["stages"][0].update(clock_errors=1),
                         lambda d: d["stages"][0].update(exclusive_cpu_s=-1.),
                         lambda d: d["stages"][1].update(stage="parent")):
            bad = copy.deepcopy(process)
            mutation(bad)
            with self.assertRaises(ValueError):
                a.stage_accounting(bad)

    def test_residual_negative_lower_not_hidden_and_not_physical_bound(self):
        bounds = a.bound_intervals([a.interval(i, i + 1, 1) for i in range(4)], .5, 2.5)
        result = a.accounting_residual(bounds, 2.)
        self.assertEqual(result["lower_accounting_cpu_core_s"], -1.)
        self.assertEqual(result["upper_accounting_cpu_core_s"], 1.)
        self.assertFalse(result["physical_uninstrumented_cpu_bound"])

    def test_raw_cumulative_trace_does_not_guess_absolute_origin(self):
        with tempfile.TemporaryDirectory(prefix="cpu_window_test_") as folder:
            path = Path(folder) / "raw.csv"
            path.write_text("elapsed_s,algorithm_usage_usec,end_to_end_usage_usec\n"
                            "0.0001,10,20\n1.0001,200010,300020\n")
            result = a.raw_cgroup_summary(path)
            self.assertFalse(result["alignment_available"])
            self.assertAlmostEqual(result["algorithm_observed_cpu_core_s"], .2)
            self.assertAlmostEqual(result["end_to_end_observed_cpu_core_s"], .3)
            path.write_text("elapsed_s,algorithm_usage_usec,end_to_end_usage_usec\n0,10,20\n1,0,30\n")
            with self.assertRaises(ValueError):
                a.raw_cgroup_summary(path)


if __name__ == "__main__":
    unittest.main()
