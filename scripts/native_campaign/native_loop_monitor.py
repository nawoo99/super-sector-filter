#!/usr/bin/env python3
import argparse
import itertools
import json
import time

import numpy as np
import rclpy
from mars_quadrotor_msgs.msg import PositionCommand
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Bool
from visualization_msgs.msg import MarkerArray


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("waypoints", help='semicolon list, for example "24,24;-24,24"')
    parser.add_argument("switch_dist", type=float)
    parser.add_argument("timeout_s", type=float)
    parser.add_argument("out_json")
    parser.add_argument("--cloud-topic", default="/cloud_registered")
    parser.add_argument("--trap-intensity", type=float, default=12012.0)
    parser.add_argument(
        "--static-pcd",
        help=(
            "optional ASCII PCD used for an auxiliary occupied-sample union; "
            "each point is inflated by the 0.20 m robot radius"
        ),
    )
    args, ros_args = parser.parse_known_args()
    return args, ros_args


ARGS, ROS_ARGS = parse_args()
WPS = [
    tuple(float(value) for value in point.split(","))
    for point in ARGS.waypoints.split(";")
]
DRONE_R = 0.2


class StaticPcdIndex:
    """Compact grid index for collision checks against a static ASCII PCD."""

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

    def nearby_points(self, position, radius_m=1.0):
        center = np.floor(position / self.CELL_M).astype(np.int32)
        reach = int(np.ceil(radius_m / self.CELL_M))
        chunks = []
        for offset in itertools.product(range(-reach, reach + 1), repeat=3):
            bounds = self.cells.get(tuple(center + np.asarray(offset)))
            if bounds is not None:
                chunks.append(self.points[bounds[0]:bounds[1]])
        if not chunks:
            return np.empty((0, 3), dtype=np.float32)
        candidates = np.concatenate(chunks)
        delta = candidates - position
        return candidates[np.einsum("ij,ij->i", delta, delta) <= radius_m**2]

    def nearest(self, position):
        # Adjacent 0.5 m cells contain every point that could be within the
        # 0.20 m body radius, while avoiding a 5x5x5 lookup at 100 Hz.
        candidates = self.nearby_points(position, radius_m=self.CELL_M)
        if not len(candidates):
            return None, None
        delta = candidates - position
        distance_sq = np.einsum("ij,ij->i", delta, delta)
        index = int(np.argmin(distance_sq))
        return float(np.sqrt(distance_sq[index])), candidates[index]


class LoopMonitor(Node):
    def __init__(self):
        super().__init__("native_loop_monitor")
        self.static_pcd = StaticPcdIndex(ARGS.static_pcd) if ARGS.static_pcd else None
        self.cloud = None
        self.occupancy_cloud = None
        self.occupancy_messages = 0
        self.trap_cloud = None
        self.latest_command = None
        self.latest_frontend_path = []
        self.latest_committed_trajectory = []
        self.min_distance = float("inf")
        self.static_pcd_min_distance = float("inf")
        self.trap_min_distance = float("inf")
        self.collisions = 0
        self.static_pcd_collisions = 0
        self.trap_collisions = 0
        self.in_collision = False
        self.in_static_pcd_collision = False
        self.in_trap_collision = False
        self.contact_events = []
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
        self.create_subscription(
            PositionCommand,
            "/planning/pos_cmd",
            self.command_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            MarkerArray,
            "/visualization/frontend_path",
            self.frontend_path_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PointCloud2,
            "/rog_map/occ",
            self.occupancy_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            MarkerArray,
            "/visualization/committed_traj",
            self.committed_trajectory_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(Bool, "/sector/full_open", self.full_open_callback, 1)

    @staticmethod
    def vector3(value):
        return [round(float(value.x), 4), round(float(value.y), 4), round(float(value.z), 4)]

    def command_callback(self, msg):
        self.latest_command = {
            "position": self.vector3(msg.position),
            "velocity": self.vector3(msg.velocity),
            "acceleration": self.vector3(msg.acceleration),
            "yaw": round(float(msg.yaw), 5),
            "yaw_dot": round(float(msg.yaw_dot), 5),
            "trajectory_id": int(msg.trajectory_id),
            "trajectory_flag": int(msg.trajectory_flag),
        }

    def marker_points(self, msg):
        points = []
        for marker in msg.markers:
            if marker.action in (marker.DELETE, marker.DELETEALL):
                continue
            for point in marker.points:
                points.append(self.vector3(point))
        return points[:500]

    def frontend_path_callback(self, msg):
        points = self.marker_points(msg)
        if points:
            self.latest_frontend_path = points

    def committed_trajectory_callback(self, msg):
        points = self.marker_points(msg)
        if points:
            self.latest_committed_trajectory = points

    def occupancy_callback(self, msg):
        try:
            points = pc2.read_points_numpy(
                msg, field_names=("x", "y", "z"), skip_nans=True
            )
        except Exception:
            return
        points = points.reshape(-1, 3)
        self.occupancy_cloud = points if points.size else None
        self.occupancy_messages += 1

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
        cloud = points[:, :3] if points.size else None
        # Only points near the current body can affect the 0.20 m contact
        # decision before the next 10 Hz scan. Cropping once per cloud avoids
        # scanning roughly 66k points for every 100 Hz odometry callback.
        if cloud is not None and self.final_position is not None:
            delta = cloud - self.final_position
            cloud = cloud[np.einsum("ij,ij->i", delta, delta) <= 2.0**2]
        self.cloud = cloud
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
            return None, None
        delta = cloud - position
        distance_sq = np.einsum("ij,ij->i", delta, delta)
        index = int(np.argmin(distance_sq))
        return float(np.sqrt(distance_sq[index])), cloud[index]

    @staticmethod
    def rounded_points(points, limit=2000):
        if points is None or not len(points):
            return []
        if len(points) > limit:
            sample_indices = np.linspace(0, len(points) - 1, limit, dtype=np.int64)
            points = points[sample_indices]
        return np.round(points, 4).tolist()

    def record_contact_event(self, kind, distance, nearest_point, position, velocity):
        local_cloud = None
        if self.cloud is not None:
            delta = self.cloud - position
            local_cloud = self.cloud[np.einsum("ij,ij->i", delta, delta) <= 1.0]
        local_static = (
            self.static_pcd.nearby_points(position, radius_m=1.0)
            if self.static_pcd is not None
            else None
        )
        local_occupancy = None
        if self.occupancy_cloud is not None:
            delta = self.occupancy_cloud - position
            local_occupancy = self.occupancy_cloud[
                np.einsum("ij,ij->i", delta, delta) <= 5.0**2
            ]
        self.contact_events.append(
            {
                "kind": kind,
                "epoch_s": round(time.time(), 6),
                "elapsed_s": round(time.time() - self.start_time, 4),
                "distance_m": round(float(distance), 5),
                "position": np.round(position, 5).tolist(),
                "velocity": np.round(velocity, 5).tolist(),
                "speed_mps": round(float(np.linalg.norm(velocity)), 5),
                "nearest_point": np.round(nearest_point, 5).tolist(),
                "position_command": self.latest_command,
                "frontend_path": self.latest_frontend_path,
                "committed_trajectory": self.latest_committed_trajectory,
                "raw_cloud_local_1m": self.rounded_points(local_cloud),
                "occupancy_messages_received": self.occupancy_messages,
                "occupancy_point_count_total": (
                    len(self.occupancy_cloud)
                    if self.occupancy_cloud is not None
                    else 0
                ),
                "occupancy_local_5m": self.rounded_points(
                    local_occupancy, limit=5000
                ),
                "static_pcd_local_1m": self.rounded_points(local_static),
            }
        )

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
        velocity = np.array([v.x, v.y, v.z], dtype=np.float32)
        self.max_speed = max(self.max_speed, float(np.hypot(v.x, v.y)))
        final_x, final_y = WPS[-1]
        self.closest_final_goal_distance = min(
            self.closest_final_goal_distance,
            float(np.hypot(p.x - final_x, p.y - final_y)),
        )
        self.samples += 1

        distance, nearest_point = self.nearest_distance(self.cloud, position)
        if distance is not None:
            self.min_distance = min(self.min_distance, distance)
            self.clearance_samples += 1
            colliding = distance < DRONE_R
            if colliding and not self.in_collision:
                self.collisions += 1
                self.record_contact_event(
                    "live_cloud", distance, nearest_point, position, velocity
                )
            self.in_collision = colliding

        if self.static_pcd is not None:
            static_distance, static_nearest = self.static_pcd.nearest(position)
            if static_distance is not None:
                self.static_pcd_min_distance = min(
                    self.static_pcd_min_distance, static_distance
                )
                static_colliding = static_distance < DRONE_R
                if static_colliding and not self.in_static_pcd_collision:
                    self.static_pcd_collisions += 1
                    self.record_contact_event(
                        "static_pcd",
                        static_distance,
                        static_nearest,
                        position,
                        velocity,
                    )
                self.in_static_pcd_collision = static_colliding

        trap_distance, _ = self.nearest_distance(self.trap_cloud, position)
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
    "static_pcd_collisions": node.static_pcd_collisions,
    "static_pcd_min_distance_m": (
        round(node.static_pcd_min_distance, 3)
        if node.static_pcd_min_distance != float("inf")
        else None
    ),
    "static_pcd_clearance_m": (
        round(node.static_pcd_min_distance - DRONE_R, 3)
        if node.static_pcd_min_distance != float("inf")
        else None
    ),
    "contact_event_count": len(node.contact_events),
    "contact_events": node.contact_events,
    "occupancy_messages": node.occupancy_messages,
    "occupancy_points_latest": (
        len(node.occupancy_cloud) if node.occupancy_cloud is not None else 0
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
console_result = dict(result)
console_result.pop("contact_events", None)
print("NATIVE_LOOP " + json.dumps(console_result), flush=True)
