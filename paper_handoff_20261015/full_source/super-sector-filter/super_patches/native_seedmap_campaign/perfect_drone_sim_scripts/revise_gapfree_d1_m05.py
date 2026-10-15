#!/usr/bin/env python3
"""Create G5-R2 without modifying the frozen G5 geometry or its results.

This is an explicitly outcome-informed development-map revision.  Cylinder 199,
which intersected the Adaptive preflight trajectory, is relocated to a
deterministic geometry-only feasible location.  Count, diameter, height, field,
all simulator parameters, and the other four maps are unchanged.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil

import gen_gapfree_d1_maps as base


REPO = Path('/root/super-sector-filter')
OLD_MANIFEST = REPO/'results/gapfree_d1_maps_20260918/manifest.json'
OLD_MANIFEST_SHA256 = 'e3e2ea0dcca7b74f687094a90692953ece56247d2f45b5eda46dc2fc062b7f73'
OUTPUT = REPO/'results/gapfree_d1_maps_20260921_r2'
OLD_NAME = 'gapfree_d1_m05'
NEW_NAME = 'gapfree_d1_m05r2'
RELOCATED_INDEX = 199
EXPECTED_OLD = (0.931831, 1.726500, 0.5, 'uniform_disjoint')
NEW_CENTER = (4.25, 29.50)
ROLE = 'relocated_after_adaptive_preflight_contact'


def read_cylinders(path):
    with Path(path).open(newline='') as stream:
        return [base.geometry.Cylinder(float(row['x']), float(row['y']),
                                       float(row['r']), row['role'])
                for row in csv.DictReader(stream)]


def revised_geometry():
    source = base.PACKAGE/'pcd/seed_maps'/f'{OLD_NAME}_cylinders.csv'
    cylinders = read_cylinders(source)
    old = cylinders[RELOCATED_INDEX]
    if tuple(old) != EXPECTED_OLD:
        raise ValueError(f'Frozen G5 cylinder {RELOCATED_INDEX} changed: {old!r}')
    cylinders[RELOCATED_INDEX] = base.geometry.Cylinder(
        NEW_CENTER[0], NEW_CENTER[1], base.RADIUS_M, ROLE)
    minimum_gap = base.validate_cylinders(cylinders)
    routes = base.connectivity.paths(cylinders)
    route = base.route_audit(cylinders, routes)
    stats = base.statistics(cylinders)
    return cylinders, routes, route, stats, minimum_gap


def target_paths(name):
    source = (
        base.PACKAGE/'config'/f'{name}.yaml',
        base.PACKAGE/'pcd/seed_maps'/f'{name}.pcd',
        base.PACKAGE/'pcd/seed_maps'/f'{name}_cylinders.csv',
    )
    mirror = tuple(base.mirror_target(path) for path in source)
    return source, mirror, base.INSTALL_CONFIG/f'{name}.yaml'


def generate(output=OUTPUT):
    output = Path(output).resolve()
    if base.geometry.sha256(OLD_MANIFEST) != OLD_MANIFEST_SHA256:
        raise ValueError('Frozen parent G1-G5 manifest changed')
    parent = json.loads(OLD_MANIFEST.read_text())
    if tuple(row['map'] for row in parent['maps']) != tuple(
            f'gapfree_d1_m{i:02d}' for i in range(1, 6)):
        raise ValueError('Unexpected parent suite membership')
    if output.exists():
        raise ValueError('Output already exists; never overwrite a map revision')
    source, mirror, install_config = target_paths(NEW_NAME)
    if any(path.exists() for path in (*source, *mirror, install_config)):
        raise ValueError('Refusing an existing G5-R2 asset')

    cylinders, routes, route, stats, minimum_gap = revised_geometry()
    output.mkdir(parents=True, exist_ok=False)
    config_path, pcd_path, csv_path = source
    base.geometry.write_cylinder_csv(csv_path, cylinders)
    point_count = base.geometry.write_pcd(pcd_path, cylinders)
    old = 'pcd_name: "seed_maps/seed1.pcd"'
    config = (base.PACKAGE/'config/seed1.yaml').read_text()
    if config.count(old) != 1:
        raise ValueError('Unexpected base configuration')
    config_path.write_text(config.replace(old, f'pcd_name: "seed_maps/{NEW_NAME}.pcd"'))
    for origin, target in zip(source, mirror):
        base.copy_exclusive(origin, target)
    base.copy_exclusive(config_path, install_config)
    base.copy_exclusive(csv_path, output/csv_path.name)

    nearest = stats['nearest_surface_gaps_m']
    with (output/f'{NEW_NAME}_nearest_gaps.csv').open('x', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('cylinder_index','x','y','radius_m','nearest_surface_gap_m'))
        for index, (cylinder, gap) in enumerate(zip(cylinders, nearest)):
            writer.writerow((index,cylinder.x,cylinder.y,cylinder.radius,gap))
    base.save_json(output/f'{NEW_NAME}_routes.json',
                   dict(map=NEW_NAME,routes=routes,audit=route))

    new_row = dict(
        label='G5', map=NEW_NAME, statistics=stats, route_audit=route,
        geometric_routes_xy=routes,
        proposal_provenance=dict(
            selection='Outcome-informed development revision; not blind validation',
            parent_map=OLD_NAME, parent_manifest=str(OLD_MANIFEST),
            parent_manifest_sha256=OLD_MANIFEST_SHA256,
            observed_failure=(
                'Adaptive profiler-on preflight contact episode at cylinder199; '
                '2026-09-21 campaign gapfree_n5_20260921_111647_3386864'),
            relocated_cylinder_index=RELOCATED_INDEX,
            old_center_m=list(EXPECTED_OLD[:2]), new_center_m=list(NEW_CENTER),
            new_location_rule=(
                'Highest pairwise surface clearance on deterministic 0.25m boundary-band grid; '
                'then exact offline loop connectivity/body-margin validation'),
            flight_observations_used_for_relocation=True),
        point_count=point_count,
    )
    new_row['assets_sha256'] = {
        str(path): base.geometry.sha256(path)
        for path in (*source, *mirror, install_config, output/csv_path.name)
    }
    maps = [*parent['maps'][:4], new_row]
    manifest = dict(parent)
    manifest.update(
        schema='gapfree-diameter1-static-suite-r2-v1', maps=maps,
        placement=(
            'G1-G4 frozen parent layouts; G5-R2 moves only parent G5 cylinder199 '
            'after an observed Adaptive development-preflight contact'),
        proposal_selection=(
            'G1-G4 original geometry-only selection; G5-R2 outcome-informed development revision'),
        old_maps_or_results_modified=False, flight_runs=0,
        final_performance_qualified=False, future_requested_flights=15,
        future_plan='G5-R2 ×3 modes ×5 primary runs after a separate fresh profiled preflight',
        revision=dict(
            parent_manifest=str(OLD_MANIFEST), parent_manifest_sha256=OLD_MANIFEST_SHA256,
            replaced_suite_member=OLD_NAME, replacement_suite_member=NEW_NAME,
            relocated_cylinder_index=RELOCATED_INDEX,
            old_cylinder=list(EXPECTED_OLD),
            new_cylinder=[*NEW_CENTER, base.RADIUS_M, ROLE],
            exact_cylinder_count_preserved=len(cylinders),
            minimum_surface_gap_m=minimum_gap,
            offline_route_min_body_clearance_m=route['min_body_clearance_m'],
            planner_algorithm_sensor_changed=False,
            map_revision_informed_by_prior_flight=True,
            confirmatory_claim_requires_fresh_unmodified_runs=True))
    generator = Path(__file__).resolve()
    manifest['generator_sha256'] = {
        str(path):base.geometry.sha256(path) for path in (
            generator, Path(base.__file__).resolve(),
            base.CAMPAIGN/'gen_cylinder_only_stress.py',
            base.CAMPAIGN/'cylinder_forest_geometry.py')}
    base.save_json(output/'manifest.json', manifest)
    base.save_json(output/'verification.json', dict(
        valid=True, map=NEW_NAME, cylinder_count=len(cylinders), diameter_m=1.0,
        relocated_cylinder_index=RELOCATED_INDEX, old_center_m=list(EXPECTED_OLD[:2]),
        new_center_m=list(NEW_CENTER), minimum_surface_gap_m=minimum_gap,
        offline_route_audit=route, point_count=point_count,
        outcome_informed_development_map=True, flights_started=0))
    print('G5-R2 MAP ONLY COMPLETE', output)
    return manifest


def main():
    generate()


if __name__ == '__main__':
    main()
