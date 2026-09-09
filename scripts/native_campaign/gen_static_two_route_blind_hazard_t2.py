#!/usr/bin/env python3
"""Generate sbd2_t2 with only the divider west endpoint changed from t1."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Cylinder, Wall, sha256, write_pcd
from gen_static_two_route_blind_hazard import (
    BODY_RADIUS_M,
    CONFIG_DIR,
    DECISION_POSITION,
    DECISION_YAW_DEG,
    HAZARD_CENTER,
    HAZARD_RADIUS_M,
    INITIAL_POSITION,
    INITIAL_YAW_RAD,
    LIVENESS_STATIONS,
    LOWER_ROUTE_SEGMENT,
    MISSION_WAYPOINTS,
    OBSTACLE_HEIGHT_M,
    PCD_DIR,
    PROBE_CENTER,
    PROBE_RADIUS_M,
    REPLAY_RISK_HORIZON_S,
    REPLAY_TRAJECTORY_DURATION_S,
    REPLAY_TRAJECTORY_END,
    REPLAY_VELOCITY,
    SCRIPT_DIR,
    SUPER_ROOT,
    WALL_THICKNESS_M,
    write_config,
)


MANIFEST_PATH = SCRIPT_DIR / "static_two_route_blind_hazard_t2_manifest.json"
MAP_CLEAR = "sbd2_t2_clear"
MAP_HAZARD = "sbd2_t2_hazard"
DIVIDER_WEST_X = 12.0
WALLS = (
    Wall("incoming_inner", (21.5, -2.0), (21.5, 18.0)),
    Wall("lower_south", (-2.0, 18.0), (21.5, 18.0)),
    Wall("route_divider", (DIVIDER_WEST_X, 23.0), (21.5, 23.0)),
    Wall("upper_north", (-2.0, 28.0), (28.0, 28.0)),
    Wall("outer_east", (28.0, -2.0), (28.0, 28.0)),
)
UPPER_ROUTE_ANCHORS = (
    (24.0, 0.0),
    (24.0, 20.5),
    (24.0, 25.5),
    (10.5, 25.5),
    (10.5, 20.5),
    (0.0, 20.5),
)


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
        "schema": "static-two-route-blind-hazard-v2",
        "role": "exploratory sbd2_t2; one-factor redesign after t1 Full failure",
        "predecessor": "sbd2_t1",
        "single_changed_factor": {
            "name": "divider_west_endpoint_x_m",
            "before": 2.0,
            "after": DIVIDER_WEST_X,
        },
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
            "divider_west_endpoint_xy_m": [DIVIDER_WEST_X, 23.0],
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
