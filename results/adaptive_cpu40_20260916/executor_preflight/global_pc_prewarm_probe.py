#!/usr/bin/env python3
"""Artifact-only DDS readiness control: reader exists before simulator startup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import get_rmw_implementation_identifier
from sensor_msgs.msg import PointCloud2

parser = argparse.ArgumentParser()
parser.add_argument('--out-dir', type=Path, required=True)
parser.add_argument('--poll-ms', choices=['1', '100'], default='1')
parser.add_argument('--pulse-count', action='store_true',
                    help='test-only extra reader toggles force four warm count-change publications')
args = parser.parse_args()
args.out_dir.mkdir(parents=True, exist_ok=False)
assert 'ROS_DOMAIN_ID' in os.environ
rclpy.init()
node = rclpy.create_node('global_pc_prewarm_probe')
received = []
started = time.monotonic()


def receive(message):
    received.append(dict(elapsed_s=time.monotonic() - started,
                         points=message.width * message.height,
                         bytes=len(message.data),
                         sha256=hashlib.sha256(bytes(message.data)).hexdigest()))


subscription = node.create_subscription(PointCloud2, '/global_pc', receive, qos_profile_sensor_data)
result = dict(rmw=get_rmw_implementation_identifier(), domain=os.environ['ROS_DOMAIN_ID'],
              poll_ms=args.poll_ms, reader_created_before_simulator=True)
process = None
extra_subscription = None
pulses = 0
try:
    with (args.out_dir / 'simulator.log').open('w') as output:
        process = subprocess.Popen(
            ['ros2', 'run', 'perfect_drone_sim', 'perfect_drone_node',
             '--ros-args', '-p', 'config_name:=seed1.yaml'],
            env=dict(os.environ, SUPER_STATIC_PC_POLL_MS=args.poll_ms),
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        while time.monotonic() - started < 9 and process.poll() is None:
            if args.pulse_count and pulses < 4 and time.monotonic() - started >= 2 + .2 * pulses:
                if extra_subscription is None:
                    extra_subscription = node.create_subscription(
                        PointCloud2, '/global_pc', lambda message: None, qos_profile_sensor_data)
                else:
                    node.destroy_subscription(extra_subscription)
                    extra_subscription = None
                pulses += 1
            rclpy.spin_once(node, timeout_sec=.02)
        result.update(received=received, publisher_count=node.count_publishers('/global_pc'),
                      test_only_subscriber_count_pulses=pulses,
                      valid=bool(received) and all(row['points'] == 241490 for row in received))
finally:
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
    result['exit_code'] = process.returncode if process else None
    if extra_subscription is not None:
        node.destroy_subscription(extra_subscription)
    node.destroy_subscription(subscription)
    node.destroy_node()
    rclpy.shutdown()
    (args.out_dir / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
