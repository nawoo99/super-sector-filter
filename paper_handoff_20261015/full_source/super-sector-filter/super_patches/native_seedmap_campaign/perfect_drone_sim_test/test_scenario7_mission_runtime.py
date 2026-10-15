"""Mission command/parser consistency without ROS processes or simulator runs."""
import argparse
import ast
import copy
import inspect
import json
from pathlib import Path
import shlex
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scenario7_mission_runtime as runtime
import scenario7_cpu_compare as child
import native_campaign as campaign


GOALS = {
    'urban_blocks_u01': [[-24, 25, 1.5], [24, 13, 1.5], [-24, -13, 1.5], [24, -25, 1.5], [0, 0, 1.5]],
    'forest_cluster_f01': [[-24, 22, 1.5], [24, 22, 1.5], [-24, -22, 1.5], [24, -22, 1.5], [0, 0, 1.5]],
}
LEGACY_GOALS = [[24, 24, 1.5], [-24, 24, 1.5], [-24, -24, 1.5], [24, -24, 1.5], [0, 0, 1.5]]


def context_for(tmp_path, name):
    goals = copy.deepcopy(GOALS.get(name, LEGACY_GOALS))
    mission = runtime.EXPECTED_MISSIONS[name]
    path = tmp_path / (mission + '.txt')
    path.write_text(''.join(' '.join(f'{value:g}' for value in row + [1.5]) + '\n' for row in goals))
    registry = tmp_path / 'registry.json'
    registry.write_text('{}')
    return dict(map=name, mission=mission, mission_file_basename=path.name, mission_file=str(path),
                mission_sha256=runtime.support.sha256(path), registry_path=str(registry),
                registry_sha256=runtime.support.sha256(registry),
                wps=';'.join(','.join(f'{x:g}' for x in row[:2]) for row in goals),
                waypoints_xyz=goals, initial_position_xyz=[0, 0, 1.5], goal_count=5,
                switch_distance_m=1.5, assets_sha256={str(path): runtime.support.sha256(path)})


@pytest.mark.parametrize('name', runtime.support.MAPS7)
def test_private_mission_binding_preserves_signature_gates_and_shared_globals(tmp_path, name):
    context = context_for(tmp_path, name)
    original_wps, original_run = campaign.LOOP_WPS, campaign.run_one
    adapted = runtime.build_run_one(campaign, context)
    assert inspect.signature(adapted) == inspect.signature(original_run)
    assert adapted.__globals__['LOOP_WPS'] == context['wps']
    assert adapted.__globals__['SCENARIO7_MISSION']['mission_file_basename'] == context['mission_file_basename']
    assert campaign.LOOP_WPS == original_wps and campaign.run_one is original_run
    assert adapted.__globals__ is not vars(campaign)
    original = ast.parse(inspect.getsource(original_run)).body[0]
    transformed = ast.parse(runtime.adapted_run_one_source(campaign)).body[0]
    # Every original conditional, timeout expression, retry limit and default
    # survives; only the declared default filename expression changes.
    old, new = runtime.RUN_ONE_REPLACEMENTS[0]
    expected = ast.parse(inspect.getsource(original_run).replace(old, new, 1)).body[0]
    assert ast.dump(transformed) == ast.dump(expected)
    assert [ast.dump(n.test) for n in ast.walk(transformed) if isinstance(n, ast.If)] == [
        ast.dump(n.test) for n in ast.walk(original) if isinstance(n, ast.If)]
    assert runtime.mission_binding(context)['goal_count'] == 5
    if name in runtime.support.ORIGINAL_MAPS:
        assert context['wps'] == campaign.LOOP_WPS
        assert context['mission_file_basename'] == 'loop24.txt'


@pytest.mark.parametrize('name', ['urban_blocks_u01', 'forest_cluster_f01'])
def test_actual_monitor_parser_accepts_negative_first_waypoint_and_all_five_goals(tmp_path, monkeypatch, name):
    context = context_for(tmp_path, name)
    command = campaign.build_loop_monitor_command(context['wps'], 1.5, 180, '/tmp/not_launched.json',
                                                  ' --static-pcd /tmp/not_loaded.pcd --speed-limit-mps 7')
    argv = shlex.split(command)
    assert argv.index('--') < argv.index(context['wps'])
    tree = ast.parse((runtime.support.LEGACY_DIR / 'native_loop_monitor.py').read_text())
    parser_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse_args')
    namespace = {'argparse': argparse}
    exec(compile(ast.Module(body=[parser_node], type_ignores=[]), '<native-parser-only>', 'exec'), namespace)
    monkeypatch.setattr(sys, 'argv', argv[1:])
    args, ros_args = namespace['parse_args']()
    assert ros_args == [] and args.waypoints == context['wps']
    assert args.switch_dist == 1.5 and args.timeout_s == 180
    namespace['ARGS'] = args
    wps_node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'WPS' for t in n.targets))
    exec(compile(ast.Module(body=[wps_node], type_ignores=[]), '<native-wps-only>', 'exec'), namespace)
    assert namespace['WPS'] == [tuple(row[:2]) for row in context['waypoints_xyz']]
    assert len(namespace['WPS']) == 5 and namespace['WPS'][-1] == (0, 0)


@pytest.mark.parametrize('name', runtime.support.MAPS7)
def test_launch_and_deferred_mission_commands_share_selected_file(tmp_path, name):
    context = context_for(tmp_path, name)
    node = ast.parse(runtime.adapted_run_one_source(campaign)).body[0]
    namespace = dict(SCENARIO7_MISSION=context, waypoint_data_name=context['mission_file_basename'],
                     drone_config_name=name+'.yaml', seedmap_super_config='unchanged.yaml',
                     reference_stack_log='/tmp/stack.log', mission_log='/tmp/mission.log')
    commands = {}
    for target in ('launch_cmd', 'mission_cmd'):
        assignments = [n for n in ast.walk(node) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == target for t in n.targets)
                       and any(isinstance(v, ast.Name) and v.id == 'waypoint_data_name' for v in ast.walk(n.value))]
        assert len(assignments) == 1
        commands[target] = eval(compile(ast.Expression(assignments[0].value), '<command-only>', 'eval'), namespace)
    assert 'waypoint_data:=' + context['mission_file_basename'] in commands['launch_cmd']
    assert '-p data_name:=' + context['mission_file_basename'] in commands['mission_cmd']
    if name in GOALS:
        assert 'loop24.txt' not in commands['launch_cmd'] + commands['mission_cmd']


def test_every_runtime_argument_forwarded_and_mismatched_map_rejected(tmp_path, monkeypatch):
    context = context_for(tmp_path, 'urban_blocks_u01')
    kwargs = {name: parameter.default for name, parameter in inspect.signature(campaign.run_one).parameters.items()
              if parameter.default is not inspect.Parameter.empty}
    kwargs.update(attempt_max=1, artifacts_dir='/tmp/uncreated', seedmap_super_config_override='unchanged.yaml',
                  observer_ready_before_mission=True, loop_timeout_override=180)
    recorder = mock.Mock(return_value={'test': 'no runtime execution'})
    builder = mock.Mock(return_value=recorder)
    monkeypatch.setattr(runtime, 'build_run_one', builder)
    assert runtime.run_one(campaign, context, 'urban_blocks_u01', 'adaptive', 9, **kwargs) == {'test': 'no runtime execution'}
    recorder.assert_called_once_with('urban_blocks_u01', 'adaptive', 9, **kwargs)
    assert recorder.call_args.kwargs['attempt_max'] == 1
    builder.reset_mock()
    with pytest.raises(ValueError, match='Flight map differs'):
        runtime.run_one(campaign, context, 'forest_cluster_f01', 'full', 10)
    builder.assert_not_called()


@pytest.mark.parametrize('key,value', [
    ('mission', 'loop24'), ('mission_file_basename', '../wrong.txt'),
    ('wps', '-24,25,1.5;0,0,1.5'), ('goal_count', 4), ('switch_distance_m', 2),
    ('mission_sha256', 'changed'), ('initial_position_xyz', [1, 0, 1.5]),
])
def test_invalid_mission_context_fails_closed(tmp_path, key, value):
    context = context_for(tmp_path, 'urban_blocks_u01')
    context[key] = value
    with pytest.raises(ValueError):
        runtime.validate_context(context)


def test_changed_native_source_rejected(tmp_path, monkeypatch):
    source = tmp_path / 'native_campaign.py'
    source.write_text(Path(campaign.__file__).read_text() + '\n# changed\n')
    monkeypatch.setattr(campaign, '__file__', str(source))
    with pytest.raises(ValueError, match='Frozen native campaign changed'):
        runtime.adapted_run_one_source(campaign)


def test_child_metadata_and_call_are_mission_bound_without_altering_cli_gates(tmp_path):
    context = context_for(tmp_path, 'urban_blocks_u01')
    assert json.loads(json.dumps(runtime.mission_binding(context))) == runtime.mission_binding(context)
    source = child.adapted_main_source()
    assert 'scenario7_mission=mission_runtime.mission_binding(mission_context)' in source
    assert 'mission_runtime.run_one(campaign, mission_context, args.map, mode, args.run, **options,' in source
    assert "Path(mission_context['mission_file'])" in source
    assert 'mission_runtime.asset_paths(mission_context)' in source
    assert 'scenario7_mission' in child.MAP_MATCH_FIELDS
    main = child.build_main()
    assert main.__globals__['mission_runtime'] is runtime
    original = next(n for n in ast.parse(runtime.support.GAPFREE_ADAPTER.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'main')
    adapted = ast.parse(source).body[0]
    for kind, attr in ((ast.If, 'test'),):
        assert [ast.dump(getattr(n, attr)) for n in ast.walk(original) if isinstance(n, kind)] == [
            ast.dump(getattr(n, attr)) for n in ast.walk(adapted) if isinstance(n, kind)]


def test_profile_reference_rejects_same_geometry_different_mission():
    plan = {key: 'same' for key in child.MAP_MATCH_FIELDS}
    reference = dict(plan, scenario7_mission='old-loop24')
    with mock.patch.object(child.inherited.legacy, 'small_pool_profile_reference_audit',
                           return_value=dict(valid=True, checks={}, acceptance_checks={})):
        assert not child.small_pool_profile_reference_audit(plan, reference, {})['valid']
