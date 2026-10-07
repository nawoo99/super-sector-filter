"""Audit semantics and continuation fixtures; not physical safety evidence."""
import csv
import json
from pathlib import Path
import pytest
import topology_polyline_v6_pilot as pilot
import topology_polyline_v6_campaign as campaign
import topology_polyline_v6_completion as completion
from test_topology_polyline_v6_campaign import install_fake_runtime


@pytest.mark.parametrize('mode,success,contacts,observer_done,solid_success,audit_valid,expected',[
    ('sector',False,1,True,False,True,True),
    ('sector',False,0,True,False,True,True),
    ('sector',True,1,True,True,True,True),
    ('full',False,0,True,False,True,True),
    ('adaptive',False,0,True,False,True,True),
    ('sector',False,1,False,False,True,False),
    ('sector',False,1,True,True,True,False),
    ('sector',False,1,True,None,True,False),
    ('sector',False,1,True,False,False,False),
])
def test_inspector_separates_observation_from_mission(tmp_path,monkeypatch,
        mode,success,contacts,observer_done,solid_success,audit_valid,expected):
    folder=tmp_path/'flight'; (folder/'artifacts').mkdir(parents=True)
    (folder/'artifacts'/f'map_run1_{mode}.attempt1.stack.log').write_text('original flight\n')
    result=dict(map='map',run=1,mode=mode,success=success,safety_collisions=contacts,
        run_valid=True,resource_valid=True,speed_limit_valid=True,
        source_acquisition={'checks':{'source_valid':True}},
        strict_recovery_audit={'valid':True},solid_obstacle_audit=dict(
            audit_valid=audit_valid,coverage={'all_received_samples_recorded':True},
            contact_episodes=contacts,completion=observer_done,success=solid_success),
        mission_time_s=1.,end_to_end_cpu_cores_mean=1.,end_to_end_cpu_core_s=1.,total_ms_mean=1.)
    (folder/'summary.json').write_text(json.dumps({'results':[result]}))
    row=dict(mode=mode,attempt_count='1',retry_count='0',planner_ingress_payload_mib_s=1.,
        map_payload_bytes_total=1048576,filter_effective_full_open_transitions=0)
    with (folder/'raw.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    monkeypatch.setattr(pilot,'goal_audit',lambda *args:{'valid':True})
    flights,complete=pilot.inspect(folder,'map',1,[mode])
    assert complete and flights[0]['quality_valid'] is expected
    assert flights[0]['success'] is success and flights[0]['contacts']==contacts
    assert campaign.reference_failure(flights[0]) == (mode in ('full','adaptive') and (not success or contacts>0))


def fake_ready(root):
    root.mkdir()
    prefix=[]
    for item in campaign.plan()[:113]:
        flight=dict(map=item['map'],run=item['run'],mode=item['mode'],stage=item['stage'],
            repeat=item['repeat'],success=completion.key(item)!=completion.CORRECTED_SLOT,
            contacts=1 if completion.key(item)==completion.CORRECTED_SLOT else 0,
            quality_valid=True,solid_replay_valid=True,time_s=1.,cpu_cores=1.,cpu_core_s=1.,
            input_mib_s=1.,input_mib_run=1.,map_ms=1.,
            full_transitions=0 if item['mode']=='adaptive' else None)
        prefix.append(flight)
    campaign.json_write(root/'protocol.json',dict(planned=campaign.plan(),
        remaining=campaign.plan()[113:],prefix_flights=prefix,hashes={},quality_corrections=[],
        candidate='topology_liveness_trial_v6_20261006'),True)
    campaign.json_write(root/'status.json',dict(state='READY',forest_gate_passed=True),True)


def test_only_127_unexecuted_slots_launch_and_sector_failures_preserved(tmp_path,monkeypatch):
    root=tmp_path/'continued'; fake_ready(root)
    calls=install_fake_runtime(monkeypatch,
        lambda index,mode:(mode!='sector',1 if mode=='sector' else 0,True))
    assert completion.execute(root)==0
    assert len(calls)==len(set(calls))==127
    assert calls==[(r['map'],r['run'],r['mode']) for r in campaign.plan()[113:]]
    assert calls[0]==('forest_cluster_f01',99528,'adaptive')
    state=json.loads((root/'status.json').read_text())
    assert state['observed_flights']==240 and state['new_observed_flights']==127
    assert state['state']=='COMPLETE'
    with (root/'flights.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==240 and rows[112]['success']=='False' and rows[112]['contacts']=='1'
    with pytest.raises(ValueError,match='no implicit resume'):
        completion.execute(root)


@pytest.mark.parametrize('success,contacts,quality,reference',[
    (False,0,True,True),(True,1,True,True),(True,0,False,False)])
def test_first_adaptive_failure_stops_before_next_launch(tmp_path,monkeypatch,
        success,contacts,quality,reference):
    root=tmp_path/'failed'; fake_ready(root)
    calls=install_fake_runtime(monkeypatch,lambda index,mode:(success,contacts,quality))
    assert completion.execute(root)==1 and len(calls)==1
    state=json.loads((root/'status.json').read_text())
    assert state['observed_flights']==114 and state['new_observed_flights']==1
    assert state['state']=='STOPPED_FOR_DIAGNOSIS'
    assert ('failed_reference' in state) is reference
    assert not (root/'final_audit.json').exists()


def test_sector_actual_evidence_failure_still_stops(tmp_path,monkeypatch):
    root=tmp_path/'bad-sector'; fake_ready(root)
    calls=install_fake_runtime(monkeypatch,
        lambda index,mode:(mode!='sector',1 if mode=='sector' else 0,mode!='sector'))
    assert completion.execute(root)==1 and len(calls)==2 and calls[-1][2]=='sector'
    state=json.loads((root/'status.json').read_text())
    assert state['observed_flights']==115 and 'failed_reference' not in state


def test_reader_migration_accepts_only_exact_documented_fix(tmp_path,monkeypatch):
    archive=tmp_path/'old.py'; reader=tmp_path/'new.py'
    archive.write_text('before\n'+completion.BEFORE+'after\n')
    reader.write_text(archive.read_text().replace(completion.BEFORE,completion.AFTER,1))
    old_hash=campaign.sha256(archive)
    monkeypatch.setattr(completion,'ARCHIVE',archive)
    monkeypatch.setattr(completion,'READER',reader)
    monkeypatch.setattr(completion,'OLD_READER_SHA256',old_hash)
    hashes=completion.verify_reader_fix({'hashes':{str(reader):old_hash}})
    assert hashes[str(reader)]==campaign.sha256(reader)
    reader.write_text(reader.read_text()+'unrelated edit\n')
    with pytest.raises(ValueError,match='Unexpected inspector edit'):
        completion.verify_reader_fix({'hashes':{str(reader):old_hash}})
