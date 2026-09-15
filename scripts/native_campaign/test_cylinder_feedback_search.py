import json
import pytest
import cylinder_feedback_search as f


def row(mode='full',run=1,success=True):
    return dict(map='cyl2_l0001',mode=mode,run=run,success=success)


def test_failed_candidate_queues_new_geometry_and_does_not_count_as_pass():
    state=dict(completed_candidates=[],passed=[],target=5,next_index=6,queue=[],current_recipe={})
    recipe=f.INITIAL[0]
    failure=dict(mode='adaptive',signature='PATH_SEARCH_STALL',position=[11,-19,1])
    f.enqueue_after_result(state,recipe,dict(decision='REFERENCE_FAILURE',rows=6,audits=[failure]))
    assert state['passed']==[] and len(state['queue'])==1
    assert state['queue'][0]==dict(name='cyl2_l0006',parent='cyl2_l0001',action='open_escape',position=[11,-19],escape_radius=4.)
    assert state['current_recipe'] is None


def test_empty_input_queues_static_observability_not_planner_change():
    failure=dict(mode='sector',signature='EMPTY_INPUT_STALL',position=[3,-1,1])
    recipe=f.audit.feedback_recipe('cyl2_l0006','cyl2_l0001',6,[failure])
    assert recipe['action']=='add_observability' and recipe['position']==[3,-1]


def test_ordinary_no_separation_queues_new_hardening():
    recipe=f.audit.feedback_recipe('cyl2_l0006','cyl2_l0001',6,[])
    assert recipe['action']=='harden' and recipe['iteration']==6


def test_empty_stall_is_not_meaningful_sector_advantage():
    rows=[row('sector',1),row('sector',2,False)]
    audits=[dict(mode='sector',signature='EMPTY_INPUT_STALL')]
    assert not f.audit.meaningful_sector_difference(rows,audits)
    audits[0]['signature']='PATH_SEARCH_STALL'
    assert f.audit.meaningful_sector_difference(rows,audits)
    assert not f.audit.meaningful_sector_difference([row('sector',2,False)],audits)


def test_qualified_diagnostic_is_followed_by_separate_standard_development_and_n20(monkeypatch):
    calls=[]
    def development(name,ack,*_):
        calls.append(('development',ack));return dict(decision='QUALIFIED')
    def confirm(*_):
        calls.append(('confirmation',20));return dict(decision='OBSERVED_N20_TARGET',observed_target=True)
    monkeypatch.setattr(f,'run_development',development);monkeypatch.setattr(f,'run_confirmation',confirm)
    result=f.evaluate(f.INITIAL[0],{},lambda **_:None)
    assert calls==[('development',True),('development',False),('confirmation',20)]
    assert result['observed_target']


@pytest.mark.parametrize('decision',['REFERENCE_FAILURE','INPUT_REDESIGN','NO_MEANINGFUL_SEPARATION'])
def test_failed_diagnostic_never_enters_confirmation(monkeypatch,decision):
    monkeypatch.setattr(f,'run_development',lambda *_:dict(decision=decision))
    monkeypatch.setattr(f,'run_confirmation',lambda *_:pytest.fail('Must redesign instead'))
    assert f.evaluate(f.INITIAL[0],{},lambda **_:None)['decision']==decision


def test_validation_preserves_invalid_and_duplicate_rows(monkeypatch):
    monkeypatch.setattr(f,'quality_valid',lambda _:True)
    monkeypatch.setattr(f.confirmation,'known_outcome',lambda _:True)
    f.validate([row()],'cyl2_l0001',range(1,4))
    with pytest.raises(RuntimeError):f.validate([row(),row()],'cyl2_l0001',range(1,4))
    monkeypatch.setattr(f,'quality_valid',lambda _:False)
    with pytest.raises(RuntimeError):f.validate([row()],'cyl2_l0001',range(1,4))


def test_main_continues_after_failure_until_five_n20_successes(tmp_path,monkeypatch):
    monkeypatch.setattr(f,'ROOT',tmp_path)
    monkeypatch.setattr(f,'INITIAL',[dict(f.INITIAL[0])])
    monkeypatch.setattr(f.search,'frozen_policy',lambda:{})
    monkeypatch.setattr(f,'verify',lambda _:None)
    monkeypatch.setattr(f,'ensure_candidate',lambda _:None)
    monkeypatch.setattr(f,'snapshot',lambda _:None)
    monkeypatch.setattr(f,'assert_no_other_flight',lambda:None)
    monkeypatch.setattr(f.solid.search.campaign,'install_campaign_signal_handlers',lambda:None)
    monkeypatch.setattr(f.solid.search.campaign,'cleanup_active_process_groups',lambda:None)
    calls=[]
    def evaluate(recipe,*_):
        calls.append(recipe)
        return dict(decision='REFERENCE_FAILURE' if len(calls)==1 else 'OBSERVED_N20_TARGET',
                    observed_target=len(calls)>1,rows=9 if len(calls)==1 else 60,audits=[])
    monkeypatch.setattr(f,'evaluate',evaluate)
    f.main()
    state=json.loads((tmp_path/'status.json').read_text())
    assert state['state']=='TARGET_OBSERVED' and len(state['passed'])==5
    assert len(calls)==6 and len({r['name'] for r in calls})==6
    assert state['completed_candidates'][0]['decision']=='REFERENCE_FAILURE'
    assert json.loads((tmp_path/'cyl2_l0001/result.json').read_text())['rows']==9
    # Restarting a completed controller must not fly or duplicate evidence.
    f.main();assert len(calls)==6


@pytest.mark.parametrize('state,allowed',[('DIAGNOSTIC_COMPLETE',True),('STOPPED_FOR_DIAGNOSIS',False)])
def test_handoff_only_after_normal_pilot_completion(tmp_path,monkeypatch,state,allowed):
    monkeypatch.setattr(f,'ROOT',tmp_path/'controller')
    monkeypatch.setattr(f,'DIAGNOSTICS',tmp_path/'diagnostics')
    monkeypatch.setattr(f,'assert_no_other_flight',lambda:None)
    status=f.DIAGNOSTICS/'cyl2_l0001/status.json';status.parent.mkdir(parents=True)
    status.write_text(json.dumps(dict(state=state)))
    if allowed:
        f.wait_for_pilot(999999999)
    else:
        with pytest.raises(RuntimeError):f.wait_for_pilot(999999999)
    result=json.loads((f.ROOT/'handoff_status.json').read_text())
    assert result['state']==('PILOT_COMPLETE_HANDOFF' if allowed else 'HANDOFF_STOPPED')
