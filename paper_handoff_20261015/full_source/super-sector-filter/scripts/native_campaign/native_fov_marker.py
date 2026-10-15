#!/usr/bin/env python3
"""Visualize the horizontal field of view used by native_sector.py.

The marker follows the filter's published full-open state, so adaptive and
trigger modes visibly switch between their sector and 360-degree phases.
"""
import argparse
import math

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import ColorRGBA
from std_msgs.msg import Bool
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray

MODE_COLOR = {
    "full": (0.2, 0.6, 1.0),      # blue
    "sector": (1.0, 0.55, 0.0),   # orange
    "velocity": (0.65, 0.35, 1.0), # purple
    "adaptive": (0.2, 0.9, 0.3),  # green
    "trigger": (1.0, 0.25, 0.25),  # red
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("full", "sector", "velocity", "adaptive", "trigger")
    )
    parser.add_argument("--radius", type=float, default=15.0)
    parser.add_argument("--half-angle-deg", type=float, default=60.0)
    parser.add_argument("--topic", default="/sector/fov_marker")
    parser.add_argument("--rate-hz", type=float, default=10.0)
    parser.add_argument("--segments", type=int, default=48)
    args, _ = parser.parse_known_args()
    return args


class FovMarker(Node):
    def __init__(self, args):
        super().__init__("native_fov_marker")
        self.args = args
        self.drone = None
        self.yaw = 0.0
        self.velocity_yaw = None
        self.full_open = args.mode == "full"
        self.create_subscription(
            Odometry, "/lidar_slam/odom", self.odom_callback, qos_profile_sensor_data
        )
        self.create_subscription(Bool, "/sector/full_open", self.full_open_callback, 1)
        self.pub = self.create_publisher(MarkerArray, args.topic, 1)
        self.create_timer(1.0 / args.rate_hz, self.publish_marker)
        self.get_logger().info(
            "fov marker: mode=%s radius=%.1fm half_angle=%.0fdeg -> %s"
            % (args.mode, args.radius, args.half_angle_deg, args.topic)
        )

    def full_open_callback(self, msg):
        self.full_open = bool(msg.data)

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.drone = np.array([p.x, p.y, p.z], dtype=np.float64)
        self.yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        v = msg.twist.twist.linear
        update_v = 1.5 if self.args.mode in ("velocity", "adaptive") else 0.2
        if math.hypot(v.x, v.y) > update_v:
            self.velocity_yaw = math.atan2(v.y, v.x)

    def arc_angles(self):
        if self.full_open:
            return np.linspace(-math.pi, math.pi, self.args.segments + 1)
        center = (
            self.velocity_yaw
            if (
                self.args.mode in ("adaptive", "velocity")
                and self.velocity_yaw is not None
            )
            else self.yaw
        )
        half = math.radians(self.args.half_angle_deg)
        return center + np.linspace(-half, half, self.args.segments + 1)

    def publish_marker(self):
        if self.drone is None:
            return
        color = MODE_COLOR[self.args.mode]
        cx, cy, cz = float(self.drone[0]), float(self.drone[1]), 0.05
        angles = self.arc_angles()
        r = self.args.radius
        rim = [
            Point(x=cx + r * math.cos(a), y=cy + r * math.sin(a), z=cz)
            for a in angles
        ]
        center_pt = Point(x=cx, y=cy, z=cz)

        fill = Marker()
        fill.header.frame_id = "world"
        fill.header.stamp = self.get_clock().now().to_msg()
        fill.ns = "fov_fill"
        fill.id = 0
        fill.type = Marker.TRIANGLE_LIST
        fill.action = Marker.ADD
        fill.scale.x = fill.scale.y = fill.scale.z = 1.0
        fill.color = ColorRGBA(r=color[0], g=color[1], b=color[2], a=0.18)
        fill.pose.orientation.w = 1.0
        for i in range(len(rim) - 1):
            fill.points += [center_pt, rim[i], rim[i + 1]]

        outline = Marker()
        outline.header.frame_id = "world"
        outline.header.stamp = fill.header.stamp
        outline.ns = "fov_outline"
        outline.id = 1
        outline.type = Marker.LINE_STRIP
        outline.action = Marker.ADD
        outline.scale.x = 0.08
        outline.color = ColorRGBA(r=color[0], g=color[1], b=color[2], a=0.9)
        outline.pose.orientation.w = 1.0
        outline.points = list(rim) if self.full_open else [center_pt] + list(rim) + [center_pt]

        arr = MarkerArray()
        arr.markers = [fill, outline]
        self.pub.publish(arr)


def main():
    args = parse_args()
    rclpy.init()
    rclpy.spin(FovMarker(args))


if __name__ == "__main__":
    main()
