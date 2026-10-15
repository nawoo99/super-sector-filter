"""Offline tests for the disclosed G5-R2 map-only revision."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import revise_gapfree_d1_m05 as revision


def test_revision_moves_only_cylinder199_and_keeps_geometry_contract():
    old = revision.read_cylinders(
        revision.base.PACKAGE/'pcd/seed_maps'/f'{revision.OLD_NAME}_cylinders.csv')
    cylinders, routes, route, stats, minimum = revision.revised_geometry()
    assert len(old) == len(cylinders) == revision.base.COUNT == 410
    changed = [index for index,(before,after) in enumerate(zip(old,cylinders))
               if before != after]
    assert changed == [revision.RELOCATED_INDEX]
    moved = cylinders[revision.RELOCATED_INDEX]
    assert moved[:2] == revision.NEW_CENTER and moved.radius == .5
    assert moved.role == revision.ROLE
    assert minimum >= 0 and stats['min_surface_gap_m'] == minimum
    assert route['valid'] and route['min_body_clearance_m'] >= .35
    assert len(routes) == len(revision.base.geometry.LOOP_WAYPOINTS)-1


def test_existing_revision_output_is_never_overwritten(tmp_path):
    output=tmp_path/'existing';output.mkdir()
    marker=output/'marker';marker.write_text('preserve')
    with pytest.raises(ValueError,match='never overwrite'):
        revision.generate(output)
    assert marker.read_text() == 'preserve'


def test_generated_revision_manifest_and_assets_match():
    manifest=revision.OUTPUT/'manifest.json'
    if not manifest.exists():
        pytest.skip('G5-R2 has not been generated yet')
    document=json.loads(manifest.read_text())
    assert document['schema']=='gapfree-diameter1-static-suite-r2-v1'
    assert tuple(row['map'] for row in document['maps']) == (
        'gapfree_d1_m01','gapfree_d1_m02','gapfree_d1_m03','gapfree_d1_m04',revision.NEW_NAME)
    assert document['revision']['map_revision_informed_by_prior_flight'] is True
    assert document['revision']['planner_algorithm_sensor_changed'] is False
    row=document['maps'][-1]
    assert row['proposal_provenance']['flight_observations_used_for_relocation'] is True
    assert row['statistics']['cylinder_count']==410
    assert row['statistics']['diameter_m']==1.0
    for path,digest in row['assets_sha256'].items():
        assert revision.base.geometry.sha256(Path(path))==digest
    for path,digest in document['generator_sha256'].items():
        assert revision.base.geometry.sha256(Path(path))==digest
