#!/usr/bin/env python3
"""Generate the three preregistered static burst-dropout held-out pairs."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import Wall, sha256, write_pcd
from gen_static_heading_mismatch import (
    BODY_RADIUS_M,
    CONFIG_DIR,
    OBSTACLE_HEIGHT_M,
    PCD_DIR,
    SCRIPT_DIR,
    SUPER_ROOT,
    WALL_THICKNESS_M,
)


MANIFEST_PATH = SCRIPT_DIR / "static_burst_dropout_confirmation_manifest.json"
SENSING_RATE_HZ = 10
DROPOUT_WARMUP_S = 1.0
DROPOUT_PERIOD_S = 2.0
DROPOUT_DURATION_S = 0.5
DROPOUT_PHASE_S = 0.0
MISSION_WAYPOINTS = ((24.5, 20.0),)


VARIANTS = (
    {
        "id": "c1_mirror",
        "clear": "shc1_mirror_clear",
        "hazard_map": "shc1_mirror_hazard",
        "initial": (24.5, 0.0, 1.5),
        "initial_yaw_rad": 0.0,
        "walls": (
            Wall("west_wall", (21.0, -3.0), (21.0, 23.0)),
            Wall("east_wall", (29.0, -3.0), (29.0, 23.0)),
            Wall("route_divider", (25.5, 2.0), (25.5, 15.0)),
        ),
        "hazard": Wall(
            "west_branch_closure", (20.65, 4.0), (25.5, 4.0)
        ),
        "audit": (24.0, 4.0, 1.0),
        "bounds": (19.5, 30.0, -4.0, 24.0),
        "bypass": (
            (24.5, 0.0), (26.5, 1.0), (26.5, 16.0), (24.5, 20.0)
        ),
        "replay_end": (24.5, 5.0, 1.5),
        "body_yaw_deg": 0.0,
    },
    {
        "id": "c2_wide_offset",
        "clear": "shc2_wide_offset_clear",
        "hazard_map": "shc2_wide_offset_hazard",
        "initial": (24.5, 0.0, 1.5),
        "initial_yaw_rad": math.pi,
        "walls": (
            Wall("west_wall", (19.5, -3.0), (19.5, 23.0)),
            Wall("east_wall", (28.5, -3.0), (28.5, 23.0)),
            Wall("route_divider", (23.25, 2.25), (23.25, 15.5)),
        ),
        "hazard": Wall(
            "east_branch_closure", (23.25, 4.4), (28.35, 4.4)
        ),
        "audit": (25.0, 4.4, 1.0),
        "bounds": (18.5, 29.5, -4.0, 24.0),
        "bypass": (
            (24.5, 0.0), (21.75, 1.0), (21.75, 16.5), (24.5, 20.0)
        ),
        "replay_end": (24.5, 5.4, 1.5),
        "body_yaw_deg": 180.0,
    },
    {
        "id": "c3_near_short",
        "clear": "shc3_near_short_clear",
        "hazard_map": "shc3_near_short_hazard",
        "initial": (24.5, 0.0, 1.5),
        "initial_yaw_rad": math.pi,
        "walls": (
            Wall("west_wall", (20.25, -3.0), (20.25, 23.0)),
            Wall("east_wall", (28.25, -3.0), (28.25, 23.0)),
            Wall("route_divider", (23.8, 2.5), (23.8, 14.5)),
        ),
        "hazard": Wall(
            "east_branch_closure", (23.8, 3.6), (28.1, 3.6)
        ),
        "audit": (25.0, 3.6, 1.0),
        "bounds": (19.25, 29.25, -4.0, 24.0),
        "bypass": (
            (24.5, 0.0), (22.1, 1.0), (22.1, 15.5), (24.5, 20.0)
        ),
        "replay_end": (24.5, 4.6, 1.5),
        "body_yaw_deg": 180.0,
    },
)


def write_config(path: Path, pcd_name: str, initial, initial_yaw_rad: float) -> None:
    contents = f'''#############| For UAV simulation |#################################
pcd_name: "seed_maps/{pcd_name}"
mesh_resource: "package://perfect_drone_sim/meshes/yunque-M.dae"
init_position:
  x: {initial[0]:.2f}
  y: {initial[1]:.2f}
  z: {initial[2]:.2f}
init_yaw: {initial_yaw_rad:.12f}

#############|For LiDAR perception simulation |###############################
is_360lidar: true
polar_resolution: 0.4
downsample_res: 0.1
vertical_fov: 178.0
sensing_blind: 0.1
sensing_horizon: 15
sensing_rate: {SENSING_RATE_HZ}
print_time_consumption: false
lidar_type: 2
depth_image_en: false

#############| Held-out common sensor fault (default-off in code) |###########
sensor_burst_dropout:
  enabled: true
  warmup_s: {DROPOUT_WARMUP_S:.1f}
  period_s: {DROPOUT_PERIOD_S:.1f}
  duration_s: {DROPOUT_DURATION_S:.1f}
  phase_s: {DROPOUT_PHASE_S:.1f}
'''
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(contents)
    os.replace(temporary, path)


def variant_manifest(variant: dict, maps: list[dict]) -> dict:
    hazard = variant["hazard"]
    audit_x, audit_y, audit_radius = variant["audit"]
    initial = variant["initial"]
    return {
        "id": variant["id"],
        "maps": maps,
        "initial_position_xyz_m": list(initial),
        "initial_yaw_rad": variant["initial_yaw_rad"],
        "mission_waypoints_xy_m": [list(point) for point in MISSION_WAYPOINTS],
        "walls": [
            {
                "name": wall.name,
                "start_xy_m": list(wall.start),
                "end_xy_m": list(wall.end),
                "thickness_m": WALL_THICKNESS_M,
                "height_m": OBSTACLE_HEIGHT_M,
            }
            for wall in variant["walls"]
        ],
        "hazard": {
            "shape": "full_height_wall",
            "start_xy_m": list(hazard.start),
            "end_xy_m": list(hazard.end),
            "thickness_m": WALL_THICKNESS_M,
            "height_m": OBSTACLE_HEIGHT_M,
            "audit_center_xy_m": [audit_x, audit_y],
            "audit_radius_m": audit_radius,
        },
        "route_check": {
            "resolution_m": 0.10,
            "inflation_step": 3,
            "flight_z_m": 1.50,
            "bounds_xy_m": list(variant["bounds"]),
            "bypass_anchors_xy_m": [list(point) for point in variant["bypass"]],
            "direct_route_segment_xy_m": [[24.5, 0.0], [24.5, 20.0]],
        },
        "visibility_check": {
            "position_xyz_m": list(initial),
            "body_yaw_deg": variant["body_yaw_deg"],
            "velocity_yaw_deg": 90.0,
            "sector_half_angle_deg": 45.0,
            "sensing_horizon_m": 15.0,
        },
        "replay": {
            "position_xyz_m": list(initial),
            "yaw_deg": variant["body_yaw_deg"],
            "velocity_xyz_mps": [0.0, 7.0, 0.0],
            "trajectory_end_xyz_m": list(variant["replay_end"]),
            "trajectory_duration_s": 1.0,
            "risk_horizon_s": 1.0,
            "risk_min_points": 200,
        },
    }


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    generated_variants = []
    for variant in VARIANTS:
        maps = []
        for map_name, include_hazard in (
            (variant["clear"], False),
            (variant["hazard_map"], True),
        ):
            pcd_path = PCD_DIR / f"{map_name}.pcd"
            config_path = CONFIG_DIR / f"{map_name}.yaml"
            walls = variant["walls"] + (
                (variant["hazard"],) if include_hazard else ()
            )
            point_count, wall_point_count = write_pcd(pcd_path, [], walls)
            write_config(
                config_path,
                pcd_path.name,
                variant["initial"],
                variant["initial_yaw_rad"],
            )
            maps.append({
                "map": map_name,
                "include_hazard": include_hazard,
                "point_count": point_count,
                "wall_point_count": wall_point_count,
                "pcd_sha256": sha256(pcd_path),
                "config_sha256": sha256(config_path),
            })
        generated_variants.append(variant_manifest(variant, maps))

    manifest = {
        "schema": "static-burst-dropout-confirmation-v1",
        "role": "preregistered held-out finite static safety-transfer suite",
        "source_preregistration": (
            "docs/static_burst_dropout_confirmation_preregistration_20260910.md"
        ),
        "body_radius_m": BODY_RADIUS_M,
        "sensing_rate_hz": SENSING_RATE_HZ,
        "sensor_burst_dropout": {
            "enabled": True,
            "warmup_s": DROPOUT_WARMUP_S,
            "period_s": DROPOUT_PERIOD_S,
            "duration_s": DROPOUT_DURATION_S,
            "yaml_phase_s": DROPOUT_PHASE_S,
            "paired_run_phase_grid_s": [round(0.2 * index, 1)
                                         for index in range(10)],
        },
        "variants": generated_variants,
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
