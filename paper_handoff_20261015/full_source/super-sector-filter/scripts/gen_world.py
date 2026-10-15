#!/usr/bin/env python3
# gen_world.py  —  static obstacle-world generator for the SUPER sector-filter campaign
# -------------------------------------------------------------------------------------
# Derived from spawn_pillars.py, but the STABLE path: instead of spawning into a
# running Gazebo via `gz service` (which can fail/timeout and is timing-dependent),
# this BAKES a complete static world SDF per seed, offline. The same file is what
# Gazebo loads AND what collision_monitor.py reads -> one source of truth, fully
# deterministic, sector-ON/OFF see a byte-identical world.
#
# Obstacles are CYLINDERS only (radius encodes "size"): the study varies size and
# spacing, not shape, and a cylinder's collision geometry is exactly parseable
# from the SDF (no STL/mesh radius guessing) and matches the geometric metric.
#
# 12-seed design (one-factor-at-a-time, 2 replicates per condition):
#   size axis  (count fixed at medium): small | medium(baseline) | large
#   spacing axis (radius fixed at medium): dense | medium(baseline) | sparse
#   seeds 1,2=small  3,4=baseline(med size)  5,6=large
#         7,8=dense  9,10=baseline(med spacing)  11,12=sparse
#   (3,4 and 9,10 are the same medium/medium condition -> 4 well-replicated baselines,
#    each a different layout via its own RNG seed.)
#
# Usage:
#   python3 gen_world.py --seed 7                 # writes default_seed7.sdf
#   python3 gen_world.py --all                    # writes all 12
#   (optional) --out-dir <dir>  --template <default_36.sdf>  --area 24
# -------------------------------------------------------------------------------------
import argparse
import math
import os
import random
import re

# ---- field / obstacle geometry ----
AREA = 30.0          # square field side [m]; obstacles in [-15,15]. Enlarged from 24: keeping
                     # COUNT=100 but spreading them over a bigger field widens the AVERAGE
                     # gaps (the min-spacing GAPS are unchanged) so the ~0.3 m tracking error
                     # no longer clips -> reliable clean flight; also makes the +/-9 loop more
                     # central (obstacles on all sides = detour room, no edge traps).
MARGIN = 3.0         # central takeoff-clear radius [m] (drone starts at 0,0)
OBST_LENGTH = 3.0    # cylinder height [m]; spans z in [0, 3], drone flies at 1.5
OBST_Z = OBST_LENGTH / 2.0
# (obstacle min-spacing is now per-density condition -- see GAPS below)

# ---- perimeter-loop waypoints (kept clear so the mission can hover/recover there) ----
CORNER_C = 9.0       # the 4 loop-corner waypoints sit at (+/-C, +/-C)
CORNER_CLEAR = 2.5   # clear radius [m] around each corner waypoint. Raised 1.5->2.5:
                     # the drone makes a ~135 deg turn AT each corner; with obstacles only
                     # 1.5 m away it clipped one mid-turn (verified: SO3 commanded full
                     # up-thrust yet the drone was forced down = a collision). 2.5 m gives
                     # the turn room. Uniform across seeds, so the A/B comparison stays fair.


def corner_waypoints(c=CORNER_C):
    """4 loop corners (CCW from +x,+y), used by the mission runner."""
    return [(c, c), (-c, c), (-c, -c), (c, -c)]


def clear_zones(c=CORNER_C):
    """discs (cx, cy, r) kept obstacle-free: takeoff center + 4 corner waypoints."""
    return [(0.0, 0.0, MARGIN)] + [(cx, cy, CORNER_CLEAR) for cx, cy in corner_waypoints(c)]

# ---- the two study axes ----
# Obstacle COUNT is fixed at 100 for EVERY seed; density is varied by the GAP (the
# minimum surface spacing between obstacles), not by the count.
COUNT = 100                                                # obstacles per seed (unified)
SIZES = {"small": 0.15, "medium": 0.25, "large": 0.40}     # cylinder radius [m]
GAPS  = {"dense": 1.1, "medium": 1.4, "sparse": 1.8}       # min SURFACE gap [m]; widened
                                                           # (all >= drone diameter ~0.6 -> traversable;
                                                           #  capped so 100 obstacles still fit the +/-12 field)

# condition -> (size_key, gap_key)
CONDITIONS = {
    "small":    ("small",  "medium"),
    "large":    ("large",  "medium"),
    "dense":    ("medium", "dense"),
    "sparse":   ("medium", "sparse"),
    "baseline": ("medium", "medium"),   # medium size AND medium spacing
}

# 10-seed map. Count fixed at 100. The old 9,10 (baseline duplicates of 3,4) are
# dropped; density (dense/sparse) is now the GAP, so 9,10 are the sparse pair.
SEED_CONDITION = {
    1: "small",    2: "small",
    3: "baseline", 4: "baseline",
    5: "large",    6: "large",
    7: "dense",    8: "dense",
    9: "sparse",  10: "sparse",
}

DEFAULT_TEMPLATE = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds/default_36.sdf"
DEFAULT_OUTDIR = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds"


def generate_positions(n, area, min_dist, zones, rng):
    """Rejection-sample n obstacle centers with >= min_dist center spacing,
    keeping each clear zone (cx, cy, r) obstacle-free (takeoff + corner waypoints)."""
    pts = []
    half = area / 2.0
    attempts = 0
    while len(pts) < n and attempts < n * 1000:
        attempts += 1
        x = rng.uniform(-half, half)
        y = rng.uniform(-half, half)
        if any(math.hypot(x - cx, y - cy) < cr for cx, cy, cr in zones):
            continue
        if all(math.hypot(x - px, y - py) >= min_dist for px, py in pts):
            pts.append((x, y))
    return pts


def obstacle_block(i, x, y, r):
    return (
        f'    <model name="pylon_{i}">\n'
        f'      <static>true</static>\n'
        f'      <pose>{x:.3f} {y:.3f} {OBST_Z:.3f} 0 0 0</pose>\n'
        f'      <link name="link">\n'
        f'        <collision name="collision">\n'
        f'          <geometry><cylinder><radius>{r:.3f}</radius><length>{OBST_LENGTH:.1f}</length></cylinder></geometry>\n'
        f'        </collision>\n'
        f'        <visual name="visual">\n'
        f'          <geometry><cylinder><radius>{r:.3f}</radius><length>{OBST_LENGTH:.1f}</length></cylinder></geometry>\n'
        f'        </visual>\n'
        f'      </link>\n'
        f'    </model>\n'
    )


# Drone included statically so the Gazebo GUI shows it (a runtime `create`-spawned
# model does NOT sync to the gz GUI). PX4 then ATTACHES to it via
# PX4_GZ_MODEL_NAME=x500_lidar_3d_0 (set in g_bringup) instead of spawning. Placed at
# the cleared center (MARGIN disc) so it never overlaps an obstacle.
DRONE_NAME = "x500_lidar_3d_0"
DRONE_BLOCK = (
    "    <!-- Vehicle: static include so the Gazebo GUI renders it; PX4 attaches via\n"
    f"         PX4_GZ_MODEL_NAME={DRONE_NAME} (g_bringup) instead of spawning. -->\n"
    "    <include>\n"
    "      <uri>model://x500_lidar_3d</uri>\n"
    f"      <name>{DRONE_NAME}</name>\n"
    "      <pose>0 0 0.2 0 0 0</pose>\n"
    "    </include>\n"
)


def build_world(template_text, world_name, positions, radius, with_drone=True):
    # reuse the PX4 boilerplate (physics/ground/sun/spherical_coords).
    head = template_text
    # cut the old obstacles: from the obstacle comment (or first pylon) onward
    cut = head.find("<!-- Obstacles")
    if cut < 0:
        cut = head.find('<model name="pylon_')
    if cut < 0:
        cut = head.rfind("</world>")
    head = head[:cut]
    # rename the world so PX4_GZ_WORLD=<world_name> and /world/<world_name>/* match
    head = re.sub(r'<world name="[^"]*">', f'<world name="{world_name}">', head, count=1)

    drone = DRONE_BLOCK if with_drone else ""
    obstacles = "".join(obstacle_block(i, x, y, radius) for i, (x, y) in enumerate(positions))
    comment = f"    <!-- Obstacles: gen_world.py r={radius} count={len(positions)} (cylinders) -->\n"
    return head.rstrip() + "\n\n" + drone + comment + obstacles + "  </world>\n</sdf>\n"


def gen_one(seed, template_text, out_dir, with_drone=True):
    cond = SEED_CONDITION[seed]
    size_key, gap_key = CONDITIONS[cond]
    radius = SIZES[size_key]
    gap = GAPS[gap_key]
    count = COUNT
    min_dist = 2 * radius + gap

    rng = random.Random(seed)
    pts = generate_positions(count, AREA, min_dist, clear_zones(), rng)

    world_name = f"default_seed{seed}"
    sdf = build_world(template_text, world_name, pts, radius, with_drone=with_drone)
    out_path = os.path.join(out_dir, f"{world_name}.sdf")
    with open(out_path, "w") as f:
        f.write(sdf)

    # manifest sidecar (record only; collision_monitor reads the SDF itself)
    man_path = os.path.join(out_dir, f"{world_name}.obstacles.csv")
    with open(man_path, "w") as f:
        f.write("x,y,r\n")
        for x, y in pts:
            f.write(f"{x:.3f},{y:.3f},{radius:.3f}\n")

    print(f"  seed {seed:2d} [{cond:8s}] size={size_key}(r={radius}) "
          f"gap={gap_key}({gap}m) (want {count}, placed {len(pts)}) -> {out_path}")
    return len(pts), count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, help="single seed 1..10")
    ap.add_argument("--all", action="store_true", help="generate all 10 seeds")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="world SDF to reuse boilerplate from")
    ap.add_argument("--out-dir", default=DEFAULT_OUTDIR)
    ap.add_argument("--no-drone", action="store_true",
                    help="omit the static drone include (PX4 will spawn it; gz GUI won't show it)")
    args = ap.parse_args()

    with open(args.template) as f:
        template_text = f.read()

    seeds = list(range(1, 11)) if args.all else ([args.seed] if args.seed else [])
    if not seeds:
        ap.error("give --seed N or --all")
    os.makedirs(args.out_dir, exist_ok=True)
    print(f"template={args.template}  out={args.out_dir}  area={AREA}x{AREA} margin={MARGIN}")
    print(f"clear corners (kept obstacle-free) @ C={CORNER_C}, r={CORNER_CLEAR}: {corner_waypoints()}")
    for s in seeds:
        if s not in SEED_CONDITION:
            print(f"  seed {s}: not in 1..12, skip"); continue
        placed, want = gen_one(s, template_text, args.out_dir, with_drone=not args.no_drone)
        if placed < want:
            print(f"    ! only placed {placed}/{want} (field too tight for the spacing); "
                  f"raise --area or lower count for this condition")


if __name__ == "__main__":
    main()
