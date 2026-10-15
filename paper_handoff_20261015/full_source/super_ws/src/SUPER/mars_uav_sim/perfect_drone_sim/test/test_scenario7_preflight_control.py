"""Offline regression for blocked references and best-effort ON observations."""
import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scenario7_cpu_compare_v3 as child
import scenario7_preflight_control as control
import scenario7_repair_runtime as runtime


def result(mode='adaptive'):
    checks = {name: True for name in (
        'sensor_cadence', 'odometry_cadence', 'odometry_header_p99',
        'odometry_header_max', 'odometry_receipt_p99', 'odometry_receipt_max',
        'odometry_order', 'fsm_main_callback', 'fsm_command_callback', 'profile_callback_coverage')}
    checks.update(odometry_cadence=False, odometry_header_p99=False)
    return dict(mode=mode, cpu_profile=True, success=True, safety_collisions=0,
                run_valid=True, resource_valid=True, speed_limit_valid=True,
                solid_obstacle_audit=dict(audit_valid=True, completion=True, contact_episodes=0),
                source_acquisition=dict(checks=dict(source=True, small_pool_timing=False)),
                small_pool_timing=dict(valid=False, checks=checks, callback_counts_instrumented=True,
                                       callback_hz=dict(fsm_main_callback=99.93, fsm_command_callback=100.)),
                message_intervals=dict(odometry=dict(mean_received_hz=97.49598294093295,
                    header_interval=dict(p99_ms=20.00678156))))


def test_reference_inventory_collects_all_missing_and_malformed(tmp_path):
    (tmp_path / 'plan.json').write_text('{}')
    (tmp_path / 'adaptive_summary.json').write_text('[]')
    report = control.inspect_profile_reference(tmp_path, ['adaptive', 'sector', 'full'])
    assert not report['valid']
    assert [x['reason'] for x in report['errors']] == [
        'invalid_reference_document', 'missing_reference_document', 'missing_reference_document']
    assert set(report['documents']) == {'plan.json'}


def test_real_adapted_main_blocks_reference_before_profiler_or_flight(tmp_path, monkeypatch):
    output = tmp_path / 'blocked'
    calls = []
    main = child.build_main(namespace_updates=dict(
        register_maps=lambda: {},
        static_latched_preflight=SimpleNamespace(map_context=lambda _: {}),
        mission_runtime=SimpleNamespace(mission_context=lambda _: {})))
    monkeypatch.setattr(main.__globals__['diagnostic'], 'Profiler', lambda *_a, **_k: calls.append('profiler'))
    monkeypatch.setattr(main.__globals__['diagnostic'].search.campaign, 'run_one',
                        lambda *_a, **_k: calls.append('flight'))
    monkeypatch.setattr(sys, 'argv', ['child', '--output', str(output), '--run', '1', '--candidate', 'repair',
        '--map', 'urban_blocks_u01', '--modes', 'adaptive', 'sector', 'full', '--side-executor-threads', '2',
        '--dedicated-static-pc-executor', '--monitor-intervals',
        '--small-pool-profile-reference', str(tmp_path / 'absent')])
    assert main() == 2
    status = json.loads((output / 'status.json').read_text())
    assert status['state'] == 'BLOCKED_BY_PREFLIGHT'
    assert status['completed'] == 0 and status['flights_started'] is False
    assert len(status['reasons']) == 4
    assert status['off_eligible'] is False
    assert calls == [] and not (output / 'raw.csv').exists()


def test_reference_block_will_not_overwrite_existing_output(tmp_path):
    args = SimpleNamespace(output=tmp_path, candidate='repair', map='urban', run=1, modes=['full'])
    with pytest.raises(FileExistsError):
        control.blocked_reference(args, [], lambda *_: None)


def test_complete_but_failed_reference_has_structured_block_without_profiler(tmp_path):
    source = child.adapted_main_source()
    tree = ast.parse(source)
    gate = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                and ast.unparse(node.test) == "profile_reference_audit is not None and (not profile_reference_audit['valid'])")
    function = ast.FunctionDef(name='run_gate', args=ast.arguments(
        posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[gate], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    args = SimpleNamespace(output=tmp_path, candidate='repair', map='urban', run=1, modes=['adaptive', 'sector', 'full'])
    namespace = dict(control=control, args=args, profile_reference_audit=dict(
        valid=False, acceptance_checks=dict(adaptive_profile_timing=False, full_safe_source=True)),
        diagnostic=SimpleNamespace(save=lambda path, value: path.write_text(json.dumps(value))))
    exec(compile(module, '<reference-gate>', 'exec'), namespace)
    assert namespace['run_gate']() == 2
    status = json.loads((tmp_path / 'status.json').read_text())
    assert status['reasons'][0]['failed_checks'] == ['adaptive_profile_timing']
    assert status['state'] == 'BLOCKED_BY_PREFLIGHT' and status['off_eligible'] is False
    # In actual main the complete-reference gate now precedes GPU construction.
    assert source.index("if profile_reference_audit is not None and not profile_reference_audit['valid']:") < source.index('profiler = diagnostic.Profiler(')


@pytest.mark.parametrize('mode', ['full', 'sector', 'adaptive'])
def test_received_odometry_failure_remains_failure_but_allows_safe_observation(mode):
    row = result(mode)
    before = copy.deepcopy(row)
    assert control.continuation_allowed(row, profile_cpu=True)
    assert row == before
    assert row['small_pool_timing']['valid'] is False
    assert control.timing_diagnosis(row)['thresholds_unchanged'] is True


@pytest.mark.parametrize('change', [
    'not_profiled', 'callback', 'order', 'sensor', 'coverage', 'source',
    'resource', 'speed', 'run', 'solid', 'contact', 'incomplete',
])
def test_only_received_odometry_failure_is_continuable(change):
    row = result()
    if change == 'not_profiled':
        assert not control.continuation_allowed(row, profile_cpu=False)
        return
    if change in ('callback', 'order', 'sensor', 'coverage'):
        key = dict(callback='fsm_main_callback', order='odometry_order',
                   sensor='sensor_cadence', coverage='profile_callback_coverage')[change]
        row['small_pool_timing']['checks'][key] = False
    elif change == 'source':
        row['source_acquisition']['checks']['source'] = False
    elif change in ('resource', 'speed', 'run'):
        row[dict(resource='resource_valid', speed='speed_limit_valid', run='run_valid')[change]] = False
    elif change == 'solid':
        row['solid_obstacle_audit']['audit_valid'] = False
    elif change == 'contact':
        row['solid_obstacle_audit']['contact_episodes'] = 1
    else:
        row['success'] = False
    assert not control.continuation_allowed(row, profile_cpu=True)


def test_actual_adapted_mode_gate_continues_and_retains_nonzero_result(tmp_path):
    """Execute the exact generated gate, not a separately reimplemented loop."""
    tree = ast.parse(child.adapted_main_source())
    gate = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                and ast.unparse(node.test) == "not all(result['source_acquisition']['checks'].values())")
    compiled = compile(ast.Module(body=[gate], type_ignores=[]), '<adapted-mode-gate>', 'exec')
    cleanup = []
    campaign = SimpleNamespace(_ACTIVE_PROCESS_GROUPS={},
                               cleanup_active_process_groups=lambda: cleanup.append('clean'))
    namespace = dict(control=control, args=SimpleNamespace(profile_cpu=True), campaign=campaign,
                     psutil=SimpleNamespace(process_iter=lambda _: []), FLIGHT_NAMES={'flight'},
                     retained_mode_failures=[], root=tmp_path,
                     diagnostic=SimpleNamespace(save=lambda path, data: path.write_text(json.dumps(data))))
    rows = []
    for mode in ('adaptive', 'sector', 'full'):
        row = result(mode)
        if mode != 'adaptive':
            row['source_acquisition']['checks']['small_pool_timing'] = True
        namespace['result'] = row
        exec(compiled, namespace)
        rows.append(row)
    assert [row['mode'] for row in rows] == ['adaptive', 'sector', 'full']
    assert cleanup == ['clean']
    failures = namespace['retained_mode_failures']
    assert len(failures) == 1 and failures[0]['off_eligible'] is False
    args = SimpleNamespace(candidate='repair', modes=['adaptive', 'sector', 'full'])
    status = control.final_status(args, rows, failures, {})
    assert status['state'] == 'COMPLETE_WITH_RETAINED_FAILURES'
    assert status['completed'] == 3 and status['preflight_valid'] is False
    assert 'return 2 if retained_mode_failures else 0' in child.adapted_main_source()


def test_remaining_process_or_group_forbids_continuation():
    campaign = SimpleNamespace(_ACTIVE_PROCESS_GROUPS={4: object()}, cleanup_active_process_groups=lambda: None)
    with pytest.raises(RuntimeError, match='groups remain'):
        control.retain_mode_failure(result(), profile_cpu=True, campaign=campaign,
                                  process_iter=lambda _: [], flight_names={'flight'})
    campaign._ACTIVE_PROCESS_GROUPS = {}
    with pytest.raises(RuntimeError, match='flight process remains'):
        control.retain_mode_failure(result(), profile_cpu=True, campaign=campaign,
            process_iter=lambda _: [SimpleNamespace(info={'cmdline': ['/bin/waypoint_mission']})],
            flight_names={'flight'})


def test_original_timing_thresholds_and_callback_semantics_are_unchanged():
    row = result()
    odom = row['message_intervals']['odometry']
    odom.update(header_interval=dict(p99_ms=20.00678156, max_ms=20.15),
                receipt_interval=dict(p99_ms=16.01, max_ms=25.22),
                backward_stamps=0, repeated_stamps=0, intervals_dropped=0)
    profile = dict(processes=[dict(duration_s=10, stages=[
        dict(stage=name, calls=1000, clock_errors=0)
        for name in ('fsm_main_callback', 'fsm_command_callback')])])
    gate = child.previous.inherited.legacy.small_pool_timing_audit(row['message_intervals'], 10, profile)
    assert not gate['valid']
    assert control.failed_checks(gate['checks']) == ['odometry_cadence', 'odometry_header_p99']
    odom['mean_received_hz'] = 98.0
    odom['header_interval']['p99_ms'] = 20.0
    assert child.previous.inherited.legacy.small_pool_timing_audit(row['message_intervals'], 10, profile)['valid']


def test_other_gate_expressions_options_and_retries_are_preserved():
    original = ast.parse(child.previous.adapted_main_source())
    adapted = ast.parse(child.adapted_main_source())
    def parser_calls(tree):
        return [ast.dump(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr in ('add_argument', 'error')]
    assert parser_calls(original) == parser_calls(adapted)
    tests = lambda tree: [ast.dump(n.test) for n in ast.walk(tree) if isinstance(n, ast.If)]
    remaining = tests(adapted)
    for condition in tests(original):
        assert condition in remaining
        remaining.remove(condition)
    assert child.previous.inherited.diagnostic.search.OPTIONS['attempt_max'] == 1
    assert 'Invalid attempt retained; diagnose before retry' in child.adapted_main_source()
    assert 'Source/config/binary changed during candidate' in child.adapted_main_source()
