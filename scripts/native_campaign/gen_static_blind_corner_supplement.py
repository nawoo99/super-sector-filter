#!/usr/bin/env python3
"""Generate five supplemental solid-wall static blind-corner maps.

The existing reliability and static-occlusion studies remain unchanged.  This
separate family keeps the deployed planners fixed and adds a harder static
stress set: a full-height L-shaped channel forces the first loop turn, while a
full-height hazard is revealed from the side only after the vehicle enters the
turn chamber.  There is no optical slit and no moving obstacle.

Large runtime PCDs and PerfectDrone configs are written into the SUPER source
tree.  This generator and its compact manifest are the tracked reproducible
source.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "static_blind_corner_supplement_manifest.json"

# One retained representative background from each original radius stratum.
SOURCE_SEEDS = (1, 3, 5, 7, 9)
RADIUS_TIERS_M = (0.150, 0.275, 0.400, 0.525, 0.650)
MAP_PREFIX = "occ_bc"

CLEAR_PATCH = (5.0, 27.5, 5.0, 27.5)
# Remove background cylinders from a common corridor around the mission
# polyline.  The added solid-wall corner remains in that corridor: this only
# removes inherited seed-map bottlenecks on the other four legs, so the
# supplemental experiment isolates the intended side-reveal intervention.
ROUTE_WAYPOINTS = (
    (0.0, 0.0),
    (24.0, 24.0),
    (-24.0, 24.0),
    (-24.0, -24.0),
    (24.0, -24.0),
    (0.0, 0.0),
)
BACKGROUND_ROUTE_CLEARANCE_M = 2.0
HAZARD_CENTER = (18.8, 24.0)
HAZARD_RADIUS_M = 0.95
OBSTACLE_HEIGHT_M = 3.2

BODY_RADIUS_M = 0.20
CHANNEL_HALF_WIDTH_M = 1.80
WALL_THICKNESS_M = 0.30
WALL_CENTER_OFFSET_M = CHANNEL_HALF_WIDTH_M + WALL_THICKNESS_M / 2.0
INNER_SOUTH_END_X_M = 19.45
WALL_DS_M = 0.05
Z_STEP_M = 0.10
CYLINDER_DS_M = 0.05


class Cylinder(NamedTuple):
    x: float
    y: float
    radius: float


class Wall(NamedTuple):
    name: str
    start: tuple[float, float]
    end: tuple[float, float]


SQRT2 = math.sqrt(2.0)
NORMAL_OFFSET = WALL_CENTER_OFFSET_M / SQRT2
INNER_DIAG_END_S = 22.05 - NORMAL_OFFSET
OUTER_DIAG_END_S = 25.95 - NORMAL_OFFSET


def walls_for_tier(tier: int) -> tuple[Wall, ...]:
    if tier not in range(1, 6):
        raise ValueError(f"unexpected radius tier {tier}")
    return (
        Wall(
            "inner_diagonal",
            (7.5 - NORMAL_OFFSET, 7.5 + NORMAL_OFFSET),
            (
                INNER_DIAG_END_S - NORMAL_OFFSET,
                INNER_DIAG_END_S + NORMAL_OFFSET,
            ),
        ),
        Wall(
            "outer_diagonal",
            (7.5 + NORMAL_OFFSET, 7.5 - NORMAL_OFFSET),
            (
                OUTER_DIAG_END_S + NORMAL_OFFSET,
                OUTER_DIAG_END_S - NORMAL_OFFSET,
            ),
        ),
        Wall("inner_south", (6.0, 22.05), (INNER_SOUTH_END_X_M, 22.05)),
        Wall("outer_north", (6.0, 25.95), (25.95, 25.95)),
        Wall("outer_east", (25.95, 22.05), (25.95, 25.95)),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cylinders(path: Path) -> list[Cylinder]:
    with path.open(newline="") as stream:
        return [
            Cylinder(float(row["x"]), float(row["y"]), float(row["r"]))
            for row in csv.DictReader(stream)
        ]


def touches_patch(cylinder: Cylinder) -> bool:
    xmin, xmax, ymin, ymax = CLEAR_PATCH
    nearest_x = min(max(cylinder.x, xmin), xmax)
    nearest_y = min(max(cylinder.y, ymin), ymax)
    return math.hypot(cylinder.x - nearest_x, cylinder.y - nearest_y) <= (
        cylinder.radius + 1e-12
    )


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    scale = dx * dx + dy * dy
    if scale <= 0.0:
        return math.dist(point, start)
    fraction = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / scale
    fraction = min(1.0, max(0.0, fraction))
    closest = (start[0] + fraction * dx, start[1] + fraction * dy)
    return math.dist(point, closest)


def touches_route_corridor(cylinder: Cylinder) -> bool:
    centre_distance = min(
        point_segment_distance(
            (cylinder.x, cylinder.y), start, end
        )
        for start, end in zip(ROUTE_WAYPOINTS, ROUTE_WAYPOINTS[1:])
    )
    return centre_distance <= (
        cylinder.radius + BACKGROUND_ROUTE_CLEARANCE_M + 1e-12
    )


def inclusive_axis(low: float, high: float, spacing: float) -> list[float]:
    intervals = max(1, int(math.ceil((high - low) / spacing)))
    return [
        low + (high - low) * index / intervals
        for index in range(intervals + 1)
    ]


def cylinder_point_count(radius: float) -> int:
    n_theta = max(8, int(round(2.0 * math.pi * radius / CYLINDER_DS_M)))
    n_z = max(2, int(round(OBSTACLE_HEIGHT_M / Z_STEP_M)))
    return n_theta * (n_z + 1)


def cylinder_points(cylinder: Cylinder) -> Iterator[tuple[float, float, float]]:
    n_theta = max(
        8, int(round(2.0 * math.pi * cylinder.radius / CYLINDER_DS_M))
    )
    n_z = max(2, int(round(OBSTACLE_HEIGHT_M / Z_STEP_M)))
    for iz in range(n_z + 1):
        z = iz * OBSTACLE_HEIGHT_M / n_z
        for it in range(n_theta):
            angle = 2.0 * math.pi * it / n_theta
            yield (
                cylinder.x + cylinder.radius * math.cos(angle),
                cylinder.y + cylinder.radius * math.sin(angle),
                z,
            )


def wall_points(wall: Wall) -> Iterator[tuple[float, float, float]]:
    dx = wall.end[0] - wall.start[0]
    dy = wall.end[1] - wall.start[1]
    length = math.hypot(dx, dy)
    tx, ty = dx / length, dy / length
    nx, ny = -ty, tx
    half = WALL_THICKNESS_M / 2.0
    ss = inclusive_axis(0.0, length, WALL_DS_M)
    ns = inclusive_axis(-half, half, WALL_DS_M)
    zs = inclusive_axis(0.0, OBSTACLE_HEIGHT_M, Z_STEP_M)

    for n in (-half, half):
        for s in ss:
            for z in zs:
                yield (
                    wall.start[0] + tx * s + nx * n,
                    wall.start[1] + ty * s + ny * n,
                    z,
                )
    for s in (0.0, length):
        for n in ns:
            for z in zs:
                yield (
                    wall.start[0] + tx * s + nx * n,
                    wall.start[1] + ty * s + ny * n,
                    z,
                )
    for z in (0.0, OBSTACLE_HEIGHT_M):
        for s in ss:
            for n in ns:
                yield (
                    wall.start[0] + tx * s + nx * n,
                    wall.start[1] + ty * s + ny * n,
                    z,
                )


def write_pcd(
    path: Path,
    cylinders: Iterable[Cylinder],
    walls: Iterable[Wall],
) -> tuple[int, int]:
    cylinders = list(cylinders)
    walls = list(walls)
    wall_count = sum(sum(1 for _ in wall_points(wall)) for wall in walls)
    point_count = sum(cylinder_point_count(item.radius) for item in cylinders)
    point_count += wall_count

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        stream.write("# .PCD v0.7 - Point Cloud Data file format\n")
        stream.write("VERSION 0.7\n")
        stream.write("FIELDS x y z\n")
        stream.write("SIZE 4 4 4\n")
        stream.write("TYPE F F F\n")
        stream.write("COUNT 1 1 1\n")
        stream.write(f"WIDTH {point_count}\n")
        stream.write("HEIGHT 1\n")
        stream.write("VIEWPOINT 0 0 0 1 0 0 0\n")
        stream.write(f"POINTS {point_count}\n")
        stream.write("DATA ascii\n")
        for cylinder in cylinders:
            for x, y, z in cylinder_points(cylinder):
                stream.write(f"{x:.4f} {y:.4f} {z:.4f}\n")
        for wall in walls:
            for x, y, z in wall_points(wall):
                stream.write(f"{x:.4f} {y:.4f} {z:.4f}\n")
    os.replace(temporary, path)
    return point_count, wall_count


def write_config(path: Path, pcd_name: str) -> None:
    contents = f'''#############| For UAV simulation |#################################
pcd_name: "seed_maps/{pcd_name}"
mesh_resource: "package://perfect_drone_sim/meshes/yunque-M.dae"
init_position:
  x: 0
  y: 0
  z: 1.5
init_yaw: 0.0

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

    for tier, (source_seed, background_radius) in enumerate(
        zip(SOURCE_SEEDS, RADIUS_TIERS_M), start=1
    ):
        source_path = SCRIPT_DIR / f"seed{source_seed}_static.csv"
        source = load_cylinders(source_path)
        if len(source) != 410:
            raise ValueError(f"{source_path}: expected 410 cylinders")
        if any(
            not math.isclose(item.radius, background_radius, abs_tol=1e-9)
            for item in source
        ):
            raise ValueError(f"{source_path}: radius tier mismatch")
        removed_patch = [item for item in source if touches_patch(item)]
        removed_route = [item for item in source if touches_route_corridor(item)]
        retained = [
            item for item in source
            if not touches_patch(item) and not touches_route_corridor(item)
        ]
        removed = [item for item in source if item not in retained]
        cylinders = retained + [
            Cylinder(HAZARD_CENTER[0], HAZARD_CENTER[1], HAZARD_RADIUS_M)
        ]
        walls = walls_for_tier(tier)
        map_name = f"{MAP_PREFIX}_r{tier}"
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        point_count, wall_count = write_pcd(pcd_path, cylinders, walls)
        write_config(config_path, pcd_path.name)
        maps.append(
            {
                "map": map_name,
                "radius_tier": tier,
                "background_radius_m": background_radius,
                "source_seed": source_seed,
                "inner_south_end_x_m": INNER_SOUTH_END_X_M,
                "base_cylinders_retained": len(retained),
                "base_cylinders_removed": len(removed),
                "base_cylinders_touching_local_patch": len(removed_patch),
                "base_cylinders_touching_route_corridor": len(removed_route),
                "wall_point_count": wall_count,
                "point_count": point_count,
                "pcd_sha256": sha256(pcd_path),
                "config_sha256": sha256(config_path),
                "walls": [
                    {
                        "name": wall.name,
                        "start_xy_m": list(wall.start),
                        "end_xy_m": list(wall.end),
                        "thickness_m": WALL_THICKNESS_M,
                        "height_m": OBSTACLE_HEIGHT_M,
                    }
                    for wall in walls
                ],
            }
        )

    manifest = {
        "schema": "static-blind-corner-supplement-v3.1-controlled-route",
        "role": (
            "supplemental static blind-corner stress; existing reliability "
            "and v1/v2 occlusion results remain unchanged"
        ),
        "source_seeds": list(SOURCE_SEEDS),
        "radius_tiers_m": list(RADIUS_TIERS_M),
        "clear_patch_xyxy_m": list(CLEAR_PATCH),
        "background_route_waypoints_xy_m": [
            list(point) for point in ROUTE_WAYPOINTS
        ],
        "background_route_surface_clearance_m": (
            BACKGROUND_ROUTE_CLEARANCE_M
        ),
        "body_radius_m": BODY_RADIUS_M,
        "channel_half_width_m": CHANNEL_HALF_WIDTH_M,
        "validated_flight_z_envelope_m": [0.5, 2.8],
        "hazard": {
            "shape": "vertical_cylinder",
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "sampling": {
            "cylinder_surface_spacing_m": CYLINDER_DS_M,
            "wall_surface_spacing_m": WALL_DS_M,
            "vertical_spacing_m": Z_STEP_M,
        },
        "maps": maps,
    }
    temporary = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, MANIFEST_PATH)
    return manifest


def main() -> None:
    manifest = generate()
    for item in manifest["maps"]:
        print(
            f"{item['map']}: radius={item['background_radius_m']:.3f} "
            f"south_end={item['inner_south_end_x_m']:.2f} "
            f"removed={item['base_cylinders_removed']} "
            f"points={item['point_count']} sha256={item['pcd_sha256']}"
        )
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
