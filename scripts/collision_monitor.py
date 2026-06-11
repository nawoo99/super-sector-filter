#!/usr/bin/env python3
# collision_monitor.py  —  geometric collision / min-obstacle-distance metric
# -------------------------------------------------------------------
# Instead of a Gazebo contact sensor (needs SDF edit + sim restart), we use the
# known pillar positions (parsed from the world SDF) + live /odometry to compute:
#   - min clearance = min over pillars of (center_dist - pillar_radius) - drone_radius
#       (surface-to-surface; negative => overlap/collision)
#   - collision episodes: debounced count (one per continuous contact, like the
#     EGO benchmark's "count as 1")
#   - min drone-center-to-pillar-surface distance over the run
# Pillars are cylinders (radius 0.25, z in [0,3]) so horizontal distance suffices
# at the 1.5 m flight height.
#
#   source /opt/ros/humble/setup.bash ; python3 collision_monitor.py --world default_36
# Writes a summary line to --out on exit (SIGINT).
# -------------------------------------------------------------------
import argparse
import math
import re
import signal

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry

PILLAR_R = 0.25
DRONE_R = 0.30          # x500 effective horizontal radius
WORLD_DIR = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds"


def load_pillars(world):
    path = f"{WORLD_DIR}/{world}.sdf"
    txt = open(path).read()
    # pillar model poses sit at z≈1.5 (cylinders of length 3 centered at 1.5)
    pillars = []
    for m in re.finditer(r"<pose>\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", txt):
        x, y, z = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if abs(z - 1.5) < 0.05:
            pillars.append((x, y))
    return pillars


class CollisionMonitor(Node):
    def __init__(self, args):
        super().__init__("collision_monitor")
        self.args = args
        self.pillars = load_pillars(args.world)
        self.coll_thresh = PILLAR_R + DRONE_R           # center-dist collision threshold
        self.min_surface = float("inf")                 # min (center_dist - PILLAR_R) seen
        self.collisions = 0
        self.in_coll = False
        self.coll_pillars = set()
        self.n = 0
        self.get_logger().info(
            f"loaded {len(self.pillars)} pillars from {args.world}; "
            f"collision if center-dist < {self.coll_thresh:.2f} m (pillar {PILLAR_R}+drone {DRONE_R})")
        self.sub = self.create_subscription(Odometry, "/odometry", self.cb, qos_profile_sensor_data)
        self.create_timer(2.0, self.heartbeat)

    def cb(self, m: Odometry):
        if not self.pillars:
            return
        x = m.pose.pose.position.x
        y = m.pose.pose.position.y
        # nearest pillar
        best_d = min(math.hypot(x - px, y - py) for px, py in self.pillars)
        self.min_surface = min(self.min_surface, best_d - PILLAR_R)
        self.n += 1
        # debounced collision episode (rising edge)
        if best_d < self.coll_thresh:
            if not self.in_coll:
                self.collisions += 1
                self.in_coll = True
                # record which pillar
                px, py = min(self.pillars, key=lambda p: math.hypot(x - p[0], y - p[1]))
                self.coll_pillars.add((round(px, 1), round(py, 1)))
                self.get_logger().warn(
                    f"*** COLLISION #{self.collisions} near pillar ({px:.1f},{py:.1f}) "
                    f"center_dist={best_d:.2f} ***")
        else:
            self.in_coll = False

    def heartbeat(self):
        if self.n:
            self.get_logger().info(
                f"min surface clearance so far = {self.min_surface:.2f} m | collisions={self.collisions}")

    def summary(self):
        line = (f"world={self.args.world} pillars={len(self.pillars)} "
                f"collisions={self.collisions} min_surface_clearance_m={self.min_surface:.3f} "
                f"coll_pillars={sorted(self.coll_pillars)} samples={self.n}")
        self.get_logger().info("=== SUMMARY ===")
        self.get_logger().info(line)
        if self.args.out:
            with open(self.args.out, "w") as f:
                f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="default_36")
    ap.add_argument("--out", default="/tmp/g5_collision.txt")
    args = ap.parse_args()

    rclpy.init()
    node = CollisionMonitor(args)

    def on_sig(*_):
        node.summary()
        rclpy.shutdown()
    signal.signal(signal.SIGINT, on_sig)
    signal.signal(signal.SIGTERM, on_sig)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        try:
            node.summary()
        except Exception:
            pass


if __name__ == "__main__":
    main()
