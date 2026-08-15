#!/usr/bin/env python3
"""Low-overhead monitor for the seed11 raw-direct outbound experiment.

Only odometry is retained while the vehicle is flying.  The static PCD is
indexed before the runner receives the READY handshake, and swept-segment
contact distances are evaluated after the run.  A small cloud subscription is
kept only during preflight so the mission cannot start before lidar data is
flowing.
"""

import argparse
import itertools
import json
import os
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from mars_quadrotor_msgs.msg import PositionCommand
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2


ROBOT_RADIUS_M = 0.20
CONTACT_RADII_M = (0.15, 0.20, 0.25)
REPORT_RADIUS_M = 2.0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("waypoints", help='semicolon list, for example "0,50"')
    parser.add_argument("switch_dist", type=float)
    parser.add_argument("timeout_s", type=float)
    parser.add_argument("out_json")
    parser.add_argument("--static-pcd", required=True)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--cloud-topic", default="/cloud_registered")
    parser.add_argument("--ready-clouds", type=int, default=5)
    parser.add_argument("--startup-timeout-s", type=float, default=45.0)
    parser.add_argument("--odom-gap-limit-s", type=float, default=0.05)
    parser.add_argument(
        "--stop-on-sticky-flag3-s",
        type=float,
        default=0.0,
        help="finish an unsuccessful guarded run after emergency flag3 remains stopped this long",
    )
    args, ros_args = parser.parse_known_args()
    return args, ros_args


ARGS, ROS_ARGS = parse_args()
WPS = [
    tuple(float(value) for value in point.split(","))
    for point in ARGS.waypoints.split(";")
]


class StaticPcdIndex:
    """Grid index with exact point-to-segment distance queries."""

    CELL_M = 0.5

    def __init__(self, path):
        with open(path) as stream:
            while True:
                line = stream.readline()
                if not line:
                    raise ValueError(f"PCD has no DATA header: {path}")
                if line.startswith("DATA "):
                    if line.strip() != "DATA ascii":
                        raise ValueError(f"only ASCII PCD is supported: {path}")
                    break
            points = np.loadtxt(stream, dtype=np.float32)
        points = points.reshape(-1, 3)
        points = points[np.isfinite(points).all(axis=1)]
        keys = np.floor(points / self.CELL_M).astype(np.int32)
        order = np.lexsort((keys[:, 2], keys[:, 1], keys[:, 0]))
        self.points = points[order]
        keys = keys[order]
        unique, starts = np.unique(keys, axis=0, return_index=True)
        ends = np.r_[starts[1:], len(self.points)]
        self.cells = {
            tuple(key): (int(start), int(end))
            for key, start, end in zip(unique, starts, ends)
        }

    def nearby_points(self, center, radius_m):
        cell = np.floor(center / self.CELL_M).astype(np.int32)
        reach = int(np.ceil(radius_m / self.CELL_M))
        chunks = []
        for offset in itertools.product(range(-reach, reach + 1), repeat=3):
            bounds = self.cells.get(tuple(cell + np.asarray(offset)))
            if bounds is not None:
                chunks.append(self.points[bounds[0]:bounds[1]])
        if not chunks:
            return np.empty((0, 3), dtype=np.float32)
        candidates = np.concatenate(chunks)
        delta = candidates - center
        return candidates[np.einsum("ij,ij->i", delta, delta) <= radius_m**2]

    def nearest_to_segment(self, start, end):
        segment = end - start
        length = float(np.linalg.norm(segment))
        midpoint = (start + end) * 0.5
        candidates = self.nearby_points(
            midpoint, radius_m=REPORT_RADIUS_M + 0.5 * length
        )
        if not len(candidates):
            return None, None, None, None
        length_sq = float(np.dot(segment, segment))
        if length_sq <= 1.0e-12:
            fractions = np.zeros(len(candidates), dtype=np.float32)
        else:
            fractions = np.clip(
                np.einsum("ij,j->i", candidates - start, segment) / length_sq,
                0.0,
                1.0,
            )
        path_points = start + fractions[:, None] * segment
        differences = candidates - path_points
        distances_sq = np.einsum("ij,ij->i", differences, differences)
        index = int(np.argmin(distances_sq))
        return (
            float(np.sqrt(distances_sq[index])),
            candidates[index],
            path_points[index],
            float(fractions[index]),
        )


def atomic_json(path, value):
    temporary_path = path + ".tmp"
    with open(temporary_path, "w") as stream:
        json.dump(value, stream)
    os.replace(temporary_path, path)


class ReferenceMonitor(Node):
    def __init__(self):
        super().__init__("native_reference_monitor")
        self.static_pcd = StaticPcdIndex(ARGS.static_pcd)
        self.process_start = time.monotonic()
        self.first_odom_position = None
        self.latest_position = None
        self.latest_velocity = None
        self.preflight_odom_messages = 0
        self.preflight_cloud_messages = 0
        self.ready = False
        self.goal_messages = 0
        self.mission_started = False
        self.mission_start = None
        self.mission_start_cpu = None
        self.position_command_messages = 0
        self.trajectory_flag2_messages = 0
        self.trajectory_flag3_messages = 0
        self.first_position_command_s = None
        self.first_trajectory_flag2_s = None
        self.first_trajectory_flag3_s = None
        self.latest_trajectory_flag = None
        self.flag2_stationary_since = None
        self.guard_stop_time = None
        self.max_position_command_gap = 0.0
        self.last_position_command_receive_time = None
        self.first_motion_s = None
        self.done_time = None
        self.waypoint_index = 0
        self.samples = []
        self.max_odom_gap = 0.0
        self.last_odom_receive_time = None
        self.path_length = 0.0
        self.max_speed = 0.0
        self.min_x = float("inf")
        self.max_x = float("-inf")
        self.min_y = float("inf")
        self.max_y = float("-inf")
        self.closest_final_goal_distance = float("inf")

        self.cloud_subscription = self.create_subscription(
            PointCloud2,
            ARGS.cloud_topic,
            self.cloud_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Odometry,
            "/lidar_slam/odom",
            self.odom_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PoseStamped,
            "/planning/click_goal",
            self.goal_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PositionCommand,
            "/planning/pos_cmd",
            self.command_callback,
            qos_profile_sensor_data,
        )

    def cloud_callback(self, _message):
        self.preflight_cloud_messages += 1
        self.maybe_ready()

    def maybe_ready(self):
        if (
            self.ready
            or self.first_odom_position is None
            or self.preflight_cloud_messages < ARGS.ready_clouds
        ):
            return
        self.ready = True
        atomic_json(
            ARGS.ready_file,
            {
                "ready": True,
                "preflight_cloud_messages": self.preflight_cloud_messages,
                "preflight_odom_messages": self.preflight_odom_messages,
                "first_odom_position": self.first_odom_position.tolist(),
            },
        )

    def goal_callback(self, _message):
        self.goal_messages += 1
        if self.mission_started:
            return
        self.mission_started = True
        self.mission_start = time.monotonic()
        self.mission_start_cpu = time.process_time()
        self.last_odom_receive_time = None
        if self.latest_position is not None:
            self.samples.append(
                (
                    0.0,
                    self.latest_position.copy(),
                    self.latest_velocity.copy(),
                )
            )
        if self.cloud_subscription is not None:
            self.destroy_subscription(self.cloud_subscription)
            self.cloud_subscription = None

    def command_callback(self, message):
        if not self.mission_started:
            return
        receive_time = time.monotonic()
        elapsed = receive_time - self.mission_start
        self.position_command_messages += 1
        if self.last_position_command_receive_time is not None:
            self.max_position_command_gap = max(
                self.max_position_command_gap,
                receive_time - self.last_position_command_receive_time,
            )
        self.last_position_command_receive_time = receive_time
        if self.first_position_command_s is None:
            self.first_position_command_s = elapsed
        if int(message.trajectory_flag) == 2:
            self.trajectory_flag2_messages += 1
            if self.first_trajectory_flag2_s is None:
                self.first_trajectory_flag2_s = elapsed
        if int(message.trajectory_flag) == 3:
            self.trajectory_flag3_messages += 1
            if self.first_trajectory_flag3_s is None:
                self.first_trajectory_flag3_s = elapsed
        self.latest_trajectory_flag = int(message.trajectory_flag)

    def odom_callback(self, message):
        receive_time = time.monotonic()
        position = np.asarray(
            [
                message.pose.pose.position.x,
                message.pose.pose.position.y,
                message.pose.pose.position.z,
            ],
            dtype=np.float64,
        )
        velocity = np.asarray(
            [
                message.twist.twist.linear.x,
                message.twist.twist.linear.y,
                message.twist.twist.linear.z,
            ],
            dtype=np.float64,
        )
        self.latest_position = position
        self.latest_velocity = velocity
        if self.first_odom_position is None:
            self.first_odom_position = position.copy()
        if not self.mission_started:
            self.preflight_odom_messages += 1
            self.maybe_ready()
            return

        elapsed = receive_time - self.mission_start
        if self.last_odom_receive_time is not None:
            self.max_odom_gap = max(
                self.max_odom_gap, receive_time - self.last_odom_receive_time
            )
        self.last_odom_receive_time = receive_time
        if self.samples:
            self.path_length += float(np.linalg.norm(position - self.samples[-1][1]))
        self.samples.append((elapsed, position.copy(), velocity.copy()))
        speed = float(np.linalg.norm(velocity))
        if (
            ARGS.stop_on_sticky_flag3_s > 0.0
            and self.latest_trajectory_flag == 3
            and speed < 0.05
        ):
            if self.flag2_stationary_since is None:
                self.flag2_stationary_since = receive_time
            elif (
                receive_time - self.flag2_stationary_since
                >= ARGS.stop_on_sticky_flag3_s
            ):
                self.guard_stop_time = receive_time
        else:
            self.flag2_stationary_since = None
        if speed > 0.10 and self.first_motion_s is None:
            self.first_motion_s = elapsed
        self.max_speed = max(self.max_speed, speed)
        self.min_x = min(self.min_x, float(position[0]))
        self.max_x = max(self.max_x, float(position[0]))
        self.min_y = min(self.min_y, float(position[1]))
        self.max_y = max(self.max_y, float(position[1]))
        final_x, final_y = WPS[-1]
        final_distance = float(
            np.hypot(position[0] - final_x, position[1] - final_y)
        )
        self.closest_final_goal_distance = min(
            self.closest_final_goal_distance, final_distance
        )
        if self.waypoint_index < len(WPS):
            target_x, target_y = WPS[self.waypoint_index]
            if np.hypot(position[0] - target_x, position[1] - target_y) < ARGS.switch_dist:
                self.waypoint_index += 1
                if self.waypoint_index >= len(WPS):
                    self.done_time = receive_time

    def evaluate_contacts(self):
        counts = {radius: 0 for radius in CONTACT_RADII_M}
        active = {radius: False for radius in CONTACT_RADII_M}
        minimum_distance = float("inf")
        evaluated_segments = 0
        events = []
        if not self.samples:
            return counts, minimum_distance, evaluated_segments, events

        pairs = zip(self.samples[:-1], self.samples[1:])
        if len(self.samples) == 1:
            pairs = [(self.samples[0], self.samples[0])]
        for first, second in pairs:
            distance, obstacle_point, path_point, fraction = (
                self.static_pcd.nearest_to_segment(first[1], second[1])
            )
            if distance is None:
                for radius in CONTACT_RADII_M:
                    active[radius] = False
                continue
            evaluated_segments += 1
            minimum_distance = min(minimum_distance, distance)
            for radius in CONTACT_RADII_M:
                colliding = distance < radius
                if colliding and not active[radius]:
                    counts[radius] += 1
                    if radius == ROBOT_RADIUS_M:
                        event_elapsed = first[0] + fraction * (second[0] - first[0])
                        event_velocity = first[2] + fraction * (second[2] - first[2])
                        events.append(
                            {
                                "kind": "static_pcd_swept_segment",
                                "elapsed_s": round(float(event_elapsed), 6),
                                "distance_m": round(float(distance), 6),
                                "position": [round(float(value), 6) for value in path_point],
                                "nearest_point": [
                                    round(float(value), 6) for value in obstacle_point
                                ],
                                "speed_mps": round(
                                    float(np.linalg.norm(event_velocity)), 6
                                ),
                            }
                        )
                active[radius] = colliding
        return counts, minimum_distance, evaluated_segments, events


rclpy.init(args=ROS_ARGS)
node = ReferenceMonitor()
while True:
    now = time.monotonic()
    if node.done_time is not None:
        break
    if node.guard_stop_time is not None:
        break
    if node.mission_started:
        if now - node.mission_start >= ARGS.timeout_s:
            break
    elif now - node.process_start >= ARGS.startup_timeout_s:
        break
    rclpy.spin_once(node, timeout_sec=0.05)

flight_end_cpu = time.process_time()
counts, minimum_distance, evaluated_segments, contact_events = node.evaluate_contacts()
success = node.done_time is not None
if node.mission_started:
    end_time = node.done_time if success else time.monotonic()
    mission_time = end_time - node.mission_start
else:
    mission_time = 0.0
monitor_flight_cpu_pct = (
    100.0 * (flight_end_cpu - node.mission_start_cpu) / mission_time
    if node.mission_start_cpu is not None and mission_time > 0.0
    else None
)
start_error = (
    float(np.linalg.norm(node.first_odom_position - np.asarray([0.0, -50.0, 1.5])))
    if node.first_odom_position is not None
    else float("inf")
)
start_pose_valid = start_error <= 0.5
odom_gap_valid = bool(node.samples) and node.max_odom_gap <= ARGS.odom_gap_limit_s
run_valid = bool(
    node.ready
    and node.mission_started
    and start_pose_valid
    and odom_gap_valid
    and node.preflight_cloud_messages >= ARGS.ready_clouds
)
final_position = node.samples[-1][1] if node.samples else None
result = {
    "success": success,
    "run_valid": run_valid,
    "monitor_type": "odom_static_pcd_swept_segment",
    "monitor_flight_cpu_pct": (
        round(monitor_flight_cpu_pct, 6)
        if monitor_flight_cpu_pct is not None
        else None
    ),
    "live_cloud_enabled": False,
    "preflight_ready": node.ready,
    "preflight_cloud_messages": node.preflight_cloud_messages,
    "preflight_odom_messages": node.preflight_odom_messages,
    "goal_messages": node.goal_messages,
    "position_command_messages": node.position_command_messages,
    "trajectory_flag2_messages": node.trajectory_flag2_messages,
    "trajectory_flag3_messages": node.trajectory_flag3_messages,
    "guard_stop_detected": node.guard_stop_time is not None,
    "guard_stop_time_s": (
        round(node.guard_stop_time - node.mission_start, 6)
        if node.guard_stop_time is not None and node.mission_start is not None
        else None
    ),
    "first_position_command_s": (
        round(node.first_position_command_s, 6)
        if node.first_position_command_s is not None
        else None
    ),
    "first_trajectory_flag2_s": (
        round(node.first_trajectory_flag2_s, 6)
        if node.first_trajectory_flag2_s is not None
        else None
    ),
    "first_trajectory_flag3_s": (
        round(node.first_trajectory_flag3_s, 6)
        if node.first_trajectory_flag3_s is not None
        else None
    ),
    "max_position_command_gap_s": round(node.max_position_command_gap, 6),
    "first_motion_s": (
        round(node.first_motion_s, 6) if node.first_motion_s is not None else None
    ),
    "start_pose_error_m": round(start_error, 6) if np.isfinite(start_error) else None,
    "start_pose_valid": start_pose_valid,
    "odom_gap_limit_s": ARGS.odom_gap_limit_s,
    "max_odom_gap_s": round(node.max_odom_gap, 6),
    "odom_gap_valid": odom_gap_valid,
    "mission_time_s": round(mission_time, 2),
    "waypoints_reached": node.waypoint_index,
    "n_waypoints": len(WPS),
    "collisions": None,
    "min_clearance_m": None,
    "static_pcd_collisions": counts[0.20],
    "static_pcd_contact_r015": counts[0.15] > 0,
    "static_pcd_contact_r020": counts[0.20] > 0,
    "static_pcd_contact_r025": counts[0.25] > 0,
    "static_pcd_episodes_r015": counts[0.15],
    "static_pcd_episodes_r020": counts[0.20],
    "static_pcd_episodes_r025": counts[0.25],
    "static_pcd_min_distance_m": (
        round(minimum_distance, 6) if np.isfinite(minimum_distance) else None
    ),
    "static_pcd_clearance_m": (
        round(minimum_distance - ROBOT_RADIUS_M, 6)
        if np.isfinite(minimum_distance)
        else None
    ),
    "contact_event_count": len(contact_events),
    "contact_events": contact_events,
    "samples": len(node.samples),
    "clearance_samples": evaluated_segments,
    "final_x": round(float(final_position[0]), 3) if final_position is not None else None,
    "final_y": round(float(final_position[1]), 3) if final_position is not None else None,
    "final_z": round(float(final_position[2]), 3) if final_position is not None else None,
    "min_x": round(node.min_x, 3) if node.min_x != float("inf") else None,
    "max_x": round(node.max_x, 3) if node.max_x != float("-inf") else None,
    "min_y": round(node.min_y, 3) if node.min_y != float("inf") else None,
    "max_y": round(node.max_y, 3) if node.max_y != float("-inf") else None,
    "path_length_m": round(node.path_length, 3),
    "max_speed_mps": round(node.max_speed, 3),
    "closest_final_goal_distance_m": (
        round(node.closest_final_goal_distance, 3)
        if node.closest_final_goal_distance != float("inf")
        else None
    ),
}
atomic_json(ARGS.out_json, result)
console_result = dict(result)
console_result.pop("contact_events", None)
print("NATIVE_REFERENCE " + json.dumps(console_result), flush=True)
