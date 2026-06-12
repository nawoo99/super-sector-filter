#!/usr/bin/env python3
# collision_monitor.py  —  geometric collision / min-obstacle-distance metric
# -------------------------------------------------------------------
# Instead of a Gazebo contact sensor (needs SDF edit + sim restart), we parse the
# obstacle (x, y, radius) straight from the world SDF Gazebo loads, and combine with
# live /odometry to compute:
#   - min surface clearance = min over obstacles of (center_dist - obstacle_radius)
#       i.e. drone-center to nearest obstacle surface
#   - collision episodes: debounced count (one per continuous contact) when that
#     clearance drops below the drone radius (body overlaps the obstacle)
# Obstacles are vertical cylinders spanning the flight height, so horizontal distance
# suffices. The world SDF is the single source of truth (same file the sim loads);
# radius is read PER obstacle, so size-varying campaign seeds work unchanged.
#
#   source /opt/ros/humble/setup.bash
#   python3 collision_monitor.py --world default_seed7       # WORLD_DIR/<name>.sdf
#   python3 collision_monitor.py --world-sdf /path/to.sdf    # explicit file
# Writes a summary line to --out on exit (SIGINT/SIGTERM).
# -------------------------------------------------------------------
import argparse
import math
import re
import signal

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry

DRONE_R = 0.30          # x500 effective horizontal radius
WORLD_DIR = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds"


def load_obstacles(sdf_path):
    """Parse obstacle (x, y, radius) from the world SDF — the SAME file Gazebo loads.
    Robust: matches each `<model name="pylon_*"/"pillar_*">` block and reads its
    <pose> and cylinder <radius> (no height heuristic; per-obstacle radius so it
    handles the size-varying campaign seeds)."""
    txt = open(sdf_path).read()
    obs = []
    for blk in re.findall(r'<model name="(?:pylon|pillar)[^"]*">(.*?)</model>', txt, re.DOTALL):
        mp = re.search(r"<pose>\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", blk)
        mr = re.search(r"<radius>\s*([-\d.eE+]+)", blk)
        if mp and mr:
            obs.append((float(mp.group(1)), float(mp.group(2)), float(mr.group(1))))
    return obs


def resolve_sdf(args):
    if args.world_sdf:
        return args.world_sdf
    return f"{WORLD_DIR}/{args.world}.sdf"


class CollisionMonitor(Node):
    def __init__(self, args):
        super().__init__("collision_monitor")
        self.args = args
        self.sdf_path = resolve_sdf(args)
        self.obstacles = load_obstacles(self.sdf_path)   # list of (x, y, radius)
        self.min_surface = float("inf")                  # min (center_dist - obstacle_radius) seen
        self.collisions = 0
        self.in_coll = False
        self.coll_obs = set()
        self.n = 0
        radii = sorted({round(r, 3) for _, _, r in self.obstacles})
        self.get_logger().info(
            f"loaded {len(self.obstacles)} obstacles from {self.sdf_path} (radii={radii}); "
            f"collision if surface clearance < drone_R {DRONE_R} m")
        self.sub = self.create_subscription(Odometry, "/odometry", self.cb, qos_profile_sensor_data)
        self.create_timer(2.0, self.heartbeat)

    def cb(self, m: Odometry):
        if not self.obstacles:
            return
        x = m.pose.pose.position.x
        y = m.pose.pose.position.y
        # nearest obstacle by SURFACE distance (accounts for per-obstacle radius)
        px, py, pr = min(self.obstacles, key=lambda o: math.hypot(x - o[0], y - o[1]) - o[2])
        surf = math.hypot(x - px, y - py) - pr           # drone-center to obstacle surface
        self.min_surface = min(self.min_surface, surf)
        self.n += 1
        # collision when the drone body (radius DRONE_R) overlaps the obstacle surface
        if surf < DRONE_R:
            if not self.in_coll:
                self.collisions += 1
                self.in_coll = True
                self.coll_obs.add((round(px, 1), round(py, 1)))
                self.get_logger().warn(
                    f"*** COLLISION #{self.collisions} near ({px:.1f},{py:.1f}) "
                    f"surf_clearance={surf:.2f} ***")
        else:
            self.in_coll = False

    def heartbeat(self):
        if self.n:
            self.get_logger().info(
                f"min surface clearance so far = {self.min_surface:.2f} m | collisions={self.collisions}")

    def summary(self):
        line = (f"world={self.args.world} obstacles={len(self.obstacles)} "
                f"collisions={self.collisions} min_surface_clearance_m={self.min_surface:.3f} "
                f"coll_obs={sorted(self.coll_obs)} samples={self.n}")
        self.get_logger().info("=== SUMMARY ===")
        self.get_logger().info(line)
        if self.args.out:
            with open(self.args.out, "w") as f:
                f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="default_36", help="world name -> WORLD_DIR/<name>.sdf")
    ap.add_argument("--world-sdf", default=None, dest="world_sdf", help="explicit world SDF path (overrides --world)")
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
