#!/usr/bin/env python3

import importlib.util
import math
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("summarize_resource_guard_campaign.py")
SPEC = importlib.util.spec_from_file_location("resource_summary", MODULE_PATH)
summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summary)


def valid_row(map_name="seed1", run="1", mode="full"):
    row = {
        "map": map_name,
        "run": run,
        "mode": mode,
        "success": "True",
        "attempt_count": "1",
        "mission_time_s": "60",
        "static_pcd_clearance_m": "0.25",
        "safety_collisions": "0",
        "filter_effective_full_open_transitions": "",
        "algorithm_cpu_scope": "simulator+planner",
        "algorithm_cpu_excludes_simulator": "False",
        "end_to_end_cpu_scope": "simulator+frontend+planner+mission",
        "system_min_available_mib": "5500",
        "system_peak_swap_used_mib": "1",
        "memory_psi_some_avg10_max": "0",
        "memory_psi_full_avg10_max": "0",
        "resource_guard_preflight_wait_s": "5",
    }
    row.update({field: "True" for field in summary.TRUE_QUALITY_FIELDS})
    row.update({field: "False" for field in summary.FALSE_QUALITY_FIELDS})
    row.update({field: "0" for field in summary.ZERO_QUALITY_FIELDS})
    row.update({field: "1.0" for field, _label in summary.METRICS})
    row["mission_time_s"] = "60"
    return row


class ResourceGuardCampaignSummaryTest(unittest.TestCase):
    def test_exact_key_and_quality_validation(self):
        rows = [valid_row(mode=mode) for mode in summary.MODES]
        result = summary.validate(rows, ["seed1"], 1)
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_rows"], 3)
        rows[0]["resource_valid"] = "False"
        result = summary.validate(rows, ["seed1"], 1)
        self.assertFalse(result["passed"])
        self.assertEqual(result["quality_failure_count"], 1)

    def test_duplicate_and_missing_keys_are_separate(self):
        row = valid_row()
        result = summary.validate([row, dict(row)], ["seed1"], 1)
        self.assertFalse(result["passed"])
        self.assertEqual(result["duplicate_keys"], [["seed1", 1, "full"]])
        self.assertEqual(len(result["missing_keys"]), 2)

    def test_summary_ignores_blank_and_nonfinite_metrics(self):
        first = valid_row()
        second = valid_row(run="2")
        first["algorithm_cpu_cores_mean"] = ""
        second["algorithm_cpu_cores_mean"] = "nan"
        second["success"] = "False"
        second["safety_collisions"] = "2"
        result = summary.summarize_group("seed1", "full", [first, second])
        self.assertEqual(result["complete"], 1)
        self.assertEqual(result["collision_runs"], 1)
        self.assertEqual(result["collision_events"], 2)
        self.assertIsNone(result["algorithm_cores_mean"])
        self.assertAlmostEqual(result["mission_time_mean_all_s"], 60)

    def test_summary_counts_speed_validity_and_clearance_margin_violations(self):
        first = valid_row()
        second = valid_row(run="2")
        first["static_pcd_clearance_m"] = "0.20"
        second["static_pcd_clearance_m"] = "0.199"
        second["speed_limit_valid"] = "False"
        result = summary.summarize_group("seed1", "full", [first, second])
        self.assertEqual(result["speed_limit_valid_count"], 1)
        self.assertEqual(result["clearance_below_0p20_count"], 1)

    def test_reduction_sign(self):
        self.assertAlmostEqual(summary.reduction(2.0, 10.0), 80.0)
        self.assertAlmostEqual(summary.reduction(12.0, 10.0), -20.0)
        self.assertIsNone(summary.reduction(1.0, 0.0))

    def test_algorithm_reductions_require_matching_scope(self):
        full = summary.summarize_group("seed1", "full", [valid_row()])
        sector_row = valid_row(mode="sector")
        sector_row["algorithm_cpu_scope"] = "planner_only"
        sector = summary.summarize_group("seed1", "sector", [sector_row])
        adaptive_row = valid_row(mode="adaptive")
        adaptive_row["algorithm_cpu_scope"] = "planner_only"
        adaptive = summary.summarize_group("seed1", "adaptive", [adaptive_row])
        rows = summary.build_reductions([full, sector, adaptive])
        algorithm = next(row for row in rows if row["metric"] == "algorithm_cores_mean")
        self.assertFalse(algorithm["adaptive_vs_full_comparison_valid"])
        self.assertIsNone(algorithm["adaptive_vs_full_reduction_pct"])
        self.assertTrue(algorithm["adaptive_vs_sector_comparison_valid"])
        end_to_end = next(row for row in rows if row["metric"] == "end_to_end_cores_mean")
        self.assertTrue(end_to_end["adaptive_vs_full_comparison_valid"])

    def test_reductions_require_all_runs_to_be_protocol_valid(self):
        full = summary.summarize_group("seed1", "full", [valid_row()])
        sector_row = valid_row(mode="sector")
        sector_row["algorithm_cpu_scope"] = "planner_only"
        sector_row["run_valid"] = "False"
        sector = summary.summarize_group("seed1", "sector", [sector_row])
        adaptive_row = valid_row(mode="adaptive")
        adaptive_row["algorithm_cpu_scope"] = "planner_only"
        adaptive = summary.summarize_group("seed1", "adaptive", [adaptive_row])
        rows = summary.build_reductions([full, sector, adaptive])
        end_to_end = next(row for row in rows if row["metric"] == "end_to_end_cores_mean")
        self.assertFalse(end_to_end["sector_vs_full_comparison_valid"])
        self.assertIsNone(end_to_end["sector_vs_full_reduction_pct"])
        self.assertFalse(end_to_end["adaptive_vs_sector_comparison_valid"])
        self.assertIsNone(end_to_end["adaptive_vs_sector_reduction_pct"])
        self.assertTrue(end_to_end["adaptive_vs_full_comparison_valid"])


if __name__ == "__main__":
    unittest.main()
