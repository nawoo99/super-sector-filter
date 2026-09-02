#!/usr/bin/env python3
import argparse
import itertools
import json
import os
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
        "--speed-limit-mps",
        type=float,
        help="optional 3-D PositionCommand/odometry speed validity bound",
    )
    parser.add_argument(
        "--speed-tolerance-mps",
        type=float,
        default=0.01,
        help="absolute numerical tolerance added to --speed-limit-mps",
    )
    parser.add_argument(
        "--static-pcd",
        help=(
            "optional ASCII PCD used for an auxiliary occupied-sample union; "
            "each point is inflated by the 0.20 m robot radius"
        ),
    )
    parser.add_argument(
        "--side-entry-event-json",
        help=(
            "authoritative side-entry-v1 spawn event; collision is computed "
            "from cylinder geometry so cpp-frontend runs need no raw DDS topic"
        ),
    )
    args, ros_args = parser.parse_known_args()
    if args.speed_limit_mps is not None and args.speed_limit_mps <= 0.0:
        parser.error("--speed-limit-mps must be positive")
    if args.speed_tolerance_mps < 0.0:
        parser.error("--speed-tolerance-mps must be non-negative")
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

    def nearest(self, position, max_distance_m=None):
        if max_distance_m is not None:
            candidates = self.nearby_points(position, radius_m=max_distance_m)
            if not len(candidates):
                return None, None
            delta = candidates - position
            distance_sq = np.einsum("ij,ij->i", delta, delta)
            index = int(np.argmin(distance_sq))
            return float(np.sqrt(distance_sq[index])), candidates[index]

        # This metric is reported as an actual nearest distance, not merely a
        # collision-within-one-cell test.  The old fixed 0.5 m query returned
        # None whenever the whole flight stayed farther than 0.5 m from the
        # static PCD, which serialized a perfectly clear run as a missing
        # (null) measurement.  Visit Chebyshev cell shells until the nearest
        # point found is closer than every face of the searched cube.  At that
        # point no unvisited cell can contain a closer point, so the result is
        # exact while normal near-obstacle queries still inspect only a few
        # cells.
        center = np.floor(position / self.CELL_M).astype(np.int32)
        best_distance_sq = float("inf")
        best_point = None
        reach = 0
        while True:
            offsets = itertools.product(range(-reach, reach + 1), repeat=3)
            for offset in offsets:
                if reach and max(abs(value) for value in offset) != reach:
                    continue
                bounds = self.cells.get(tuple(center + np.asarray(offset)))
                if bounds is None:
                    continue
                candidates = self.points[bounds[0]:bounds[1]]
                delta = candidates - position
                distance_sq = np.einsum("ij,ij->i", delta, delta)
                index = int(np.argmin(distance_sq))
                if float(distance_sq[index]) < best_distance_sq:
                    best_distance_sq = float(distance_sq[index])
                    best_point = candidates[index]

            low = (center - reach) * self.CELL_M
            high = (center + reach + 1) * self.CELL_M
            unsearched_lower_bound = float(
                np.min(np.concatenate((position - low, high - position)))
            )
            if (best_point is not None and
                    best_distance_sq <= unsearched_lower_bound**2):
                return float(np.sqrt(best_distance_sq)), best_point
            reach += 1


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
        self.static_pcd_min_context = None
        self.trap_min_distance = float("inf")
        self.side_entry_event = None
        self.side_entry_event_error = None
        self.side_entry_min_clearance = float("inf")
        self.side_entry_collision_episodes = 0
        self.collisions = 0
        self.static_pcd_collisions = 0
        self.trap_collisions = 0
        self.in_collision = False
        self.in_static_pcd_collision = False
        self.in_trap_collision = False
        self.in_side_entry_collision = False
        self.contact_events = []
        self.samples = 0
        self.clearance_samples = 0
        self.waypoint_index = 0
        self.last_position = None
        self.final_position = None
        self.path_length = 0.0
        self.max_speed = 0.0
        self.max_odom_speed_3d = 0.0
        self.max_command_speed = 0.0
        self.max_command_horizontal_speed = 0.0
        self.speed_exceedance_count = 0
        self.command_speed_exceedance_count = 0
        self.odom_speed_exceedance_count = 0
        self.first_speed_exceedance = None
        self.max_speed_context = None
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

    def load_side_entry_event(self):
        if self.side_entry_event is not None or not ARGS.side_entry_event_json:
            return
        if not os.path.exists(ARGS.side_entry_event_json):
            return
        try:
            with open(ARGS.side_entry_event_json) as stream:
                event = json.load(stream)
            required = (
                "side_entry_v1_geometry_valid",
                "side_entry_v1_trap_x",
                "side_entry_v1_trap_y",
                "side_entry_v1_radius_m",
                "side_entry_v1_height_m",
            )
            missing = [key for key in required if key not in event]
            if missing:
                raise ValueError("missing keys: " + ", ".join(missing))
            if event["side_entry_v1_geometry_valid"] is not True:
                raise ValueError("spawn geometry was not validated")
            if float(event["side_entry_v1_radius_m"]) <= 0.0:
                raise ValueError("radius must be positive")
            if float(event["side_entry_v1_height_m"]) <= 0.0:
                raise ValueError("height must be positive")
            self.side_entry_event = event
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            self.side_entry_event_error = str(error)

    def update_side_entry_collision(self, position, velocity):
        self.load_side_entry_event()
        if self.side_entry_event is None:
            self.in_side_entry_collision = False
            return
        event = self.side_entry_event
        center = np.array(
            [
                float(event["side_entry_v1_trap_x"]),
                float(event["side_entry_v1_trap_y"]),
            ],
            dtype=np.float64,
        )
        radius = float(event["side_entry_v1_radius_m"])
        height = float(event["side_entry_v1_height_m"])
        offset = position[:2].astype(np.float64) - center
        radial_distance = float(np.linalg.norm(offset))
        radial_outside = max(0.0, radial_distance - radius)
        if position[2] < 0.0:
            vertical_outside = float(-position[2])
        elif position[2] > height:
            vertical_outside = float(position[2] - height)
        else:
            vertical_outside = 0.0
        solid_distance = float(np.hypot(radial_outside, vertical_outside))
        clearance = solid_distance - DRONE_R
        self.side_entry_min_clearance = min(
            self.side_entry_min_clearance, clearance
        )
        colliding = clearance < 0.0
        if colliding and not self.in_side_entry_collision:
            self.side_entry_collision_episodes += 1
            if radial_distance > 1e-9:
                direction = offset / radial_distance
            else:
                direction = np.array([1.0, 0.0], dtype=np.float64)
            nearest_point = np.array(
                [
                    center[0] + radius * direction[0],
                    center[1] + radius * direction[1],
                    min(height, max(0.0, float(position[2]))),
                ],
                dtype=np.float64,
            )
            self.record_contact_event(
                "side_entry_v1",
                solid_distance,
                nearest_point,
                position,
                velocity,
            )
        self.in_side_entry_collision = colliding

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
        velocity = np.array(
            [msg.velocity.x, msg.velocity.y, msg.velocity.z], dtype=np.float64
        )
        speed = float(np.linalg.norm(velocity))
        horizontal_speed = float(np.hypot(msg.velocity.x, msg.velocity.y))
        self.max_command_speed = max(self.max_command_speed, speed)
        self.max_command_horizontal_speed = max(
            self.max_command_horizontal_speed, horizontal_speed
        )
        self.record_speed_sample(
            "command",
            speed,
            np.array(
                [msg.position.x, msg.position.y, msg.position.z],
                dtype=np.float64,
            ),
            velocity,
            self.latest_command,
        )

    def record_speed_sample(self, kind, speed, position, velocity, command=None):
        if not np.isfinite(speed):
            exceeded = ARGS.speed_limit_mps is not None
        else:
            exceeded = (
                ARGS.speed_limit_mps is not None
                and speed > ARGS.speed_limit_mps + ARGS.speed_tolerance_mps
            )
        context = {
            "kind": kind,
            "elapsed_s": round(time.time() - self.start_time, 6),
            "speed_mps": round(float(speed), 6),
            "position": np.round(position, 6).tolist(),
            "velocity": np.round(velocity, 6).tolist(),
            "acceleration": (
                command.get("acceleration") if command is not None else None
            ),
            "trajectory_id": (
                command.get("trajectory_id") if command is not None else None
            ),
            "trajectory_flag": (
                command.get("trajectory_flag") if command is not None else None
            ),
        }
        if (
            self.max_speed_context is None
            or speed > self.max_speed_context["speed_mps"]
        ):
            self.max_speed_context = context
        if not exceeded:
            return
        self.speed_exceedance_count += 1
        if kind == "command":
            self.command_speed_exceedance_count += 1
        else:
            self.odom_speed_exceedance_count += 1
        if self.first_speed_exceedance is None:
            self.first_speed_exceedance = context

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
        # /cloud_registered is a rendered observation, not the simulator's
        # static geometry oracle.  MARSIM fills angular pixels around each
        # source PCD sample, so a live point can lie inside the 0.20 m marker
        # radius even when the vehicle remains outside the source PCD.  Keep
        # the historical live marker unchanged, but attach an independent
        # static-PCD check at the event pose (and the rendered point's offset
        # from that PCD) so a live-only rasterization boundary is not silently
        # reported as a common physical collision across filter modes.
        static_distance_at_event = None
        static_nearest_at_event = None
        live_point_static_distance = None
        if self.static_pcd is not None:
            static_distance_at_event, static_nearest_at_event = (
                self.static_pcd.nearest(position)
            )
            if kind == "live_cloud":
                live_point_static_distance, _ = self.static_pcd.nearest(
                    nearest_point
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
                "static_distance_at_event_m": (
                    round(float(static_distance_at_event), 5)
                    if static_distance_at_event is not None else None
                ),
                "static_clearance_at_event_m": (
                    round(float(static_distance_at_event - DRONE_R), 5)
                    if static_distance_at_event is not None else None
                ),
                "static_contact_at_event": (
                    static_distance_at_event < DRONE_R
                    if static_distance_at_event is not None else None
                ),
                "static_nearest_point_at_event": (
                    np.round(static_nearest_at_event, 5).tolist()
                    if static_nearest_at_event is not None else None
                ),
                "live_point_static_distance_m": (
                    round(float(live_point_static_distance), 5)
                    if live_point_static_distance is not None else None
                ),
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
        self.update_side_entry_collision(position, velocity)
        self.max_speed = max(self.max_speed, float(np.hypot(v.x, v.y)))
        odom_speed_3d = float(np.linalg.norm(velocity))
        self.max_odom_speed_3d = max(self.max_odom_speed_3d, odom_speed_3d)
        self.record_speed_sample(
            "odom", odom_speed_3d, position, velocity, self.latest_command
        )
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
            # One exact query establishes a finite upper bound.  Thereafter a
            # point can change the run-wide minimum only if it lies inside the
            # current minimum, while collision episode tracking needs at most
            # the body radius.  Bounding later lookups this way preserves both
            # results exactly without paying for a global nearest query at
            # every 100 Hz odometry sample.
            static_search_radius = (
                None
                if self.static_pcd_min_distance == float("inf")
                else max(DRONE_R, self.static_pcd_min_distance)
            )
            static_distance, static_nearest = self.static_pcd.nearest(
                position, max_distance_m=static_search_radius
            )
            if static_distance is not None:
                if static_distance < self.static_pcd_min_distance:
                    self.static_pcd_min_distance = static_distance
                    self.static_pcd_min_context = {
                        "elapsed_s": round(time.time() - self.start_time, 6),
                        "position": np.round(position, 6).tolist(),
                        "velocity": np.round(velocity, 6).tolist(),
                        "speed_mps": round(odom_speed_3d, 6),
                        "nearest_point": np.round(static_nearest, 6).tolist(),
                        "distance_m": round(float(static_distance), 6),
                        "clearance_m": round(
                            float(static_distance - DRONE_R), 6
                        ),
                        "waypoint_index": self.waypoint_index,
                    }
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
    "static_pcd_enabled": node.static_pcd is not None,
    "static_pcd_point_count": (
        len(node.static_pcd.points) if node.static_pcd is not None else 0
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
    "static_pcd_min_context": node.static_pcd_min_context,
    "contact_event_count": len(node.contact_events),
    # Protocol safety authority is explicit.  Static seed-map campaigns use
    # the same source PCD for every mode; runs without that oracle retain the
    # historical live-cloud episode count.  The raw live fields above remain
    # available and are never overwritten by this classification.
    "safety_contact_source": (
        "static_pcd+side_entry_v1_geometry"
        if ARGS.side_entry_event_json and node.static_pcd is not None
        else "side_entry_v1_geometry"
        if ARGS.side_entry_event_json
        else "static_pcd"
        if node.static_pcd is not None
        else "live_cloud"
    ),
    "safety_collisions": (
        (node.static_pcd_collisions if node.static_pcd is not None else 0)
        + node.side_entry_collision_episodes
        if ARGS.side_entry_event_json
        else node.static_pcd_collisions
        if node.static_pcd is not None
        else node.collisions
    ),
    "live_only_contact_event_count": sum(
        1 for event in node.contact_events
        if event.get("kind") == "live_cloud"
        and event.get("static_contact_at_event") is False
    ),
    "static_confirmed_live_contact_event_count": sum(
        1 for event in node.contact_events
        if event.get("kind") == "live_cloud"
        and event.get("static_contact_at_event") is True
    ),
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
    "side_entry_v1_event_requested": bool(ARGS.side_entry_event_json),
    "side_entry_v1_event_loaded": node.side_entry_event is not None,
    "side_entry_v1_event_error": node.side_entry_event_error,
    "side_entry_v1_geometry_valid": (
        node.side_entry_event.get("side_entry_v1_geometry_valid")
        if node.side_entry_event is not None else None
    ),
    "side_entry_v1_collision_episodes": node.side_entry_collision_episodes,
    "side_entry_v1_collision": node.side_entry_collision_episodes > 0,
    "side_entry_v1_min_clearance_m": (
        round(node.side_entry_min_clearance, 3)
        if node.side_entry_min_clearance != float("inf") else None
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
    "max_odom_speed_3d_mps": round(node.max_odom_speed_3d, 6),
    "max_command_speed_mps": round(node.max_command_speed, 6),
    "max_command_horizontal_speed_mps": round(
        node.max_command_horizontal_speed, 6
    ),
    "speed_limit_mps": ARGS.speed_limit_mps,
    "speed_tolerance_mps": ARGS.speed_tolerance_mps,
    "speed_limit_valid": (
        None
        if ARGS.speed_limit_mps is None
        else node.speed_exceedance_count == 0
    ),
    "speed_exceedance_count": node.speed_exceedance_count,
    "command_speed_exceedance_count": node.command_speed_exceedance_count,
    "odom_speed_exceedance_count": node.odom_speed_exceedance_count,
    "first_speed_exceedance_kind": (
        node.first_speed_exceedance.get("kind")
        if node.first_speed_exceedance else None
    ),
    "first_speed_exceedance_time_s": (
        node.first_speed_exceedance.get("elapsed_s")
        if node.first_speed_exceedance else None
    ),
    "first_speed_exceedance_mps": (
        node.first_speed_exceedance.get("speed_mps")
        if node.first_speed_exceedance else None
    ),
    "first_speed_exceedance_trajectory_id": (
        node.first_speed_exceedance.get("trajectory_id")
        if node.first_speed_exceedance else None
    ),
    "first_speed_exceedance_trajectory_flag": (
        node.first_speed_exceedance.get("trajectory_flag")
        if node.first_speed_exceedance else None
    ),
    "speed_exceedance_context": node.first_speed_exceedance,
    "max_speed_context": node.max_speed_context,
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
