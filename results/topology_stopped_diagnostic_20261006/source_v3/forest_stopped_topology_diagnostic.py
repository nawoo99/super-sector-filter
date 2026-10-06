#!/usr/bin/env python3
"""Opt-in closed-loop branch test; NOT a canonical mission or historical replay."""
import argparse
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

import psutil
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from scenario7_geometry import SampledSolidAudit, load_geometry, sha256


SOURCE = Path('/root/super_ws/src/SUPER')
INSTALL = Path('/root/super_ws/forest_liveness_trial_v3_20261006/install')
START = (8.6753022, 18.9734347, 2.685578)
GOAL = (24.025, 22.025, 1.5)
RESET_GOAL = (*START[:2], 1.5)
PROFILE = 'static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml'
SIM_CONFIG = 'forest_stopped_diagnostic_20261006.yaml'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variant', choices=('control', 'available', 'exhausted'), required=True)
    args = parser.parse_args()
    binary = INSTALL / 'perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_full_node'
    if b'[TEST_FOREST_TOPOLOGY_STATE]' not in binary.read_bytes():
        raise RuntimeError('Selected binary lacks the opt-in state reconstruction hook')
    lock = open('/tmp/super_sector_filter_native.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for process in psutil.process_iter(['cmdline']):
        command = process.info['cmdline'] or []
        if command and Path(command[0]).name in ('fsm_node', 'perfect_drone_full_node',
                'perfect_drone_adaptive_node', 'perfect_drone_frontend_node', 'perfect_drone_node'):
            raise RuntimeError('A flight process is already running')
    args.output.mkdir(parents=True, exist_ok=False)
    pcd = SOURCE / 'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/forest_cluster_f01.pcd'
    geometry = load_geometry(pcd)
    audit = SampledSolidAudit(geometry)
    env = dict(os.environ)
    # Use the same execution/certificate options as the V2 canonical-derived pilot.
    settings = {
        'SUPER_CPU_PROFILE': '1', 'SUPER_ASYNC_CERTIFIED_RECOVERY': '1',
        'SUPER_ASYNC_GENERATE_TRAJ': '1', 'SUPER_STOPPED_DEPARTURE_V4': '1',
        'SUPER_STOPPED_HOLD_V5': '1', 'SUPER_GOAL_CHANGE_FULL_REFRESH_V6': '0',
        'SUPER_SECTOR_ACTIVE_YAW_SCAN': '0', 'SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT': '0',
        'SUPER_SKIP_BACKUP_DIAGNOSTIC_REPLAY': '1',
        'SUPER_SKIP_UNOBSERVED_PATH_PUBLICATION': '1',
        'SUPER_FAST_OCCUPIED_BOX_SCAN': '1', 'SUPER_SNAPSHOT_LINE_QUERY': '1',
        'SUPER_SNAPSHOT_NEIGHBOR_CACHE': '1', 'SUPER_SIDE_EXECUTOR_THREADS': '3',
        'SUPER_MONITOR_INTERVALS': '1', 'SUPER_GUARDED_DEMAND_REPLAN': '1',
        'SUPER_GOAL_RETRANSMIT_IDENTITY': '1', 'SUPER_HEADLESS_PARAMETER_SERVICES': '1',
        'SUPER_FRONTEND_DEDICATED_EXECUTOR': '0', 'SUPER_STATIC_PC_DEDICATED_EXECUTOR': '1',
        'SUPER_STATIC_PC_CACHED_EXECUTOR': '0', 'SUPER_OPTIMIZER_PHASE_MEMORY_TRACE': '0',
        'SUPER_OPT_CLEARANCE_GATE_FIRST': '1', 'ROS_DOMAIN_ID': '161',
    }
    for key in tuple(env):
        if key.startswith('SUPER_TEST_'):
            env.pop(key)
    env.update(settings)
    if args.variant != 'control':
        env['SUPER_TEST_FOREST_TOPOLOGY_STATE'] = args.variant
    os.environ['ROS_DOMAIN_ID'] = env['ROS_DOMAIN_ID']
    inputs = (binary, Path(__file__).resolve(),
              SOURCE / 'super_planner/src/super_core/super_planner.cpp',
              SOURCE / 'super_planner/include/super_core/super_planner.h',
              SOURCE / 'super_planner/config' / PROFILE,
              SOURCE / 'mars_uav_sim/perfect_drone_sim/config' / SIM_CONFIG,
              geometry.geometry_path, pcd)
    manifest = dict(schema='forest-stopped-topology-diagnostic-v1', variant=args.variant,
        source_run=97036, historical_map_replay=False, fresh_lidar_map=True,
        canonical_mission=False, flight_attempts=1, automatic_retries=0,
        start=list(START), goal=list(GOAL), reset_goal=list(RESET_GOAL),
        test_deadline_s=180, terminal_stall_window_s=60, terminal_stall_radius_m=0.02,
        settings=settings, opt_in=args.variant if args.variant != 'control' else None,
        hashes={str(path): sha256(path) for path in inputs}, geometry=geometry.metadata())
    (args.output / 'protocol.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rclpy.init()
    node = rclpy.create_node('forest_stopped_diagnostic_observer')
    publisher = node.create_publisher(PoseStamped, '/planning/click_goal', 1)
    rows = []
    started = time.monotonic()
    phase = 'warmup'
    goal_sent = reset_sent = None
    hold_started = None
    hold_origin = None
    hold_ok = False
    last = None
    cpu_rows = []
    samples_file = (args.output / 'odometry.csv').open('w', newline='')
    writer = csv.writer(samples_file, lineterminator='\n')
    writer.writerow(['sample', 'header_ns', 'receipt_ns', 'elapsed_s', 'phase',
                     'x', 'y', 'z', 'vx', 'vy', 'vz', 'clearance_m'])

    def odometry(message):
        nonlocal last
        p, v = message.pose.pose.position, message.twist.twist.linear
        position, velocity = (p.x, p.y, p.z), (v.x, v.y, v.z)
        now_ns = time.monotonic_ns()
        elapsed = now_ns / 1e9 - started
        stamp = message.header.stamp.sec * 10**9 + message.header.stamp.nanosec
        clearance = audit.observe(position, velocity, stamp, now_ns, elapsed)
        writer.writerow([audit.samples, stamp, now_ns, elapsed, phase, *position, *velocity, clearance])
        rows.append((elapsed, position, velocity, phase))
        last = (position, velocity, now_ns / 1e9)

    subscription = node.create_subscription(Odometry, '/lidar_slam/odom', odometry,
                                             qos_profile_sensor_data)
    def send_goal(goal):
        message = PoseStamped()
        message.header.frame_id = 'world'
        message.header.stamp = node.get_clock().now().to_msg()
        message.pose.position.x, message.pose.position.y, message.pose.position.z = goal
        message.pose.orientation.w = 1.0
        publisher.publish(message)
        print(json.dumps(dict(event='goal_published', goal=goal, elapsed=time.monotonic()-started)), flush=True)

    log_path = args.output / 'stack.log'
    log_stream = log_path.open('w')
    process = subprocess.Popen([str(binary), '--ros-args', '-p', 'drone_config:='+SIM_CONFIG,
                                '-p', 'super_config:='+PROFILE],
                               env=env, stdout=log_stream, stderr=subprocess.STDOUT,
                               start_new_session=True)
    status = 'UNFINISHED'
    last_resource = last_print = last_stack_read = 0
    stack = ''
    origin_time = None
    stall_origin = None
    try:
        while True:
            rclpy.spin_once(node, timeout_sec=0.01)
            now = time.monotonic()
            elapsed = now - started
            if process.poll() is not None:
                status = 'PROCESS_EXIT'
                break
            if now-last_resource >= 1:
                measured = psutil.Process(process.pid)
                usage = measured.cpu_times()
                cpu_rows.append(dict(elapsed_s=elapsed, cpu_s=usage.user+usage.system,
                    rss_bytes=measured.memory_info().rss, host_cpu_pct=psutil.cpu_percent(),
                    available_bytes=psutil.virtual_memory().available, swap_bytes=psutil.swap_memory().used))
                last_resource = now
            if elapsed-last_print >= 5:
                print(json.dumps(dict(event='progress', phase=phase, elapsed_s=round(elapsed, 2),
                                      position=last[0] if last else None)), flush=True)
                last_print = elapsed
            if elapsed >= 180:
                status = 'DIAGNOSTIC_DEADLINE'
                break
            if last and now-last[2] > 2:
                status = 'ODOMETRY_LOST'
                break
            if now-last_stack_read >= 0.25:
                stack = log_path.read_text(errors='replace')
                last_stack_read = now
            if phase == 'warmup' and elapsed >= 4 and last and publisher.get_subscription_count():
                if math.dist(last[0], START) > 0.15:
                    status = 'WRONG_INITIAL_POSE'
                    break
                send_goal(GOAL)
                goal_sent = now
                phase = 'primary_goal'
                origin_time, stall_origin = now, last[0]
            if phase == 'primary_goal' and last:
                if math.dist(last[0], GOAL) <= 1.5:
                    status = 'GOAL_REACHED'
                    break
                if math.dist(last[0], stall_origin) > 0.02:
                    origin_time, stall_origin = now, last[0]
                if args.variant == 'exhausted' and '[TRAJ_GUARD_RECOVERY_EXHAUSTED]' in stack:
                    hold_started, hold_origin = now, last[0]
                    phase = 'exhausted_hold'
                elif now-origin_time >= 60:
                    status = 'PERSISTENT_NO_PROGRESS'
                    break
            elif phase == 'exhausted_hold' and last:
                if math.dist(last[0], hold_origin) > 0.02 or math.sqrt(sum(x*x for x in last[1])) > 0.05:
                    status = 'UNSTABLE_EXHAUSTED_HOLD'
                    break
                if now-hold_started >= 3:
                    hold_ok = True
                    send_goal(RESET_GOAL)
                    reset_sent = now
                    phase = 'distinct_goal_reset'
                    origin_time, stall_origin = now, last[0]
            elif phase == 'distinct_goal_reset' and last:
                if math.dist(last[0], RESET_GOAL) <= 0.2:
                    status = 'HOLD_THEN_RESET_GOAL_REACHED'
                    break
                if math.dist(last[0], stall_origin) > 0.02:
                    origin_time, stall_origin = now, last[0]
                if now-origin_time >= 60:
                    status = 'RESET_GOAL_NO_PROGRESS'
                    break
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
        samples_file.close()
        log_stream.close()
        node.destroy_node()
        rclpy.shutdown()
        stack = log_path.read_text(errors='replace')
        markers = {name: stack.count('['+name+']') for name in (
            'TEST_FOREST_TOPOLOGY_STATE', 'TRAJ_GUARD_ZONE_DISCONNECT',
            'TRAJ_GUARD_RECOVERY_EXHAUSTED', 'TRAJ_GUARD_LOCAL_ESCAPE',
            'TRAJ_GUARD_VERTICAL_RECOVERY', 'TRAJ_GUARD_REROUTE_RESEED')}
        (args.output / 'resources.json').write_text(json.dumps(cpu_rows, indent=2)+'\n')
        solid = audit.summary()
        no_contact = solid['audit_valid'] and solid['contact_episodes'] == 0
        checks = dict(no_contact=no_contact, odometry_received=bool(rows),
            speed_limit_valid=bool(rows) and max(math.sqrt(sum(x*x for x in row[2])) for row in rows) <= 7.01,
            input_hashes_unchanged=all(sha256(path) == digest for path, digest in manifest['hashes'].items()))
        if args.variant == 'control':
            checks.update(goal_reached=status == 'GOAL_REACHED', hook_inert=markers['TEST_FOREST_TOPOLOGY_STATE'] == 0)
        elif args.variant == 'available':
            checks.update(goal_reached=status == 'GOAL_REACHED', actual_zone_disconnect=markers['TRAJ_GUARD_ZONE_DISCONNECT'] >= 1,
                state_injected_once=markers['TEST_FOREST_TOPOLOGY_STATE'] == 1,
                certified_local_escape=markers['TRAJ_GUARD_LOCAL_ESCAPE'] >= 1)
        else:
            checks.update(hold_then_goal_reset=status == 'HOLD_THEN_RESET_GOAL_REACHED', stable_hold=hold_ok,
                state_injected_once=markers['TEST_FOREST_TOPOLOGY_STATE'] == 1,
                actual_zone_disconnect=markers['TRAJ_GUARD_ZONE_DISCONNECT'] >= 1,
                exhaustion_once=markers['TRAJ_GUARD_RECOVERY_EXHAUSTED'] == 1)
        report = dict(schema='forest-stopped-topology-diagnostic-result-v1', variant=args.variant,
            status=status, passed=all(checks.values()), checks=checks, markers=markers,
            elapsed_s=time.monotonic()-started, goal_sent_monotonic=goal_sent,
            reset_sent_monotonic=reset_sent, last_pose=last[0] if last else None,
            solid_audit=solid, cpu_measurement_scope='diagnostic composed simulator+planner; not a canonical performance cohort',
            hashes={name: sha256(args.output / name) for name in ('protocol.json', 'odometry.csv', 'stack.log', 'resources.json')})
        (args.output / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(dict(event='finished', variant=args.variant, status=status,
                              passed=report['passed'], markers=markers, contacts=solid['contact_episodes'])), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
