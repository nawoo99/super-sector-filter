#!/usr/bin/env python3
"""Read captured immutable grids, CIRI halfspaces and exact polynomials offline.

This compares inputs, not an exact MINCO replay or a replacement certificate.
Only equal surrounding publication versions are labeled coherent.
"""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
import struct
import numpy as np
from scenario7_geometry import load_geometry


def snapshot(path):
    stream_context = path.open('rb') if path.is_file() else gzip.open(str(path)+'.gz','rb')
    with stream_context as stream:
        def read(fmt):
            return struct.unpack('<'+fmt, stream.read(struct.calcsize('<'+fmt)))
        if stream.read(8) != b'ROGDIAG1':
            raise ValueError('wrong snapshot format')
        version, empty = read('QQ')
        grids = []
        for _ in range(2):
            resolution, = read('d')
            half, size, origin = (np.array(read('iii')) for _ in range(3))
            low, high = (np.array(read('ddd')) for _ in range(2))
            occupied, known = (np.frombuffer(stream.read(read('Q')[0]*8), dtype='<u8') for _ in range(2))
            grids.append(dict(resolution=resolution, half=half, size=size, origin=origin,
                              low=low, high=high, occupied=occupied, known=known))
        if stream.read(1):
            raise ValueError('extra snapshot bytes')
    return version, empty, grids


def occupied(grid, point):
    index = np.floor(np.asarray(point)/grid['resolution']).astype(np.int64)
    if np.max(np.abs(index-grid['origin'])-grid['half']) > 0:
        return None
    local = (index+grid['half']) % grid['size']
    hashed = int(local[0]*grid['size'][1]*grid['size'][2]+local[1]*grid['size'][2]+local[2])
    word = int(grid['occupied'][hashed//64])
    return bool((word >> (hashed % 64)) & 1)


def points(path):
    with path.open() as stream:
        return np.array([[float(r[k]) for k in ('x', 'y', 'z')] for r in csv.DictReader(stream)]).reshape(-1,3)


def polynomials(path):
    pieces = {}
    with path.open() as stream:
        for row in csv.DictReader(stream):
            i, axis, power = (int(row[k]) for k in ('piece', 'axis', 'power'))
            piece = pieces.setdefault(i, dict(duration=float(row['duration_s']), coefficients={}))
            piece['coefficients'][axis,power] = float(row['coefficient'])
    return [pieces[i] for i in sorted(pieces)]


def evaluate(pieces, at):
    for piece in pieces:
        if at <= piece['duration']+1e-9:
            return np.array([sum(value*at**power for (axis,power),value in piece['coefficients'].items()
                                 if axis == a) for a in range(3)])
        at -= piece['duration']
    raise ValueError('trajectory time out of range')


def analyze(directory, geometry=None):
    if not (directory/'COMPLETE').is_file():
        return dict(directory=str(directory), complete=False)
    meta = dict(line.split('=',1) for line in (directory/'metadata.txt').read_text().splitlines())
    result = dict(directory=str(directory), complete=True, metadata=meta)
    result['frontend_coherent'] = meta['frontend_map_written'] == '1' and meta['frontend_start'] == meta['frontend_end']
    result['guard_coherent'] = meta['guard_map_written'] == '1' and meta['guard_before'] == meta['guard_snapshot'] == meta['guard_after']
    guide = points(directory/'guide.csv')
    result['guide_points'] = len(guide)
    frontend_grids = None
    if geometry is not None and len(guide):
        result['guide_min_analytic_body_clearance_m'] = min(float(np.min(geometry.clearances(p))) for p in guide)
    if (directory/'frontend.map').is_file() or (directory/'frontend.map.gz').is_file():
        version, _, grids = snapshot(directory/'frontend.map')
        frontend_grids = grids
        result['frontend_version'] = version
        result['guide_inflated_occupied_points'] = sum(occupied(grids[1],p) is True for p in guide)
    collision = np.array([float(meta['collision_'+axis]) for axis in ('x','y','z')])
    at = float(meta['collision_tt'])
    if at >= 0 and ((directory/'guard.map').is_file() or (directory/'guard.map.gz').is_file()):
        version, _, grids = snapshot(directory/'guard.map')
        result['guard_version'] = version
        result['collision_raw_voxel_occupied'] = occupied(grids[0],collision)
        result['collision_inflated_voxel_occupied'] = occupied(grids[1],collision)
        pieces = polynomials(directory/'candidate.csv')
        if pieces:
            point = evaluate(pieces,at)
            result['collision_time_polynomial_point'] = point.tolist()
            result['collision_polynomial_reconstruction_error_m'] = float(np.linalg.norm(point-collision))
            result['collision_may_be_raycast_voxel_center'] = True
            result['polynomial_point_inflated_voxel_occupied'] = occupied(grids[1],point)
            if frontend_grids is not None:
                result['polynomial_point_frontend_inflated_voxel_occupied'] = occupied(frontend_grids[1],point)
                result['guard_query_frontend_inflated_voxel_occupied'] = occupied(frontend_grids[1],collision)
                result['frontend_and_guard_same_publication'] = meta['frontend_start'] == meta['guard_snapshot']
            if geometry is not None:
                result['unflown_polynomial_point_analytic_body_clearance_m'] = float(np.min(geometry.clearances(point)))
                result['unflown_guard_query_analytic_body_clearance_m'] = float(np.min(geometry.clearances(collision)))
        per_poly = {}
        per_poly_actual = {}
        with (directory/'corridors.csv').open() as stream:
            for row in csv.DictReader(stream):
                normal = np.array([float(row[k]) for k in ('nx','ny','nz')])
                norm = np.linalg.norm(normal)
                if not math.isfinite(norm) or norm == 0:
                    raise ValueError('invalid captured plane')
                violation = (normal@collision+float(row['d']))/norm
                key = int(row['corridor'])
                per_poly[key] = max(per_poly.get(key,-math.inf),float(violation))
                if pieces:
                    actual_violation = (normal@point+float(row['d']))/norm
                    per_poly_actual[key] = max(per_poly_actual.get(key,-math.inf),float(actual_violation))
        result['collision_min_union_plane_violation_m'] = min(per_poly.values(), default=None)
        result['collision_inside_any_ciri_polytope'] = any(v <= 1e-9 for v in per_poly.values())
        result['polynomial_point_min_union_plane_violation_m'] = min(per_poly_actual.values(),default=None)
        result['polynomial_point_inside_any_ciri_polytope'] = any(v <= 1e-9 for v in per_poly_actual.values())
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--geometry-pcd', type=Path)
    args = parser.parse_args()
    geometry = load_geometry(args.geometry_pcd) if args.geometry_pcd else None
    reports = [analyze(path,geometry) for path in sorted(args.root.iterdir(),key=lambda p:int(p.name)) if path.is_dir()]
    payload = dict(schema='planner-input-comparison-v1', exact_optimizer_replay=False, reports=reports)
    if args.output:
        with args.output.open('x') as stream:
            json.dump(payload,stream,indent=2)
            stream.write('\n')
    print(json.dumps(payload,indent=2))


if __name__ == '__main__':
    main()
