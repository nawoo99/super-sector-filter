#!/usr/bin/env python3
"""Generate the v3 open-bypass angular blind-turn development fixture.

This is a newly named component/Full-feasibility gate.  It preserves the v2
lower optical wall and hazard but removes the upper channel wall that turned
the outgoing leg into a local dead end.  No planner configuration is changed.
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
MANIFEST_PATH = SCRIPT_DIR / "angular_blind_turn_v3_gate_manifest.json"

MAP_NAME = "abt3_gate_open"
INITIAL_POSITION = (24.0, 0.0, 1.5)
INITIAL_YAW_RAD = math.pi / 2.0
ROUTE_WAYPOINTS = ((24.0, 24.0), (0.0, 24.0))

HAZARD_CENTER = (16.2, 24.4)
HAZARD_RADIUS_M = 1.20
OBSTACLE_HEIGHT_M = 3.20
BODY_RADIUS_M = 0.20

LOWER_WALL_Y_M = 23.00
WALL_WEST_X_M = 14.00
WALL_EAST_X_M = 23.20
WALL_THICKNESS_M = 0.30
APERTURE_CENTER_X_M = 19.65
APERTURE_WIDTH_M = 0.38

GUIDE_POSTS = tuple(
    Cylinder(x, y, 0.15)
    for y in (5.0, 10.0, 15.0)
    for x in (22.0, 26.0)
)

REPLAY_POSITION = (24.0, 23.5, 1.5)
REPLAY_YAW_DEG = 90.0
REPLAY_VELOCITY = (0.0, 7.0, 0.0)
REPLAY_TRAJECTORY_END = (16.2, 24.4, 1.5)
REPLAY_TRAJECTORY_DURATION_S = 1.15
REPLAY_RISK_HORIZON_S = 1.0

# The first anchor is within the planner's 7 m Euclidean horizon from the
# replay/corner state, but already commits to the north side of the hazard.
ROUTE_CHECK_ANCHORS = (
    (24.0, 23.5),
    (18.0, 26.1),
    (14.5, 26.1),
    (0.0, 24.0),
)


def walls() -> tuple[Wall, ...]:
    half = APERTURE_WIDTH_M / 2.0
    return (
        Wall(
            "lower_occluder_west",
            (WALL_WEST_X_M, LOWER_WALL_Y_M),
            (APERTURE_CENTER_X_M - half, LOWER_WALL_Y_M),
        ),
        Wall(
            "lower_occluder_east",
            (APERTURE_CENTER_X_M + half, LOWER_WALL_Y_M),
            (WALL_EAST_X_M, LOWER_WALL_Y_M),
        ),
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
    pcd_path = PCD_DIR / f"{MAP_NAME}.pcd"
    config_path = CONFIG_DIR / f"{MAP_NAME}.yaml"
    cylinders = [*GUIDE_POSTS, Cylinder(*HAZARD_CENTER, HAZARD_RADIUS_M)]
    wall_geometry = walls()
    point_count, wall_point_count = write_pcd(
        pcd_path, cylinders, wall_geometry
    )
    write_config(config_path, pcd_path.name)
    manifest = {
        "schema": "angular-blind-turn-v3-open-bypass-gate-v1",
        "purpose": "development gate only; do not pool with v1/v2/evaluation",
        "map": MAP_NAME,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "route_waypoints_xy_m": [list(point) for point in ROUTE_WAYPOINTS],
        "hazard": {
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "body_radius_m": BODY_RADIUS_M,
        "lower_wall": {
            "west_x_m": WALL_WEST_X_M,
            "east_x_m": WALL_EAST_X_M,
            "y_m": LOWER_WALL_Y_M,
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
            "aperture_center_x_m": APERTURE_CENTER_X_M,
            "aperture_width_m": APERTURE_WIDTH_M,
        },
        "upper_channel_wall_present": False,
        "guide_posts": [
            {"center_xy_m": [post.x, post.y], "radius_m": post.radius}
            for post in GUIDE_POSTS
        ],
        "replay": {
            "position_xyz_m": list(REPLAY_POSITION),
            "yaw_deg": REPLAY_YAW_DEG,
            "velocity_xyz_mps": list(REPLAY_VELOCITY),
            "trajectory_end_xyz_m": list(REPLAY_TRAJECTORY_END),
            "trajectory_duration_s": REPLAY_TRAJECTORY_DURATION_S,
            "risk_horizon_s": REPLAY_RISK_HORIZON_S,
        },
        "route_check": {
            "resolution_m": 0.10,
            "inflation_step": 3,
            "inflation_radius_m": 0.30,
            "flight_z_m": 1.50,
            "bounds_xy_m": [-1.0, 27.0, 20.0, 29.0],
            "anchors_xy_m": [list(point) for point in ROUTE_CHECK_ANCHORS],
            "planning_horizon_m": 7.0,
        },
        "point_count": point_count,
        "wall_point_count": wall_point_count,
        "pcd_sha256": sha256(pcd_path),
        "config_sha256": sha256(config_path),
        "runtime_root": str(SUPER_ROOT),
        "generator_sha256": sha256(Path(__file__)),
        "shared_geometry_generator_sha256": sha256(
            SCRIPT_DIR / "gen_static_blind_corner_supplement.py"
        ),
    }
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, MANIFEST_PATH)
    return manifest


def main() -> None:
    manifest = generate()
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
