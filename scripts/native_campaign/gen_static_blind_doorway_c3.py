#!/usr/bin/env python3
"""Generate the continuous-turn static blind-doorway c3 audit pair.

C3 preserves c2 geometry and changes the mission contract only: the vehicle
receives the west exit as its sole goal, so it follows the L corridor without
stopping at a synthetic corner waypoint to rotate and scan first.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Cylinder, sha256, write_pcd
from gen_static_blind_doorway_c2 import (
    HAZARD_CENTER,
    HAZARD_RADIUS_M,
    PROBE_CENTER,
    PROBE_RADIUS_M,
    REPLAY_POSITION,
    REPLAY_RISK_HORIZON_S,
    REPLAY_TRAJECTORY_DURATION_S,
    REPLAY_TRAJECTORY_END,
    REPLAY_VELOCITY,
    REPLAY_YAW_DEG,
)
from gen_static_blind_doorway_exploration import (
    BODY_RADIUS_M,
    CONFIG_DIR,
    INITIAL_POSITION,
    INITIAL_YAW_RAD,
    LIVENESS_STATIONS,
    OBSTACLE_HEIGHT_M,
    PCD_DIR,
    ROUTE_CHECK_ANCHORS,
    SCRIPT_DIR,
    SUPER_ROOT,
    WALLS,
    WALL_THICKNESS_M,
    write_config,
)


MANIFEST_PATH = SCRIPT_DIR / "static_blind_doorway_c3_manifest.json"
MAP_CLEAR = "sbd1_c3_clear"
MAP_HAZARD = "sbd1_c3_hazard"
MISSION_WAYPOINTS = ((0.0, 24.0),)
NOMINAL_OUTGOING_SEGMENT = ((24.0, 24.0), (0.0, 24.0))


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
        "schema": "static-blind-doorway-exploration-v3",
        "role": (
            "exploratory continuous-turn c3 audit only; preserve c1/c2 and "
            "never pool candidate selection with confirmatory evaluation"
        ),
        "selection_basis": {
            "predecessor": "sbd1_c2",
            "geometry_changed_from_c2": False,
            "c2_fixed_sector_clearance_m": 0.780,
            "c2_failure": (
                "the intermediate corner waypoint stopped the vehicle and "
                "rotated body yaw to 143.570 degrees before hazard passage"
            ),
            "mission_change": "remove intermediate (24,24) waypoint",
        },
        "maps": maps,
        "initial_position_xyz_m": list(INITIAL_POSITION),
        "initial_yaw_rad": INITIAL_YAW_RAD,
        "mission_waypoints_xy_m": [list(point) for point in MISSION_WAYPOINTS],
        "route_waypoints_xy_m": [
            list(point) for point in NOMINAL_OUTGOING_SEGMENT
        ],
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
            "clear_sector_complete_contact_free": True,
            "clear_sector_effective_full_open_max": 0,
            "clear_sector_hypothetical_committed_conflict_required": True,
            "hazard_sector_degradation_required": True,
            "hazard_shadow_exact_occupied_min": 2,
            "hazard_shadow_pre_reveal_full_open_allowed": False,
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
