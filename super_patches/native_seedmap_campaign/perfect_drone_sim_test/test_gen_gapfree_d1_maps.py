"""Offline geometry, reproducibility and generated asset tests; never ROS flights."""
import csv
import json
import math
from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import gen_gapfree_d1_maps as maps


def test_uniform_layout_is_reproducible_and_removes_1m_spacing():
    a,n=maps.layout(2026091801)
    b,m=maps.layout(2026091801)
    assert a==b and n==m
    assert len(a)==410 and maps.validate_cylinders(a)>=0
    stats=maps.statistics(a)
    assert 0<=stats['min_surface_gap_m']<1
    assert stats['nearest_gap_below_1m_count']>0
    assert sum(x['count'] for x in stats['nearest_surface_gap_histogram'])==410
    assert stats['obstacle_density_per_m2']==410/4096
    assert stats['obstacle_xy_area_fraction']==410*math.pi*.5**2/4096


def test_different_seeds_change_positions_only():
    a,_=maps.layout(2026091801)
    b,_=maps.layout(2026091802)
    assert a!=b
    assert len(a)==len(b)==410
    assert {c.radius for c in a+b}=={.5}


@pytest.mark.parametrize('reason',['overlap','radius','nonfinite','boundary','count'])
def test_bad_analytic_geometry_refused(reason):
    c,_=maps.layout(2026091801)
    if reason=='overlap': c[1]=c[0]
    elif reason=='radius': c[0]=c[0]._replace(radius=.6)
    elif reason=='nonfinite': c[0]=c[0]._replace(x=float('nan'))
    elif reason=='boundary': c[0]=c[0]._replace(x=32.)
    else:c.pop()
    with pytest.raises(ValueError):maps.validate_cylinders(c)


def test_whole_segments_checked_not_just_endpoints():
    routes=[[a,b] for a,b in zip(maps.geometry.LOOP_WAYPOINTS,maps.geometry.LOOP_WAYPOINTS[1:])]
    obstacle=[maps.geometry.Cylinder(12.,12.,.5)]
    with pytest.raises(ValueError):maps.route_audit(obstacle,routes)


def test_missing_leg_and_nonfinite_route_refused():
    routes=[[a,b] for a,b in zip(maps.geometry.LOOP_WAYPOINTS,maps.geometry.LOOP_WAYPOINTS[1:])]
    with pytest.raises(ValueError):maps.route_audit([],routes[:-1])
    routes[0].insert(1,(float('nan'),1.))
    with pytest.raises(ValueError):maps.route_audit([],routes)


def test_existing_output_never_overwritten(tmp_path):
    marker=tmp_path/'original.txt'
    marker.write_text('preserve')
    with pytest.raises(ValueError):maps.generate(tmp_path)
    assert marker.read_text()=='preserve'


def test_generated_suite_and_all_exact_asset_hashes():
    manifest=maps.OUTPUT/'manifest.json'
    if not manifest.exists():pytest.skip('Maps not yet generated')
    doc=json.loads(manifest.read_text())
    assert doc['flight_runs']==0 and doc['minimum_1m_gap_removed']
    assert not doc['protected_start_goal_pockets'] and not doc['cleared_nominal_route_tube']
    assert not doc['planner_algorithm_sensor_changed']
    assert len(doc['maps'])==5 and len({r['map'] for r in doc['maps']})==5
    for path,digest in doc['generator_sha256'].items():assert maps.geometry.sha256(Path(path))==digest
    base=yaml.safe_load((maps.PACKAGE/'config/seed1.yaml').read_text())
    for row in doc['maps']:
        for path,digest in row['assets_sha256'].items():assert maps.geometry.sha256(Path(path))==digest
        name=row['map']; csv_path=maps.PACKAGE/'pcd/seed_maps'/f'{name}_cylinders.csv'
        with csv_path.open() as stream:
            cylinders=[maps.geometry.Cylinder(float(r['x']),float(r['y']),float(r['r']),r['role'])
                       for r in csv.DictReader(stream)]
        assert maps.validate_cylinders(cylinders)>=0
        assert maps.statistics(cylinders)==row['statistics']
        assert maps.route_audit(cylinders,row['geometric_routes_xy'])==row['route_audit']
        config=yaml.safe_load((maps.PACKAGE/'config'/f'{name}.yaml').read_text())
        assert config.pop('pcd_name')==f'seed_maps/{name}.pcd'
        expected=dict(base);expected.pop('pcd_name');assert config==expected
        assert row['point_count']==800730
        assert row['route_audit']['min_body_clearance_m']>=.35
