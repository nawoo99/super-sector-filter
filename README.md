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
| G3 | SUPER plans a trajectory to a goal | ⚠️ goal interface works; A* needs the drone **airborne** (ground start is invalid) |
| G4 | PX4 follows SUPER's command (mars→quadrotor cmd converter) | ⬜ |
| G5 | Full loop + collision metric (Gazebo contact) | ⬜ |
| G6 | sector on/off comparison | ⬜ |

### Key findings / gotchas
- **PX4 SITL must run under a TTY (tmux)** — a plain background `&` makes its
  `pxh` shell hit EOF and exit (Gazebo survives, so only PX4 odom stops).
- **Transform from odom, not TF** — the TF buffer fails intermittently under
  `use_sim_time`.
- **`cloud_preprocessor` runs on wall clock** but passes through the cloud's
  sim-time stamp, which is what SUPER needs.
- **Ground start blocks planning** — the experiment must do *takeoff → stabilize
  → send goal*; a grounded drone's start is not in free space, so A* times out.
- SUPER's command output is `mars_quadrotor_msgs/PositionCommand`, a superset of
  `quadrotor_msgs/PositionCommand`, so a trivial field-copy converter bridges it
  to a PX4 offboard controller (G4, in progress).

## Acknowledgements

Built on [SUPER](https://github.com/hku-mars/SUPER) and
[ROG-Map](https://github.com/hku-mars/ROG-Map) (HKU-MARS). PX4 SITL + Gazebo
Harmonic for simulation.
