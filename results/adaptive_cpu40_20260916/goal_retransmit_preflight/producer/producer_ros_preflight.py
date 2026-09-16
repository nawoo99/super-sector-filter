#!/usr/bin/env python3
"""No-flight actual waypoint producer test. Each invocation is one preserved attempt."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('legacy', 'identity'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--launch-style', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if os.environ.get('ROS_DOMAIN_ID') != '189':
        raise RuntimeError('This isolated fixture requires ROS_DOMAIN_ID=189')
    qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)
    rclpy.init()
    node = rclpy.create_node('goal_identity_preflight_observer')
    odom_pub = node.create_publisher(Odometry, '/lidar_slam/odom', qos)
    trigger_pub = node.create_publisher(PoseStamped, '/goal', qos)
    records, actions = [], []
    position = [0.0, 0.0, 1.5]
    def received(msg):
        p, q = msg.pose.position, msg.pose.orientation
        records.append(dict(receipt_ns=time.monotonic_ns(),
                            stamp_ns=msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec,
                            frame=msg.header.frame_id,
                            raw=[p.x, p.y, p.z, q.x, q.y, q.z, q.w]))
    subscription = node.create_subscription(PoseStamped, '/planning/click_goal', received, qos)
    def odom_tick():
        msg = Odometry()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = 'world'
        msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z = position
        msg.pose.pose.orientation.w = 1.0
        odom_pub.publish(msg)
    timer = node.create_timer(0.01, odom_tick)
    report = {'mode': args.mode, 'valid': False, 'records': records, 'actions': actions,
              'domain': 189, 'fake_odom_hz_requested': 100, 'no_fsm_gpu_or_flight': True}
    proc = None
    log = (args.output / 'mission.log').open('x')
    def until(predicate, seconds=8.0):
        deadline = time.monotonic() + seconds
        while not predicate():
            if proc is not None and proc.poll() is not None:
                raise AssertionError(f'mission exited early: {proc.returncode}')
            if time.monotonic() >= deadline:
                raise AssertionError(f'condition timed out after {seconds}s; records={len(records)}')
            rclpy.spin_once(node, timeout_sec=0.02)
    try:
        env = dict(os.environ, SUPER_GOAL_RETRANSMIT_IDENTITY='1' if args.mode == 'identity' else '0')
        cmd = ['/root/super_ws/install/mission_planner/lib/mission_planner/waypoint_mission',
               '--ros-args', '-p', 'config_name:=waypoint.yaml', '-p', 'data_name:=loop24.txt']
        if args.launch_style:
            cmd = ['ros2', 'launch', str(Path(__file__).with_name('producer_launchstyle.launch.py'))]
        report['launch_style_output_log'] = args.launch_style
        report['command'] = cmd
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        report['child_pid'] = proc.pid
        until(lambda: len(records) >= 3)
        initial = list(records[:3])
        assert all(r['raw'] == [24.0, 24.0, 1.5, 0.0, 0.0, 0.0, 1.0] and r['frame'] == 'world' for r in initial)
        until(lambda: trigger_pub.get_subscription_count() == 1)
        action_ns = time.monotonic_ns()
        actions.append({'event': 'rviz_retrigger', 'at_ns': action_ns})
        click = PoseStamped()
        click.header.stamp = node.get_clock().now().to_msg()
        trigger_pub.publish(click)
        until(lambda: len([r for r in records if r['receipt_ns'] > action_ns]) >= 3, 5.0)
        retrigger = [r for r in records if r['receipt_ns'] > action_ns][:3]
        assert all(r['raw'] == initial[0]['raw'] and r['frame'] == initial[0]['frame'] for r in retrigger)
        transition_ns = time.monotonic_ns()
        actions.append({'event': 'odom_reaches_first_waypoint', 'at_ns': transition_ns})
        position[:] = [24.0, 24.0, 1.5]
        until(lambda: len([r for r in records if r['raw'][0] == -24.0]) >= 3, 5.0)
        waypoint = [r for r in records if r['raw'][0] == -24.0][:3]
        assert all(r['raw'] == [-24.0, 24.0, 1.5, 0.0, 0.0, 0.0, 1.0] and r['frame'] == 'world' for r in waypoint)
        stages = {'initial': initial, 'retrigger_same_pose': retrigger, 'next_waypoint': waypoint}
        report['stages'] = stages
        intervals = {}
        for name, stage in stages.items():
            stamps = [r['stamp_ns'] for r in stage]
            assert all(s > 0 for s in stamps)
            assert len(set(stamps)) == (1 if args.mode == 'identity' else 3), (name, stamps)
            dt = [(b['receipt_ns'] - a['receipt_ns']) / 1e9 for a, b in zip(stage, stage[1:])]
            # Timer's > 1.0 s check yields nominal 1.00--1.01 s; allow modest scheduling jitter.
            assert all(0.90 <= x <= 1.15 for x in dt), (name, dt)
            intervals[name] = dt
        assert retrigger[0]['stamp_ns'] > initial[-1]['stamp_ns']
        assert waypoint[0]['stamp_ns'] > retrigger[-1]['stamp_ns']
        report['receipt_intervals_s'] = intervals
        report['valid'] = True
    except Exception as exc:
        report['error'] = repr(exc)
    finally:
        if proc is not None and proc.poll() is None:
            # Launch forwards SIGINT itself; signaling its whole group would
            # hit the node twice and may turn a graceful stop into exit -2.
            if args.launch_style:
                proc.send_signal(signal.SIGINT)
            else:
                os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=3)
        report['child_returncode'] = None if proc is None else proc.returncode
        report['exact_child_reaped'] = proc is None or proc.poll() is not None
        node.destroy_timer(timer)
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()
        log.close()
        contents = (args.output / 'mission.log').read_text()
        report['settings_marker_present'] = '[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1' in contents
        report['identity_markers'] = [line for line in contents.splitlines() if '[MISSION_GOAL_IDENTITY]' in line]
        if args.launch_style:
            died = re.findall(r'process has died.*exit code (-?\d+)', contents)
            report['launched_node_failure_exit_codes'] = [int(code) for code in died]
            if died:
                report['valid'] = False
                report['cleanup_error'] = 'launched node had a nonclean exit; preserve attempt'
        if report['settings_marker_present'] != (args.mode == 'identity'):
            report['valid'] = False
            report['marker_error'] = 'settings marker does not match requested mode'
        (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
