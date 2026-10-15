import csv
import os
import tempfile
import unittest

from summarize_shadow_ab import summarize


class ShadowAbSummaryTest(unittest.TestCase):
    def test_paired_delta_and_order(self):
        fields = [
            "map", "run", "mode", "success", "contact_event_count",
            "mission_time_s", "fsm_cpu_pct",
        ]
        rows = [
            {"map": "seed2", "run": "1", "mode": "full_control_v10",
             "success": "True", "contact_event_count": "0",
             "mission_time_s": "20", "fsm_cpu_pct": "80"},
            {"map": "seed2", "run": "1", "mode": "full_shadow_v10",
             "success": "True", "contact_event_count": "1",
             "mission_time_s": "22", "fsm_cpu_pct": "90"},
        ]
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            pair_rows, result = summarize(path)
        finally:
            os.unlink(path)
        self.assertEqual(result["n_pairs"], 1)
        self.assertEqual(result["delta_fsm_cpu_pct_mean"], 10.0)
        self.assertEqual(result["shadow_contacts"], 1)
        self.assertEqual(pair_rows[0]["order"], "control_shadow")


if __name__ == "__main__":
    unittest.main()
