import unittest
import summarize_cpu_attribution as s


class AttributionTest(unittest.TestCase):
    def test_required_scopes_follow_actual_subscriptions(self):
        self.assertNotIn('frontend_map_ack', s.required_stages('sector'))
        self.assertIn('frontend_map_ack', s.required_stages('adaptive'))
        self.assertNotIn('frontend_cloud', s.required_stages('full'))
        for mode in ('sector', 'adaptive'):
            self.assertIn('frontend_cloud', s.required_stages(mode))

    def test_exclusive_only_and_unknown_retained(self):
        rows = [dict(stage=name, exclusive_cpu_core_s=cpu, inclusive_cpu_core_s=999)
                for name, cpu in [('sim_render_callback', 1), ('frontend_acquisition', 2),
                                  ('frontend_stats', 3), ('new_unknown', 4)]]
        result = s.group(rows)
        self.assertEqual(sum(result.values()), 10)
        self.assertEqual(result['autonomy_measured_subtotal'], 2)
        self.assertEqual(result['unclassified_measured'], 4)

    def test_invalid_or_duplicate_rejected(self):
        for value in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                s.group([dict(stage='map_cloud_enqueue', exclusive_cpu_core_s=value)])
        with self.assertRaises(ValueError):
            s.group([dict(stage='map_cloud_enqueue', exclusive_cpu_core_s=1)] * 2)


if __name__ == '__main__':
    unittest.main()
