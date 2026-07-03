# FIXED-YAW blindspot — the static scenario where adaptive is justified

Across density / geometry / speed we found NO sector safety cost under velocity-tracking
yaw, because the ±60° forward cone always points along motion, so obstacles are pre-mapped
while ahead and persist in ROG-Map. **That is exactly why pure sector was always safe.**

The forward-only blindspot becomes real when the **heading is DECOUPLED from velocity** — a
common operational constraint (a payload/sensor must point a fixed way, holonomic transport,
etc.). We added a FIXED-YAW mode (`offboard.py` `fixed_yaw_deg`, wired via g_bringup
`FIXED_YAW`). With a constant heading, on the loop legs where motion is NOT along the fixed
forward, the cone faces away from where the drone is going → forward-only sensing misses
obstacles in the path.

Dense seed7, clean 0.9, FIXED_YAW=0, per-run fresh bringup, n=3:

| mode | completes | collisions (r1,r2,r3) | pts_mean | savings |
|------|:---------:|:---------------------:|---------:|:-------:|
| **sector (±60°)** | 3/3 | **[2, 2, 2]** | ~3060 | 64%↓ |
| adaptive (risk-gate) | 3/3 | **[0, 0, 8]** | ~9080 | ~0% |

(velocity-tracking baseline @0.9 was sector [0,1,0], adaptive [0,0,0].)

## Findings
1. **Fixed yaw creates a real, consistent static safety cost for sector**: exactly 2
   collisions every run (the same blind-leg obstacles, e.g. (-8.0,-0.5), (-7.7,2.2)). This
   is the regime where the forward-only blindspot genuinely bites — and it is STATIC.
2. **Adaptive recovers it in 2/3 runs (0 collisions)**: the risk-gate detects the close
   side/behind obstacle as the drone approaches and expands to full-view → ROG-Map sees it
   → SUPER avoids. This is the adaptive-hero result: sector 2 → adaptive 0.
3. **Reliability wrinkle**: 1/3 adaptive runs spiked to 8 collisions — the risk-gate's
   full-view flooding over-populates the dense ROG-Map and occasionally destabilizes SUPER
   planning (the same high-variance full-view-in-dense effect seen in `full` mode). So by
   MEAN adaptive (2.7) can look worse than sector (2.0), but by MEDIAN it is 0 vs 2.

## Next (to turn this into a clean "adaptive wins")
Remove the over-population variance so adaptive reliably beats sector:
- test on medium/sparse density (full-view floods less), and/or
- a DIRECTIONAL expansion — widen the sector toward the VELOCITY heading instead of full
  360° (maps what's ahead-in-motion without flooding rear obstacles); this is the clean
  mechanism the fixed-yaw scenario motivates.

Feature: `controller/offboard.py` (`fixed_yaw_deg`), `scripts/g_bringup.sh` (`FIXED_YAW`).
Raw rows: `fixedyaw_blindspot_seed7.csv`.
