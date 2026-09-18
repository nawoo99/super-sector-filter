#!/usr/bin/env python3
"""Read-only admission and map bindings for the frozen G1–G5 map suite.

Canonical transport hashes describe PCL PointXYZI/ROS records, not ASCII bytes.
Registering these expectations does not certify transport: fresh DDS/RViz
evidence must still pass the existing map-bound acceptance validator.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

REPO = Path('/root/super-sector-filter')
LEGACY_DIR = REPO / 'scripts/native_campaign'
PACKAGE = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim')
MANIFEST = REPO / 'results/gapfree_d1_maps_20260918/manifest.json'
MANIFEST_SHA256 = 'e3e2ea0dcca7b74f687094a90692953ece56247d2f45b5eda46dc2fc062b7f73'
MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1, 6))
LEGACY_CHILD = LEGACY_DIR / 'adaptive_cpu40_seed1.py'
LEGACY_CHILD_SHA256 = '954876f41d60d5ce76cb5b0742b6da826daca2a4e7f0b355e0b3878e1b77dac3'

if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_geometry(path):
    """Strict ASCII XYZ/XYZI -> little-endian 32-byte PointXYZI records."""
    path = Path(path)
    header = {}
    with path.open() as stream:
        for line in stream:
            tokens = line.split()
            if not tokens or tokens[0].startswith('#'):
                continue
            key, values = tokens[0].upper(), tokens[1:]
            if key in header:
                raise ValueError(f'Duplicate PCD header {key}: {path}')
            header[key] = values
            if key == 'DATA':
                break
        fields = header.get('FIELDS')
        if fields not in (['x', 'y', 'z'], ['x', 'y', 'z', 'intensity']):
            raise ValueError(f'Unsupported canonical fields: {path}')
        ncols = len(fields)
        if (header.get('DATA') != ['ascii'] or header.get('SIZE') != ['4'] * ncols
                or header.get('TYPE') != ['F'] * ncols
                or header.get('COUNT') != ['1'] * ncols
                or header.get('HEIGHT') != ['1']):
            raise ValueError(f'Unsupported PCD layout: {path}')
        count = int(header['POINTS'][0])
        if count <= 0 or header.get('WIDTH') != [str(count)]:
            raise ValueError(f'Invalid PCD dimensions: {path}')
        values = np.loadtxt(stream, dtype='<f4', ndmin=2)
    if values.shape != (count, ncols) or not np.isfinite(values).all():
        raise ValueError(f'Invalid PCD data count/values: {path}')
    # PCL aligned PointXYZI: xyz, homogeneous 1, intensity, 12 padding bytes.
    records = np.zeros((count, 8), dtype='<f4')
    records[:, :3] = values[:, :3]
    records[:, 3] = 1.0
    if ncols == 4:
        records[:, 4] = values[:, 3]
    return dict(points=count, sha256=hashlib.sha256(records.tobytes()).hexdigest(),
                bytes=count * 32, point_step=32, frame='world')


def validate_suite():
    """Validate the exact previously generated suite, including all asset copies."""
    if sha256(MANIFEST) != MANIFEST_SHA256:
        raise ValueError('Frozen G1–G5 manifest changed')
    if sha256(LEGACY_CHILD) != LEGACY_CHILD_SHA256:
        raise ValueError('Legacy child baseline changed; review adapter differential')
    document = json.loads(MANIFEST.read_text())
    if (document.get('schema') != 'gapfree-diameter1-static-suite-v1'
            or tuple(row.get('map') for row in document.get('maps', [])) != MAPS):
        raise ValueError('Expected exact ordered G1–G5 manifest')
    bindings = {str(MANIFEST): MANIFEST_SHA256, str(LEGACY_CHILD): LEGACY_CHILD_SHA256}
    contexts = {}
    for row in document['maps']:
        name = row['map']
        if (row['statistics']['cylinder_count'] != 410
                or row['statistics']['diameter_m'] != 1.0
                or row['route_audit']['valid'] is not True):
            raise ValueError('Map geometry admission failed: ' + name)
        assets = row['assets_sha256']
        required = (PACKAGE / 'config' / (name + '.yaml'),
                    PACKAGE / 'pcd/seed_maps' / (name + '.pcd'),
                    PACKAGE / 'pcd/seed_maps' / (name + '_cylinders.csv'))
        if not all(str(path) in assets for path in required):
            raise ValueError('Incomplete map asset bindings: ' + name)
        for path, expected in assets.items():
            if sha256(path) != expected:
                raise ValueError('Frozen map asset changed: ' + path)
            bindings[path] = expected
        geometry = canonical_geometry(required[1])
        if geometry['points'] != row['point_count']:
            raise ValueError('Canonical point count mismatch: ' + name)
        contexts[name] = dict(map=name, label=row['label'], geometry=geometry)
    return dict(valid=True, schema='gapfree-map-admission-v1', maps=contexts,
                manifest=str(MANIFEST), manifest_sha256=MANIFEST_SHA256,
                assets_sha256=bindings,
                transport_certified=False, flights_started=False)


def register_maps():
    """Register exact expectations in this process only; no legacy file writes."""
    import static_latched_preflight as static
    admission = validate_suite()
    for name, context in admission['maps'].items():
        geometry = context['geometry']
        value = (geometry['points'], geometry['sha256'])
        if name in static.MAP_GEOMETRIES and static.MAP_GEOMETRIES[name] != value:
            raise ValueError('Conflicting in-process map geometry: ' + name)
        static.MAP_GEOMETRIES[name] = value
        context.update(static.map_context(name))
    return admission


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ('check', 'static'):
        raise SystemExit('Usage: gapfree_campaign_support.py check | static create/validate ...')
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
