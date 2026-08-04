# Sector Filter for SUPER (LiDAR-native planner) on Gazebo/PX4

Integrating an adaptive **horizontal sector filter** into [SUPER](https://github.com/hku-mars/SUPER)
(HKU-MARS, *Science Robotics* 2025), a LiDAR-native high-speed MAV planner, and
running it on a **Gazebo + PX4 SITL** pipeline with a 360° LiDAR.

## Motivation

The sector filter restricts the horizontal field of view of the LiDAR point
cloud to a forward cone (±60°) **before** it is inserted into the occupancy map,
reducing the dominant raycasting cost of map updates.

**Why SUPER (and not EGO-Planner):** EGO-Planner is depth-camera oriented; a
depth camera's FoV (~87°) is already narrower than the ±60° sector, so the filter
removes almost nothing. SUPER is **LiDAR-native** and ingests the full 360° cloud
(via ROG-Map), so restricting to ±60° genuinely removes ~66% of points and cuts
the dominant raycasting cost.

Profiling on SUPER's `static_dense` benchmark (ROG-Map's built-in timing):

| Component | per-frame | rate | share |
|-----------|----------:|-----:|------:|
| Mapping (ROG-Map) | 14.7 ms | 10 Hz | 17% |
| Planning (super_planner) | 47.5 ms | 15 Hz | 83% |

Map update is dominated by raycasting + cache update (the point-count-scaling part
= 100% of map time), which the sector filter directly attacks. Note SUPER's planner
is unusually heavy, so the *system-level* CPU saving is capped by mapping's share
(~17%); the **mapping-layer** reduction (~55%) is the clean, rate-independent result.

## What's here

```
gz_super_bridge/        Our ROS2 package
  src/cloud_preprocessor.cpp   Gazebo /points (sensor) -> sector filter ->
                               odom-based world transform -> /cloud_registered
config/
  static_gazebo.yaml     SUPER config tuned for the Gazebo/PX4 ground-start setup
  static_gazebo.diff     diff vs SUPER's static_dense.yaml
scripts/
  g_bringup.sh           One-shot tmux bringup of the whole stack
  cmd_bridge.py          mars_quadrotor_msgs -> quadrotor_msgs PositionCommand
  g_fly.py               Takeoff -> hover -> goal sequencer (drives offboard.py)
  g6_analyze.py          sector ON/OFF perf-log comparison
  collision_monitor.py   geometric collision / min-obstacle-distance metric (G5)
  gen_world.py           bakes per-seed static obstacle worlds for the campaign
super_patches/
  pr44_pcl_conversions.patch   SUPER ROS2 build fix (unmerged upstream PR #44)
  pr45_isnan_cxx17.patch       SUPER ROS2 build fix (unmerged upstream PR #45)
```

## How the integration works

ROG-Map (SUPER's mapper) expects the cloud **already in the world frame** (it does
not apply TF; odom is only the raycast origin). So the world-frame transform is a
required step — and it's exactly where the sector filter lives:

```
Gazebo LiDAR /points (sensor frame, ~80k pts/frame)
   -> [sector filter ±60° in sensor frame]        # our contribution
   -> transform kept points to world (from /odometry, deterministic)
   -> /cloud_registered (world)
   -> SUPER ROG-Map -> occupancy -> planner
```

The transform uses the **odometry message directly** (not the TF buffer), because
under `use_sim_time` the TF buffer fails intermittently. In this Gazebo setup
`body->lidar` and `world->map` are identity, so the odom pose *is* the world
transform.

`sector_enable` (param) toggles the filter on/off for the A/B comparison. SUPER
source is **not modified** for the filter — it lives entirely in `cloud_preprocessor`.

## Setup (Ubuntu 22.04 + ROS 2 Humble)

1. Clone & build SUPER (ROS2):
   ```bash
   cd super_ws/src && git clone https://github.com/hku-mars/SUPER.git
   cd SUPER && bash scripts/select_ros_version.sh ROS2
   git apply ../../super_patches/pr45_isnan_cxx17.patch    # from this repo
   git apply ../../super_patches/pr44_pcl_conversions.patch
   ```
   Deps: `libglfw3-dev libglew-dev libncurses5-dev libeigen3-dev libdw-dev
   libfmt-dev ros-humble-pcl-conversions ros-humble-pcl-ros ros-humble-mavros-msgs`
2. Copy `config/static_gazebo.yaml` into `super_planner/config/`.
3. Drop `gz_super_bridge/` into the workspace `src/` and `colcon build`.
4. Bring up: `bash scripts/g_bringup.sh default_36`
   (needs the Gazebo/PX4 + 360° LiDAR + odom pipeline; topics `/points`, `/odometry`).

## Verification progress

| Gate | What | Status |
|------|------|--------|
| Build | SUPER ROS2 Humble (+2 patches) | ✅ |
| G1 | `/cloud_registered` overlaps obstacles in world frame | ✅ (99% within 2 m) |
| G2 | ROG-Map builds occupancy from the Gazebo cloud | ✅ (17k cells, 100% within 2 m) |
| G3 | SUPER plans a trajectory to a goal | ✅ takeoff to 1.5 m, then goal → SUPER plans & executes (fsm WAIT_GOAL→exec→WAIT_GOAL) |
| G4 | PX4 follows SUPER's command (mars→quadrotor cmd bridge) | ✅ drone autonomously flew to the goal (reached, d=0.6 m) |
| G5 | Field traversal + collision metric | ✅ 12 m traverse to goal (d=0.5 m), altitude held 1.0–1.5 m, metrics: min clearance 0.29 m, **1 collision** (sector ON) |
| G6 | sector on/off comparison | ✅ ~55% fewer points → **~66% lower ROG-Map update time** |

### G6 result — sector filter effect on ROG-Map cost

Controlled A/B at a fixed drone pose (same scene, only `sector_enable` toggled;
`rm_performance_log.csv`, ~460/710 steady-state frames):

| metric | sector ON | sector OFF | reduction |
|--------|----------:|-----------:|----------:|
| PointCloudNumber | 1553 pts | 3474 pts | 55.3% |
| Raycast | 0.172 ms | 0.522 ms | **67.1%** |
| Total (map update) | 0.282 ms | 0.830 ms | **66.1%** |
| Update_cache | 0.109 ms | 0.307 ms | 64.6% |

The raycast-time reduction (67%) exceeds the point reduction (55%): the sector
drops the *long* rear/side rays into open space (max-range), while the kept
forward cone is obstacle-blocked (short rays) — so per-point raycast saving is
amplified. (Absolute times are small here because voxel(0.15)+stride(2) already
thin the cloud; the **relative** reduction is the rate-independent contribution.)
Reproduce: `python3 scripts/g6_analyze.py`.

### Key findings / gotchas
- **PX4 SITL must run under a TTY (tmux)** — a plain background `&` makes its
  `pxh` shell hit EOF and exit (Gazebo survives, so only PX4 odom stops).
- **Transform from odom, not TF** — the TF buffer fails intermittently under
  `use_sim_time`.
- **`cloud_preprocessor` runs on wall clock** but passes through the cloud's
  sim-time stamp, which is what SUPER needs.
- **Ground start blocks planning** — the experiment must do *takeoff → stabilize
  → send goal*; a grounded drone's start is not in free space, so A* times out.
  `g_fly.py` climbs to 1.5 m and holds before issuing the goal.
- **SUPER and offboard.py both want `/planning/pos_cmd` but with different
  message types** (`mars_quadrotor_msgs` vs `quadrotor_msgs` — different type
  hash ⇒ no connection). SUPER's output is remapped to `/super/pos_cmd` and
  `cmd_bridge.py` copies the common field subset onto `/planning/pos_cmd`.
  Neither SUPER nor offboard.py is modified.
- **OFFBOARD arming needs `COM_RCL_EXCEPT 4`** — otherwise PX4 preflight blocks
  arming with "No connection to the GCS". `g_bringup.sh` also sets
  `NAV_RCL_ACT 0` / `NAV_DLL_ACT 0` / `COM_ARM_WO_GPS 0`.
- **Run Gazebo HEADLESS — do NOT kill the GUI after start (the key takeoff fix).**
  Killing `gz sim -g` after startup corrupts the gz_bridge **actuator** forwarding:
  PX4 motor outputs never reach `/model/.../command/motor_speed`, so the rotors
  stay silent even though PX4 is armed+OFFBOARD and commands full up-thrust
  (`thrust_body z=-1.0`; `actuator_motors` go to an uneven attitude-saturating mix
  and the drone never leaves the ground). `g_bringup.sh` launches with `HEADLESS=1`
  so the GUI client never starts — takeoff is then reliable (and cloud recovers to
  full 10 Hz). This was the long-standing "armed but no lift" blocker.
- **Single-shot OFFBOARD/ARM can drop** — `/keyboard_cmd` is one `std_msgs/String`;
  a dropped message leaves the drone in *Hold*. `g_fly.py` resends OFFBOARD then
  ARM every 1 s until the climb starts (z>0.6).
- **`virtual_ground_height` must sit just below the start, not far below the real
  floor.** Real Gazebo floor is z=0; setting it to -1.5 let SUPER plan a descent
  into the ground (drone sank before the goal). `static_gazebo.yaml` uses **-0.3**
  (below the `z≈0.04` ground start, just under the floor) — altitude is then held
  at ~1.5 m across the traverse.
- **Far goals time out in A\***; SUPER plans within the mapped/observed region, so
  drive it with goals a few metres out (the planned waypoint loop fits this).
- **Collision metric is geometric, not a contact sensor** — `collision_monitor.py`
  reads each obstacle's `(x, y, radius)` straight from the world SDF (matching
  `<model name="pylon_*/pillar_*">` → `<pose>` + cylinder `<radius>`, per obstacle)
  and computes min surface clearance + debounced collision count from `/odometry`;
  no SDF edit / sim restart. Launch it *fresh per flight* (a long-lived instance can
  go stale on the best-effort odom QoS).

## Legacy Gazebo campaign maps (seeded static worlds)

> This section records the earlier Gazebo/PX4 100-obstacle design. It is not the
> current native MARSIM seed1--10 geometry. The native v6 design is documented
> below; running `scripts/gen_world.py --all` regenerates these legacy worlds.

`gen_world.py` bakes a **complete static world SDF per seed** (cylinders only;
radius encodes obstacle size) by reusing the PX4 world boilerplate. This is the
*stable* path vs runtime `gz service` spawning: deterministic, no spawn failures,
sector-ON/OFF see a byte-identical world, and the **same SDF is the single source
of truth** for both Gazebo and `collision_monitor.py`.

10-seed design (one-factor-at-a-time, 2 replicates/condition). **Obstacle count is
fixed at 100 for every seed; density is varied by the GAP (min surface spacing
between obstacles), not the count:**

| seeds | condition | radius | gap | count |
|-------|-----------|-------:|----:|------:|
| 1,2   | small     | 0.15 | 1.1 | 100 |
| 3,4   | baseline  | 0.25 | 1.1 | 100 |
| 5,6   | large     | 0.40 | 1.1 | 100 |
| 7,8   | dense     | 0.25 | 0.8 | 100 |
| 9,10  | sparse    | 0.25 | 1.5 | 100 |

Size axis (1–6) varies the radius at a fixed gap; density axis (7–10 vs baseline)
varies the gap at a fixed radius. All gaps are >= the drone diameter (~0.6 m) so
every layout stays traversable, and capped so 100 obstacles fit the ±12 m field.

```bash
python3 scripts/gen_world.py --all        # writes default_seed1..10.sdf into PX4 worlds/
bash scripts/g_bringup.sh default_seed7   # HEADLESS, sector via SECTOR=true/false
python3 scripts/collision_monitor.py --world default_seed7
```

Field is square ±12 m (`AREA=24`); the SUPER map is therefore enlarged to
`map_size [28,28,6]` (the old `[15,110,6]` only covered x∈[±7.5] — obstacles past
that were unmapped/flown blind).

Validated end-to-end on `default_seed3` (100 obstacles): the baked world loads in
PX4, SUPER navigates the ±12 field to the goal, altitude holds, and
`collision_monitor` reads the 100 obstacles from the same SDF. **Gotcha for the
campaign:** place loop waypoints in obstacle-free spots — a goal sitting next to a
pillar makes the drone graze it while hovering and inflates the collision count
(score collisions during *transit*, not goal-hover).

## Campaign runner & analysis (Steps 4-5)

`g_campaign.py` automates the A/B/C study. For each seed world it brings the stack
up **once**, then flies the perimeter loop in three modes, `--runs` times each:

| mode | sector filter | g_mission flags |
|------|---------------|-----------------|
| `full`     | OFF the whole loop (360 view baseline)    | `--no-adaptive --sector-base off` |
| `sector`   | ON the whole loop (+/-60, no recovery)    | `--no-adaptive --sector-base on`  |
| `adaptive` | ON on legs, OFF (full-view) at corners    | (adaptive default) `--sector-base on` |

All three fly the identical waypoint path and dwell at corners, so only the filter
behaviour differs. Per `(seed, run, mode)` we record into `results/campaign.csv`:

- **mission time**, success, corners reached, leg timeouts
- **ROG-Map mapping cost** -- `Total / Raycast / Update_cache / Inflation` (ms) and
  `PointCloudNumber`, sliced to *exactly this mission's frames*. `g_mission` stamps
  the perf-log data-row range at loop start/end, so we slice cleanly without
  restarting the planner (the log is truncated only once per bring-up). ROG-Map
  logs `Total=0` on skipped frames (odom below the virtual-ground band / no new
  points), so we also report `*_active_mean` over frames that actually mapped.
- **CPU%** of `fsm_node` and `cloud_preprocessor` -- exact `utime+stime` delta from
  `/proc/<pid>/stat` over the loop window (picks the busiest matching pid so a
  ros2/shell wrapper can't be sampled by mistake).
- **collisions + min surface clearance** -- `collision_monitor.py`, fresh per run.

```bash
source /opt/ros/humble/setup.bash
python3 scripts/g_campaign.py --seeds 9 --runs 1                  # smoke: 1 seed (sparse) x 3 modes
python3 scripts/g_campaign.py --seeds 1-10 --runs 5              # full campaign
python3 scripts/g_analyze.py results/campaign.csv --csv-out tables.csv
```

`g_analyze.py` aggregates mean +/- std per mode and the headline **reduction vs the
`full` baseline**: the efficiency claim (sector cuts points / Total / Raycast / CPU)
against the safety cost (sector raises collisions / lowers clearance) and how much
of that safety the **adaptive** corner recovery buys back.

## Quick launchers & watching (RViz)

`scripts/super_aliases.sh` (source it from `~/.bashrc`) adds seed-indexed launchers,
EGO-style:

```bash
super 1          # seed-1 map, sector filter OFF (full 360 baseline)
super_sec 1      # seed-1 map, sector filter ON  (+/-60 cone)
super_watch 1 adaptive   # HEADLESS sim + RViz + one perimeter loop to eyeball
                         # mode = full | sector | adaptive
super_exit               # tear down the whole stack (sim + RViz + nodes)
```

The sim runs **HEADLESS** (the Gazebo GUI is the takeoff-stability fix — never
started). You watch in **RViz** instead (`scripts/super_watch.rviz`, fixed frame
`world`), which shows more than the Gazebo view would: the sector-filtered
`/cloud_registered` (a +/-60 wedge — or a full ring at corners in adaptive mode),
the ROG-Map occupancy the planner avoids (`/rog_map/inf_occ`), and SUPER's
committed trajectory + A* path + goal. All displays use Best-Effort QoS so they
bind to any publisher. Compare `super_watch N full` (full ring) vs
`super_watch N sector` (wedge) to *see* the mapping-cost reduction.

> `watch.sh` must guard the ROS `source` with `set +u; … ; set -u` — under `set -u`
> `source /opt/ros/humble/setup.bash` aborts the script (ROS setup references unset
> vars), which silently kills the launcher right before RViz.

## Native seed1--10 v6 obstacle-size sweep

The current native MARSIM maps keep the v5 mission scale (64 x 64 m, 410
cylinders, loop corners at +/-24 m) but replace the old size/density conditions
with one controlled size axis. Every map has a minimum **1.00 m physical
surface-to-surface gap**; seeds 1--2 through 9--10 use radii 0.150, 0.275,
0.400, 0.525, and 0.650 m respectively. Thus each tier changes radius by
0.125 m and diameter by a clearly visible 0.25 m (62.5% of the modeled
0.40 m drone diameter).

```bash
python3 scripts/native_campaign/gen_seeds1_10_v2.py
```

The exact tier table, gap definition, generated assets, backup locations, and
v5/v6 result-version boundary are in
[`docs/native_seed1_10_v6.md`](docs/native_seed1_10_v6.md). Existing v5 campaign
tables remain historical v5 evidence and must not be relabeled as v6; the v6
headline numbers require a fresh full campaign. A one-run endpoint smoke is in
[`results/native_seed1_10_v6_final_endpoint_smoke.csv`](results/native_seed1_10_v6_final_endpoint_smoke.csv);
it validates the selected upper tier but is not a replacement for that campaign.

## Native seed11 raw-input baseline

The campaign runner distinguishes the true raw LiDAR path from the historical
`full` mode. `raw` sends `/cloud_registered` directly to SUPER with the current
3 m/s planner settings; `full` keeps every point but still copies and republishes
the cloud through the Python filter. Rotate mode order when comparing them:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed11 --modes raw full sector adaptive --runs 10 --rotate-modes \
  --out results/native_seed11_pipeline_ablation_n10.csv
```

Mode `upstream` is a separate raw-direct 8 m/s public-example control. It is not
a reproduction of the paper's 60-map by 18-speed simulation protocol. The
comparison and interpretation boundary are recorded in
[`docs/paper_story.md`](docs/paper_story.md).

## Native seed12/13 blind-sector diagnostic

The native MARSIM campaign has two opt-in corner cases. `seed12` and its
reflected companion `seed13` inject a tagged three-cylinder trap only while its
complete silhouette is visible to the velocity-aligned sector and hidden from
the body-aligned sector:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed12 seed13 --modes sector adaptive --runs 5 \
  --out results/seed12_seed13_operational.csv
```

Use `SEED12_MATCHED_PREFIX=1` or `SEED13_MATCHED_PREFIX=1` for the stricter
control in which both runs use body-sector filtering until the trap's first
cloud frame. Protocol, metrics, initial results, and interpretation are in
[`docs/seed12_dynamic_scenario.md`](docs/seed12_dynamic_scenario.md).

## Native seed14/15 stall-recovery diagnostic

In the native runner, `adaptive` is the final hybrid: a velocity-aligned +/-60
degree sector while cruising, 360-degree view after an armed low-speed stall,
then velocity-sector again after sustained motion resumes. The former
velocity-only implementation remains available as mode `velocity`; `trigger`
uses the same fair startup/stall gate but keeps a body-yaw sector while closed.

Seed14 and seed15 use the same controlled approach to `(20,0)`, hold until
odometry speed has stayed below `0.6 m/s` for `1.6 s`, then release toward
mirrored final goals. A rear-open pocket is injected at the `x=18 m` crossing.
The barrier and mission driver are independent of filter state, and both rear
endpoints lie outside the closed `+/-60 degree` sector. This deliberately tests
the hybrid arm/open/reclose path; seed12/13 remain the unexpected-popup safety
tests. A recovery-specific map origin keeps the 40 m goal and bypass inside
ROG-Map:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed14 seed15 \
  --modes full sector velocity trigger adaptive --runs 3 \
  --out results/native_recovery_seed14_15_n3.csv
```

See [`docs/hybrid_adaptive_recovery.md`](docs/hybrid_adaptive_recovery.md) for
the state thresholds, validity checks, metrics, and visual watch commands.

## Acknowledgements

Built on [SUPER](https://github.com/hku-mars/SUPER) and
[ROG-Map](https://github.com/hku-mars/ROG-Map) (HKU-MARS). PX4 SITL + Gazebo
Harmonic for simulation.
