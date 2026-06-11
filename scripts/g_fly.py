#!/usr/bin/env python3
# g_fly.py  —  takeoff + (optional) goal sequencer for the SUPER/Gazebo stack
# -------------------------------------------------------------------
# The drone starts on the ground (z~0.04), which is NOT valid free space for
# SUPER's A* (start must be airborne). This script drives offboard.py through:
#   1. read /odometry -> home (hx,hy,hz, heading)
#   2. publish /position_cmd (ENU PoseStamped) at (hx,hy,z) to climb & hold
#   3. /keyboard_cmd "OFFBOARD" then "ARM"
#   4. wait until hovering at z
#   5. (if --goal) publish /planning/click_goal -> SUPER plans (G3); cmd_bridge
#      forwards SUPER's cmd to offboard -> drone flies (G4). Monitor progress.
# The hover setpoint keeps being published so that if SUPER stops commanding,
# offboard.py holds position instead of drifting.
#
# Run with humble + px4? no — only needs std/geometry/nav msgs:
#   source /opt/ros/humble/setup.bash ; python3 g_fly.py --goal X Y Z
# -------------------------------------------------------------------
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
    return (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0))  # w,x,y,z


def quat_to_yaw(w, x, y, z):
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class GFly(Node):
    def __init__(self, args):
        super().__init__("g_fly")
        self.args = args
        self.home = None          # (x,y,z,yaw)
        self.hold_target = None   # (x,y,z) POSITION-mode fallback setpoint
        self.odom = None          # latest (x,y,z)
        self.start_t = time.time()
        self.phase = "wait_odom"
        self.offb_sent = False
        self.arm_sent = False
        self.goal_sent = False
        self.hover_t0 = None
        self.goal_t0 = None

        # goal SUPER subscribes best_effort/volatile/keep_last(1)
        goal_qos = QoSProfile(depth=1)
        goal_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        goal_qos.history = HistoryPolicy.KEEP_LAST
        goal_qos.durability = DurabilityPolicy.VOLATILE

        self.sub = self.create_subscription(Odometry, "/odometry", self.odom_cb, qos_profile_sensor_data)
        self.pub_sp = self.create_publisher(PoseStamped, "/position_cmd", 10)
        self.pub_kc = self.create_publisher(String, "/keyboard_cmd", 10)
        self.pub_goal = self.create_publisher(PoseStamped, "/planning/click_goal", goal_qos)

        self.timer = self.create_timer(0.05, self.tick)   # 20 Hz
        self.log_timer = self.create_timer(1.0, self.log_status)

    def odom_cb(self, m: Odometry):
        p = m.pose.pose.position
        q = m.pose.pose.orientation
        self.odom = (p.x, p.y, p.z)
        if self.home is None:
            yaw = quat_to_yaw(q.w, q.x, q.y, q.z)
            self.home = (p.x, p.y, p.z, yaw)
            self.hold_target = (p.x, p.y, float(self.args.z))
            self.get_logger().info(
                f"home: ({p.x:.2f},{p.y:.2f},{p.z:.2f}) yaw={math.degrees(yaw):.0f}deg "
                f"-> takeoff z={self.args.z}")

    def keyboard(self, s):
        m = String(); m.data = s; self.pub_kc.publish(m)

    def publish_hover(self):
        # POSITION-mode fallback target: home until a goal is sent, then the goal
        # (so if SUPER stops commanding at the goal, we hold there, not fly home).
        _, _, _, hyaw = self.home
        hx, hy, hz = self.hold_target
        sp = PoseStamped()
        sp.header.frame_id = "world"
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.pose.position.x = hx
        sp.pose.position.y = hy
        sp.pose.position.z = hz
        w, x, y, z = yaw_to_quat(hyaw)
        sp.pose.orientation.w = w; sp.pose.orientation.z = z
        self.pub_sp.publish(sp)

    def publish_goal(self):
        gx, gy, gz = self.args.goal
        g = PoseStamped()
        g.header.frame_id = "world"
        g.header.stamp = self.get_clock().now().to_msg()
        g.pose.position.x = float(gx)
        g.pose.position.y = float(gy)
        g.pose.position.z = float(gz)
        g.pose.orientation.w = 1.0
        self.pub_goal.publish(g)

    def tick(self):
        if self.home is None:
            return
        t = time.time() - self.start_t

        # always hold the hover setpoint (POSITION-mode fallback)
        self.publish_hover()

        # OFFBOARD at t=1.0, ARM at t=4.0
        if not self.offb_sent and t > 1.0:
            self.keyboard("OFFBOARD"); self.offb_sent = True
            self.get_logger().info("-> OFFBOARD")
        if not self.arm_sent and t > 4.0:
            self.keyboard("ARM"); self.arm_sent = True
            self.get_logger().info("-> ARM")

        # detect hover reached
        if self.phase in ("wait_odom", "climbing"):
            self.phase = "climbing"
            if self.odom is not None:
                dz = abs(self.odom[2] - self.args.z)
                if dz < 0.25:
                    if self.hover_t0 is None:
                        self.hover_t0 = time.time()
                    elif time.time() - self.hover_t0 > 2.0:
                        self.phase = "hover"
                        self.get_logger().info(f"*** HOVER reached at z={self.odom[2]:.2f} ***")
                else:
                    self.hover_t0 = None

        # send goal once hovering
        if self.phase == "hover" and self.args.goal and not self.goal_sent:
            self.publish_goal()
            self.goal_sent = True
            self.goal_t0 = time.time()
            self.phase = "to_goal"
            gx, gy, gz = self.args.goal
            self.hold_target = (float(gx), float(gy), float(gz))  # hold at goal if SUPER stops
            self.get_logger().info(f"*** GOAL sent: ({gx},{gy},{gz}) ***")

        # re-publish goal a few times (best_effort, in case SUPER missed it)
        if self.phase == "to_goal" and self.goal_t0 and (time.time() - self.goal_t0) < 1.5:
            if int((time.time() - self.goal_t0) * 5) % 2 == 0:
                self.publish_goal()

        # goal reached / timeout
        if self.phase == "to_goal" and self.odom is not None:
            gx, gy, gz = self.args.goal
            d = math.hypot(self.odom[0] - float(gx), self.odom[1] - float(gy))
            if d < 0.6:
                self.get_logger().info(f"*** GOAL REACHED (d={d:.2f}) ***")
                self.phase = "done"
            elif time.time() - self.goal_t0 > self.args.timeout:
                self.get_logger().warn(f"*** GOAL TIMEOUT after {self.args.timeout}s (d={d:.2f}) ***")
                self.phase = "done"

    def log_status(self):
        if self.odom is None:
            self.get_logger().info("[wait] no /odometry yet")
            return
        x, y, z = self.odom
        extra = ""
        if self.args.goal and self.phase in ("to_goal", "done"):
            gx, gy, _ = self.args.goal
            extra = f" | goal_d={math.hypot(x-float(gx), y-float(gy)):.2f}"
        self.get_logger().info(f"[{self.phase}] pos=({x:.2f},{y:.2f},{z:.2f}){extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--z", type=float, default=1.5, help="takeoff/hover altitude (ENU, m)")
    ap.add_argument("--goal", type=float, nargs=3, metavar=("X", "Y", "Z"), default=None,
                    help="goal in world/ENU; if omitted, just takeoff and hold")
    ap.add_argument("--timeout", type=float, default=60.0, help="goal-reach timeout (s)")
    args = ap.parse_args()

    rclpy.init()
    node = GFly(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
