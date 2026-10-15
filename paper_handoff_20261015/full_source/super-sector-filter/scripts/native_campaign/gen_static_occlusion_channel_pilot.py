#!/usr/bin/env python3
"""Generate the separately versioned channelized static-occlusion pilot.

The first finite-wall pilot showed that physical occlusion was delivered but
did not constrain every policy to the same reveal geometry.  This v2 pilot
uses the independent even-seed backgrounds and inserts a common L-shaped
channel around the first loop corner.  The paired nominal map has a narrow
horizontal sensor slit through the two inner walls; the occluded map fills
that slit.  The slit is shorter than the declared vehicle diameter, so it
changes line of sight without adding a body-traversable route.

PCDs and PerfectDrone configs are runtime assets in the SUPER source tree.
This script plus the compact tracked manifest are their reproducible source.
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
MANIFEST_PATH = SCRIPT_DIR / "static_occlusion_channel_pilot_manifest.json"

SOURCE_SEEDS = (2, 4, 6, 8, 10)
RADIUS_TIERS_M = (0.150, 0.275, 0.400, 0.525, 0.650)
MAP_PREFIX = "occ_c"

CLEAR_PATCH = (5.0, 27.5, 5.0, 27.5)  # xmin, xmax, ymin, ymax
HAZARD_CENTER = (18.0, 24.0)
HAZARD_RADIUS_M = 0.75
OBSTACLE_HEIGHT_M = 3.2

BODY_RADIUS_M = 0.20
CHANNEL_HALF_WIDTH_M = 1.80
WALL_THICKNESS_M = 0.30
WALL_CENTER_OFFSET_M = CHANNEL_HALF_WIDTH_M + WALL_THICKNESS_M / 2.0
WALL_DS_M = 0.05
Z_STEP_M = 0.10
CYLINDER_DS_M = 0.05

# Removing z=1.4 and 1.5 rows leaves a 0.30 m sampled opening bounded by the
# retained 1.3 and 1.6 m rows.  The declared 0.40 m body diameter cannot pass
# it with positive clearance.
SENSOR_SLIT_Z_MIN_M = 1.35
SENSOR_SLIT_Z_MAX_M = 1.55


class Cylinder(NamedTuple):
    x: float
    y: float
    radius: float


class Wall(NamedTuple):
    name: str
    start: tuple[float, float]
    end: tuple[float, float]
    sensor_slit: bool


SQRT2 = math.sqrt(2.0)
NORMAL_OFFSET = WALL_CENTER_OFFSET_M / SQRT2
INNER_DIAG_END_S = 22.05 - NORMAL_OFFSET
OUTER_DIAG_END_S = 25.95 - NORMAL_OFFSET

WALLS = (
    Wall(
        "inner_diagonal",
        (7.5 - NORMAL_OFFSET, 7.5 + NORMAL_OFFSET),
        (INNER_DIAG_END_S - NORMAL_OFFSET,
         INNER_DIAG_END_S + NORMAL_OFFSET),
        True,
    ),
    Wall(
        "outer_diagonal",
        (7.5 + NORMAL_OFFSET, 7.5 - NORMAL_OFFSET),
        (OUTER_DIAG_END_S + NORMAL_OFFSET,
         OUTER_DIAG_END_S - NORMAL_OFFSET),
        False,
    ),
    Wall("inner_south", (6.0, 22.05), (19.45, 22.05), True),
    Wall("outer_north", (6.0, 25.95), (25.95, 25.95), False),
    Wall("outer_east", (25.95, 22.05), (25.95, 25.95), False),
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


def wall_points(
    wall: Wall, *, open_sensor_slit: bool
) -> Iterator[tuple[float, float, float]]:
    dx = wall.end[0] - wall.start[0]
    dy = wall.end[1] - wall.start[1]
    length = math.hypot(dx, dy)
    tx, ty = dx / length, dy / length
    nx, ny = -ty, tx
    half = WALL_THICKNESS_M / 2.0
    ss = inclusive_axis(0.0, length, WALL_DS_M)
    ns = inclusive_axis(-half, half, WALL_DS_M)
    zs = inclusive_axis(0.0, OBSTACLE_HEIGHT_M, Z_STEP_M)

    def emit(s: float, n: float, z: float):
        if (
            open_sensor_slit
            and wall.sensor_slit
            and SENSOR_SLIT_Z_MIN_M <= z <= SENSOR_SLIT_Z_MAX_M
        ):
            return
        yield (
            wall.start[0] + tx * s + nx * n,
            wall.start[1] + ty * s + ny * n,
            z,
        )

    for n in (-half, half):
        for s in ss:
            for z in zs:
                yield from emit(s, n, z)
    for s in (0.0, length):
        for n in ns:
            for z in zs:
                yield from emit(s, n, z)
    for z in (0.0, OBSTACLE_HEIGHT_M):
        for s in ss:
            for n in ns:
                yield from emit(s, n, z)


def write_pcd(
    path: Path,
    cylinders: Iterable[Cylinder],
    *,
    open_sensor_slit: bool,
) -> tuple[int, int]:
    cylinders = list(cylinders)
    per_wall = [
        sum(1 for _ in wall_points(wall, open_sensor_slit=open_sensor_slit))
        for wall in WALLS
    ]
    wall_count = sum(per_wall)
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
        for wall in WALLS:
            for x, y, z in wall_points(
                wall, open_sensor_slit=open_sensor_slit
            ):
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

    for tier, (source_seed, radius) in enumerate(
        zip(SOURCE_SEEDS, RADIUS_TIERS_M), start=1
    ):
        source_path = SCRIPT_DIR / f"seed{source_seed}_static.csv"
        source = load_cylinders(source_path)
        if len(source) != 410:
            raise ValueError(f"{source_path}: expected 410 cylinders")
        if any(
            not math.isclose(item.radius, radius, abs_tol=1e-9)
            for item in source
        ):
            raise ValueError(f"{source_path}: radius tier mismatch")
        retained = [item for item in source if not touches_patch(item)]
        removed = [item for item in source if touches_patch(item)]
        cylinders = retained + [
            Cylinder(HAZARD_CENTER[0], HAZARD_CENTER[1], HAZARD_RADIUS_M)
        ]

        for visibility, open_slit in (("nom", True), ("occ", False)):
            map_name = f"{MAP_PREFIX}_r{tier}_{visibility}"
            pcd_path = PCD_DIR / f"{map_name}.pcd"
            config_path = CONFIG_DIR / f"{map_name}.yaml"
            point_count, wall_count = write_pcd(
                pcd_path, cylinders, open_sensor_slit=open_slit
            )
            write_config(config_path, pcd_path.name)
            maps.append(
                {
                    "map": map_name,
                    "radius_tier": tier,
                    "background_radius_m": radius,
                    "source_seed": source_seed,
                    "visibility": visibility,
                    "sensor_slit_open": open_slit,
                    "base_cylinders_retained": len(retained),
                    "base_cylinders_removed": len(removed),
                    "wall_point_count": wall_count,
                    "point_count": point_count,
                    "pcd_sha256": sha256(pcd_path),
                    "config_sha256": sha256(config_path),
                }
            )

    manifest = {
        "schema": "static-occlusion-channel-pilot-v2",
        "role": (
            "exploratory channelization gate; v1 odd-seed pilot is design "
            "data and any later confirmatory cohort must be independent"
        ),
        "source_seeds": list(SOURCE_SEEDS),
        "radius_tiers_m": list(RADIUS_TIERS_M),
        "clear_patch_xyxy_m": list(CLEAR_PATCH),
        "body_radius_m": BODY_RADIUS_M,
        "channel_half_width_m": CHANNEL_HALF_WIDTH_M,
        "hazard": {
            "shape": "vertical_cylinder",
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "walls": [
            {
                "name": wall.name,
                "start_xy_m": list(wall.start),
                "end_xy_m": list(wall.end),
                "thickness_m": WALL_THICKNESS_M,
                "height_m": OBSTACLE_HEIGHT_M,
                "sensor_slit": wall.sensor_slit,
            }
            for wall in WALLS
        ],
        "nominal_sensor_slit": {
            "z_min_m": SENSOR_SLIT_Z_MIN_M,
            "z_max_m": SENSOR_SLIT_Z_MAX_M,
            "height_m": SENSOR_SLIT_Z_MAX_M - SENSOR_SLIT_Z_MIN_M,
            "body_traversable": False,
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
            f"removed={item['base_cylinders_removed']} "
            f"points={item['point_count']} sha256={item['pcd_sha256']}"
        )
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
