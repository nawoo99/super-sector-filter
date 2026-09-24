#!/usr/bin/env python3
"""Additive map admission for frozen G1–G4/G5-R2, urban U1 and forest F1.

The new manifest digest is measured at admission and frozen by the manual
controller. Transport hashes are expectations, not DDS/RViz certification.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import sys

PACKAGE = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim')
REPO = Path('/root/super-sector-filter')
LEGACY_DIR = REPO / 'scripts/native_campaign'
LEGACY_CHILD = LEGACY_DIR / 'adaptive_cpu40_seed1.py'
LEGACY_CHILD_SHA256 = '954876f41d60d5ce76cb5b0742b6da826daca2a4e7f0b355e0b3878e1b77dac3'
GAPFREE_SUPPORT = PACKAGE / 'scripts/gapfree_campaign_support.py'
GAPFREE_ADAPTER = PACKAGE / 'scripts/gapfree_cpu_compare.py'
GAPFREE_MONITOR = PACKAGE / 'scripts/gapfree_native_loop_monitor.py'
GAPFREE_SUPPORT_SHA256 = 'c279b1309c1c31d41ab703e21e6c1ad26a8d476b92a0f1b2cec4c46329721c69'
GAPFREE_ADAPTER_SHA256 = '3714f9953eff9af00c4da5326bf91052ffc19d0c21c27caca62775fb2049c0fb'
GAPFREE_MONITOR_SHA256 = '73f2b766ffc843d726c0b96d4544fd08df8d74880f279aa6025f9885c31dae82'
MANIFEST = REPO / 'results/scenario7_maps_20260924/manifest.json'
MIRROR = REPO / 'super_patches/native_seedmap_campaign'
INSTALL_CONFIG = Path('/root/super_ws/install/perfect_drone_sim/share/perfect_drone_sim/config')
ORIGINAL_MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1, 5)) + ('gapfree_d1_m05r2',)
ADDED_MAPS = ('urban_blocks_u01', 'forest_cluster_f01')
MAPS7 = ORIGINAL_MAPS + ADDED_MAPS
MAPS = MAPS7
MAP_LABELS = dict(zip(MAPS7, ('G1', 'G2', 'G3', 'G4', 'G5-R2', 'U1', 'F1')))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_baselines():
    bindings = {str(GAPFREE_SUPPORT): GAPFREE_SUPPORT_SHA256,
                str(GAPFREE_ADAPTER): GAPFREE_ADAPTER_SHA256,
                str(GAPFREE_MONITOR): GAPFREE_MONITOR_SHA256,
                str(LEGACY_CHILD): LEGACY_CHILD_SHA256}
    for path, expected in bindings.items():
        if sha256(path) != expected:
            raise ValueError('Inherited campaign baseline changed: ' + path)
    return bindings


# Verify the inherited modules before importing executable Python from them.
verify_baselines()
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))
import gapfree_campaign_support as gapfree

canonical_geometry = gapfree.canonical_geometry


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_solid_geometry(path, map_name):
    document = json.loads(Path(path).read_text())
    if (document.get('schema') != 'scenario-solid-geometry-v1'
            or document.get('map') != map_name
            or not _finite(document.get('body_radius_m'))
            or document['body_radius_m'] != 0.2):
        raise ValueError('Solid geometry identity/body mismatch: ' + map_name)
    boxes, cylinders = document.get('boxes'), document.get('cylinders')
    if not isinstance(boxes, list) or not isinstance(cylinders, list) or not boxes + cylinders:
        raise ValueError('Nonempty solid obstacle lists required: ' + map_name)
    identifiers = set()
    for family, rows, fields, dimensions in (
            ('box', boxes, ('cx', 'cy', 'z_min', 'z_max', 'size_x', 'size_y'), ('size_x', 'size_y')),
            ('cylinder', cylinders, ('x', 'y', 'r', 'z_min', 'z_max'), ('r',))):
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Invalid solid obstacle: ' + map_name)
            identity = row.get('id')
            if not isinstance(identity, str) or not identity or identity in identifiers:
                raise ValueError('Unique nonempty solid IDs required: ' + map_name)
            identifiers.add(identity)
            if (not all(_finite(row.get(key)) for key in fields)
                    or row['z_min'] >= row['z_max']
                    or any(row[key] <= 0 for key in dimensions)):
                raise ValueError('Invalid finite ' + family + ' dimensions: ' + map_name)
    return document


def _required_added_assets(name):
    config = PACKAGE / 'config' / (name + '.yaml')
    pcd = PACKAGE / 'pcd/seed_maps' / (name + '.pcd')
    solid = pcd.with_name(name + '_geometry.json')
    return (config, pcd, solid,
            MIRROR / 'perfect_drone_sim_config' / config.name,
            MIRROR / 'perfect_drone_sim_pcd/seed_maps' / pcd.name,
            MIRROR / 'perfect_drone_sim_pcd/seed_maps' / solid.name,
            INSTALL_CONFIG / config.name)


def validate_suite():
    bindings = verify_baselines()
    original = gapfree.validate_suite()
    bindings.update(original['assets_sha256'])
    manifest_digest = sha256(MANIFEST)
    document = json.loads(MANIFEST.read_text())
    if (document.get('schema') != 'scenario7-added-maps-v1'
            or tuple(row.get('map') for row in document.get('maps', [])) != ADDED_MAPS):
        raise ValueError('Expected exact ordered U1/F1 added map manifest')
    bindings[str(MANIFEST)] = manifest_digest
    contexts = {name: dict(context) for name, context in original['maps'].items()}
    for name, context in contexts.items():
        solid = PACKAGE / 'pcd/seed_maps' / (name + '_cylinders.csv')
        context.update(label=MAP_LABELS[name], family='gapfree',
                       solid_geometry_path=str(solid), solid_geometry_sha256=bindings[str(solid)],
                       solid_geometry_format='gapfree-cylinder-csv',
                       box_count=0, cylinder_count=410, body_radius_m=0.2)
    baseline_config = (PACKAGE / 'config' / (ORIGINAL_MAPS[0] + '.yaml')).read_text()
    baseline_pcd_name = 'pcd_name: "seed_maps/' + ORIGINAL_MAPS[0] + '.pcd"'
    if baseline_config.count(baseline_pcd_name) != 1:
        raise ValueError('Original simulator config identity changed')
    for row in document['maps']:
        name = row['map']
        expected_family = 'urban' if name == ADDED_MAPS[0] else 'forest'
        if (row.get('label') != MAP_LABELS[name] or row.get('family') != expected_family
                or row.get('route_audit', {}).get('valid') is not True
                or not isinstance(row.get('statistics'), dict)
                or type(row.get('point_count')) is not int or row['point_count'] <= 0):
            raise ValueError('Added map geometry admission failed: ' + name)
        required = _required_added_assets(name)
        assets = row.get('assets_sha256', {})
        if not isinstance(assets, dict) or not all(str(path) in assets for path in required):
            raise ValueError('Incomplete added map asset bindings: ' + name)
        for path, expected in assets.items():
            if (not isinstance(path, str) or not Path(path).is_absolute()
                    or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)
                    or sha256(path) != expected):
                raise ValueError('Frozen added map asset changed: ' + str(path))
            if path in bindings and bindings[path] != expected:
                raise ValueError('Conflicting asset hash: ' + path)
            bindings[path] = expected
        config, pcd, solid = required[:3]
        for first, second in ((config, required[3]), (pcd, required[4]),
                              (solid, required[5]), (config, required[6])):
            if assets[str(first)] != assets[str(second)]:
                raise ValueError('Added map source/mirror/install mismatch: ' + name)
        expected_config = baseline_config.replace(
            baseline_pcd_name, 'pcd_name: "seed_maps/' + name + '.pcd"')
        if config.read_text() != expected_config:
            raise ValueError('Added map simulator/sensor profile changed: ' + name)
        solid_doc = validate_solid_geometry(solid, name)
        geometry = canonical_geometry(pcd)
        if geometry['points'] != row['point_count']:
            raise ValueError('Canonical point count mismatch: ' + name)
        contexts[name] = dict(map=name, label=row['label'], family=row['family'], geometry=geometry,
                              solid_geometry_path=str(solid), solid_geometry_sha256=assets[str(solid)],
                              solid_geometry_format=solid_doc['schema'],
                              box_count=len(solid_doc['boxes']), cylinder_count=len(solid_doc['cylinders']),
                              body_radius_m=solid_doc['body_radius_m'])
    if sha256(MANIFEST) != manifest_digest:
        raise ValueError('Added manifest changed during admission')
    return dict(valid=True, schema='scenario7-map-admission-v1', maps=contexts,
                manifest=str(MANIFEST), manifest_sha256=manifest_digest,
                original_manifest=original['manifest'], original_manifest_sha256=original['manifest_sha256'],
                assets_sha256=bindings, transport_certified=False, flights_started=False)


def register_maps():
    import static_latched_preflight as static
    admission = validate_suite()
    # Check every conflict before mutating the in-process transport registry.
    for name, context in admission['maps'].items():
        value = (context['geometry']['points'], context['geometry']['sha256'])
        if name in static.MAP_GEOMETRIES and static.MAP_GEOMETRIES[name] != value:
            raise ValueError('Conflicting in-process map geometry: ' + name)
    for name, context in admission['maps'].items():
        static.MAP_GEOMETRIES[name] = (context['geometry']['points'], context['geometry']['sha256'])
        transport = static.map_context(name)
        # The frozen admission is written as JSON. Keep Paths owned by the
        # static validator intact; serialize only this returned snapshot.
        context.update(transport, paths={key: str(path) for key, path in transport['paths'].items()})
    return admission


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ('check', 'static'):
        raise SystemExit('Usage: scenario7_campaign_support.py check | static create/validate ...')
    admission = register_maps()
    if args[0] == 'check':
        if len(args) != 1:
            raise SystemExit('check takes no additional arguments')
        print(json.dumps(admission, indent=2, default=str))
        return 0
    import static_latched_preflight as static
    return static.main(args[1:])


if __name__ == '__main__':
    raise SystemExit(main())
