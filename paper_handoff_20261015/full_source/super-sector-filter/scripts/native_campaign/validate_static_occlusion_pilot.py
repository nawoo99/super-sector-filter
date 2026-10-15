#!/usr/bin/env python3
"""Fail closed on the frozen static-occlusion pilot geometry and assets."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "static_occlusion_pilot_manifest.json"
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
BODY_RADIUS_M = 0.20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pcd_header(path: Path) -> dict[str, str]:
    header = {}
    with path.open() as stream:
        for line in stream:
            key, _, value = line.strip().partition(" ")
            header[key] = value
            if key == "DATA":
                break
    return header


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    projection = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / length_sq
    projection = min(1.0, max(0.0, projection))
    nearest = (start[0] + projection * dx, start[1] + projection * dy)
    return math.hypot(point[0] - nearest[0], point[1] - nearest[1])


def segment_rectangle_distance(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: list[float],
) -> float:
    xmin, xmax, ymin, ymax = bounds
    # The frozen local approach has positive slope and does not intersect the
    # rectangle.  Its closest point is therefore one of the four corners.
    return min(
        point_segment_distance((x, y), start, end)
        for x in (xmin, xmax)
        for y in (ymin, ymax)
    )


def ray_hits_wall(
    origin: tuple[float, float],
    target: tuple[float, float],
    wall: list[float],
) -> bool:
    xmin, xmax, ymin, ymax = wall
    dy = target[1] - origin[1]
    if abs(dy) < 1e-12:
        return False
    for wall_y in (ymin, ymax):
        fraction = (wall_y - origin[1]) / dy
        if 0.0 < fraction < 1.0:
            x = origin[0] + fraction * (target[0] - origin[0])
            if xmin <= x <= xmax:
                return True
    return False


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "static-occlusion-pilot-v1":
        errors.append("unexpected schema")
    maps = manifest.get("maps") or []
    if len(maps) != 10:
        errors.append(f"expected 10 maps, found {len(maps)}")

    by_tier: dict[int, list[dict]] = {}
    for item in maps:
        by_tier.setdefault(int(item["radius_tier"]), []).append(item)
        pcd_path = PCD_DIR / f"{item['map']}.pcd"
        config_path = CONFIG_DIR / f"{item['map']}.yaml"
        if not pcd_path.is_file():
            errors.append(f"missing {pcd_path}")
            continue
        if not config_path.is_file():
            errors.append(f"missing {config_path}")
            continue
        if sha256(pcd_path) != item["pcd_sha256"]:
            errors.append(f"PCD hash mismatch: {item['map']}")
        if sha256(config_path) != item["config_sha256"]:
            errors.append(f"config hash mismatch: {item['map']}")
        header = pcd_header(pcd_path)
        if header.get("DATA") != "ascii":
            errors.append(f"non-ASCII PCD: {item['map']}")
        if int(header.get("POINTS", -1)) != int(item["point_count"]):
            errors.append(f"PCD point-count mismatch: {item['map']}")
        expected_reference = f'pcd_name: "seed_maps/{item["map"]}.pcd"'
        if expected_reference not in config_path.read_text():
            errors.append(f"config PCD reference mismatch: {item['map']}")

    for tier in range(1, 6):
        pair = sorted(by_tier.get(tier, []), key=lambda item: item["visibility"])
        if {item["visibility"] for item in pair} != {"nom", "occ"}:
            errors.append(f"tier {tier}: nominal/occluded pair missing")
            continue
        nominal = next(item for item in pair if item["visibility"] == "nom")
        occluded = next(item for item in pair if item["visibility"] == "occ")
        common_keys = (
            "background_radius_m",
            "source_seed",
            "base_cylinders_retained",
            "base_cylinders_removed",
        )
        if any(nominal[key] != occluded[key] for key in common_keys):
            errors.append(f"tier {tier}: pair background mismatch")
        if nominal["wall_included"] or not occluded["wall_included"]:
            errors.append(f"tier {tier}: wall treatment mismatch")
        wall_points = int(occluded["point_count"]) - int(nominal["point_count"])
        if wall_points != 10162:
            errors.append(f"tier {tier}: unexpected wall point delta {wall_points}")

    hazard = manifest["hazard"]
    wall = manifest["occluder"]["bounds_xyxy_m"]
    hazard_center = tuple(hazard["center_xy_m"])
    hazard_radius = float(hazard["radius_m"])

    approach = ((11.0, 11.0), (24.0, 24.0))
    wall_distance = segment_rectangle_distance(*approach, wall)
    if wall_distance - BODY_RADIUS_M < 0.50:
        errors.append(
            f"nominal approach wall clearance below 0.50 m: "
            f"{wall_distance - BODY_RADIUS_M:.6f}"
        )
    hazard_approach_clearance = point_segment_distance(
        hazard_center, *approach
    ) - hazard_radius - BODY_RADIUS_M
    if hazard_approach_clearance < 2.0:
        errors.append(
            "hazard intrudes on diagonal approach: "
            f"{hazard_approach_clearance:.6f}"
        )

    # Center rays must be blocked throughout the declared hidden approach and
    # unblocked at the predeclared reveal station.  This is an analytic map
    # check; sensor-delivery evidence is still required from the ROS smoke.
    for station in (12.0, 14.0, 16.0, 18.0, 20.0):
        if not ray_hits_wall((station, station), hazard_center, wall):
            errors.append(f"hazard center is visible too early at x=y={station}")
    if ray_hits_wall((21.0, 21.0), hazard_center, wall):
        errors.append("hazard center remains hidden at x=y=21 reveal station")

    # A fixed northern bypass around the outgoing-leg hazard proves that the
    # local patch is not a geometric trap.  Background cylinders touching the
    # whole patch were removed by the generator.
    bypass = ((24.0, 24.0), (22.0, 25.5), (17.0, 25.5), (11.0, 24.0))
    minimum_bypass_clearance = min(
        point_segment_distance(hazard_center, start, end)
        - hazard_radius
        - BODY_RADIUS_M
        for start, end in zip(bypass, bypass[1:])
    )
    if minimum_bypass_clearance < 0.50:
        errors.append(
            f"northern bypass clearance below 0.50 m: {minimum_bypass_clearance:.6f}"
        )

    result = {
        "status": "PASS" if not errors else "FAIL",
        "map_count": len(maps),
        "pair_count": len(by_tier),
        "approach_wall_body_clearance_m": round(wall_distance - BODY_RADIUS_M, 6),
        "approach_hazard_body_clearance_m": round(hazard_approach_clearance, 6),
        "northern_bypass_body_clearance_m": round(minimum_bypass_clearance, 6),
        "hidden_center_ray_stations_m": [12, 14, 16, 18, 20],
        "reveal_center_ray_station_m": 21,
        "errors": errors,
    }
    return result


def main() -> None:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
