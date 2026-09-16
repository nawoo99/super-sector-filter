#!/usr/bin/env python3
"""No-flight actual RViz late/reconnect test of the opted-in one-shot static map.

The compiled probe uses the installed RViz PointCloud2 display, not a substitute
Python cloud subscriber. Run only after coordinated build/ROS process release.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from ament_index_python.packages import get_package_prefix, get_package_share_directory


def records(text, marker):
    result = []
    for line in text.splitlines():
        if marker not in line:
            continue
        prefix, body = line.split(marker, 1)
        record = dict(re.findall(r'(\w+)=([^\s]+)', body))
        stamp = re.findall(r'\[(\d+)\.(\d{1,9})\]', prefix)
        if stamp:
            seconds, fraction = stamp[-1]
            record['_log_stamp_ns'] = int(seconds) * 10**9 + int(fraction.ljust(9, '0'))
        result.append(record)
    return result


def summary_span_s(text):
    summaries = records(text, '[STATIC_PC_LATCHED_SUMMARY]')
    stamps = [record.get('_log_stamp_ns') for record in summaries]
    if len(stamps) < 2 or any(stamp is None for stamp in stamps):
        return 0.0
    if any(b < a for a, b in zip(stamps, stamps[1:])):
        raise RuntimeError('nonmonotonic publication summary timestamps')
    return (stamps[-1] - stamps[0]) / 1e9


def stop_child(process, timeout_s=8):
    if process is None or process.poll() is not None:
        return dict(forced=False, exit_code=None if process is None else process.returncode)
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=timeout_s)
        return dict(forced=False, exit_code=process.returncode)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
        return dict(forced=True, exit_code=process.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--probe-binary', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-points', type=int, default=241490)
    parser.add_argument('--config', default='seed1.yaml')
    parser.add_argument('--view', choices=('watch_sector', 'top_down', 'fpv', 'benchmark'),
                        default='watch_sector')
    args = parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID') != '191':
        raise SystemExit('set isolated ROS_DOMAIN_ID=191 for this no-flight RViz test')
    if not re.fullmatch(r'[a-f0-9]{64}', args.expected_sha256):
        parser.error('expected SHA must come from a successful legacy geometry sample')
    if args.out_dir.exists():
        raise SystemExit('refusing to overwrite an existing attempt directory')
    if not args.probe_binary.is_file():
        parser.error('probe binary does not exist')
    args.out_dir.mkdir(parents=True)
    simulator_log = args.out_dir / 'simulator.log'
    result = dict(valid=False, schema='static-latched-rviz-v1', reader_restarts=0,
                  probes=[], publisher_no_republish=False,
                  no_fsm=True, no_goals_or_commands_published=True,
                  actual_rviz=True, ros_domain_id=191, phases=[],
                  expected_sha256=args.expected_sha256, expected_points=args.expected_points)
    env = dict(os.environ, SUPER_STATIC_PC_DURABLE='1', SUPER_STATIC_PC_LATCHED_ONCE='1',
               SUPER_STATIC_PC_POLL_MS='1', SUPER_STATIC_PC_TWO_PHASE='0',
               SUPER_STATIC_PC_CACHED_EXECUTOR='0')
    binary = Path(get_package_prefix('perfect_drone_sim')) / 'lib/perfect_drone_sim/perfect_drone_node'
    viewer_config = Path(get_package_share_directory('perfect_drone_sim')) / 'rviz2' / (
        args.view + '_durable.rviz')
    command = [str(binary), '--ros-args', '-p', 'config_name:=' + args.config]
    result['simulator_command'] = command
    simulator = viewer = None
    node = None
    started = time.monotonic()
    deadline = started + 100
    published_at = None
    rclpy.init()

    def log_text():
        return simulator_log.read_text(errors='replace') if simulator_log.exists() else ''

    def wait_for(predicate, seconds, reason):
        end = min(deadline, time.monotonic() + seconds)
        while time.monotonic() < end:
            if simulator is not None and simulator.poll() is not None:
                raise RuntimeError('simulator exited early')
            if predicate():
                return
            rclpy.spin_once(node, timeout_sec=.05)
        raise RuntimeError('timeout waiting for ' + reason)

    try:
        node = rclpy.create_node('static_map_rviz_orchestrator')
        # This node only inspects graph discovery. It creates no map subscription.
        with simulator_log.open('x') as log:
            simulator = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                         env=env, start_new_session=True)
            wait_for(lambda: len(records(log_text(), '[STATIC_PC_LATCHED_PUBLICATION]')) == 1,
                     25, 'single retained map publication')
            published_at = time.monotonic()
            wait_for(lambda: node.count_publishers('/global_pc') == 1, 5, 'one map publisher')
            if node.count_subscribers('/global_pc') != 0:
                raise RuntimeError('isolated test unexpectedly has an existing static-map reader')
            result['phases'].append('one_shot_before_any_viewer')
            for phase in ('late', 'reconnected'):
                phase_result = args.out_dir / (phase + '.json')
                phase_png = args.out_dir / (phase + '.png')
                viewer_command = [str(args.probe_binary), str(viewer_config),
                                  str(args.expected_points), args.expected_sha256,
                                  str(phase_png), str(phase_result)]
                with (args.out_dir / (phase + '.log')).open('x') as viewer_log:
                    viewer = subprocess.Popen(viewer_command, stdout=viewer_log,
                                              stderr=subprocess.STDOUT, env=env,
                                              start_new_session=True)
                    wait_for(lambda: viewer.poll() is not None, 35, phase + ' actual RViz display')
                if viewer.returncode != 0 or not phase_result.is_file():
                    raise RuntimeError(phase + ' RViz probe failed: exit=' + str(viewer.returncode))
                evidence = json.loads(phase_result.read_text())
                if evidence.get('valid') is not True:
                    raise RuntimeError(phase + ' RViz evidence invalid')
                result['phases'].append(phase + '_actual_rviz_full_sha_display')
                result[phase] = evidence
                result['probes'].append(dict(evidence, phase=phase))
                if phase == 'reconnected':
                    result['reader_restarts'] += 1
                wait_for(lambda: node.count_subscribers('/global_pc') == 0, 8,
                         phase + ' viewer subscriber removal')
                result['phases'].append(phase + '_viewer_disconnected')
            wait_for(lambda: time.monotonic() - published_at >= 5, 6,
                     'at least five seconds without app republish')
            wait_for(lambda: summary_span_s(log_text()) >= 5, 20,
                     'cumulative publisher summaries spanning at least five seconds')
        result['observation_before_shutdown_s'] = time.monotonic() - published_at
    except Exception as error:
        result['error'] = str(error)
    finally:
        result['viewer_cleanup'] = stop_child(viewer)
        result['simulator_cleanup'] = stop_child(simulator)
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
        try:
            if result.get('error'):
                raise RuntimeError(result['error'])
            text = log_text()
            initial = records(text, '[STATIC_PC_LATCHED_PUBLICATION]')
            final = records(text, '[STATIC_PC_LATCHED_SUMMARY]')
            keys = ('publications', 'points', 'bytes', 'stamp_ns', 'timers_created', 'poll_callbacks')
            if len(initial) != 1 or len(final) < 2 or summary_span_s(text) < 5:
                raise RuntimeError('missing single initial/final publication evidence')
            baseline = {key: int(initial[0][key]) for key in keys}
            if (baseline['publications'] != 1 or baseline['timers_created'] != 0
                    or baseline['poll_callbacks'] != 0 or baseline['points'] != args.expected_points
                    or baseline['stamp_ns'] <= 0 or initial[0].get('complete_geometry') != '1'
                    or any(record.get('enabled') != '1' for record in final)
                    or any({key: int(record[key]) for key in keys} != baseline for record in final)):
                raise RuntimeError('one-shot counters changed or geometry incomplete')
            if '[STATIC_PC_PUBLICATION]' in text or 'Publish global map size:' in text:
                raise RuntimeError('legacy polling publication also occurred')
            for phase in ('late', 'reconnected'):
                actual = result[phase]['geometry']
                if (actual['sha256'] != args.expected_sha256
                        or actual['points'] != baseline['points'] or actual['bytes'] != baseline['bytes']
                        or int(actual['stamp_ns']) != baseline['stamp_ns']):
                    raise RuntimeError(phase + ' RViz sample differs from the sole publication')
            if result['viewer_cleanup']['forced'] or result['simulator_cleanup']['forced']:
                raise RuntimeError('forced process cleanup invalidates clean lifecycle claim')
            if (result['viewer_cleanup']['exit_code'] != 0 or
                    result['simulator_cleanup']['exit_code'] != 0):
                raise RuntimeError('nonzero child exit invalidates clean lifecycle claim')
            result.update(valid=True, publication_counters=baseline,
                          latched_summary=final[-1], publisher_no_republish=True,
                          steady_summary_span_s=summary_span_s(text),
                          scope='Actual RViz static-map late/reconnect smoke; no flight/CPU claim')
        except Exception as error:
            result['valid'] = False
            result['error'] = str(error)
        (args.out_dir / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(valid=result['valid'], out_dir=str(args.out_dir),
                          error=result.get('error'))))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
