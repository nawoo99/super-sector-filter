#!/usr/bin/env python3
"""Offline map-admission and narrowly scoped legacy-adapter regression tests."""
import ast
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import gapfree_campaign_support as support


class GeometryTests(unittest.TestCase):
    def fixture(self, folder, rows, fields='x y z intensity', points=None):
        n = len(rows) if points is None else points
        cols = len(fields.split())
        path = Path(folder) / 'map.pcd'
        path.write_text(f'FIELDS {fields}\nSIZE ' + ' '.join(['4'] * cols)
                        + '\nTYPE ' + ' '.join(['F'] * cols)
                        + '\nCOUNT ' + ' '.join(['1'] * cols)
                        + f'\nWIDTH {n}\nHEIGHT 1\nPOINTS {n}\nDATA ascii\n'
                        + '\n'.join(rows) + '\n')
        return path

    def test_canonical_xyzi_bytes_have_homogeneous_one_and_padding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.fixture(temp, ['1 2 3 1', '-4 5 6 1'])
            actual = support.canonical_geometry(path)
        expected = b''.join(struct.pack('<5f12x', *values)
                            for values in ((1, 2, 3, 1, 1), (-4, 5, 6, 1, 1)))
        self.assertEqual(actual['sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(actual['bytes'], 64)

    def test_canonical_xyz_missing_intensity_is_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.fixture(temp, ['1 2 3'], fields='x y z')
            actual = support.canonical_geometry(path)
        self.assertEqual(actual['sha256'], hashlib.sha256(struct.pack('<5f12x', 1, 2, 3, 1, 0)).hexdigest())

    def test_invalid_count_and_nonfinite_are_rejected(self):
        for rows, count in ((['1 2 3 1'], 2), (['nan 2 3 1'], 1)):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                path = self.fixture(temp, rows, points=count)
                with self.assertRaises(ValueError):
                    support.canonical_geometry(path)

    def test_independent_seed1_transport_hash_matches_existing_contract(self):
        static = importlib.import_module('static_latched_preflight')
        actual = support.canonical_geometry(support.PACKAGE / 'pcd/seed_maps/seed1.pcd')
        self.assertEqual(actual, static.EXPECTED_GEOMETRY)

    def test_exact_five_maps_admitted_and_legacy_geometry_preserved(self):
        static = importlib.import_module('static_latched_preflight')
        before = dict(static.MAP_GEOMETRIES)
        result = support.register_maps()
        self.assertTrue(result['valid'])
        self.assertFalse(result['transport_certified'])
        self.assertEqual(tuple(result['maps']), support.MAPS)
        for name, value in before.items():
            self.assertEqual(static.MAP_GEOMETRIES[name], value)
        for name in support.MAPS:
            context = result['maps'][name]
            self.assertEqual(context['geometry']['points'], 800730)
            self.assertEqual(context['geometry']['bytes'], 25623360)
            self.assertEqual(context['paths'][name + '_pcd'], support.PACKAGE / 'pcd/seed_maps' / (name + '.pcd'))

    def test_changed_manifest_fails_before_registration(self):
        with patch.object(support, 'sha256', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'manifest changed'):
                support.register_maps()


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.child = importlib.import_module('gapfree_cpu_compare')

    def test_profile_reference_requires_exact_map_manifest(self):
        fake = dict(valid=True, checks={'legacy': True}, acceptance_checks={'legacy': True})
        values = {key: 'expected' for key in self.child.MAP_MATCH_FIELDS}
        with patch.object(self.child.legacy, 'small_pool_profile_reference_audit', return_value=fake):
            mismatch = self.child.small_pool_profile_reference_audit(values, {}, {})
        self.assertFalse(mismatch['valid'])
        fake = dict(valid=True, checks={'legacy': True}, acceptance_checks={'legacy': True})
        with patch.object(self.child.legacy, 'small_pool_profile_reference_audit', return_value=fake):
            match = self.child.small_pool_profile_reference_audit(values, dict(values), {})
        self.assertTrue(match['valid'])

    def test_partial_observer_files_retained_without_native_row_or_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'result with spaces'
            scratch = Path(temp) / 'scratch'
            scratch.mkdir()
            source = scratch / 'gapfree_d1_m01_run1_full.attempt1.odometry.csv'
            source.write_text('partial odometry\n')
            campaign = SimpleNamespace(TMPDIR=str(scratch))
            self.child.preserve_supplemental_artifacts(root, campaign)
            self.assertEqual((root / 'artifacts' / source.name).read_text(), 'partial odometry\n')
            self.assertTrue(source.exists())
            # A second finalization must preserve an already-copied observation.
            self.child.preserve_supplemental_artifacts(root, campaign)
            self.assertTrue(source.exists())

    def test_preservation_never_overwrites_conflicting_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'result'
            scratch = Path(temp) / 'scratch'
            scratch.mkdir()
            source = scratch / 'gapfree_d1_m01_run1_full.attempt1.odometry.csv'
            source.write_text('new partial\n')
            (root / 'artifacts').mkdir(parents=True)
            target = root / 'artifacts' / source.name
            target.write_text('existing evidence\n')
            self.child.preserve_supplemental_artifacts(root, SimpleNamespace(TMPDIR=str(scratch)))
            self.assertEqual(target.read_text(), 'existing evidence\n')
            self.assertEqual(source.read_text(), 'new partial\n')

    def test_copied_main_changes_only_approved_admission_and_observer_bindings(self):
        baseline = support.LEGACY_CHILD.read_text()
        self.assertEqual(support.sha256(support.LEGACY_CHILD), support.LEGACY_CHILD_SHA256)
        original = baseline[baseline.index('def main():'):]
        replacements = (
            ('def main():\n', 'def main():\n    map_admission = register_maps()\n'),
            ("parser.add_argument('--map', choices=tuple(static_latched_preflight.MAP_GEOMETRIES), default='seed1')",
             "parser.add_argument('--map', choices=MAPS, default=MAPS[0])"),
            ('if args.guarded_demand_replan and not args.time_reference_folder:',
             'if args.guarded_demand_replan and not args.time_reference_folder and not args.mission_time_as_metric:'),
            ('campaign = diagnostic.search.campaign\n',
             "campaign = diagnostic.search.campaign\n    campaign.LOOP_MON = str(MONITOR)\n    campaign.TMPDIR = tempfile.mkdtemp(prefix='gapfree_n5_', dir='/tmp')\n    os.environ['GAPFREE_BASE_MONITOR'] = str(LEGACY_DIR / 'native_loop_monitor.py')\n"),
            ("Path(__file__).resolve().with_name('native_loop_monitor.py')", "LEGACY_DIR / 'native_loop_monitor.py'"),
            ("Path(__file__).resolve().with_name('message_intervals.py')", "LEGACY_DIR / 'message_intervals.py'"),
            ("                  runtime / 'mission_planner/data/loop24.txt',\n",
             "                  runtime / 'mission_planner/data/loop24.txt',\n"
             "                  runtime / 'mission_planner/launch/benchmark_seedmap.launch.py',\n"),
            ("                   sensor_planner_intra_process=args.compose,\n",
             "                   sensor_planner_intra_process=args.compose,\n"
             "                   observer_ready_before_mission=True,\n"),
            ('        asset_sha256=hashes, baseline_seconds=12,\n',
             '        asset_sha256=hashes, baseline_seconds=12,\n'
             '        observer_ready_before_mission=True,\n'
             '        observer_ready_definition=(\n'
             "            'gapfree observer recorded its first valid odometry sample before '\n"
             "            'waypoint_mission process creation'\n"
             '        ),\n'),
            ('    hashes = {str(p): event.sha(p) for p in sorted(files)}',
             "    files.update({MANIFEST, LEGACY_CHILD, Path(support.__file__).resolve(), MONITOR})\n    files.update(Path(path) for path in map_admission['assets_sha256'])\n    hashes = {str(p): event.sha(p) for p in sorted(files)}"),
            ('    plan = dict(\n',
             "    plan = dict(\n        gapfree_scratch_directory=campaign.TMPDIR,\n        gapfree_manifest_sha256=map_admission['manifest_sha256'],\n        gapfree_geometry=map_admission['maps'][args.map]['geometry'],\n        gapfree_adapter_baseline_sha256=support.LEGACY_CHILD_SHA256,\n"),
            ('                stream.flush()\n                if not quality_valid(row):',
             '                stream.flush()\n                solid_cylinder_audit = copy_supplemental_artifacts(root, args.map, args.run, mode, campaign)\n                if not quality_valid(row):'),
            ('                result = diagnostic.summarize(profiler, row)\n',
             "                result = diagnostic.summarize(profiler, row)\n                result['solid_cylinder_audit'] = solid_cylinder_audit\n"),
            ("                result['source_acquisition']['checks']['telemetry_map_scope']",
             "                result['source_acquisition']['checks']['solid_cylinder_observation_valid'] = (\n                    solid_cylinder_audit.get('audit_valid') is True)\n                result['source_acquisition']['checks']['telemetry_map_scope']"),
            ('        campaign.cleanup_active_process_groups()\n',
             '        campaign.cleanup_active_process_groups()\n        preserve_supplemental_artifacts(root, campaign)\n'),
        )
        for old, new in replacements:
            self.assertIn(old, original)
            original = original.replace(old, new, 1)
        actual = (SCRIPTS / 'gapfree_cpu_compare.py').read_text()
        actual = actual[actual.index('def main():'):]
        self.assertEqual(ast.dump(ast.parse(actual)), ast.dump(ast.parse(original)))


if __name__ == '__main__':
    unittest.main()
