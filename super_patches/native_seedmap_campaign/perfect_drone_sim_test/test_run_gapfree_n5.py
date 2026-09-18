"""Exact manual campaign coverage, preservation and contact accounting; no ROS."""
import csv
import os
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_gapfree_n5 as controller
sys.path.insert(0,str(controller.LEGACY))
from test_c24_normal_validation import valid_triplet


@pytest.fixture(scope='module',autouse=True)
def register():
    controller.support.register_maps()


def contact(map_name, episodes=0):
    root=controller.support.PACKAGE/'pcd/seed_maps'
    return dict(audit_valid=True,map=map_name,completion=True,samples=20,
        contact_episodes=episodes,robot_radius_m=.2,cylinder_count=410,
        observation='received_odometry_samples_only',swept_collision_check=False,
        cylinder_z_min_m=0,cylinder_z_max_m=3,
        invalid_samples=0,timestamp_nonmonotonic_count=0,receipt_nonmonotonic_count=0,
        cylinders_sha256=controller.base.sha(root/(map_name+'_cylinders.csv')),
        pcd_sha256=controller.base.sha(root/(map_name+'.pcd')))


def test_fresh_map_bound_static_and_exact75_primary(tmp_path):
    plan=controller.build_plan(tmp_path)
    static=[c for c in plan if c['phase']=='static']
    flights=[c for c in plan if 'path' in c]
    assert len(static)==40 and len(flights)==30
    assert sum(len(c['modes']) for c in flights if c['phase']=='test5')==75
    assert sum(len(c['modes']) for c in flights if c['phase']=='preflight')==15
    assert len({(c['map'],c['run'],m) for c in flights for m in c['modes']})==90
    for c in flights:
        cmd=c['command']
        assert '--time-reference-folder' not in cmd
        assert '--guarded-demand-replan' in cmd and '--mission-time-as-metric' in cmd
        assert '--async-certified-recovery' in cmd
        assert cmd[cmd.index('--side-executor-threads')+1]=='3'
        assert '--extended-demand-lease' not in cmd
        assert ('--profile-cpu' in cmd)==(c['phase']=='preflight')
        assert ('--small-pool-profile-reference' in cmd)==(c['phase']=='test5')
    for c in static:
        if c['name'].startswith('accept_'):
            assert c['command'][1].endswith('gapfree_campaign_support.py')
            assert c['command'][2:4]==['static','create']


@pytest.mark.parametrize('field,value',[
    ('audit_valid',False),('completion',False),('samples',0),('samples',True),
    ('robot_radius_m',.1),('contact_episodes',None),('contact_episodes',-1),
    ('contact_episodes',True),('cylinder_count',409),('cylinders_sha256','bad'),
    ('timestamp_nonmonotonic_count',1),('invalid_samples',1)])
def test_invalid_contacts_never_become_zero(field,value):
    name=controller.MAPS[0];doc=contact(name)
    assert controller.contact_valid(doc,name)
    doc[field]=value
    assert not controller.contact_valid(doc,name)


def make_triplet(tmp_path, phase='test5'):
    items=controller.build_plan(tmp_path/'campaign')
    item=next(c for c in items if c['phase']==phase)
    folder=Path(item['path'])
    valid_triplet(folder,item['map'],item['run'],phase=='preflight',controller.CANDIDATE,item['modes'],True)
    for mode in controller.MODES:
        path=controller.contact_file(folder,item['map'],item['run'],mode)
        path.parent.mkdir(parents=True,exist_ok=True)
        odom=path.with_name(path.name.removesuffix('.cylinder_audit.json')+'.odometry.csv')
        odom.write_text('sample,x,y,z\n1,0,0,1.5\n')
        doc=contact(item['map']);doc['odometry_sha256']=controller.base.sha(odom)
        controller.base.save(path,doc)
    return items,item,folder


@pytest.mark.parametrize('mode',['full','adaptive','sector'])
def test_analytic_contact_stops_full_adaptive_but_preserves_sector_outcome(tmp_path,mode):
    items,item,folder=make_triplet(tmp_path)
    assert controller.triplet_audit(item)['valid']
    p=controller.contact_file(folder,item['map'],item['run'],mode)
    doc=controller.base.read(p);doc['contact_episodes']=2
    controller.base.save(p,doc)
    audit=controller.triplet_audit(item)
    assert audit['valid']==(mode=='sector')
    assert audit['analytic_contacts'][mode]['contact_episodes']==2
    assert audit['outcome_failures'][mode]['analytic_contact_episodes']==2
    assert controller.contact_only_failure(audit)==(mode in ('full','adaptive'))
    assert controller.audit_accepted(audit,continue_after_contact=True)
    assert controller.audit_accepted(audit,continue_after_contact=False)==audit['valid']
    assert not controller.phase_gate(items,'test5')['valid']


def test_continue_policy_accepts_only_contact_and_preserves_strict_failure(tmp_path,monkeypatch):
    _,item,folder=make_triplet(tmp_path)
    path=controller.contact_file(folder,item['map'],item['run'],'adaptive')
    doc=controller.base.read(path);doc['contact_episodes']=1
    controller.base.save(path,doc)
    audit=controller.triplet_audit(item)
    controller.base.save(folder/'triplet_verification.json',audit)
    monkeypatch.setattr(controller,'MAPS',(item['map'],))
    monkeypatch.setitem(controller.COUNTS,'test5',1)
    strict=controller.phase_gate([item],'test5')
    continued=controller.phase_gate([item],'test5',continue_after_contact=True)
    assert not strict['valid'] and not strict['strict_valid']
    assert continued['valid'] and not continued['strict_valid']
    assert continued['records'][0]['contact_only_continued']

    audit['acceptance_checks']['adaptive:success']=False
    audit['valid']=False
    assert not controller.contact_only_failure(audit)
    assert not controller.audit_accepted(audit,continue_after_contact=True)


def test_partial_report_retains_unfinished_and_unknown_contacts(tmp_path):
    items,item,folder=make_triplet(tmp_path)
    path=controller.contact_file(folder,item['map'],item['run'],'sector')
    doc=contact(item['map'],2);doc['completion']=False
    controller.base.save(path,doc)
    result=controller.write_progress(tmp_path/'campaign')
    sector=next(r for r in result if r['map']==item['map'] and r['mode']=='sector')
    assert sector['attempts']==1 and sector['planned']==5
    assert sector['contact_unknown_runs']==1 and sector['contact_episodes'] is None
    untouched=next(r for r in result if r['map']==controller.MAPS[-1])
    assert untouched['attempts']==0 and untouched['completion_pct_observed'] is None
    assert untouched['cpu_cores_mean'] is None


def test_same_path_not_overwritten_and_report_does_not_launch(tmp_path):
    with pytest.raises(SystemExit):controller.main(['--output',str(tmp_path)])
    controller.base.save(tmp_path/'plan.json',dict(schema='gapfree-n5-manual-v1'))
    with mock.patch.object(controller,'reports') as report, mock.patch.object(controller.base,'execute') as execute:
        controller.main(['--report',str(tmp_path)])
    report.assert_called_once();execute.assert_not_called()


def test_report_protocol_ignores_only_unique_scratch():
    original = dict(map=controller.MAPS[0], cpu_profile=False, gapfree_manifest_sha256='frozen',
                    gapfree_scratch_directory='/tmp/gapfree_n5_a')
    another = dict(original, gapfree_scratch_directory='/tmp/gapfree_n5_b')
    assert controller.report_protocol_fingerprint(original)==controller.report_protocol_fingerprint(another)
    assert controller.report_protocol_fingerprint(original)!=controller.report_protocol_fingerprint(dict(another,cpu_profile=True))
    assert controller.report_protocol_fingerprint(original)!=controller.report_protocol_fingerprint(dict(another,gapfree_manifest_sha256='changed'))


@pytest.mark.parametrize('key,value',[('infrastructure_failure','True'),('retry_count','1'),('attempt_count','2')])
def test_bad_cost_accounting_remains_outcome_but_not_performance(tmp_path,key,value):
    _,item,folder=make_triplet(tmp_path)
    path=folder/'raw.csv'
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    for row in rows:row[key]=value
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    result=controller.write_progress(tmp_path/'campaign')
    observed=[r for r in result if r['map']==item['map']]
    assert all(r['attempts']==1 and r['performance_valid_runs']==0 and r['cpu_cores_mean'] is None for r in observed)


def test_reports_restore_legacy_fingerprint_on_error(tmp_path):
    make_triplet(tmp_path)
    original=controller.base.reports.protocol_fingerprint
    with mock.patch.object(controller.base.reports,'main',side_effect=ValueError('test report failure')):
        records=controller.reports(tmp_path/'campaign')
    assert records[-1]['state']=='REPORT_ERROR'
    assert controller.base.reports.protocol_fingerprint is original


def test_best_effort_main_retains_process_and_resource_failures(tmp_path,monkeypatch):
    root=tmp_path/'campaign'
    commands=[
        dict(name='preflight_x_r01',phase='preflight',map='x',run=1,repeat=1,
             modes=list(controller.MODES),path=str(root/'preflight/x/r01'),candidate='test',command=[]),
        dict(name='test5_x_r01',phase='test5',map='x',run=2,repeat=1,
             modes=list(controller.MODES),path=str(root/'test5/x/r01'),candidate='test',command=[]),
    ]
    monkeypatch.setattr(controller,'MAPS',('x',))
    monkeypatch.setattr(controller,'build_plan',lambda _root:commands)
    monkeypatch.setattr(controller,'freeze_sources',lambda _root:({},{}))
    monkeypatch.setattr(controller.support,'register_maps',lambda:None)
    monkeypatch.setattr(controller.base,'changed_inputs',lambda _frozen:[])
    monkeypatch.setattr(controller.base,'freeze_files',lambda *_args,**_kwargs:None)
    monkeypatch.setattr(controller.base.static,'map_context',lambda _map:{})
    monkeypatch.setattr(controller.base.static,'validate_manifest',lambda *_args:dict(valid=True))
    execute=mock.Mock(side_effect=[7,controller.base.MemoryRunawayError('synthetic resource abort')])
    monkeypatch.setattr(controller.base,'execute',execute)
    monkeypatch.setattr(controller,'triplet_audit',lambda _item:dict(valid=False,
        acceptance_checks={'full:success':False},outcomes={},outcome_failures={}))
    monkeypatch.setattr(controller,'phase_gate',lambda *_args,**_kwargs:dict(valid=False,strict_valid=False))
    monkeypatch.setattr(controller,'write_progress',lambda _root:[])
    monkeypatch.setattr(controller,'reports',lambda _root:[dict(phase='all',state='REPORT_ERROR')])
    for key in tuple(os.environ):
        if key.startswith('SUPER_'):monkeypatch.delenv(key)

    controller.main(['--output',str(root),'--continue-after-failure'])

    status=controller.base.read(root/'status.json')
    assert execute.call_count==2
    assert status['state']=='COMPLETE_WITH_RETAINED_FAILURES'
    assert status['continue_after_failure'] is True
    assert len(status['completed'])==2
    assert status['completed'][0]['returncode']==7
    assert status['completed'][1]['diagnostic_contaminated'] is True
