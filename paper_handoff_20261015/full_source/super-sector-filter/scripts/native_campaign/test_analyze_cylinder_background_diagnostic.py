import csv
import json

import analyze_cylinder_background_diagnostic as analysis


def fixture(tmp_path,complete):
    for folder in ('ack','solid','artifacts'): (tmp_path/folder).mkdir()
    prefix='cyl2_test_run1_sector'
    ack=dict(first_odom_epoch_s=0,last_odom_epoch_s=21.3,
             post_warmup=dict(samples=101,max_gap_s=1.3,hz=101/11.3),
             samples=[dict(receive_epoch_s=10+i*.1) for i in range(101)])
    (tmp_path/'ack'/f'{prefix}.json').write_text(json.dumps(ack))
    (tmp_path/'solid'/f'{prefix}.json').write_text(json.dumps(dict(success=complete,waypoint_epoch_s=[20.2] if complete else [])))
    (tmp_path/'artifacts'/f'{prefix}.attempt1.stack.log').write_text('MAP_STALE\n')
    row=dict(map='cyl2_test',run='1',mode='sector',success=str(complete),
             mission_time_s='20',solid_collision_episodes='0',solid_min_clearance_m='.3',
             solid_report_json='original.json')
    with (tmp_path/'diagnostic_raw.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)


def test_original_metrics_preserved_when_adding_goal_boundary(tmp_path,monkeypatch):
    fixture(tmp_path,True)
    for name in ('quality_valid','known_outcome','safe'): monkeypatch.setattr(analysis,name,lambda _:True)
    result=analysis.analyze(tmp_path)
    row=result['rows'][0]
    assert row['original_observer_window']['max_gap_s']==1.3
    assert .19 < row['goal_bounded_window']['max_gap_s'] < .21
    assert row['flight_window_end_kind']=='solid_fifth_waypoint'
    assert not result['all_nine_unique_rows'] and result['not_standard_n20']
    assert result['analysis_boundary_amendment'].startswith('Post-hoc')


def test_failed_trial_not_given_fictitious_completion_boundary(tmp_path,monkeypatch):
    fixture(tmp_path,False)
    for name in ('quality_valid','known_outcome','safe'): monkeypatch.setattr(analysis,name,lambda _:True)
    result=analysis.analyze(tmp_path)
    assert result['rows'][0]['flight_window_end_kind']=='last_odom_includes_cleanup'
    assert result['counts']['sector']['complete']==0
