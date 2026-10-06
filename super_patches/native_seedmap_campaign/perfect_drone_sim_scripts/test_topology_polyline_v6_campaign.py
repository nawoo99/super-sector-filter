"""Controller orchestration fixtures only; no simulated safety certificates."""
import collections
import csv
import json
from pathlib import Path
import pytest
import topology_polyline_v6_campaign as campaign


def test_exact_predeclared_inventory():
    rows=campaign.plan()
    assert len(rows)==240
    assert collections.Counter(row['stage'] for row in rows)=={
        'forest_n10':30,'seven_map_n10':210}
    assert len({(row['stage'],row['map'],row['mode'],row['run']) for row in rows})==240
    counts=collections.Counter((row['stage'],row['map'],row['mode']) for row in rows)
    assert len(counts)==24 and set(counts.values())=={10}
    assert [row['mode'] for row in rows[:6]]==[
        'full','sector','adaptive','sector','adaptive','full']
    assert all(row['stage']=='forest_n10' for row in rows[:30])


def test_preserved_relative_artifact_paths_resolve_against_repo():
    assert campaign.artifact_folder('results/example')==campaign.REPO/'results/example'
    assert campaign.artifact_folder('/root/example')==Path('/root/example')


@pytest.mark.parametrize('mode,success,contacts,expected',[
    ('full',True,0,False),('full',False,0,True),('full',True,1,True),
    ('adaptive',False,0,True),('adaptive',True,1,True),
    ('sector',False,0,False),('sector',True,1,False)])
def test_reference_failure_policy(mode,success,contacts,expected):
    assert campaign.reference_failure(dict(mode=mode,success=success,contacts=contacts))==expected


def fake_protocol(root):
    root.mkdir()
    campaign.json_write(root/'protocol.json',dict(planned=campaign.plan(),hashes={},
        candidate='topology_liveness_trial_v6_20261006'),True)
    campaign.json_write(root/'status.json',dict(state='READY',forest_gate_passed=False),True)


def install_fake_runtime(monkeypatch,outcome):
    calls=[]
    class Process:
        pid=12345
        def __init__(self,args,**kwargs):
            _,_,folder,name,run,mode=args
            folder=Path(folder); folder.mkdir(parents=True)
            calls.append((name,int(run),mode))
            with (folder/'raw.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=['map','run','mode'])
                writer.writeheader(); writer.writerow(dict(map=name,run=run,mode=mode))
            campaign.json_write(folder/'plan.json',dict(asset_sha256={}),True)
            campaign.json_write(folder/'summary.json',dict(results=[dict(
                candidate='topology_liveness_trial_v6_20261006')]),True)
        def wait(self,**kwargs): return 0
        def poll(self): return 0
    def inspect(folder,name,run,modes):
        mode=modes[0]; success,contacts,quality=outcome(len(calls),mode)
        flight=dict(map=name,run=run,mode=mode,success=success,contacts=contacts,
            quality_valid=quality,time_s=1.,cpu_cores=1.,cpu_core_s=1.,input_mib_s=1.,
            input_mib_run=1.,map_ms=1.,full_transitions=0 if mode=='adaptive' else None)
        return [flight],True
    monkeypatch.setattr(campaign.subprocess,'Popen',Process)
    monkeypatch.setattr(campaign,'inspect',inspect)
    monkeypatch.setattr(campaign,'replay_solid',lambda *args:dict(valid=True))
    monkeypatch.setattr(campaign.signal,'signal',lambda *args:None)
    return calls


def test_stops_before_second_flight_on_actual_full_failure(tmp_path,monkeypatch):
    root=tmp_path/'failed'; fake_protocol(root)
    calls=install_fake_runtime(monkeypatch,lambda index,mode:(False,0,True))
    assert campaign.execute(root)==1
    assert len(calls)==1
    state=json.loads((root/'status.json').read_text())
    assert state['state']=='STOPPED_FOR_DIAGNOSIS'
    assert state['observed_flights']==1 and not state['forest_gate_passed']
    assert state['failed_reference']['success'] is False
    assert not (root/'forest_gate.json').exists()


def test_quality_failure_never_expands(tmp_path,monkeypatch):
    root=tmp_path/'invalid'; fake_protocol(root)
    calls=install_fake_runtime(monkeypatch,lambda index,mode:(True,0,False))
    assert campaign.execute(root)==1 and len(calls)==1
    assert not (root/'forest_gate.json').exists()


def test_sector_outcomes_retained_and_all_240_executed_once(tmp_path,monkeypatch):
    root=tmp_path/'complete'; fake_protocol(root)
    calls=install_fake_runtime(monkeypatch,
        lambda index,mode:(mode!='sector',1 if mode=='sector' else 0,True))
    assert campaign.execute(root)==0
    assert len(calls)==240 and len(set(calls))==240
    gate=json.loads((root/'forest_gate.json').read_text())
    assert gate['full_safe_complete']==gate['adaptive_safe_complete']==10
    assert gate['sector_safe_complete']==0
    state=json.loads((root/'status.json').read_text())
    assert state['state']=='COMPLETE' and state['forest_gate_passed']
    with (root/'flights.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==240 and sum(row['contacts']=='1' for row in rows)==80
    assert 'NA' in (root/'summary_by_map.md').read_text()
    with pytest.raises(ValueError,match='No implicit resume'):
        campaign.execute(root)
