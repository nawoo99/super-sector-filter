#!/usr/bin/env python3
"""Generate shm1_h6 with only the h5 east-closure y coordinate changed."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Wall, sha256, write_pcd
from gen_static_heading_mismatch import (
    BODY_RADIUS_M, CONFIG_DIR, OBSTACLE_HEIGHT_M, PCD_DIR, SCRIPT_DIR,
    SUPER_ROOT, WALL_THICKNESS_M,
)
from gen_static_heading_mismatch_h5 import (
    INITIAL_POSITION, INITIAL_YAW_RAD, MISSION_WAYPOINTS, WALLS, write_config,
)


MANIFEST_PATH = SCRIPT_DIR / "static_heading_mismatch_h6_manifest.json"
MAP_CLEAR = "shm1_h6_clear"
MAP_HAZARD = "shm1_h6_hazard"
HAZARD_WALL = Wall("east_branch_closure", (23.5, 4.0), (27.85, 4.0))
AUDIT_CENTER = (25.0, 4.0)
AUDIT_RADIUS_M = 1.0
REPLAY_POSITION = INITIAL_POSITION
REPLAY_YAW_DEG = 180.0
REPLAY_VELOCITY = (0.0, 7.0, 0.0)
REPLAY_TRAJECTORY_END = (24.5, 5.0, 1.5)


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    maps = []
    for map_name, include_hazard in ((MAP_CLEAR, False), (MAP_HAZARD, True)):
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        walls = WALLS + ((HAZARD_WALL,) if include_hazard else ())
        point_count, wall_point_count = write_pcd(pcd_path, [], walls)
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
        "schema": "static-heading-mismatch-v6",
        "role": "exploratory near-fork branch-closure topology",
        "predecessor": "shm1_h5",
        "single_changed_factor": {
            "name": "east_branch_closure_y_m", "before": 8.0, "after": 4.0
        },
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "mission_waypoints_xy_m": [list(p) for p in MISSION_WAYPOINTS],
        "body_radius_m": BODY_RADIUS_M,
        "walls": [{
            "name": wall.name,
            "start_xy_m": list(wall.start),
            "end_xy_m": list(wall.end),
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        } for wall in WALLS],
        "hazard": {
            "shape": "full_height_wall",
            "start_xy_m": list(HAZARD_WALL.start),
            "end_xy_m": list(HAZARD_WALL.end),
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
            "audit_center_xy_m": list(AUDIT_CENTER),
            "audit_radius_m": AUDIT_RADIUS_M,
        },
        "route_check": {
            "resolution_m": 0.10,
            "inflation_step": 3,
            "flight_z_m": 1.50,
            "bounds_xy_m": [19.0, 29.0, -4.0, 24.0],
            "bypass_anchors_xy_m": [
                [24.5, 0.0], [22.5, 1.0], [22.5, 16.0], [24.5, 20.0]
            ],
            "direct_route_segment_xy_m": [[24.5, 0.0], [24.5, 20.0]],
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
