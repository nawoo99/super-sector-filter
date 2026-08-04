#!/usr/bin/env python3
import argparse
import json
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Bool


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("waypoints", help='semicolon list, for example "24,24;-24,24"')
    parser.add_argument("switch_dist", type=float)
    parser.add_argument("timeout_s", type=float)
    parser.add_argument("out_json")
    parser.add_argument("--cloud-topic", default="/cloud_registered")
    parser.add_argument("--trap-intensity", type=float, default=12012.0)
    args, ros_args = parser.parse_known_args()
    return args, ros_args


ARGS, ROS_ARGS = parse_args()
WPS = [
    tuple(float(value) for value in point.split(","))
    for point in ARGS.waypoints.split(";")
]
DRONE_R = 0.2


class LoopMonitor(Node):
    def __init__(self):
        super().__init__("native_loop_monitor")
        self.cloud = None
        self.trap_cloud = None
        self.min_distance = float("inf")
        self.trap_min_distance = float("inf")
        self.collisions = 0
        self.trap_collisions = 0
        self.in_collision = False
        self.in_trap_collision = False
        self.samples = 0
        self.clearance_samples = 0
        self.waypoint_index = 0
        self.last_position = None
        self.final_position = None
        self.path_length = 0.0
        self.max_speed = 0.0
        self.min_x = float("inf")
        self.max_x = float("-inf")
        self.min_y = float("inf")
        self.max_y = float("-inf")
        self.closest_final_goal_distance = float("inf")
        self.full_open_state = None
        self.observed_open_time = None
        self.observed_open_position = None
        self.observed_close_time = None
        self.observed_close_position = None
        self.start_time = time.time()
        self.done_time = None
        self.create_subscription(
            PointCloud2, ARGS.cloud_topic, self.cloud_callback, qos_profile_sensor_data
        )
        self.create_subscription(
            Odometry, "/lidar_slam/odom", self.odom_callback, qos_profile_sensor_data
        )
        self.create_subscription(Bool, "/sector/full_open", self.full_open_callback, 1)

    def full_open_callback(self, msg):
        new_state = bool(msg.data)
        old_state = self.full_open_state
        self.full_open_state = new_state
        if old_state is False and new_state and self.observed_open_time is None:
            self.observed_open_time = time.time()
            self.observed_open_position = (
                self.final_position.copy() if self.final_position is not None else None
            )
        elif old_state is True and not new_state and self.observed_close_time is None:
            self.observed_close_time = time.time()
            self.observed_close_position = (
                self.final_position.copy() if self.final_position is not None else None
            )

    def cloud_callback(self, msg):
        try:
            points = pc2.read_points_numpy(
                msg, field_names=("x", "y", "z", "intensity"), skip_nans=True
            )
        except Exception:
            return
        points = points.reshape(-1, 4)
        self.cloud = points[:, :3] if points.size else None
        if points.size:
            trap_mask = np.isclose(
                points[:, 3], ARGS.trap_intensity, rtol=0.0, atol=0.01
            )
            self.trap_cloud = points[trap_mask, :3] if trap_mask.any() else None
        else:
            self.trap_cloud = None

    @staticmethod
    def nearest_distance(cloud, position):
        if cloud is None or len(cloud) == 0:
            return None
        delta = cloud - position
        return float(np.sqrt(np.einsum("ij,ij->i", delta, delta)).min())

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        position = np.array([p.x, p.y, p.z], dtype=np.float32)
        if self.last_position is not None:
            self.path_length += float(np.linalg.norm(position - self.last_position))
        self.last_position = position.copy()
        self.final_position = position.copy()
        self.min_x = min(self.min_x, float(p.x))
        self.max_x = max(self.max_x, float(p.x))
        self.min_y = min(self.min_y, float(p.y))
        self.max_y = max(self.max_y, float(p.y))
        v = msg.twist.twist.linear
        self.max_speed = max(self.max_speed, float(np.hypot(v.x, v.y)))
        final_x, final_y = WPS[-1]
        self.closest_final_goal_distance = min(
            self.closest_final_goal_distance,
            float(np.hypot(p.x - final_x, p.y - final_y)),
        )
        self.samples += 1

        distance = self.nearest_distance(self.cloud, position)
        if distance is not None:
            self.min_distance = min(self.min_distance, distance)
            self.clearance_samples += 1
            colliding = distance < DRONE_R
            if colliding and not self.in_collision:
                self.collisions += 1
            self.in_collision = colliding

        trap_distance = self.nearest_distance(self.trap_cloud, position)
        if trap_distance is not None:
            self.trap_min_distance = min(self.trap_min_distance, trap_distance)
            trap_colliding = trap_distance < DRONE_R
            if trap_colliding and not self.in_trap_collision:
                self.trap_collisions += 1
            self.in_trap_collision = trap_colliding
        else:
            self.in_trap_collision = False

        if self.waypoint_index < len(WPS):
            target_x, target_y = WPS[self.waypoint_index]
            distance_sq = (p.x - target_x) ** 2 + (p.y - target_y) ** 2
            if distance_sq < ARGS.switch_dist**2:
                self.waypoint_index += 1
                if self.waypoint_index >= len(WPS):
                    self.done_time = time.time()


rclpy.init(args=ROS_ARGS)
node = LoopMonitor()
while time.time() - node.start_time < ARGS.timeout_s and node.done_time is None:
    rclpy.spin_once(node, timeout_sec=0.2)

success = node.done_time is not None
mission_time = (
    node.done_time - node.start_time
    if success
    else time.time() - node.start_time
)
result = {
    "success": success,
    "mission_time_s": round(mission_time, 2),
    "waypoints_reached": node.waypoint_index,
    "n_waypoints": len(WPS),
    "collisions": node.collisions,
    # Historical field: UAV-center to nearest obstacle surface point.
    "min_clearance_m": (
        round(node.min_distance, 3)
        if node.min_distance != float("inf")
        else None
    ),
    "trap_collisions": node.trap_collisions,
    "trap_min_surface_distance_m": (
        round(node.trap_min_distance, 3)
        if node.trap_min_distance != float("inf")
        else None
    ),
    "trap_clearance_m": (
        round(node.trap_min_distance - DRONE_R, 3)
        if node.trap_min_distance != float("inf")
        else None
    ),
    "samples": node.samples,
    "clearance_samples": node.clearance_samples,
    "final_x": round(float(node.final_position[0]), 3) if node.final_position is not None else None,
    "final_y": round(float(node.final_position[1]), 3) if node.final_position is not None else None,
    "final_z": round(float(node.final_position[2]), 3) if node.final_position is not None else None,
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
    "observed_open_time_s": (
        round(node.observed_open_time, 6) if node.observed_open_time is not None else None
    ),
    "observed_open_x": (
        round(float(node.observed_open_position[0]), 3)
        if node.observed_open_position is not None else None
    ),
    "observed_open_y": (
        round(float(node.observed_open_position[1]), 3)
        if node.observed_open_position is not None else None
    ),
    "observed_close_time_s": (
        round(node.observed_close_time, 6) if node.observed_close_time is not None else None
    ),
    "observed_close_x": (
        round(float(node.observed_close_position[0]), 3)
        if node.observed_close_position is not None else None
    ),
    "observed_close_y": (
        round(float(node.observed_close_position[1]), 3)
        if node.observed_close_position is not None else None
    ),
}
with open(ARGS.out_json, "w") as stream:
    json.dump(result, stream)
print("NATIVE_LOOP " + json.dumps(result), flush=True)
