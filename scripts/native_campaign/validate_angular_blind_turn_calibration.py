#!/usr/bin/env python3
"""Fail-closed structural validator for ``abt_cal_s1..s5``."""

from __future__ import annotations

import json
import math
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from validate_static_blind_corner_supplement import (
    point_segment_distance,
    segment_hits_wall,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "angular_blind_turn_calibration_manifest.json"


def pcd_header(path: Path) -> dict[str, str]:
    header = {}
    with path.open() as stream:
        for line in stream:
            key, _, value = line.strip().partition(" ")
            header[key] = value
            if key == "DATA":
                break
    return header


def circle_samples(center: tuple[float, float], radius: float):
    for index in range(1440):
        angle = 2.0 * math.pi * index / 1440
        yield (
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle),
        )


def angle_delta_deg(value: float) -> float:
    return math.degrees(math.atan2(math.sin(value), math.cos(value)))


def first_visible_on_northbound(
    walls: list[dict], center: tuple[float, float], radius: float
) -> tuple[float, float] | None:
    for index in range(401):
        y = 18.0 + 0.01 * index
        origin = (24.0, y)
        relative_angles = []
        for target in circle_samples(center, radius):
            if not any(segment_hits_wall(origin, target, wall) for wall in walls):
                bearing = math.atan2(target[1] - y, target[0] - 24.0)
                relative_angles.append(abs(angle_delta_deg(bearing - math.pi / 2)))
        if relative_angles:
            return y, min(relative_angles)
    return None


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "angular-blind-turn-calibration-v1":
        errors.append("unexpected schema")
    maps = manifest.get("maps") or []
    if len(maps) != 5:
        errors.append(f"expected 5 maps, found {len(maps)}")
    route = [tuple(point) for point in manifest["route_waypoints_xy_m"]]
    expected_route = [
        (0.0, 0.0), (24.0, 0.0), (24.0, 24.0), (-24.0, 24.0),
        (-24.0, -24.0), (24.0, -24.0), (0.0, 0.0),
    ]
    if route != expected_route:
        errors.append("unexpected route")
    incoming = (route[2][0] - route[1][0], route[2][1] - route[1][1])
    outgoing = (route[3][0] - route[2][0], route[3][1] - route[2][1])
    turn = math.degrees(math.acos(
        sum(a * b for a, b in zip(incoming, outgoing)) /
        (math.hypot(*incoming) * math.hypot(*outgoing))
    ))
    if not math.isclose(turn, 90.0, abs_tol=1e-9):
        errors.append(f"critical turn is {turn}, not 90 degrees")

    center = tuple(manifest["hazard"]["center_xy_m"])
    walls = manifest["walls"]
    body_radius = float(manifest["body_radius_m"])
    reveals = []
    min_relative_angles = []
    bypass_clearances = []
    for severity, item in enumerate(maps, start=1):
        if item["map"] != f"abt_cal_s{severity}":
            errors.append(f"unexpected map order/name: {item['map']}")
        pcd_path = PCD_DIR / f"{item['map']}.pcd"
        config_path = CONFIG_DIR / f"{item['map']}.yaml"
        if not pcd_path.is_file() or not config_path.is_file():
            errors.append(f"missing runtime asset: {item['map']}")
            continue
        if sha256(pcd_path) != item["pcd_sha256"]:
            errors.append(f"PCD hash mismatch: {item['map']}")
        if sha256(config_path) != item["config_sha256"]:
            errors.append(f"config hash mismatch: {item['map']}")
        header = pcd_header(pcd_path)
        if header.get("DATA") != "ascii":
            errors.append(f"non-ASCII PCD: {item['map']}")
        if int(header.get("POINTS", -1)) != int(item["point_count"]):
            errors.append(f"point-count mismatch: {item['map']}")
        if f'pcd_name: "seed_maps/{item["map"]}.pcd"' not in config_path.read_text():
            errors.append(f"config reference mismatch: {item['map']}")

        radius = float(item["hazard_radius_m"])
        reveal = first_visible_on_northbound(walls, center, radius)
        if reveal is None:
            errors.append(f"hazard never revealed: {item['map']}")
            continue
        reveal_y, minimum_relative = reveal
        reveals.append(reveal_y)
        min_relative_angles.append(minimum_relative)
        if not 21.0 <= reveal_y <= 21.8:
            errors.append(f"reveal y outside [21.0,21.8]: {item['map']}={reveal_y}")
        if minimum_relative <= 47.0:
            errors.append(
                f"visible hazard enters 45-degree crop margin: "
                f"{item['map']}={minimum_relative}"
            )

        # The direct post-turn route must intersect every hazard.
        if point_segment_distance(center, (24.0, 24.0), (-24.0, 24.0)) > radius:
            errors.append(f"direct outgoing route misses hazard: {item['map']}")
        # A common northern bypass remains feasible for Full/Adaptive.
        bypass = [(24.0, 22.5), (24.0, 26.2), (13.2, 26.2), (13.2, 24.0)]
        minimum = math.inf
        for start, end in zip(bypass, bypass[1:]):
            for index in range(101):
                t = index / 100.0
                point = (
                    start[0] + t * (end[0] - start[0]),
                    start[1] + t * (end[1] - start[1]),
                )
                hazard_clearance = math.dist(point, center) - radius - body_radius
                minimum = min(minimum, hazard_clearance)
                for wall in walls:
                    # Conservative dense surface approximation is sufficient
                    # for this axis-aligned two-wall calibration geometry.
                    x0, y0 = wall["start_xy_m"]
                    x1, y1 = wall["end_xy_m"]
                    wall_distance = point_segment_distance(point, (x0, y0), (x1, y1))
                    minimum = min(
                        minimum,
                        wall_distance - float(wall["thickness_m"]) / 2.0 - body_radius,
                    )
        bypass_clearances.append(minimum)
        if minimum < 0.45 - 1e-6:
            errors.append(f"northern bypass too tight: {item['map']}={minimum}")

    z_min, z_max = manifest["validated_flight_z_envelope_m"]
    if z_min < 0.0 or z_max + body_radius > manifest["hazard"]["height_m"]:
        errors.append("hazard does not cover validated 3D body envelope")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "map_count": len(maps),
        "critical_turn_deg": turn,
        "first_visible_northbound_y_m": [round(value, 3) for value in reveals],
        "first_visible_min_relative_deg": [
            round(value, 3) for value in min_relative_angles
        ],
        "northern_bypass_body_clearance_min_m": round(
            min(bypass_clearances, default=math.nan), 6
        ),
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
