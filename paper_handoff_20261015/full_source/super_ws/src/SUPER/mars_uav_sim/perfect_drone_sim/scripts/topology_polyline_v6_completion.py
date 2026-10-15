#!/usr/bin/env python3
"""Re-audit and preserve V6's 113-flight prefix; execute only its 127 missing slots."""
import argparse
import csv
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import topology_polyline_v6_campaign as core

PARENT = core.REPO/'results/topology_polyline_v6_n10_20261006'
ARCHIVE = core.REPO/'results/topology_polyline_v6_reader_fix_20261007/topology_polyline_v6_pilot.before.py'
READER = Path(__file__).with_name('topology_polyline_v6_pilot.py').resolve()
OLD_READER_SHA256 = '74e76d8763d6dde2534916f455d1082a347a8c5917deb6ebf756e3da31b80ecd'
BEFORE = "            and solid['completion'] == result['success']\n"
AFTER = ("            and solid['completion'] is True\n"
         "            and type(solid['success']) is bool\n"
         "            and solid['success'] == result['success']\n")
PREFIX_COUNT = 113
CORRECTED_SLOT = ('seven_map_n10','forest_cluster_f01',99528,'sector')


def key(row):
    return row['stage'],row['map'],int(row['run']),row['mode']


def verify_reader_fix(parent_protocol):
    """Accept exactly the documented audit-only edit, no other frozen-input change."""
    if (parent_protocol['hashes'].get(str(READER)) != OLD_READER_SHA256
            or core.sha256(ARCHIVE) != OLD_READER_SHA256):
        raise ValueError('Old inspector archive/frozen hash mismatch')
    old = ARCHIVE.read_text()
    if old.count(BEFORE) != 1 or READER.read_text() != old.replace(BEFORE,AFTER,1):
        raise ValueError('Unexpected inspector edit beyond observation/success separation')
    hashes = dict(parent_protocol['hashes'])
    hashes[str(READER)] = core.sha256(READER)
    core.verify_hashes(hashes)
    return hashes


def read_prefix():
    protocol = json.loads((PARENT/'protocol.json').read_text())
    state = json.loads((PARENT/'status.json').read_text())
    planned = core.plan()
    if (protocol['planned'] != planned or state['state'] != 'STOPPED_FOR_DIAGNOSIS'
            or state['observed_flights'] != PREFIX_COUNT
            or state['launch_requests'] != PREFIX_COUNT
            or state['current'] != planned[PREFIX_COUNT-1]
            or not state['forest_gate_passed']):
        raise ValueError('Unexpected parent inventory/state; no implicit retry')
    hashes = verify_reader_fix(protocol)
    with (PARENT/'flights.csv').open(newline='') as stream:
        saved = list(csv.DictReader(stream))
    if len(saved) != PREFIX_COUNT or [key(r) for r in saved] != [key(r) for r in planned[:PREFIX_COUNT]]:
        raise ValueError('Prefix is not the exact original planned order')
    raw_paths = {p.resolve() for p in PARENT.glob('*/**/raw.csv')}
    expected_paths = {(PARENT/r['directory']/'raw.csv').resolve() for r in planned[:PREFIX_COUNT]}
    if raw_paths != expected_paths:
        raise ValueError('Unexpected physical result outside prefix')
    if any((PARENT/r['directory']).exists() for r in planned[PREFIX_COUNT:]):
        raise ValueError('Remaining slot already exists; refusing duplicate execution')
    flights, replays, corrections, preserved_hashes = [], [], [], {}
    evidence = [PARENT/name for name in
        ('protocol.json','status.json','flights.csv','summary_by_map.md','controller.log','forest_gate.json')]
    for item, previous in zip(planned,saved):
        folder = PARENT/item['directory']
        group, complete = core.inspect(folder,item['map'],item['run'],[item['mode']])
        if not complete or len(group) != 1:
            raise ValueError('Incomplete preserved physical evidence')
        flight = group[0]
        # Only the mistaken quality flag may change. Outcomes and every measured
        # metric, artifact path and original raw/stack hash must stay identical.
        for name,value in flight.items():
            if name == 'quality_valid':
                continue
            old = previous[name]
            equivalent = (value is None and old == '' or
                isinstance(value,bool) and old == str(value) or
                isinstance(value,(int,float)) and not isinstance(value,bool) and float(old) == value or
                isinstance(value,str) and old == value)
            if not equivalent:
                raise ValueError('Preserved flight changed: '+name)
        if not flight['quality_valid'] or core.reference_failure(flight):
            raise ValueError('Preserved flight still fails evidence/reference gate')
        if previous['quality_valid'] != str(flight['quality_valid']):
            if key(item) != CORRECTED_SLOT or previous['quality_valid'] != 'False':
                raise ValueError('Unexpected quality correction')
            corrections.append(dict(identity=key(item),before=False,after=True,
                mission_success=flight['success'],contacts=flight['contacts'],
                reason='observer completion is independent of mission success'))
        replay = core.replay_solid(folder,flight)
        old_replay = json.loads((folder/'independent_solid_replay.json').read_text())
        if replay != old_replay:
            raise ValueError('Original independent replay disagreement')
        replays.append(dict(identity=key(item),**replay))
        with (folder/'raw.csv').open(newline='') as stream:
            raw = list(csv.DictReader(stream))
        if (len(raw) != 1 or raw[0]['map'] != item['map']
                or int(raw[0]['run']) != item['run'] or raw[0]['mode'] != item['mode']):
            raise ValueError('Original raw identity disagreement')
        child = json.loads((folder/'summary.json').read_text())['results'][0]
        if child['candidate'] != protocol['candidate']:
            raise ValueError('Original candidate disagreement')
        core.verify_hashes(json.loads((folder/'plan.json').read_text())['asset_sha256'])
        flight.update(stage=item['stage'],repeat=item['repeat'],solid_replay_valid=True)
        flights.append(flight)
        evidence.extend(p for p in folder.rglob('*') if p.is_file())
        evidence.append(folder.with_suffix('.controller.log'))
    if len(corrections) != 1:
        raise ValueError('Expected exactly one observation/success correction')
    for file in evidence:
        preserved_hashes[str(file.resolve())] = core.sha256(file)
    hashes.update(preserved_hashes)
    hashes[str(ARCHIVE)] = OLD_READER_SHA256
    for file in (Path(__file__).resolve(),Path(__file__).with_name('test_topology_polyline_v6_completion.py')):
        hashes[str(file)] = core.sha256(file)
    return dict(parent=str(PARENT),candidate=protocol['candidate'],hashes=hashes,
        planned=planned,remaining=planned[PREFIX_COUNT:],prefix_flights=flights,
        prefix_replays=replays,quality_corrections=corrections,
        preserved_physical_flights=PREFIX_COUNT,new_physical_flights=127,
        source_reader_migration=dict(before=OLD_READER_SHA256,after=core.sha256(READER),
            scope='observation completion versus mission success; no planner/map/profile edits'),
        separate_forest_cohort=True,original_failures_retained=True,retries=0,
        global_mission_cutoff_s=None,terminal_no_progress_s=60,terminal_no_progress_radius_m=0.02,
        canonical_promoted=False,frozen_c41_replaced=False)


def prepare(root):
    if root.exists():
        raise ValueError('Refusing existing continuation directory')
    proof = read_prefix()
    root.mkdir(parents=True,exist_ok=False)
    core.json_write(root/'protocol.json',proof,True)
    core.json_write(root/'prefix_reaudit.json',dict(
        physical_flights=PREFIX_COUNT,all_quality_valid=True,all_solid_replays_valid=True,
        quality_corrections=proof['quality_corrections'],replays=proof['prefix_replays']),True)
    core.json_write(root/'status.json',dict(state='READY',preserved_flights=PREFIX_COUNT,
        new_observed_flights=0,observed_flights=PREFIX_COUNT,total_planned_flights=240,
        forest_gate_passed=True,canonical_promoted=False),True)
    core.tables(root,proof['prefix_flights'])


def execute(root):
    proof = json.loads((root/'protocol.json').read_text())
    state = json.loads((root/'status.json').read_text())
    if (state['state'] != 'READY' or proof['planned'] != core.plan()
            or proof['remaining'] != core.plan()[PREFIX_COUNT:]
            or len(proof['prefix_flights']) != PREFIX_COUNT):
        raise ValueError('Expected untouched READY continuation; no implicit resume/retry')
    core.verify_hashes(proof['hashes'])
    flights, child = list(proof['prefix_flights']), None
    state.update(state='RUNNING',pid=os.getpid(),started_epoch_s=time.time(),
        launch_requests=0,new_observed_flights=0,current=None)
    def save():
        state.update(observed_flights=len(flights),new_observed_flights=len(flights)-PREFIX_COUNT,
            updated_epoch_s=time.time())
        core.json_write(root/'status.json',state); core.tables(root,flights)
    def interrupt(signum,frame):
        raise InterruptedError('Continuation interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupt); signal.signal(signal.SIGINT,interrupt)
    save()
    try:
        for item in proof['remaining']:
            core.verify_hashes(proof['hashes'])
            state['current'] = item; save()
            folder = root/item['directory']; folder.parent.mkdir(parents=True,exist_ok=True)
            with folder.with_suffix('.controller.log').open('x') as log:
                child = subprocess.Popen(['bash',str(core.LAUNCHER),str(folder),item['map'],
                    str(item['run']),item['mode']],cwd=core.REPO,stdin=subprocess.DEVNULL,
                    stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                state['child_pid'] = child.pid; state['launch_requests'] += 1; save()
                code = child.wait()
            group, complete = core.inspect(folder,item['map'],item['run'],[item['mode']])
            if not complete or len(group) != 1:
                raise ValueError('Incomplete single-flight evidence; no replacement')
            flight = group[0]
            flight.update(stage=item['stage'],repeat=item['repeat'],solid_replay_valid=False)
            flights.append(flight); save()
            replay = core.replay_solid(folder,flight)
            core.json_write(folder/'independent_solid_replay.json',replay,True)
            flight['solid_replay_valid'] = True
            with (folder/'raw.csv').open(newline='') as stream:
                raw = list(csv.DictReader(stream))
            if (len(raw) != 1 or raw[0]['map'] != item['map']
                    or int(raw[0]['run']) != item['run'] or raw[0]['mode'] != item['mode']):
                raise ValueError('Raw flight identity disagreement')
            result = json.loads((folder/'summary.json').read_text())['results'][0]
            if result['candidate'] != proof['candidate']:
                raise ValueError('Wrong candidate result')
            core.verify_hashes(json.loads((folder/'plan.json').read_text())['asset_sha256'])
            save()
            print(json.dumps(dict(event='flight_verified',observed_flights=len(flights),
                new_observed_flights=len(flights)-PREFIX_COUNT,stage=item['stage'],map=item['map'],
                mode=item['mode'],repeat=item['repeat'],success=flight['success'],
                contacts=flight['contacts'],time_s=flight['time_s'])),flush=True)
            if core.reference_failure(flight):
                state['failed_reference'] = flight
                raise ValueError('Actual Full/Adaptive failure; retain and stop')
            if code or not flight['quality_valid']:
                raise ValueError('Actual runtime/evidence/resource/speed failure; retain and stop')
        if ([key(r) for r in flights] != [key(r) for r in proof['planned']]
                or len({key(r) for r in flights}) != 240 or state['launch_requests'] != 127):
            raise ValueError('Final physical inventory mismatch')
        core.verify_hashes(proof['hashes'])
        core.json_write(root/'final_audit.json',dict(valid=True,unique_flights=240,
            preserved_flights=PREFIX_COUNT,new_physical_flights=127,forest_flights=30,
            seven_map_flights=210,retries=0,all_quality_valid=True,all_solid_replays_valid=True,
            quality_corrections=proof['quality_corrections'],original_failures_retained=True,
            canonical_promoted=False,frozen_c41_replaced=False),True)
        state.update(state='COMPLETE',completed_epoch_s=time.time(),current=None); save()
        print(json.dumps(state),flush=True); return 0
    except Exception as error:
        if child and child.poll() is None:
            os.killpg(child.pid,signal.SIGINT)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM); child.wait(timeout=5)
        state.update(state='STOPPED_FOR_DIAGNOSIS',error=str(error)); save()
        print(json.dumps(state),flush=True); return 1


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare-only',action='store_true')
    action.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    root = args.output.resolve()
    if args.execute:
        return execute(root)
    prepare(root)
    print(json.dumps(dict(state='READY',output=str(root),preserved=113,remaining=127)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
