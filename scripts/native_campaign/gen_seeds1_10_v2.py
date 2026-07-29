#!/usr/bin/env python3
"""Regenerate seeds 1-10 with a bigger field + smaller obstacles, matching
seed11(reference)'s scale: AREA 40 (+-20, area~1600 m^2 vs seed11's 15x110=1650),
obstacle radius shifted down to seed11's estimated trunk-scale (0.10/0.15/0.20
vs old 0.15/0.25/0.40). Density axis (GAPS) and COUNT(100)/CONDITIONS/
SEED_CONDITION unchanged. Does NOT modify gen_world.py itself (keeps the
original Gazebo-campaign geometry reproducible); overrides module globals
locally for this regeneration only.
"""
import sys, os, shutil
sys.path.insert(0, "/root/commands/super_gazebo")
import gen_world as gw

# --- overrides ---
gw.AREA = 40.0                                          # +-20 (was 30/+-15)
gw.SIZES = {"small": 0.10, "medium": 0.15, "large": 0.20}  # was 0.15/0.25/0.40
CORNER_C_NEW = 12.0                                       # loop corners, was 9.0

out_dir = gw.DEFAULT_OUTDIR
backup_dir = os.path.join(out_dir, "backup_v1_seeds1-10")
os.makedirs(backup_dir, exist_ok=True)

template_text = open(gw.DEFAULT_TEMPLATE).read()

for seed in range(1, 11):
    # backup old files first
    for ext in ("sdf", "obstacles.csv"):
        src = os.path.join(out_dir, f"default_seed{seed}.{ext}")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, f"default_seed{seed}.{ext}"))

    cond = gw.SEED_CONDITION[seed]
    size_key, gap_key = gw.CONDITIONS[cond]
    radius = gw.SIZES[size_key]
    gap = gw.GAPS[gap_key]
    min_dist = 2 * radius + gap

    import random
    rng = random.Random(seed)
    zones = [(0.0, 0.0, gw.MARGIN)] + [(cx, cy, gw.CORNER_CLEAR) for cx, cy in gw.corner_waypoints(CORNER_C_NEW)]
    pts = gw.generate_positions(gw.COUNT, gw.AREA, min_dist, zones, rng)

    world_name = f"default_seed{seed}"
    sdf = gw.build_world(template_text, world_name, pts, radius, with_drone=False)
    with open(os.path.join(out_dir, f"{world_name}.sdf"), "w") as f:
        f.write(sdf)
    with open(os.path.join(out_dir, f"{world_name}.obstacles.csv"), "w") as f:
        f.write("x,y,r\n")
        for x, y in pts:
            f.write(f"{x:.3f},{y:.3f},{radius:.3f}\n")

    print(f"seed{seed:2d} [{cond:8s}] r={radius} gap={gap} area={gw.AREA} "
          f"(want {gw.COUNT}, placed {len(pts)}) -> {world_name}.sdf")

print(f"\n(구 버전 백업: {backup_dir})")
