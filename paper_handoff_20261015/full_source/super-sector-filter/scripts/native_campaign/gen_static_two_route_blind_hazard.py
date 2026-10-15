#!/usr/bin/env python3
"""Generate preregistered sbd2 two-route static blind-hazard pairs.

The clear and hazard members share a branching corridor.  The hazard member
adds exactly one full-height cylinder that closes the short lower branch while
an upper branch remains open.  This generator changes scenario data only.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Cylinder, Wall, sha256, write_pcd


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "static_two_route_blind_hazard_manifest.json"

MAP_CLEAR = "sbd2_t1_clear"
MAP_HAZARD = "sbd2_t1_hazard"
INITIAL_POSITION = (24.0, 0.0, 1.5)
INITIAL_YAW_RAD = math.pi / 2.0
MISSION_WAYPOINTS = ((0.0, 20.5),)

OBSTACLE_HEIGHT_M = 3.20
BODY_RADIUS_M = 0.20
WALL_THICKNESS_M = 0.30

# The east chamber joins two westbound routes.  The horizontal divider ends at
# x=2 on the west and x=21.5 on the east.  A vehicle that chooses the lower
# branch must return to one of those endpoints before crossing to the upper
# route.
WALLS = (
    Wall("incoming_inner", (21.5, -2.0), (21.5, 18.0)),
    Wall("lower_south", (-2.0, 18.0), (21.5, 18.0)),
    Wall("route_divider", (2.0, 23.0), (21.5, 23.0)),
    Wall("upper_north", (-2.0, 28.0), (28.0, 28.0)),
    Wall("outer_east", (28.0, -2.0), (28.0, 28.0)),
)

# The lower corridor has 4.70 m surface-to-surface width.  Cylinder diameter
# 4.20 m leaves only 0.25 m geometric gaps; 0.30 m map inflation closes them.
HAZARD_CENTER = (15.0, 20.5)
HAZARD_RADIUS_M = 2.10
PROBE_CENTER = (HAZARD_CENTER[0] + HAZARD_RADIUS_M, HAZARD_CENTER[1])
PROBE_RADIUS_M = 0.12

DECISION_POSITION = (24.0, 19.0, 1.5)
DECISION_YAW_DEG = 90.0
REPLAY_VELOCITY = (0.0, 7.0, 0.0)
REPLAY_TRAJECTORY_END = (16.8, 20.5, 1.5)
REPLAY_TRAJECTORY_DURATION_S = 1.0
REPLAY_RISK_HORIZON_S = 1.0

UPPER_ROUTE_ANCHORS = (
    (24.0, 0.0),
    (24.0, 20.5),
    (24.0, 25.5),
    (0.0, 25.5),
    (0.0, 20.5),
)
LOWER_ROUTE_SEGMENT = ((24.0, 20.5), (0.0, 20.5))
LIVENESS_STATIONS = (
    {"name": "incoming", "position_xyz_m": [24.0, 12.0, 1.5], "yaw_deg": 90.0},
    {"name": "junction", "position_xyz_m": [24.0, 20.0, 1.5], "yaw_deg": 90.0},
    {"name": "upper", "position_xyz_m": [12.0, 25.5, 1.5], "yaw_deg": 180.0},
)


def write_config(path: Path, pcd_name: str) -> None:
    contents = f'''#############| For UAV simulation |#################################
pcd_name: "seed_maps/{pcd_name}"
mesh_resource: "package://perfect_drone_sim/meshes/yunque-M.dae"
init_position:
  x: {INITIAL_POSITION[0]:.1f}
  y: {INITIAL_POSITION[1]:.1f}
  z: {INITIAL_POSITION[2]:.1f}
init_yaw: {INITIAL_YAW_RAD:.12f}

#############|For LiDAR perception simulation |###############################
is_360lidar: true
polar_resolution: 0.4
downsample_res: 0.1
vertical_fov: 178.0
sensing_blind: 0.1
sensing_horizon: 15
sensing_rate: 10
print_time_consumption: false
lidar_type: 2
depth_image_en: false
'''
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(contents)
    os.replace(temporary, path)


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    maps = []
    for map_name, include_hazard in ((MAP_CLEAR, False), (MAP_HAZARD, True)):
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        cylinders = (
            [Cylinder(*HAZARD_CENTER, HAZARD_RADIUS_M)]
            if include_hazard else []
        )
        point_count, wall_point_count = write_pcd(pcd_path, cylinders, WALLS)
        write_config(config_path, pcd_path.name)
        maps.append(
            {
                "map": map_name,
                "include_hazard": include_hazard,
                "point_count": point_count,
                "wall_point_count": wall_point_count,
                "pcd_sha256": sha256(pcd_path),
                "config_sha256": sha256(config_path),
            }
        )

    manifest = {
        "schema": "static-two-route-blind-hazard-v1",
        "role": (
            "preregistered exploratory sbd2 topology; never pool candidate "
            "selection with confirmatory or Map1-10 results"
        ),
        "preregistration": "docs/static_two_route_preregistration_20260909.md",
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "mission_waypoints_xy_m": [list(point) for point in MISSION_WAYPOINTS],
        "body_radius_m": BODY_RADIUS_M,
        "walls": [
            {
                "name": wall.name,
                "start_xy_m": list(wall.start),
                "end_xy_m": list(wall.end),
                "thickness_m": WALL_THICKNESS_M,
                "height_m": OBSTACLE_HEIGHT_M,
            }
            for wall in WALLS
        ],
        "hazard": {
            "shape": "vertical_cylinder",
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
            "probe_center_xy_m": list(PROBE_CENTER),
            "probe_radius_m": PROBE_RADIUS_M,
        },
        "route_check": {
            "resolution_m": 0.10,
            "inflation_step": 3,
            "inflation_radius_m": 0.30,
            "flight_z_m": 1.50,
            "bounds_xy_m": [-3.0, 29.0, -3.0, 29.0],
            "upper_route_anchors_xy_m": [list(point) for point in UPPER_ROUTE_ANCHORS],
            "lower_route_segment_xy_m": [list(point) for point in LOWER_ROUTE_SEGMENT],
            "divider_east_endpoint_xy_m": [21.5, 23.0],
            "planning_horizon_m": 7.0,
        },
        "visibility_check": {
            "decision_position_xyz_m": list(DECISION_POSITION),
            "yaw_deg": DECISION_YAW_DEG,
            "sector_half_angle_deg": 45.0,
            "sensing_horizon_m": 15.0,
        },
        "liveness_check": {
            "stations": list(LIVENESS_STATIONS),
            "sector_half_angle_deg": 45.0,
            "sensing_horizon_m": 15.0,
            "minimum_geometric_support_points": 10,
        },
        "replay": {
            "position_xyz_m": list(DECISION_POSITION),
            "yaw_deg": DECISION_YAW_DEG,
            "velocity_xyz_mps": list(REPLAY_VELOCITY),
            "trajectory_end_xyz_m": list(REPLAY_TRAJECTORY_END),
            "trajectory_duration_s": REPLAY_TRAJECTORY_DURATION_S,
            "risk_horizon_s": REPLAY_RISK_HORIZON_S,
            "risk_min_points": 200,
        },
        "closed_loop_gate": {
            "common_timeout_s": 90.0,
            "clear_sector_hypothetical_committed_conflict_required": True,
            "full_complete_contact_free_required": True,
            "sector_degradation_required": True,
            "adaptive_complete_contact_free_required": True,
            "adaptive_hazard_matched_exact_min": 2,
            "adaptive_effective_full_open_min": 1,
        },
        "generator_sha256": sha256(Path(__file__)),
        "runtime_root": str(SUPER_ROOT),
    }
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, MANIFEST_PATH)
    return manifest


def main() -> None:
    print(json.dumps(generate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
