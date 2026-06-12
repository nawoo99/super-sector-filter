#!/usr/bin/env python3
# g_mission.py  —  perimeter-loop mission runner for the SUPER sector-filter campaign
# -------------------------------------------------------------------------------------
# Takeoff (reusing g_fly's proven OFFBOARD/ARM-resend climb) then fly a square
# perimeter loop through the obstacle field:  (0,0) -> c1 -> c2 -> c3 -> c4 -> (0,0),
# with the 4 corners at (+/-C, +/-C) (gen_world keeps those discs obstacle-free).
#
# Long legs are auto-subdivided into <= --max-leg nav points so SUPER's A* (which
# plans within the observed region) can solve each hop; only the CORNERS trigger
# the adaptive full-view recovery hook (a no-op placeholder here — step 3 wires the
# runtime sector toggle). Collisions/clearance are scored by collision_monitor.py
# running alongside.
#
#   source /opt/ros/humble/setup.bash
#   python3 g_mission.py [--c 9] [--z 1.5] [--max-leg 9] [--corner-hover 3]
# -------------------------------------------------------------------------------------
import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String


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

        goal_qos = QoSProfile(depth=1)
        goal_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        goal_qos.history = HistoryPolicy.KEEP_LAST
        goal_qos.durability = DurabilityPolicy.VOLATILE

        self.sub = self.create_subscription(Odometry, "/odometry", self.odom_cb, qos_profile_sensor_data)
        self.pub_sp = self.create_publisher(PoseStamped, "/position_cmd", 10)
        self.pub_kc = self.create_publisher(String, "/keyboard_cmd", 10)
        self.pub_goal = self.create_publisher(PoseStamped, "/planning/click_goal", goal_qos)

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
                    self.get_logger().info(f"*** HOVER at z={self.odom[2]:.2f} -> start loop ***")
                    self.send_current_wp()
            else:
                self.hover_t0 = None

        if self.phase == "mission":
            self.run_mission()

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
                # --- adaptive full-view recovery hook (placeholder; step 3 toggles sector) ---
                if self.recover_t0 is None:
                    self.recover_t0 = time.time()
                    self.get_logger().info(
                        f"*** CORNER {self.wi} reached ({x:.1f},{y:.1f}) d={d:.2f} -> RECOVERY (full-view) {self.args.corner_hover}s ***")
                if time.time() - self.recover_t0 < self.args.corner_hover:
                    return  # dwell at the corner for the full-view sweep
                self.recover_t0 = None
            self.advance()

        # per-leg timeout safety
        if time.time() - self.wp_sent_t > self.args.leg_timeout:
            self.get_logger().warn(f"*** WP {self.wi} TIMEOUT (d={d:.2f}) -> skip ***")
            self.recover_t0 = None
            self.advance()

    def advance(self):
        self.wi += 1
        if self.wi >= len(self.wps):
            self.phase = "done"
            self.get_logger().info("*** LOOP COMPLETE -> hold at home ***")
            self.hold = (self.home[0], self.home[1], float(self.args.z))
            return
        self.send_current_wp()

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
    args = ap.parse_args()

    rclpy.init()
    node = GMission(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
