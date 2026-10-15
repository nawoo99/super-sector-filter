#!/usr/bin/env python3
"""Small ROS graph equivalence check for the Python and C++ sector filters."""

import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2 as pc2


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_FILTER = os.path.join(SCRIPT_DIR, "native_sector.py")


class Harness(Node):
    def __init__(self):
        super().__init__("native_sector_equivalence_harness")
        self.cloud_pub = self.create_publisher(
            PointCloud2, "/equivalence/cloud", qos_profile_sensor_data
        )
        self.odom_pub = self.create_publisher(
            Odometry, "/lidar_slam/odom", qos_profile_sensor_data
        )
        self.outputs = {"python": None, "cpp": None, "witness": None}
        self.create_subscription(
            PointCloud2,
            "/equivalence/python",
            lambda msg: self.outputs.__setitem__("python", msg),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PointCloud2,
            "/equivalence/cpp",
            lambda msg: self.outputs.__setitem__("cpp", msg),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PointCloud2,
            "/equivalence/witness",
            lambda msg: self.outputs.__setitem__("witness", msg),
            qos_profile_sensor_data,
        )


def points_of(message):
    points = pc2.read_points_numpy(
        message, field_names=("x", "y", "z", "intensity"), skip_nans=True
    ).reshape(-1, 4)
    return sorted(tuple(round(float(value), 5) for value in row) for row in points)


def terminate(process):
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=2.0)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    with tempfile.TemporaryDirectory(prefix="native-sector-equivalence-") as tempdir:
        common = [
            "sector", "60", "--input-topic", "/equivalence/cloud",
            "--no-replan-guard", "--near-field-radius-m", "1.5",
        ]
        python_stats = os.path.join(tempdir, "python.json")
        cpp_stats = os.path.join(tempdir, "cpp.json")
        processes = [
            subprocess.Popen(
                [sys.executable, PYTHON_FILTER, *common,
                 "--output-topic", "/equivalence/python",
                 "--stats-json", python_stats],
                preexec_fn=os.setsid,
            ),
            subprocess.Popen(
                ["ros2", "run", "mission_planner", "native_sector_cpp", *common,
                 "--output-topic", "/equivalence/cpp",
                 "--guard-witness-topic", "/equivalence/witness",
                 "--guard-witness-radius-m", "3.1",
                 "--stats-json", cpp_stats],
                preexec_fn=os.setsid,
            ),
        ]
        try:
            rclpy.init()
            harness = Harness()
            discovery_deadline = time.monotonic() + 8.0
            while (
                harness.cloud_pub.get_subscription_count() < 2
                and time.monotonic() < discovery_deadline
            ):
                rclpy.spin_once(harness, timeout_sec=0.1)
            if harness.cloud_pub.get_subscription_count() < 2:
                raise RuntimeError("filters did not discover the synthetic cloud publisher")
            for _ in range(3):
                odom = Odometry()
                odom.pose.pose.orientation.w = 1.0
                harness.odom_pub.publish(odom)
                rclpy.spin_once(harness, timeout_sec=0.1)

            fields = [
                PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
                PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
                PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
                PointField(name="intensity", offset=12, datatype=PointField.FLOAT32, count=1),
            ]
            points = [
                (5.0, 0.0, 0.0, 1.0),       # forward sector
                (4.0, 8.0, 0.0, 2.0),       # outside +60 deg
                (4.0, -8.0, 0.0, 3.0),      # outside -60 deg
                (-1.0, 0.0, 0.0, 4.0),      # rear, retained by near halo
                (-3.0, 0.0, 0.0, 5.0),      # rear, rejected
                (2.0, math.sqrt(3.0), 0.0, 6.0),
                (float("nan"), 0.0, 0.0, 7.0),
            ]
            cloud = pc2.create_cloud(odom.header, fields, points)
            cloud.is_dense = False
            harness.cloud_pub.publish(cloud)
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                rclpy.spin_once(harness, timeout_sec=0.1)
                if all(harness.outputs.values()):
                    break
            if not all(harness.outputs.values()):
                raise RuntimeError("did not receive both filters and guard witness")
            python_points = points_of(harness.outputs["python"])
            cpp_points = points_of(harness.outputs["cpp"])
            if python_points != cpp_points:
                raise AssertionError(
                    f"filtered points differ:\npython={python_points}\ncpp={cpp_points}"
                )
            if not harness.outputs["python"].is_dense or not harness.outputs["cpp"].is_dense:
                raise AssertionError("filtered outputs must both be marked dense")
            witness_points = points_of(harness.outputs["witness"])
            expected_witness = sorted(
                tuple(round(float(value), 5) for value in point)
                for point in (points[3], points[4], points[5])
            )
            if witness_points != expected_witness:
                raise AssertionError(
                    f"bounded witness differs:\n"
                    f"expected={expected_witness}\nactual={witness_points}"
                )

            time.sleep(1.2)
            python_snapshot = json.load(open(python_stats))
            cpp_snapshot = json.load(open(cpp_stats))
            for key in ("frames", "published_frames", "kept_points", "input_points"):
                if python_snapshot[key] != cpp_snapshot[key]:
                    raise AssertionError(
                        f"stats mismatch {key}: {python_snapshot[key]} != {cpp_snapshot[key]}"
                    )
            if cpp_snapshot["guard_witness_published_frames"] != 1:
                raise AssertionError("C++ witness publication count must be one")
            if cpp_snapshot["guard_witness_points"] != len(expected_witness):
                raise AssertionError("C++ witness point count does not match output")
            if cpp_snapshot["guard_witness_payload_bytes"] != len(expected_witness) * 16:
                raise AssertionError("C++ witness payload counter does not match packed data")
            print(
                "PASS native sector geometry/stats equivalence: "
                f"{len(cpp_points)} retained, {len(witness_points)} witness points"
            )
        finally:
            if rclpy.ok():
                harness.destroy_node()
                rclpy.shutdown()
            for process in processes:
                terminate(process)


if __name__ == "__main__":
    main()
