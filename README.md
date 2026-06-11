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
| G5 | Full loop + collision metric | 🟡 partial: collision metric verified + SUPER crosses the field, but SUPER commands a **descending** trajectory → drone grounds before the goal (open issue) |
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
  `NAV_RCL_ACT 0` / `NAV_DLL_ACT 0`. Under heavy load the Gazebo **GUI client
  (`gz sim -g`) starves ekf2** ("ekf2 missing data") — run headless / kill the
  GUI for reliable arming.
- **Takeoff (offboard-from-ground) is flaky — two distinct causes:**
  1. **Single-shot OFFBOARD/ARM drop (fixed).** `/keyboard_cmd` is one
     `std_msgs/String`; if the OFFBOARD or ARM message is dropped the drone sits
     in *Hold* (or armed-but-Hold) and never engages. `g_fly.py` now **resends
     OFFBOARD then ARM every 1 s until the climb starts** (z>0.6). Confirmed:
     re-publishing OFFBOARD flips nav-state Hold→Offboard.
  2. **[open] Armed+Offboard+full-thrust but no lift (intermittent).** Even with
     `arming_state=2`, `nav_state=14 (OFFBOARD)`, preflight OK and the controller
     commanding full up-thrust (`thrust_body z=-1.0`), the drone can stay on the
     ground. `actuator_motors` then shows an **uneven mix** (e.g. `[0.07, 0.39,
     0.03, 1.0]`) — thrust spent on attitude correction, not climb — i.e. a
     Gazebo physics / EKF-attitude divergence (drone effectively stuck/tilted).
     It worked cleanly *once* (G3/G4 + the first G5 traverse), so it's
     intermittent and environmental (PX4 SITL + this custom `x500_lidar_3d`
     model), not an integration defect. Needs a stable-takeoff recipe before G5
     collision stats can be collected at scale.
- **Collision metric is geometric, not a contact sensor** — `collision_monitor.py`
  parses pillar centers (cylinders r=0.25) from the world SDF and computes min
  clearance + debounced collision count from `/odometry`; no SDF edit / sim
  restart. Logic verified (reads correct clearance), but launch it *fresh per
  flight* — a long-lived instance can go stale on the best-effort odom QoS.
- **[G5 open issue] SUPER commands a descending trajectory** — with goal z=1.5 the
  drone takes off to 1.4 m then SUPER's `/super/pos_cmd` z steadily drops
  (`FP recv z=0.97→0.84…`) and the drone grounds before the goal. offboard.py
  tracks position-only and follows faithfully, so the descent is SUPER-side.
  **Likely cause:** `static_gazebo.yaml` sets `virtual_ground_height: -1.5`, but
  the real Gazebo floor is z=0 — SUPER thinks it has 1.5 m of room below and
  plans down into the real ground. (It was set to -1.5 only to clear the
  `z≈0.04` ground-start "odom below virtual ground" check.) **Next step:** raise
  it to ≈ -0.3 (below the start, just below the real floor) and re-test G5.

## Acknowledgements

Built on [SUPER](https://github.com/hku-mars/SUPER) and
[ROG-Map](https://github.com/hku-mars/ROG-Map) (HKU-MARS). PX4 SITL + Gazebo
Harmonic for simulation.
