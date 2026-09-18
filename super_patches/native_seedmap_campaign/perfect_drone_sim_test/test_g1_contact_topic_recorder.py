"""Fake-message/offline recorder tests; never initialize ROS or start flights."""
from array import array
import importlib.util
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts/g1_contact_topic_recorder.py"
spec = importlib.util.spec_from_file_location("g1_topic_recorder", PATH)
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class Message:
    def __init__(self, **values):
        self.__dict__.update(values)
    def get_fields_and_field_types(self):
        return {key: "fake" for key in self.__dict__}


def polynomial(stamp=1, heartbeat=False):
    return Message(header=Message(stamp=Message(sec=10, nanosec=stamp), frame_id="world"),
        trajectory_id=134, trajectory_generation=2**32+134, type=1 if heartbeat else 7,
        piece_num_pos=0 if heartbeat else 2, order_pos=3,
        coef_pos_x=array('d', [] if heartbeat else range(8)),
        coef_pos_y=array('d', [] if heartbeat else range(10,18)),
        coef_pos_z=array('d', [] if heartbeat else range(20,28)),
        time_pos=[] if heartbeat else [1., 2.], start_wt_pos=12.25,
        piece_num_yaw=0 if heartbeat else 1, order_yaw=1,
        coef_yaw=[] if heartbeat else [.1,.2], time_yaw=[] if heartbeat else [3.], start_wt_yaw=12.25)


def test_full_polynomial_retained_and_heartbeat_does_not_replace_it(tmp_path):
    out=tmp_path/'recording'; r=recorder.Recorder(out)
    assert r.submit('/planning_cmd/poly_traj',polynomial())
    assert r.submit('/planning_cmd/poly_traj',polynomial(2,True))
    summary=r.close()
    rows=[json.loads(line) for line in (out/'polynomial_trajectories.jsonl').read_text().splitlines()]
    assert len(rows)==2 and rows[0]['message']['coef_pos_z']==list(range(20,28))
    assert rows[0]['message']['time_pos']==[1.,2.]
    assert rows[0]['message']['trajectory_generation']==2**32+134
    assert rows[0]['polynomial']['kind']=='full_polynomial'
    assert rows[1]['polynomial']['kind']=='heartbeat_only'
    assert summary['last_full_polynomial']['sequence']==1
    assert summary['local_retention_complete'] and summary['written_jsonl_bytes']>0


def test_pose_orientation_acceleration_and_yaw_fields_are_retained(tmp_path):
    r=recorder.Recorder(tmp_path/'recording')
    header=Message(stamp=Message(sec=11,nanosec=7),frame_id='world')
    odom=Message(header=header,pose=Message(pose=Message(position=Message(x=1.,y=2.,z=3.),
        orientation=Message(x=.1,y=.2,z=.3,w=.9))),twist=Message(twist=Message(linear=Message(x=4.,y=5.,z=6.))))
    command=Message(header=header,position=Message(x=1.,y=2.,z=3.),acceleration=Message(x=7.,y=8.,z=9.),
                    yaw=-1.5,yaw_dot=.04,trajectory_id=134,trajectory_flag=1)
    r.submit('/lidar_slam/odom',odom);r.submit('/planning/pos_cmd',command);r.close()
    a=json.loads((r.output/'odometry.jsonl').read_text());b=json.loads((r.output/'position_commands.jsonl').read_text())
    assert a['message']['pose']['pose']['orientation']['w']==.9
    assert b['message']['acceleration']['z']==9. and b['message']['yaw']==-1.5
    assert a['header_ns']==11000000007 and b['message']['trajectory_id']==134


def test_nonfinite_and_bad_coefficients_are_evidence_not_silent_zero(tmp_path):
    r=recorder.Recorder(tmp_path/'recording');msg=polynomial();msg.coef_pos_x=[float('nan')]
    r.submit('/planning_cmd/poly_traj',msg);summary=r.close()
    doc=json.loads((r.output/'polynomial_trajectories.jsonl').read_text())
    assert doc['message']['coef_pos_x']==['NaN']
    assert doc['nonfinite_field_paths']==['message.coef_pos_x[0]']
    assert not doc['polynomial']['coefficient_lengths_valid']
    assert summary['topics']['/planning_cmd/poly_traj']['invalid_polynomial_lengths']==1


def test_repeated_backward_stamps_and_reported_middleware_loss(tmp_path):
    r=recorder.Recorder(tmp_path/'recording')
    for stamp in [3,3,1]:r.submit('/planning_cmd/poly_traj',polynomial(stamp,True))
    r.middleware_lost('/planning_cmd/poly_traj',2);summary=r.close()
    count=summary['topics']['/planning_cmd/poly_traj']
    assert count['repeated_header_stamps']==1 and count['backward_header_stamps']==1
    assert count['middleware_reported_lost_messages']==2


def test_byte_budget_drops_are_counted_and_keep_files_bounded(tmp_path):
    r=recorder.Recorder(tmp_path/'recording',max_bytes=10)
    r.submit('/planning_cmd/poly_traj',polynomial());summary=r.close()
    assert summary['written_jsonl_bytes']==0
    assert summary['topics']['/planning_cmd/poly_traj']['dropped_byte_budget']==1
    assert not summary['local_retention_complete']


def test_queue_saturation_is_nonblocking_and_counted(tmp_path,monkeypatch):
    release=threading.Event();original=recorder.Recorder._write
    def held_writer(self):release.wait(3);original(self)
    monkeypatch.setattr(recorder.Recorder,'_write',held_writer)
    r=recorder.Recorder(tmp_path/'recording',queue_capacity=1)
    assert r.submit('/planning_cmd/poly_traj',polynomial())
    assert not r.submit('/planning_cmd/poly_traj',polynomial(2))
    release.set();summary=r.close()
    assert summary['topics']['/planning_cmd/poly_traj']['dropped_queue_full']==1
    assert not summary['local_retention_complete']


def test_existing_output_refused(tmp_path):
    with pytest.raises(FileExistsError):recorder.Recorder(tmp_path)
