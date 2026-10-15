#!/usr/bin/env python3
"""Generate the preregistered static 90-degree blind-turn calibration set.

The family is intentionally separate from the frozen Map1--10 and ``occ_bw``
assets.  A northbound approach turns west into a bounded channel.  The lower
wall occludes a static hazard until shortly before the waypoint switch; Full
can retain that observation, fixed Sector cannot see it outside its 45-degree
crop, and Adaptive can test the newly committed westbound trajectory against
the raw-cloud window.  Only the hazard radius changes across the five
calibration severities.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import (
    Cylinder,
    Wall,
    load_cylinders,
    point_segment_distance,
    sha256,
    touches_patch,
    write_config,
    write_pcd,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "angular_blind_turn_calibration_manifest.json"

MAP_PREFIX = "abt_cal_s"
SOURCE_SEEDS = (1, 3, 5, 7, 9)
BACKGROUND_RADII_M = (0.150, 0.275, 0.400, 0.525, 0.650)
HAZARD_RADII_M = (1.10, 1.20, 1.30, 1.40, 1.50)
HAZARD_CENTER = (18.5, 24.0)
OBSTACLE_HEIGHT_M = 3.2
BODY_RADIUS_M = 0.20
BACKGROUND_ROUTE_CLEARANCE_M = 2.0

# Start -> east -> north -> west gives an exact 90-degree critical turn at
# (24, 24), rather than loop24's 135-degree first turn.
ROUTE_WAYPOINTS = (
    (0.0, 0.0),
    (24.0, 0.0),
    (24.0, 24.0),
    (-24.0, 24.0),
    (-24.0, -24.0),
    (24.0, -24.0),
    (0.0, 0.0),
)

WALL_THICKNESS_M = 0.30
WALL_EAST_X_M = 23.20
WALL_WEST_X_M = 14.00
LOWER_WALL_Y_M = 22.00
UPPER_WALL_Y_M = 25.20
WALLS = (
    Wall(
        "lower_occluder",
        (WALL_WEST_X_M, LOWER_WALL_Y_M),
        (WALL_EAST_X_M, LOWER_WALL_Y_M),
    ),
    Wall(
        "upper_channel",
        (WALL_WEST_X_M, UPPER_WALL_Y_M),
        (WALL_EAST_X_M, UPPER_WALL_Y_M),
    ),
)


def touches_route_corridor(cylinder: Cylinder) -> bool:
    centre_distance = min(
        point_segment_distance((cylinder.x, cylinder.y), start, end)
        for start, end in zip(ROUTE_WAYPOINTS, ROUTE_WAYPOINTS[1:])
    )
    return centre_distance <= (
        cylinder.radius + BACKGROUND_ROUTE_CLEARANCE_M + 1e-12
    )


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    maps = []
    for severity, values in enumerate(
        zip(SOURCE_SEEDS, BACKGROUND_RADII_M, HAZARD_RADII_M), start=1
    ):
        source_seed, background_radius, hazard_radius = values
        source_path = SCRIPT_DIR / f"seed{source_seed}_static.csv"
        source = load_cylinders(source_path)
        if len(source) != 410:
            raise ValueError(f"{source_path}: expected 410 cylinders")
        if any(
            not math.isclose(item.radius, background_radius, abs_tol=1e-9)
            for item in source
        ):
            raise ValueError(f"{source_path}: radius tier mismatch")
        retained = [
            item for item in source
            if not touches_patch(item) and not touches_route_corridor(item)
        ]
        removed = [item for item in source if item not in retained]
        cylinders = retained + [
            Cylinder(HAZARD_CENTER[0], HAZARD_CENTER[1], hazard_radius)
        ]
        map_name = f"{MAP_PREFIX}{severity}"
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        point_count, wall_point_count = write_pcd(
            pcd_path, cylinders, WALLS
        )
        write_config(config_path, pcd_path.name)
        maps.append(
            {
                "map": map_name,
                "severity": severity,
                "source_seed": source_seed,
                "background_radius_m": background_radius,
                "hazard_radius_m": hazard_radius,
                "base_cylinders_retained": len(retained),
                "base_cylinders_removed": len(removed),
                "point_count": point_count,
                "wall_point_count": wall_point_count,
                "pcd_sha256": sha256(pcd_path),
                "config_sha256": sha256(config_path),
            }
        )

    manifest = {
        "schema": "angular-blind-turn-calibration-v1",
        "purpose": "calibration-only; never pool with independent evaluation",
        "map_prefix": MAP_PREFIX,
        "maps": maps,
        "source_seeds": list(SOURCE_SEEDS),
        "route_waypoints_xy_m": [list(point) for point in ROUTE_WAYPOINTS],
        "waypoint_switch_distance_m": 1.5,
        "critical_turn_deg": 90.0,
        "background_route_surface_clearance_m":
            BACKGROUND_ROUTE_CLEARANCE_M,
        "hazard": {
            "center_xy_m": list(HAZARD_CENTER),
            "radii_m": list(HAZARD_RADII_M),
            "height_m": OBSTACLE_HEIGHT_M,
        },
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
        "validated_flight_z_envelope_m": [0.5, 2.8],
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
            f"{item['map']}: radius={item['hazard_radius_m']:.2f}m "
            f"points={item['point_count']} sha256={item['pcd_sha256']}"
        )
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
