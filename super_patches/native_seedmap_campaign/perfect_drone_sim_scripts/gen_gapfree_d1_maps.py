#!/usr/bin/env python3
"""Five static, diameter-1m maps: disjoint cylinders and offline connectivity only.

No ROS process, planner changes, flight test, reserved route tube, or 1m gap
constraint. Reuse the campaign's PCD serializer and offline route checker;
record their hashes. Geometry filtering is disclosed, not flight qualification.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
import shutil
import sys

import numpy as np

CAMPAIGN = Path('/root/super-sector-filter/scripts/native_campaign')
sys.path.insert(0, str(CAMPAIGN))
import gen_cylinder_only_stress as geometry
import cylinder_forest_geometry as connectivity

PACKAGE = Path(__file__).resolve().parents[1]
MIRROR = Path('/root/super-sector-filter/super_patches/native_seedmap_campaign')
INSTALL_CONFIG = Path('/root/super_ws/install/perfect_drone_sim/share/perfect_drone_sim/config')
OUTPUT = Path('/root/super-sector-filter/results/gapfree_d1_maps_20260918')
DIAMETER_M = 1.0
RADIUS_M = DIAMETER_M / 2
COUNT = 410
FIELD_HALF_M = 32.0
BODY_RADIUS_M = .20
CERTIFIED_BODY_MARGIN_M = .35
GRID_NODE_BODY_MARGIN_M = .45
GRID_STEP_M = .10
MAP_SPECS = tuple((f'G{i}', f'gapfree_d1_m{i:02d}', 2026091800+i) for i in range(1, 6))
GAP_BINS = (0., .1, .25, .5, 1., 2., math.inf)


def validate_cylinders(cylinders):
    if len(cylinders) != COUNT:
        raise ValueError('Expected exactly410 cylinders')
    if any(not all(math.isfinite(v) for v in c[:3]) or c.radius != RADIUS_M
           or abs(c.x)+c.radius > FIELD_HALF_M or abs(c.y)+c.radius > FIELD_HALF_M
           for c in cylinders):
        raise ValueError('Invalid diameter, finite coordinate, or field extent')
    gap = min(geometry.surface_gap(a, b) for i, a in enumerate(cylinders) for b in cylinders[i+1:])
    if gap < 0:
        raise ValueError('Overlapping cylinders')
    return gap


def layout(seed):
    rng = random.Random(seed)
    cylinders, proposals = [], 0
    limit = FIELD_HALF_M - RADIUS_M
    while len(cylinders) < COUNT and proposals < 100000:
        proposals += 1
        # Quantize BEFORE overlap checking so the analytic CSV geometry is exact.
        c = geometry.Cylinder(round(rng.uniform(-limit, limit), 6),
            round(rng.uniform(-limit, limit), 6), RADIUS_M, 'uniform_disjoint')
        if any(geometry.surface_gap(c, d) < 0 for d in cylinders):
            continue
        cylinders.append(c)
    if len(cylinders) != COUNT:
        raise ValueError('Nonoverlap placement did not reach the requested count')
    validate_cylinders(cylinders)
    return cylinders, proposals


def route_audit(cylinders, routes):
    if len(routes) != len(geometry.LOOP_WAYPOINTS)-1:
        raise ValueError('Missing mission legs')
    minimum, lengths, segments = math.inf, [], 0
    for i, leg in enumerate(routes):
        if len(leg) < 2 or tuple(leg[0]) != geometry.LOOP_WAYPOINTS[i] or tuple(leg[-1]) != geometry.LOOP_WAYPOINTS[i+1]:
            raise ValueError('Offline route does not connect the exact mission endpoints')
        if not all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in leg):
            raise ValueError('Invalid route coordinate')
        lengths.append(sum(math.dist(a, b) for a, b in zip(leg, leg[1:])))
        for a, b in zip(leg, leg[1:]):
            segments += 1
            minimum = min(minimum, *(geometry.point_segment_distance(c[:2], a, b)
                - c.radius - BODY_RADIUS_M for c in cylinders))
    if minimum < CERTIFIED_BODY_MARGIN_M:
        raise ValueError('Exact continuous XY segments lack required body margin')
    return dict(valid=True, min_body_clearance_m=minimum,
        required_body_margin_m=CERTIFIED_BODY_MARGIN_M, robot_radius_m=BODY_RADIUS_M,
        segment_count=segments, leg_lengths_m=lengths, total_length_m=sum(lengths),
        route_scope='Offline analytic XY at flight z1.5; all cylinders height3; not dynamics certification',
        offline_routes_supplied_to_planner=False)


def connected_layout(base_seed):
    rejected = []
    for attempt in range(1, 201):
        seed = base_seed + (attempt-1)*1000003
        cylinders, proposals = layout(seed)
        # Necessary endpoints plus the existing grid checker's conservative
        # node margin, NOT the old3m/2.5m start/goal pockets or2m route tube.
        endpoint_margin = min(math.dist(c[:2], point)-c.radius-BODY_RADIUS_M
            for c in cylinders for point in geometry.LOOP_WAYPOINTS[:-1])
        if endpoint_margin < GRID_NODE_BODY_MARGIN_M:
            rejected.append(dict(attempt=attempt, actual_seed=seed, reason='offline_endpoint_margin',
                                 min_endpoint_body_clearance_m=endpoint_margin))
            continue
        try:
            routes = connectivity.paths(cylinders)
            audit = route_audit(cylinders, routes)
        except ValueError as exc:
            rejected.append(dict(attempt=attempt, actual_seed=seed, reason='offline_connectivity', error=str(exc)))
            continue
        return cylinders, routes, audit, dict(base_seed=base_seed, actual_seed=seed, accepted_attempt=attempt,
            accepted_layout_coordinate_proposals=proposals, rejected_layouts=rejected,
            selection='Geometry only; no flight/performance observations')
    raise ValueError('No offline connected proposal found in200 geometric attempts')


def statistics(cylinders):
    validate_cylinders(cylinders)
    xy = np.array([c[:2] for c in cylinders], dtype=float)
    gap = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2) - DIAMETER_M
    np.fill_diagonal(gap, np.inf)
    nearest = gap.min(axis=1)
    histogram = []
    for low, high in zip(GAP_BINS, GAP_BINS[1:]):
        n = int(np.count_nonzero((nearest >= low) & (nearest < high)))
        histogram.append(dict(lower_m=low, upper_m=high if math.isfinite(high) else None,
                              count=n, fraction=n/len(cylinders)))
    area = (2*FIELD_HALF_M)**2
    return dict(cylinder_count=len(cylinders), diameter_m=DIAMETER_M,
        height_m=geometry.OBSTACLE_HEIGHT_M, field_area_m2=area,
        obstacle_density_per_m2=len(cylinders)/area,
        obstacle_density_per_100m2=len(cylinders)/area*100,
        obstacle_xy_area_fraction=len(cylinders)*math.pi*RADIUS_M**2/area,
        min_surface_gap_m=float(nearest.min()), nearest_surface_gap_mean_m=float(nearest.mean()),
        nearest_surface_gap_sd_m=float(nearest.std(ddof=1)),
        nearest_surface_gap_quantiles_m={f'p{p:02d}':float(np.percentile(nearest, p))
                                         for p in (0, 5, 10, 25, 50, 75, 90, 95, 100)},
        nearest_surface_gap_histogram=histogram,
        nearest_gap_below_1m_count=int(np.count_nonzero(nearest < 1.)),
        nearest_gap_scope='One nearest neighbor surface-to-surface gap per cylinder; mutual pairs counted per endpoint',
        nearest_surface_gaps_m=nearest.tolist())


def mirror_target(path):
    relative = path.relative_to(PACKAGE)
    return MIRROR / ('perfect_drone_sim_' + relative.parts[0]) / Path(*relative.parts[1:])


def copy_exclusive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def write_plots(output, records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), constrained_layout=True)
    for ax, row in zip(axes.flat, records):
        for c in row['_cylinders']:
            ax.add_patch(Circle(c[:2], c.radius, facecolor='#777777', edgecolor='none'))
        nominal = np.array(geometry.LOOP_WAYPOINTS)
        ax.plot(nominal[:, 0], nominal[:, 1], '--', color='#2972b6', lw=1, label='Nominal mission legs')
        for j, route in enumerate(row['_routes']):
            route = np.array(route)
            ax.plot(route[:, 0], route[:, 1], color='#138a36', lw=1,
                    label='Offline witness only' if j == 0 else None)
        ax.scatter(nominal[:-1, 0], nominal[:-1, 1], marker='x', color='#dc4b3b', s=24)
        ax.set(xlim=(-32,32), ylim=(-32,32), aspect='equal', xlabel='x (m)', ylabel='y (m)',
               title=f"{row['label']} | d=1m, n=410 | min gap={row['statistics']['min_surface_gap_m']:.4f}m")
    axes.flat[-1].axis('off')
    axes.flat[-1].text(.04,.96,'Same count, diameter, height and field\nOnly random placement differs\n\nGray: static cylinders\nBlue: nominal mission\nGreen: offline connectivity witness\n(not supplied to the planner)\n\nZero flight tests',va='top',fontsize=12)
    axes.flat[0].legend(loc='lower left',fontsize=7)
    fig.savefig(output/'map_overview.png', dpi=170)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,5), constrained_layout=True)
    for row in records:
        values = np.sort(row['statistics']['nearest_surface_gaps_m'])
        ax.step(values, np.arange(1,len(values)+1)/len(values), where='post', label=row['label'])
    ax.axvline(1., linestyle='--', color='#555555', label='Old 1m constraint (removed)')
    ax.set(xlabel='Nearest neighbor surface gap (m)',ylabel='Empirical cumulative fraction',ylim=(0,1),
           title='One nearest gap per cylinder; all maps diameter1m')
    ax.legend()
    ax.grid(alpha=.2)
    fig.savefig(output/'nearest_gap_cdf.png', dpi=170)
    plt.close(fig)


def generate(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; never overwrite a map suite')
    generator = Path(__file__).resolve()
    test = PACKAGE/'test/test_gen_gapfree_d1_maps.py'
    assets = []
    for _, name, _ in MAP_SPECS:
        sources = [PACKAGE/'config'/f'{name}.yaml', PACKAGE/'pcd/seed_maps'/f'{name}.pcd',
                   PACKAGE/'pcd/seed_maps'/f'{name}_cylinders.csv']
        assets.extend(sources + [mirror_target(p) for p in sources] + [INSTALL_CONFIG/f'{name}.yaml'])
    for path in assets + [mirror_target(generator), mirror_target(test)]:
        if path.exists():
            raise ValueError('Refusing existing target: '+str(path))
    # Complete geometry first; failed generation cannot partially replace old assets.
    records = []
    for label, name, seed in MAP_SPECS:
        cylinders, routes, audit, provenance = connected_layout(seed)
        stats = statistics(cylinders)
        print(name, 'geometry PASS', 'seed', provenance['actual_seed'],
              'attempt',provenance['accepted_attempt'],'min gap',stats['min_surface_gap_m'],
              'body margin',audit['min_body_clearance_m'],flush=True)
        records.append(dict(label=label,map=name,statistics=stats,route_audit=audit,
            geometric_routes_xy=routes,proposal_provenance=provenance,_cylinders=cylinders,_routes=routes))
    output.mkdir(parents=True, exist_ok=False)
    copy_exclusive(generator, mirror_target(generator))
    copy_exclusive(test, mirror_target(test))
    for row in records:
        name = row['map']
        csv_path = PACKAGE/'pcd/seed_maps'/f'{name}_cylinders.csv'
        pcd_path = PACKAGE/'pcd/seed_maps'/f'{name}.pcd'
        config_path = PACKAGE/'config'/f'{name}.yaml'
        geometry.write_cylinder_csv(csv_path,row['_cylinders'])
        points = geometry.write_pcd(pcd_path,row['_cylinders'])
        # Preserve every simulator/sensor parameter verbatim; only pcd_name changes.
        source_config = PACKAGE/'config/seed1.yaml'
        content = source_config.read_text()
        old = 'pcd_name: "seed_maps/seed1.pcd"'
        if content.count(old) != 1:
            raise ValueError('Unexpected base configuration; no implicit parameter rewrite')
        with config_path.open('x') as stream:
            stream.write(content.replace(old,f'pcd_name: "seed_maps/{name}.pcd"'))
        for source in (csv_path,pcd_path,config_path):
            copy_exclusive(source,mirror_target(source))
        copy_exclusive(config_path,INSTALL_CONFIG/config_path.name)
        # Store analytical geometry alongside the manifest for later contact audits.
        copy_exclusive(csv_path,output/csv_path.name)
        row['point_count'] = points
        row['assets_sha256'] = {str(p):geometry.sha256(p) for p in (
            csv_path,pcd_path,config_path,*(mirror_target(p) for p in (csv_path,pcd_path,config_path)),
            INSTALL_CONFIG/config_path.name,output/csv_path.name)}
        nearest = row['statistics']['nearest_surface_gaps_m']
        with (output/f'{name}_nearest_gaps.csv').open('x',newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(('cylinder_index','x','y','radius_m','nearest_surface_gap_m'))
            for i, (c, gap) in enumerate(zip(row['_cylinders'],nearest)):
                writer.writerow((i,c.x,c.y,c.radius,gap))
        save_json(output/f'{name}_routes.json',dict(map=name,routes=row['_routes'],audit=row['route_audit']))
    write_plots(output,records)
    serializable = [{k:v for k,v in r.items() if not k.startswith('_')} for r in records]
    save_json(output/'manifest.json',dict(schema='gapfree-diameter1-static-suite-v1',maps=serializable,
        same_count_height_field_across_maps=True,minimum_1m_gap_removed=True,
        enforced_pairwise_surface_gap_m=0.,overlap_allowed=False,
        placement='Uniform random sequential nonoverlap placement, same field/count/d1 across5 seeds',
        protected_start_goal_pockets=False,cleared_nominal_route_tube=False,
        connectivity_policy=dict(robot_radius_m=BODY_RADIUS_M,required_body_margin_m=CERTIFIED_BODY_MARGIN_M,
            grid_node_body_margin_m=GRID_NODE_BODY_MARGIN_M,grid_step_m=GRID_STEP_M,
            all_five_loop24_legs_checked=True,exact_continuous_xy_segments_checked=True,
            vertical_scope='z1.5 inside cylinders z0..3, analytic radius.5',
            geometry_not_dynamics=True,offline_routes_supplied_to_planner=False),
        proposal_selection='Only geometric criteria, including conservative endpoint/grid clearance; no flights observed',
        generator_sha256={str(p):geometry.sha256(p) for p in (
            generator,test,mirror_target(generator),mirror_target(test),
            CAMPAIGN/'gen_cylinder_only_stress.py',CAMPAIGN/'cylinder_forest_geometry.py')},
        base_simulator_config=dict(path=str(PACKAGE/'config/seed1.yaml'),sha256=geometry.sha256(PACKAGE/'config/seed1.yaml'),
                                  only_changed_key='pcd_name'),
        planner_algorithm_sensor_changed=False,old_maps_or_results_modified=False,
        flight_runs=0,final_performance_qualified=False,future_requested_flights=75,
        future_plan='5maps ×3modes ×5runs; not authorized to launch in this map-only request'))
    columns = ['label','map','cylinder_count','diameter_m','height_m','min_surface_gap_m',
        'nearest_surface_gap_mean_m','nearest_surface_gap_sd_m','nearest_p10_m','nearest_p50_m','nearest_p90_m',
        'obstacle_density_per_m2','obstacle_xy_area_fraction','nearest_gap_below_1m_count',
        'offline_min_body_clearance_m','offline_path_length_m','point_count','accepted_geometric_attempt']
    with (output/'summary.csv').open('x',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        for row in records:
            s=row['statistics']
            writer.writerow(dict(label=row['label'],map=row['map'],**{k:s[k] for k in columns if k in s},
                **{f'nearest_p{p}_m':s['nearest_surface_gap_quantiles_m'][f'p{p}'] for p in (10,50,90)},
                offline_min_body_clearance_m=row['route_audit']['min_body_clearance_m'],
                offline_path_length_m=row['route_audit']['total_length_m'],point_count=row['point_count'],
                accepted_geometric_attempt=row['proposal_provenance']['accepted_attempt']))
    print('MAPS ONLY COMPLETE',output,flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args(argv)
    generate(args.output)


if __name__ == '__main__':
    main()
