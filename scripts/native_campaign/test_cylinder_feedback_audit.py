import csv
import json
import cylinder_feedback_audit as a


def evidence(tmp_path,monkeypatch,ack_gap=100,empty=1200,path_timeout=0,pending=False):
    (tmp_path/'solid').mkdir();(tmp_path/'artifacts').mkdir();(tmp_path/'ack').mkdir()
    stem='cyl2_test_run1_sector';path=tmp_path/'solid'/f'{stem}.json'
    path.write_text(json.dumps(dict(success=False,waypoint_epoch_s=[],max_position_step_m=.07)))
    path.with_suffix('.poses.csv').write_text('x,y,z\n3,-1,1.5\n')
    (tmp_path/'artifacts'/f'{stem}.attempt1.stack.log').write_text(
        'Empty or non-dense point cloud\n'*empty+'0.1 seconds time limit exceeded\n'*path_timeout)
    (tmp_path/'ack'/f'{stem}.json').write_text(json.dumps(dict(first_odom_epoch_s=0,last_odom_epoch_s=110,
          samples=[dict(receive_epoch_s=i) for i in range(10,111-int(ack_gap))])))
    (tmp_path/'artifacts'/f'{stem}.attempt1.filt_stats.json').write_text(json.dumps(dict(trajectory_guard_full_refresh_pending_ack=pending)))
    monkeypatch.setattr(a,'segments',lambda _:[dict(longest_pose_hold_s=90)])
    monkeypatch.setattr(a.confirmation,'safe',lambda _:False)
    monkeypatch.setattr(a.confirmation,'contact_free',lambda _:True)
    return dict(map='cyl2_test',run=1,mode='sector',success=False,solid_collision_episodes=0,solid_report_json=str(path))


def test_empty_log_plus_measured_ack_gap_localizes_starvation(tmp_path,monkeypatch):
    row=evidence(tmp_path,monkeypatch)
    result=a.audit_row(row)
    assert result['signature']=='EMPTY_INPUT_STALL' and result['ack_instrumented']
    assert result['diagnostic_not_causal_proof'] and result['position']==[3,-1,1.5]


def test_live_ack_path_timeout_is_not_empty_input(tmp_path,monkeypatch):
    row=evidence(tmp_path,monkeypatch,ack_gap=1,empty=0,path_timeout=300)
    assert a.audit_row(row)['signature']=='PATH_SEARCH_STALL'


def test_pending_exact_ack_distinguished_from_regular_ack(tmp_path,monkeypatch):
    row=evidence(tmp_path,monkeypatch,ack_gap=1,empty=0,pending=True)
    assert a.audit_row(row)['signature']=='PENDING_REFRESH_ACK'
