#!/usr/bin/env python3
"""Generate the native seed1..10 v6 uniform-gap obstacle-size sweep.

The mission scale remains the v5 time-matched setup: a 64 x 64 m field,
410 cylinders, and loop corners at +/-24 m.  V6 removes the old density axis:
every map has a 1.0 m minimum physical surface gap, while two deterministic
seeds are assigned to each of five clearly separated cylinder radii.

The tracked ``seedN_static.csv`` files are the geometry source of truth.  This
script also updates the Gazebo sidecar/SDF and the native MARSIM PCD.  Existing
v5 assets are copied once to versioned backup directories before replacement.
"""

from __future__ import annotations

import os
from pathlib import Path
import random
import shutil
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gen_world as gw  # noqa: E402
from csv_to_pcd import convert  # noqa: E402


FIELD_SIZE_M = 64.0
COUNT = 410
CORNER_M = 24.0
SURFACE_GAP_M = 1.0
# Manifests quantize x/y to 1 mm.  A 2 mm center-distance guard keeps the
# serialized geometry at or above the nominal surface gap even in the worst
# case where both endpoints round toward each other.
SERIALIZATION_GUARD_M = 0.002
RADIUS_TIERS_M = (0.150, 0.275, 0.400, 0.525, 0.650)
SEED_RADIUS_M = {
    seed: RADIUS_TIERS_M[(seed - 1) // 2] for seed in range(1, 11)
}

WORLD_DIR = Path(gw.DEFAULT_OUTDIR)
WORLD_BACKUP_DIR = WORLD_DIR / "backup_v5_before_uniform_gap_size_sweep"
RUNTIME_PCD_DIR = Path(
    "/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
)
PCD_BACKUP_DIR = RUNTIME_PCD_DIR / "backup_v5_before_uniform_gap_size_sweep"


def physical_clear_zones(radius: float):
    """Keep the requested free radius clear to each obstacle surface."""
    zones = [(0.0, 0.0, gw.MARGIN + radius)]
    zones.extend(
        (x, y, gw.CORNER_CLEAR + radius)
        for x, y in gw.corner_waypoints(CORNER_M)
    )
    return zones


def generate_seed(seed: int, radius: float):
    minimum_center_distance = (
        2.0 * radius + SURFACE_GAP_M + SERIALIZATION_GUARD_M
    )
    points = gw.generate_positions(
        COUNT,
        FIELD_SIZE_M,
        minimum_center_distance,
        physical_clear_zones(radius),
        random.Random(seed),
    )
    if len(points) != COUNT:
        raise RuntimeError(
            f"seed{seed}: placed only {len(points)}/{COUNT}; "
            "the selected radius/gap tier is infeasible"
        )
    return points


def write_manifest(path: Path, points, radius: float):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        stream.write("x,y,r\n")
        for x, y in points:
            stream.write(f"{x:.3f},{y:.3f},{radius:.3f}\n")
    os.replace(temporary, path)


def write_text(path: Path, contents: str):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(contents)
    os.replace(temporary, path)


def backup_once(source: Path, backup_directory: Path):
    if not source.exists():
        return
    backup_directory.mkdir(parents=True, exist_ok=True)
    destination = backup_directory / source.name
    if not destination.exists():
        shutil.copy2(source, destination)


def backup_v5_assets(seed: int):
    backup_once(WORLD_DIR / f"default_seed{seed}.sdf", WORLD_BACKUP_DIR)
    backup_once(
        WORLD_DIR / f"default_seed{seed}.obstacles.csv", WORLD_BACKUP_DIR
    )
    backup_once(RUNTIME_PCD_DIR / f"seed{seed}.pcd", PCD_BACKUP_DIR)


def main():
    template_text = Path(gw.DEFAULT_TEMPLATE).read_text()
    WORLD_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_PCD_DIR.mkdir(parents=True, exist_ok=True)

    print(
        "native seed1..10 v6: "
        f"field={FIELD_SIZE_M}m count={COUNT} gap={SURFACE_GAP_M}m "
        f"radii={RADIUS_TIERS_M}"
    )
    for seed in range(1, 11):
        radius = SEED_RADIUS_M[seed]
        points = generate_seed(seed, radius)
        backup_v5_assets(seed)

        tracked_manifest = SCRIPT_DIR / f"seed{seed}_static.csv"
        write_manifest(tracked_manifest, points, radius)

        world_name = f"default_seed{seed}"
        external_manifest = WORLD_DIR / f"{world_name}.obstacles.csv"
        shutil.copy2(tracked_manifest, external_manifest)
        sdf = gw.build_world(
            template_text, world_name, points, radius, with_drone=False
        )
        write_text(WORLD_DIR / f"{world_name}.sdf", sdf)

        runtime_pcd = RUNTIME_PCD_DIR / f"seed{seed}.pcd"
        temporary_pcd = runtime_pcd.with_suffix(".pcd.tmp")
        convert(str(tracked_manifest), str(temporary_pcd), height=3.0)
        os.replace(temporary_pcd, runtime_pcd)

        print(
            f"seed{seed:2d}: radius={radius:.3f}m "
            f"diameter={2.0 * radius:.3f}m, "
            f"surface_gap={SURFACE_GAP_M:.2f}m, obstacles={len(points)}"
        )

    print(f"v5 world backup: {WORLD_BACKUP_DIR}")
    print(f"v5 PCD backup:   {PCD_BACKUP_DIR}")


if __name__ == "__main__":
    main()
