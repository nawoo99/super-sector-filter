#!/usr/bin/env python3
"""No-flight ROS static-map transport test; standalone or composed without goals.

Run after sourcing ROS/workspace setup; provide an unused ROS_DOMAIN_ID and a
working renderer display exactly as for an ordinary simulator smoke test.
Artifacts are written only to --out-dir. The child process group is cleaned up.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from ament_index_python.packages import get_package_prefix
from rclpy.qos import (qos_profile_sensor_data, QoSProfile,
                      ReliabilityPolicy, DurabilityPolicy, HistoryPolicy)
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from mars_quadrotor_msgs.msg import PositionCommand


def audit_latched_once(text, received, expected_points, expected_sha256, observation_s):
    """Strict offline counter/payload audit; no ROS calls or delivery assumptions."""
    def records(marker):
        result = []
        for line in text.splitlines():
            if marker not in line:
                continue
            prefix, body = line.split(marker, 1)
            record = dict(re.findall(r'(\w+)=([^\s]+)', body))
            stamp = re.findall(r'\[(\d+)\.(\d{1,9})\]', prefix)
            if stamp:
                sec, fraction = stamp[-1]
                record['_log_stamp_ns'] = int(sec) * 10**9 + int(fraction.ljust(9, '0'))
            result.append(record)
        return result

    initial = records('[STATIC_PC_LATCHED_PUBLICATION]')
    summaries = records('[STATIC_PC_LATCHED_SUMMARY]')
    if len(initial) != 1 or len(summaries) < 2:
        raise ValueError('one initial latched publication and at least two cumulative summaries required')
    if observation_s is None or observation_s < 5.0:
        raise ValueError('latched publication must be observed for at least5s before shutdown')
    fields = ('publications', 'points', 'bytes', 'stamp_ns', 'timers_created', 'poll_callbacks')
    try:
        baseline = {key: int(initial[0][key]) for key in fields}
        snapshots = [{key: int(record[key]) for key in fields} for record in summaries]
    except (KeyError, ValueError) as error:
        raise ValueError('incomplete or noninteger latched counter evidence') from error
    if (initial[0].get('complete_geometry') != '1'
            or any(record.get('enabled') != '1' for record in summaries)
            or baseline['publications'] != 1 or baseline['timers_created'] != 0
            or baseline['poll_callbacks'] != 0 or baseline['stamp_ns'] <= 0
            or baseline['points'] != expected_points or baseline['bytes'] <= 0
            or any(snapshot != baseline for snapshot in snapshots)):
        raise ValueError('latched publication counters are invalid or changed during the observation')
    if '[STATIC_PC_PUBLICATION]' in text or 'Publish global map size:' in text:
        raise ValueError('legacy static publication occurred in latched-once mode')
    summary_stamps = [record.get('_log_stamp_ns') for record in summaries]
    if (any(stamp is None for stamp in summary_stamps)
            or any(b < a for a, b in zip(summary_stamps, summary_stamps[1:]))
            or summary_stamps[-1] - summary_stamps[0] < 5 * 10**9):
        raise ValueError('steady cumulative summary timestamps must span at least5s monotonically')
    for label in ('first', 'second', 'reconnected'):
        clouds = received.get(label, [])
        if len(clouds) != 1:
            raise ValueError(f'{label} must receive exactly one retained sample')
        cloud = clouds[0]
        if (cloud['sha256'] != expected_sha256 or cloud['points'] != expected_points
                or cloud['bytes'] != baseline['bytes'] or cloud['stamp_ns'] != baseline['stamp_ns']
                or cloud.get('frame') != 'world' or cloud.get('point_step', 0) <= 0
                or cloud['bytes'] != cloud['points'] * cloud['point_step']):
            raise ValueError(f'{label} differs from the single complete publication')
    return dict(valid=True, checks=dict(complete_geometry=True, exact_sha256=True,
                                       all_readers_same_stamp=True, publication_count_one=True,
                                       no_static_timers=True, no_static_poll_callbacks=True,
                                       cumulative_summaries_steady_at_least5s=True),
                initial=baseline, publication_count=len(initial), summary_count=len(summaries),
                observation_before_shutdown_s=observation_s,
                steady_summary_span_s=(summary_stamps[-1] - summary_stamps[0]) / 1e9,
                one_publication=True, no_static_timers=True, no_static_poll_callbacks=True,
                all_readers_same_stamp=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--config', default='seed1.yaml')
    parser.add_argument('--expected-points', type=int, default=241490)
    parser.add_argument('--poll-ms', type=int, choices=(1, 100), default=100,
                        help='1 is the untouched legacy control; 100 is the candidate')
    parser.add_argument('--two-phase', action='store_true',
                        help='retain legacy1ms startup, then100ms; requires --poll-ms1')
    parser.add_argument('--durable', action='store_true',
                        help='Plan A: global-PC reliable/transient-local only; legacy1ms schedule')
    parser.add_argument('--latched-once', action='store_true',
                        help='C18: publish complete durable geometry once, without static polling')
    parser.add_argument('--composition', choices=('standalone', 'full', 'adaptive'),
                        default='standalone', help='actual binary; composed modes have FSM but no mission/goals')
    parser.add_argument('--reader-qos', choices=('legacy', 'durable'), default='legacy',
                        help='legacy is current best-effort/volatile; durable is reliable/transient-local')
    parser.add_argument('--sequence', choices=('late', 'reader-first'), default='late',
                        help='reader-first preserves bootstrap reader readiness before later transitions')
    parser.add_argument('--expected-sha256',
                        help='require exact geometry payload SHA from a separate legacy control')
    parser.add_argument('--capture-first-payload', action='store_true',
                        help='Diagnostic only: retain exact first received bytes before strict validation; never relax acceptance')
    args = parser.parse_args()
    if args.two_phase and args.poll_ms != 1:
        parser.error('--two-phase requires --poll-ms 1')
    if args.durable and (args.poll_ms != 1 or args.two_phase):
        parser.error('--durable requires --poll-ms 1 and --two-phase disabled')
    if args.durable and not args.expected_sha256:
        parser.error('--durable requires --expected-sha256 from a successful actual legacy geometry sample')
    if args.latched_once and (not args.durable or args.reader_qos != 'durable'):
        parser.error('--latched-once requires --durable and --reader-qos durable; old readers are not claimed compatible')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.out_dir / 'simulator.log'
    result_path = args.out_dir / 'result.json'
    if log_path.exists() or result_path.exists():
        raise SystemExit('refusing to overwrite previous integration-test artifacts')
    if os.environ.get('ROS_DOMAIN_ID') != '190':
        raise SystemExit('set the dedicated ROS_DOMAIN_ID=190 before this no-flight test')

    env = dict(os.environ, SUPER_STATIC_PC_POLL_MS=str(args.poll_ms),
               SUPER_STATIC_PC_TWO_PHASE='1' if args.two_phase else '0',
               SUPER_STATIC_PC_DURABLE='1' if args.durable else '0',
               SUPER_STATIC_PC_LATCHED_ONCE='1' if args.latched_once else '0',
               SUPER_STATIC_PC_CACHED_EXECUTOR='0')
    env.pop('SUPER_SENSOR_FULL_ACQUISITION', None)
    executables = dict(standalone='perfect_drone_node', full='perfect_drone_full_node',
                       adaptive='perfect_drone_adaptive_node')
    binary = Path(get_package_prefix('perfect_drone_sim')) / 'lib/perfect_drone_sim' / executables[args.composition]
    command = [str(binary), '--ros-args']
    if args.composition == 'standalone':
        command += ['-p', f'config_name:={args.config}']
    else:
        env.update(SUPER_SIDE_EXECUTOR_THREADS='2', SUPER_STATIC_PC_DEDICATED_EXECUTOR='1',
                   SUPER_HEADLESS_PARAMETER_SERVICES='1')
        profile = ('static_seedmaps_guard_viability_tight_v7.yaml' if args.composition == 'full'
                   else 'static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml')
        command += ['-p', f'drone_config:={args.config}', '-p', f'super_config:={profile}']
        if args.composition == 'full':
            env['SUPER_SENSOR_FULL_ACQUISITION'] = '1'
        else:
            # Effective source45/event-only arguments from native_campaign.py;
            # there is no rate limiter, raw-risk worker or extra near-field crop.
            frontend = ['adaptive', '45', '--stats-json', str(args.out_dir / 'frontend_stats.json'),
                        '--event-recovery', '--full-refresh-generation-ack', '--reliable-output',
                        '--replan-fail-streak-open', '3', '--max-publish-hz', '0',
                        '--full-open-extra-max-points', '0', '--trajectory-guard-hold-s', '0',
                        '--map-commit-refresh-age-s', '0', '--map-commit-pre-stale-full-age-s', '0',
                        '--sensor-acquisition', '--near-field-radius-m', '0',
                        '--near-field-speed-gain-s', '0', '--near-field-max-radius-m', '0']
            command += ['-p', 'filter_arguments:=' + ';'.join(frontend)]
    result = dict(valid=False, command=command, ros_domain_id=os.environ['ROS_DOMAIN_ID'],
                  no_fsm=args.composition == 'standalone', composition=args.composition,
                  fixture_publishes_no_goals_or_commands=True, poll_ms=args.poll_ms,
                  two_phase=args.two_phase, durable=args.durable,
                  latched_once=args.latched_once,
                  reader_qos=args.reader_qos, sequence=args.sequence,
                  expected_sha256=args.expected_sha256, phases=[])
    process = None
    node = None
    subscriptions = []
    received = {'first': [], 'second': [], 'reconnected': []}
    motion = dict(command_messages=0, odom_messages=0, initial_position=None,
                  max_position_delta_m=0.0, first_odom_receipt_ns=None, last_odom_receipt_ns=None)
    started = time.monotonic()
    latched_publication_observed_at = None
    shutdown_requested_at = None
    total_deadline = started + 90.0
    reader_qos = (qos_profile_sensor_data if args.reader_qos == 'legacy' else
                  QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL))
    rclpy.init()

    def log_text():
        return log_path.read_text(errors='replace') if log_path.exists() else ''

    def wait_for(predicate, timeout_s, reason):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if time.monotonic() >= total_deadline:
                raise RuntimeError('hard90s fixture deadline exceeded')
            if process.poll() is not None:
                raise RuntimeError(f'simulator exited early: {process.returncode}')
            if predicate():
                return
            rclpy.spin_once(node, timeout_sec=.02)
        raise RuntimeError(f'timeout waiting for {reason}')

    def spin_for(duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            if time.monotonic() >= total_deadline:
                raise RuntimeError('hard90s fixture deadline exceeded')
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
            if args.capture_first_payload and label == 'first' and len(received[label]) == 1:
                payload_path = args.out_dir / 'first_payload.bin'
                with payload_path.open('xb') as payload:
                    payload.write(bytes(msg.data))
                result['diagnostic_first_payload'] = dict(path=str(payload_path.resolve()),
                                                          sha256=cloud['sha256'])
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
            if args.latched_once:
                prior_stamp = result.get('latched_geometry_stamp_ns', cloud['stamp_ns'])
                if cloud['stamp_ns'] <= 0 or prior_stamp != cloud['stamp_ns']:
                    raise RuntimeError(f'latched timestamp changed in phase {label}')
                result['latched_geometry_stamp_ns'] = cloud['stamp_ns']
            result['geometry_sha256'] = cloud['sha256']
            result['geometry_layout'] = layout
            result['geometry_validated_clouds'] = result.get('geometry_validated_clouds', 0) + 1
            if label == 'first' and args.sequence == 'reader-first':
                result['reader_first_geometry_valid'] = True
                result['reader_first_geometry_sha256'] = cloud['sha256']
        return accept

    def subscribe(label):
        subscription = node.create_subscription(
            PointCloud2, '/global_pc', callback(label), reader_qos)
        subscriptions.append(subscription)
        return subscription

    def observe_command(_msg):
        motion['command_messages'] += 1
        raise RuntimeError('unexpected position command in a no-goal transport fixture')

    def observe_odom(msg):
        p = msg.pose.pose.position
        position = [p.x, p.y, p.z]
        if not all(math.isfinite(value) for value in position):
            raise RuntimeError('nonfinite odometry in no-flight transport fixture')
        if motion['initial_position'] is None:
            motion['initial_position'] = position
            motion['first_odom_receipt_ns'] = time.monotonic_ns()
        motion['odom_messages'] += 1
        motion['last_odom_receipt_ns'] = time.monotonic_ns()
        delta = math.dist(position, motion['initial_position'])
        motion['max_position_delta_m'] = max(motion['max_position_delta_m'], delta)
        if delta > 1e-6:
            raise RuntimeError('simulator moved in a no-goal transport fixture')

    try:
        node = rclpy.create_node('static_pc_late_subscriber_test')
        subscriptions.append(node.create_subscription(
            Odometry, '/lidar_slam/odom', observe_odom, qos_profile_sensor_data))
        subscriptions.append(node.create_subscription(
            PositionCommand, '/planning/pos_cmd', observe_command, qos_profile_sensor_data))
        first = subscribe('first') if args.sequence == 'reader-first' else None
        with log_path.open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
            effective_poll_ms = 0 if args.latched_once else args.poll_ms
            wait_for(lambda: f'[STATIC_PC_POLL_SETTINGS] poll_ms={effective_poll_ms} ' in log_text(),
                     20, 'effective static polling settings')
            result['effective_poll_ms'] = effective_poll_ms
            if args.latched_once:
                wait_for(lambda: '[STATIC_PC_LATCHED_PUBLICATION]' in log_text(),
                         10, 'complete one-shot geometry publication')
                latched_publication_observed_at = time.monotonic()
                result['phases'].append('one_shot_geometry_published')
            durable_marker = f'[STATIC_PC_DURABLE_SETTINGS] enabled={int(args.durable)} '
            wait_for(lambda: durable_marker in log_text(), 5, 'effective static durability settings')
            actual_marker = re.search(
                re.escape(durable_marker) + r'actual_qos=1 reliability=(\w+) durability=(\w+) '
                r'history=(\w+) depth=(\d+)', log_text())
            if actual_marker is None:
                raise RuntimeError('publisher get_actual_qos marker missing')
            actual = dict(zip(('reliability', 'durability', 'history', 'depth'), actual_marker.groups()))
            actual['depth'] = int(actual['depth'])
            result['publisher_actual_qos'] = actual
            expected_actual = dict(reliability='reliable' if args.durable else 'best_effort',
                                   durability='transient_local' if args.durable else 'volatile',
                                   history='keep_last', depth=1 if args.durable else 100)
            if actual != expected_actual:
                raise RuntimeError(f'publisher actual QoS differs from expected: {actual}')
            wait_for(lambda: bool(node.get_publishers_info_by_topic('/global_pc')),
                     5, 'global-PC publisher discovery')
            publishers = node.get_publishers_info_by_topic('/global_pc')
            if len(publishers) != 1:
                raise RuntimeError(f'isolated domain has {len(publishers)} global-PC publishers')
            offered = publishers[0].qos_profile
            result['offered_qos'] = dict(
                reliability=int(offered.reliability), durability=int(offered.durability),
                history=int(offered.history), depth=int(offered.depth))
            expected_reliability = (ReliabilityPolicy.RELIABLE if args.durable else
                                    ReliabilityPolicy.BEST_EFFORT)
            expected_durability = (DurabilityPolicy.TRANSIENT_LOCAL if args.durable else
                                  DurabilityPolicy.VOLATILE)
            if offered.reliability != expected_reliability or offered.durability != expected_durability:
                raise RuntimeError(f'actual publisher QoS differs from requested profile: {result["offered_qos"]}')
            # FastDDS graph discovery may omit history/depth even though the
            # publisher's own get_actual_qos() above reports them correctly.
            # Unknown graph fields are disclosed, never treated as verified.
            history_known = offered.history not in (HistoryPolicy.UNKNOWN, HistoryPolicy.SYSTEM_DEFAULT)
            depth_known = offered.depth > 0
            result['graph_qos_verified'] = dict(reliability=True, durability=True,
                                                history=history_known, depth=depth_known)
            if ((history_known and offered.history != HistoryPolicy.KEEP_LAST) or
                    (depth_known and offered.depth != expected_actual['depth'])):
                raise RuntimeError(f'known graph history/depth contradict publisher actual QoS: {result["offered_qos"]}')
            if args.sequence == 'reader-first':
                wait_for(lambda: bool(received['first']), 10, 'reader-first static geometry')
                result['phases'].append('reader_first_static_geometry')
                # Wait past the legacy bootstrap window before testing transitions.
                # Publication counts are load-dependent; no fixed count is asserted.
                spin_for(5.3)
                result['phases'].append('reader_first_steady_no_republish' if args.latched_once
                                        else 'reader_first_waited_past_bootstrap_window')
            else:
                if not args.latched_once:
                    wait_for(lambda: (re.search(r'\[STATIC_PC_PUBLICATION\].*subscribers=0 bootstrap=1', log_text())
                                      if args.poll_ms == 100 else 'Publish global map size:' in log_text()),
                             10, 'bootstrap without listeners')
                spin_for(.3)
                result['phases'].append('one_shot_without_subscribers' if args.latched_once
                                        else 'bootstrap_without_subscribers')
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
            if args.latched_once:
                # Removing a reader does not create new immutable map content.
                # Latched contract preserves the surviving reader's exact map,
                # unlike legacy count-edge publication semantics.
                spin_for(.5)
                if len(received['first']) != baseline_first:
                    raise RuntimeError('unexpected repeated delivery to stable reader in one-shot mode')
                result['phases'].append('subscriber_2_to_1_retained_without_republish')
            else:
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
            if args.latched_once:
                spin_for(max(0., 11.0 - (time.monotonic() - latched_publication_observed_at)))
                wait_for(lambda: '[SENSOR_CADENCE_SUMMARY]' in log_text(),
                         6, 'at least50 source frames without static polling')
            if motion['odom_messages'] < 2 or motion['command_messages'] != 0:
                raise RuntimeError('missing stationary odometry or unexpected command in no-flight fixture')

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
            if not cadence or not 9.5 <= cadence[-1] <= 10.5:
                raise RuntimeError(f'source cadence missing or outside smoke range: {cadence}')
            result.update(valid=True, clouds=received,
                          bootstrap_publications=1 if args.poll_ms == 100 else None,
                          publication_records=publication_lines, sensor_cadence_hz=cadence,
                          scope='No-goal static-map transport smoke; no flight/performance claim')
    except Exception as error:
        result['error'] = str(error)
        result['clouds'] = received
    finally:
        if process is not None and process.poll() is None:
            # Direct simulator child, not ros2-run/launch: one SIGINT only.
            shutdown_requested_at = time.monotonic()
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                result['forced_cleanup'] = True
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
        result['no_flight_observation'] = motion
        result['simulator_exit_code'] = process.returncode if process else None
        result['exact_child_reaped'] = process is not None and process.poll() is not None
        if result['simulator_exit_code'] != 0 or result.get('forced_cleanup'):
            result['valid'] = False
            result['cleanup_error'] = 'direct child did not exit cleanly after one SIGINT'
        if args.latched_once:
            observation_s = (shutdown_requested_at - latched_publication_observed_at
                             if shutdown_requested_at is not None and latched_publication_observed_at is not None
                             else None)
            try:
                result['latched_once_audit'] = audit_latched_once(
                    log_text(), received, args.expected_points, args.expected_sha256, observation_s)
                result['valid'] = (result['valid'] is True
                                   and result['latched_once_audit'].get('valid') is True)
            except (KeyError, ValueError) as error:
                result['valid'] = False
                result['latched_once_audit'] = dict(valid=False, error=str(error),
                                                    observation_before_shutdown_s=observation_s)
        result_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
