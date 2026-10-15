#!/usr/bin/env python3
"""Inject a deterministic mirrored U pocket for the seed14/15 recovery test.

The pocket appears permanently once the vehicle crosses a fixed world-x
threshold.  Its spawn condition deliberately has no dependency on the sector
filter mode, armed state, or full-open state.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import os
import sys
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2


DEFAULT_INTENSITY = 14015.0
FORWARD_HALF_ANGLE_DEG = 60.0


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Inject a progress-triggered tangent-cylinder recovery pocket "
            "into a registered PointCloud2 stream."
        )
    )
    parser.add_argument("--side", choices=("left", "right"), default="left")
    parser.add_argument("--trigger-x", type=float, default=20.0)
    parser.add_argument("--min-trigger-speed", type=float, default=1.5)
    parser.add_argument("--min-cruise-s", type=float, default=2.1)
    parser.add_argument(
        "--max-trigger-abs-y",
        type=float,
        default=0.5,
        help="Diagnostic only; velocity-frame geometry is not rejected by it.",
    )
    parser.add_argument(
        "--max-trigger-velocity-yaw-deg",
        type=float,
        default=10.0,
        help="Diagnostic only; velocity-frame geometry is not rejected by it.",
    )
    parser.add_argument("--front-forward-m", type=float, default=6.0)
    parser.add_argument("--rear-forward-m", type=float, default=-4.0)
    parser.add_argument("--half-width-m", type=float, default=1.5)
    parser.add_argument("--horizon-m", type=float, default=15.0)
    parser.add_argument("--radius-m", type=float, default=0.25)
    parser.add_argument("--height-m", type=float, default=3.0)
    parser.add_argument("--point-spacing-m", type=float, default=0.10)
    parser.add_argument("--z-spacing-m", type=float, default=0.15)
    parser.add_argument("--intensity", type=float, default=DEFAULT_INTENSITY)
    parser.add_argument("--input-topic", default="/cloud_registered")
    parser.add_argument("--output-topic", default="/cloud_recovery")
    parser.add_argument("--odom-topic", default="/lidar_slam/odom")
    parser.add_argument("--event-json")
    args, ros_args = parser.parse_known_args()
    return args, ros_args


def wrap_angle(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def update_cruise_since(cruise_since, now_s, speed, min_speed):
    """Update the start of a continuous, strictly-above-threshold interval."""
    if speed <= min_speed:
        return None
    return now_s if cruise_since is None else cruise_since


def continuous_cruise_duration(cruise_since, now_s):
    if cruise_since is None:
        return 0.0
    return max(0.0, now_s - cruise_since)


def trigger_invalid_reasons(
    speed,
    cruise_duration_s,
    velocity_yaw,
    min_trigger_speed,
    min_cruise_s,
):
    """Return stable machine-readable reasons for an invalid x crossing."""
    reasons = []
    if speed <= min_trigger_speed:
        reasons.append("speed_not_strictly_above_minimum")
    if cruise_duration_s + 1e-9 < min_cruise_s:
        reasons.append("insufficient_continuous_cruise")
    if velocity_yaw is None:
        reasons.append("velocity_yaw_unavailable")
    return reasons


def tangent_segment_centers(first_xy, last_xy, radius):
    """Return inclusive centres along a segment at one-diameter spacing."""
    if radius <= 0.0:
        raise ValueError("--radius-m must be positive")
    first = np.asarray(first_xy, dtype=np.float64)
    last = np.asarray(last_xy, dtype=np.float64)
    steps = float(np.linalg.norm(last - first)) / (2.0 * radius)
    rounded_steps = int(round(steps))
    if rounded_steps < 1:
        raise ValueError("each wall segment must be at least one diameter long")
    if not math.isclose(steps, rounded_steps, rel_tol=0.0, abs_tol=1e-7):
        raise ValueError(
            "segment length must be an integer multiple of the cylinder diameter"
        )
    return np.linspace(first, last, rounded_steps + 1)


def recovery_u_centers(
    trigger_x, front_forward, rear_forward, half_width, side, radius
):
    """Build a mirrored rear-open U pocket in the nominal velocity frame."""
    if front_forward <= 0.0:
        raise ValueError("--front-forward-m must be positive")
    if rear_forward >= 0.0:
        raise ValueError("--rear-forward-m must be negative")
    if half_width <= 0.0:
        raise ValueError("--half-width-m must be positive")
    sign = 1.0 if side == "left" else -1.0
    front_x = trigger_x + front_forward
    rear_x = trigger_x + rear_forward
    short_endpoint = np.array(
        [rear_x, sign * half_width], dtype=np.float64
    )
    front_short = np.array(
        [front_x, sign * half_width], dtype=np.float64
    )
    front_long = np.array(
        [front_x, -sign * half_width], dtype=np.float64
    )
    long_endpoint = np.array(
        [rear_x, -sign * half_width], dtype=np.float64
    )
    short_side = tangent_segment_centers(
        short_endpoint, front_short, radius
    )
    front = tangent_segment_centers(front_short, front_long, radius)
    long_side = tangent_segment_centers(front_long, long_endpoint, radius)
    centers = np.vstack((short_side, front[1:], long_side[1:]))
    blocker = np.array([front_x, 0.0], dtype=np.float64)
    return (
        centers,
        (short_side, front, long_side),
        blocker,
        short_endpoint,
        long_endpoint,
    )


def validate_u_geometry(
    args, centers, segments, blocker, short_endpoint, long_endpoint
):
    """Validate tangent spacing, sensing range, and hidden rear endpoints."""
    if args.horizon_m <= 0.0:
        raise ValueError("--horizon-m must be positive")
    trigger = np.array([args.trigger_x, 0.0], dtype=np.float64)
    blocker_matches = np.all(
        np.isclose(centers, blocker, atol=1e-7), axis=1
    )
    if int(blocker_matches.sum()) != 1:
        raise ValueError("the front blocker must be included exactly once")
    if np.linalg.norm(blocker - trigger) + args.radius_m > args.horizon_m:
        raise ValueError("the front blocker is outside the sensing horizon")

    endpoint_inner_edges = {}
    for label, endpoint in (
        ("short", short_endpoint),
        ("long", long_endpoint),
    ):
        delta = endpoint - trigger
        distance = float(np.linalg.norm(delta))
        if distance + args.radius_m > args.horizon_m:
            raise ValueError(label + " rear endpoint is outside the horizon")
        bearing = abs(math.atan2(delta[1], delta[0]))
        angular_radius = math.asin(min(1.0, args.radius_m / distance))
        inner_edge_deg = math.degrees(bearing - angular_radius)
        if inner_edge_deg <= FORWARD_HALF_ANGLE_DEG:
            raise ValueError(
                label + " rear endpoint is not outside the velocity sector"
            )
        endpoint_inner_edges[label] = inner_edge_deg

    for segment in segments:
        spacing = np.linalg.norm(np.diff(segment, axis=0), axis=1)
        if not np.allclose(
            spacing, 2.0 * args.radius_m, rtol=0.0, atol=1e-7
        ):
            raise ValueError("U-pocket cylinders are not tangent")
    return (
        endpoint_inner_edges["short"],
        endpoint_inner_edges["long"],
    )


def transform_xy(local_xy, world_origin_xy, yaw):
    """Rigidly transform velocity-frame xy coordinates into world xy."""
    local = np.asarray(local_xy, dtype=np.float64)
    origin = np.asarray(world_origin_xy, dtype=np.float64)
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    return local @ rotation.T + origin


def cylinder_surface_points(
    centers, radius, height, point_spacing, z_spacing
):
    """Sample the outer surfaces of all vertical cylinders as xyz points."""
    if min(height, point_spacing, z_spacing) <= 0.0:
        raise ValueError(
            "--height-m, --point-spacing-m, and --z-spacing-m must be positive"
        )
    circumference = 2.0 * math.pi * radius
    n_theta = max(16, int(math.ceil(circumference / point_spacing)))
    n_z_intervals = max(1, int(math.ceil(height / z_spacing)))
    theta = np.linspace(0.0, 2.0 * math.pi, n_theta, endpoint=False)
    z = np.linspace(0.0, height, n_z_intervals + 1)
    theta_grid, z_grid = np.meshgrid(theta, z)
    local_x = radius * np.cos(theta_grid.ravel())
    local_y = radius * np.sin(theta_grid.ravel())
    local_z = z_grid.ravel()

    points_per_cylinder = local_x.size
    points = np.empty((len(centers) * points_per_cylinder, 3), dtype=np.float32)
    for index, center in enumerate(centers):
        block = slice(
            index * points_per_cylinder, (index + 1) * points_per_cylinder
        )
        points[block, 0] = center[0] + local_x
        points[block, 1] = center[1] + local_y
        points[block, 2] = local_z
    return points


class RecoveryScenario(Node):
    def __init__(self, args):
        super().__init__("native_recovery_scenario")
        self.args = args
        if min(
            args.min_trigger_speed,
            args.min_cruise_s,
            args.max_trigger_abs_y,
            args.max_trigger_velocity_yaw_deg,
        ) < 0.0:
            raise ValueError("trigger validation thresholds must be non-negative")
        if args.max_trigger_velocity_yaw_deg > 180.0:
            raise ValueError(
                "--max-trigger-velocity-yaw-deg must not exceed 180"
            )
        (
            self.nominal_centers,
            self.nominal_segments,
            nominal_blocker,
            nominal_short_endpoint,
            nominal_long_endpoint,
        ) = recovery_u_centers(
            args.trigger_x,
            args.front_forward_m,
            args.rear_forward_m,
            args.half_width_m,
            args.side,
            args.radius_m,
        )
        (
            self.short_inner_edge_deg,
            self.long_inner_edge_deg,
        ) = validate_u_geometry(
            args,
            self.nominal_centers,
            self.nominal_segments,
            nominal_blocker,
            nominal_short_endpoint,
            nominal_long_endpoint,
        )
        nominal_origin = np.array([args.trigger_x, 0.0], dtype=np.float64)
        self.local_centers = self.nominal_centers - nominal_origin
        self.local_blocker = nominal_blocker - nominal_origin
        self.local_short_endpoint = nominal_short_endpoint - nominal_origin
        self.local_long_endpoint = nominal_long_endpoint - nominal_origin
        self.local_wall_points = cylinder_surface_points(
            self.local_centers,
            args.radius_m,
            args.height_m,
            args.point_spacing_m,
            args.z_spacing_m,
        )
        self.world_centers = None
        self.wall_points = None

        self.position = None
        self.speed = 0.0
        self.yaw = 0.0
        self.velocity_yaw = None
        self.cruise_since = None
        self.cruise_qualified = False
        self.max_cruise_duration_s = 0.0
        self.spawned = False
        self.trigger_evaluated = False
        self.trigger_invalid = False
        self.frames = 0
        self.injected_frames = 0
        self.last_visible_points = 0
        self.layout_warning_emitted = False

        self.create_subscription(
            PointCloud2,
            args.input_topic,
            self.cloud_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Odometry,
            args.odom_topic,
            self.odom_callback,
            qos_profile_sensor_data,
        )
        self.cloud_pub = self.create_publisher(
            PointCloud2, args.output_topic, qos_profile_sensor_data
        )
        self.create_timer(5.0, self.report)

        self.get_logger().info(
            "recovery U-pocket armed: side=%s, trigger x>=%.2f m after "
            ">%.2f m/s for %.2f s; velocity-frame front=(%.2f, 0.00), "
            "rear endpoints=(%.2f, %.2f)/(%.2f, %.2f) "
            "(%d tangent cylinders), endpoint inner edges=%.2f/%.2f deg"
            % (
                args.side,
                args.trigger_x,
                args.min_trigger_speed,
                args.min_cruise_s,
                self.local_blocker[0],
                self.local_long_endpoint[0],
                self.local_long_endpoint[1],
                self.local_short_endpoint[0],
                self.local_short_endpoint[1],
                len(self.local_centers),
                self.short_inner_edge_deg,
                self.long_inner_edge_deg,
            )
        )

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        v = msg.twist.twist.linear
        self.position = np.array([p.x, p.y, p.z], dtype=np.float64)
        self.speed = math.hypot(v.x, v.y)
        self.velocity_yaw = (
            math.atan2(v.y, v.x) if self.speed > 1e-9 else None
        )
        self.yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        now_s = self.now()
        self.cruise_since = update_cruise_since(
            self.cruise_since,
            now_s,
            self.speed,
            self.args.min_trigger_speed,
        )
        cruise_duration_s = continuous_cruise_duration(
            self.cruise_since, now_s
        )
        self.max_cruise_duration_s = max(
            self.max_cruise_duration_s, cruise_duration_s
        )
        if cruise_duration_s >= self.args.min_cruise_s:
            self.cruise_qualified = True
        if not self.trigger_evaluated and p.x >= self.args.trigger_x:
            self.trigger_evaluated = True
            self.evaluate_trigger(now_s)

    def evaluate_trigger(self, now_s):
        cruise_duration_s = self.max_cruise_duration_s
        invalid_reasons = trigger_invalid_reasons(
            self.speed,
            cruise_duration_s,
            self.velocity_yaw,
            self.args.min_trigger_speed,
            self.args.min_cruise_s,
        )
        valid_spawn = not invalid_reasons
        world_geometry = self.transform_trigger_geometry()
        if valid_spawn:
            self.materialize_wall(world_geometry)
        event = self.make_trigger_event(
            now_s,
            valid_spawn,
            invalid_reasons,
            cruise_duration_s,
            world_geometry,
        )
        if valid_spawn:
            self.spawn(event)
        else:
            self.reject_spawn(event)

    def transform_trigger_geometry(self):
        if self.velocity_yaw is None:
            return None
        origin = self.position[:2]
        return {
            "centers": transform_xy(
                self.local_centers, origin, self.velocity_yaw
            ),
            "blocker": transform_xy(
                self.local_blocker, origin, self.velocity_yaw
            ),
            "short_endpoint": transform_xy(
                self.local_short_endpoint, origin, self.velocity_yaw
            ),
            "long_endpoint": transform_xy(
                self.local_long_endpoint, origin, self.velocity_yaw
            ),
        }

    def materialize_wall(self, world_geometry):
        self.world_centers = world_geometry["centers"]
        self.wall_points = self.local_wall_points.copy()
        self.wall_points[:, :2] = transform_xy(
            self.local_wall_points[:, :2],
            self.position[:2],
            self.velocity_yaw,
        )

    def make_trigger_event(
        self,
        now_s,
        valid_spawn,
        invalid_reasons,
        cruise_duration_s,
        world_geometry,
    ):
        event_time_s = round(now_s, 6)
        event_wall_time_s = round(time.time(), 6)
        velocity_yaw_deg = (
            round(math.degrees(wrap_angle(self.velocity_yaw)), 3)
            if self.velocity_yaw is not None
            else None
        )
        if world_geometry is None:
            blocker = short_endpoint = long_endpoint = (None, None)
            wall_y_min = wall_y_max = None
        else:
            blocker = world_geometry["blocker"]
            short_endpoint = world_geometry["short_endpoint"]
            long_endpoint = world_geometry["long_endpoint"]
            wall_y_min = round(
                float(world_geometry["centers"][:, 1].min()), 4
            )
            wall_y_max = round(
                float(world_geometry["centers"][:, 1].max()), 4
            )

        def rounded_coordinate(point, index):
            value = point[index]
            return None if value is None else round(float(value), 4)

        return {
            "event": (
                "recovery_wall_spawn"
                if valid_spawn
                else "recovery_spawn_invalid"
            ),
            "valid_spawn": valid_spawn,
            "invalid_reasons": list(invalid_reasons),
            "spawn_time_s": event_time_s if valid_spawn else None,
            "spawn_wall_time_s": event_wall_time_s if valid_spawn else None,
            "trigger_evaluation_time_s": event_time_s,
            "trigger_evaluation_wall_time_s": event_wall_time_s,
            "side": self.args.side,
            "trigger_threshold_x": self.args.trigger_x,
            "trigger_x": round(float(self.position[0]), 4),
            "trigger_y": round(float(self.position[1]), 4),
            "trigger_z": round(float(self.position[2]), 4),
            "trigger_yaw_deg": round(math.degrees(self.yaw), 3),
            "trigger_velocity_yaw_deg": velocity_yaw_deg,
            "trigger_speed_mps": round(self.speed, 4),
            "trigger_cruise_duration_s": round(cruise_duration_s, 6),
            "trigger_cruise_qualified": self.cruise_qualified,
            "min_trigger_speed_mps": self.args.min_trigger_speed,
            "min_cruise_s": self.args.min_cruise_s,
            "barrier_frame": "trigger_velocity",
            "max_trigger_abs_y_m": self.args.max_trigger_abs_y,
            "max_trigger_velocity_yaw_deg": (
                self.args.max_trigger_velocity_yaw_deg
            ),
            "trigger_abs_y_diagnostic_ok": (
                abs(float(self.position[1])) <= self.args.max_trigger_abs_y
            ),
            "trigger_velocity_yaw_diagnostic_ok": (
                velocity_yaw_deg is not None
                and abs(velocity_yaw_deg)
                <= self.args.max_trigger_velocity_yaw_deg
            ),
            "wall_x": rounded_coordinate(blocker, 0),
            "blocker_x": rounded_coordinate(blocker, 0),
            "blocker_y": rounded_coordinate(blocker, 1),
            "wall_y_min": wall_y_min,
            "wall_y_max": wall_y_max,
            "short_endpoint_x": rounded_coordinate(short_endpoint, 0),
            "short_endpoint_y": rounded_coordinate(short_endpoint, 1),
            "long_endpoint_x": rounded_coordinate(long_endpoint, 0),
            "long_endpoint_y": rounded_coordinate(long_endpoint, 1),
            "local_blocker_x": round(float(self.local_blocker[0]), 10),
            "local_blocker_y": round(float(self.local_blocker[1]), 10),
            "local_blocker_forward_m": round(
                float(self.local_blocker[0]), 10
            ),
            "local_short_endpoint_x": round(
                float(self.local_short_endpoint[0]), 10
            ),
            "local_short_endpoint_y": round(
                float(self.local_short_endpoint[1]), 10
            ),
            "local_short_endpoint_forward_m": round(
                float(self.local_short_endpoint[0]), 10
            ),
            "local_short_endpoint_lateral_m": round(
                float(self.local_short_endpoint[1]), 10
            ),
            "local_long_endpoint_x": round(
                float(self.local_long_endpoint[0]), 10
            ),
            "local_long_endpoint_y": round(
                float(self.local_long_endpoint[1]), 10
            ),
            "local_long_endpoint_forward_m": round(
                float(self.local_long_endpoint[0]), 10
            ),
            "local_long_endpoint_lateral_m": round(
                float(self.local_long_endpoint[1]), 10
            ),
            "short_endpoint_inner_edge_deg": round(
                self.short_inner_edge_deg, 3
            ),
            "long_endpoint_inner_edge_deg": round(
                self.long_inner_edge_deg, 3
            ),
            "wall_radius_m": self.args.radius_m,
            "wall_height_m": self.args.height_m,
            "wall_cylinder_count": len(self.local_centers),
            "wall_center_spacing_m": 2.0 * self.args.radius_m,
            "wall_point_count": len(self.local_wall_points),
            "horizon_m": self.args.horizon_m,
            "intensity": self.args.intensity,
        }

    def spawn(self, event):
        self.spawned = True
        self.write_event(event)
        print(
            "RECOVERY_WALL_SPAWN " + json.dumps(event, sort_keys=True),
            flush=True,
        )
        self.get_logger().info(
            "recovery U pocket spawned permanently at x=%.3f m "
            "(speed %.3f m/s)"
            % (self.position[0], self.speed)
        )

    def reject_spawn(self, event):
        self.trigger_invalid = True
        self.write_event(event)
        print(
            "RECOVERY_SPAWN_INVALID " + json.dumps(event, sort_keys=True),
            flush=True,
        )
        self.get_logger().error(
            "recovery spawn invalid at first x crossing: %s"
            % ", ".join(event["invalid_reasons"])
        )

    def write_event(self, event):
        if not self.args.event_json:
            return
        tmp_path = "%s.tmp.%d" % (self.args.event_json, os.getpid())
        try:
            with open(tmp_path, "w") as stream:
                json.dump(event, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_path, self.args.event_json)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def visible_wall_points(self):
        delta_xy = self.wall_points[:, :2] - self.position[:2]
        visible = np.einsum("ij,ij->i", delta_xy, delta_xy) <= (
            self.args.horizon_m**2
        )
        return self.wall_points[visible]

    def cloud_layout(self, msg):
        field_names = {field.name for field in msg.fields}
        required = {"x", "y", "z", "intensity"}
        if not required <= field_names:
            missing = ", ".join(sorted(required - field_names))
            raise ValueError("input PointCloud2 is missing fields: " + missing)
        dtype = pc2.dtype_from_fields(msg.fields, point_step=msg.point_step)
        for name in required:
            if name not in dtype.names:
                raise ValueError("unsupported multi-count PointCloud2 field: " + name)
        intensity_dtype = dtype.fields["intensity"][0]
        if np.issubdtype(intensity_dtype, np.integer):
            limits = np.iinfo(intensity_dtype)
            if not limits.min <= self.args.intensity <= limits.max:
                raise ValueError("intensity tag is outside the input field range")
        return dtype

    @staticmethod
    def flattened_input_bytes(msg):
        """Copy point records while excluding any organized-cloud row padding."""
        packed_row_bytes = int(msg.width) * int(msg.point_step)
        raw = memoryview(msg.data)
        if msg.height == 1 and msg.row_step == packed_row_bytes:
            return raw.tobytes()
        flattened = bytearray(int(msg.width) * int(msg.height) * msg.point_step)
        destination = 0
        for row in range(int(msg.height)):
            source = row * int(msg.row_step)
            flattened[destination : destination + packed_row_bytes] = raw[
                source : source + packed_row_bytes
            ]
            destination += packed_row_bytes
        return bytes(flattened)

    def augment_cloud(self, msg, visible):
        dtype = self.cloud_layout(msg)
        synthetic = np.zeros(len(visible), dtype=dtype)
        synthetic["x"] = visible[:, 0]
        synthetic["y"] = visible[:, 1]
        synthetic["z"] = visible[:, 2]
        synthetic["intensity"] = self.args.intensity
        host_is_bigendian = sys.byteorder == "big"
        if bool(msg.is_bigendian) != host_is_bigendian:
            synthetic.byteswap(inplace=True)

        payload = array.array("B")
        payload.frombytes(self.flattened_input_bytes(msg))
        payload.frombytes(synthetic.tobytes())
        original_count = int(msg.width) * int(msg.height)
        width = original_count + len(synthetic)

        output = PointCloud2()
        output.header = msg.header
        output.height = 1
        output.width = width
        output.fields = msg.fields
        output.is_bigendian = msg.is_bigendian
        output.point_step = msg.point_step
        output.row_step = msg.point_step * width
        output.is_dense = msg.is_dense
        output.data = payload
        return output

    def cloud_callback(self, msg):
        self.frames += 1
        if not self.spawned or self.position is None:
            self.cloud_pub.publish(msg)
            return

        visible = self.visible_wall_points()
        self.last_visible_points = len(visible)
        if visible.size == 0:
            self.cloud_pub.publish(msg)
            return
        try:
            output = self.augment_cloud(msg, visible)
        except Exception as exc:
            if not self.layout_warning_emitted:
                self.get_logger().warning(
                    "cannot preserve input cloud layout for injection: %s" % exc
                )
                self.layout_warning_emitted = True
            self.cloud_pub.publish(msg)
            return
        self.cloud_pub.publish(output)
        self.injected_frames += 1

    def report(self):
        state = (
            "invalid"
            if self.trigger_invalid
            else "spawned" if self.spawned else "armed"
        )
        position_x = float("nan") if self.position is None else self.position[0]
        print(
            "[native_recovery] state=%s side=%s x=%.2f frames=%d "
            "injected=%d visible_points=%d"
            % (
                state,
                self.args.side,
                position_x,
                self.frames,
                self.injected_frames,
                self.last_visible_points,
            ),
            flush=True,
        )


def main():
    args, ros_args = parse_args()
    rclpy.init(args=ros_args)
    node = RecoveryScenario(args)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
