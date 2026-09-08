#!/usr/bin/env python3
"""Generate the preregistered static-occlusion pilot maps.

The pilot is deliberately separate from seed1..10.  It uses one existing
layout from each of the five background-cylinder radius tiers, clears the
same first-corner intervention zone, and adds one common cylindrical hazard.
The paired ``nom`` map exposes that hazard directly; the ``occ`` map adds a
finite wall that hides it on the diagonal approach and reveals it shortly
before the 90-degree turn at (24, 24).

PCDs and PerfectDrone configs are runtime assets in the SUPER source tree.
The compact JSON manifest is the tracked source of truth together with this
script and the already tracked seed*_static.csv files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "static_occlusion_pilot_manifest.json"

SOURCE_SEEDS = (1, 3, 5, 7, 9)
RADIUS_TIERS_M = (0.150, 0.275, 0.400, 0.525, 0.650)
MAP_PREFIX = "occ_p"

# The cleared patch makes the intervention comparable across the five
# background maps and leaves a deterministic northern bypass.  A base
# cylinder is removed whenever its footprint touches this rectangle.
CLEAR_PATCH = (11.0, 26.0, 11.0, 27.0)  # xmin, xmax, ymin, ymax

HAZARD_CENTER = (19.50, 24.00)
HAZARD_RADIUS_M = 0.65
OBSTACLE_HEIGHT_M = 3.0

# The wall stays 0.74 m from the nominal x=y approach at its closest corner.
# With a 0.20 m body sphere this is not itself a forced-contact construction.
WALL_BOUNDS = (14.00, 20.30, 21.35, 21.65)  # xmin, xmax, ymin, ymax

CYLINDER_DS_M = 0.05
Z_STEP_M = 0.10
WALL_DS_M = 0.05


class Cylinder(NamedTuple):
    x: float
    y: float
    radius: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cylinders(path: Path) -> list[Cylinder]:
    with path.open(newline="") as stream:
        rows = csv.DictReader(stream)
        return [
            Cylinder(float(row["x"]), float(row["y"]), float(row["r"]))
            for row in rows
        ]


def touches_patch(cylinder: Cylinder) -> bool:
    xmin, xmax, ymin, ymax = CLEAR_PATCH
    nearest_x = min(max(cylinder.x, xmin), xmax)
    nearest_y = min(max(cylinder.y, ymin), ymax)
    return math.hypot(cylinder.x - nearest_x, cylinder.y - nearest_y) <= (
        cylinder.radius + 1e-12
    )


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


def inclusive_axis(low: float, high: float, spacing: float) -> list[float]:
    intervals = max(1, int(math.ceil((high - low) / spacing)))
    return [low + (high - low) * index / intervals for index in range(intervals + 1)]


def wall_points() -> Iterator[tuple[float, float, float]]:
    xmin, xmax, ymin, ymax = WALL_BOUNDS
    xs = inclusive_axis(xmin, xmax, WALL_DS_M)
    ys = inclusive_axis(ymin, ymax, WALL_DS_M)
    zs = inclusive_axis(0.0, OBSTACLE_HEIGHT_M, Z_STEP_M)

    # Edge duplicates are retained intentionally: the deterministic point
    # count can be known before streaming the ASCII PCD body.
    for y in (ymin, ymax):
        for x in xs:
            for z in zs:
                yield (x, y, z)
    for x in (xmin, xmax):
        for y in ys:
            for z in zs:
                yield (x, y, z)
    for z in (0.0, OBSTACLE_HEIGHT_M):
        for x in xs:
            for y in ys:
                yield (x, y, z)


def write_pcd(
    path: Path,
    cylinders: Iterable[Cylinder],
    include_wall: bool,
) -> int:
    cylinders = list(cylinders)
    wall_count = sum(1 for _ in wall_points()) if include_wall else 0
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
        if include_wall:
            for x, y, z in wall_points():
                stream.write(f"{x:.4f} {y:.4f} {z:.4f}\n")
    os.replace(temporary, path)
    return point_count


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
        if any(not math.isclose(item.radius, radius, abs_tol=1e-9) for item in source):
            raise ValueError(f"{source_path}: radius tier does not match {radius}")
        retained = [item for item in source if not touches_patch(item)]
        removed = [item for item in source if touches_patch(item)]
        cylinders = retained + [
            Cylinder(HAZARD_CENTER[0], HAZARD_CENTER[1], HAZARD_RADIUS_M)
        ]

        for visibility, include_wall in (("nom", False), ("occ", True)):
            map_name = f"{MAP_PREFIX}_r{tier}_{visibility}"
            pcd_path = PCD_DIR / f"{map_name}.pcd"
            config_path = CONFIG_DIR / f"{map_name}.yaml"
            point_count = write_pcd(pcd_path, cylinders, include_wall)
            write_config(config_path, pcd_path.name)
            maps.append(
                {
                    "map": map_name,
                    "radius_tier": tier,
                    "background_radius_m": radius,
                    "source_seed": source_seed,
                    "visibility": visibility,
                    "wall_included": include_wall,
                    "base_cylinders_retained": len(retained),
                    "base_cylinders_removed": len(removed),
                    "point_count": point_count,
                    "pcd_sha256": sha256(pcd_path),
                    "config_sha256": sha256(config_path),
                }
            )

    manifest = {
        "schema": "static-occlusion-pilot-v1",
        "purpose": (
            "exploratory mechanism gate only; excluded from a later "
            "independent confirmatory cohort"
        ),
        "source_seeds": list(SOURCE_SEEDS),
        "radius_tiers_m": list(RADIUS_TIERS_M),
        "clear_patch_xyxy_m": list(CLEAR_PATCH),
        "hazard": {
            "shape": "vertical_cylinder",
            "center_xy_m": list(HAZARD_CENTER),
            "radius_m": HAZARD_RADIUS_M,
            "height_m": OBSTACLE_HEIGHT_M,
        },
        "occluder": {
            "shape": "closed_rectangular_prism",
            "bounds_xyxy_m": list(WALL_BOUNDS),
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate deterministically and report the resulting manifest",
    )
    parser.parse_args()
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
