#!/usr/bin/env python3
"""Query equivalence and opt-in no-flight real-cloud timing checks."""
import ast
import itertools
import json
import os
from pathlib import Path
import sys
import time
import unittest

import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
NATIVE_SCRIPTS = Path("/root/super-sector-filter/scripts/native_campaign")
sys.path.insert(0, str(NATIVE_SCRIPTS))
from ascii_pcd_xyz import load_ascii_pcd_xyz
from scenario7_repair_pcd_index import INDEX_POLICY, optimized_index_class


def legacy_class(loader=load_ascii_pcd_xyz):
    source = NATIVE_SCRIPTS / "native_loop_monitor.py"
    module = ast.parse(source.read_text(), filename=str(source))
    definition, = [node for node in module.body
                   if isinstance(node, ast.ClassDef) and node.name == "StaticPcdIndex"]
    namespace = dict(np=np, itertools=itertools, load_ascii_pcd_xyz=loader)
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["StaticPcdIndex"]


class ExactIndexTest(unittest.TestCase):
    def assert_nearest_equal(self, old, new, point, radius=None):
        left = old.nearest(point, max_distance_m=radius)
        right = new.nearest(point, max_distance_m=radius)
        self.assertEqual(left[0], right[0])
        if left[1] is None:
            self.assertIsNone(right[1])
        else:
            np.testing.assert_array_equal(left[1], right[1])

    def test_random_negative_boundary_and_tie_queries(self):
        rng = np.random.default_rng(9026)
        points = np.concatenate((rng.uniform(-3, 3, (2500, 3)),
                                 [[-1, 0, 0], [1, 0, 0], [0, -.5, 0],
                                  [0, .5, 0], [0, 0, -.2], [0, 0, .2],
                                  [0, 0, .2], [.5, .5, .5]])).astype(np.float32)
        base = legacy_class(lambda _: points.copy())
        old, new = base(None), optimized_index_class(base)(None)
        queries = [np.asarray(point, dtype=np.float32) for point in
                   [[0, 0, 0], [.5, .5, .5], [-.5, -.5, -.5], [5, 0, 0],
                    *rng.uniform(-3, 3, (12, 3))]]
        for point in queries:
            self.assert_nearest_equal(old, new, point)
            for radius in [.0, .2, .5, .51, 1., 5.]:
                with self.subTest(point=point, radius=radius):
                    np.testing.assert_array_equal(old.nearby_points(point, radius),
                                                  new.nearby_points(point, radius))
                    self.assert_nearest_equal(old, new, point, radius)

    def test_sparse_far_origin_and_global_nearest_ties(self):
        points = np.array([[5, 0, 1.5], [-5, 0, 1.5], [0, 5, 1.5],
                           [0, -5, 1.5], [6, 0, 1.5]], dtype=np.float32)
        base = legacy_class(lambda _: points.copy())
        old, new = base(None), optimized_index_class(base)(None)
        for point in [[0, 0, 1.5], [.125, -.125, 1.5], [-.5, -.5, 1.5]]:
            point = np.asarray(point, dtype=np.float32)
            self.assert_nearest_equal(old, new, point)
            for radius in [.2, 4.99, 5., 5.01]:
                self.assert_nearest_equal(old, new, point, radius)

    @unittest.skipUnless(os.environ.get("SCENARIO7_INDEX_CLOUD_TESTS") == "1",
                         "Set SCENARIO7_INDEX_CLOUD_TESTS=1 for real-cloud replay/benchmark")
    def test_real_clouds_and_startup_query_timing(self):
        base = legacy_class()
        report = {"index_policy": INDEX_POLICY, "flights": 0, "clouds": {}}
        for name in ["urban_blocks_u01", "seed1"]:
            path = PACKAGE / "pcd/seed_maps" / (name + ".pcd")
            old, new = base(path), optimized_index_class(base)(path)
            if name == "urban_blocks_u01":
                queries = [[0., 0., 1.5], [-.025567, .077205, 1.560773],
                           [-1.94266, 1.800371, 2.120715], [-3.607745, 3.372095, 2.446942],
                           [-3.624506, 3.374678, 2.42528]]
            else:
                queries = [[0., 0., 1.5], [1.5, 2.5, 1.5], [12., 12., 1.5],
                           [-12., 12., 1.5], [12., -12., 1.5]]
            comparisons = 0
            for point in queries:
                point = np.asarray(point, dtype=np.float32)
                distance, _ = old.nearest(point)
                for radius in [None, .2, .5, distance, max(.2, distance - .01)]:
                    self.assert_nearest_equal(old, new, point, radius)
                    comparisons += 1
            position = np.array([0., 0., 1.5], dtype=np.float32)
            radius, _ = old.nearest(position)
            times = {}
            for label, index in [("legacy", old), ("repair", new)]:
                index.nearest(position, max_distance_m=radius)
                samples = []
                for _ in range(20):
                    start = time.perf_counter_ns()
                    index.nearest(position, max_distance_m=radius)
                    samples.append((time.perf_counter_ns() - start) / 1e6)
                times[label] = dict(median_ms=float(np.median(samples)),
                                    max_ms=max(samples), samples=len(samples))
            report["clouds"][name] = dict(points=len(old.points), comparisons=comparisons,
                                           origin_nearest_m=radius, query_times=times)
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
