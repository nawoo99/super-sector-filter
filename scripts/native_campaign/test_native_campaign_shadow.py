import os
import tempfile
import unittest

from native_campaign import parse_shadow_guard_log


class ShadowGuardLogTest(unittest.TestCase):
    def test_separates_geometry_from_map_races(self):
        lines = """\
[INFO] -- [TRAJ_GUARD_SHADOW_SAFE] phase=x gen=1 map=1 samples=5 range=[0,1] validation_ms=2.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=EXP status=VERSION_CHANGED gen=2 map=2 validation_ms=3.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=APPENDED_BACKUP status=OCCUPIED gen=3 map=2 validation_ms=4.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=EXP_TO_BACKUP_STITCH status=OUT_OF_MAP gen=4 map=2 validation_ms=5.000 action=observed_after_commit
[WARN] -- [TRAJ_GUARD_SHADOW_UNSAFE] phase=x segment=NOT_APPLICABLE status=MAP_NOT_COMMITTED gen=5 map=0 validation_ms=0.100 action=observed_after_commit
[INFO] -- [TRAJ_GUARD_SHADOW_SKIPPED] phase=x gen=6 reason=RATE_LIMIT since_last_ms=25.000 min_interval_ms=250.000 action=observed_after_commit
"""
        handle, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(lines)
            result = parse_shadow_guard_log(path)
        finally:
            os.unlink(path)

        self.assertEqual(result["shadow_safe_candidates"], 1)
        self.assertEqual(result["shadow_unsafe_candidates"], 4)
        self.assertEqual(result["shadow_skipped_candidates"], 1)
        self.assertEqual(result["shadow_validated_candidates"], 5)
        self.assertEqual(result["shadow_geometric_unsafe"], 2)
        self.assertEqual(result["shadow_map_race"], 1)
        self.assertEqual(result["shadow_other_indeterminate"], 1)
        self.assertEqual(result["shadow_unsafe_exp"], 0)
        self.assertEqual(result["shadow_unsafe_appended_backup"], 1)
        self.assertEqual(result["shadow_unsafe_stitch"], 1)
        self.assertAlmostEqual(result["shadow_validation_ms_mean"], 2.82)
        self.assertAlmostEqual(result["shadow_validation_ms_max"], 5.0)


if __name__ == "__main__":
    unittest.main()
