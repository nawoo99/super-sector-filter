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
AREA = 24.0          # square field side [m]; obstacles in [-AREA/2, AREA/2]
MARGIN = 3.0         # central takeoff-clear radius [m] (drone starts at 0,0)
OBST_LENGTH = 3.0    # cylinder height [m]; spans z in [0, 3], drone flies at 1.5
OBST_Z = OBST_LENGTH / 2.0
GAP = 0.9            # min SURFACE gap between obstacles [m]; >= drone diameter (~0.6)
                     # so every random layout stays traversable

# ---- perimeter-loop waypoints (kept clear so the mission can hover/recover there) ----
CORNER_C = 9.0       # the 4 loop-corner waypoints sit at (+/-C, +/-C)
CORNER_CLEAR = 1.5   # clear radius [m] around each corner waypoint


def corner_waypoints(c=CORNER_C):
    """4 loop corners (CCW from +x,+y), used by the mission runner."""
    return [(c, c), (-c, c), (-c, -c), (c, -c)]


def clear_zones(c=CORNER_C):
    """discs (cx, cy, r) kept obstacle-free: takeoff center + 4 corner waypoints."""
    return [(0.0, 0.0, MARGIN)] + [(cx, cy, CORNER_CLEAR) for cx, cy in corner_waypoints(c)]

# ---- the two study axes ----
SIZES = {"small": 0.15, "medium": 0.25, "large": 0.40}     # cylinder radius [m]
COUNTS = {"dense": 160, "medium": 100, "sparse": 50}       # obstacle count (density)

# condition -> (size_key, count_key)
CONDITIONS = {
    "small":    ("small",  "medium"),
    "large":    ("large",  "medium"),
    "dense":    ("medium", "dense"),
    "sparse":   ("medium", "sparse"),
    "baseline": ("medium", "medium"),   # medium size AND medium spacing
}

# 12-seed map
SEED_CONDITION = {
    1: "small",   2: "small",
    3: "baseline", 4: "baseline",   # "medium size"  (= medium,medium)
    5: "large",   6: "large",
    7: "dense",   8: "dense",
    9: "baseline", 10: "baseline",  # "medium spacing" (= medium,medium)
    11: "sparse", 12: "sparse",
}

DEFAULT_TEMPLATE = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds/default_36.sdf"
DEFAULT_OUTDIR = "/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds"


def generate_positions(n, area, min_dist, zones, rng):
    """Rejection-sample n obstacle centers with >= min_dist center spacing,
    keeping each clear zone (cx, cy, r) obstacle-free (takeoff + corner waypoints)."""
    pts = []
    half = area / 2.0
    attempts = 0
    while len(pts) < n and attempts < n * 400:
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


def build_world(template_text, world_name, positions, radius):
    # reuse the PX4 boilerplate (physics/ground/sun/spherical_coords); the PX4
    # drone model is added at runtime, so the world only needs ground + obstacles.
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

    obstacles = "".join(obstacle_block(i, x, y, radius) for i, (x, y) in enumerate(positions))
    comment = f"    <!-- Obstacles: gen_world.py r={radius} count={len(positions)} (cylinders) -->\n"
    return head.rstrip() + "\n\n" + comment + obstacles + "  </world>\n</sdf>\n"


def gen_one(seed, template_text, out_dir):
    cond = SEED_CONDITION[seed]
    size_key, count_key = CONDITIONS[cond]
    radius = SIZES[size_key]
    count = COUNTS[count_key]
    min_dist = 2 * radius + GAP

    rng = random.Random(seed)
    pts = generate_positions(count, AREA, min_dist, clear_zones(), rng)

    world_name = f"default_seed{seed}"
    sdf = build_world(template_text, world_name, pts, radius)
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
          f"spacing={count_key}(want {count}, placed {len(pts)}) -> {out_path}")
    return len(pts), count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, help="single seed 1..12")
    ap.add_argument("--all", action="store_true", help="generate all 12 seeds")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="world SDF to reuse boilerplate from")
    ap.add_argument("--out-dir", default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    with open(args.template) as f:
        template_text = f.read()

    seeds = list(range(1, 13)) if args.all else ([args.seed] if args.seed else [])
    if not seeds:
        ap.error("give --seed N or --all")
    os.makedirs(args.out_dir, exist_ok=True)
    print(f"template={args.template}  out={args.out_dir}  area={AREA}x{AREA} margin={MARGIN}")
    print(f"clear corners (kept obstacle-free) @ C={CORNER_C}, r={CORNER_CLEAR}: {corner_waypoints()}")
    for s in seeds:
        if s not in SEED_CONDITION:
            print(f"  seed {s}: not in 1..12, skip"); continue
        placed, want = gen_one(s, template_text, args.out_dir)
        if placed < want:
            print(f"    ! only placed {placed}/{want} (field too tight for the spacing); "
                  f"raise --area or lower count for this condition")


if __name__ == "__main__":
    main()
