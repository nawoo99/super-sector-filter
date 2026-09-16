#!/usr/bin/env python3
"""Freeze five physical Normal maps and five geometry-only cylinder probes.

No ROS flights, outcome-based map selection, planner edits or historical data
pooling. Offline paths certify free space only and are never mission inputs.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

import gen_cylinder_only_stress as g
from cylinder_forest_geometry import paths

ROOT = Path(__file__).resolve().parents[2]
MIRROR = ROOT / 'super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim'
SEEDS = (1, 3, 5, 7, 9)
# Frozen without flight outcomes. These are separated posts, not touching rows.
NE = ((20.4, 24.0), (17.0, 24.8), (13.6, 23.2))
NW = ((-24.0, 20.4), (-24.8, 17.0), (-23.2, 13.6))


def geometry_stats(cylinders):
    nearest = [min(g.surface_gap(c, d) for j, d in enumerate(cylinders) if j != i)
               for i, c in enumerate(cylinders)]
    return dict(count=len(cylinders), diameter_m=2*cylinders[0].radius,
        height_m=g.OBSTACLE_HEIGHT_M, min_surface_gap_m=min(nearest),
        mean_nearest_surface_gap_m=sum(nearest)/len(nearest))


def proposal(seed, radius, corners):
    structural = [g.Cylinder(x, y, radius, 'corner_post') for x, y in corners]
    background = []
    for item in g.load_source(seed, radius):
        if (not g.protected_location(item) and g.route_surface_distance(item) > 2.0
                and not g.conflicts(item, structural + background, 1.0)):
            background.append(item)
    background = g.refill_background(background, structural, radius,
                                      2026091600 + seed, 410-len(structural))
    return structural + background


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    names = [f'c19_cyl_probe_s{i}' for i in range(1, 6)]
    for name in names:
        if any(p.exists() for p in (g.PCD_DIR / f'{name}.pcd', g.CONFIG_DIR / f'{name}.yaml')):
            raise RuntimeError('Refusing to overwrite a previous map: ' + name)
    spec = dict(schema='c19-map-suite-geometry-v1', normal_seeds=SEEDS,
        normal_choice='First physical seed in each historical diameter tier, not best-performing seed',
        stress_names=names, radius_tiers_m=g.RADIUS_TIERS_M, cylinder_count=410,
        stress_min_surface_gap_m=1.0, background_route_clearance_m=2.0,
        ne_posts=NE, nw_posts=NW, s1_to_s3='NE posts only', s4_to_s5='NE and NW posts',
        source_background_seeds=SEEDS, background_not_unseen=True,
        planner_change=False, sensor_fault=False, moving_obstacle=False,
        cylinder_only=True, final_performance_qualified=False, flight_runs=0,
        no_performance_based_selection=True, no_historical_results_pooling=True,
        waypoint_file='loop24.txt', max_velocity_m_s=7, sector_half_angle_deg=45,
        lidar_hz=10, control_hz=100, generator_sha256=g.sha256(Path(__file__)))
    (output / 'preregistration.json').write_text(json.dumps(spec, indent=2)+'\n')
    rows = []
    for index, (seed, radius) in enumerate(zip(SEEDS, g.RADIUS_TIERS_M), 1):
        normal = g.load_source(seed, radius)
        normal_assets = [g.SCRIPT_DIR/f'seed{seed}_static.csv', g.PCD_DIR/f'seed{seed}.pcd',
                         g.CONFIG_DIR/f'seed{seed}.yaml']
        rows.append(dict(group='Normal', display=f'N{index}', map=f'seed{seed}',
            **geometry_stats(normal), assets={str(p):g.sha256(p) for p in normal_assets},
            status='physical map frozen; current-version all-map flight campaign pending'))
        name = names[index-1]
        cylinders = proposal(seed, radius, NE if index <= 3 else NE+NW)
        stats = geometry_stats(cylinders)
        if stats['count'] != 410 or stats['min_surface_gap_m'] < 1.0-1e-9:
            raise RuntimeError('Geometry contract failed: '+name)
        witness = paths(cylinders)
        # Check every exact compressed segment, not just lattice endpoints.
        clearance = min(g.point_segment_distance(c[:2], a, b)-c.radius-.20
            for leg in witness for a, b in zip(leg, leg[1:]) for c in cylinders)
        if clearance < .35:
            raise RuntimeError('Offline route lacks body clearance: '+name)
        csv_path = output / f'{name}_cylinders.csv'
        pcd_path, config_path = g.PCD_DIR/f'{name}.pcd', g.CONFIG_DIR/f'{name}.yaml'
        g.write_cylinder_csv(csv_path, cylinders)
        points = g.write_pcd(pcd_path, cylinders)
        g.write_config(config_path, name)
        for original, target in ((pcd_path, MIRROR/'pcd/seed_maps'/pcd_path.name),
                                 (config_path, MIRROR/'config'/config_path.name)):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise RuntimeError('Refusing to overwrite existing mirror: '+str(target))
            shutil.copy2(original, target)
        rows.append(dict(group='Stress', display=f'S{index}', map=name, **stats,
            structural_posts=3 if index <= 3 else 6, point_count=points,
            geometry_route_body_clearance_m=clearance, geometric_routes_xy=witness,
            offline_route_not_supplied_to_planner=True,
            assets={str(p):g.sha256(p) for p in (csv_path,pcd_path,config_path)},
            status='geometry-only exploratory candidate; zero flight validation'))
        print(name, 'geometry PASS', stats, 'clearance', clearance, flush=True)
    (output/'manifest.json').write_text(json.dumps(dict(spec=spec,maps=rows),indent=2)+'\n')
    lines = ['# C19 physical map suite (geometry frozen, not performance qualified)', '',
        '| Map | Physical map | Cylinders | Diameter m | Min surface gap m | Mean nearest surface gap m |',
        '|---|---|---:|---:|---:|---:|']
    for row in sorted(rows, key=lambda x:(x['group'],x['display'])):
        lines.append(f"| {row['display']} | {row['map']} | {row['count']} | "
            f"{row['diameter_m']:.2f} | {row['min_surface_gap_m']:.3f} | "
            f"{row['mean_nearest_surface_gap_m']:.3f} |")
    lines += ['', 'All cylinders are static and 3 m high. Gap is surface-to-surface, '
        'not center spacing. N1–N5 are seed1/3/5/7/9, not the old paired-seed aggregates. '
        'S1–S5 use separated corner posts with permanent background; no wall primitives, '
        'dropout or dynamic obstacles. Old rejected maps and all their outcomes remain archived.', '',
        'Stress layouts are frozen BEFORE any current-policy flight. Geometric free-space '
        'routes do not prove dynamic feasibility, Full/Adaptive completion, or Sector disadvantage. '
        'Next step must retain all failures and keep any map redesign in a separate exploratory version. '
        'Neither these source backgrounds nor the current algorithm are unseen generalization evidence.', '']
    (output/'README.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
