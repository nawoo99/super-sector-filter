"""Result release tests; no ROS imports or physical simulation."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('freeze', Path(__file__).with_name('freeze_v6_results.py'))
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


def inventory():
    rows = []
    for stage, maps in (('seven_map_n10', freeze.MAPS), ('forest_n10', freeze.MAPS[-1:])):
        for map_name in maps:
            for repeat in range(1, 11):
                for mode in freeze.MODES:
                    row = dict(stage=stage, map=map_name, repeat=str(repeat), mode=mode,
                               success='True', contacts='0', quality_valid='True',
                               solid_replay_valid='True', time_s='10',
                               full_transitions='2' if mode == 'adaptive' else '',
                               host_cpu_pct_mean='7', baseline_host_cpu_pct_mean='3',
                               experiment_host_capacity_pct='5', map_frames_s='10')
                    row.update({k: '1' for k in freeze.METRICS})
                    rows.append(row)
    return rows


def test_inventory_complete_separate_stages():
    freeze.validate_inventory(inventory())


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'quality', 'reference', 'nan'])
def test_inventory_rejects_invalid(mutation):
    rows = inventory()
    if mutation == 'duplicate': rows[-1] = dict(rows[0])
    if mutation == 'missing': rows.pop()
    if mutation == 'quality': rows[0]['quality_valid'] = 'False'
    if mutation == 'reference': rows[0]['success'] = 'False'
    if mutation == 'nan': rows[0]['cpu_cores'] = 'nan'
    with pytest.raises(ValueError): freeze.validate_inventory(rows)


def test_completion_and_contact_are_independent():
    rows = [r for r in inventory() if r['stage'] == 'seven_map_n10'
            and r['map'] == freeze.MAPS[-1] and r['mode'] == 'sector']
    rows[0].update(success='False', contacts='1', time_s='100')
    rows[1].update(success='False', time_s='50')
    rows[2].update(contacts='1')
    result = freeze.aggregate(rows, 'Forest')
    assert (result['complete'], result['contact_runs'], result['safe_complete']) == (8, 2, 7)
    assert result['observed_time_s_mean'] == 23
    assert result['complete_time_s_mean'] == 10
    assert result['adaptive_full_transitions_sum'] is None


def test_integral_float_transition_count():
    assert freeze.count('8.0') == 8
    for invalid in ('nan', '2.5', '-1', ''):
        with pytest.raises(ValueError): freeze.count(invalid)


def test_empty_audit_must_not_pass_vacuous_all():
    with pytest.raises(ValueError, match='acquisition'):
        freeze.validate_audits(dict(source_acquisition=dict(checks={}, frames=[{}])))


def complete_marker(output):
    freeze.json_write(output/'build_complete.json', dict(state='BUILT_NOT_SEALED', main=210,
        gate=30, sha256={p.name: freeze.sha(p) for p in output.iterdir() if p.is_file()}))


def test_seal_detects_changes_and_forbids_reseal(tmp_path):
    source = tmp_path/'source.csv'; source.write_text('original outcome\n')
    output = tmp_path/'release'; output.mkdir()
    (output/'table.csv').write_text('all results\n')
    freeze.json_write(output/'source_manifest.json', dict(sha256={str(source): freeze.sha(source)}))
    complete_marker(output)
    freeze.seal(output)
    freeze.verify(output)
    with pytest.raises(ValueError, match='Already sealed'): freeze.seal(output)
    (output/'table.csv').write_text('selective replacement\n')
    with pytest.raises(ValueError, match='Frozen asset changed'): freeze.verify(output)


def test_verify_detects_changed_raw_source(tmp_path):
    source = tmp_path/'raw.csv'; source.write_text('failed\n')
    output = tmp_path/'release'; output.mkdir()
    freeze.json_write(output/'source_manifest.json', dict(sha256={str(source): freeze.sha(source)}))
    complete_marker(output)
    freeze.seal(output)
    source.write_text('success\n')
    with pytest.raises(ValueError, match='Frozen source changed'): freeze.verify(output)


def test_build_refuses_existing_destination(tmp_path):
    with pytest.raises(ValueError, match='Existing output refused'):
        freeze.build(Path('/missing'), tmp_path)


def test_partial_build_cannot_be_sealed(tmp_path):
    freeze.json_write(tmp_path/'source_manifest.json', dict(sha256={}))
    with pytest.raises(FileNotFoundError): freeze.seal(tmp_path)
