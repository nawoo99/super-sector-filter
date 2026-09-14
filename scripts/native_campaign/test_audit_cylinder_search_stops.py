from audit_cylinder_search_stops import audit_log


def record(t,fields):
    return f"[ERROR] [{t:.9f}] [fsm]: [TRAJ_GUARD_BRAKE_REJECTED] {fields}; no brake command published"


def test_retries_cluster_but_separate_events_remain():
    text="\n".join(record(t,"speed0=6.815") for t in (1789397757.2,1789397757.21,1789397760.0))
    got=audit_log(text)
    assert got["rejection_log_records"]==3
    assert len(got["moving_rejection_episodes"])==2
    assert got["moving_rejection_episodes"][0]["moving_rejection_log_records"]==2


def test_stationary_brake_is_not_moving_failure():
    got=audit_log(record(1789397757.3,"speed0=0 motion_pose_speed=0 motion_twist_speed=0 motion_dt=0.11 motion_source=position_difference"))
    assert got["moving_rejection_episodes"]==[]
    assert got["frozen_pose_moving_twist_records"]==[]


def test_pose_twist_disagreement_requires_frozen_position():
    got=audit_log(record(1789397757.3,"speed0=0 motion_pose_speed=0 motion_twist_speed=6.815 motion_dt=0.11s motion_source=position_difference"))
    assert len(got["frozen_pose_moving_twist_records"])==1
    moving=audit_log(record(1789397757.3,"speed0=6 motion_pose_speed=6 motion_twist_speed=6.815 motion_dt=0.11 motion_source=position_difference"))
    assert moving["frozen_pose_moving_twist_records"]==[]
