#!/usr/bin/env python3
# g_mission.py  —  perimeter-loop mission runner for the SUPER sector-filter campaign
# -------------------------------------------------------------------------------------
# Takeoff (reusing g_fly's proven OFFBOARD/ARM-resend climb) then fly a square
# perimeter loop through the obstacle field:  (0,0) -> c1 -> c2 -> c3 -> c4 -> (0,0),
# with the 4 corners at (+/-C, +/-C) (gen_world keeps those discs obstacle-free).
#
# Long legs are auto-subdivided into <= --max-leg nav points so SUPER's A* (which
# plans within the observed region) can solve each hop; only the CORNERS trigger
# the adaptive full-view recovery: the cloud_preprocessor sector filter is dropped
# (full 360 view) via /sector/enable while hovering at each corner, then restored.
# Use --no-adaptive to keep the sector ON for the A/B comparison. Collisions/
# clearance are scored by collision_monitor.py running alongside.
#
#   source /opt/ros/humble/setup.bash
#   python3 g_mission.py [--c 9] [--z 1.5] [--max-leg 9] [--corner-hover 3]
# -------------------------------------------------------------------------------------
import argparse
import json
import math
import os
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String, Bool


def yaw_to_quat(yaw):
    return (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0))


def quat_to_yaw(w, x, y, z):
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def build_waypoints(home, corners, z, max_leg):
    """Return [(x, y, z, is_corner)] : the corner anchors with nav midpoints inserted
    so every leg is <= max_leg. Mission = home -> c1..c4 -> home (corners recover)."""
    anchors = [(cx, cy, True) for cx, cy in corners] + [(home[0], home[1], False)]
    wps = []
    prev = (home[0], home[1])
    for ax, ay, is_corner in anchors:
        d = math.hypot(ax - prev[0], ay - prev[1])
        n = max(1, int(math.ceil(d / max_leg)))
        for k in range(1, n + 1):
            t = k / n
            wx = prev[0] + (ax - prev[0]) * t
            wy = prev[1] + (ay - prev[1]) * t
            wps.append((wx, wy, z, is_corner and k == n))
        prev = (ax, ay)
    return wps


class GMission(Node):
    def __init__(self, args):
        super().__init__("g_mission")
        self.args = args
        self.home = None
        self.hold = None          # POSITION-mode fallback target (x,y,z)
        self.odom = None
        self.start_t = time.time()
        self.phase = "wait_odom"
        self.last_offb_t = -10.0
        self.last_arm_t = -10.0
        self.hover_t0 = None
        # mission state
        self.wps = []
        self.wi = 0
        self.wp_sent_t = 0.0
        self.recover_t0 = None
        # campaign metrics
        self.mission_t0 = None        # wall time the loop actually started
        self.perf_row_start = None    # rm_performance_log.csv data-row count at loop start
        self.corners_reached = 0
        self.timeouts = 0
        self.metrics_written = False
        self.exit_after = None        # set when campaign-mode should shut down

        goal_qos = QoSProfile(depth=1)
        goal_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        goal_qos.history = HistoryPolicy.KEEP_LAST
        goal_qos.durability = DurabilityPolicy.VOLATILE

        self.sub = self.create_subscription(Odometry, "/odometry", self.odom_cb, qos_profile_sensor_data)
        self.pub_sp = self.create_publisher(PoseStamped, "/position_cmd", 10)
        self.pub_kc = self.create_publisher(String, "/keyboard_cmd", 10)
        self.pub_goal = self.create_publisher(PoseStamped, "/planning/click_goal", goal_qos)
        self.pub_sector = self.create_publisher(Bool, "/sector/enable", 1)
        self.pub_risk = self.create_publisher(Bool, "/sector/risk_gate", 1)
        self.pub_align = self.create_publisher(Bool, "/sector/align_velocity", 1)
        self.sector_on = True   # track current sector state (adaptive recovery)

        self.create_timer(0.05, self.tick)
        self.create_timer(1.0, self.log_status)

    def odom_cb(self, m):
        p = m.pose.pose.position
        q = m.pose.pose.orientation
        self.odom = (p.x, p.y, p.z)
        if self.home is None:
            yaw = quat_to_yaw(q.w, q.x, q.y, q.z)
            self.home = (p.x, p.y, p.z, yaw)
            self.hold = (p.x, p.y, float(self.args.z))
            corners = [(self.args.c, self.args.c), (-self.args.c, self.args.c),
                       (-self.args.c, -self.args.c), (self.args.c, -self.args.c)]
            self.wps = build_waypoints((p.x, p.y), corners, float(self.args.z), self.args.max_leg)
            self.get_logger().info(
                f"home=({p.x:.2f},{p.y:.2f}) -> loop C={self.args.c}, {len(self.wps)} waypoints "
                f"({sum(1 for w in self.wps if w[3])} corners)")

    def keyboard(self, s):
        m = String(); m.data = s; self.pub_kc.publish(m)

    def publish_sector_raw(self, on):
        """Unconditionally publish the sector state (used once for the per-mode base:
        full=OFF, sector/adaptive=ON). Bypasses the adaptive gate in set_sector()."""
        m = Bool(); m.data = bool(on); self.pub_sector.publish(m)
        self.sector_on = on

    def publish_risk_gate(self, on):
        """Enable/disable the cloud_preprocessor's risk-gated auto-expansion (adaptive
        mode = fixed sector that expands to full-view only near side obstacles)."""
        m = Bool(); m.data = bool(on); self.pub_risk.publish(m)

    def publish_align_velocity(self, on):
        """Enable/disable velocity-aligned sector (directional recovery: the ±60 cone
        points along MOTION instead of body-forward, recovering the fixed-yaw blindspot
        without full-view over-population)."""
        m = Bool(); m.data = bool(on); self.pub_align.publish(m)

    def set_sector(self, on):
        """Toggle the cloud_preprocessor sector filter at runtime (adaptive recovery).
        on=False -> full 360 view (catch side obstacles the +/-60 sector misses)."""
        if not self.args.adaptive or on == self.sector_on:
            return
        m = Bool(); m.data = bool(on); self.pub_sector.publish(m)
        self.sector_on = on
        self.get_logger().info(f"    [adaptive] sector -> {'ON' if on else 'OFF (full-view)'}")

    def perf_rows(self):
        """Current data-row count of the ROG-Map performance log (excludes header).
        Used to slice exactly the frames that belong to THIS mission for the campaign."""
        try:
            with open(self.args.perf_log) as f:
                n = sum(1 for _ in f)
            return max(0, n - 1)
        except OSError:
            return None

    def write_metrics(self, success):
        if self.metrics_written or not self.args.metrics_out:
            return
        self.metrics_written = True
        mt = (time.time() - self.mission_t0) if self.mission_t0 else 0.0
        rec = {
            "mode": self.args.mode,
            "seed": self.args.seed,
            "run": self.args.run,
            "success": bool(success),
            "mission_time_s": round(mt, 2),
            "perf_row_start": self.perf_row_start,
            "perf_row_end": self.perf_rows(),
            "n_waypoints": len(self.wps),
            "corners_reached": self.corners_reached,
            "timeouts": self.timeouts,
        }
        try:
            os.makedirs(os.path.dirname(self.args.metrics_out) or ".", exist_ok=True)
            with open(self.args.metrics_out, "w") as f:
                json.dump(rec, f)
            self.get_logger().info(f"*** METRICS -> {self.args.metrics_out}: {rec} ***")
        except OSError as e:
            self.get_logger().error(f"metrics write failed: {e}")

    def publish_hover(self):
        _, _, _, hyaw = self.home
        hx, hy, hz = self.hold
        sp = PoseStamped()
        sp.header.frame_id = "world"
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.pose.position.x = hx; sp.pose.position.y = hy; sp.pose.position.z = hz
        w, x, y, z = yaw_to_quat(hyaw)
        sp.pose.orientation.w = w; sp.pose.orientation.z = z
        self.pub_sp.publish(sp)

    def publish_goal(self, x, y, z):
        g = PoseStamped()
        g.header.frame_id = "world"
        g.header.stamp = self.get_clock().now().to_msg()
        g.pose.position.x = float(x); g.pose.position.y = float(y); g.pose.position.z = float(z)
        g.pose.orientation.w = 1.0
        self.pub_goal.publish(g)

    def tick(self):
        # campaign safety: if the loop never starts (e.g. odom never arrives, climb stalls),
        # don't hang forever -- abort cleanly so the runner can move to the next mode.
        if (self.args.metrics_out and self.phase not in ("mission", "done")
                and (time.time() - self.start_t) > self.args.startup_timeout):
            self.get_logger().warn(
                f"*** STARTUP TIMEOUT ({self.args.startup_timeout:.0f}s, phase={self.phase}) "
                f"-> abort (success=False) ***")
            self.write_metrics(False)
            rclpy.shutdown()
            return
        if self.home is None:
            return
        t = time.time() - self.start_t
        self.publish_hover()  # POSITION fallback (hold last target if SUPER stops)

        # robust climb: resend OFFBOARD/ARM until airborne
        if self.phase == "climbing" and self.odom and self.odom[2] < 0.6:
            if t > 1.0 and (t - self.last_offb_t) > 1.0:
                self.keyboard("OFFBOARD"); self.last_offb_t = t
            if t > 3.0 and (t - self.last_arm_t) > 1.0:
                self.keyboard("ARM"); self.last_arm_t = t

        if self.phase in ("wait_odom", "climbing"):
            self.phase = "climbing"
            if self.odom and abs(self.odom[2] - self.args.z) < 0.25:
                if self.hover_t0 is None:
                    self.hover_t0 = time.time()
                elif time.time() - self.hover_t0 > 2.0:
                    self.phase = "mission"
                    # per-mode sector base: full=OFF(360), sector/adaptive=ON(+/-60)
                    self.publish_sector_raw(self.args.sector_base == "on")
                    # adaptive = risk-gated auto-expansion (fixed sector that widens near side obstacles)
                    self.publish_risk_gate(self.args.risk_gate == "on")
                    # velocity-aligned sector (directional recovery for fixed-yaw blindspot)
                    self.publish_align_velocity(self.args.align_velocity == "on")
                    self.mission_t0 = time.time()
                    self.perf_row_start = self.perf_rows()
                    self.get_logger().info(
                        f"*** HOVER at z={self.odom[2]:.2f} -> start loop "
                        f"(mode={self.args.mode}, sector_base={self.args.sector_base}, "
                        f"risk_gate={self.args.risk_gate}, "
                        f"perf_row_start={self.perf_row_start}) ***")
                    self.send_current_wp()
            else:
                self.hover_t0 = None

        if self.phase == "mission":
            self.run_mission()

        # campaign mode: shut down a moment after the loop ends so the runner advances
        if self.exit_after is not None and time.time() > self.exit_after:
            self.write_metrics(self.phase == "done")
            rclpy.shutdown()

    def send_current_wp(self):
        x, y, z, _ = self.wps[self.wi]
        self.hold = (x, y, z)
        self.publish_goal(x, y, z)
        self.wp_sent_t = time.time()

    def run_mission(self):
        if self.odom is None:
            return
        x, y, z, is_corner = self.wps[self.wi]
        d = math.hypot(self.odom[0] - x, self.odom[1] - y)
        # re-publish the goal a few times right after switching (best_effort)
        if time.time() - self.wp_sent_t < 1.2 and int((time.time() - self.wp_sent_t) * 5) % 2 == 0:
            self.publish_goal(x, y, z)

        reach = self.args.reach_corner if is_corner else self.args.reach_nav
        if d < reach:
            if is_corner:
                # --- adaptive full-view recovery: drop the sector filter while hovering
                #     at the corner so ROG-Map sees the side obstacles the +/-60 cone misses ---
                if self.recover_t0 is None:
                    self.recover_t0 = time.time()
                    self.corners_reached += 1
                    self.set_sector(False)   # full 360 view
                    self.get_logger().info(
                        f"*** CORNER {self.wi} reached ({x:.1f},{y:.1f}) d={d:.2f} -> RECOVERY (full-view) {self.args.corner_hover}s ***")
                if time.time() - self.recover_t0 < self.args.corner_hover:
                    return  # dwell at the corner for the full-view sweep
                self.recover_t0 = None
            self.advance()

        # per-leg timeout safety
        if time.time() - self.wp_sent_t > self.args.leg_timeout:
            self.timeouts += 1
            self.get_logger().warn(f"*** WP {self.wi} TIMEOUT (d={d:.2f}) -> skip ***")
            self.recover_t0 = None
            self.advance()

        # overall mission timeout safety (campaign): never hang a seed forever
        if self.mission_t0 and (time.time() - self.mission_t0) > self.args.mission_timeout:
            self.get_logger().warn("*** MISSION TIMEOUT -> abort loop (success=False) ***")
            self.finish(success=False)

    def advance(self):
        self.set_sector(True)   # restore sector filter when leaving a corner
        self.wi += 1
        if self.wi >= len(self.wps):
            self.get_logger().info("*** LOOP COMPLETE -> hold at home ***")
            self.finish(success=True)
            return
        self.send_current_wp()

    def finish(self, success):
        """End the loop: hold at home, write metrics, and (campaign mode) schedule exit."""
        if self.phase == "done":
            return
        self.phase = "done"
        self.hold = (self.home[0], self.home[1], float(self.args.z))
        self.write_metrics(success)
        if self.args.metrics_out:
            # let the drone settle at home, then the campaign exit-check shuts us down
            self.exit_after = time.time() + self.args.settle

    def log_status(self):
        if self.odom is None:
            self.get_logger().info("[wait] no /odometry"); return
        x, y, z = self.odom
        tgt = ""
        if self.phase == "mission" and self.wi < len(self.wps):
            wx, wy, _, isc = self.wps[self.wi]
            tgt = f" -> wp{self.wi}{'(corner)' if isc else ''} d={math.hypot(x-wx, y-wy):.2f}"
        self.get_logger().info(f"[{self.phase}] pos=({x:.2f},{y:.2f},{z:.2f}){tgt}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c", type=float, default=9.0, help="loop corner coordinate (+/-C, +/-C)")
    ap.add_argument("--z", type=float, default=1.5, help="flight altitude [m]")
    ap.add_argument("--max-leg", type=float, default=9.0, dest="max_leg", help="max leg length before subdividing [m]")
    ap.add_argument("--reach-nav", type=float, default=2.0, dest="reach_nav", help="advance radius at nav points [m]")
    ap.add_argument("--reach-corner", type=float, default=1.0, dest="reach_corner", help="advance radius at corners [m]")
    ap.add_argument("--corner-hover", type=float, default=3.0, dest="corner_hover", help="dwell at each corner [s]")
    ap.add_argument("--leg-timeout", type=float, default=40.0, dest="leg_timeout", help="per-waypoint timeout [s]")
    ap.add_argument("--adaptive", dest="adaptive", action="store_true", default=True,
                    help="adaptive full-view recovery: drop sector at corners (default on)")
    ap.add_argument("--no-adaptive", dest="adaptive", action="store_false",
                    help="disable recovery (sector stays ON the whole loop) for the A/B comparison")
    # --- campaign metrics (Step 4) ---
    ap.add_argument("--mode", default="adaptive", help="label recorded in metrics (full|sector|adaptive)")
    ap.add_argument("--seed", default="", help="seed label recorded in metrics")
    ap.add_argument("--run", default="", help="run index recorded in metrics")
    ap.add_argument("--sector-base", default="on", choices=["on", "off"], dest="sector_base",
                    help="sector state to publish at loop start (full=off, sector/adaptive=on)")
    ap.add_argument("--risk-gate", default="off", choices=["on", "off"], dest="risk_gate",
                    help="risk-gated auto-expansion (adaptive: fixed sector widens to full-view near side obstacles)")
    ap.add_argument("--align-velocity", default="off", choices=["on", "off"], dest="align_velocity",
                    help="velocity-aligned sector (directional recovery: cone points along motion, not body-forward)")
    ap.add_argument("--metrics-out", default=None, dest="metrics_out",
                    help="write JSON metrics here at loop end and exit (campaign mode)")
    ap.add_argument("--perf-log", dest="perf_log",
                    default="/root/super_ws/src/SUPER/rog_map/log/rm_performance_log.csv",
                    help="ROG-Map performance log to slice for this mission")
    ap.add_argument("--mission-timeout", type=float, default=240.0, dest="mission_timeout",
                    help="abort the whole loop after this many seconds (campaign safety)")
    ap.add_argument("--settle", type=float, default=4.0,
                    help="hold at home this long after loop end before exiting (campaign)")
    ap.add_argument("--startup-timeout", type=float, default=120.0, dest="startup_timeout",
                    help="abort if the loop never starts within this many seconds (campaign safety)")
    args = ap.parse_args()

    rclpy.init()
    node = GMission(args)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        # campaign safety: make sure metrics land even on an unexpected exit
        try:
            node.write_metrics(node.phase == "done")
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
