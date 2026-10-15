import sys, os
sys.path.insert(0, "/root/commands/super_gazebo")
import gen_world as gw

# SAME dense field as seed7 (RNG seed 7, dense gap), but corners NOT cleared:
# CORNER_CLEAR 2.5 -> 0.8 so obstacles sit right in the ~135deg turn path.
gw.CORNER_CLEAR = 0.8

SEED_SRC = 7                      # reuse seed7's density (dense) + RNG layout
NEW_NAME = "default_seed77"       # distinct name so we don't overwrite seed7
cond = gw.SEED_CONDITION[SEED_SRC]
size_key, gap_key = gw.CONDITIONS[cond]
radius = gw.SIZES[size_key]; gap = gw.GAPS[gap_key]
min_dist = 2*radius + gap
import random
rng = random.Random(SEED_SRC)
pts = gw.generate_positions(gw.COUNT, gw.AREA, min_dist, gw.clear_zones(), rng)

with open(gw.DEFAULT_TEMPLATE) as f: tmpl = f.read()
sdf = gw.build_world(tmpl, NEW_NAME, pts, radius, with_drone=True)
outdir = gw.DEFAULT_OUTDIR
with open(os.path.join(outdir, f"{NEW_NAME}.sdf"), "w") as f: f.write(sdf)
with open(os.path.join(outdir, f"{NEW_NAME}.obstacles.csv"), "w") as f:
    f.write("x,y,r\n")
    for x,y in pts: f.write(f"{x:.3f},{y:.3f},{radius:.3f}\n")

# how many obstacles now sit near the 4 corners (within 2.5m = the old clear radius)?
import math
corners = gw.corner_waypoints()
near = sum(1 for x,y in pts for cx,cy in corners if math.hypot(x-cx,y-cy) < 2.5)
print(f"{NEW_NAME}: cond={cond} r={radius} gap={gap} placed={len(pts)} | obstacles within 2.5m of corners = {near}")
print(f"  (baseline seed7 has 0 there — CORNER_CLEAR was 2.5)")
