#!/usr/bin/env python3
"""Add one block-city and one clustered trunk forest; never run ROS or flights.

Authoritative solids, sampled PCDs, and continuous offline route witnesses are
separate artifacts. Only geometry qualifies a proposal. Existing assets are
immutable; --verify-existing reuses a suite only after checking its full hash
inventory and analytical geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
REPO = Path('/root/super-sector-filter')
MIRROR = REPO / 'super_patches/native_seedmap_campaign'
INSTALL_CONFIG = Path('/root/super_ws/install/perfect_drone_sim/share/perfect_drone_sim/config')
OUTPUT = REPO / 'results/scenario7_maps_20260924'
MAP_NAMES = ('urban_blocks_u01', 'forest_cluster_f01')
FIELD_HALF_M = 32.
BODY_RADIUS_M = .20
REQUIRED_MARGIN_M = .35
NODE_MARGIN_M = .45
GRID_STEP_M = .10
FLIGHT_Z_M = 1.5
SURFACE_DS_M = .05
Z_STEP_M = .10
FOREST_SEED = 2026092401
LOOP_WAYPOINTS = ((0., 0.), (24., 24.), (-24., 24.), (-24., -24.),
                  (24., -24.), (0., 0.))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def scene(name, boxes=(), cylinders=()):
    return dict(schema='scenario-solid-geometry-v1', map=name,
                body_radius_m=BODY_RADIUS_M, boxes=list(boxes), cylinders=list(cylinders))


def urban_layout():
    return scene(MAP_NAMES[0], boxes=[
        dict(id=f'building_{i:02d}', cx=x, cy=y, z_min=0., z_max=6., size_x=6., size_y=8.)
        for i, (x, y) in enumerate(( (x, y) for y in (-19., -7., 7., 19.)
                                    for x in (-19., -7., 7., 19.)), 1)])


def forest_layout(seed=FOREST_SEED):
    """Ten separated cluster disks, 27 trunks each, plus 140 uniform trunks.

    Proposals are checked for overlap only. No start/goal pocket or mission
    corridor is carved. Whole layouts later face the offline route check.
    """
    rng = random.Random(seed)
    centers, cylinders, proposals = [], [], 0
    while len(centers) < 10 and proposals < 100000:
        proposals += 1
        p = (round(rng.uniform(-26., 26.), 6), round(rng.uniform(-26., 26.), 6))
        if all(math.dist(p, q) >= 10. for q in centers):
            centers.append(p)
    if len(centers) != 10:
        raise ValueError('Could not place ten cluster centers')

    def add(x, y, role):
        x, y = round(x, 6), round(y, 6)
        if max(abs(x), abs(y)) + .5 > FIELD_HALF_M:
            return False
        if any(math.hypot(x-c['x'], y-c['y']) < 1. for c in cylinders):
            return False
        cylinders.append(dict(id=f'trunk_{len(cylinders)+1:03d}', x=x, y=y, r=.5,
                              z_min=0., z_max=4., role=role))
        return True

    for index, (cx, cy) in enumerate(centers, 1):
        accepted = 0
        for _ in range(100000):
            if accepted == 27:
                break
            proposals += 1
            dx, dy = rng.gauss(0., 2.1), rng.gauss(0., 2.1)
            if math.hypot(dx, dy) <= 4.5 and add(cx+dx, cy+dy, f'cluster_{index:02d}'):
                accepted += 1
        if accepted != 27:
            raise ValueError('Could not pack a cluster without overlap')
    for _ in range(100000):
        if len(cylinders) == 410:
            break
        proposals += 1
        add(rng.uniform(-31.5, 31.5), rng.uniform(-31.5, 31.5), 'background')
    if len(cylinders) != 410:
        raise ValueError('Could not place 410 disjoint trunks')
    return scene(MAP_NAMES[1], cylinders=cylinders), dict(
        actual_seed=seed, proposal_count=proposals, cluster_centers_xy=centers,
        cluster_count=10, trunks_per_cluster=27, clustered_trunk_count=270,
        background_trunk_count=140, cluster_center_min_spacing_m=10.,
        cluster_offset_distribution='Gaussian sigma2.1m, truncated at radius4.5m; nonoverlap rejection',
        background_distribution='Uniform across the complete field, subject only to nonoverlap')


def box_bounds(box):
    return (box['cx']-box['size_x']/2, box['cx']+box['size_x']/2,
            box['cy']-box['size_y']/2, box['cy']+box['size_y']/2)


def point_box_distance(point, box):
    xmin, xmax, ymin, ymax = box_bounds(box)
    return math.hypot(max(xmin-point[0], 0., point[0]-xmax),
                      max(ymin-point[1], 0., point[1]-ymax))


def point_segment_distance(point, start, end):
    dx, dy = end[0]-start[0], end[1]-start[1]
    length2 = dx*dx+dy*dy
    t = 0. if not length2 else max(0., min(1.,
        ((point[0]-start[0])*dx+(point[1]-start[1])*dy)/length2))
    return math.hypot(point[0]-start[0]-t*dx, point[1]-start[1]-t*dy)


def segment_box_distance(start, end, box):
    """Exact Euclidean distance from a 2D closed segment to a solid rectangle."""
    xmin, xmax, ymin, ymax = box_bounds(box)
    low, high = 0., 1.
    for p, q, lower, upper in ((start[0], end[0], xmin, xmax),
                                (start[1], end[1], ymin, ymax)):
        delta = q-p
        if delta == 0.:
            if p < lower or p > upper:
                low, high = 1., 0.
                break
        else:
            ta, tb = sorted(((lower-p)/delta, (upper-p)/delta))
            low, high = max(low, ta), min(high, tb)
            if low > high:
                break
    if low <= high:
        return 0.
    return min(point_box_distance(start, box), point_box_distance(end, box),
               *(point_segment_distance(corner, start, end) for corner in
                 ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax))))


def pair_gap(a, b, kind):
    if kind == 'cylinders':
        return math.hypot(a['x']-b['x'], a['y']-b['y'])-a['r']-b['r']
    return math.hypot(max(abs(a['cx']-b['cx'])-(a['size_x']+b['size_x'])/2, 0.),
                      max(abs(a['cy']-b['cy'])-(a['size_y']+b['size_y'])/2, 0.))


def validate_geometry(doc):
    if doc.get('schema') != 'scenario-solid-geometry-v1' or doc.get('body_radius_m') != BODY_RADIUS_M:
        raise ValueError('Invalid geometry schema or body radius')
    if doc.get('map') not in MAP_NAMES:
        raise ValueError('Unexpected map identity')
    boxes, cylinders = doc['boxes'], doc['cylinders']
    if (doc['map'] == MAP_NAMES[0] and (len(boxes) != 16 or cylinders)
            or doc['map'] == MAP_NAMES[1] and (boxes or len(cylinders) != 410)):
        raise ValueError('Unexpected primitive count or family')
    ids = [p['id'] for p in boxes+cylinders]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError('Primitive IDs must be unique nonempty strings')
    for kind, items in (('boxes', boxes), ('cylinders', cylinders)):
        keys = ('cx', 'cy', 'size_x', 'size_y', 'z_min', 'z_max') if kind == 'boxes' else ('x', 'y', 'r', 'z_min', 'z_max')
        for item in items:
            if not all(math.isfinite(item[k]) for k in keys):
                raise ValueError('Nonfinite primitive')
            if kind == 'boxes':
                if (item['size_x'], item['size_y'], item['z_min'], item['z_max']) != (6., 8., 0., 6.):
                    raise ValueError('Wrong building dimensions')
                xmin, xmax, ymin, ymax = box_bounds(item)
                inside = min(xmin, ymin) >= -32. and max(xmax, ymax) <= 32.
            else:
                if (item['r'], item['z_min'], item['z_max']) != (.5, 0., 4.):
                    raise ValueError('Wrong trunk dimensions')
                inside = max(abs(item['x']), abs(item['y']))+item['r'] <= 32.
            if not inside:
                raise ValueError('Primitive extends beyond the field')
        for i, a in enumerate(items):
            for b in items[i+1:]:
                if kind == 'boxes':
                    overlap = (abs(a['cx']-b['cx']) < (a['size_x']+b['size_x'])/2 and
                               abs(a['cy']-b['cy']) < (a['size_y']+b['size_y'])/2)
                else:
                    overlap = pair_gap(a, b, kind) < 0.
                if overlap:
                    raise ValueError('Overlapping primitives')
    return True


def node_free_mask(doc):
    size = int(2*FIELD_HALF_M/GRID_STEP_M)+1
    axis = -FIELD_HALF_M+GRID_STEP_M*np.arange(size)
    x, y = np.meshgrid(axis, axis)
    free = np.ones((size, size), dtype=bool)
    clearance = BODY_RADIUS_M+NODE_MARGIN_M
    for box in doc['boxes']:
        xmin, xmax, ymin, ymax = box_bounds(box)
        dx, dy = np.maximum(np.maximum(xmin-x, x-xmax), 0.), np.maximum(np.maximum(ymin-y, y-ymax), 0.)
        free &= dx*dx+dy*dy >= clearance*clearance
    for c in doc['cylinders']:
        free &= (x-c['x'])**2+(y-c['y'])**2 >= (c['r']+clearance)**2
    return free


def offline_routes(doc):
    free = node_free_mask(doc)
    size = len(free)
    cell = lambda p: (round((p[1]+32.)/GRID_STEP_M), round((p[0]+32.)/GRID_STEP_M))
    neighbors = [(dy, dx, math.hypot(dx, dy)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
    routes = []
    for start, end in zip(LOOP_WAYPOINTS, LOOP_WAYPOINTS[1:]):
        begin, goal = cell(start), cell(end)
        if not free[begin] or not free[goal]:
            raise ValueError('Mission endpoint lacks conservative node clearance')
        queue, best, parent = [(math.dist(begin, goal), 0., begin)], {begin: 0.}, {}
        while queue:
            _, cost, node = heapq.heappop(queue)
            if cost > best[node]+1e-9:
                continue
            if node == goal:
                break
            for dy, dx, length in neighbors:
                nxt = (node[0]+dy, node[1]+dx)
                if not (0 <= nxt[0] < size and 0 <= nxt[1] < size and free[nxt]):
                    continue
                candidate = cost+length
                if candidate+1e-9 < best.get(nxt, math.inf):
                    best[nxt], parent[nxt] = candidate, node
                    heapq.heappush(queue, (candidate+math.dist(nxt, goal), candidate, nxt))
        else:
            raise ValueError('Mission endpoints are not connected on conservative grid')
        chain, node = [goal], goal
        while node != begin:
            node = parent[node]
            chain.append(node)
        chain.reverse()
        compact = [chain[0]]
        for i in range(1, len(chain)-1):
            if (chain[i][0]-chain[i-1][0], chain[i][1]-chain[i-1][1]) != (chain[i+1][0]-chain[i][0], chain[i+1][1]-chain[i][1]):
                compact.append(chain[i])
        compact.append(chain[-1])
        routes.append([(round(-32.+col*GRID_STEP_M, 6), round(-32.+row*GRID_STEP_M, 6)) for row, col in compact])
    return routes


def route_audit(doc, routes):
    if len(routes) != 5:
        raise ValueError('Expected all five mission legs')
    if any(not (p['z_min'] <= FLIGHT_Z_M <= p['z_max']) for p in doc['boxes']+doc['cylinders']):
        raise ValueError('XY proof requires flight plane inside every obstacle height')
    minimum, lengths, count = math.inf, [], 0
    for i, leg in enumerate(routes):
        if len(leg) < 2 or tuple(leg[0]) != LOOP_WAYPOINTS[i] or tuple(leg[-1]) != LOOP_WAYPOINTS[i+1]:
            raise ValueError('Missing or mismatched mission endpoint')
        if any(len(p) != 2 or not all(math.isfinite(v) and abs(v) <= FIELD_HALF_M for v in p) for p in leg):
            raise ValueError('Invalid route coordinates')
        lengths.append(sum(math.dist(a, b) for a, b in zip(leg, leg[1:])))
        for a, b in zip(leg, leg[1:]):
            count += 1
            distances = [segment_box_distance(a, b, box) for box in doc['boxes']]
            distances += [max(0., point_segment_distance((c['x'], c['y']), a, b)-c['r']) for c in doc['cylinders']]
            minimum = min(minimum, min(distances)-BODY_RADIUS_M)
    if minimum < REQUIRED_MARGIN_M:
        raise ValueError('A continuous route segment lacks the required body clearance')
    return dict(valid=True, min_body_clearance_m=minimum, required_body_margin_m=REQUIRED_MARGIN_M,
                robot_radius_m=BODY_RADIUS_M, flight_z_m=FLIGHT_Z_M,
                segment_count=count, leg_lengths_m=lengths, total_length_m=sum(lengths),
                method='Exact segment-to-solid-rectangle and segment-to-disk XY distances',
                node_body_margin_m=NODE_MARGIN_M, grid_step_m=GRID_STEP_M,
                conservative_edge_body_margin_bound_m=NODE_MARGIN_M-math.sqrt(2)*GRID_STEP_M/2,
                offline_routes_supplied_to_planner=False,
                scope='Static geometric connectivity at z1.5 only; no dynamics or flight qualification')


def connected_forest():
    rejected = []
    for attempt in range(1, 101):
        doc, provenance = forest_layout(FOREST_SEED+(attempt-1)*1000003)
        validate_geometry(doc)
        try:
            routes = offline_routes(doc)
            audit = route_audit(doc, routes)
        except ValueError as error:
            rejected.append(dict(attempt=attempt, actual_seed=provenance['actual_seed'], reason=str(error)))
            continue
        provenance.update(base_seed=FOREST_SEED, accepted_attempt=attempt, rejected_layouts=rejected,
                          selection='Whole-layout geometry-only endpoint/connectivity rejection; zero flight observations')
        return doc, routes, audit, provenance
    raise ValueError('No connected forest found in 100 geometry-only attempts')


def statistics(doc):
    validate_geometry(doc)
    kind = 'boxes' if doc['boxes'] else 'cylinders'
    items = doc[kind]
    nearest = [min(pair_gap(a, b, kind) for j, b in enumerate(items) if i != j) for i, a in enumerate(items)]
    area = 4096.
    occupied = sum(p['size_x']*p['size_y'] for p in doc['boxes'])+sum(math.pi*p['r']**2 for p in doc['cylinders'])
    bins = (0., .1, .25, .5, 1., 2., math.inf)
    return dict(box_count=len(doc['boxes']), cylinder_count=len(doc['cylinders']),
                obstacle_count=len(items), field_area_m2=area, obstacle_density_per_m2=len(items)/area,
                obstacle_density_per_100m2=len(items)/area*100., obstacle_xy_area_fraction=occupied/area,
                height_m=items[0]['z_max']-items[0]['z_min'],
                min_surface_gap_m=min(nearest), nearest_surface_gap_mean_m=float(np.mean(nearest)),
                nearest_surface_gap_sd_m=float(np.std(nearest, ddof=1)),
                nearest_surface_gap_quantiles_m={f'p{p:02d}': float(np.percentile(nearest, p)) for p in (0, 5, 10, 25, 50, 75, 90, 95, 100)},
                nearest_gap_below_1m_count=sum(g < 1. for g in nearest),
                nearest_surface_gap_histogram=[dict(lower_m=low, upper_m=high if math.isfinite(high) else None,
                                                     count=sum(low <= g < high for g in nearest)) for low, high in zip(bins, bins[1:])],
                nearest_surface_gaps_m=nearest,
                nearest_gap_scope='Nearest surface gap per primitive; mutual pairs counted once for each endpoint')


def inclusive_axis(low, high, spacing):
    count = max(1, int(math.ceil((high-low)/spacing)))
    return [low+(high-low)*i/count for i in range(count+1)]


def primitive_points(doc):
    for box in doc['boxes']:
        xmin, xmax, ymin, ymax = box_bounds(box)
        xs, ys, zs = inclusive_axis(xmin, xmax, SURFACE_DS_M), inclusive_axis(ymin, ymax, SURFACE_DS_M), inclusive_axis(box['z_min'], box['z_max'], Z_STEP_M)
        for y in (ymin, ymax):
            for x in xs:
                for z in zs:
                    yield x, y, z
        for x in (xmin, xmax):
            for y in ys:
                for z in zs:
                    yield x, y, z
        for z in (box['z_min'], box['z_max']):
            for x in xs:
                for y in ys:
                    yield x, y, z
    for c in doc['cylinders']:
        ntheta = max(8, round(2*math.pi*c['r']/SURFACE_DS_M))
        for z in inclusive_axis(c['z_min'], c['z_max'], Z_STEP_M):
            for i in range(ntheta):
                angle = 2*math.pi*i/ntheta
                yield c['x']+c['r']*math.cos(angle), c['y']+c['r']*math.sin(angle), z


def point_count(doc):
    total = 0
    for box in doc['boxes']:
        nx, ny, nz = (math.ceil(box['size_x']/SURFACE_DS_M)+1,
                      math.ceil(box['size_y']/SURFACE_DS_M)+1,
                      math.ceil((box['z_max']-box['z_min'])/Z_STEP_M)+1)
        total += 2*(nx*nz+ny*nz+nx*ny)
    for c in doc['cylinders']:
        total += max(8, round(2*math.pi*c['r']/SURFACE_DS_M))*(math.ceil((c['z_max']-c['z_min'])/Z_STEP_M)+1)
    return total


def write_pcd(path, doc):
    count = point_count(doc)
    with path.open('x') as stream:
        stream.write('# .PCD v0.7 - Point Cloud Data file format\nVERSION 0.7\nFIELDS x y z intensity\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n')
        stream.write(f'WIDTH {count}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {count}\nDATA ascii\n')
        written = 0
        for x, y, z in primitive_points(doc):
            stream.write(f'{x:.6f} {y:.6f} {z:.6f} 1.0\n')
            written += 1
    if count != written:
        raise ValueError('PCD point count mismatch')
    return count


def mirror_target(path):
    relative = path.relative_to(PACKAGE)
    return MIRROR/('perfect_drone_sim_'+relative.parts[0])/Path(*relative.parts[1:])


def copy_exclusive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_assets(name):
    return (PACKAGE/'config'/f'{name}.yaml', PACKAGE/'pcd/seed_maps'/f'{name}.pcd',
            PACKAGE/'pcd/seed_maps'/f'{name}_geometry.json')


def config_text(name):
    base = (PACKAGE/'config/seed1.yaml').read_text()
    old = 'pcd_name: "seed_maps/seed1.pcd"'
    if base.count(old) != 1:
        raise ValueError('Unexpected seed1 config; refusing implicit parameter changes')
    return base.replace(old, f'pcd_name: "seed_maps/{name}.pcd"')


def write_overview(path, records):
    # The installed Matplotlib binary uses system NumPy. Isolate rendering from
    # user-site NumPy upgrades without changing packages or the calling process.
    subprocess.run([sys.executable, '-s', str(Path(__file__).resolve()),
                    '--render-overview', str(path)], input=json.dumps(records),
                   text=True, check=True)


def render_overview(path, records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)
    for ax, row in zip(axes, records):
        doc = row['_geometry']
        for box in doc['boxes']:
            xmin, _, ymin, _ = box_bounds(box)
            ax.add_patch(Rectangle((xmin, ymin), box['size_x'], box['size_y'], facecolor='#697586', edgecolor='white', lw=.5))
        for c in doc['cylinders']:
            ax.add_patch(Circle((c['x'], c['y']), c['r'], facecolor='#43734a' if c['role'] != 'background' else '#93a99a', edgecolor='none'))
        nominal = np.array(LOOP_WAYPOINTS)
        ax.plot(nominal[:, 0], nominal[:, 1], '--', color='#478dc9', lw=1., label='Nominal loop24')
        for i, route in enumerate(row['geometric_routes_xy']):
            route = np.array(route)
            ax.plot(route[:, 0], route[:, 1], color='#f7a21b', lw=1.1, label='Offline connectivity witness' if i == 0 else None)
        ax.scatter(nominal[:-1, 0], nominal[:-1, 1], marker='x', c='#d22238', s=30, label='Mission endpoints')
        stats = row['statistics']
        title = 'U1: 16 buildings, 6×8×6 m' if row['family'] == 'urban' else 'F1: 410 trunks, d=1 m, h=4 m; 10 clusters + background'
        ax.set(xlim=(-32, 32), ylim=(-32, 32), aspect='equal', xlabel='x (m)', ylabel='y (m)',
               title=title+'\n'+f"Footprint {stats['obstacle_xy_area_fraction']:.1%} | minimum gap {stats['min_surface_gap_m']:.4f} m")
        ax.legend(loc='lower left', fontsize=7)
        ax.grid(alpha=.12)
    fig.suptitle('Added scenario maps — geometric validation only; zero flight tests\nWitnesses are not supplied to the planner', fontsize=12)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def assert_hashes(inventory):
    for name, digest in inventory.items():
        if not Path(name).is_file() or sha256(name) != digest:
            raise ValueError('Missing or changed asset: '+name)


def verify_existing(output=OUTPUT):
    manifest = json.loads((Path(output)/'manifest.json').read_text())
    if manifest.get('schema') != 'scenario7-added-maps-v1' or [r['map'] for r in manifest['maps']] != list(MAP_NAMES):
        raise ValueError('Unexpected suite manifest')
    for key in ('generator_sha256', 'protected_existing_assets_sha256', 'report_assets_sha256'):
        assert_hashes(manifest[key])
    for row in manifest['maps']:
        assert_hashes(row['assets_sha256'])
        cfg, pcd, geometry_path = source_assets(row['map'])
        doc = json.loads(geometry_path.read_text())
        if statistics(doc) != row['statistics'] or route_audit(doc, row['geometric_routes_xy']) != row['route_audit']:
            raise ValueError('Analytical geometry no longer agrees with manifest')
        if cfg.read_text() != config_text(row['map']) or point_count(doc) != row['point_count']:
            raise ValueError('Config or sampling metadata mismatch')
    return manifest


def generate(output=OUTPUT):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; use --verify-existing for immutable reuse')
    generator = Path(__file__).resolve()
    test = PACKAGE/'test/test_gen_scenario7_maps.py'
    targets = [mirror_target(generator), mirror_target(test)]
    for name in MAP_NAMES:
        assets = source_assets(name)
        targets += [*assets, *(mirror_target(p) for p in assets), INSTALL_CONFIG/f'{name}.yaml']
    for target in targets:
        if target.exists():
            raise ValueError('Refusing to overwrite existing target: '+str(target))
    started = time.monotonic()
    protected = sorted(p for p in (PACKAGE/'pcd/seed_maps').rglob('*') if p.is_file())
    protected += sorted((PACKAGE/'config').glob('*.yaml'))
    original_hashes = {str(p): sha256(p) for p in protected}
    urban = urban_layout()
    validate_geometry(urban)
    routes = offline_routes(urban)
    records = [dict(map=MAP_NAMES[0], label='U1', family='urban', _geometry=urban,
                    statistics=statistics(urban), geometric_routes_xy=routes,
                    route_audit=route_audit(urban, routes),
                    proposal_provenance=dict(layout='Cartesian 4×4 block grid; x/y centers −19,−7,7,19m',
                                             nominal_internal_street_widths_m=[4., 6., 8.], random_seed=None,
                                             selection='Deterministic design and geometry-only certification'))]
    forest, routes, audit, provenance = connected_forest()
    records.append(dict(map=MAP_NAMES[1], label='F1', family='forest', _geometry=forest,
                        statistics=statistics(forest), geometric_routes_xy=routes,
                        route_audit=audit, proposal_provenance=provenance))
    # All geometry is validated before any new asset is published.
    output.mkdir(parents=True, exist_ok=False)
    copy_exclusive(generator, mirror_target(generator))
    copy_exclusive(test, mirror_target(test))
    for row in records:
        name = row['map']
        cfg, pcd, geometry_path = source_assets(name)
        save_json(geometry_path, row['_geometry'])
        row['point_count'] = write_pcd(pcd, row['_geometry'])
        with cfg.open('x') as stream:
            stream.write(config_text(name))
        for source in (cfg, pcd, geometry_path):
            copy_exclusive(source, mirror_target(source))
        copy_exclusive(cfg, INSTALL_CONFIG/cfg.name)
        save_json(output/f'{name}_routes.json', dict(map=name, routes=row['geometric_routes_xy'], audit=row['route_audit']))
        row['assets_sha256'] = {str(p): sha256(p) for p in
            (cfg, pcd, geometry_path, *(mirror_target(p) for p in (cfg, pcd, geometry_path)), INSTALL_CONFIG/cfg.name)}
        print(name, 'points', row['point_count'], 'minimum gap', row['statistics']['min_surface_gap_m'],
              'continuous body clearance', row['route_audit']['min_body_clearance_m'], flush=True)
    write_overview(output/'overview.png', records)
    assert_hashes(original_hashes)
    manifest = dict(schema='scenario7-added-maps-v1', maps=[{k: v for k, v in row.items() if not k.startswith('_')} for row in records],
        field_xy_bounds_m=[-32., 32.], initial_position_xyz_m=[0., 0., 1.5], body_radius_m=BODY_RADIUS_M,
        mission='loop24', loop_waypoints_xy=LOOP_WAYPOINTS, flight_runs=0,
        existing_map_assets_unchanged=True, planner_algorithm_sensor_changed=False,
        global_minimum_surface_gap_m=0., minimum_1m_gap_imposed=False,
        protected_start_goal_pockets=False, cleared_nominal_route_tube=False,
        sampling=dict(horizontal_or_circumferential_target_m=SURFACE_DS_M, vertical_step_m=Z_STEP_M,
            serialization='ASCII PCD xyz + intensity1.0, six decimals', floor_added=False,
            urban='All six box faces; shared edge samples retained, roof/bottom restricted to building footprints',
            forest='Lateral cylinder surfaces including boundary rings, 63 samples per ring; same convention as existing gapfree maps',
            cylinder_caps='Solid collision model includes caps; PCD has no filled cap disks, matching existing cylinders',
            vertical_changes='Existing gapfree cylinders H3m; new forest H4m; new buildings H6m. Separate families, not a matched-height intervention.',
            interpretation='PCD rendering is sampled-surface geometry; solid truth and geometric route proof use analytic primitives'),
        generator_sha256={str(p): sha256(p) for p in (generator, test, mirror_target(generator), mirror_target(test))},
        protected_existing_assets_sha256=original_hashes,
        report_assets_sha256={str(p): sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
        generation_wall_seconds=time.monotonic()-started)
    save_json(output/'manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--verify-existing', action='store_true')
    parser.add_argument('--render-overview', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.render_overview:
        if args.render_overview.exists():
            raise ValueError('Refusing to overwrite existing overview')
        render_overview(args.render_overview, json.load(sys.stdin))
        return
    manifest = verify_existing(args.output) if args.verify_existing else generate(args.output)
    print(json.dumps(dict(status='verified' if args.verify_existing else 'generated',
                          maps=[r['map'] for r in manifest['maps']], output=str(args.output), flight_runs=0)))


if __name__ == '__main__':
    main()
