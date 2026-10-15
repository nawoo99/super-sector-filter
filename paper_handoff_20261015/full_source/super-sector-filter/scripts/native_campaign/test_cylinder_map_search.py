import unittest

import cylinder_map_search as search
from analyze_cylinder_only_stress_full_gate import contact_free, quality_valid


class MapOnlySearchTests(unittest.TestCase):
    def test_fixed_runtime_policy(self):
        self.assertEqual(search.OPTIONS["filter_half_angle_deg"],45)
        self.assertEqual(search.OPTIONS["attempt_max"],1)
        self.assertEqual(search.OPTIONS["adaptive_risk_body_clearance_m"],.2)
        self.assertEqual(search.OPTIONS["loop_timeout_override"],180)
        self.assertEqual(search.PROFILES["full"],
                         "static_seedmaps_guard_viability_tight_v7.yaml")

    def test_exact_cylinder_clearance_not_bounding_cluster(self):
        c = search.geometry.Cylinder(19.5,24.35,.4,"closure")
        self.assertAlmostEqual(search.clearance([(20.5,23),(20.5,26)],[c]),.4)
        self.assertAlmostEqual(search.clearance([(19.5,23),(19.5,26)],[c]),-.6)

    def test_old_inbound_crossing_rejected_by_clearance(self):
        old = search.geometry.structural_cylinders(.65)
        self.assertLess(search.clearance([(0,0),(24,24)],old),0)

    def test_quality_gate_fails_closed(self):
        self.assertFalse(contact_free({}))
        self.assertFalse(quality_valid({}))
        row = dict(run_valid=True,resource_valid=True,infrastructure_failure=False,
                   speed_limit_valid=True,attempt_count=1,retry_count=0,
                   static_pcd_collisions=0,safety_collisions=0)
        self.assertTrue(quality_valid(row))
        self.assertTrue(contact_free(row))
        row["static_pcd_collisions"]=1
        self.assertFalse(contact_free(row))


if __name__=="__main__": unittest.main()
