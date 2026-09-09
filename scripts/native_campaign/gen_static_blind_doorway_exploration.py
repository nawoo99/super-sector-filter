#!/usr/bin/env python3
"""Generate the first static blind-doorway closed-loop audit pair.

This is an exploratory mechanism fixture, not an evaluation map.  The clear
member contains only the L-corridor.  The hazard member adds one full-height
static cylinder; every other point and every planner/filter parameter remains
identical.  The clear member is used to audit SUPER's naturally committed
trajectory against the hypothetical cylinder before exposing any policy to
the cylinder itself.
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
MANIFEST_PATH = SCRIPT_DIR / "static_blind_doorway_exploration_manifest.json"

MAP_CLEAR = "sbd1_c1_clear"
MAP_HAZARD = "sbd1_c1_hazard"
INITIAL_POSITION = (24.0, 0.0, 1.5)
INITIAL_YAW_RAD = math.pi / 2.0
ROUTE_WAYPOINTS = ((24.0, 24.0), (0.0, 24.0))

OBSTACLE_HEIGHT_M = 3.20
BODY_RADIUS_M = 0.20
WALL_THICKNESS_M = 0.30

# A real L corridor: the vehicle travels north between the inner/east walls,
# then turns west between the inner/north walls.  The 0.85 m opening between
# the route centre and the inner-wall endpoint is not a sensor slit; the free
# chamber east of the endpoint is 4.85 m wide after wall half-thicknesses.
WALLS = (
    Wall("inner_incoming", (21.5, -2.0), (21.5, 21.5)),
    Wall("inner_outgoing", (-2.0, 21.5), (23.0, 21.5)),
    Wall("outer_east", (28.0, -2.0), (28.0, 28.0)),
    Wall("outer_north", (-2.0, 28.0), (28.0, 28.0)),
)

# The route y=24 intersects this cylinder.  Its southern offset closes the
# narrow inner-wall side while leaving a broad, inflation-feasible northern
# bypass for Full/Adaptive after raw observation.
HAZARD_CENTER = (18.4, 23.3)
HAZARD_RADIUS_M = 1.20

# Isolated point on the cylinder surface where y=24 intersects its east face.
PROBE_CENTER = (
    HAZARD_CENTER[0]
    + math.sqrt(HAZARD_RADIUS_M**2 - (24.0 - HAZARD_CENTER[1]) ** 2),
    24.0,
)
PROBE_RADIUS_M = 0.12

ROUTE_CHECK_ANCHORS = (
    (24.0, 0.0),
    (24.0, 21.0),
    (24.0, 24.0),
    (22.0, 26.0),
    (15.0, 26.0),
    (0.0, 24.0),
)

LIVENESS_STATIONS = (
    {"name": "outgoing_x20", "position_xyz_m": [20.0, 26.0, 1.5]},
    {"name": "outgoing_x12", "position_xyz_m": [12.0, 26.0, 1.5]},
    {"name": "outgoing_x4", "position_xyz_m": [4.0, 26.0, 1.5]},
)

REPLAY_POSITION = (24.0, 21.7, 1.5)
REPLAY_YAW_DEG = 90.0
REPLAY_VELOCITY = (0.0, 7.0, 0.0)
REPLAY_TRAJECTORY_END = (18.8, 24.0, 1.5)
REPLAY_TRAJECTORY_DURATION_S = 0.95
REPLAY_RISK_HORIZON_S = 1.0


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
    for map_name, include_hazard in (
        (MAP_CLEAR, False),
        (MAP_HAZARD, True),
    ):
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
        "schema": "static-blind-doorway-exploration-v1",
        "role": (
            "exploratory closed-loop mechanism audit only; never pool with "
            "v1-v4, Map1-10, or a future held-out evaluation"
        ),
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "route_waypoints_xy_m": [list(point) for point in ROUTE_WAYPOINTS],
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
            "anchors_xy_m": [list(point) for point in ROUTE_CHECK_ANCHORS],
            "planning_horizon_m": 7.0,
        },
        "visibility_check": {
            "pre_reveal_position_xy_m": [24.0, 20.5],
            "reveal_position_xy_m": list(REPLAY_POSITION[:2]),
            "yaw_deg": REPLAY_YAW_DEG,
            "sector_half_angle_deg": 45.0,
        },
        "liveness_check": {
            "stations": list(LIVENESS_STATIONS),
            "yaw_deg": 180.0,
            "sector_half_angle_deg": 45.0,
            "sensing_horizon_m": 15.0,
            "minimum_geometric_support_points": 10,
        },
        "replay": {
            "position_xyz_m": list(REPLAY_POSITION),
            "yaw_deg": REPLAY_YAW_DEG,
            "velocity_xyz_mps": list(REPLAY_VELOCITY),
            "trajectory_end_xyz_m": list(REPLAY_TRAJECTORY_END),
            "trajectory_duration_s": REPLAY_TRAJECTORY_DURATION_S,
            "risk_horizon_s": REPLAY_RISK_HORIZON_S,
        },
        "closed_loop_audit_gate": {
            "clear_map_complete_contact_free": True,
            "clear_map_map_stale_max": 0,
            "clear_map_effective_full_open_max": 0,
            "clear_map_hypothetical_committed_conflict_required": True,
            "hazard_shadow_exact_occupied_min": 2,
            "hazard_shadow_exact_occupied_before_contact": True,
            "hazard_shadow_pre_probe_full_open_allowed": False,
        },
        "generator_sha256": sha256(Path(__file__)),
        "shared_geometry_generator_sha256": sha256(
            SCRIPT_DIR / "gen_static_blind_corner_supplement.py"
        ),
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
