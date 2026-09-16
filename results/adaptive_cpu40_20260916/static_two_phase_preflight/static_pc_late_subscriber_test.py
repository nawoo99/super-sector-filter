#!/usr/bin/env python3
"""No-flight ROS integration test: simulator only, no FSM or command publisher.

Run after sourcing ROS/workspace setup; provide an unused ROS_DOMAIN_ID and a
working renderer display exactly as for an ordinary simulator smoke test.
Artifacts are written only to --out-dir. The child process group is cleaned up.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--config', default='seed1.yaml')
    parser.add_argument('--expected-points', type=int, default=241490)
    parser.add_argument('--poll-ms', type=int, choices=(1, 100), default=100,
                        help='1 is the untouched legacy control; 100 is the candidate')
    parser.add_argument('--two-phase', action='store_true',
                        help='retain legacy1ms startup, then100ms; requires --poll-ms1')
    parser.add_argument('--sequence', choices=('late', 'reader-first'), default='late',
                        help='reader-first preserves bootstrap reader readiness before later transitions')
    parser.add_argument('--expected-sha256',
                        help='require exact geometry payload SHA from a separate legacy control')
    args = parser.parse_args()
    if args.two_phase and args.poll_ms != 1:
        parser.error('--two-phase requires --poll-ms 1')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.out_dir / 'simulator.log'
    result_path = args.out_dir / 'result.json'
    if log_path.exists() or result_path.exists():
        raise SystemExit('refusing to overwrite previous integration-test artifacts')
    if 'ROS_DOMAIN_ID' not in os.environ:
        raise SystemExit('set a dedicated ROS_DOMAIN_ID before this no-flight test')

    env = dict(os.environ, SUPER_STATIC_PC_POLL_MS=str(args.poll_ms),
               SUPER_STATIC_PC_TWO_PHASE='1' if args.two_phase else '0')
    command = ['ros2', 'run', 'perfect_drone_sim', 'perfect_drone_node',
               '--ros-args', '-p', f'config_name:={args.config}']
    result = dict(valid=False, command=command, ros_domain_id=os.environ['ROS_DOMAIN_ID'],
                  no_fsm=True, no_commands_published=True, poll_ms=args.poll_ms,
                  two_phase=args.two_phase, sequence=args.sequence,
                  expected_sha256=args.expected_sha256, phases=[])
    process = None
    node = None
    subscriptions = []
    received = {'first': [], 'second': [], 'reconnected': []}
    started = time.monotonic()
    rclpy.init()

    def log_text():
        return log_path.read_text(errors='replace') if log_path.exists() else ''

    def wait_for(predicate, timeout_s, reason):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'simulator exited early: {process.returncode}')
            if predicate():
                return
            rclpy.spin_once(node, timeout_sec=.02)
        raise RuntimeError(f'timeout waiting for {reason}')

    def spin_for(duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            if process.poll() is not None:
                raise RuntimeError(f'simulator exited early: {process.returncode}')
            rclpy.spin_once(node, timeout_sec=.02)

    def callback(label):
        def accept(msg):
            cloud = dict(
                elapsed_s=time.monotonic() - started,
                points=int(msg.width) * int(msg.height), point_step=int(msg.point_step),
                bytes=len(msg.data), frame=msg.header.frame_id,
                sha256=hashlib.sha256(bytes(msg.data)).hexdigest(),
                stamp_ns=msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec)
            received[label].append(cloud)
            # Validate and retain phase-local evidence immediately. A later
            # known best-effort transition timeout must not erase reader-first
            # geometry evidence or silently validate malformed earlier data.
            layout = dict(width=int(msg.width), height=int(msg.height),
                          point_step=int(msg.point_step), row_step=int(msg.row_step),
                          is_bigendian=bool(msg.is_bigendian), is_dense=bool(msg.is_dense),
                          fields=[dict(name=f.name, offset=int(f.offset),
                                       datatype=int(f.datatype), count=int(f.count))
                                  for f in msg.fields])
            if (cloud['points'] != args.expected_points or cloud['frame'] != 'world'
                    or cloud['point_step'] <= 0
                    or cloud['bytes'] != cloud['points'] * cloud['point_step']
                    or cloud['bytes'] != layout['row_step'] * layout['height']):
                raise RuntimeError(f'incomplete or malformed geometry in phase {label}')
            if result.get('geometry_sha256', cloud['sha256']) != cloud['sha256']:
                raise RuntimeError(f'geometry payload changed in phase {label}')
            if result.get('geometry_layout', layout) != layout:
                raise RuntimeError(f'geometry layout changed in phase {label}')
            if args.expected_sha256 and cloud['sha256'] != args.expected_sha256:
                raise RuntimeError(f'geometry SHA differs from legacy control in phase {label}')
            result['geometry_sha256'] = cloud['sha256']
            result['geometry_layout'] = layout
            result['geometry_validated_clouds'] = result.get('geometry_validated_clouds', 0) + 1
            if label == 'first' and args.sequence == 'reader-first':
                result['reader_first_geometry_valid'] = True
                result['reader_first_geometry_sha256'] = cloud['sha256']
        return accept

    def subscribe(label):
        subscription = node.create_subscription(
            PointCloud2, '/global_pc', callback(label), qos_profile_sensor_data)
        subscriptions.append(subscription)
        return subscription

    try:
        node = rclpy.create_node('static_pc_late_subscriber_test')
        first = subscribe('first') if args.sequence == 'reader-first' else None
        with log_path.open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
            wait_for(lambda: f'[STATIC_PC_POLL_SETTINGS] poll_ms={args.poll_ms} ' in log_text(),
                     20, 'effective static polling settings')
            if args.sequence == 'reader-first':
                wait_for(lambda: bool(received['first']), 10, 'reader-first static geometry')
                result['phases'].append('reader_first_static_geometry')
                # Wait past the legacy bootstrap window before testing transitions.
                # Publication counts are load-dependent; no fixed count is asserted.
                spin_for(5.3)
                result['phases'].append('reader_first_waited_past_bootstrap_window')
            else:
                wait_for(lambda: (re.search(r'\[STATIC_PC_PUBLICATION\].*subscribers=0 bootstrap=1', log_text())
                                  if args.poll_ms == 100 else 'Publish global map size:' in log_text()),
                         10, 'bootstrap without listeners')
                spin_for(.3)
                result['phases'].append('bootstrap_without_subscribers')
            if args.two_phase:
                wait_for(lambda: '[STATIC_PC_TWO_PHASE] enabled=true phase=coarse ' in log_text(),
                         10, 'two-phase handoff after5.1s node time')
                if 'phase=legacy_fallback ' in log_text():
                    raise RuntimeError('unexpected clock fallback in stable-clock smoke')
                result['phases'].append('two_phase_coarse_handoff')

            if first is None:
                first = subscribe('first')
                wait_for(lambda: bool(received['first']), 5, 'first persistent late subscriber')
                result['phases'].append('late_subscriber_0_to_1')
            second = subscribe('second')
            wait_for(lambda: bool(received['second']), 5, 'second persistent subscriber')
            result['phases'].append('subscriber_1_to_2')
            # Let all messages from the 1→2 transition drain before measuring 2→1.
            spin_for(.3)
            baseline_first = len(received['first'])
            node.destroy_subscription(second)
            subscriptions.remove(second)
            wait_for(lambda: len(received['first']) > baseline_first, 5, 'count decrease 2 to 1')
            result['phases'].append('subscriber_2_to_1')
            node.destroy_subscription(first)
            subscriptions.remove(first)
            wait_for(lambda: node.count_subscribers('/global_pc') == 0, 5, 'zero subscribers')
            spin_for(.4)
            subscribe('reconnected')
            wait_for(lambda: bool(received['reconnected']), 5, 'reconnected subscriber')
            result['phases'].append('subscriber_1_to_0_to_1')
            spin_for(.3)

            clouds = [cloud for group in received.values() for cloud in group]
            if not clouds or any(cloud['points'] != args.expected_points or cloud['frame'] != 'world'
                                 or cloud['bytes'] != cloud['points'] * cloud['point_step']
                                 for cloud in clouds):
                raise RuntimeError('incomplete or malformed static geometry')
            geometry_hashes = {cloud['sha256'] for cloud in clouds}
            if len(geometry_hashes) != 1:
                raise RuntimeError('static geometry payload changed across subscriber transitions')
            geometry_sha256 = next(iter(geometry_hashes))
            if args.expected_sha256 and geometry_sha256 != args.expected_sha256:
                raise RuntimeError('geometry SHA differs from supplied legacy control')
            result['geometry_sha256'] = geometry_sha256
            publication_lines = [line for line in log_text().splitlines()
                                 if '[STATIC_PC_PUBLICATION]' in line]
            if args.poll_ms == 100 and sum('bootstrap=1' in line for line in publication_lines) != 1:
                raise RuntimeError('bootstrap not exactly once')
            cadence = [float(value) for value in re.findall(
                r'\[SENSOR_CADENCE_SUMMARY\].*? hz=([0-9.]+)', log_text())]
            if not cadence or not 9.0 <= cadence[-1] <= 11.0:
                raise RuntimeError(f'source cadence missing or outside smoke range: {cadence}')
            result.update(valid=True, clouds=received,
                          bootstrap_publications=1 if args.poll_ms == 100 else None,
                          publication_records=publication_lines, sensor_cadence_hz=cadence,
                          scope='Simulator-only static-map publication smoke; no flight/performance claim')
    except Exception as error:
        result['error'] = str(error)
        result['clouds'] = received
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
        if node is not None:
            for subscription in subscriptions:
                node.destroy_subscription(subscription)
            node.destroy_node()
        rclpy.shutdown()
        result['elapsed_s'] = time.monotonic() - started
        result['simulator_exit_code'] = process.returncode if process else None
        result_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
