"""C24 prospective counts, fail-closed gates, and owned memory sentinel; no flights."""
import copy
import csv
import json
from pathlib import Path
from unittest import mock

import pytest
import run_c24_normal_validation as controller


def valid_triplet(folder, map_name='seed1', run=18000, profile=True,
                  candidate='c24_fixture', order=controller.MODES, async_enabled=False):
    folder.mkdir(parents=True, exist_ok=True)
    plan = dict(map=map_name, run=run, modes=list(order), cpu_profile=profile, candidate=candidate,
        side_executor_threads=3, extended_demand_lease=False, guarded_demand_replan=True,
        event_body_heading=True, mission_time_as_metric=True, sector_outcomes_as_metrics=True,
        async_certified_recovery=async_enabled)
    controller.save(folder/'plan.json', plan)
    controller.save(folder/'status.json', dict(state='COMPLETE', completed=3, candidate=candidate))
    raw = []
    for mode in order:
        extra = ('full_source_always_360','full_readback_size','full_ray_count') if mode == 'full' else (
            'source_mode_enabled','quarter_width_before_cloud','actual_depth_readback_narrowed',
            'only_acquired_rays_converted','source_cloud_byte_counts','fixed_sector_never_full')
        if mode == 'adaptive':
            extra += ('event_mode_enabled','raw_risk_worker_disabled')
        if mode == 'sector':
            extra += ('goal_identity_consistency',)
        if not profile:
            extra += ('small_pool_profile_reference',)
        if async_enabled:
            extra += ('async_certified_recovery_setting',)
        source = {key: True for key in controller.SOURCE_CHECKS + extra}
        timing = {key: True for key in controller.TIMING_CHECKS + (controller.PROFILE_TIMING_CHECKS if profile else ())}
        row = dict(map=map_name, run=run, mode=mode, candidate=candidate, success=True, safety_collisions=0,
            run_valid=True, resource_valid=True, speed_limit_valid=True, source_acquisition={'checks':source},
            strict_recovery_audit={'valid':True,'mode':mode},
            small_pool_timing={'valid':True,'checks':timing,'callback_counts_instrumented':profile},
            cpu_profile=profile, callback_trace=False, cpu_comparison_instrumented=False,
            demand_replan_exercised=True, goal_retransmit_exercised=True,
            goal_identity_audit={'valid':True,'identity_consistency_valid':True},
            static_pc_delivery_validated=True, static_latched_audit={'valid':True},
            end_to_end_cpu_cores_mean=.5, end_to_end_cpu_core_s=20, mission_time_s=39,
            reference_comparison={'mission_time_guardrail_pass':False},
            async_certified_recovery=async_enabled, async_recovery_setting_audit={'valid':True})
        controller.save(folder/f'{mode}_summary.json', row)
        raw.append(dict(map=map_name, run=str(run), mode=mode, success='True', safety_collisions='0',
            run_valid='True', resource_valid='True', speed_limit_valid='True', infrastructure_failure='False',
            attempt_count='1', retry_count='0', cgroup_cpu_duration_s='40', static_pcd_enabled='True',
            safety_contact_source='static_pcd', static_pcd_collisions='0',
            end_to_end_cpu_cores_mean='.5', end_to_end_cpu_core_s='20'))
    write_raw(folder, raw)
    return plan, raw


def write_raw(folder, rows):
    with (folder/'raw.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def change_summary(folder, selected_mode, **changes):
    value = controller.read(folder/f'{selected_mode}_summary.json')
    value.update(changes)
    controller.save(folder/f'{selected_mode}_summary.json', value)


def test_exact_90_flights_75_off_fresh_static_and_no_n20(tmp_path):
    commands = controller.build_plan(tmp_path, 18000)
    static = [c for c in commands if c['phase']=='static']
    flights = [c for c in commands if 'path' in c]
    assert len(static) == 40  # 30 DDS + 5 actual RViz + 5 manifest creation.
    assert len(flights) == 30 and sum(len(c['modes']) for c in flights) == 90
    assert sum(len(c['modes']) for c in flights if c['phase']=='validation5') == 75
    assert len({(c['map'],c['run'],m) for c in flights for m in c['modes']}) == 90
    assert {c['phase'] for c in flights} == {'preflight','validation5'}
    for m in controller.MAPS:
        assert sum(c['map']==m and c['phase']=='preflight' for c in flights) == 1
        assert sum(c['map']==m and c['phase']=='validation5' for c in flights) == 5
    for c in flights:
        cmd = c['command']
        assert set(c['modes']) == set(controller.MODES)
        assert cmd[cmd.index('--side-executor-threads')+1] == '3'
        assert '--extended-demand-lease' not in cmd
        assert '--guarded-demand-replan' in cmd
        assert '--event-body-heading' in cmd and '--mission-time-as-metric' in cmd
        assert '--sector-outcomes-as-metrics' in cmd
        assert '--async-certified-recovery' not in cmd
        assert str(tmp_path/'static_preflight'/c['map']/'acceptance.json') in cmd
        assert str(tmp_path/'references'/c['map']) in cmd
        assert ('--profile-cpu' in cmd) is (c['phase']=='preflight')
        if c['phase']=='validation5':
            index = controller.MAPS.index(c['map'])
            assert str(tmp_path/'preflight'/c['map']/f'r01_run{18000+index}') in cmd


def test_rotations_and_single_async_optin_in_every_flight(tmp_path):
    commands = controller.build_plan(tmp_path, async_certified_recovery=True)
    flights = [c for c in commands if 'path' in c]
    assert all(c['command'].count('--async-certified-recovery') == 1 for c in flights)
    assert all(c['async_certified_recovery'] is True for c in flights)
    off = [c for c in flights if c['phase']=='validation5']
    for repeat in range(1,6):
        maps = [c['map'] for c in off if c['repeat']==repeat]
        assert maps == list(controller.MAPS[repeat-1:] + controller.MAPS[:repeat-1])
    assert len({tuple(c['modes']) for c in off}) == 6


def test_optional_extension_flags_cannot_override_frozen_controls():
    assert controller.extension_options(['--documented-future-option'], ['SUPER_FUTURE_OPTION=1']) == (
        ['--documented-future-option'], {'SUPER_FUTURE_OPTION':'1'})
    for flags, env in [(['--modes'],[]),(['--extended-demand-lease'],[]),
                       (['--async-certified-recovery'],[]),(['--bad=1'],[]),
                       (['--future','--future'],[]),([],['HOME=/tmp']),
                       ([],['SUPER_CPU_PROFILE=1']),([],['SUPER_TEST=']),([],['SUPER_TEST=1','SUPER_TEST=2'])]:
        with pytest.raises(ValueError):
            controller.extension_options(flags, env)


@pytest.mark.parametrize('profile',[False,True])
def test_time_ratio_is_not_an_acceptance_gate(tmp_path, profile):
    valid_triplet(tmp_path, profile=profile)
    change_summary(tmp_path,'adaptive',mission_time_s=1000)
    assert controller.triplet_audit(tmp_path,'seed1',18000,profile,'c24_fixture',controller.MODES)['valid']


@pytest.mark.parametrize('profile',[False,True])
def test_sector_collision_and_incompletion_are_retained_in_on_and_off(tmp_path, profile):
    _, raw = valid_triplet(tmp_path,profile=profile)
    change_summary(tmp_path,'sector',success=False,safety_collisions=2)
    for row in raw:
        if row['mode']=='sector':
            row.update(success='False',safety_collisions='2',static_pcd_collisions='2')
    write_raw(tmp_path,raw)
    result = controller.triplet_audit(tmp_path,'seed1',18000,profile)
    assert result['valid']
    assert result['outcome_failures']['sector'] == {'success':False,'safety_collisions':2}


@pytest.mark.parametrize('mode',['full','adaptive'])
@pytest.mark.parametrize('profile',[False,True])
def test_full_adaptive_outcomes_always_fail_gate(tmp_path, mode, profile):
    _, raw = valid_triplet(tmp_path,profile=profile)
    change_summary(tmp_path,mode,success=False,safety_collisions=1)
    for row in raw:
        if row['mode']==mode:
            row.update(success='False',safety_collisions='1',static_pcd_collisions='1')
    write_raw(tmp_path,raw)
    assert not controller.triplet_audit(tmp_path,'seed1',18000,profile)['valid']


@pytest.mark.parametrize('field,value',[
    ('resource_valid',False),('run_valid',False),('speed_limit_valid',False),('cpu_profile',False),
    ('callback_trace',True),('cpu_comparison_instrumented',True),
    ('source_acquisition',{'checks':{}}),('source_acquisition',{'checks':{'fake':True}}),
    ('strict_recovery_audit',{'valid':False,'mode':'sector'}),
    ('small_pool_timing',{'valid':True,'checks':{}}),('safety_collisions',None),
    ('end_to_end_cpu_cores_mean',float('nan')),('map','seed9'),('run',True),('mode','adaptive'),
])
def test_sector_measurement_contract_or_identity_failure_never_passes(tmp_path, field, value):
    valid_triplet(tmp_path)
    change_summary(tmp_path,'sector',**{field:value})
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True)['valid']


def test_missing_duplicate_retried_raw_or_false_cached_acceptance(tmp_path):
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True)['valid']
    _, raw = valid_triplet(tmp_path)
    write_raw(tmp_path,raw+[raw[0]])
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True)['valid']
    raw[0]['retry_count'] = '1'
    write_raw(tmp_path,raw)
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True)['valid']


def test_async_marker_required_only_for_selected_new_policy(tmp_path):
    valid_triplet(tmp_path, async_enabled=True)
    assert controller.triplet_audit(tmp_path,'seed1',18000,True,async_certified_recovery=True)['valid']
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True,async_certified_recovery=False)['valid']
    change_summary(tmp_path,'full',async_recovery_setting_audit={'valid':False})
    assert not controller.triplet_audit(tmp_path,'seed1',18000,True,async_certified_recovery=True)['valid']


def test_exact_gate_reaudits_all_slots_and_rejects_missing_false_or_duplicate(tmp_path):
    commands = controller.build_plan(tmp_path/'campaign')
    assert not controller.phase_gate(commands,'preflight')['valid']
    selected = [c for c in commands if c['phase']=='preflight']
    for c in selected:
        folder = Path(c['path'])
        valid_triplet(folder,c['map'],c['run'],True,c['candidate'],c['modes'])
        audit = controller.triplet_audit(folder,c['map'],c['run'],True,c['candidate'],c['modes'])
        controller.save(folder/'triplet_verification.json',audit)
    assert controller.phase_gate(commands,'preflight')['valid']
    assert not controller.phase_gate(commands+[selected[0]],'preflight')['valid']
    folder = Path(selected[0]['path'])
    audit = controller.read(folder/'triplet_verification.json')
    audit['valid'] = False
    controller.save(folder/'triplet_verification.json',audit)
    assert not controller.phase_gate(commands,'preflight')['valid']
    audit['valid'] = True
    controller.save(folder/'triplet_verification.json',audit)
    change_summary(folder,'full',resource_valid=False)
    assert not controller.phase_gate(commands,'preflight')['valid']


def test_modified_or_removed_frozen_file_detected(tmp_path):
    file = tmp_path/'input.txt'
    file.write_text('old')
    frozen = {}
    controller.freeze_files(frozen,[file])
    assert controller.changed_inputs(frozen) == []
    file.write_text('new')
    assert controller.changed_inputs(frozen) == [str(file)]
    with pytest.raises(RuntimeError):
        controller.freeze_files(frozen,[file])
    file.unlink()
    assert controller.changed_inputs(frozen) == [str(file)]


def test_reports_attempted_on_partial_and_error_recorded_without_hiding_evidence(tmp_path):
    folder = tmp_path/'validation5'/'seed1'/'r1'
    valid_triplet(folder,profile=False)
    with mock.patch.object(controller.reports,'main',side_effect=ValueError('broken report')) as reporter:
        result = controller.report_partial(tmp_path)
    assert reporter.call_count == 1
    assert result[0]['state'] == 'NO_RAW_ROWS'
    assert result[1]['state'] == 'REPORT_ERROR'
    assert (folder/'raw.csv').is_file()
    assert controller.read(tmp_path/'report_status.json')['reports'] == result


def node(pid=123, name='perfect_drone_adaptive_node', rss=4609, owned=True):
    return dict(pid=pid,create_time=100.0,executable='/runtime/'+name,argv0='/runtime/'+name,
                rss_mib=rss,owned_descendant=owned)


def test_memory_sentinel_exact_name_owned_and_strict_threshold():
    assert controller.select_memory_runaway([node(rss=4608)]) is None
    assert controller.select_memory_runaway([node(rss=4609)])['pid'] == 123
    assert controller.select_memory_runaway([node(rss=3300)]) is None
    assert controller.select_memory_runaway([node(name='chrome',rss=9000)]) is None
    assert controller.select_memory_runaway([node(owned=False,rss=9000)]) is None
    assert controller.select_memory_runaway([node(rss=float('nan'))]) is None
    assert controller.select_memory_runaway([node(1,rss=4700),node(2,rss=4800)])['pid'] == 2


def test_capture_marks_contamination_before_debugger_permission_failure(tmp_path):
    item = {'path':str(tmp_path)}
    target = node()
    def debugger(*args, **kwargs):
        marker = controller.read(tmp_path/'diagnostic_contamination.json')
        assert marker['contaminated'] is True
        assert marker['cpu_performance_valid'] is False
        assert kwargs['timeout'] == 20
        assert 'thread apply all bt 24' in args[0]
        raise PermissionError('ptrace denied')
    with mock.patch.object(controller,'owned_composed_nodes',return_value=[target]), \
         mock.patch.object(controller.shutil,'which',return_value='/usr/bin/gdb'), \
         mock.patch.object(controller.subprocess,'run',side_effect=debugger) as capture:
        result = controller.capture_runaway(item,999,target)
    assert capture.call_count == 1
    assert 'ptrace denied' in result['error']
    assert result['capture_attempts'] == 1
    assert (tmp_path/'memory_runaway_diagnostic'/'result.json').is_file()


def test_capture_refuses_reused_or_unowned_pid(tmp_path):
    with mock.patch.object(controller,'owned_composed_nodes',return_value=[]), \
         mock.patch.object(controller.subprocess,'run') as capture:
        result = controller.capture_runaway({'path':str(tmp_path)},999,node())
    capture.assert_not_called()
    assert 'no longer' in result['error']
    assert controller.read(tmp_path/'diagnostic_contamination.json')['contaminated'] is True


def test_execute_captures_once_then_interrupts_only_owned_child_group(tmp_path):
    class Child:
        pid = 999
        returncode = None
        waits = []

        def wait(self, timeout):
            self.waits.append(timeout)
            if len(self.waits) == 1:
                raise controller.subprocess.TimeoutExpired('fake child',timeout)
            self.returncode = -2
            return self.returncode

        def poll(self):
            return self.returncode

    child = Child()
    item = {'name':'validation5_seed1_r01','path':str(tmp_path/'flight'), 'command':['never-run']}
    with mock.patch.object(controller.subprocess,'Popen',return_value=child), \
         mock.patch.object(controller,'owned_composed_nodes',return_value=[node()]), \
         mock.patch.object(controller,'capture_runaway') as capture, \
         mock.patch.object(controller.os,'killpg') as kill:
        with pytest.raises(controller.MemoryRunawayError):
            controller.execute(item,tmp_path,{})
    capture.assert_called_once_with(item,999,node())
    kill.assert_called_once_with(999,controller.signal.SIGINT)
    assert child.waits == [1.0,20]


def test_contaminated_triplet_never_passes_even_if_original_rows_are_successful(tmp_path):
    valid_triplet(tmp_path)
    original = (tmp_path/'raw.csv').read_bytes()
    controller.save(tmp_path/'diagnostic_contamination.json',{'contaminated':True})
    audit = controller.triplet_audit(tmp_path,'seed1',18000,True)
    assert not audit['valid'] and audit['checks']['not_diagnostic_contaminated'] is False
    assert (tmp_path/'raw.csv').read_bytes() == original
