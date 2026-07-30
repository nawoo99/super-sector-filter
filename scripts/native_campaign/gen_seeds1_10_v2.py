#!/usr/bin/env python3
"""Regenerate seeds 1-10 with a bigger field, matching seed1-10's mission TIME
(not area) to seed11: v4 already matched area (1600 vs seed11's 1650 m^2) and
density (0.10/m^2 each) but average speed still came out ~2x seed1's (~2.87 m/s)
vs seed11's (~1.40 m/s) -- a structural effect of seed11's long dense corridor,
not obstacle density. To close the mission-time gap (37s -> seed11's ~70s) the
loop path itself needs to roughly double: corner distance 12->24 (loop dist
105.9m->211.9m at the same ~2.87 m/s -> ~74s predicted). Field half-width kept
at corner+8m margin (same margin convention as v3/v4) -> AREA 64 (+-32,
4096 m^2, now LARGER than seed11's 1650 m^2 -- trades the old "same area"
framing for a "same mission duration" framing). Density held at 0.10/m^2 ->
COUNT 160->410. SIZES/GAPS/CONDITIONS/SEED_CONDITION unchanged from v4. Does
NOT modify gen_world.py itself (keeps the original Gazebo-campaign geometry
reproducible); overrides module globals locally for this regeneration only.
"""
import sys, os, shutil
sys.path.insert(0, "/root/commands/super_gazebo")
import gen_world as gw

# --- overrides ---
gw.AREA = 64.0                                          # +-32 (was 40.0/+-20)
gw.SIZES = {"small": 0.10, "medium": 0.15, "large": 0.20}  # unchanged from v4
gw.COUNT = 410                                          # was 160 -- keeps density
                                                          # ~0.10/m^2 (seed11-matched) now
                                                          # that AREA grew 1600->4096 m^2
CORNER_C_NEW = 24.0                                       # loop corners, was 12.0 --
                                                          # doubles loop path length
                                                          # (105.9m->211.9m) to close the
                                                          # mission-time gap vs seed11

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
