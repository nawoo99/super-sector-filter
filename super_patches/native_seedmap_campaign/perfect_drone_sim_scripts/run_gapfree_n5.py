#!/usr/bin/env python3
"""Manual G1-G5 campaign: fresh transport/ON15, then OFF75 with complete records.

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

MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1, 6))
MODES = ('full', 'sector', 'adaptive')
PHASES = ('preflight', 'test5')
COUNTS = dict(preflight=1, test5=5)
CANDIDATE = 'c24_gapfree_d1_n5'
MANIFEST = REPO/'results/gapfree_d1_maps_20260918/manifest.json'
PROTOCOL = REPO/'docs/gapfree_n5_manual_campaign_20260918.md'
PRIOR_INVENTORY = REPO/'results/c25_normal_confirmation_20260917/iteration02/frozen_inputs_and_evidence.json'
PRIMARY_CONTACT_NOTE = 'Analytic static finite cylinders, body sphere radius0.2m, received odometry samples; not continuous swept collision proof'


def build_plan(root, base_run=30000):
    if type(base_run) is not int or base_run < 1:
        raise ValueError('Positive integer base-run required')
    commands = []
    for name in MAPS:
        for item in base.static_commands(root, name):
            if item['name'].startswith('accept_'):
                item['command'] = [sys.executable, str(SCRIPTS/'gapfree_campaign_support.py'),
                                   'static', *item['command'][2:]]
            commands.append(dict(item, map=name))
    for phase in PHASES:
        for repeat in range(COUNTS[phase]):
            shift = repeat % len(MAPS)
            for name in MAPS[shift:] + MAPS[:shift]:
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


def phase_gate(commands, phase):
    planned = [c for c in commands if c.get('phase') == phase]
    expected = {(m,r,mode) for m in MAPS for r in range(1,COUNTS[phase]+1) for mode in MODES}
    actual = [(c['map'],c['repeat'],m) for c in planned for m in c['modes']]
    identities = [(c['map'],c['run'],m) for c in planned for m in c['modes']]
    records = []
    for item in planned:
        fresh = triplet_audit(item)
        stored = base.load_document(Path(item['path'])/'triplet_verification.json')
        records.append(dict(name=item['name'], valid=fresh['valid'] is True and fresh==stored))
    checks = dict(exact_coverage=len(actual)==len(expected) and set(actual)==expected,
                  unique_identities=len(identities)==len(set(identities)),
                  fresh_stored_audits_match=bool(records) and all(r['valid'] for r in records))
    return dict(valid=base.explicit_true_checks(checks), phase=phase, checks=checks,
                expected_flights=len(expected), planned_triplets=len(planned), records=records)


def mean_sd(values):
    values = [n for v in values if (n:=base.number(v)) is not None]
    return dict(n=len(values), mean=statistics.mean(values) if values else None,
                sd=statistics.stdev(values) if len(values)>1 else None)


def write_progress(root):
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
    for index,name in enumerate(MAPS,1):
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
    lines=['# G1–G5 본시험 진행/결과 (모드별 목표5회)', '',
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


def reports(root):
    write_progress(root)
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
    if changed:
        raise RuntimeError('Existing C25 source/evidence changed; cannot silently claim same candidate: '+repr(changed))
    # Verify all old evidence once and hold runtime/source/config/binary inputs
    # throughout this campaign; completed old flight observations are not reused.
    frozen={p:h for p,h in old.items() if not p.startswith(str(REPO/'results'))}
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
                        original_normal_preserved=True,maps_manifest_sha256=base.sha(MANIFEST))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--dry-run',action='store_true',help='Offline check and plan only; no ROS processes')
    parser.add_argument('--report',type=Path,help='Rebuild reports of an existing result folder; no flight')
    args=parser.parse_args(argv)
    support.register_maps()
    if args.report:
        if args.output or args.dry_run:parser.error('--report is independent of --output/--dry-run')
        plan=base.load_document(args.report/'plan.json')
        if plan.get('schema')!='gapfree-n5-manual-v1':parser.error('Not a gapfree campaign result folder')
        reports(args.report.resolve());return
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
    def status(state,**extra):
        base.save(root/'status.json',dict(state=state,pid=os.getpid(),current=current,completed=history,
            requested_off_flights=75,requested_on_flights=15,automatic_retry=False,
            audited_off_flights=3*sum(e.get('phase')=='test5' and e.get('valid') is True for e in history),
            elapsed_s=time.monotonic()-started,updated_local=datetime.now().astimezone().isoformat(),**extra))
    def interrupted(signum,_frame):raise InterruptedError('Interrupted by signal '+str(signum))
    handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        print('RESULT DIRECTORY:',root,flush=True)
        status('PREPARING')
        frozen,admission=freeze_sources(root)
        base.save(root/'admission.json',admission)
        commands=build_plan(root)
        for phase in PHASES:
            base.save(root/phase/'plan.json',dict(maps=list(MAPS),phase=phase,independent_cohort=True,
                profile_preflight_runs_per_mode=1 if phase=='preflight' else 0,
                unprofiled_runs_per_mode=5 if phase=='test5' else 0,parent_plan=str(root/'plan.json')))
        base.save(root/'plan.json',dict(schema='gapfree-n5-manual-v1',maps=list(MAPS),modes=list(MODES),
            map_labels=dict(zip(MAPS,('G1','G2','G3','G4','G5'))),candidate=CANDIDATE,commands=commands,
            profiled_preflight_flights=15,unprofiled_primary_flights=75,static_dds_cases=30,rviz_cases=5,
            no_retry=True,no_replacement=True,all_failures_retained=True,no_runtime_tuning=True,
            primary_contact_scope=PRIMARY_CONTACT_NOTE,pcd_contact_is_secondary=True,
            full_adaptive_outcome_stop_boundary='After current triplet; at most2 remaining simulated modes',
            measurement_source_resource_failure_stops=True,sector_outcomes_as_metrics=True,
            async_certified_recovery=True,side_executor_threads=3,dispatch_lease_s=.25,
            mission_time_as_metric=True,historical_time_references=None,
            old_cohorts_not_pooled=True,primary_cpu_scope='Whole experiment cgroup, including simulator; observer excluded',
            original_cpu40_target_not_a_gate=True,frozen_sha256=frozen))
        base.freeze_files(frozen,[root/'plan.json',root/'admission.json',*(root/p/'plan.json' for p in PHASES)])
        base.save(root/'frozen_inputs_and_evidence.json',frozen)
        write_progress(root)
        if args.dry_run:
            status('DRY_RUN_ONLY',planned_flights=90,actual_flights_started=0)
            print('DRY RUN PASS: static35 + separateON15 + primaryOFF75; no ROS launched',flush=True)
            return
        previous_phase='static'
        for item in commands:
            current={k:v for k,v in item.items() if k!='command'}
            changed=base.changed_inputs(frozen)
            if changed:raise RuntimeError('Frozen inputs changed: '+repr(changed))
            if item['phase']!=previous_phase:
                if previous_phase=='static':
                    validations={m:base.static.validate_manifest(root/'static_preflight'/m/'acceptance.json',base.static.map_context(m)) for m in MAPS}
                    base.save(root/'static_gate.json',validations)
                    if not all(v.get('valid') is True for v in validations.values()):raise RuntimeError('Static transport/RViz gate failed')
                else:
                    gate=phase_gate(commands,previous_phase)
                    base.save(root/(previous_phase+'_gate.json'),gate);reports(root)
                    if gate['valid'] is not True:raise RuntimeError('Fresh ON15 gate failed; OFF75 not started')
                previous_phase=item['phase']
            status('RUNNING');print('START',item['name'],flush=True)
            try:
                # The common campaign lock covers static rendering too. Flight
                # child owns that same lock itself for its whole triplet.
                with contextlib.ExitStack() as stack:
                    if item['phase']=='static':
                        common=stack.enter_context(open(base.event.diagnostic.search.campaign.LOCK_PATH,'a'))
                        fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    code=base.execute(item,root,env)
            except base.MemoryRunawayError:
                history.append(dict(name=item['name'],phase=item['phase'],returncode=None,valid=False,diagnostic_contaminated=True))
                raise
            entry=dict(name=item['name'],phase=item['phase'],returncode=code);history.append(entry)
            if 'path' in item:
                folder=Path(item['path']);audit=triplet_audit(item)
                base.save(folder/'triplet_verification.json',audit)
                entry.update(valid=audit['valid'],outcome_failures=audit['outcome_failures'])
                if item['phase']=='preflight':
                    base.save(folder/'thread_cpu_summary.json',{m:base.stages.summarize(folder,m,item['run'],item['map'])
                              for m in MODES if (folder/f'{m}_summary.json').is_file()})
                write_progress(root)
                if code or not audit['valid']:raise RuntimeError('Flight gate failed; all attempts retained: '+item['name'])
                base.freeze_files(frozen,[folder/'plan.json',folder/'raw.csv',folder/'status.json',folder/'triplet_verification.json',
                    *(folder/f'{m}_summary.json' for m in MODES),*(contact_file(folder,item['map'],item['run'],m) for m in MODES),
                    *(folder/'artifacts'/f"{item['map']}_run{item['run']}_{m}.attempt1.odometry.csv" for m in MODES)])
            elif code:raise RuntimeError('Static verification failed: '+item['name'])
            elif item['name'].startswith('accept_'):
                path=root/'static_preflight'/item['map']/'acceptance.json'
                validation=base.static.validate_manifest(path,base.static.map_context(item['map']))
                if not validation['valid']:raise RuntimeError('Static manifest failed: '+item['map'])
                base.freeze_files(frozen,[path,*map(Path,validation['evidence_sha256'])])
            base.save(root/'frozen_inputs_and_evidence.json',frozen)
            print('FINISH',json.dumps(entry),flush=True);status('RUNNING')
        gate=phase_gate(commands,'test5');base.save(root/'test5_gate.json',gate)
        if not gate['valid'] or base.changed_inputs(frozen):raise RuntimeError('Final exact75/frozen evidence gate failed')
        if any(r['state']!='WRITTEN' for r in reports(root)):raise RuntimeError('Flights finished but reports incomplete')
        status('COMPLETE',completed_off_flights=75,completed_on_flights=15)
        print('COMPLETE:',root/'summary_by_map.md',flush=True)
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS',error=repr(exc))
        try:reports(root)
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
