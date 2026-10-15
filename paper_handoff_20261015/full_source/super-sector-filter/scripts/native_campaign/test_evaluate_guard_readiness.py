import csv
import os
import tempfile
import unittest

from evaluate_guard_readiness import evaluate


class GuardReadinessTest(unittest.TestCase):
    def test_fails_closed_on_insufficient_dense_evidence(self):
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "shadow_contact_events_with_epoch",
                    "shadow_contacts_with_prior_unsafe", "shadow_map_race",
                ])
                writer.writeheader()
                writer.writerow({
                    "shadow_contact_events_with_epoch": 1,
                    "shadow_contacts_with_prior_unsafe": 1,
                    "shadow_map_race": 0,
                })
            result = evaluate({
                "n_pairs": 4,
                "delta_fsm_cpu_pct_median": 2.0,
                "control_mission_time_s_mean": 20.0,
                "delta_mission_time_s_median": 0.5,
            }, [path])
        finally:
            os.unlink(path)
        self.assertFalse(result["ready_for_enforcement"])
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertIn("dense_contact_events", failed)
        self.assertIn("dense_paired_ab_available", failed)

    def test_fails_on_dense_completion_regression(self):
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "shadow_contact_events_with_epoch",
                    "shadow_contacts_with_prior_unsafe", "shadow_map_race",
                ])
                writer.writeheader()
                writer.writerow({
                    "shadow_contact_events_with_epoch": 20,
                    "shadow_contacts_with_prior_unsafe": 20,
                    "shadow_map_race": 0,
                })
            result = evaluate({
                "n_pairs": 4,
                "delta_fsm_cpu_pct_median": 2.0,
                "control_mission_time_s_mean": 20.0,
                "delta_mission_time_s_median": 0.5,
            }, [path], {
                "n_pairs": 10,
                "delta_fsm_cpu_pct_median": 2.0,
                "control_successes": 10,
                "shadow_successes": 8,
            })
        finally:
            os.unlink(path)
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertIn("dense_shadow_all_complete", failed)
        self.assertIn("dense_completion_parity", failed)

    def test_fails_when_most_shadow_candidates_would_be_rejected(self):
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "shadow_contact_events_with_epoch",
                    "shadow_contacts_with_prior_unsafe", "shadow_map_race",
                    "shadow_safe_candidates", "shadow_validated_candidates",
                ])
                writer.writeheader()
                writer.writerow({
                    "shadow_contact_events_with_epoch": 20,
                    "shadow_contacts_with_prior_unsafe": 20,
                    "shadow_map_race": 0,
                    "shadow_safe_candidates": 40,
                    "shadow_validated_candidates": 100,
                })
            result = evaluate({
                "n_pairs": 4,
                "delta_fsm_cpu_pct_median": 1.0,
                "control_mission_time_s_mean": 30.0,
                "delta_mission_time_s_median": 0.1,
            }, [path], {
                "n_pairs": 10,
                "delta_fsm_cpu_pct_median": 1.0,
                "control_successes": 10,
                "shadow_successes": 10,
            })
        finally:
            os.unlink(path)
        safe_check = next(
            check for check in result["checks"]
            if check["name"] == "dense_safe_candidate_fraction"
        )
        self.assertFalse(safe_check["passed"])
        self.assertFalse(result["ready_for_enforcement"])


if __name__ == "__main__":
    unittest.main()
