#!/usr/bin/env python3
import argparse
import json
import math
import os

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Bool


# Filtering is deliberately latest-only.  A depth-five sensor queue can hold
# roughly half a second of 10 Hz clouds while NumPy rebuilds a filtered frame;
# processing that backlog makes the planner map old precisely when it needs a
# fresh scan.  ROG-Map's own cloud subscription is already best-effort/depth 1.
LATEST_CLOUD_QOS = QoSProfile(
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.VOLATILE,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", nargs="?", default="sector",
        choices=(
            "full", "sector", "velocity", "adaptive", "trigger", "legacy-trigger"
        ),
    )
    parser.add_argument("half_angle_deg", nargs="?", type=float, default=60.0)
    parser.add_argument("--input-topic", default="/cloud_registered")
    parser.add_argument("--output-topic", default="/cloud_sector")
    parser.add_argument(
        "--max-publish-hz", type=float, default=0.0,
        help=(
            "maximum filtered-cloud publish rate; zero disables rate "
            "limiting (input callbacks and recovery state still update)"
        ),
    )
    parser.add_argument("--track-trap", action="store_true")
    parser.add_argument(
        "--sector-until-trap",
        action="store_true",
        help="Use body-sector before the first tagged trap frame.",
    )
    parser.add_argument("--trap-intensity", type=float, default=12012.0)
    parser.add_argument("--event-json")
    parser.add_argument("--stats-json")
    parser.add_argument("--stall-v", type=float)
    parser.add_argument("--stall-t", type=float)
    parser.add_argument("--resume-v", type=float)
    parser.add_argument("--resume-t", type=float)
    parser.add_argument(
        "--replan-fail-streak-open", type=int, default=5,
        help="consecutive /planning/replan_status=False before forcing full-open",
    )
    parser.add_argument(
        "--replan-ok-streak-close", type=int, default=15,
        help="consecutive /planning/replan_status=True (after a guard-open) before re-narrowing",
    )
    parser.add_argument(
        "--no-replan-guard", action="store_true",
        help="disable the replan-failure-triggered full-open safety valve",
    )
    parser.add_argument(
        "--bounded-replan-guard", action="store_true",
        help=(
            "route replan-failure recovery through bounded full-cloud bursts "
            "instead of holding the filter continuously open"
        ),
    )
    parser.add_argument(
        "--replan-open-burst-s", type=float,
        help=(
            "duration of each bounded replan-triggered full-cloud burst; "
            "defaults to open-burst-s"
        ),
    )
    parser.add_argument(
        "--replan-open-cooldown-s", type=float,
        help=(
            "cooldown after each bounded replan burst; defaults to "
            "open-cooldown-s"
        ),
    )
    parser.add_argument(
        "--near-field-radius-m", type=float, default=1.5,
        help="always keep points within this 3D radius of the drone, "
             "regardless of sector angle (never blind the near-field)",
    )
    parser.add_argument(
        "--near-field-speed-gain-s", type=float, default=0.0,
        help=(
            "add speed * this many seconds to the omnidirectional near-field "
            "radius (adaptive reaction-distance halo)"
        ),
    )
    parser.add_argument(
        "--near-field-max-radius-m", type=float,
        help="upper bound for the speed-adaptive near-field radius",
    )
    parser.add_argument(
        "--open-burst-s", type=float, default=0.0,
        help=(
            "when adaptive stall recovery is active, pass full clouds for "
            "this many seconds per burst; zero preserves legacy sustained-open"
        ),
    )
    parser.add_argument(
        "--open-cooldown-s", type=float, default=0.0,
        help="sector-only cooldown between adaptive full-cloud bursts",
    )
    args, ros_args = parser.parse_known_args()
    return args, ros_args


class SectorFilter(Node):
    STATEFUL_MODES = ("adaptive", "trigger", "legacy-trigger")
    STALL_V = 0.6
    STALL_T = 1.2
    RESUME_V = 1.5
    RESUME_T = 2.0

    def __init__(self, args):
        super().__init__("native_sector")
        self.args = args
        self.mode = args.mode
        self.half_angle = math.radians(args.half_angle_deg)
        self.drone = None
        self.yaw = 0.0
        self.velocity_yaw = None
        self.latest_speed_mps = 0.0
        self.kept = 0
        self.total = 0
        self.frames = 0
        self.published_frames = 0
        self.rate_limited_frames = 0
        self.max_publish_hz = args.max_publish_hz
        self.next_publish_time_s = None
        self.open = False
        self.effective_recovery_open = False
        self.open_burst_s = args.open_burst_s
        self.open_cooldown_s = args.open_cooldown_s
        self.open_burst_until_s = None
        self.next_open_burst_s = None
        # Adaptive and trigger first prove sustained cruise, so launch idle
        # cannot open the filter.  legacy-trigger preserves the old ablation.
        self.armed = self.mode == "legacy-trigger"
        self.slow_since = None
        self.fast_since = None
        self.armed_frames = 0
        self.open_frames = 0
        self.input_points = 0
        self.open_input_points = 0
        self.arm_transitions = 0
        self.open_transitions = 0
        self.close_transitions = 0
        self.arm_transition_times_s = []
        self.open_transition_times_s = []
        self.close_transition_times_s = []
        self.first_transition_time_s = None
        self.first_stall_candidate_time_s = None
        self.first_open_stall_start_time_s = None
        self.first_open_delay_s = None
        self.first_arm_time_s = None
        self.first_open_time_s = None
        self.first_close_time_s = None
        self.stall_candidate_count = 0
        self.max_stall_candidate_duration_s = 0.0
        self.min_armed_closed_speed_mps = None
        self.trap_event = {}
        self.trap_seen = False
        self.near_field_radius_m = args.near_field_radius_m
        self.near_field_speed_gain_s = args.near_field_speed_gain_s
        self.near_field_max_radius_m = (
            args.near_field_max_radius_m
            if args.near_field_max_radius_m is not None
            else args.near_field_radius_m
        )
        self.max_effective_near_field_radius_m = self.near_field_radius_m
        self.replan_guard_en = not args.no_replan_guard
        self.replan_fail_streak_open = args.replan_fail_streak_open
        self.replan_ok_streak_close = args.replan_ok_streak_close
        self.replan_guard_bounded = args.bounded_replan_guard
        self.replan_guard_burst_s = (
            args.replan_open_burst_s
            if args.replan_open_burst_s is not None
            else self.open_burst_s
        )
        self.replan_guard_cooldown_s = (
            args.replan_open_cooldown_s
            if args.replan_open_cooldown_s is not None
            else self.open_cooldown_s
        )
        self.replan_guard_active = False
        self.replan_guard_open = False
        self.replan_guard_burst_until_s = None
        self.replan_guard_next_burst_s = None
        self.replan_fail_streak = 0
        self.replan_ok_streak = 0
        self.replan_guard_open_frames = 0
        self.replan_guard_open_transitions = 0
        self.replan_guard_close_transitions = 0
        self.replan_status_count = 0
        self.replan_fail_count = 0
        self.max_replan_fail_streak = 0
        self.first_replan_guard_open_time_s = None
        self.stall_v = self.STALL_V if args.stall_v is None else args.stall_v
        self.stall_t = self.STALL_T if args.stall_t is None else args.stall_t
        self.resume_v = self.RESUME_V if args.resume_v is None else args.resume_v
        self.resume_t = self.RESUME_T if args.resume_t is None else args.resume_t
        if min(self.stall_v, self.stall_t, self.resume_v, self.resume_t) < 0.0:
            raise ValueError("adaptive thresholds must be non-negative")
        if self.max_publish_hz < 0.0:
            raise ValueError("max-publish-hz must be non-negative")
        if min(self.open_burst_s, self.open_cooldown_s) < 0.0:
            raise ValueError("adaptive burst durations must be non-negative")
        if min(
            self.near_field_radius_m,
            self.near_field_speed_gain_s,
            self.near_field_max_radius_m,
        ) < 0.0:
            raise ValueError("near-field radius settings must be non-negative")
        if self.near_field_max_radius_m < self.near_field_radius_m:
            raise ValueError(
                "near-field-max-radius-m must be at least near-field-radius-m"
            )
        if min(
            self.replan_guard_burst_s,
            self.replan_guard_cooldown_s,
        ) < 0.0:
            raise ValueError("replan burst durations must be non-negative")
        if self.replan_guard_bounded and self.replan_guard_burst_s <= 0.0:
            raise ValueError(
                "bounded-replan-guard requires a positive replan burst"
            )
        if self.resume_v <= self.stall_v:
            raise ValueError("resume-v must be greater than stall-v")

        self.create_subscription(
            PointCloud2, args.input_topic, self.cloud_callback, LATEST_CLOUD_QOS
        )
        self.create_subscription(
            Odometry, "/lidar_slam/odom", self.odom_callback, qos_profile_sensor_data
        )
        if self.mode != "full" and self.replan_guard_en:
            self.create_subscription(
                Bool, "/planning/replan_status", self.replan_status_callback,
                qos_profile_sensor_data,
            )
        self.pub = self.create_publisher(
            PointCloud2, args.output_topic, LATEST_CLOUD_QOS
        )
        self.full_open_pub = self.create_publisher(Bool, "/sector/full_open", 1)
        self.trigger_armed_pub = self.create_publisher(
            Bool, "/sector/trigger_armed", 1
        )
        self.create_timer(1.0, self.publish_periodic_state)
        self.create_timer(5.0, self.report)
        self.get_logger().info(
            "%s mode, half-angle %.1f deg, input %s, publish cap %.2f Hz"
            % (
                self.mode,
                args.half_angle_deg,
                args.input_topic,
                self.max_publish_hz,
            )
        )
        if self.mode in self.STATEFUL_MODES:
            self.get_logger().info(
                "%s thresholds: stall <%.2f m/s for %.2fs, resume >%.2f m/s for %.2fs, "
                "full burst %.2fs / cooldown %.2fs"
                % (
                    self.mode,
                    self.stall_v,
                    self.stall_t,
                    self.resume_v,
                    self.resume_t,
                    self.open_burst_s,
                    self.open_cooldown_s,
                )
            )
        self.publish_state()
        self.write_stats()

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def should_publish_cloud(self, now):
        """Apply a deadline-based publication cap without delaying input state."""
        if self.max_publish_hz <= 0.0:
            return True
        publish_period_s = 1.0 / self.max_publish_hz
        if self.next_publish_time_s is None:
            self.next_publish_time_s = now + publish_period_s
            return True
        if now < self.next_publish_time_s:
            self.rate_limited_frames += 1
            return False

        # Advance the ideal deadline, rather than resetting it to the current
        # input timestamp.  Resetting on every publication quantizes a 5--7 Hz
        # input down to every second frame (~3 Hz) even when the cap is 4 Hz.
        elapsed_s = now - self.next_publish_time_s
        periods = math.floor(elapsed_s / publish_period_s) + 1
        self.next_publish_time_s += periods * publish_period_s
        return True

    def start_recovery_burst(self, now):
        """Start a bounded full-cloud burst, or legacy sustained opening."""
        if self.open_burst_s <= 0.0:
            self.effective_recovery_open = self.open
            self.open_burst_until_s = None
            self.next_open_burst_s = None
            return
        self.effective_recovery_open = True
        self.open_burst_until_s = now + self.open_burst_s
        self.next_open_burst_s = (
            self.open_burst_until_s + self.open_cooldown_s
        )

    def update_recovery_burst(self, now):
        """Advance the burst scheduler on a cloud arrival; return state change."""
        previous = self.effective_recovery_open
        if not self.open:
            self.effective_recovery_open = False
        elif self.open_burst_s <= 0.0:
            self.effective_recovery_open = True
        elif (
            self.next_open_burst_s is not None
            and now >= self.next_open_burst_s
        ):
            self.start_recovery_burst(now)
        else:
            self.effective_recovery_open = (
                self.open_burst_until_s is not None
                and now < self.open_burst_until_s
            )
        return previous != self.effective_recovery_open

    def stop_recovery_open(self):
        self.open = False
        self.effective_recovery_open = False
        self.open_burst_until_s = None
        self.next_open_burst_s = None

    def start_replan_guard_burst(self, now):
        """Open the replan valve once, respecting the configured bound."""
        was_open = self.replan_guard_open
        self.replan_guard_open = True
        if self.replan_guard_bounded:
            self.replan_guard_burst_until_s = now + self.replan_guard_burst_s
            self.replan_guard_next_burst_s = (
                self.replan_guard_burst_until_s
                + self.replan_guard_cooldown_s
            )
        else:
            self.replan_guard_burst_until_s = None
            self.replan_guard_next_burst_s = None
        if not was_open:
            self.replan_guard_open_transitions += 1
            if self.first_replan_guard_open_time_s is None:
                self.first_replan_guard_open_time_s = round(now, 6)

    def update_replan_guard_burst(self, now):
        """Expire a bounded one-shot replan burst on cloud arrival."""
        was_open = self.replan_guard_open
        if not self.replan_guard_active:
            self.replan_guard_open = False
        elif not self.replan_guard_bounded:
            self.replan_guard_open = True
        else:
            self.replan_guard_open = (
                self.replan_guard_burst_until_s is not None
                and now < self.replan_guard_burst_until_s
            )
            if not self.replan_guard_open:
                # Bounded mode is deliberately one-shot.  A later burst must
                # earn a new failure streak after the cooldown; it does not
                # repeat forever merely because the old recovery episode did
                # not collect an unlikely long streak of successful replans.
                self.replan_guard_active = False
                self.replan_guard_burst_until_s = None
        if was_open and not self.replan_guard_open:
            self.replan_guard_close_transitions += 1
        return was_open != self.replan_guard_open

    def stop_replan_guard(self):
        self.replan_guard_active = False
        if self.replan_guard_open:
            self.replan_guard_close_transitions += 1
        self.replan_guard_open = False
        self.replan_guard_burst_until_s = None
        self.replan_guard_next_burst_s = None

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.drone = np.array([p.x, p.y, p.z], dtype=np.float32)
        self.yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        v = msg.twist.twist.linear
        speed = math.hypot(v.x, v.y)
        self.latest_speed_mps = speed
        velocity_update_v = (
            self.resume_v if self.mode in ("velocity", "adaptive") else 0.2
        )
        if speed > velocity_update_v:
            self.velocity_yaw = math.atan2(v.y, v.x)

        if self.mode not in self.STATEFUL_MODES:
            return
        now = self.now()
        if not self.armed:
            if speed > self.resume_v:
                if self.fast_since is None:
                    self.fast_since = now
                elif now - self.fast_since > self.resume_t:
                    self.armed = True
                    self.fast_since = None
                    self.record_transition("arm", now)
                    self.get_logger().info(
                        "%s armed: sustained motion at %.2f m/s"
                        % (self.mode, speed)
                    )
                    self.publish_state()
                    self.write_stats()
            else:
                self.fast_since = None
            return

        if not self.open:
            self.min_armed_closed_speed_mps = (
                speed
                if self.min_armed_closed_speed_mps is None
                else min(self.min_armed_closed_speed_mps, speed)
            )
            if speed < self.stall_v:
                if self.slow_since is None:
                    self.slow_since = now
                    self.stall_candidate_count += 1
                    if self.first_stall_candidate_time_s is None:
                        self.first_stall_candidate_time_s = round(now, 6)
                        self.write_stats()
                slow_duration = now - self.slow_since
                self.max_stall_candidate_duration_s = max(
                    self.max_stall_candidate_duration_s, slow_duration
                )
                if slow_duration > self.stall_t:
                    if self.first_open_delay_s is None:
                        self.first_open_stall_start_time_s = round(
                            self.slow_since, 6
                        )
                        self.first_open_delay_s = round(now - self.slow_since, 6)
                    self.open = True
                    self.slow_since = None
                    self.fast_since = None
                    self.start_recovery_burst(now)
                    self.record_transition("open", now)
                    self.get_logger().info(
                        "%s full-open: stalled at %.2f m/s" % (self.mode, speed)
                    )
                    self.publish_state()
                    self.write_stats()
            else:
                if self.slow_since is not None:
                    self.max_stall_candidate_duration_s = max(
                        self.max_stall_candidate_duration_s,
                        now - self.slow_since,
                    )
                self.slow_since = None
        elif speed > self.resume_v:
            if self.fast_since is None:
                self.fast_since = now
            elif now - self.fast_since > self.resume_t:
                self.stop_recovery_open()
                self.slow_since = None
                self.fast_since = None
                self.record_transition("close", now)
                self.get_logger().info(
                    "%s sector-closed: motion resumed at %.2f m/s"
                    % (self.mode, speed)
                )
                self.publish_state()
                self.write_stats()
        else:
            self.fast_since = None

    def record_transition(self, transition, now):
        count_name = transition + "_transitions"
        setattr(self, count_name, getattr(self, count_name) + 1)
        timestamp = round(now, 6)
        times_name = transition + "_transition_times_s"
        getattr(self, times_name).append(timestamp)
        if self.first_transition_time_s is None:
            self.first_transition_time_s = timestamp
        first_name = "first_%s_time_s" % transition
        if getattr(self, first_name) is None:
            setattr(self, first_name, timestamp)

    def replan_status_callback(self, msg):
        now = self.now()
        self.replan_status_count += 1
        if msg.data:
            self.replan_ok_streak += 1
            self.replan_fail_streak = 0
        else:
            self.replan_fail_streak += 1
            self.replan_ok_streak = 0
            self.replan_fail_count += 1
            self.max_replan_fail_streak = max(
                self.max_replan_fail_streak, self.replan_fail_streak
            )

        if not self.replan_guard_active:
            cooldown_ready = (
                self.replan_guard_next_burst_s is None
                or now >= self.replan_guard_next_burst_s
            )
            if (
                cooldown_ready
                and self.replan_fail_streak >= self.replan_fail_streak_open
            ):
                trigger_fail_streak = self.replan_fail_streak
                self.replan_guard_active = True
                self.start_replan_guard_burst(now)
                # A later one-shot must be justified by fresh failures rather
                # than inheriting the streak that opened this burst.
                if self.replan_guard_bounded:
                    self.replan_fail_streak = 0
                self.get_logger().warning(
                    "%s replan-guard ACTIVE: %d consecutive replan failures, "
                    "bounded=%d"
                    % (
                        self.mode,
                        trigger_fail_streak,
                        int(self.replan_guard_bounded),
                    )
                )
                self.publish_state()
                self.write_stats()
        else:
            if (
                not self.replan_guard_bounded
                and self.replan_ok_streak >= self.replan_ok_streak_close
            ):
                self.stop_replan_guard()
                self.get_logger().info(
                    "%s replan-guard INACTIVE: %d consecutive replans succeeded"
                    % (self.mode, self.replan_ok_streak)
                )
                self.publish_state()
                self.write_stats()

    def publish_state(self):
        full_open = Bool()
        full_open.data = self.mode == "full" or (
            self.mode in self.STATEFUL_MODES
            and self.effective_recovery_open
        ) or self.replan_guard_open
        trigger_armed = Bool()
        trigger_armed.data = (
            self.mode in self.STATEFUL_MODES and self.armed
        )
        self.full_open_pub.publish(full_open)
        self.trigger_armed_pub.publish(trigger_armed)

    def publish_periodic_state(self):
        self.publish_state()
        self.write_stats()

    def cloud_callback(self, msg):
        now = self.now()
        burst_state_changed = self.update_recovery_burst(now)
        replan_burst_state_changed = self.update_replan_guard_burst(now)
        if burst_state_changed or replan_burst_state_changed:
            self.publish_state()
        self.frames += 1
        input_points = int(msg.width) * int(msg.height)
        self.input_points += input_points
        self.total += input_points
        if self.mode in self.STATEFUL_MODES:
            if self.armed:
                self.armed_frames += 1
        effective_open = self.mode == "full" or (
            self.mode in self.STATEFUL_MODES
            and self.effective_recovery_open
        ) or self.replan_guard_open
        if effective_open:
            self.open_frames += 1
            self.open_input_points += input_points
        if self.replan_guard_open:
            self.replan_guard_open_frames += 1
        if not self.should_publish_cloud(now):
            return
        self.published_frames += 1
        passthrough = (
            self.mode == "full"
            or self.drone is None
            or (
                self.mode in self.STATEFUL_MODES
                and self.effective_recovery_open
            )
            or self.replan_guard_open
        )
        if passthrough and not self.args.track_trap:
            self.kept += input_points
            self.pub.publish(msg)
            return

        try:
            points = pc2.read_points_numpy(
                msg, field_names=("x", "y", "z", "intensity"), skip_nans=True
            )
            points = points.reshape(-1, 4)
        except Exception as exc:
            self.get_logger().warning("cannot decode cloud: %s" % exc)
            self.kept += input_points
            self.pub.publish(msg)
            return

        if points.size == 0:
            self.kept += input_points
            self.pub.publish(msg)
            return

        trap_mask = self.trap_mask(points)
        trap_present = bool(trap_mask.any())
        if trap_present:
            self.trap_seen = True
        self.track_trap_input(points, trap_mask)
        if passthrough:
            output = points
        else:
            center = (
                self.velocity_yaw
                if (
                    self.mode in ("adaptive", "velocity")
                    and self.velocity_yaw is not None
                    and (not self.args.sector_until_trap or self.trap_seen)
                )
                else self.yaw
            )
            relative = (
                np.arctan2(
                    points[:, 1] - self.drone[1],
                    points[:, 0] - self.drone[0],
                )
                - center
            )
            relative = (relative + np.pi) % (2.0 * np.pi) - np.pi
            keep = np.abs(relative) <= self.half_angle
            if self.near_field_radius_m > 0.0:
                effective_near_field_radius_m = min(
                    self.near_field_max_radius_m,
                    self.near_field_radius_m
                    + self.near_field_speed_gain_s * self.latest_speed_mps,
                )
                self.max_effective_near_field_radius_m = max(
                    self.max_effective_near_field_radius_m,
                    effective_near_field_radius_m,
                )
                near = (
                    np.linalg.norm(points[:, :3] - self.drone, axis=1)
                    <= effective_near_field_radius_m
                )
                keep = keep | near
            output = points[keep]

        self.kept += len(output)
        self.track_trap_kept(output)
        # pc2.create_cloud() hardcodes is_dense=False. Points were already
        # read with skip_nans=True so the output is genuinely dense, but a
        # non-dense flag makes ROG-map's cloudCallback silently drop the
        # WHOLE frame (pcl::fromROSMsg copies the flag as-is, no rescan) --
        # confirmed via fsm_node logs showing most sector/adaptive frames
        # ("Empty or non-dense point cloud, skip cloud callback") being
        # dropped, leaving CIRI's occupancy map several meters stale.
        out_msg = pc2.create_cloud(msg.header, msg.fields, output)
        out_msg.is_dense = True
        self.pub.publish(out_msg)

    def trap_mask(self, points):
        if not self.args.track_trap or points.size == 0:
            return np.zeros(len(points), dtype=bool)
        return np.isclose(
            points[:, 3], self.args.trap_intensity, rtol=0.0, atol=0.01
        )

    def trap_geometry(self, trap_points):
        center = trap_points[:, :2].mean(axis=0)
        bearing = math.atan2(
            float(center[1] - self.drone[1]),
            float(center[0] - self.drone[0]),
        )
        body_relative = math.degrees(
            (bearing - self.yaw + math.pi) % (2.0 * math.pi) - math.pi
        )
        velocity_relative = None
        if self.velocity_yaw is not None:
            velocity_relative = math.degrees(
                (bearing - self.velocity_yaw + math.pi) % (2.0 * math.pi)
                - math.pi
            )
        distance = math.hypot(
            float(center[0] - self.drone[0]),
            float(center[1] - self.drone[1]),
        )
        return {
            "distance_m": round(distance, 4),
            "body_relative_deg": round(body_relative, 3),
            "velocity_relative_deg": (
                round(velocity_relative, 3)
                if velocity_relative is not None
                else None
            ),
        }

    def track_trap_input(self, points, mask=None):
        if "trap_input_time_s" in self.trap_event:
            return
        if mask is None:
            mask = self.trap_mask(points)
        if not mask.any():
            return
        self.trap_event["trap_input_time_s"] = round(self.now(), 6)
        self.trap_event.update(
            {"input_" + key: value for key, value in self.trap_geometry(points[mask]).items()}
        )
        self.write_trap_event()
        print(
            "SEED12_TRAP_INPUT " + json.dumps(self.trap_event, sort_keys=True),
            flush=True,
        )

    def track_trap_kept(self, points):
        if "trap_kept_time_s" in self.trap_event:
            return
        mask = self.trap_mask(points)
        if not mask.any():
            return
        kept_time = self.now()
        self.trap_event["trap_kept_time_s"] = round(kept_time, 6)
        input_time = self.trap_event.get("trap_input_time_s", kept_time)
        self.trap_event["trap_keep_delay_s"] = round(kept_time - input_time, 6)
        self.trap_event.update(
            {"kept_" + key: value for key, value in self.trap_geometry(points[mask]).items()}
        )
        self.write_trap_event()
        print(
            "SEED12_TRAP_KEPT " + json.dumps(self.trap_event, sort_keys=True),
            flush=True,
        )

    def write_trap_event(self):
        if not self.args.event_json:
            return
        tmp_path = self.args.event_json + ".tmp"
        with open(tmp_path, "w") as stream:
            json.dump(self.trap_event, stream, indent=2, sort_keys=True)
        os.replace(tmp_path, self.args.event_json)

    def stats_snapshot(self):
        frame_denominator = max(1, self.frames)
        point_denominator = max(1, self.input_points)
        open_duty_pct = 100.0 if self.mode == "full" else (
            100.0 * self.open_frames / frame_denominator
        )
        open_point_duty_pct = 100.0 if self.mode == "full" else (
            100.0 * self.open_input_points / point_denominator
        )
        first_open_duration_s = None
        if self.first_open_time_s is not None and self.first_close_time_s is not None:
            first_open_duration_s = round(
                self.first_close_time_s - self.first_open_time_s, 6
            )
        return {
            "mode": self.mode,
            "half_angle_deg": round(math.degrees(self.half_angle), 3),
            "stall_v": self.stall_v,
            "stall_t": self.stall_t,
            "resume_v": self.resume_v,
            "resume_t": self.resume_t,
            "velocity_yaw_update_v": (
                self.resume_v
                if self.mode in ("velocity", "adaptive")
                else 0.2
            ),
            "frames": self.frames,
            "published_frames": self.published_frames,
            "rate_limited_frames": self.rate_limited_frames,
            "max_publish_hz": self.max_publish_hz,
            "publish_duty_pct": round(
                100.0 * self.published_frames / frame_denominator, 3
            ),
            "input_points": self.input_points,
            "kept_points": self.kept,
            "kept_pct": round(100.0 * self.kept / point_denominator, 3),
            "armed": self.armed,
            "armed_duty_pct": round(
                100.0 * self.armed_frames / frame_denominator, 3
            ),
            "open": self.mode == "full"
                    or self.effective_recovery_open
                    or self.replan_guard_open,
            "recovery_active": self.open,
            "open_burst_s": self.open_burst_s,
            "open_cooldown_s": self.open_cooldown_s,
            "near_field_radius_m": self.near_field_radius_m,
            "near_field_speed_gain_s": self.near_field_speed_gain_s,
            "near_field_max_radius_m": self.near_field_max_radius_m,
            "max_effective_near_field_radius_m": round(
                self.max_effective_near_field_radius_m, 6
            ),
            "open_duty_pct": round(open_duty_pct, 3),
            "open_point_duty_pct": round(open_point_duty_pct, 3),
            "arm_transitions": self.arm_transitions,
            "open_transitions": self.open_transitions,
            "close_transitions": self.close_transitions,
            "arm_transition_times_s": self.arm_transition_times_s,
            "open_transition_times_s": self.open_transition_times_s,
            "close_transition_times_s": self.close_transition_times_s,
            "first_transition_time_s": self.first_transition_time_s,
            "first_stall_candidate_time_s": self.first_stall_candidate_time_s,
            "first_open_stall_start_time_s": self.first_open_stall_start_time_s,
            "first_open_delay_s": self.first_open_delay_s,
            "first_arm_time_s": self.first_arm_time_s,
            "first_open_time_s": self.first_open_time_s,
            "first_close_time_s": self.first_close_time_s,
            "first_open_duration_s": first_open_duration_s,
            "stall_candidate_count": self.stall_candidate_count,
            "max_stall_candidate_duration_s": round(
                self.max_stall_candidate_duration_s, 6
            ),
            "min_armed_closed_speed_mps": (
                round(self.min_armed_closed_speed_mps, 6)
                if self.min_armed_closed_speed_mps is not None
                else None
            ),
            "replan_guard_en": self.replan_guard_en,
            "replan_guard_bounded": self.replan_guard_bounded,
            "replan_guard_active": self.replan_guard_active,
            "replan_guard_burst_s": (
                self.replan_guard_burst_s
                if self.replan_guard_bounded else 0.0
            ),
            "replan_guard_cooldown_s": (
                self.replan_guard_cooldown_s
                if self.replan_guard_bounded else 0.0
            ),
            "replan_fail_streak_open": self.replan_fail_streak_open,
            "replan_ok_streak_close": self.replan_ok_streak_close,
            "replan_guard_open": self.replan_guard_open,
            "replan_guard_open_transitions": self.replan_guard_open_transitions,
            "replan_guard_close_transitions": self.replan_guard_close_transitions,
            "replan_guard_open_duty_pct": round(
                100.0 * self.replan_guard_open_frames / frame_denominator, 3
            ),
            "replan_status_count": self.replan_status_count,
            "replan_fail_count": self.replan_fail_count,
            "max_replan_fail_streak": self.max_replan_fail_streak,
            "first_replan_guard_open_time_s": self.first_replan_guard_open_time_s,
        }

    def write_stats(self, snapshot=None):
        if not self.args.stats_json:
            return
        if snapshot is None:
            snapshot = self.stats_snapshot()
        tmp_path = self.args.stats_json + ".tmp"
        with open(tmp_path, "w") as stream:
            json.dump(snapshot, stream, indent=2, sort_keys=True)
        os.replace(tmp_path, self.args.stats_json)

    def report(self):
        if not self.frames:
            return
        snapshot = self.stats_snapshot()
        kept_pct = snapshot["kept_pct"]
        extension = ""
        if self.mode in self.STATEFUL_MODES:
            extension = (
                " armed=%d armed_duty=%.0f%% recovery=%d full_open=%d "
                "open_duty=%.0f%%"
            ) % (
                int(self.armed),
                100.0 * self.armed_frames / max(1, self.frames),
                int(self.open),
                int(self.effective_recovery_open),
                100.0 * self.open_frames / max(1, self.frames),
            )
        if self.replan_guard_en and self.mode != "full":
            extension += (
                " guard_active=%d guard_open=%d guard_duty=%.0f%% "
                "fail_streak=%d/%d max_fail_streak=%d"
                % (
                    int(self.replan_guard_active),
                    int(self.replan_guard_open),
                    100.0 * self.replan_guard_open_frames / max(1, self.frames),
                    self.replan_fail_streak,
                    self.replan_fail_streak_open,
                    self.max_replan_fail_streak,
                )
            )
        print(
            "[native_sector %s] frames=%d published=%d kept %.0f%% "
            "(%d/%d pts/input-frame)%s"
            % (
                self.mode,
                self.frames,
                self.published_frames,
                kept_pct,
                self.kept // max(1, self.frames),
                self.total // max(1, self.frames),
                extension,
            ),
            flush=True,
        )
        self.write_stats(snapshot)


def main():
    args, ros_args = parse_args()
    rclpy.init(args=ros_args)
    node = SectorFilter(args)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.write_stats()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
