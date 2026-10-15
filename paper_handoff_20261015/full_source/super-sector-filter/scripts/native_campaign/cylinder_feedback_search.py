#!/usr/bin/env python3
"""Persistent failure -> audit -> new map -> test -> fresh n20 search.

No candidate-count stopping rule. Stop only at five observed n20 qualifying
maps, user cancellation, or a genuine infrastructure/integrity resource block.
All outcome-dependent selections and rejected maps are retained explicitly.
"""
import csv
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import cylinder_feedback_geometry as geometry
import cylinder_feedback_audit as audit
import cylinder_map_search as search
import cylinder_solid_campaign as solid
import cylinder_background_diagnostic as diagnostic
import confirm_cylinder_search_n20 as confirmation
from analyze_cylinder_only_stress_full_gate import quality_valid

ROOT=search.ROOT/'results/cylinder_feedback_search_20260915'
DIAGNOSTICS=search.ROOT/'results/cylinder_background_diagnostic_20260915'
INITIAL=[dict(name='cyl2_l0001',parent='cyl2_k02',action='origin_background'),
         dict(name='cyl2_l0002',parent='cyl2_k03',action='origin_background'),
         dict(name='cyl2_l0003',parent='cyl2_k06',action='open_escape',position=[11.694730456669117,-18.99846723955505],escape_radius=4.),
         dict(name='cyl2_l0004',parent='cyl2_k04',action='harden',iteration=1),
         dict(name='cyl2_l0005',parent='cyl2_k05',action='harden',iteration=3)]


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def read_rows(path):
    if not path.exists():return []
    with path.open() as stream:return list(csv.DictReader(stream))


def validate(rows,name,runs):
    keys={(int(r['run']),r['mode']) for r in rows}
    if (len(keys)!=len(rows) or not keys<={(n,m) for n in runs for m in confirmation.MODES}
            or any(r['map']!=name or not quality_valid(r) or not confirmation.known_outcome(r) for r in rows)):
        raise RuntimeError('Invalid/duplicate evidence retained; manual infrastructure diagnosis required')


def stage_decision(rows,audits):
    if confirmation.reference_failure(rows):return 'REFERENCE_FAILURE'
    if any(a['signature'] in ('EMPTY_INPUT_STALL','PENDING_REFRESH_ACK') for a in audits):return 'INPUT_REDESIGN'
    if len(rows)<9:return 'MORE_DIAGNOSTIC_BLOCKS'
    if confirmation.qualified(rows,3) and audit.meaningful_sector_difference(rows,audits):return 'QUALIFIED'
    return 'NO_MEANINGFUL_SEPARATION'


def ensure_candidate(recipe):
    p=search.OUT/recipe['name']/'manifest.json'
    if p.exists():
        m=json.loads(p.read_text())
        if m['parameters']!=recipe or m['policy']!=search.frozen_policy():raise RuntimeError('Existing candidate declaration changed')
        if any(search.geometry.sha256(Path(a))!=h for a,h in m['assets'].items()):raise RuntimeError('Candidate asset changed')
    else:geometry.emit(recipe)


def verify(plan):
    if search.frozen_policy()!=plan['runtime_policy']:raise RuntimeError('Frozen runtime changed')
    for p,h in plan['instrumentation_sha256'].items():
        if search.geometry.sha256(Path(p))!=h:raise RuntimeError('Frozen research helper changed')
    if shutil.disk_usage(ROOT).free<8*1024**3:raise RuntimeError('Less than8 GiB disk free; preserve evidence, stop for storage direction')


def assert_no_other_flight():
    names={'fsm_node','perfect_drone_full_node','perfect_drone_frontend_node','perfect_drone_node'}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            argv=entry.joinpath('cmdline').read_bytes().split(b'\0')
            if argv and Path(os.fsdecode(argv[0])).name in names:
                raise RuntimeError(f'Existing simulator/planner PID{entry.name}; do not start concurrent flight')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue


def run_development(name,with_ack,plan,checkpoint):
    folder=(DIAGNOSTICS if with_ack else solid.OUT)/name
    raw=folder/('diagnostic_raw.csv' if with_ack else 'raw.csv')
    rows=read_rows(raw);validate(rows,name,range(1,4))
    if any(r.get('solid_observer_sha256')!=search.geometry.sha256(solid.OBSERVER) for r in rows):
        raise RuntimeError('Recorded observer differs from current measurement protocol')
    declaration=dict(map=name,with_extra_ack_observer=with_ack,runs=[1,2,3],
                     protocol='diagnostic-only' if with_ack else 'standard-prelaunch-solid',
                     plan_sha256=search.geometry.sha256(ROOT/'plan.json'),
                     manifest_sha256=search.geometry.sha256(search.OUT/name/'manifest.json'))
    freeze=folder/'feedback_stage_freeze.json'
    if freeze.exists() and json.loads(freeze.read_text())!=declaration:raise RuntimeError('Stage declaration changed')
    if not freeze.exists():save(freeze,declaration)
    # L0001 may be adopted from the pilot started before this controller existed.
    if rows and with_ack and (folder/'freeze.json').exists():
        old=json.loads((folder/'freeze.json').read_text())
        if (old['runtime_policy']!=plan['runtime_policy'] or old['candidate_manifest_sha256']!=declaration['manifest_sha256']
                or old['diagnostic_script_sha256']!=search.geometry.sha256(Path(diagnostic.__file__))):
            raise RuntimeError('Pilot adoption integrity mismatch')
    audits=audit.audit_failures(rows)
    for run in range(1,4):
        keys={(int(r['run']),r['mode']) for r in rows}
        this={m for n,m in keys if n==run}
        # Complete a partly recorded block after restart, even if it failed.
        if not this and stage_decision(rows,audits) not in ('MORE_DIAGNOSTIC_BLOCKS','QUALIFIED'):break
        if len(this)==3:continue
        with raw.open('a',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=solid.FIELDS,extrasaction='ignore',lineterminator='\n')
            if stream.tell()==0:writer.writeheader();stream.flush()
            offset=run-1;modes=confirmation.MODES[offset:]+confirmation.MODES[:offset]
            for mode in modes:
                if (run,mode) in keys:continue
                checkpoint(map=name,phase='diagnostic' if with_ack else 'standard_development',run=run,mode=mode)
                verify(plan)
                if with_ack:
                    row,ack=diagnostic.trial(name,mode,run,folder)
                else:row=solid.run_trial(name,mode,run,folder);ack=None
                writer.writerow(row);stream.flush();rows.append(row)
                validate(rows,name,range(1,4))
                if ack and (ack['malformed'] or ack['first_odom_epoch_s'] is None or ack['last_odom_epoch_s'] is None):
                    raise RuntimeError('Invalid ACK observation retained')
                verify(plan)
                print('FEEDBACK_FLIGHT '+json.dumps({k:row[k] for k in ('map','run','mode','success','mission_time_s','solid_collision_episodes')}),flush=True)
                checkpoint(last_flight={k:row[k] for k in ('map','run','mode','success','mission_time_s','solid_collision_episodes')})
        audits=audit.audit_failures(rows)
        if stage_decision(rows,audits)!='MORE_DIAGNOSTIC_BLOCKS':break
    outcome=dict(map=name,phase='diagnostic' if with_ack else 'standard_development',rows=len(rows),
                 decision=stage_decision(rows,audits),counts=confirmation.result(rows)['counts'],audits=audits)
    save(folder/'feedback_result.json',outcome)
    return outcome


def run_confirmation(name,plan,checkpoint):
    folder=confirmation.ROOT/name;raw=folder/'raw.csv';rows=read_rows(raw)
    validate(rows,name,confirmation.RUNS)
    if not confirmation.result(rows)['exact_60_unique_rows'] and not confirmation.reference_failure(rows):
        checkpoint(map=name,phase='confirmation_n20',run=None,mode=None)
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/'feedback_controller.log').open('a') as log:
            proc=solid.search.campaign.spawn_process_group([sys.executable,str(Path(confirmation.__file__)),
                 name,'--min-development-runs','3','--stop-on-reference-failure'],stdout=log,stderr=log)
            try:
                while proc.poll() is None:
                    time.sleep(10)
                    current=read_rows(raw)
                    checkpoint(confirmation_rows=len(current),confirmation_counts=confirmation.result(current)['counts'])
                if proc.returncode:raise RuntimeError(f'Confirmation child failed:{proc.returncode}; evidence retained')
            finally:solid.search.campaign.terminate_group(proc,grace_s=3.)
    rows=read_rows(raw);validate(rows,name,confirmation.RUNS);verify(plan)
    result=confirmation.result(rows);audits=audit.audit_failures(rows)
    meaningful=audit.meaningful_sector_difference(rows,audits)
    passed=result['observed_user_criterion_met'] and meaningful
    # A completed n20 with only empty-cloud failures must trigger another map.
    outcome=dict(map=name,phase='confirmation_n20',rows=len(rows),counts=result['counts'],
        decision='OBSERVED_N20_TARGET' if passed else 'REFERENCE_FAILURE' if confirmation.reference_failure(rows)
        else 'INPUT_REDESIGN' if audits else 'NO_MEANINGFUL_SEPARATION',
        audits=audits,observed_target=passed,population_guarantee=False)
    save(folder/'feedback_result.json',outcome);return outcome


def evaluate(recipe,plan,checkpoint):
    name=recipe['name'];outcome=run_development(name,True,plan,checkpoint)
    if outcome['decision']!='QUALIFIED':return outcome
    outcome=run_development(name,False,plan,checkpoint)
    if outcome['decision']!='QUALIFIED':return outcome
    return run_confirmation(name,plan,checkpoint)


def enqueue_after_result(state,recipe,outcome):
    """Atomic state transition: a failed candidate always gets a NEW recipe."""
    state['completed_candidates'].append(dict(map=recipe['name'],decision=outcome['decision'],rows=outcome.get('rows',0)))
    if outcome.get('observed_target'):
        if recipe['name'] not in state['passed']:state['passed'].append(recipe['name'])
    if len(state['passed'])<state['target']:
        index=state['next_index'];state['next_index']+=1
        parent=recipe['parent'] if outcome['decision']=='GEOMETRY_REJECTION' else recipe['name']
        new=audit.feedback_recipe(f'cyl2_l{index:04d}',parent,index,outcome.get('audits',[]))
        state['queue'].append(new)
    state['current_recipe']=None


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert_no_other_flight()
    files=[Path(__file__).resolve(),Path(geometry.__file__),Path(audit.__file__),Path(diagnostic.__file__),
           Path(solid.__file__),solid.OBSERVER,Path(confirmation.__file__),Path(search.__file__),Path(geometry.routes.__file__),
           Path(search.geometry.__file__),Path(sys.modules['cylinder_background_variants'].__file__),
           Path(sys.modules['audit_cylinder_flight_segments'].__file__),
           Path(sys.modules['analyze_cylinder_only_stress_full_gate'].__file__)]
    plan=dict(schema='persistent-map-only-feedback-v1',target=5,initial=INITIAL,no_candidate_count_limit=True,
        runtime_policy=search.frozen_policy(),instrumentation_sha256={str(p):search.geometry.sha256(p) for p in files},
        development_protocol='extra-ACK n3 then separate standard-solid n3; no pooling',
        confirmation='fresh standard-solid runs101..120 per mode; stop at failed reference block boundary',
        criterion='Full20/20 and Adaptive20/20 safe; Sector has actual failure/contact plus at least one completion and a non-empty-input failure signature',
        stopping='five observed qualifying maps, user cancellation, or real infrastructure/integrity/storage block',
        selection='outcome-dependent including n20; all failures and maps retained; not independent holdout',
        auto_git_snapshot_between_candidates=True,no_push=True)
    plan_path=ROOT/'plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text())!=plan:raise RuntimeError('Feedback plan changed')
    if not plan_path.exists():save(plan_path,plan)
    state_path=ROOT/'status.json'
    state=(json.loads(state_path.read_text()) if state_path.exists() else
           dict(queue=INITIAL.copy(),current_recipe=None,passed=[],completed_candidates=[],next_index=6,target=5))
    state.update(pid=os.getpid(),state='RUNNING')
    def checkpoint(**changes):
        state.update(changes);state['updated_epoch_s']=time.time();save(state_path,state)
    solid.search.campaign.install_campaign_signal_handlers();checkpoint()
    try:
        while len(state['passed'])<state['target']:
            verify(plan)
            if state['current_recipe'] is None:
                state['current_recipe']=state['queue'].pop(0)
            recipe=state['current_recipe'];name=recipe['name']
            checkpoint(map=name,phase='geometry',run=None,mode=None)
            save(ROOT/name/'recipe.json',recipe)
            result_path=ROOT/name/'result.json'
            if result_path.exists():outcome=json.loads(result_path.read_text())
            else:
                try:ensure_candidate(recipe)
                except ValueError as error:
                    outcome=dict(map=name,decision='GEOMETRY_REJECTION',rows=0,audits=[],reason=str(error))
                else:
                    snapshot(name)
                    outcome=evaluate(recipe,plan,checkpoint)
                save(result_path,outcome)
            enqueue_after_result(state,recipe,outcome);checkpoint()
            snapshot(name)
            print('FEEDBACK_CANDIDATE '+json.dumps(dict(map=name,decision=outcome['decision'],passed=state['passed'],queued=len(state['queue']))),flush=True)
        checkpoint(state='TARGET_OBSERVED',phase='complete')
    except BaseException as error:
        checkpoint(state='STOPPED_FOR_DIAGNOSIS',error=str(error));raise
    finally:solid.search.campaign.cleanup_active_process_groups()


def snapshot(name):
    """Commit only this search's files, between flights; never touch upstream."""
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=search.ROOT,text=True)
    if staged.strip():raise RuntimeError('User-staged files present; do not mix automatic evidence commit')
    mirror=search.ROOT/'super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim'
    candidates=[ROOT,search.OUT/name,DIAGNOSTICS/name,solid.OUT/name,confirmation.ROOT/name,
                mirror/'config'/f'{name}.yaml',mirror/'pcd/seed_maps'/f'{name}.pcd']
    paths=[str(p.relative_to(search.ROOT)) for p in candidates if p.exists()]
    subprocess.run(['git','add','--',*paths],cwd=search.ROOT,check=True,stdout=subprocess.DEVNULL)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=search.ROOT).returncode:
        subprocess.run(['git','-c','gc.auto=0','commit','-m',f'Retain map-only feedback evidence for {name}'],
                       cwd=search.ROOT,check=True,stdout=subprocess.DEVNULL)


def wait_for_pilot(pid):
    """Handoff survives the chat turn, but never resumes a cancelled pilot."""
    path=DIAGNOSTICS/'cyl2_l0001'/'status.json'
    marker=ROOT/'handoff_status.json'
    try:
        while Path(f'/proc/{pid}').exists():
            try:cmd=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
            except FileNotFoundError:break
            if 'cylinder_background_diagnostic.py cyl2_l0001' not in cmd:
                raise RuntimeError('Pilot PID identity changed; refusing ambiguous handoff')
            save(marker,dict(state='WAITING_FOR_PILOT',pid=os.getpid(),pilot_pid=pid,updated_epoch_s=time.time()))
            time.sleep(5)
        if json.loads(path.read_text())['state']!='DIAGNOSTIC_COMPLETE':
            raise RuntimeError('Pilot did not finish normally; do not automatically resume a cancellation/invalid run')
        assert_no_other_flight()
        save(marker,dict(state='PILOT_COMPLETE_HANDOFF',pid=os.getpid(),updated_epoch_s=time.time()))
    except BaseException as error:
        save(marker,dict(state='HANDOFF_STOPPED',pid=os.getpid(),error=str(error),updated_epoch_s=time.time()));raise


def snapshot_implementation():
    """Initial approved source/evidence snapshot, after pilot, before new flight."""
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=search.ROOT,text=True).strip():
        raise RuntimeError('Pre-existing staged changes; preserve them and stop handoff')
    relative=['scripts/native_campaign/cylinder_feedback_audit.py',
              'scripts/native_campaign/cylinder_feedback_geometry.py',
              'scripts/native_campaign/test_cylinder_feedback_geometry.py',
              'scripts/native_campaign/cylinder_feedback_search.py',
              'scripts/native_campaign/test_cylinder_feedback_audit.py',
              'scripts/native_campaign/test_cylinder_feedback_search.py',
              'docs/cylinder_persistent_feedback_20260915.md',
              'docs/cylinder_background_five_maps_20260915.md',
              'docs/codex_handoff_full_v10_contact_investigation.md',
              'docs/viability_guard_ciri_avoidance_2026-08-15.md','docs/연구일지.md',
              'results/cylinder_background_five_20260915',
              'results/cylinder_background_diagnostic_20260915/cyl2_l0001']
    paths=[p for p in relative if (search.ROOT/p).exists()]
    subprocess.run(['git','add','--',*paths],cwd=search.ROOT,check=True,stdout=subprocess.DEVNULL)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=search.ROOT).returncode:
        subprocess.run(['git','-c','gc.auto=0','commit','-m','Continue map-only redesign after failures through fresh n20 confirmation'],
                       cwd=search.ROOT,check=True,stdout=subprocess.DEVNULL)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-for-pilot',type=int)
    args=parser.parse_args()
    if args.wait_for_pilot:
        wait_for_pilot(args.wait_for_pilot);snapshot_implementation()
    main()
