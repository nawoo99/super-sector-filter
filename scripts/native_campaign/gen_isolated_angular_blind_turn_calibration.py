#!/usr/bin/env python3
"""Generate the v2 isolated 90-degree angular blind-turn calibration.

The planner is frozen.  Every candidate uses the same controlled geometry and
differs only in the horizontal position of a 0.38 m optical aperture.  The
vehicle starts on the northbound leg, so the first waypoint switch is the
single critical north-to-west transition.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import (
    Cylinder,
    Wall,
    sha256,
    write_pcd,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "isolated_angular_blind_turn_manifest.json"

MAP_PREFIX = "abt2_cal_t"
APERTURE_CENTERS_X_M = (19.50, 19.575, 19.65, 19.725, 19.80)
APERTURE_WIDTH_M = 0.38
HAZARD_CENTER = (16.20, 24.40)
HAZARD_RADIUS_M = 1.20
OBSTACLE_HEIGHT_M = 3.20
BODY_RADIUS_M = 0.20

LOWER_WALL_Y_M = 23.00
UPPER_WALL_Y_M = 26.00
WALL_WEST_X_M = 14.00
WALL_EAST_X_M = 23.20
WALL_THICKNESS_M = 0.30

INITIAL_POSITION = (24.0, 0.0, 1.5)
INITIAL_YAW_RAD = math.pi / 2.0
ROUTE_WAYPOINTS = ((24.0, 24.0), (0.0, 24.0))
GUIDE_POSTS = tuple(
    Cylinder(x, y, 0.15)
    for y in (5.0, 10.0, 15.0)
    for x in (22.0, 26.0)
)

# Surface patches are deliberately disjoint from either wall.  Each patch is
# centred on the first hazard surface exposed by its corresponding aperture,
# rather than on the hazard centre (which made the v1 probe overlap a wall).
PROBE_CENTERS_XY_M = (
    (17.00789, 25.28731),
    (17.00789, 25.28731),
    (16.97028, 25.32014),
    (16.97028, 25.32014),
    (16.97028, 25.32014),
)
PROBE_RADIUS_M = 0.12


def walls_for_aperture(center_x: float) -> tuple[Wall, ...]:
    half = APERTURE_WIDTH_M / 2.0
    return (
        Wall(
            "lower_occluder_west",
            (WALL_WEST_X_M, LOWER_WALL_Y_M),
            (center_x - half, LOWER_WALL_Y_M),
        ),
        Wall(
            "lower_occluder_east",
            (center_x + half, LOWER_WALL_Y_M),
            (WALL_EAST_X_M, LOWER_WALL_Y_M),
        ),
        Wall(
            "upper_channel",
            (WALL_WEST_X_M, UPPER_WALL_Y_M),
            (WALL_EAST_X_M, UPPER_WALL_Y_M),
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
    maps = []
    common_cylinders = list(GUIDE_POSTS) + [
        Cylinder(*HAZARD_CENTER, HAZARD_RADIUS_M)
    ]
    for tier, (aperture_x, probe_center) in enumerate(
        zip(APERTURE_CENTERS_X_M, PROBE_CENTERS_XY_M), start=1
    ):
        map_name = f"{MAP_PREFIX}{tier}"
        walls = walls_for_aperture(aperture_x)
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        point_count, wall_point_count = write_pcd(
            pcd_path, common_cylinders, walls
        )
        write_config(config_path, pcd_path.name)
        maps.append(
            {
                "map": map_name,
                "tier": tier,
                "aperture_center_x_m": aperture_x,
                "aperture_width_m": APERTURE_WIDTH_M,
                "probe_center_xy_m": list(probe_center),
                "probe_radius_m": PROBE_RADIUS_M,
                "point_count": point_count,
                "wall_point_count": wall_point_count,
                "pcd_sha256": sha256(pcd_path),
                "config_sha256": sha256(config_path),
            }
        )

    manifest = {
        "schema": "isolated-angular-blind-turn-calibration-v2",
        "purpose": "calibration-only; never pool with v1 or evaluation",
        "map_prefix": MAP_PREFIX,
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "route_waypoints_xy_m": [list(point) for point in ROUTE_WAYPOINTS],
        "waypoint_switch_distance_m": 1.5,
        "critical_turn_deg": 90.0,
        "hazard": {
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "body_radius_m": BODY_RADIUS_M,
        "guide_posts": [
            {"center_xy_m": [post.x, post.y], "radius_m": post.radius}
            for post in GUIDE_POSTS
        ],
        "wall_geometry": {
            "west_x_m": WALL_WEST_X_M,
            "east_x_m": WALL_EAST_X_M,
            "lower_y_m": LOWER_WALL_Y_M,
            "upper_y_m": UPPER_WALL_Y_M,
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "validated_flight_z_envelope_m": [0.5, 2.8],
        "design_max_speed_mps": 7.0,
        "minimum_required_reveal_lead_s": 0.4,
        "fixed_sector_half_angle_deg": 45.0,
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
    for item in manifest["maps"]:
        print(
            f"{item['map']}: aperture_x={item['aperture_center_x_m']:.2f} "
            f"points={item['point_count']} sha256={item['pcd_sha256']}"
        )
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
