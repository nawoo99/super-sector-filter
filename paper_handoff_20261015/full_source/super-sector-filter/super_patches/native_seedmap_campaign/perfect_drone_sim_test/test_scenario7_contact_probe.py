"""Offline contact probe invariants; no ROS process is started."""
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_contact_probe as probe


def fake_command(root, map_name):
    return dict(phase='preflight', command=['python', 'child.py', '--modes', 'adaptive', 'sector', 'full',
        '--run', '60000', '--output', str(root / 'old'), '--candidate', 'primary',
        '--static-latched-preflight', 'old.json', '--profile-cpu', '--map', map_name,
        '--side-executor-threads', '3', '--compose'])


def test_exactly_one_adaptive_profiled_mode_without_flight_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.child.previous.support, 'register_maps', lambda: {})
    monkeypatch.setattr(probe.controller, 'build_namespace', lambda **_: SimpleNamespace(
        build_plan=lambda root, maps, run: [fake_command(root, maps[0])]))
    args = probe.flight_arguments(tmp_path, 'gapfree_d1_m01', 777, tmp_path / 'acceptance.json')
    assert args[args.index('--modes') + 1:args.index('--run')] == ['adaptive']
    assert args[args.index('--run') + 1] == '777'
    assert args[args.index('--output') + 1] == str(tmp_path / 'flight')
    assert '--profile-cpu' in args
    assert '--small-pool-profile-reference' not in args and '--time-reference-folder' not in args


def test_real_argument_derivation_twice_does_not_create_output_directories(tmp_path):
    output = tmp_path / 'future_diagnostic'
    acceptance = probe.V1_ROOT / 'static_preflight/gapfree_d1_m01/acceptance.json'
    first = probe.flight_arguments(output, 'gapfree_d1_m01', 62000, acceptance)
    second = probe.flight_arguments(output, 'gapfree_d1_m01', 62000, acceptance)
    assert first == second
    assert not output.exists()
    assert first[first.index('--output') + 1] == str(output / 'flight')
    assert first[first.index('--static-latched-preflight') + 1] == str(acceptance)
    assert not any('scenario7_contact_probe_plan_' in value for value in first)


def test_roi_hits_actual_urban_entry_wall_and_is_hash_bound(tmp_path):
    g1 = probe.trace_settings(tmp_path, 'gapfree_d1_m01')
    urban = probe.trace_settings(tmp_path, 'urban_blocks_u01')
    assert (g1['roi']['center_x'], g1['roi']['center_y']) == (-28.591183, -4.598807)
    assert (urban['roi']['center_x'], urban['roi']['center_y']) == (22., 9.5)
    assert urban['roi']['half_extent_xy_m'] == 2
    assert urban['roi']['z_min_m'] == -.5 and urban['roi']['z_max_m'] == 3.5
    assert urban['settings_sha256'] != g1['settings_sha256']


def test_diagnostic_adapter_preserves_every_inherited_gate_and_option():
    original = ast.parse(probe.child.adapted_main_source())
    adapted = ast.parse(probe.adapt_child(probe.child.adapted_main_source()))
    def checks(tree):
        return [ast.dump(node.test) for node in ast.walk(tree) if isinstance(node, ast.If)]
    assert checks(original) == checks(adapted)
    for text in ('profile_reference_eligible=False', 'primary_comparison_eligible=False',
                 "schema=PROBE['schema']", 'CPU_comparison_eligible=False'):
        assert text in probe.adapt_child(probe.child.adapted_main_source())
    assert probe.child.previous.inherited.diagnostic.search.OPTIONS['attempt_max'] == 1


def footer(count=1):
    value = dict(kind='trace_footer', submitted=count, written=count, file_byte_cap=probe.FILE_CAP,
                 file_cap_reached=False)
    value.update({name: 0 for name in ('dropped', 'errors', 'oversize_drops', 'queue_drops',
        'contention_drops', 'exception_drops', 'closed_drops', 'file_cap_drops', 'queued_records', 'queued_bytes')})
    return value


def write_trace(path, *rows):
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


def test_complete_footer_and_real_rows_required(tmp_path):
    path = tmp_path / 'contact_trace_1.jsonl'
    write_trace(path, dict(kind='sensor_render_cloud', sequence=1), footer())
    audit = probe.audit_trace_file(path)
    assert audit['complete_lossless'] and audit['data_rows'] == 1
    aggregate = probe.audit_traces(tmp_path)
    assert aggregate['complete_lossless']
    assert 'trajectory_validation_result' in aggregate['missing_evidence_kinds']


@pytest.mark.parametrize('change', ['missing', 'drops', 'cap', 'count', 'truncated', 'after_footer', 'sequence'])
def test_partial_capped_or_dropped_trace_is_never_called_complete(tmp_path, change):
    path = tmp_path / 'contact_trace_1.jsonl'
    rows = [dict(kind='sensor_render_cloud', sequence=1), footer()]
    if change == 'missing':
        rows.pop()
    elif change == 'drops':
        rows[-1]['dropped'] = 1
    elif change == 'cap':
        rows[-1]['file_cap_reached'] = True
    elif change == 'count':
        rows[-1]['written'] = 2
    elif change == 'after_footer':
        rows.append(dict(kind='sensor_render_cloud', sequence=2))
    elif change == 'sequence':
        rows[0]['sequence'] = 0
    write_trace(path, *rows)
    if change == 'truncated':
        path.write_text(path.read_text() + '{truncated')
    assert not probe.audit_trace_file(path)['complete_lossless']


def test_missing_traces_are_explicit(tmp_path):
    report = probe.audit_traces(tmp_path)
    assert not report['complete_lossless'] and report['files'] == []
    assert set(report['missing_evidence_kinds']) == probe.REQUIRED_KINDS


def test_concurrent_submit_sequence_reordering_is_not_a_drop(tmp_path):
    path = tmp_path / 'contact_trace_1.jsonl'
    write_trace(path, dict(kind='sensor_render_cloud', sequence=2),
                dict(kind='map_input_cloud', sequence=1), footer(2))
    assert probe.audit_trace_file(path)['complete_lossless']


def test_frozen_inventory_rejects_changed_sources_or_binaries(tmp_path, monkeypatch):
    asset = tmp_path / 'binary'
    asset.write_bytes(b'original')
    inventory = tmp_path / 'inventory.json'
    inventory.write_text(json.dumps({str(asset): probe.sha(asset)}))
    monkeypatch.setattr(probe, 'V1_INVENTORY', inventory)
    monkeypatch.setattr(probe, 'V1_INVENTORY_SHA256', probe.sha(inventory))
    assert probe.frozen_v1_inputs()[str(asset)] == probe.sha(asset)
    asset.write_bytes(b'changed')
    with pytest.raises(ValueError, match='cannot launch a later revision'):
        probe.frozen_v1_inputs()


def test_fresh_output_is_required_and_frozen_campaign_is_protected(tmp_path):
    with pytest.raises(FileExistsError):
        probe.main(['--map', 'gapfree_d1_m01', '--output', str(tmp_path), '--run-id', '777', '--prepare-only'])
    with pytest.raises(SystemExit):
        probe.main(['--map', 'gapfree_d1_m01', '--output', str(probe.V1_ROOT / 'probe'), '--run-id', '777', '--run'])
