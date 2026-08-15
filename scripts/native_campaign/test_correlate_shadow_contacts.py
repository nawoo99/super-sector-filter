import json
import os
import tempfile
import unittest

from correlate_shadow_contacts import correlate


class ShadowContactCorrelationTest(unittest.TestCase):
    def test_matches_prediction_and_keeps_unmatched_counts(self):
        stack = """\
[fsm] [WARN] [1000000000.000] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=APPENDED_BACKUP status=OCCUPIED gen=2 map=3 from_tt=0.100 collision_tt=0.600
[fsm] [WARN] [1000000010.000] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=EXP status=OCCUPIED gen=3 map=4 from_tt=0.000 collision_tt=1.000
"""
        monitor = {"contact_events": [
            {"kind": "static_pcd", "epoch_s": 1000000000.55},
            {"kind": "live_cloud", "epoch_s": 1000000020.0},
        ]}
        stack_handle, stack_path = tempfile.mkstemp(text=True)
        json_handle, json_path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(stack_handle, "w") as stream:
                stream.write(stack)
            with os.fdopen(json_handle, "w") as stream:
                json.dump(monitor, stream)
            result = correlate(stack_path, json_path)
        finally:
            os.unlink(stack_path)
            os.unlink(json_path)
        self.assertEqual(result["shadow_contacts_with_prior_unsafe"], 1)
        self.assertEqual(result["shadow_contacts_without_prior_unsafe"], 1)
        self.assertEqual(result["shadow_geometric_unsafe_followed_by_contact"], 1)
        self.assertEqual(result["shadow_geometric_unsafe_not_followed_by_contact"], 1)
        self.assertAlmostEqual(result["shadow_nearest_prediction_error_s"], 0.05)
        self.assertEqual(result["shadow_correlated_segments"], ["APPENDED_BACKUP"])


if __name__ == "__main__":
    unittest.main()
