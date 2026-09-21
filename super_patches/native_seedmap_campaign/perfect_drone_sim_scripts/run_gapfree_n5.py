#!/usr/bin/env python3
"""Manual gapfree campaign: fresh transport/profile, then n=5 with complete records.

Execute only when invoked by the user. Dry-run does offline validation and
writes the exact plan without launching ROS. Reuse existing runtime policy.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import statistics
import sys
import time

SCRIPTS = Path(__file__).resolve().parent
REPO = Path('/root/super-sector-filter')
LEGACY = REPO/'scripts/native_campaign'
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(SCRIPTS))
import run_c24_normal_validation as base
import gapfree_campaign_support as support

MAPS = support.MAPS
MODES = ('full', 'sector', 'adaptive')
PHASES = ('preflight', 'test5')
COUNTS = dict(preflight=1, test5=5)
CANDIDATE = 'c24_gapfree_d1_n5'
MANIFEST = support.MANIFEST
PROTOCOL = REPO/'docs/gapfree_n5_manual_campaign_20260918.md'
PRIOR_INVENTORY = REPO/'results/c25_normal_confirmation_20260917/iteration02/frozen_inputs_and_evidence.json'
PRIMARY_CONTACT_NOTE = 'Analytic static finite cylinders, body sphere radius0.2m, received odometry samples; not continuous swept collision proof'
OBSERVATION_ONLY_SOURCE_PATHS = frozenset({
    str(RUNTIME_PATH) for RUNTIME_PATH in (
        Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp'),
        Path('/root/super_ws/src/SUPER/rog_map/src/rog_map/prob_map.cpp'),
        Path('/root/super_ws/src/SUPER/rog_map/src/rog_map/rog_map.cpp'),
        Path('/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp'),
        Path('/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp'),
    )
})
CAMPAIGN_ORCHESTRATION_SOURCE_PATHS = frozenset({
    str(REPO/'scripts/native_campaign/native_campaign.py'),
    '/root/super_ws/src/SUPER/mission_planner/launch/benchmark_seedmap.launch.py',
})


def build_plan(root, base_run=30000, maps=None):
    if type(base_run) is not int or base_run < 1:
        raise ValueError('Positive integer base-run required')
    maps = tuple(MAPS if maps is None else maps)
    if not maps or len(maps) != len(set(maps)) or not set(maps) <= set(MAPS):
        raise ValueError('Non-empty unique gapfree map selection required')
    commands = []
    for name in maps:
        for item in base.static_commands(root, name):
            if item['name'].startswith('accept_'):
                item['command'] = [sys.executable, str(SCRIPTS/'gapfree_campaign_support.py'),
                                   'static', *item['command'][2:]]
            commands.append(dict(item, map=name))
    for phase in PHASES:
        for repeat in range(COUNTS[phase]):
            shift = repeat % len(maps)
            for name in maps[shift:] + maps[:shift]:
                index = MAPS.index(name)
                run = base_run + (0 if phase == 'preflight' else 100) + repeat*10 + index
                folder = root/phase/name/f'r{repeat+1:02d}_run{run}'
                reference = root/'preflight'/name/f'r01_run{base_run+index}'
                command = base.common_args(root)
                command[1] = str(SCRIPTS/'gapfree_cpu_compare.py')
                command.remove('--extended-demand-lease')
                i = command.index('--time-reference-folder')
                del command[i:i+2]
                for flag, value in {
                    '--candidate': CANDIDATE, '--side-executor-threads':'3',
                    '--static-latched-preflight': str(root/'static_preflight'/name/'acceptance.json'),
                }.items():
                    command[command.index(flag)+1] = value
                order = base.ORDERS[(repeat+index) % len(base.ORDERS)]
                command += ['--event-body-heading', '--mission-time-as-metric', '--sector-outcomes-as-metrics',
                            '--async-certified-recovery', '--map', name, '--run', str(run), '--output', str(folder)]
                command += ['--profile-cpu'] if phase == 'preflight' else [
                    '--small-pool-profile-reference', str(reference)]
                command += ['--modes', *order]
                commands.append(dict(name=f'{phase}_{name}_r{repeat+1:02d}', phase=phase, map=name,
                    run=run, repeat=repeat+1, modes=list(order), path=str(folder), candidate=CANDIDATE,
                    async_certified_recovery=True, command=command))
    return commands


def contact_file(folder, name, run, mode):
    return folder/'artifacts'/f'{name}_run{run}_{mode}.attempt1.cylinder_audit.json'


def triplet_audit(item):
    folder = Path(item['path'])
    audit = base.triplet_audit(folder, item['map'], item['run'], item['phase']=='preflight',
                              CANDIDATE, item['modes'], True)
    # Preserve every base check, including the historical sampled-PCD any-contact
    # observation. Analytic geometry supplies the new maps' primary episode count.
    checks = dict(audit['acceptance_checks'])
    contacts = {}
    for mode in MODES:
        path = contact_file(folder, item['map'], item['run'], mode)
        doc = base.load_document(path)
        contacts[mode] = doc
        checks[mode+':analytic_contact_evidence'] = contact_valid(doc, item['map'])
        checks[mode+':full_recorded_odometry'] = trajectory_evidence_valid(path, doc)
        count = contact_count(doc) if checks[mode+':analytic_contact_evidence'] else None
        audit['outcomes'][mode]['analytic_contact_episodes'] = count
        if count is None or count > 0 or mode in audit['outcome_failures']:
            audit['outcome_failures'][mode] = dict(audit['outcomes'][mode])
        if mode in ('full', 'adaptive'):
            checks[mode+':analytic_zero_contact'] = contact_count(doc) == 0 if contact_valid(doc,item['map']) else False
    audit.update(schema='gapfree-n5-triplet-v1', base_schema='c24-triplet-audit-v1',
        analytic_contacts=contacts, acceptance_checks=checks, valid=base.explicit_true_checks(checks))
    return audit


def contact_count(doc):
    value = doc.get('contact_episodes')
    return value if type(value) is int and value >= 0 else None


def contact_valid(doc, map_name):
    # Keep this explicit: a missing/unfinished observer must never imply zero.
    expected = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps')
    try:
        return (doc.get('audit_valid') is True and doc.get('map') == map_name
            and doc.get('completion') is True and type(doc.get('samples')) is int and doc['samples'] > 1
            and contact_count(doc) is not None and doc.get('robot_radius_m') == .2
            and doc.get('cylinder_count') == 410
            and doc.get('observation') == 'received_odometry_samples_only'
            and doc.get('swept_collision_check') is False
            and doc.get('cylinder_z_min_m') == 0 and doc.get('cylinder_z_max_m') == 3
            and all(doc.get(k)==0 for k in ('invalid_samples','timestamp_nonmonotonic_count','receipt_nonmonotonic_count'))
            and doc.get('cylinders_sha256') == base.sha(expected/(map_name+'_cylinders.csv'))
            and doc.get('pcd_sha256') == base.sha(expected/(map_name+'.pcd')))
    except (OSError,TypeError):
        return False


def trajectory_evidence_valid(path, doc):
    trajectory=path.with_name(path.name.removesuffix('.cylinder_audit.json')+'.odometry.csv')
    try:
        return trajectory.is_file() and doc.get('odometry_sha256') == base.sha(trajectory)
    except OSError:
        return False


def contact_only_failure(audit):
    """True only when known Full/Adaptive contact is the entire audit failure."""
    checks = audit.get('acceptance_checks', {})
    if not isinstance(checks, dict):
        return False
    failed = {name for name, passed in checks.items() if passed is not True}
    if not failed:
        return False
    tolerated = set()
    for mode in ('full', 'adaptive'):
        outcome = audit.get('outcomes', {}).get(mode, {})
        analytic = outcome.get('analytic_contact_episodes')
        sampled = base.number(outcome.get('safety_collisions'))
        observed = ((type(analytic) is int and analytic > 0)
                    or (sampled is not None and sampled > 0))
        evidence_ok = checks.get(mode + ':analytic_contact_evidence') is True
        trajectory_ok = checks.get(mode + ':full_recorded_odometry') is True
        if observed and evidence_ok and trajectory_ok:
            tolerated.update((mode + ':zero_contact', mode + ':analytic_zero_contact'))
    return failed <= tolerated


def audit_accepted(audit, continue_after_contact=False):
    return audit.get('valid') is True or (continue_after_contact and contact_only_failure(audit))


def phase_gate(commands, phase, continue_after_contact=False, maps=None):
    maps = tuple(MAPS if maps is None else maps)
    planned = [c for c in commands if c.get('phase') == phase]
    expected = {(m,r,mode) for m in maps for r in range(1,COUNTS[phase]+1) for mode in MODES}
    actual = [(c['map'],c['repeat'],m) for c in planned for m in c['modes']]
    identities = [(c['map'],c['run'],m) for c in planned for m in c['modes']]
    records = []
    for item in planned:
        fresh = triplet_audit(item)
        stored = base.load_document(Path(item['path'])/'triplet_verification.json')
        stored_match = fresh == stored
        records.append(dict(name=item['name'],
            valid=stored_match and audit_accepted(fresh, continue_after_contact),
            strict_valid=stored_match and fresh['valid'] is True,
            contact_only_continued=(stored_match and fresh['valid'] is not True
                                    and continue_after_contact and contact_only_failure(fresh))))
    checks = dict(exact_coverage=len(actual)==len(expected) and set(actual)==expected,
                  unique_identities=len(identities)==len(set(identities)),
                  fresh_stored_audits_match=bool(records) and all(r['valid'] for r in records))
    return dict(valid=base.explicit_true_checks(checks),
                strict_valid=bool(records) and all(r['strict_valid'] for r in records),
                continue_after_contact=continue_after_contact, phase=phase, checks=checks,
                expected_flights=len(expected), planned_triplets=len(planned), records=records)


def mean_sd(values):
    values = [n for v in values if (n:=base.number(v)) is not None]
    return dict(n=len(values), mean=statistics.mean(values) if values else None,
                sd=statistics.stdev(values) if len(values)>1 else None)


def write_progress(root, maps=None):
    maps = tuple(MAPS if maps is None else maps)
    observations=[]
    for raw_path in sorted((root/'test5').rglob('raw.csv')):
        with raw_path.open(newline='') as stream:
            for row in csv.DictReader(stream):
                folder=raw_path.parent
                doc=base.load_document(contact_file(folder,row['map'],row['run'],row['mode']))
                valid_contact=(contact_valid(doc,row['map']) and
                    trajectory_evidence_valid(contact_file(folder,row['map'],row['run'],row['mode']),doc))
                summary=base.load_document(folder/f"{row['mode']}_summary.json")
                recovery=summary.get('strict_recovery_audit',{})
                contaminated=(folder/'diagnostic_contamination.json').exists()
                duration=base.number(row.get('cgroup_cpu_duration_s'))
                costs_ok=(not contaminated and all(base.boolean(row.get(k)) is True
                    for k in ('run_valid','resource_valid','speed_limit_valid'))
                    and base.boolean(row.get('infrastructure_failure')) is False
                    and base.number(row.get('attempt_count')) == 1 and base.number(row.get('retry_count')) == 0
                    and duration is not None and duration > 0)
                observations.append(dict(row, contact_known=valid_contact,
                    analytic_contact_episodes=contact_count(doc) if valid_contact else None,
                    recovery_completed=len(recovery['completed_cycles']) if isinstance(recovery.get('completed_cycles'),list) else None,
                    costs_valid=costs_ok, raw_source=str(raw_path)))
    result=[]
    keys={'mission_time_s':'mission_time_s','cpu_cores':'end_to_end_cpu_cores_mean',
          'cpu_core_s':'end_to_end_cpu_core_s','input_mib_s':'map_payload_mib_s',
          'input_bytes':'map_payload_bytes_total','map_ms':'total_ms_mean'}
    for name in maps:
        index = MAPS.index(name) + 1
        for mode in MODES:
            rows=[r for r in observations if r['map']==name and r['mode']==mode]
            known=[r for r in rows if r['contact_known']]
            entry=dict(map_label=f'G{index}',map=name,mode=mode,planned=5,attempts=len(rows),
                completed=sum(base.boolean(r.get('success')) is True for r in rows),
                contact_known_runs=len(known),contact_unknown_runs=len(rows)-len(known),
                contact_runs=sum(r['analytic_contact_episodes']>0 for r in known),
                contact_episodes=sum(r['analytic_contact_episodes'] for r in known) if known else None,
                performance_valid_runs=sum(r['costs_valid'] for r in rows),
                adaptive_certified_recovery_cycles=sum(r['recovery_completed'] for r in rows if r['recovery_completed'] is not None) if any(r['recovery_completed'] is not None for r in rows) else None)
            entry['completion_pct_observed']=100*entry['completed']/len(rows) if rows else None
            for prefix,key in keys.items():
                stats=mean_sd(r.get(key) for r in rows if r['costs_valid'])
                entry.update({prefix+'_'+k:v for k,v in stats.items()})
            result.append(entry)
    for row in result:
        full=next(r for r in result if r['map']==row['map'] and r['mode']=='full')
        for metric in ('cpu_cores','cpu_core_s','input_mib_s','map_ms'):
            f,v=full[metric+'_mean'],row[metric+'_mean']
            row[metric+'_reduction_vs_full_pct']=100*(1-v/f) if f and v is not None else None
    with (root/'summary_by_map.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(result[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(result)
    def fmt(value,digits=3):
        return 'N/A' if value is None else f'{value:.{digits}f}'
    lines=['# G1–G4 + G5-R2 본시험 진행/결과 (모드별 목표5회)', '',
        '본시험75회만 집계. ON15는 별도 report_preflight. 접촉 횟수는 정적 원기둥/기체 구 모델의 수신 odometry 표본 기준 진입 episode 수.',
        'CPU는 실험 cgroup 전체(시뮬레이터 포함), 평균 cores 및 측정구간 core-s. 접촉/미완료 시도도 보존. 오류/오염 회차 비용은 N/A.', '',
        '| 맵 | 모드 | 수행/목표 | 완주/수행 | 완주율(%) | 접촉 주행 | 접촉 횟수 | 접촉 미확인 | 시간(s) | 평균 CPU(cores) | 누적 CPU(core-s) |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in result:
        lines.append(f"| {r['map_label']} | {r['mode']} | {r['attempts']}/5 | {r['completed']}/{r['attempts']} | {fmt(r['completion_pct_observed'],1)} | {r['contact_runs']}/{r['contact_known_runs']} | {r['contact_episodes'] if r['contact_episodes'] is not None else 'N/A'} | {r['contact_unknown_runs']} | {fmt(r['mission_time_s_mean'],2)} | {fmt(r['cpu_cores_mean'])} | {fmt(r['cpu_core_s_mean'],2)} |")
    lines += ['', '전체 지표·분포·감소율·GPU/메모리·주파수·실제 소스 전환: report_test5/summary_ko.md 및 all_metrics.csv.',
              '아직 실행하지 않은 slot이나 raw행 생성 전 중단은 실패0이 아니다. status.json의 상태·예정/수행 횟수를 함께 확인한다.',
              'legacy report의 safety_collisions는 기존 sampled-PCD 지표이며 이 표의 analytic contact episode와 별도다.']
    (root/'summary_by_map.md').write_text('\n'.join(lines)+'\n')
    return result


def report_protocol_fingerprint(plan):
    # Unique scratch paths isolate repeat invocations, not experimental policy.
    # All geometry, options and source-binding fields remain in the fingerprint.
    normalized = {k:v for k,v in plan.items() if k != 'gapfree_scratch_directory'}
    return LEGACY_REPORT_FINGERPRINT(normalized)


LEGACY_REPORT_FINGERPRINT = base.reports.protocol_fingerprint
LEGACY_REPORT_LOAD_RUNS = base.reports.load_runs

# Keep observed safety and attempt metadata even when comparative costs are
# inadmissible. Full original rows and traces remain unchanged on disk.
REPORT_OUTCOME_KEYS = {
    'success', 'run_valid', 'resource_valid', 'speed_limit_valid',
    'infrastructure_failure', 'attempt_count', 'retry_count',
    'first_attempt_success', 'diagnostic_contaminated', 'logical_cpus',
    'waypoints_reached', 'n_waypoints', 'closest_final_goal_distance_m',
    'collisions', 'safety_collisions', 'static_pcd_collisions',
    'min_clearance_m', 'static_pcd_clearance_m', 'static_pcd_min_distance_m',
    'static_pcd_enabled', 'static_pcd_point_count', 'contact_event_count',
    'live_only_contact_event_count', 'static_confirmed_live_contact_event_count',
    'static_hazard_collisions', 'static_hazard_min_clearance_m',
    'trap_collisions', 'trap_min_surface_distance_m', 'trap_clearance_m',
    'clearance_samples', 'samples', 'max_speed_mps', 'max_odom_speed_3d_mps',
    'max_command_speed_mps', 'max_command_horizontal_speed_mps',
    'speed_limit_mps', 'speed_tolerance_mps', 'speed_exceedance_count',
    'command_speed_exceedance_count', 'odom_speed_exceedance_count',
}
REPORT_OUTCOME_PREFIXES = ('first_contact_', 'first_speed_exceedance_',
                          'static_pcd_contact_', 'static_pcd_episodes_')


def report_load_runs(campaign_roots, repo):
    """Apply the same cost admission as the map summary, preserving all attempts."""
    runs, warnings = LEGACY_REPORT_LOAD_RUNS(campaign_roots, repo)
    raw_cache = {}
    for run in runs:
        source = Path(run['source'])
        if source not in raw_cache:
            with source.open(newline='') as stream:
                raw_cache[source] = list(csv.DictReader(stream))
        rows = [row for row in raw_cache[source] if all(
            str(row.get(key)) == str(run.get(key)) for key in ('map', 'mode', 'run'))]
        row = rows[0] if len(rows) == 1 else {}
        duration = base.number(row.get('cgroup_cpu_duration_s'))
        checks = dict(exact_raw_identity=len(rows) == 1,
            no_diagnostic_contamination=not (source.parent/'diagnostic_contamination.json').exists(),
            run_valid=base.boolean(row.get('run_valid')) is True,
            resource_valid=base.boolean(row.get('resource_valid')) is True,
            speed_limit_valid=base.boolean(row.get('speed_limit_valid')) is True,
            no_infrastructure_failure=base.boolean(row.get('infrastructure_failure')) is False,
            one_attempt=base.number(row.get('attempt_count')) == 1,
            no_retry=base.number(row.get('retry_count')) == 0,
            measured_duration=duration is not None and duration > 0)
        admissible = all(checks.values())
        run['cost_comparison_admission'] = dict(valid=admissible, checks=checks,
            scope='Same raw quality/no-retry/duration/contamination policy as summary_by_map; outcomes retained')
        if not admissible:
            def keep(key):
                return key in REPORT_OUTCOME_KEYS or key.startswith(REPORT_OUTCOME_PREFIXES)
            run['metrics'] = {key: value if keep(key) else None
                              for key, value in run['metrics'].items()}
            # The legacy contamination path suppresses some contact metadata.
            # Restore only original measured safety fields, never any cost.
            for key, value in row.items():
                if keep(key) and key not in ('run_valid', 'diagnostic_contaminated'):
                    run['metrics'][key] = base.reports.numeric(value)
            rejected = ', '.join(key for key, valid in checks.items() if not valid)
            warnings.append(f"{run['map']}/{run['run']}/{run['mode']}: comparative costs N/A "
                            f"({rejected}); attempt and observed safety outcome retained")
        run['metrics']['cost_comparison_valid'] = int(admissible)
    return runs, warnings


def reports(root, maps=None):
    maps = tuple(MAPS if maps is None else maps)
    write_progress(root, maps)
    records=[]
    for phase in PHASES:
        if not any((root/phase).rglob('raw.csv')):
            records.append(dict(phase=phase,state='NO_RAW_ROWS'));continue
        original = base.reports.protocol_fingerprint
        original_load_runs = base.reports.load_runs
        try:
            base.reports.protocol_fingerprint = report_protocol_fingerprint
            base.reports.load_runs = report_load_runs
            base.reports.main(['--campaign',str(root/phase),'--output',str(root/('report_'+phase))])
            records.append(dict(phase=phase,state='WRITTEN'))
        except BaseException as exc:
            records.append(dict(phase=phase,state='REPORT_ERROR',error=repr(exc)))
        finally:
            base.reports.protocol_fingerprint = original
            base.reports.load_runs = original_load_runs
    base.save(root/'report_status.json',dict(reports=records))
    return records


def freeze_sources(root):
    old=base.load_document(PRIOR_INVENTORY)
    if not old:
        raise RuntimeError('Missing previous frozen runtime inventory')
    changed=base.changed_inputs(old)
    admitted_paths=OBSERVATION_ONLY_SOURCE_PATHS|CAMPAIGN_ORCHESTRATION_SOURCE_PATHS
    unexpected=[path for path in changed if path not in admitted_paths]
    if unexpected:
        raise RuntimeError('Existing C25 source/evidence changed; cannot silently claim same candidate: '+repr(unexpected))
    # Verify all old evidence once and hold runtime/source/config/binary inputs
    # throughout this campaign; completed old flight observations are not reused.
    frozen={p:h for p,h in old.items() if not p.startswith(str(REPO/'results'))}
    source_overlay=[]
    for name in sorted(admitted_paths):
        path=Path(name)
        if name in frozen and path.is_file():
            current=base.sha(path)
            orchestration=name in CAMPAIGN_ORCHESTRATION_SOURCE_PATHS
            source_overlay.append(dict(path=name,baseline_sha256=frozen[name],current_sha256=current,
                classification=('observer_ready_campaign_orchestration' if orchestration
                                else 'observation_only_unbuilt_source'),
                executed_by_primary_campaign=orchestration,
                planner_algorithm_changed=False,
                installed_binary_remains_frozen=not orchestration))
            frozen[name]=current
    manifest=base.read(MANIFEST)
    for row in manifest['maps']:
        for p,h in row['assets_sha256'].items():
            if base.sha(p)!=h:raise RuntimeError('New map asset mismatch: '+p)
            frozen[p]=h
    paths=[MANIFEST,PROTOCOL,PRIOR_INVENTORY,*SCRIPTS.glob('*gapfree*.py'),SCRIPTS/'run_gapfree_n5.sh']
    paths += list((REPO/'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts').glob('*gapfree*'))
    paths += [REPO/'scripts/native_campaign/run_gapfree_n5.sh']
    base.freeze_files(frozen,paths)
    return frozen,dict(previous_files_verified=len(old),previous_changed_files=changed,
                        admitted_source_changes=source_overlay,
                        original_normal_preserved=True,maps_manifest_sha256=base.sha(MANIFEST))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--dry-run',action='store_true',help='Offline check and plan only; no ROS processes')
    parser.add_argument('--report',type=Path,help='Rebuild reports of an existing result folder; no flight')
    parser.add_argument('--continue-after-contact',action='store_true',
        help='Retain contact outcomes and continue; all non-contact failures still stop')
    parser.add_argument('--continue-after-failure',action='store_true',
        help='Best-effort scheduling: retain and continue after flight/static/process/resource/measurement failures')
    parser.add_argument('--maps',nargs='+',choices=MAPS,default=list(MAPS),
        help='Subset to execute; for example --maps gapfree_d1_m05r2 runs revised G5 only')
    args=parser.parse_args(argv)
    selected_maps=tuple(dict.fromkeys(args.maps))
    if len(selected_maps) != len(args.maps):
        parser.error('--maps entries must be unique')
    continue_after_contact = args.continue_after_contact or args.continue_after_failure
    support.register_maps()
    if args.report:
        if args.output or args.dry_run:parser.error('--report is independent of --output/--dry-run')
        plan=base.load_document(args.report/'plan.json')
        if plan.get('schema')!='gapfree-n5-manual-v1':parser.error('Not a gapfree campaign result folder')
        report_maps=tuple(plan.get('maps',MAPS))
        if not report_maps or len(report_maps)!=len(set(report_maps)) or not set(report_maps)<=set(MAPS):
            parser.error('Invalid map selection in campaign plan')
        reports(args.report.resolve(),report_maps);return
    root=(args.output or REPO/'results'/('gapfree_n5_'+datetime.now().strftime('%Y%m%d_%H%M%S')+f'_{os.getpid()}')).resolve()
    if root.exists():parser.error('Existing output refused; original attempts are never overwritten or resumed')
    if any(k.startswith('SUPER_') and k not in ('SUPER_CPU_PROFILE','SUPER_CALLBACK_TRACE') for k in os.environ):
        parser.error('Unexpected inherited SUPER_* override; use a clean terminal with campaign options')
    lock=open('/tmp/super_sector_filter_gapfree_n5.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:parser.error('Another gapfree campaign is already running')
    root.mkdir(parents=True,exist_ok=False)
    logfile=(root/'controller.log').open('x')
    previous_stdout,previous_stderr=sys.stdout,sys.stderr
    class Tee:
        def __init__(self,stream):self.stream=stream
        def write(self,value):
            result=self.stream.write(value);logfile.write(value);logfile.flush();return result
        def flush(self):self.stream.flush();logfile.flush()
    sys.stdout,sys.stderr=Tee(previous_stdout),Tee(previous_stderr)
    started,history,current,frozen=time.monotonic(),[],None,{}
    env=dict(os.environ,SUPER_CPU_PROFILE='0',SUPER_CALLBACK_TRACE='0')
    requested_off_flights=3*COUNTS['test5']*len(selected_maps)
    requested_on_flights=3*COUNTS['preflight']*len(selected_maps)
    def status(state,**extra):
        base.save(root/'status.json',dict(state=state,pid=os.getpid(),current=current,completed=history,
            requested_off_flights=requested_off_flights,requested_on_flights=requested_on_flights,automatic_retry=False,
            continue_after_contact=continue_after_contact,
            continue_after_failure=args.continue_after_failure,
            audited_off_flights=3*sum(e.get('phase')=='test5' and e.get('accepted_for_coverage') is True for e in history),
            elapsed_s=time.monotonic()-started,updated_local=datetime.now().astimezone().isoformat(),**extra))
    def update_progress(context):
        try:return write_progress(root,selected_maps)
        except Exception as exc:
            if not args.continue_after_failure:raise
            path=root/'progress_errors.json';document=base.load_document(path)
            errors=document.get('errors',[]) if isinstance(document,dict) else []
            errors.append(dict(context=context,error=repr(exc),time_local=datetime.now().astimezone().isoformat()))
            base.save(path,dict(errors=errors));return []
    def interrupted(signum,_frame):raise InterruptedError('Interrupted by signal '+str(signum))
    handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        print('RESULT DIRECTORY:',root,flush=True)
        status('PREPARING')
        frozen,admission=freeze_sources(root)
        base.save(root/'admission.json',admission)
        commands=build_plan(root,maps=selected_maps)
        for phase in PHASES:
            base.save(root/phase/'plan.json',dict(maps=list(selected_maps),phase=phase,independent_cohort=True,
                profile_preflight_runs_per_mode=1 if phase=='preflight' else 0,
                unprofiled_runs_per_mode=5 if phase=='test5' else 0,parent_plan=str(root/'plan.json')))
        base.save(root/'plan.json',dict(schema='gapfree-n5-manual-v1',maps=list(selected_maps),modes=list(MODES),
            map_labels={name:f'G{MAPS.index(name)+1}' for name in selected_maps},candidate=CANDIDATE,commands=commands,
            profiled_preflight_flights=requested_on_flights,unprofiled_primary_flights=requested_off_flights,
            static_dds_cases=6*len(selected_maps),rviz_cases=len(selected_maps),
            no_retry=True,no_replacement=True,all_failures_retained=True,no_runtime_tuning=True,
            primary_contact_scope=PRIMARY_CONTACT_NOTE,pcd_contact_is_secondary=True,
            continue_after_contact=continue_after_contact,
            continue_after_failure=args.continue_after_failure,
            full_adaptive_outcome_stop_boundary=('Contact is retained and campaign continues; non-contact failures stop'
                if args.continue_after_contact and not args.continue_after_failure else
                ('All trial failures are retained and scheduling continues; frozen-input changes and user interruption stop'
                 if args.continue_after_failure else 'After current triplet; at most2 remaining simulated modes')),
            measurement_source_resource_failure_stops=not args.continue_after_failure,sector_outcomes_as_metrics=True,
            async_certified_recovery=True,side_executor_threads=3,dispatch_lease_s=.25,
            mission_time_as_metric=True,historical_time_references=None,
            old_cohorts_not_pooled=True,primary_cpu_scope='Whole experiment cgroup, including simulator; observer excluded',
            original_cpu40_target_not_a_gate=True,frozen_sha256=frozen))
        base.freeze_files(frozen,[root/'plan.json',root/'admission.json',*(root/p/'plan.json' for p in PHASES)])
        base.save(root/'frozen_inputs_and_evidence.json',frozen)
        update_progress('initial')
        if args.dry_run:
            status('DRY_RUN_ONLY',planned_flights=requested_on_flights+requested_off_flights,actual_flights_started=0)
            print(f'DRY RUN PASS: maps={list(selected_maps)} separateON{requested_on_flights} '
                  f'+ primaryOFF{requested_off_flights}; no ROS launched',flush=True)
            return
        previous_phase='static'
        for item in commands:
            current={k:v for k,v in item.items() if k!='command'}
            changed=base.changed_inputs(frozen)
            if changed:raise RuntimeError('Frozen inputs changed: '+repr(changed))
            if item['phase']!=previous_phase:
                if previous_phase=='static':
                    try:
                        validations={m:base.static.validate_manifest(root/'static_preflight'/m/'acceptance.json',base.static.map_context(m)) for m in selected_maps}
                        base.save(root/'static_gate.json',validations)
                        static_valid=all(v.get('valid') is True for v in validations.values())
                    except Exception as exc:
                        static_valid=False
                        base.save(root/'static_gate.json',dict(valid=False,error=repr(exc)))
                    if not static_valid and not args.continue_after_failure:
                        raise RuntimeError('Static transport/RViz gate failed')
                else:
                    try:
                        gate=phase_gate(commands,previous_phase,continue_after_contact,selected_maps)
                    except Exception as exc:
                        gate=dict(valid=False,phase=previous_phase,error=repr(exc))
                    base.save(root/(previous_phase+'_gate.json'),gate)
                    try:reports(root,selected_maps)
                    except Exception as exc:base.save(root/(previous_phase+'_report_error.json'),dict(error=repr(exc)))
                    if gate['valid'] is not True and not args.continue_after_failure:
                        raise RuntimeError(
                            f'Fresh ON{requested_on_flights} measurement/completion gate failed; '
                            f'OFF{requested_off_flights} not started')
                previous_phase=item['phase']
            status('RUNNING');print('START',item['name'],flush=True)
            execution_error=None;memory_runaway=False
            try:
                # The common campaign lock covers static rendering too. Flight
                # child owns that same lock itself for its whole triplet.
                with contextlib.ExitStack() as stack:
                    if item['phase']=='static':
                        common=stack.enter_context(open(base.event.diagnostic.search.campaign.LOCK_PATH,'a'))
                        fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    code=base.execute(item,root,env)
            except InterruptedError:
                raise
            except Exception as exc:
                if not args.continue_after_failure:
                    if isinstance(exc,base.MemoryRunawayError):
                        history.append(dict(name=item['name'],phase=item['phase'],returncode=None,
                            valid=False,diagnostic_contaminated=True,execution_error=repr(exc)))
                    raise
                code=None;execution_error=repr(exc);memory_runaway=isinstance(exc,base.MemoryRunawayError)
            entry=dict(name=item['name'],phase=item['phase'],returncode=code);history.append(entry)
            if execution_error is not None:
                entry.update(valid=False,accepted_for_coverage=False,execution_error=execution_error,
                    diagnostic_contaminated=memory_runaway)
                update_progress(item['name']+':execution_error')
                print('FINISH_RETAINED_FAILURE',json.dumps(entry),flush=True);status('RUNNING')
                continue
            if 'path' in item:
                folder=Path(item['path'])
                try:audit=triplet_audit(item)
                except Exception as exc:
                    if not args.continue_after_failure:raise
                    entry.update(valid=False,accepted_for_coverage=False,audit_error=repr(exc))
                    update_progress(item['name']+':audit_error')
                    print('FINISH_RETAINED_FAILURE',json.dumps(entry),flush=True);status('RUNNING')
                    continue
                base.save(folder/'triplet_verification.json',audit)
                accepted=audit_accepted(audit,continue_after_contact)
                entry.update(valid=audit['valid'],accepted_for_coverage=accepted,
                    contact_only_continued=(accepted and audit['valid'] is not True),
                    outcome_failures=audit['outcome_failures'])
                if item['phase']=='preflight':
                    try:
                        base.save(folder/'thread_cpu_summary.json',{m:base.stages.summarize(folder,m,item['run'],item['map'])
                                  for m in MODES if (folder/f'{m}_summary.json').is_file()})
                    except Exception as exc:
                        if not args.continue_after_failure:raise
                        entry['thread_cpu_summary_error']=repr(exc)
                update_progress(item['name']+':complete')
                if (code or not accepted) and not args.continue_after_failure:
                    raise RuntimeError('Flight measurement/completion gate failed; all attempts retained: '+item['name'])
                evidence=[folder/'plan.json',folder/'raw.csv',folder/'status.json',folder/'triplet_verification.json',
                    *(folder/f'{m}_summary.json' for m in MODES),*(contact_file(folder,item['map'],item['run'],m) for m in MODES),
                    *(folder/'artifacts'/f"{item['map']}_run{item['run']}_{m}.attempt1.odometry.csv" for m in MODES)]
                base.freeze_files(frozen,evidence if not args.continue_after_failure else [p for p in evidence if p.is_file()])
            elif code and not args.continue_after_failure:raise RuntimeError('Static verification failed: '+item['name'])
            elif item['name'].startswith('accept_'):
                path=root/'static_preflight'/item['map']/'acceptance.json'
                try:validation=base.static.validate_manifest(path,base.static.map_context(item['map']))
                except Exception as exc:
                    validation=dict(valid=False,error=repr(exc),evidence_sha256={})
                entry['valid']=validation.get('valid') is True
                if not entry['valid'] and not args.continue_after_failure:
                    raise RuntimeError('Static manifest failed: '+item['map'])
                evidence=[path,*map(Path,validation.get('evidence_sha256',{}))]
                base.freeze_files(frozen,evidence if not args.continue_after_failure else [p for p in evidence if p.is_file()])
            base.save(root/'frozen_inputs_and_evidence.json',frozen)
            print('FINISH',json.dumps(entry),flush=True);status('RUNNING')
        try:gate=phase_gate(commands,'test5',continue_after_contact,selected_maps)
        except Exception as exc:gate=dict(valid=False,phase='test5',error=repr(exc))
        base.save(root/'test5_gate.json',gate)
        changed=base.changed_inputs(frozen)
        if changed:raise RuntimeError('Frozen evidence changed: '+repr(changed))
        try:report_records=reports(root,selected_maps)
        except Exception as exc:
            report_records=[dict(phase='all',state='REPORT_ERROR',error=repr(exc))]
            base.save(root/'report_error.json',report_records[0])
        report_ok=all(r['state']=='WRITTEN' for r in report_records)
        if (not gate['valid'] or not report_ok) and not args.continue_after_failure:
            raise RuntimeError(f'Final exact{requested_off_flights} evidence/report gate failed')
        retained=any(e.get('returncode') not in (0,None) or e.get('valid') is False
                     or e.get('execution_error') or e.get('audit_error') for e in history)
        retained=retained or not gate.get('valid',False) or not report_ok
        status('COMPLETE_WITH_RETAINED_FAILURES' if retained else 'COMPLETE',
            completed_off_flights=requested_off_flights if gate.get('valid') else None,
            scheduled_off_flights=requested_off_flights,scheduled_on_flights=requested_on_flights,
            retained_failures=retained)
        print('FINISHED:',root/'summary_by_map.md',flush=True)
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS',error=repr(exc))
        try:reports(root,selected_maps)
        except BaseException as report_error:base.save(root/'report_error.json',dict(error=repr(report_error)))
        print('STOPPED; preserved results:',root,repr(exc),file=sys.stderr,flush=True)
        raise
    finally:
        for sig,handler in handlers.items():signal.signal(sig,handler)
        lock.close()
        sys.stdout,sys.stderr=previous_stdout,previous_stderr
        logfile.close()


if __name__=='__main__':
    main()
