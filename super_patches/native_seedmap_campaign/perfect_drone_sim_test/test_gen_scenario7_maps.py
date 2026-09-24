"""Offline solid geometry tests; no simulator, ROS, or flight process."""
import copy
import json
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import gen_scenario7_maps as maps


def test_urban_geometry_and_nonoverlap():
    doc = maps.urban_layout()
    assert maps.validate_geometry(doc)
    stats = maps.statistics(doc)
    assert stats['box_count'] == 16
    assert stats['min_surface_gap_m'] == 4.
    assert stats['obstacle_xy_area_fraction'] == 16*6*8/4096
    assert maps.point_count(doc) == 1173856


def test_forest_reproducibility_clustering_density_and_gap():
    a, pa = maps.forest_layout()
    b, pb = maps.forest_layout()
    assert a == b and pa == pb
    assert maps.validate_geometry(a)
    roles = [c['role'] for c in a['cylinders']]
    assert roles.count('background') == 140
    assert all(roles.count(f'cluster_{i:02d}') == 27 for i in range(1, 11))
    stats = maps.statistics(a)
    assert stats['cylinder_count'] == 410
    assert stats['obstacle_density_per_m2'] == 410/4096
    assert stats['obstacle_xy_area_fraction'] == pytest.approx(410*math.pi*.25/4096)
    assert 0 <= stats['min_surface_gap_m'] < 1.
    assert stats['nearest_gap_below_1m_count'] > 270
    assert maps.point_count(a) == 1059030


@pytest.mark.parametrize('reason', ['overlap', 'nonfinite', 'boundary', 'dimension', 'count', 'id'])
def test_invalid_solids_refused(reason):
    doc = maps.urban_layout()
    if reason == 'overlap':
        doc['boxes'][1].update(cx=doc['boxes'][0]['cx'], cy=doc['boxes'][0]['cy'])
    elif reason == 'nonfinite':
        doc['boxes'][0]['cx'] = float('nan')
    elif reason == 'boundary':
        doc['boxes'][0]['cx'] = 31.
    elif reason == 'dimension':
        doc['boxes'][0]['z_max'] = 3.
    elif reason == 'count':
        doc['boxes'].pop()
    else:
        doc['boxes'][1]['id'] = doc['boxes'][0]['id']
    with pytest.raises(ValueError):
        maps.validate_geometry(doc)


@pytest.mark.parametrize('a,b,expected', [
    ((-4., 0.), (4., 0.), 0.),       # end points clear, middle intersects
    ((-4., 2.), (4., 2.), 1.),       # closest point is edge interior
    ((2., 2.), (3., 3.), math.sqrt(2)),
    ((2., 2.), (2., 2.), math.sqrt(2)),
    ((-3., 1.), (3., 1.), 0.),       # grazing boundary
    ((1.5, 3.), (3., 1.5), 2.5/math.sqrt(2)),  # closest is corner to segment interior
])
def test_exact_segment_box_distance(a, b, expected):
    box = dict(cx=0., cy=0., size_x=2., size_y=2.)
    assert maps.segment_box_distance(a, b, box) == pytest.approx(expected)


@pytest.mark.parametrize('kind', ['boxes', 'cylinders'])
def test_whole_route_segments_checked(kind):
    doc = maps.scene('test')
    if kind == 'boxes':
        doc['boxes'] = [dict(cx=12., cy=12., size_x=2., size_y=2., z_min=0., z_max=6.)]
    else:
        doc['cylinders'] = [dict(x=12., y=12., r=.5, z_min=0., z_max=4.)]
    routes = [[a, b] for a, b in zip(maps.LOOP_WAYPOINTS, maps.LOOP_WAYPOINTS[1:])]
    with pytest.raises(ValueError, match='continuous route segment'):
        maps.route_audit(doc, routes)


def test_routes_preserve_exact_endpoints_and_certify_continuous_clearance():
    doc = maps.urban_layout()
    routes = maps.offline_routes(doc)
    audit = maps.route_audit(doc, routes)
    assert audit['valid'] and audit['min_body_clearance_m'] >= .35
    assert not audit['offline_routes_supplied_to_planner']
    with pytest.raises(ValueError, match='five mission legs'):
        maps.route_audit(doc, routes[:-1])
    bad = copy.deepcopy(routes)
    bad[0].insert(1, (float('nan'), 0.))
    with pytest.raises(ValueError, match='Invalid route'):
        maps.route_audit(doc, bad)


def test_existing_output_never_overwritten(tmp_path):
    with pytest.raises(ValueError, match='already exists'):
        maps.generate(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_overview_uses_compatible_system_plotting_environment(tmp_path):
    doc = maps.urban_layout()
    row = dict(_geometry=doc, geometric_routes_xy=[], family='urban', statistics=maps.statistics(doc))
    output = tmp_path/'overview.png'
    maps.write_overview(output, [row])
    assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    with pytest.raises(Exception):
        maps.write_overview(output, [row])


def test_generated_suite_geometry_hashes_and_sensor_config():
    if not (maps.OUTPUT/'manifest.json').exists():
        pytest.skip('Suite not generated yet')
    manifest = maps.verify_existing()
    assert manifest['flight_runs'] == 0
    assert not manifest['planner_algorithm_sensor_changed']
    assert not manifest['sampling']['floor_added']
    for row in manifest['maps']:
        geometry = json.loads(maps.source_assets(row['map'])[2].read_text())
        assert maps.validate_geometry(geometry)
        assert row['route_audit']['min_body_clearance_m'] >= .35
