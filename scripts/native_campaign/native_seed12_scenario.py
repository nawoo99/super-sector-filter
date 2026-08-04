#!/usr/bin/env python3
"""Inject a deterministic late-appearing obstacle for the seed12 experiment."""

import argparse
import csv
import json
import math
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
from visualization_msgs.msg import Marker


def wrap_angle(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-topic", default="/cloud_registered")
    parser.add_argument("--output-topic", default="/cloud_seed12")
    parser.add_argument("--event-json")
    parser.add_argument("--trace-csv")
    parser.add_argument("--speed-min", type=float, default=2.0)
    parser.add_argument("--mismatch-deg", type=float, default=60.0)
    parser.add_argument("--hold-s", type=float, default=0.15)
    parser.add_argument("--lead-m", type=float, default=2.5)
    parser.add_argument("--bearing-offset-deg", type=float, default=7.0)
    parser.add_argument("--fixed-trap-x", type=float)
    parser.add_argument("--fixed-trap-y", type=float)
    parser.add_argument("--prediction-s", type=float, default=0.0)
    parser.add_argument("--nudge-outside-sector", action="store_true")
    parser.add_argument("--nudge-margin-deg", type=float, default=1.0)
    parser.add_argument("--max-nudge-deg", type=float, default=25.0)
    parser.add_argument("--trigger-distance-min", type=float, default=0.0)
    parser.add_argument("--trigger-distance-max", type=float, default=float("inf"))
    parser.add_argument("--sector-half-deg", type=float, default=60.0)
    parser.add_argument("--adaptive-half-deg", type=float, default=60.0)
    parser.add_argument("--radius-m", type=float, default=0.25)
    parser.add_argument("--rough-trap-count", type=int, default=1)
    parser.add_argument("--rough-trap-start-m", type=float, default=0.0)
    parser.add_argument("--rough-trap-spacing-m", type=float, default=0.35)
    parser.add_argument("--height-m", type=float, default=3.0)
    parser.add_argument("--horizon-m", type=float, default=15.0)
    parser.add_argument("--point-spacing-m", type=float, default=0.05)
    parser.add_argument("--z-spacing-m", type=float, default=0.10)
    parser.add_argument("--trap-intensity", type=float, default=12012.0)
    args, ros_args = parser.parse_known_args()
    return args, ros_args


class Seed12Scenario(Node):
    def __init__(self, args):
        super().__init__("native_seed12_scenario")
        self.args = args
        self.position = None
        self.yaw = 0.0
        self.velocity = np.zeros(2, dtype=np.float64)
        self.speed = 0.0
        self.velocity_yaw = None
        self.command = None
        self.trigger_since = None
        self.trigger_geometry = None
        self.pending_trap_center = None
        self.spawned = False
        fixed_values = (args.fixed_trap_x, args.fixed_trap_y)
        if (fixed_values[0] is None) != (fixed_values[1] is None):
            raise ValueError("--fixed-trap-x and --fixed-trap-y must be used together")
        self.fixed_trap_center = (
            np.array(fixed_values, dtype=np.float64)
            if fixed_values[0] is not None
            else None
        )
        self.trap_center = None
        self.trap_centers = None
        self.trap_points = None
        self.frames = 0
        self.injected_frames = 0
        self.max_mismatch_deg = 0.0
        self.trace_stream = None
        self.trace_writer = None
        if args.trace_csv:
            self.trace_stream = open(args.trace_csv, "w", newline="", buffering=1)
            self.trace_writer = csv.DictWriter(
                self.trace_stream,
                fieldnames=(
                    "time_s",
                    "x",
                    "y",
                    "yaw_deg",
                    "velocity_yaw_deg",
                    "mismatch_deg",
                    "speed_mps",
                    "candidate_x",
                    "candidate_y",
                    "candidate_distance_m",
                    "candidate_body_relative_deg",
                    "candidate_velocity_relative_deg",
                    "candidate_angular_radius_deg",
                    "fully_outside_sector",
                    "fully_inside_adaptive",
                    "qualifies",
                    "cmd_position_x",
                    "cmd_position_y",
                    "cmd_velocity_x",
                    "cmd_velocity_y",
                    "cmd_acceleration_x",
                    "cmd_acceleration_y",
                    "cmd_jerk_x",
                    "cmd_jerk_y",
                ),
            )
            self.trace_writer.writeheader()

        self.create_subscription(
            PointCloud2, args.input_topic, self.cloud_callback, qos_profile_sensor_data
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
        self.cloud_pub = self.create_publisher(
            PointCloud2, args.output_topic, qos_profile_sensor_data
        )
        self.marker_pub = self.create_publisher(Marker, "/seed12/trap_marker", 1)
        self.create_timer(5.0, self.report)

        if self.fixed_trap_center is not None:
            condition = (
                "fixed trap=(%.2f, %.2f), distance %.1f..%.1f m, "
                "adaptive-only geometry"
                % (
                    self.fixed_trap_center[0],
                    self.fixed_trap_center[1],
                    args.trigger_distance_min,
                    args.trigger_distance_max,
                )
            )
        elif args.prediction_s > 0.0:
            condition = (
                "%.2f s PVAJ prediction, distance %.1f..%.1f m, "
                "adaptive-only geometry"
                % (
                    args.prediction_s,
                    args.trigger_distance_min,
                    args.trigger_distance_max,
                )
            )
        else:
            condition = "|yaw-vyaw|>=%.1f deg" % args.mismatch_deg
        self.get_logger().info(
            "seed12 armed: speed>=%.2f m/s, %s for %.2f s"
            % (args.speed_min, condition, args.hold_s)
        )

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def command_callback(self, msg):
        self.command = {
            "position": np.array([msg.position.x, msg.position.y], dtype=np.float64),
            "velocity": np.array([msg.velocity.x, msg.velocity.y], dtype=np.float64),
            "acceleration": np.array(
                [msg.acceleration.x, msg.acceleration.y], dtype=np.float64
            ),
            "jerk": np.array([msg.jerk.x, msg.jerk.y], dtype=np.float64),
        }

    def candidate_trap_center(self):
        if self.fixed_trap_center is not None:
            return self.fixed_trap_center
        if self.args.prediction_s <= 0.0 or self.command is None:
            return None
        t = self.args.prediction_s
        return (
            self.command["position"]
            + self.command["velocity"] * t
            + 0.5 * self.command["acceleration"] * t**2
            + self.command["jerk"] * t**3 / 6.0
        )

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        v = msg.twist.twist.linear

        self.position = np.array([p.x, p.y, p.z], dtype=np.float64)
        self.yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        self.velocity[:] = (v.x, v.y)
        self.speed = float(np.linalg.norm(self.velocity))
        if self.speed > 0.2:
            self.velocity_yaw = math.atan2(v.y, v.x)

        if self.spawned or self.velocity_yaw is None:
            return

        signed_mismatch = wrap_angle(self.velocity_yaw - self.yaw)
        mismatch = abs(signed_mismatch)
        if self.speed >= self.args.speed_min:
            self.max_mismatch_deg = max(
                self.max_mismatch_deg, math.degrees(mismatch)
            )
        candidate = self.candidate_trap_center()
        trace_geometry = {}
        if candidate is None:
            qualifies = (
                self.speed >= self.args.speed_min
                and mismatch >= math.radians(self.args.mismatch_deg)
            )
            self.trigger_geometry = None
            self.pending_trap_center = None
        else:
            delta = candidate - self.position[:2]
            distance = float(np.linalg.norm(delta))
            bearing = math.atan2(delta[1], delta[0])
            body_relative = wrap_angle(bearing - self.yaw)
            velocity_relative = wrap_angle(bearing - self.velocity_yaw)
            angular_radius = math.asin(
                min(1.0, self.args.radius_m / max(distance, self.args.radius_m))
            )
            predicted_center = np.array(candidate, dtype=np.float64)
            nudge = 0.0
            if self.args.nudge_outside_sector:
                target_body_angle = (
                    math.radians(
                        self.args.sector_half_deg + self.args.nudge_margin_deg
                    )
                    + angular_radius
                )
                required_nudge = max(
                    0.0, target_body_angle - abs(body_relative)
                )
                if required_nudge <= math.radians(self.args.max_nudge_deg):
                    direction_sign = math.copysign(
                        1.0,
                        body_relative
                        if abs(body_relative) > 1e-6
                        else signed_mismatch,
                    )
                    nudge = direction_sign * required_nudge
                    bearing += nudge
                    candidate = self.position[:2] + distance * np.array(
                        [math.cos(bearing), math.sin(bearing)], dtype=np.float64
                    )
                    body_relative = wrap_angle(bearing - self.yaw)
                    velocity_relative = wrap_angle(bearing - self.velocity_yaw)
            fully_outside_sector = (
                abs(body_relative) - angular_radius
                >= math.radians(self.args.sector_half_deg)
            )
            fully_inside_adaptive = (
                abs(velocity_relative) + angular_radius
                <= math.radians(self.args.adaptive_half_deg)
            )
            trace_geometry = {
                "candidate_x": float(candidate[0]),
                "candidate_y": float(candidate[1]),
                "candidate_distance_m": distance,
                "candidate_body_relative_deg": math.degrees(body_relative),
                "candidate_velocity_relative_deg": math.degrees(velocity_relative),
                "candidate_angular_radius_deg": math.degrees(angular_radius),
                "fully_outside_sector": int(fully_outside_sector),
                "fully_inside_adaptive": int(fully_inside_adaptive),
            }
            qualifies = (
                self.speed >= self.args.speed_min
                and mismatch >= math.radians(self.args.mismatch_deg)
                and self.args.trigger_distance_min <= distance
                <= self.args.trigger_distance_max
                and fully_outside_sector
                and fully_inside_adaptive
            )
            self.pending_trap_center = np.array(candidate, dtype=np.float64)
            self.trigger_geometry = {
                "trigger_trap_distance_m": round(distance, 4),
                "trigger_trap_body_relative_deg": round(
                    math.degrees(body_relative), 3
                ),
                "trigger_trap_velocity_relative_deg": round(
                    math.degrees(velocity_relative), 3
                ),
                "trigger_trap_angular_radius_deg": round(
                    math.degrees(angular_radius), 3
                ),
                "trigger_predicted_x": round(float(predicted_center[0]), 4),
                "trigger_predicted_y": round(float(predicted_center[1]), 4),
                "trigger_trap_nudge_deg": round(math.degrees(nudge), 3),
                "trigger_trap_nudge_lateral_m": round(
                    distance * math.sin(abs(nudge)), 4
                ),
            }
        self.write_trace(signed_mismatch, qualifies, trace_geometry)
        now = self.now()
        if not qualifies:
            self.trigger_since = None
            return
        if self.trigger_since is None:
            self.trigger_since = now
            return
        if now - self.trigger_since >= self.args.hold_s:
            self.spawn(signed_mismatch)

    def write_trace(self, signed_mismatch, qualifies, geometry):
        if self.trace_writer is None:
            return
        row = {
            "time_s": "%.6f" % self.now(),
            "x": "%.6f" % self.position[0],
            "y": "%.6f" % self.position[1],
            "yaw_deg": "%.6f" % math.degrees(self.yaw),
            "velocity_yaw_deg": "%.6f" % math.degrees(self.velocity_yaw),
            "mismatch_deg": "%.6f" % math.degrees(abs(signed_mismatch)),
            "speed_mps": "%.6f" % self.speed,
            "qualifies": int(qualifies),
        }
        if self.command is not None:
            row.update(
                {
                    "cmd_position_x": self.command["position"][0],
                    "cmd_position_y": self.command["position"][1],
                    "cmd_velocity_x": self.command["velocity"][0],
                    "cmd_velocity_y": self.command["velocity"][1],
                    "cmd_acceleration_x": self.command["acceleration"][0],
                    "cmd_acceleration_y": self.command["acceleration"][1],
                    "cmd_jerk_x": self.command["jerk"][0],
                    "cmd_jerk_y": self.command["jerk"][1],
                }
            )
        row.update(geometry)
        self.trace_writer.writerow(row)

    def spawn(self, signed_mismatch):
        if self.pending_trap_center is None:
            offset = math.radians(self.args.bearing_offset_deg)
            trap_bearing = self.velocity_yaw + math.copysign(
                offset, signed_mismatch
            )
            direction = np.array(
                [math.cos(trap_bearing), math.sin(trap_bearing)], dtype=np.float64
            )
            center_xy = self.position[:2] + self.args.lead_m * direction
            base_center = np.array(center_xy, dtype=np.float64)
            velocity_offset = math.copysign(
                self.args.bearing_offset_deg, signed_mismatch
            )
        else:
            base_center = self.pending_trap_center.copy()
            velocity_offset = None

        ray = base_center - self.position[:2]
        ray_norm = float(np.linalg.norm(ray))
        if ray_norm <= 1e-6:
            ray = self.velocity / max(self.speed, 1e-6)
        else:
            ray /= ray_norm
        count = max(1, self.args.rough_trap_count)
        offsets = (
            self.args.rough_trap_start_m
            + np.arange(count, dtype=np.float64) * self.args.rough_trap_spacing_m
        )
        self.trap_centers = base_center + offsets[:, None] * ray
        self.trap_center = self.trap_centers[0]
        self.trap_points = self.make_cylinder_points()
        self.spawned = True

        event = {
            "spawn_time_s": round(self.now(), 6),
            "spawn_wall_time_s": round(time.time(), 6),
            "trigger_x": round(float(self.position[0]), 4),
            "trigger_y": round(float(self.position[1]), 4),
            "trigger_z": round(float(self.position[2]), 4),
            "trigger_yaw_deg": round(math.degrees(self.yaw), 3),
            "trigger_velocity_yaw_deg": round(
                math.degrees(self.velocity_yaw), 3
            ),
            "trigger_mismatch_deg": round(math.degrees(abs(signed_mismatch)), 3),
            "trigger_signed_mismatch_deg": round(
                math.degrees(signed_mismatch), 3
            ),
            "trigger_speed_mps": round(self.speed, 4),
            "trap_x": round(float(self.trap_center[0]), 4),
            "trap_y": round(float(self.trap_center[1]), 4),
            "trap_centers": [
                [round(float(center[0]), 4), round(float(center[1]), 4)]
                for center in self.trap_centers
            ],
            "trap_count": count,
            "trap_spacing_m": self.args.rough_trap_spacing_m,
            "trap_start_offset_m": self.args.rough_trap_start_m,
            "trap_first_distance_m": round(
                float(np.linalg.norm(self.trap_center - self.position[:2])), 4
            ),
            "trap_last_distance_m": round(
                float(np.linalg.norm(self.trap_centers[-1] - self.position[:2])),
                4,
            ),
            "trap_radius_m": self.args.radius_m,
            "trap_lead_m": (
                self.args.lead_m if self.pending_trap_center is None else None
            ),
            "trap_velocity_offset_deg": velocity_offset,
            "trap_prediction_s": (
                self.args.prediction_s if self.args.prediction_s > 0.0 else None
            ),
        }
        if self.trigger_geometry is not None:
            event.update(self.trigger_geometry)
        self.write_event(event)
        print("SEED12_SPAWN " + json.dumps(event, sort_keys=True), flush=True)
        self.publish_marker()

    def make_cylinder_points(self):
        circumference = 2.0 * math.pi * self.args.radius_m
        n_theta = max(16, int(math.ceil(circumference / self.args.point_spacing_m)))
        n_z = max(2, int(math.ceil(self.args.height_m / self.args.z_spacing_m)))
        theta = np.linspace(0.0, 2.0 * math.pi, n_theta, endpoint=False)
        z = np.linspace(0.0, self.args.height_m, n_z + 1)
        theta_grid, z_grid = np.meshgrid(theta, z)
        cylinders = []
        for center in self.trap_centers:
            points = np.empty((theta_grid.size, 4), dtype=np.float32)
            points[:, 0] = (
                center[0] + self.args.radius_m * np.cos(theta_grid.ravel())
            )
            points[:, 1] = (
                center[1] + self.args.radius_m * np.sin(theta_grid.ravel())
            )
            points[:, 2] = z_grid.ravel()
            points[:, 3] = self.args.trap_intensity
            cylinders.append(points)
        return np.concatenate(cylinders, axis=0)

    def cloud_callback(self, msg):
        self.frames += 1
        if not self.spawned or self.position is None:
            self.cloud_pub.publish(msg)
            return

        try:
            raw = pc2.read_points_numpy(
                msg, field_names=("x", "y", "z", "intensity"), skip_nans=True
            )
            raw = raw.reshape(-1, 4)
        except Exception as exc:
            self.get_logger().warning("cannot decode cloud: %s" % exc)
            self.cloud_pub.publish(msg)
            return

        delta = self.trap_points[:, :3] - self.position
        visible = np.einsum("ij,ij->i", delta, delta) <= self.args.horizon_m**2
        trap = self.trap_points[visible]
        if trap.size == 0:
            self.cloud_pub.publish(msg)
            return

        augmented = np.concatenate((raw, trap), axis=0) if raw.size else trap
        self.cloud_pub.publish(pc2.create_cloud(msg.header, msg.fields, augmented))
        self.injected_frames += 1

    def publish_marker(self):
        for index, center in enumerate(self.trap_centers):
            marker = Marker()
            marker.header.frame_id = "world"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "seed12_dynamic_trap"
            marker.id = 1200 + index
            marker.type = Marker.CYLINDER
            marker.action = Marker.ADD
            marker.pose.position.x = float(center[0])
            marker.pose.position.y = float(center[1])
            marker.pose.position.z = self.args.height_m / 2.0
            marker.pose.orientation.w = 1.0
            marker.scale.x = 2.0 * self.args.radius_m
            marker.scale.y = 2.0 * self.args.radius_m
            marker.scale.z = self.args.height_m
            marker.color.r = 0.95
            marker.color.g = 0.15
            marker.color.b = 0.10
            marker.color.a = 0.9
            self.marker_pub.publish(marker)

    def write_event(self, event):
        if not self.args.event_json:
            return
        tmp_path = self.args.event_json + ".tmp"
        with open(tmp_path, "w") as stream:
            json.dump(event, stream, indent=2, sort_keys=True)
        os.replace(tmp_path, self.args.event_json)

    def report(self):
        state = "spawned" if self.spawned else "armed"
        print(
            "[native_seed12] state=%s frames=%d injected=%d max_mismatch=%.1fdeg"
            % (
                state,
                self.frames,
                self.injected_frames,
                self.max_mismatch_deg,
            ),
            flush=True,
        )
        if self.spawned:
            self.publish_marker()


ARGS, ROS_ARGS = parse_args()
rclpy.init(args=[__file__] + ROS_ARGS)
rclpy.spin(Seed12Scenario(ARGS))
