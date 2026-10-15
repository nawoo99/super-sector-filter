# Seed-by-seed verification reference

Everything you need to run each seed yourself (gz GUI + RViz) and record sector-vs-adaptive.

## Modes (what each one is)

| mode | sector filter | recovery | g_mission flags |
|------|---------------|----------|-----------------|
| **full** | OFF (360°) | — | `--no-adaptive --sector-base off --risk-gate off --align-velocity off` |
| **sector** | ON, ±60° on **body-forward** | none | `--no-adaptive --sector-base on --risk-gate off --align-velocity off` |
| **adaptive** | ON, ±60° on **velocity dir** | velocity-aligned | `--no-adaptive --sector-base on --risk-gate off --align-velocity on` |

`FIXED_YAW=0.0` decouples heading from velocity → exposes the sector blindspot (this is the
scenario where adaptive is justified). Unset / `999` = heading tracks velocity (no blindspot).

## Per-seed settings

All seeds: **100 obstacles**, field **±15 m** (AREA 30), 4-corner loop at **±9**, altitude **1.5 m**.
Only the obstacle **radius** and **surface gap** differ:

| seed | condition | radius [m] | gap [m] | notes / expected blindspot signal |
|:----:|-----------|:----------:|:-------:|-----------------------------------|
| 1, 2 | small     | 0.15 | 1.4 | small pillars — medium signal |
| 3, 4 | baseline  | 0.25 | 1.4 | medium |
| 5, 6 | large     | 0.40 | 1.4 | big targets — medium/strong |
| **7, 8** | **dense** | 0.25 | **1.1** | **tight — strongest signal** (seed7: sector 2 → adaptive 0) |
| 9, 10 | sparse    | 0.25 | 1.8 | wide — **weak** (may not clip even when blind) |
| 77   | dense + cluttered corners | 0.25 | 1.1 | bonus: 9 obstacles at the turns (CORNER_CLEAR 0.8) |

## Commands

### Visual (Gazebo GUI + RViz, one loop)
```bash
# fixed-yaw blindspot demo — run sector, watch, super_exit, then adaptive
FIXED_YAW=0.0 bash /root/commands/super_gazebo/watch.sh <N> sector   gui
super_exit
FIXED_YAW=0.0 bash /root/commands/super_gazebo/watch.sh <N> adaptive gui
super_exit

# baseline (heading tracks velocity — no blindspot, for contrast)
bash /root/commands/super_gazebo/watch.sh <N> sector gui
super_exit
```
RViz: `/cloud_registered` = the ±60° wedge (green boxes). sector → wedge fixed to the nose;
adaptive → wedge rotates to follow motion. `/rog_map inf_occ` (red) = what the planner sees.
Collision count prints in the g_mission terminal.

### Headless metrics (numbers only, n=3, no GUI — faster)
```bash
# one seed, one mode, fixed-yaw, 3 runs -> CSV with collisions/min_clearance/pts
FIXED_YAW=0.0 python3 /root/commands/super_gazebo/g_campaign.py \
    --seeds <N> --runs 3 --modes sector   --mission-timeout 220 --out /tmp/s<N>_sector.csv
FIXED_YAW=0.0 python3 /root/commands/super_gazebo/g_campaign.py \
    --seeds <N> --runs 3 --modes adaptive --mission-timeout 220 --out /tmp/s<N>_adaptive.csv
```
Key CSV columns: `collisions`, `min_clearance_m`, `corners_reached`, `pts_mean`
(sector≈3000 = 64% savings; velocity-aligned adaptive should also ≈3000, full-view ≈9000).

## Environment variables (passed to g_bringup)

| var | default | effect |
|-----|:-------:|--------|
| `SECTOR` | true | sector filter on/off at bringup (`full` sets false) |
| `GUI` | 0 | `1` = Gazebo GUI on (drone visible; watch.sh `gui` sets this) |
| `FIXED_YAW` | 999.0 | hold heading at this deg (NED); 999 = track velocity |
| `RISK_GATE` | false | full-view risk-gate variant of adaptive (not used by the current adaptive) |
| `RISK_RANGE` | 2.0 | risk-gate trigger range [m] |
| `ALIGN_VEL` | false | velocity-aligned sector at bringup (adaptive publishes it at loop start anyway) |

## Common config (identical for all seeds)

- **Flight** (`config/static_gazebo.yaml`): max_vel 0.9, max_acc 3.5, max_jerk 25, altitude 1.5,
  planning_horizon 7, inflation 0.3 m (step 3), virtual band [0.2, 2.8].
- **Map** (ROG-Map): map_size [34,34,6], voxel_num [500,500,100] (KEEP ≤500 — bigger OOMs fsm),
  resolution 0.05.
- **Controller** (`controller/offboard.py`, SO3 attitude): hover_thr 0.70, thr_max 0.98,
  vmax_h 1.8, tilt_max 30°, alt_floor 0.85.
- **Sector** (`cloud_preprocessor`): ±60° (min/max_angle_deg ∓60), stride 2, voxel_leaf 0.15.
  Velocity-align: align_vmin 0.15 m/s, low-pass α 0.5, holds last travel dir through slowdowns.

## Record sheet

| seed | sector coll (n=3) | adaptive coll (n=3) | wedge behaviour (eyeball) |
|:----:|:-----------------:|:-------------------:|---------------------------|
| 7 | [2,2,2] (mine) | [0,0,0] (mine) | sector=fixed, adaptive=rotates |
| 8 | | | |
| 5 | | | |
| 6 | | | |
| … | | | |

## Teardown
`super_exit`  (or `tmux kill-server; pkill -9 -f 'gz sim'; pkill -9 -f fsm_node`).
Between seeds: ALWAYS `super_exit` before the next bringup. Don't close the Gazebo GUI window
alone mid-flight (corrupts the actuator bridge) — end the whole run with `super_exit`.
