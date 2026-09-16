"""Read-only validation of the preregistered physical map suite."""
import csv
import json
from pathlib import Path
import unittest

import freeze_c19_map_suite as suite


class FrozenSuiteTest(unittest.TestCase):
    def test_all_ten_physical_maps_and_assets(self):
        root = suite.ROOT / 'results/c19_map_suite_20260916'
        manifest = json.loads((root / 'manifest.json').read_text())
        self.assertFalse(manifest['spec']['final_performance_qualified'])
        self.assertEqual(manifest['spec']['flight_runs'], 0)
        maps = manifest['maps']
        self.assertEqual(len(maps), 10)
        self.assertEqual(len({m['map'] for m in maps}), 10)
        self.assertEqual([m['map'] for m in maps if m['group']=='Normal'],
                         ['seed1', 'seed3', 'seed5', 'seed7', 'seed9'])
        for m in maps:
            self.assertEqual(m['count'], 410)
            self.assertGreaterEqual(m['min_surface_gap_m'], 1)
            for path, digest in m['assets'].items():
                self.assertEqual(suite.g.sha256(Path(path)), digest)
            if m['group'] == 'Stress':
                self.assertGreaterEqual(m['geometry_route_body_clearance_m'], .35)
                self.assertEqual(len(m['geometric_routes_xy']), 5)
                with (root / (m['map']+'_cylinders.csv')).open() as stream:
                    cylinders = [suite.g.Cylinder(float(r['x']),float(r['y']),float(r['r']),r['role'])
                                 for r in csv.DictReader(stream)]
                self.assertEqual(sum(c.role=='corner_post' for c in cylinders), m['structural_posts'])
                self.assertGreaterEqual(suite.geometry_stats(cylinders)['min_surface_gap_m'], 1)
                # Audit exact line segments against serialized analytic geometry.
                for leg in m['geometric_routes_xy']:
                    for a, b in zip(leg,leg[1:]):
                        self.assertGreaterEqual(min(suite.g.point_segment_distance(c[:2],a,b)-c.radius-.2
                                                    for c in cylinders), .35)
                for suffix, folder in (('.yaml','config'),('.pcd','pcd/seed_maps')):
                    actual = (suite.g.CONFIG_DIR if suffix=='.yaml' else suite.g.PCD_DIR)/(m['map']+suffix)
                    self.assertEqual(suite.g.sha256(actual),
                                     suite.g.sha256(suite.MIRROR/folder/actual.name))


if __name__ == '__main__':
    unittest.main()
