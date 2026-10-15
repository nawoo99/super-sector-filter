"""Read-only runner admission and a mocked one-flight lifecycle (no ROS)."""
import inspect
import json
from contextlib import ExitStack
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_g1_contact_diagnostic as runner


@pytest.fixture
def baseline():
    return json.loads((runner.BASELINE / 'plan.json').read_text())


def test_exact_original_options_one_adaptive_attempt(baseline):
    options = runner.replay_options(baseline)
    assert options == baseline['effective_run_options']['adaptive']
    assert options['attempt_max'] == 1 and options['loop_timeout_override'] == 180
    assert options['adaptive_event_recovery'] is True
    with pytest.raises(ValueError):
        baseline['effective_run_options']['adaptive']['attempt_max'] = 2
        runner.replay_options(baseline)


def test_original_environment_replayed_with_only_trace_addition(baseline, tmp_path):
    environment = runner.replay_environment(baseline, tmp_path)
    assert environment['SUPER_CPU_PROFILE'] == '1'
    assert environment['SUPER_CALLBACK_TRACE'] == '0'
    assert environment['SUPER_SIDE_EXECUTOR_THREADS'] == '3'
    assert environment['SUPER_FRONTEND_DEDICATED_EXECUTOR'] == '0'
    assert environment['SUPER_G1_CONTACT_TRACE_DIR'] == str(tmp_path)
    assert environment['SUPER_CONTACT_TRACE_CENTER_X'] == '-28.591183000000001'
    assert environment['SUPER_CONTACT_TRACE_CENTER_Y'] == '-4.5988069999999999'
    assert environment['SUPER_GUARDED_DEMAND_EXTENDED_LEASE'] == '0'
    assert environment['SUPER_OPTIMIZER_PHASE_MEMORY_TRACE'] == '0'
    for environment_key, plan_key in runner.BOOL_ENV_FIELDS.items():
        assert environment[environment_key] == str(int(baseline[plan_key]))


def test_environment_binding_matches_legacy_assignments(baseline):
    # These are the exact non-mode-specific names assigned in the frozen child.
    import ast
    tree = ast.parse(runner.adapter.__file__ and Path(runner.adapter.__file__).read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and
                    ast.unparse(target.value) == 'os.environ' and
                    isinstance(target.slice, ast.Constant)):
                    names.add(target.slice.value)
    replay_names = set(runner.replay_environment(baseline, '/tmp/test'))
    assert names == replay_names - {
        'SUPER_G1_CONTACT_TRACE_DIR',
        'SUPER_CONTACT_TRACE_CENTER_X',
        'SUPER_CONTACT_TRACE_CENTER_Y',
    }


def test_nonboolean_plan_flags_are_rejected(baseline):
    baseline['cpu_profile'] = '1'
    with pytest.raises(ValueError):
        runner.replay_environment(baseline, '/tmp/test')


def test_allowlist_does_not_allow_old_binary_change(tmp_path, monkeypatch):
    old_binary = tmp_path / 'perfect_drone_adaptive_node'
    changed_source = tmp_path / 'hook.cpp'
    old_binary.write_text('original')
    changed_source.write_text('before')
    plan = {'runtime_policy': {'sha256': {str(old_binary): runner.support.sha256(old_binary)}},
            'asset_sha256': {str(changed_source): runner.support.sha256(changed_source)}}
    monkeypatch.setattr(runner, 'TRACE_SOURCE_PATHS', (changed_source,))
    changed_source.write_text('logging hook')
    hashes, changes = runner.verify_baseline(plan)
    assert len(changes) == 1 and changes[0]['path'] == str(changed_source)
    assert hashes[str(old_binary)] == plan['runtime_policy']['sha256'][str(old_binary)]
    old_binary.write_text('rebuilt')
    with pytest.raises(RuntimeError, match='Unexpected baseline change'):
        runner.verify_baseline(plan)


def test_config_changes_cannot_be_waived(tmp_path, monkeypatch):
    config = tmp_path / 'config.yaml'
    config.write_text('old')
    plan = {'runtime_policy': {'sha256': {}},
            'asset_sha256': {str(config): runner.support.sha256(config)}}
    monkeypatch.setattr(runner, 'TRACE_SOURCE_PATHS', ())
    config.write_text('new')
    with pytest.raises(RuntimeError):
        runner.verify_baseline(plan)


def test_original_install_cannot_be_diagnostic_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'INSTALL', tmp_path)
    with pytest.raises(ValueError):
        runner.ros_environment(tmp_path)
    with pytest.raises(ValueError):
        runner.ros_environment(tmp_path / 'accidental_overlay')


def test_ros_overlay_shell_paths_are_quoted(tmp_path):
    prefix = tmp_path / 'diag install'
    (prefix / 'perfect_drone_sim/lib/perfect_drone_sim').mkdir(parents=True)
    (prefix / 'local_setup.bash').write_text('')
    binary = prefix / 'perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node'
    binary.write_text('binary')
    command, selected = runner.ros_environment(prefix)
    assert "source '" + str(prefix / 'local_setup.bash') + "'" in command
    assert selected == binary


def test_wrong_ros_package_prefix_rejected(tmp_path):
    with mock.patch.object(runner.subprocess, 'run', return_value=mock.Mock(stdout='/wrong/prefix\n')):
        with pytest.raises(RuntimeError, match='Wrong ROS package overlay'):
            runner.verify_package_prefix('environment', tmp_path)


def test_prepare_only_does_not_call_flight(tmp_path, baseline, monkeypatch):
    base = tmp_path / 'baseline'
    base.mkdir()
    (base / 'plan.json').write_text(json.dumps(baseline))
    prefix = tmp_path / 'overlay'
    prefix.mkdir()
    (prefix / 'local_setup.bash').write_text('')
    binary = prefix / 'binary'
    binary.write_text('')
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (scripts / 'g1_contact_topic_recorder.py').write_text('')
    monkeypatch.setattr(runner, 'SCRIPTS', scripts)
    admission = {'maps': {runner.MAP: {'geometry': baseline['gapfree_geometry']}}}
    with mock.patch.object(runner.support, 'register_maps', return_value=admission), \
         mock.patch.object(runner, 'verify_baseline', return_value=({}, [])), \
         mock.patch.object(runner, 'ros_environment', return_value=('env', binary)), \
         mock.patch.object(runner, 'verify_package_prefix', return_value=str(prefix)), \
         mock.patch.object(runner.legacy.diagnostic.search.campaign, 'run_one') as flight, \
         mock.patch.dict(runner.os.environ, {}, clear=True):
        result = runner.main(['--output', str(tmp_path / 'prepared'), '--baseline', str(base),
                              '--diagnostic-install', str(prefix), '--prepare-only'])
        assert result == 0 and flight.call_count == 0
    status = json.loads((tmp_path / 'prepared/status.json').read_text())
    assert status['actual_flights'] == 0 and status['state'] == 'PREPARED_ONLY'
    prepared = json.loads((tmp_path / 'prepared/plan.json').read_text())
    assert prepared['primary_comparison_eligible'] is False
    assert prepared['CPU_comparison_eligible'] is False


def test_explicit_operation_required_and_existing_output_preserved(tmp_path):
    with pytest.raises(SystemExit):
        runner.main(['--output', str(tmp_path / 'new')])
    with pytest.raises(FileExistsError):
        runner.main(['--output', str(tmp_path), '--prepare-only'])


def test_only_one_run_one_call_site_no_mode_loop():
    import ast
    tree = ast.parse(inspect.getsource(runner.main))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == 'run_one']
    assert len(calls) == 1
    assert ast.unparse(calls[0].args[0]) == 'map_name'
    assert ast.unparse(calls[0].args[1]) == 'MODE'
    assert not any(isinstance(node, (ast.For, ast.While)) and calls[0] in list(ast.walk(node))
                   for node in ast.walk(tree))


def test_mocked_contact_lifecycle_runs_once_keeps_diagnostic_scope(tmp_path, baseline, monkeypatch):
    base = tmp_path / 'baseline'
    base.mkdir()
    (base / 'plan.json').write_text(json.dumps(baseline))
    prefix = tmp_path / 'overlay'
    prefix.mkdir()
    (prefix / 'local_setup.bash').write_text('')
    binary = prefix / 'binary'
    binary.write_text('')
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (scripts / 'g1_contact_topic_recorder.py').write_text('')
    output = tmp_path / 'run'
    monkeypatch.setattr(runner, 'SCRIPTS', scripts)
    campaign = runner.legacy.diagnostic.search.campaign
    monkeypatch.setattr(campaign, 'LOCK_PATH', str(tmp_path / 'native.lock'))
    admission = {'maps': {runner.MAP: {'geometry': baseline['gapfree_geometry']}}}
    profiler = mock.Mock(error=None)
    guard = mock.Mock(error=None, maximum_mib=1024.)
    observer = mock.Mock()
    observer.poll.return_value = None

    def start_observer(*unused_args, **unused_kwargs):
        recording = output / 'topic_recording'
        recording.mkdir()
        (recording / 'ready.json').write_text('{}')
        return observer

    def fly(map_name, mode, run, **options):
        assert map_name == runner.MAP and mode == 'adaptive'
        assert options['attempt_max'] == 1
        assert runner.os.environ['SUPER_CPU_PROFILE'] == '1'
        assert runner.os.environ['SUPER_G1_CONTACT_TRACE_DIR'] == str(output / 'cpp_trace')
        stem = f'{map_name}_run{run}_{mode}.attempt1'
        (output / 'artifacts' / (stem + '.stack.log')).write_text('diagnostic stack')
        (output / 'cpp_trace/trace.jsonl').write_text('{"diagnostic":true}\n')
        return dict(map=map_name, mode=mode, run=run, success=True,
                    attempt_count=1, retry_count=0)

    patches = [
        mock.patch.object(runner.support, 'register_maps', return_value=admission),
        mock.patch.object(runner, 'verify_baseline', return_value=({}, [])),
        mock.patch.object(runner, 'ros_environment', return_value=('env', binary)),
        mock.patch.object(runner, 'verify_package_prefix', return_value=str(prefix)),
        mock.patch.object(runner, 'ensure_no_flights'),
        mock.patch.object(runner, 'unchanged', return_value=[]),
        mock.patch.object(runner.time, 'sleep'),
        mock.patch.object(runner.subprocess, 'Popen', side_effect=start_observer),
        mock.patch.object(runner, 'terminate_observer'),
        mock.patch.object(runner, 'OwnedRssGuard', return_value=guard),
        mock.patch.object(runner.legacy.diagnostic, 'Profiler', return_value=profiler),
        mock.patch.object(runner.legacy.diagnostic, 'summarize', return_value={'diagnostic_only': True}),
        mock.patch.object(runner.legacy, 'quality_valid', return_value=True),
        mock.patch.object(runner.legacy, 'static_latched_audit', return_value={'valid': True}),
        mock.patch.object(runner.legacy.source, 'audit_source', return_value={'checks': {'source': True}}),
        mock.patch.object(runner.legacy.recovery_audit, 'audit_file', return_value={'valid': True}),
        mock.patch.object(runner.adapter, 'copy_supplemental_artifacts',
                          return_value={'audit_valid': True, 'contact_episodes': 1, 'completion': True}),
        mock.patch.object(runner.adapter, 'preserve_supplemental_artifacts'),
        mock.patch.object(campaign, 'cleanup_active_process_groups'),
        mock.patch.dict(runner.os.environ, {}, clear=True),
    ]
    with ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        flight = stack.enter_context(mock.patch.object(campaign, 'run_one', side_effect=fly))
        code = runner.main(['--output', str(output), '--baseline', str(base),
                            '--diagnostic-install', str(prefix), '--run'])
        assert code == 0 and flight.call_count == 1
        profiler.close.assert_called_once()
    status = json.loads((output / 'status.json').read_text())
    assert status['state'] == 'DIAGNOSTIC_CONTACT'
    assert status['actual_flights'] == 1 and status['contact_episodes'] == 1
    result = json.loads((output / 'diagnostic_summary.json').read_text())
    assert result['CPU_comparison_eligible'] is False
    assert result['primary_comparison_eligible'] is False
    assert result['checks']['one_attempt'] is True
    assert (output / 'raw.csv').is_file()
