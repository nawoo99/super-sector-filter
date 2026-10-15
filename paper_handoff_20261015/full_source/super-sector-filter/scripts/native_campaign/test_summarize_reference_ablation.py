#!/usr/bin/env python3
import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import summarize_reference_ablation as summary  # noqa: E402


class ReferenceAblationSummaryTest(unittest.TestCase):
    def make_raw_row(
        self,
        mode,
        run,
        *,
        success=True,
        run_valid=True,
        goal_messages=1,
        center_distance=0.30,
        mission_time=10.0,
        path_length=100.0,
        fsm_cpu=50.0,
        position_command_messages=None,
        trajectory_flag2_messages=None,
        first_trajectory_flag2_s=None,
        max_position_command_gap_s=None,
    ):
        row = {field: "" for field in summary.REQUIRED_COLUMNS}
        contact_015 = center_distance < 0.15
        contact_020 = center_distance < 0.20
        contact_025 = center_distance < 0.25
        row.update(
            {
                "map": "seed11",
                "run": str(run),
                "mode": mode,
                "experiment_profile": mode,
                "success": str(success),
                "run_valid": str(run_valid),
                "monitor_type": "odom_static_pcd_swept_segment",
                "live_cloud_enabled": "False",
                "goal_messages": str(goal_messages),
                "n_waypoints": "1",
                "static_pcd_contact_r015": str(contact_015),
                "static_pcd_contact_r020": str(contact_020),
                "static_pcd_contact_r025": str(contact_025),
                "static_pcd_min_distance_m": str(center_distance),
                "static_pcd_clearance_m": str(center_distance - 0.20),
                "mission_time_s": str(mission_time),
                "path_length_m": str(path_length),
                "fsm_cpu_pct": str(fsm_cpu),
                "monitor_flight_cpu_pct": "7.0",
                "pts_mean": "65000",
                "total_ms_mean": "12.0",
                "raycast_ms_mean": "5.0",
                "update_ms_mean": "7.0",
                "inflation_ms_mean": "3.0",
                "perf_row_start": "10",
                "perf_row_end": "110",
                "position_command_messages": (
                    "" if position_command_messages is None
                    else str(position_command_messages)
                ),
                "trajectory_flag2_messages": (
                    "" if trajectory_flag2_messages is None
                    else str(trajectory_flag2_messages)
                ),
                "first_trajectory_flag2_s": (
                    "" if first_trajectory_flag2_s is None
                    else str(first_trajectory_flag2_s)
                ),
                "max_position_command_gap_s": (
                    "" if max_position_command_gap_s is None
                    else str(max_position_command_gap_s)
                ),
            }
        )
        return row

    def write_campaign(self, path, rows, *, omit=(), include_observability=False):
        fieldnames = set(summary.REQUIRED_COLUMNS) - set(omit)
        if include_observability:
            fieldnames.update(summary.COMPATIBLE_OPTIONAL_FLOAT_COLUMNS)
            fieldnames.update(summary.COMPATIBLE_OPTIONAL_INT_COLUMNS)
        fieldnames = sorted(fieldnames)
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def build_balanced_rows(self):
        repeat = "raw_oneway_repeat"
        once = "raw_oneway_once"
        by_run = {
            1: (
                self.make_raw_row(repeat, 1, goal_messages=38, center_distance=0.30,
                                  mission_time=10.0),
                self.make_raw_row(once, 1, center_distance=0.18, mission_time=8.0),
            ),
            2: (
                self.make_raw_row(once, 2, center_distance=0.30, mission_time=9.0),
                self.make_raw_row(repeat, 2, goal_messages=39, center_distance=0.18,
                                  mission_time=10.0),
            ),
            3: (
                self.make_raw_row(repeat, 3, goal_messages=37, center_distance=0.30,
                                  mission_time=11.0),
                self.make_raw_row(once, 3, center_distance=0.30, mission_time=8.0),
            ),
            4: (
                self.make_raw_row(once, 4, center_distance=0.18, mission_time=10.0),
                self.make_raw_row(repeat, 4, goal_messages=40, center_distance=0.18,
                                  mission_time=10.0),
            ),
        }
        return [row for run in sorted(by_run) for row in by_run[run]]

    def test_type7_quantile_and_mcnemar(self):
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(summary.type7_quantile(values, 0.25), 1.75)
        self.assertEqual(summary.type7_quantile(values, 0.50), 2.5)
        self.assertEqual(summary.type7_quantile(values, 0.75), 3.25)
        self.assertEqual(summary.type7_quantile([7.0], 0.25), 7.0)
        self.assertAlmostEqual(summary.mcnemar_exact(0, 4), 0.125)
        self.assertEqual(summary.mcnemar_exact(0, 0), 1.0)

    def test_mode_summary_and_balanced_pair_effects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "goal_ab.csv"
            self.write_campaign(path, self.build_balanced_rows())
            rows = summary.load_campaign(summary.CampaignSpec("goal_ab", path))

        mode_rows = summary.build_mode_summary(rows)
        by_mode = {row["mode"]: row for row in mode_rows}
        self.assertEqual(by_mode["raw_oneway_repeat"]["n_valid"], 4)
        self.assertEqual(by_mode["raw_oneway_repeat"]["goal_expected_n"], 4)
        self.assertEqual(by_mode["raw_oneway_once"]["goal_expected_n"], 4)
        self.assertEqual(by_mode["raw_oneway_repeat"]["contact_r020_n"], 2)
        self.assertEqual(by_mode["raw_oneway_once"]["contact_r020_n"], 2)

        continuous, binary, warnings = summary.build_paired_summaries(rows)
        self.assertEqual(warnings, [])
        time_row = next(row for row in continuous if row["metric"] == "mission_time_s")
        self.assertEqual(time_row["n_AB_present"], 2)
        self.assertEqual(time_row["n_BA_present"], 2)
        self.assertTrue(time_row["order_balanced"])
        self.assertAlmostEqual(time_row["delta_median"], -1.5)
        self.assertAlmostEqual(time_row["delta_q1"], -2.25)
        self.assertAlmostEqual(time_row["delta_q3"], -0.75)
        self.assertAlmostEqual(time_row["delta_AB_median"], -2.5)
        self.assertAlmostEqual(time_row["delta_BA_median"], -0.5)
        self.assertAlmostEqual(time_row["order_interaction"], -2.0)
        self.assertAlmostEqual(time_row["approx_order_effect"], -1.0)

        contact_row = next(row for row in binary if row["metric"] == "contact_r020")
        self.assertEqual(contact_row["all_neither"], 1)
        self.assertEqual(contact_row["all_a_only"], 1)
        self.assertEqual(contact_row["all_b_only"], 1)
        self.assertEqual(contact_row["all_both"], 1)
        self.assertEqual(contact_row["all_risk_difference"], 0.0)
        self.assertEqual(contact_row["all_mcnemar_p"], 1.0)

    def test_missing_new_monitor_cpu_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "old_schema.csv"
            self.write_campaign(
                path,
                [self.make_raw_row("raw_oneway_once", 1)],
                omit={"monitor_flight_cpu_pct"},
            )
            with self.assertRaisesRegex(
                summary.ValidationError, "monitor_flight_cpu_pct"
            ):
                summary.load_campaign(summary.CampaignSpec("old", path))

    def test_guarded_contrast_and_command_observability(self):
        ready = "raw_oneway_ready"
        guarded = "raw_oneway_guarded"
        rows = [
            self.make_raw_row(
                ready,
                1,
                position_command_messages=1000,
                trajectory_flag2_messages=0,
                max_position_command_gap_s=0.012,
            ),
            self.make_raw_row(
                guarded,
                1,
                position_command_messages=990,
                trajectory_flag2_messages=25,
                first_trajectory_flag2_s=7.5,
                max_position_command_gap_s=0.014,
            ),
            self.make_raw_row(
                guarded,
                2,
                position_command_messages=980,
                trajectory_flag2_messages=15,
                first_trajectory_flag2_s=8.0,
                max_position_command_gap_s=0.016,
            ),
            self.make_raw_row(
                ready,
                2,
                position_command_messages=1000,
                trajectory_flag2_messages=0,
                max_position_command_gap_s=0.012,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "guarded_ab.csv"
            self.write_campaign(path, rows, include_observability=True)
            parsed = summary.load_campaign(
                summary.CampaignSpec("guarded_ab", path)
            )

        mode_rows = summary.build_mode_summary(parsed)
        guarded_mode = next(row for row in mode_rows if row["mode"] == guarded)
        self.assertEqual(guarded_mode["trajectory_flag2_messages_n"], 2)
        self.assertEqual(guarded_mode["trajectory_flag2_messages_median"], 20.0)
        self.assertEqual(guarded_mode["first_trajectory_flag2_s_n"], 2)

        continuous, _binary, warnings = summary.build_paired_summaries(parsed)
        self.assertEqual(warnings, [])
        flag2 = next(
            row for row in continuous
            if row["contrast"] == "guarded_minus_ready"
            and row["metric"] == "trajectory_flag2_messages"
        )
        self.assertEqual(flag2["n_AB_present"], 1)
        self.assertEqual(flag2["n_BA_present"], 1)
        self.assertTrue(flag2["order_balanced"])
        self.assertEqual(flag2["delta_median"], 20.0)

    def test_main_writes_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "goal_ab.csv"
            prefix = root / "summary"
            self.write_campaign(input_path, self.build_balanced_rows())
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = summary.main(
                    [
                        "--campaign",
                        f"goal_ab={input_path}",
                        "--out-prefix",
                        str(prefix),
                    ]
                )
            self.assertEqual(exit_code, 0)
            mode_path, continuous_path, binary_path = summary.output_paths(prefix)
            for path in (mode_path, continuous_path, binary_path):
                self.assertTrue(path.is_file())
                with path.open(newline="") as stream:
                    self.assertGreater(len(list(csv.DictReader(stream))), 0)

    def test_invalid_boolean_and_non_nested_contacts_are_rejected(self):
        with self.assertRaises(summary.ValidationError):
            summary.parse_required_bool("yes", "run_valid", "test")

        row = self.make_raw_row("raw_oneway_once", 1)
        row["static_pcd_contact_r015"] = "True"
        row["static_pcd_contact_r020"] = "False"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad_contact.csv"
            self.write_campaign(path, [row])
            with self.assertRaisesRegex(summary.ValidationError, "not nested"):
                summary.load_campaign(summary.CampaignSpec("bad", path))


if __name__ == "__main__":
    unittest.main()
