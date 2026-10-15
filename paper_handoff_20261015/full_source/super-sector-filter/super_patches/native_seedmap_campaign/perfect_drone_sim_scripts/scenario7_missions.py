#!/usr/bin/env python3
"""Frozen, per-map scenario7 missions and offline geometric admission.

The five original maps retain loop24. New mission TXT files exclude the initial
pose and contain five x/y/z/switch-distance rows. Runtime lookup uses stdlib
only: geometry and NumPy are imported solely for explicit offline proof work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

PACKAGE = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim')
REPO = Path('/root/super-sector-filter')
MIRROR = REPO/'super_patches/native_seedmap_campaign'
MISSION_DATA = Path('/root/super_ws/src/SUPER/mission_planner/data')
INSTALLED_DATA = Path('/root/super_ws/install/mission_planner/share/mission_planner/data')
MIRROR_DATA = MIRROR/'mission_planner_data'
OUTPUT = REPO/'results/scenario7_missions_20260924'
MANIFEST = OUTPUT/'manifest.json'
MAP_MANIFEST = REPO/'results/scenario7_maps_20260924/manifest.json'
SCHEMA = 'scenario7-mission-registry-v1'
ORIGINAL_MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1, 5))+('gapfree_d1_m05r2',)
ADDED_MAPS = ('urban_blocks_u01', 'forest_cluster_f01')
MAPS = ORIGINAL_MAPS+ADDED_MAPS
INITIAL = (0., 0., 1.5)
SWITCH_DISTANCE_M = 1.5
GOALS = {
    'loop24': ((24., 24.), (-24., 24.), (-24., -24.), (24., -24.), (0., 0.)),
    'urban_building_corners_v3': ((-24., 25.), (24., 13.), (-24., -13.), (24., -25.), (0., 0.)),
    'forest_wide_zigzag_v2': ((-24., 22.), (24., 22.), (-24., -22.), (24., -22.), (0., 0.)),
}
MISSION_BY_MAP = {**dict.fromkeys(ORIGINAL_MAPS, 'loop24'),
                  'urban_blocks_u01': 'urban_building_corners_v3',
                  'forest_cluster_f01': 'forest_wide_zigzag_v2'}
FAMILY_BY_MAP = {**dict.fromkeys(ORIGINAL_MAPS, 'normal'),
                 'urban_blocks_u01': 'urban', 'forest_cluster_f01': 'forest'}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def mission_text(mission):
    return ''.join(f'{x:g} {y:g} 1.5 1.5\n' for x, y in GOALS[mission])


def mission_paths(mission):
    return tuple(directory/(mission+'.txt') for directory in (MISSION_DATA, MIRROR_DATA, INSTALLED_DATA))


def expected_row(map_name):
    if map_name not in MISSION_BY_MAP:
        raise ValueError('Unknown scenario7 map: '+str(map_name))
    mission = MISSION_BY_MAP[map_name]
    points = [list(INITIAL[:2]), *[list(p) for p in GOALS[mission]]]
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    return dict(map=map_name, family=FAMILY_BY_MAP[map_name], mission=mission, mission_name=mission,
                mission_file_basename=mission+'.txt', mission_file=str(MISSION_DATA/(mission+'.txt')),
                installed_mission_file=str(INSTALLED_DATA/(mission+'.txt')),
                initial_position_xyz=list(INITIAL), height_m=1.5,
                waypoints_xyz=[[x, y, 1.5] for x, y in GOALS[mission]],
                waypoints_xy=[list(p) for p in GOALS[mission]],
                wps=';'.join(f'{x:g},{y:g}' for x, y in GOALS[mission]),
                goal_count=5, mission_file_excludes_initial_pose=True,
                switch_distance_m=SWITCH_DISTANCE_M,
                nominal_leg_lengths_m=lengths, nominal_total_length_m=sum(lengths))


def verify_hashes(inventory):
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError('Missing mission asset hash inventory')
    for name, expected in inventory.items():
        path = Path(name)
        if not path.is_absolute() or not path.is_file() or sha256(path) != expected:
            raise ValueError('Missing or changed mission-bound asset: '+str(name))


def read_registry(path=None):
    path = Path(path) if path is not None else MANIFEST
    raw = path.read_bytes()
    doc = json.loads(raw)
    if doc.get('schema') != SCHEMA or list(doc.get('missions', {})) != list(MAPS):
        raise ValueError('Mission registry identity/order mismatch')
    return doc, path, hashlib.sha256(raw).hexdigest()


def validate_row(map_name, row, inventory):
    expected = expected_row(map_name)
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError('Approved mission definition changed: '+map_name)
    paths = mission_paths(row['mission'])
    required = {str(path) for path in paths}
    bindings = row.get('assets_sha256', {})
    if set(bindings) != required or any(inventory.get(p) != h for p, h in bindings.items()):
        raise ValueError('Incomplete or inconsistent selected mission bindings: '+map_name)
    verify_hashes(bindings)
    for path in paths:
        if path.read_text() != mission_text(row['mission']):
            raise ValueError('Mission TXT differs from approved goals/switch distance: '+str(path))
    if row.get('mission_sha256') != bindings[str(paths[0])]:
        raise ValueError('Mission content digest mismatch: '+map_name)
    return dict(row)


def mission_context(map_name):
    """Fast selected-map context, validating only its three small TXT assets.

    The registry digest is returned for admission/freeze checks; callers use
    validate_missions() once to verify its full source/proof inventory.
    """
    if map_name not in MISSION_BY_MAP:
        raise ValueError('Unknown scenario7 map: '+str(map_name))
    doc, path, digest = read_registry()
    context = validate_row(map_name, doc['missions'][map_name], doc['assets_sha256'])
    context.update(registry_path=str(path), registry_sha256=digest)
    return context


def validate_missions():
    """Validate the complete immutable registry; no flight/plot imports."""
    doc, path, digest = read_registry()
    verify_hashes(doc['assets_sha256'])
    verify_hashes(doc['protected_existing_mission_assets_sha256'])
    required_sources = (Path(__file__).resolve(), PACKAGE/'test/test_scenario7_missions.py',
                        MIRROR/'perfect_drone_sim_scripts/scenario7_missions.py',
                        MIRROR/'perfect_drone_sim_test/test_scenario7_missions.py', MAP_MANIFEST)
    if any(str(source) not in doc['assets_sha256'] for source in required_sources):
        raise ValueError('Mission registry is missing source/map-manifest bindings')
    contexts = {}
    for map_name in MAPS:
        context = validate_row(map_name, doc['missions'][map_name], doc['assets_sha256'])
        context.update(registry_path=str(path), registry_sha256=digest)
        contexts[map_name] = context
    for map_name in ADDED_MAPS:
        proof_path = path.parent/(map_name+'_proof.json')
        geometry_path = PACKAGE/'pcd/seed_maps'/(map_name+'_geometry.json')
        if any(str(p) not in doc['assets_sha256'] for p in (proof_path, geometry_path)):
            raise ValueError('Mission registry is missing proof/geometry binding')
        proof = json.loads(proof_path.read_text())
        context = contexts[map_name]
        if (proof.get('schema') != 'scenario7-mission-geometry-proof-v1'
                or proof.get('map') != map_name or proof.get('mission') != context['mission']
                or proof.get('geometry_sha256') != doc['assets_sha256'][str(geometry_path)]
                or proof.get('mission_sha256') != context['mission_sha256']
                or proof.get('waypoints_xyz') != [list(INITIAL)]+context['waypoints_xyz']
                or proof.get('route_audit', {}).get('valid') is not True
                or proof['route_audit'].get('min_body_clearance_m', -1.) < .35):
            raise ValueError('Mission proof does not match the admitted mission: '+map_name)
    bindings = dict(doc['assets_sha256'])
    bindings.update(doc['protected_existing_mission_assets_sha256'])
    bindings[str(path)] = digest
    return dict(valid=True, assets_sha256=bindings,
                manifest=dict(path=str(path), sha256=digest, schema=SCHEMA),
                manifest_path=str(path), manifest_sha256=digest,
                missions=contexts, flights_started=False)


def geometric_proof(map_name):
    """Build a static connected-path witness without modifying map assets."""
    import gen_scenario7_maps as geometry
    row = expected_row(map_name)
    geometry_path = PACKAGE/'pcd/seed_maps'/(map_name+'_geometry.json')
    doc = json.loads(geometry_path.read_text())
    geometry.validate_geometry(doc)
    waypoints = (INITIAL[:2], *GOALS[row['mission']])
    previous = geometry.LOOP_WAYPOINTS
    try:
        geometry.LOOP_WAYPOINTS = waypoints
        routes = geometry.offline_routes(doc)
        audit = geometry.route_audit(doc, routes)
    finally:
        geometry.LOOP_WAYPOINTS = previous
    endpoints = []
    for p in waypoints:
        distances = [geometry.point_box_distance(p, b) for b in doc['boxes']]
        distances += [max(0., math.dist(p, (c['x'], c['y']))-c['r']) for c in doc['cylinders']]
        endpoints.append(min(distances)-geometry.BODY_RADIUS_M)
    connectors = []
    for a, b in zip(waypoints, waypoints[1:]):
        distances = [geometry.segment_box_distance(a, b, box) for box in doc['boxes']]
        distances += [max(0., geometry.point_segment_distance((c['x'], c['y']), a, b)-c['r']) for c in doc['cylinders']]
        connectors.append(dict(body_collision_obstacle_count=sum(d < geometry.BODY_RADIUS_M for d in distances),
                               centerline_intersection_obstacle_count=sum(d == 0. for d in distances),
                               min_solid_body_clearance_m=min(distances)-geometry.BODY_RADIUS_M))
    return dict(schema='scenario7-mission-geometry-proof-v1', map=map_name, mission=row['mission'],
                geometry_path=str(geometry_path), geometry_sha256=sha256(geometry_path),
                mission_sha256=hashlib.sha256(mission_text(row['mission']).encode()).hexdigest(),
                waypoints_xyz=[list(INITIAL)]+row['waypoints_xyz'],
                min_endpoint_body_clearance_m=min(endpoints), endpoint_body_clearances_m=endpoints,
                nominal_leg_lengths_m=row['nominal_leg_lengths_m'], nominal_total_length_m=row['nominal_total_length_m'],
                straight_connector_audits=connectors,
                straight_connectors_are_feasible_paths=False,
                geometric_routes_xy=[[list(p) for p in leg] for leg in routes], route_audit=audit,
                offline_routes_supplied_to_planner=False, flight_runs=0)


def verify_proofs():
    validate_missions()
    doc, path, _ = read_registry()
    for map_name in ADDED_MAPS:
        stored = json.loads((path.parent/(map_name+'_proof.json')).read_text())
        if stored != geometric_proof(map_name):
            raise ValueError('Recomputed geometric proof differs: '+map_name)
    return dict(valid=True, flight_runs=0)


def copy_exclusive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def generate():
    started = time.monotonic()
    script = Path(__file__).resolve()
    test = PACKAGE/'test/test_scenario7_missions.py'
    mirrored_script = MIRROR/'perfect_drone_sim_scripts'/script.name
    mirrored_test = MIRROR/'perfect_drone_sim_test'/test.name
    targets = [OUTPUT, mirrored_script, mirrored_test]
    for map_name in ADDED_MAPS:
        targets += list(mission_paths(MISSION_BY_MAP[map_name]))
    for target in targets:
        if target.exists() or target.is_symlink():
            raise ValueError('Refusing to overwrite existing mission target: '+str(target))
    if INSTALLED_DATA.is_symlink() or INSTALLED_DATA.resolve() != INSTALLED_DATA:
        raise ValueError('Unexpected installed mission data directory; resolve before generation')
    loop_paths = mission_paths('loop24')
    if any(p.read_text() != mission_text('loop24') for p in loop_paths):
        raise ValueError('Existing loop24 differs from approved unchanged baseline')
    preserved = {str(p): sha256(p) for folder in (MISSION_DATA, MIRROR_DATA, INSTALLED_DATA)
                 for p in sorted(folder.glob('*.txt')) if p.is_file()}
    preserved[str(MAP_MANIFEST)] = sha256(MAP_MANIFEST)
    proofs = {name: geometric_proof(name) for name in ADDED_MAPS}
    OUTPUT.mkdir(parents=True, exist_ok=False)
    copy_exclusive(script, mirrored_script)
    copy_exclusive(test, mirrored_test)
    for map_name in ADDED_MAPS:
        mission = MISSION_BY_MAP[map_name]
        source, mirror, install = mission_paths(mission)
        with source.open('x') as stream:
            stream.write(mission_text(mission))
        copy_exclusive(source, mirror)
        # Existing install/loop24.txt is a source symlink; use that convention.
        install.symlink_to(source)
        save_json(OUTPUT/(map_name+'_proof.json'), proofs[map_name])
    rows, assets = {}, {}
    for map_name in MAPS:
        row = expected_row(map_name)
        bindings = {str(p): sha256(p) for p in mission_paths(row['mission'])}
        row.update(assets_sha256=bindings, mission_sha256=bindings[row['mission_file']])
        rows[map_name] = row
        assets.update(bindings)
    for source in (script, test, mirrored_script, mirrored_test, MAP_MANIFEST):
        assets[str(source)] = sha256(source)
    for map_name in ADDED_MAPS:
        for source in (PACKAGE/'pcd/seed_maps'/(map_name+'_geometry.json'), OUTPUT/(map_name+'_proof.json')):
            assets[str(source)] = sha256(source)
    verify_hashes(preserved)
    manifest = dict(schema=SCHEMA, missions=rows, assets_sha256=assets,
                    protected_existing_mission_assets_sha256=preserved,
                    original_maps_retain_loop24=True, map_assets_changed=False,
                    planner_algorithm_sensor_changed=False, flight_runs=0,
                    installed_mission_data_directory=str(INSTALLED_DATA),
                    installed_mission_data_directory_resolved=str(INSTALLED_DATA.resolve()),
                    new_install_entries='Source symlinks, matching existing loop24.txt install convention',
                    txt_format='Five rows x y z switch_distance; initial pose excluded; final origin included',
                    monitor_wps_format='Five semicolon-separated x,y pairs; initial pose excluded',
                    geometric_proofs_are_planner_inputs=False,
                    generation_wall_seconds=time.monotonic()-started)
    save_json(MANIFEST, manifest)
    return validate_missions()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--verify-proofs', action='store_true')
    parser.add_argument('--map', choices=MAPS)
    args = parser.parse_args()
    if args.generate:
        value = generate()
    elif args.verify_proofs:
        value = verify_proofs()
    elif args.map:
        value = mission_context(args.map)
    else:
        value = validate_missions()
    print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
