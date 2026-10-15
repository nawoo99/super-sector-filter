#!/usr/bin/env python3
"""Generate the quiet mirrored base maps for recovery seeds 14 and 15.

The UAV uses a controlled `(20, 0, 1.5)` hold before mirrored final goals at
`(40, +/-1, 1.5)`. The recovery pocket is injected by
native_recovery_scenario.py at the x=18 crossing, independent of filter mode.
Keeping it out of the PCD prevents pre-mapping before the controlled hold.
MARSIM's non-empty PCD requirement is met by one harmless cylinder behind the
start and outside the initial LiDAR horizon.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from csv_to_pcd import convert


RADIUS = 0.25
LIDAR_HORIZON = 15.0

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = REPO_ROOT / "scripts" / "native_campaign"
PCD_DIR = (
    REPO_ROOT
    / "super_patches"
    / "native_seedmap_campaign"
    / "perfect_drone_sim_pcd"
)


def seed14_centres() -> list[tuple[float, float]]:
    return [(-20.0, 0.0)]


def reflected(centres: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return sorted((x, -y) for x, y in centres)


def validate(seed14: list[tuple[float, float]], seed15: list[tuple[float, float]]) -> None:
    assert len(seed14) == len(seed15)
    assert {(x, -y) for x, y in seed14} == set(seed15)

    nearest_surface = min(math.hypot(x, y) - RADIUS for x, y in seed14)
    assert nearest_surface > LIDAR_HORIZON
    assert seed14 == [(-20.0, 0.0)]
    assert seed15 == [(-20.0, -0.0)]


def write_csv(path: Path, centres: list[tuple[float, float]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("x", "y", "r"))
        for x, y in centres:
            writer.writerow((f"{x:.3f}", f"{y:.3f}", f"{RADIUS:.3f}"))


def main() -> None:
    seed14 = seed14_centres()
    seed15 = reflected(seed14)
    validate(seed14, seed15)
    PCD_DIR.mkdir(parents=True, exist_ok=True)

    for seed, centres in ((14, seed14), (15, seed15)):
        csv_path = CSV_DIR / f"seed{seed}_static.csv"
        pcd_path = PCD_DIR / f"seed{seed}.pcd"
        write_csv(csv_path, centres)
        convert(str(csv_path), str(pcd_path), height=3.0)

    nearest = min(math.hypot(x, y) - RADIUS for x, y in seed14)
    print(
        f"generated mirrored quiet bases: {len(seed14)} cylinders each, "
        f"nearest initial surface={nearest:.3f} m"
    )


if __name__ == "__main__":
    main()
