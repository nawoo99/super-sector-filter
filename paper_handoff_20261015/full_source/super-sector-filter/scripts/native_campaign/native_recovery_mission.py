#!/usr/bin/env python3
"""Controlled seed14/15 recovery mission, independent of filter state."""

import argparse
import json
import math
import os
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)


def recovery_goals(
    side,
    approach_x=20.0,
    approach_y=0.0,
    final_x=40.0,
    final_y_bias=1.0,
    height=1.5,
):
    """Return mirrored (approach, final) xyz goals without ROS state."""
    if side not in ("left", "right"):
        raise ValueError("side must be 'left' or 'right'")
    if final_y_bias < 0.0:
        raise ValueError("final_y_bias must be non-negative")
    sign = 1.0 if side == "left" else -1.0
    approach = (float(approach_x), float(approach_y), float(height))
    final = (float(final_x), sign * float(final_y_bias), float(height))
    return approach, final


def parse_args():
    parser = argparse.ArgumentParser(
        description="Publish a controlled approach, hold, and recovery goal sequence."
    )
    parser.add_argument("--side", choices=("left", "right"), default="left")
    parser.add_argument("--approach-x", type=float, default=20.0)
    parser.add_argument("--approach-y", type=float, default=0.0)
    parser.add_argument("--final-x", type=float, default=40.0)
    parser.add_argument("--final-y-bias", type=float, default=1.0)
    parser.add_argument("--height", type=float, default=1.5)
    parser.add_argument("--start-delay-s", type=float, default=3.0)
    parser.add_argument("--approach-radius-m", type=float, default=0.4)
    parser.add_argument("--hold-low-speed-s", type=float, default=1.6)
    parser.add_argument("--low-speed-v", type=float, default=0.6)
    parser.add_argument("--event-json")
    parser.add_argument("--odom-topic", default="/lidar_slam/odom")
    parser.add_argument("--goal-topic", default="/planning/click_goal")
    args, ros_args = parser.parse_known_args()
    if args.final_y_bias < 0.0:
        parser.error("--final-y-bias must be non-negative")
    if args.height <= 0.0:
        parser.error("--height must be positive")
    if args.start_delay_s < 0.0:
        parser.error("--start-delay-s must be non-negative")
    if args.approach_radius_m <= 0.0:
        parser.error("--approach-radius-m must be positive")
    if args.hold_low_speed_s <= 0.0:
        parser.error("--hold-low-speed-s must be positive")
    if args.low_speed_v <= 0.0:
        parser.error("--low-speed-v must be positive")
    return args, ros_args


class RecoveryMission(Node):
    WAIT = "wait"
    APPROACH = "approach"
    HOLD = "hold"
    FINAL = "final"

    def __init__(self, args):
        super().__init__("native_recovery_mission")
        self.args = args
        self.approach_goal, self.final_goal = recovery_goals(
            args.side,
            args.approach_x,
            args.approach_y,
            args.final_x,
            args.final_y_bias,
            args.height,
        )
        self.phase = self.WAIT
        self.position = None
        self.speed = None
        self.first_odom_time_s = None
        self.last_odom_time_s = None
        self.low_speed_since_s = None
        self.event = {
            "side": args.side,
            "phase": self.phase,
            "approach_goal": self.goal_record(self.approach_goal),
            "final_goal": self.goal_record(self.final_goal),
            "start_delay_s": args.start_delay_s,
            "approach_radius_m": args.approach_radius_m,
            "hold_low_speed_s": args.hold_low_speed_s,
            "low_speed_v": args.low_speed_v,
        }

        self.create_subscription(
            Odometry, args.odom_topic, self.odom_callback, qos_profile_sensor_data
        )
        # Match waypoint_mission's goal publisher: best-effort, volatile,
        # keep-last(100).  SUPER's subscriber is best-effort keep-last(1).
        goal_qos = QoSProfile(depth=100)
        goal_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        goal_qos.history = HistoryPolicy.KEEP_LAST
        goal_qos.durability = DurabilityPolicy.VOLATILE
        self.goal_pub = self.create_publisher(
            PoseStamped, args.goal_topic, goal_qos
        )
        self.create_timer(0.1, self.tick)
        self.get_logger().info(
            "recovery mission side=%s approach=(%.2f, %.2f) final=(%.2f, %.2f)"
            % (
                args.side,
                self.approach_goal[0],
                self.approach_goal[1],
                self.final_goal[0],
                self.final_goal[1],
            )
        )

    @staticmethod
    def goal_record(goal):
        return {"x": goal[0], "y": goal[1], "z": goal[2]}

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def odom_callback(self, msg):
        now_s = self.now()
        position = msg.pose.pose.position
        velocity = msg.twist.twist.linear
        self.position = (
            float(position.x),
            float(position.y),
            float(position.z),
        )
        self.speed = math.hypot(velocity.x, velocity.y)
        self.last_odom_time_s = now_s
        if self.first_odom_time_s is None:
            self.first_odom_time_s = now_s
            self.get_logger().info(
                "first odom; approach starts after %.2f s" % self.args.start_delay_s
            )

        if self.phase == self.APPROACH and self.approach_distance() <= (
            self.args.approach_radius_m
        ):
            self.enter_hold(now_s)

        if self.phase == self.HOLD:
            self.update_low_speed(now_s)

    def tick(self):
        now_s = self.now()
        if (
            self.phase == self.WAIT
            and self.first_odom_time_s is not None
            and now_s - self.first_odom_time_s >= self.args.start_delay_s
        ):
            self.start_approach(now_s)

        if self.phase == self.APPROACH:
            if self.approach_distance() <= self.args.approach_radius_m:
                self.enter_hold(now_s)
            self.publish_goal(self.approach_goal)
        elif self.phase == self.HOLD:
            self.publish_goal(self.approach_goal)
        elif self.phase == self.FINAL:
            self.publish_goal(self.final_goal)

    def approach_distance(self):
        if self.position is None:
            return math.inf
        return math.hypot(
            self.position[0] - self.approach_goal[0],
            self.position[1] - self.approach_goal[1],
        )

    def start_approach(self, now_s):
        self.phase = self.APPROACH
        self.record_transition("approach_start", now_s)
        self.write_event()
        self.print_transition("APPROACH", self.approach_goal)

    def enter_hold(self, now_s):
        if self.phase != self.APPROACH:
            return
        self.phase = self.HOLD
        self.low_speed_since_s = None
        self.record_transition(
            "hold_start", now_s, distance_m=self.approach_distance()
        )
        self.write_event()
        self.print_transition("HOLD", self.approach_goal)

    def update_low_speed(self, now_s):
        if self.speed is None or self.speed >= self.args.low_speed_v:
            self.low_speed_since_s = None
            return
        if self.low_speed_since_s is None:
            self.low_speed_since_s = now_s
            return
        duration_s = now_s - self.low_speed_since_s
        if duration_s >= self.args.hold_low_speed_s:
            self.release_final(now_s, duration_s)

    def release_final(self, now_s, low_speed_duration_s):
        if self.phase != self.HOLD:
            return
        self.phase = self.FINAL
        self.record_transition(
            "release",
            now_s,
            low_speed_duration_s=low_speed_duration_s,
        )
        self.write_event()
        self.print_transition("RELEASE", self.final_goal)

    def publish_goal(self, goal):
        msg = PoseStamped()
        msg.header.frame_id = "world"
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = goal[0]
        msg.pose.position.y = goal[1]
        msg.pose.position.z = goal[2]
        msg.pose.orientation.w = 1.0
        self.goal_pub.publish(msg)

    def record_transition(self, name, now_s, **extra):
        self.event["phase"] = self.phase
        self.event[name + "_time_s"] = round(now_s, 6)
        self.event[name + "_wall_time_s"] = round(time.time(), 6)
        self.event[name + "_position"] = self.position_record()
        self.event[name + "_speed_mps"] = (
            None if self.speed is None else round(self.speed, 4)
        )
        for key, value in extra.items():
            self.event[name + "_" + key] = round(float(value), 6)

    def position_record(self):
        if self.position is None:
            return None
        return {
            "x": round(self.position[0], 4),
            "y": round(self.position[1], 4),
            "z": round(self.position[2], 4),
        }

    def print_transition(self, transition, goal):
        position = self.position or (math.nan, math.nan, math.nan)
        print(
            "RECOVERY_MISSION_%s side=%s pos=(%.2f,%.2f,%.2f) goal=(%.2f,%.2f,%.2f)"
            % (
                transition,
                self.args.side,
                position[0],
                position[1],
                position[2],
                goal[0],
                goal[1],
                goal[2],
            ),
            flush=True,
        )

    def write_event(self):
        if not self.args.event_json:
            return
        tmp_path = "%s.tmp.%d" % (self.args.event_json, os.getpid())
        try:
            with open(tmp_path, "w") as stream:
                json.dump(self.event, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_path, self.args.event_json)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def main():
    args, ros_args = parse_args()
    rclpy.init(args=ros_args)
    node = RecoveryMission(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
