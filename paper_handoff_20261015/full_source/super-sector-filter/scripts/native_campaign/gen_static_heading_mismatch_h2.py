#!/usr/bin/env python3
"""Generate shm1_h2 by changing only the h1 static hazard geometry."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Cylinder, sha256, write_pcd
from gen_static_heading_mismatch import (
    BODY_RADIUS_M, CONFIG_DIR, INITIAL_POSITION, INITIAL_YAW_RAD,
    MISSION_WAYPOINTS, OBSTACLE_HEIGHT_M, PCD_DIR, REPLAY_POSITION,
    REPLAY_VELOCITY, REPLAY_YAW_DEG, SCRIPT_DIR, SUPER_ROOT, WALLS,
    WALL_THICKNESS_M, write_config,
)


MANIFEST_PATH = SCRIPT_DIR / "static_heading_mismatch_h2_manifest.json"
MAP_CLEAR = "shm1_h2_clear"
MAP_HAZARD = "shm1_h2_hazard"
HAZARD_CENTER = (24.75, 3.40)
HAZARD_RADIUS_M = 0.12
PROBE_RADIUS_M = 0.17
REPLAY_TRAJECTORY_END = (24.55, 4.50, 1.5)


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    maps = []
    for map_name, include_hazard in ((MAP_CLEAR, False), (MAP_HAZARD, True)):
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        cylinders = [Cylinder(*HAZARD_CENTER, HAZARD_RADIUS_M)] if include_hazard else []
        point_count, wall_point_count = write_pcd(pcd_path, cylinders, WALLS)
        write_config(config_path, pcd_path.name)
        maps.append({
            "map": map_name,
            "include_hazard": include_hazard,
            "point_count": point_count,
            "wall_point_count": wall_point_count,
            "pcd_sha256": sha256(pcd_path),
            "config_sha256": sha256(config_path),
        })

    manifest = {
        "schema": "static-heading-mismatch-v2",
        "role": "exploratory shm1_h2; narrow-pole redesign after h1 edge reveal",
        "predecessor": "shm1_h1",
        "single_changed_factor": {
            "name": "hazard_geometry_xy_radius_m",
            "before": [24.0, 5.0, 1.2],
            "after": [*HAZARD_CENTER, HAZARD_RADIUS_M],
        },
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "mission_waypoints_xy_m": [list(point) for point in MISSION_WAYPOINTS],
        "body_radius_m": BODY_RADIUS_M,
        "walls": [{
            "name": wall.name,
            "start_xy_m": list(wall.start),
            "end_xy_m": list(wall.end),
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        } for wall in WALLS],
        "hazard": {
            "shape": "vertical_cylinder",
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
            "probe_radius_m": PROBE_RADIUS_M,
        },
        "route_check": {
            "resolution_m": 0.10,
            "inflation_step": 3,
            "flight_z_m": 1.50,
            "bounds_xy_m": [19.0, 29.0, -4.0, 24.0],
            "bypass_anchors_xy_m": [[24.0, 0.0], [23.6, 2.5], [23.6, 4.5], [24.0, 20.0]],
            "direct_route_segment_xy_m": [[24.52, 0.0], [24.52, 20.0]],
        },
        "visibility_check": {
            "position_xyz_m": list(REPLAY_POSITION),
            "body_yaw_deg": REPLAY_YAW_DEG,
            "velocity_yaw_deg": 90.0,
            "sector_half_angle_deg": 45.0,
            "sensing_horizon_m": 15.0,
        },
        "replay": {
            "position_xyz_m": list(REPLAY_POSITION),
            "yaw_deg": REPLAY_YAW_DEG,
            "velocity_xyz_mps": list(REPLAY_VELOCITY),
            "trajectory_end_xyz_m": list(REPLAY_TRAJECTORY_END),
            "trajectory_duration_s": 1.0,
            "risk_horizon_s": 1.0,
            "risk_min_points": 200,
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
