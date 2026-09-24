"""Per-map mission identity, monitor agreement and static proof tests; no ROS."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import scenario7_missions as missions


def test_exact_approved_missions_exclude_start_and_return_to_origin():
    urban = missions.expected_row('urban_blocks_u01')
    forest = missions.expected_row('forest_cluster_f01')
    assert urban['wps'] == '-24,25;24,13;-24,-13;24,-25;0,0'
    assert forest['wps'] == '-24,22;24,22;-24,-22;24,-22;0,0'
    for row in (urban, forest):
        assert row['goal_count'] == len(row['waypoints_xyz']) == 5
        assert row['waypoints_xyz'][-1] == [0., 0., 1.5]
        assert row['waypoints_xyz'][0] != row['initial_position_xyz']
        assert all(p[2] == 1.5 for p in row['waypoints_xyz'])
        txt = missions.mission_text(row['mission'])
        assert [list(map(float, line.split())) for line in txt.splitlines()] == [p+[1.5] for p in row['waypoints_xyz']]
    assert urban['nominal_total_length_m'] == pytest.approx(222.8548050753024)
    assert forest['nominal_total_length_m'] == pytest.approx(226.23056476879765)


def test_normal_five_maps_keep_exact_loop24():
    expected = '24 24 1.5 1.5\n-24 24 1.5 1.5\n-24 -24 1.5 1.5\n24 -24 1.5 1.5\n0 0 1.5 1.5\n'
    assert missions.mission_text('loop24') == expected
    for map_name in missions.ORIGINAL_MAPS:
        context = missions.expected_row(map_name)
        assert context['family'] == 'normal' and context['mission'] == 'loop24'
        assert context['wps'] == '24,24;-24,24;-24,-24;24,-24;0,0'


def test_unknown_map_fails_closed():
    with pytest.raises(ValueError, match='Unknown scenario7 map'):
        missions.mission_context('unapproved_map')


@pytest.fixture
def selected(tmp_path, monkeypatch):
    monkeypatch.setattr(missions, 'MISSION_DATA', tmp_path/'source')
    monkeypatch.setattr(missions, 'MIRROR_DATA', tmp_path/'mirror')
    monkeypatch.setattr(missions, 'INSTALLED_DATA', tmp_path/'install')
    row = missions.expected_row('urban_blocks_u01')
    for path in missions.mission_paths(row['mission']):
        path.parent.mkdir()
        path.write_text(missions.mission_text(row['mission']))
    row['assets_sha256'] = {str(p): missions.sha256(p) for p in missions.mission_paths(row['mission'])}
    row['mission_sha256'] = row['assets_sha256'][row['mission_file']]
    return row, dict(row['assets_sha256'])


def test_selected_identity_hashes_and_txt_agree(selected):
    row, inventory = selected
    assert missions.validate_row('urban_blocks_u01', row, inventory) == row


@pytest.mark.parametrize('field,value', [('mission', 'loop24'), ('wps', '0,0'), ('goal_count', 6),
                                        ('height_m', 2.), ('switch_distance_m', 2.)])
def test_registry_cannot_silently_change_approved_mission(selected, field, value):
    row, inventory = selected
    row[field] = value
    with pytest.raises(ValueError, match='Approved mission definition changed'):
        missions.validate_row('urban_blocks_u01', row, inventory)


def test_rehashed_wrong_txt_still_fails(selected):
    row, inventory = selected
    for path in missions.mission_paths(row['mission']):
        path.write_text('0 0 1.5 1.5\n')
        row['assets_sha256'][str(path)] = missions.sha256(path)
        inventory[str(path)] = missions.sha256(path)
    row['mission_sha256'] = row['assets_sha256'][row['mission_file']]
    with pytest.raises(ValueError, match='TXT differs'):
        missions.validate_row('urban_blocks_u01', row, inventory)


def test_missing_installed_binding_fails(selected):
    row, inventory = selected
    del row['assets_sha256'][row['installed_mission_file']]
    with pytest.raises(ValueError, match='Incomplete'):
        missions.validate_row('urban_blocks_u01', row, inventory)


def test_runtime_import_avoids_geometry_and_plot_modules():
    script = str(missions.PACKAGE/'scripts')
    code = ('import sys;sys.path.insert(0,'+repr(script)+');import scenario7_missions;'
            'assert not any(n in sys.modules for n in ("numpy","matplotlib","gen_scenario7_maps"))')
    subprocess.run([sys.executable, '-c', code], check=True)


def test_generated_registry_and_continuous_mission_proofs():
    if not missions.MANIFEST.exists():
        pytest.skip('Missions not generated yet')
    result = missions.validate_missions()
    assert result['valid'] and not result['flights_started']
    assert tuple(result['missions']) == missions.MAPS
    assert result['assets_sha256'][str(missions.MANIFEST)] == missions.sha256(missions.MANIFEST)
    assert missions.verify_proofs()['valid']
    for map_name in missions.MAPS:
        context = missions.mission_context(map_name)
        assert context == result['missions'][map_name]
        assert json.loads(json.dumps(context)) == context
