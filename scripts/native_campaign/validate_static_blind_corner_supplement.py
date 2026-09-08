#!/usr/bin/env python3
"""Fail closed on the five supplemental solid blind-corner assets."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "static_blind_corner_supplement_manifest.json"
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"


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


def wall_coordinates(
    point: tuple[float, float], wall: dict
) -> tuple[float, float, float]:
    start = wall["start_xy_m"]
    end = wall["end_xy_m"]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    tx, ty = dx / length, dy / length
    nx, ny = -ty, tx
    px, py = point[0] - start[0], point[1] - start[1]
    return px * tx + py * ty, px * nx + py * ny, length


def segment_hits_wall(
    origin: tuple[float, float], target: tuple[float, float], wall: dict
) -> bool:
    s0, n0, length = wall_coordinates(origin, wall)
    s1, n1, _ = wall_coordinates(target, wall)
    half = float(wall["thickness_m"]) / 2.0
    t_low, t_high = 0.0, 1.0
    for value0, delta, low, high in (
        (s0, s1 - s0, 0.0, length),
        (n0, n1 - n0, -half, half),
    ):
        if abs(delta) < 1e-12:
            if value0 < low or value0 > high:
                return False
            continue
        enter = (low - value0) / delta
        leave = (high - value0) / delta
        if enter > leave:
            enter, leave = leave, enter
        t_low = max(t_low, enter)
        t_high = min(t_high, leave)
        if t_low > t_high:
            return False
    return t_high > 1e-9 and t_low < 1.0 - 1e-9


def blocked(
    origin: tuple[float, float], target: tuple[float, float], walls: list[dict]
) -> bool:
    return any(segment_hits_wall(origin, target, wall) for wall in walls)


def point_wall_surface_distance(point: tuple[float, float], wall: dict) -> float:
    s, n, length = wall_coordinates(point, wall)
    half = float(wall["thickness_m"]) / 2.0
    ds = max(0.0, -s, s - length)
    dn = max(0.0, abs(n) - half)
    return math.hypot(ds, dn)


def sampled_path_clearance(
    path: list[tuple[float, float]],
    walls: list[dict],
    hazard_center: tuple[float, float],
    hazard_radius: float,
    body_radius: float,
) -> tuple[float, float]:
    wall_clearance = math.inf
    hazard_clearance = math.inf
    for start, end in zip(path, path[1:]):
        length = math.dist(start, end)
        samples = max(2, int(math.ceil(length / 0.02)))
        for index in range(samples + 1):
            t = index / samples
            point = (
                start[0] + t * (end[0] - start[0]),
                start[1] + t * (end[1] - start[1]),
            )
            wall_clearance = min(
                wall_clearance,
                min(point_wall_surface_distance(point, wall) for wall in walls)
                - body_radius,
            )
            hazard_clearance = min(
                hazard_clearance,
                math.dist(point, hazard_center) - hazard_radius - body_radius,
            )
    return wall_clearance, hazard_clearance


def first_diagonal_reveal(
    walls: list[dict], hazard_center: tuple[float, float]
) -> float | None:
    for index in range(1501):
        station = 7.5 + index * 0.01
        if not blocked((station, station), hazard_center, walls):
            return station
    return None


def angle_delta_deg(value: float) -> float:
    return math.degrees(math.atan2(math.sin(value), math.cos(value)))


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "static-blind-corner-supplement-v3":
        errors.append("unexpected schema")
    maps = manifest.get("maps") or []
    if len(maps) != 5:
        errors.append(f"expected 5 maps, found {len(maps)}")

    hazard = manifest["hazard"]
    hazard_center = tuple(hazard["center_xy_m"])
    hazard_radius = float(hazard["radius_m"])
    body_radius = float(manifest["body_radius_m"])
    z_min, z_max = manifest["validated_flight_z_envelope_m"]
    if z_min < 0.0 or z_max + body_radius > float(hazard["height_m"]):
        errors.append("hazard does not cover validated 3D body envelope")

    reveal_stations: list[float] = []
    reveal_distances: list[float] = []
    reveal_inner_edge_angles: list[float] = []
    bypass_wall_clearances: list[float] = []
    bypass_hazard_clearances: list[float] = []
    approach_wall_clearances: list[float] = []
    approach_hazard_clearances: list[float] = []

    for expected_tier, item in enumerate(maps, start=1):
        if int(item["radius_tier"]) != expected_tier:
            errors.append(f"unexpected tier order: {item['map']}")
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
        reference = f'pcd_name: "seed_maps/{item["map"]}.pcd"'
        if reference not in config_path.read_text():
            errors.append(f"config reference mismatch: {item['map']}")

        walls = item["walls"]
        if any(float(wall["height_m"]) < z_max + body_radius for wall in walls):
            errors.append(f"wall does not cover 3D body envelope: {item['map']}")
        for station in (11.0, 14.0, 17.0, 20.0):
            if not blocked((station, station), hazard_center, walls):
                errors.append(
                    f"hazard visible before blind corner: {item['map']}@{station}"
                )

        reveal = first_diagonal_reveal(walls, hazard_center)
        if reveal is None:
            errors.append(f"no diagonal reveal: {item['map']}")
            continue
        reveal_stations.append(reveal)
        reveal_distance = math.dist((reveal, reveal), hazard_center)
        reveal_distances.append(reveal_distance)
        bearing = math.atan2(hazard_center[1] - reveal, hazard_center[0] - reveal)
        relative = abs(angle_delta_deg(bearing - math.pi / 4.0))
        angular_radius = math.degrees(math.asin(hazard_radius / reveal_distance))
        inner_edge = relative - angular_radius
        reveal_inner_edge_angles.append(inner_edge)
        if not 3.80 <= reveal_distance <= 4.30:
            errors.append(
                f"reveal distance outside [3.80,4.30]: {item['map']}="
                f"{reveal_distance:.6f}"
            )
        if inner_edge <= 50.0:
            errors.append(
                f"entire hazard not outside 45-deg crop with 5-deg margin: "
                f"{item['map']}={inner_edge:.6f}"
            )

        approach = [(7.5, 7.5), (reveal - 0.05, reveal - 0.05)]
        approach_wall, approach_hazard = sampled_path_clearance(
            approach, walls, hazard_center, hazard_radius, body_radius
        )
        approach_wall_clearances.append(approach_wall)
        approach_hazard_clearances.append(approach_hazard)
        if approach_wall < 1.50 or approach_hazard < 2.20:
            errors.append(
                f"invalid approach clearance: {item['map']}="
                f"{approach_wall:.6f}/{approach_hazard:.6f}"
            )

        bypass = [
            (24.0, 24.0),
            (22.5, 25.36),
            (17.5, 25.36),
            (6.2, 24.0),
        ]
        bypass_wall, bypass_hazard = sampled_path_clearance(
            bypass, walls, hazard_center, hazard_radius, body_radius
        )
        bypass_wall_clearances.append(bypass_wall)
        bypass_hazard_clearances.append(bypass_hazard)
        if bypass_wall < 0.20 - 1e-6 or bypass_hazard < 0.20 - 1e-6:
            errors.append(
                f"invalid bypass clearance: {item['map']}="
                f"{bypass_wall:.6f}/{bypass_hazard:.6f}"
            )

        by_name = {wall["name"]: wall for wall in walls}
        joins = (
            (
                tuple(by_name["inner_diagonal"]["end_xy_m"]),
                by_name["inner_south"],
            ),
            (
                tuple(by_name["outer_diagonal"]["end_xy_m"]),
                by_name["outer_east"],
            ),
            (
                tuple(by_name["outer_north"]["end_xy_m"]),
                by_name["outer_east"],
            ),
        )
        if any(
            point_wall_surface_distance(point, wall) > 1e-6
            for point, wall in joins
        ):
            errors.append(f"channel wall join gap: {item['map']}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "map_count": len(maps),
        "source_seeds": manifest.get("source_seeds"),
        "flight_z_envelope_m": [z_min, z_max],
        "hazard_center_xy_m": list(hazard_center),
        "hazard_radius_m": hazard_radius,
        "reveal_stations_xy_m": [round(value, 3) for value in reveal_stations],
        "reveal_distances_m": [round(value, 6) for value in reveal_distances],
        "reveal_hazard_inner_edge_relative_deg": [
            round(value, 6) for value in reveal_inner_edge_angles
        ],
        "approach_wall_body_clearance_min_m": round(
            min(approach_wall_clearances, default=math.nan), 6
        ),
        "approach_hazard_body_clearance_min_m": round(
            min(approach_hazard_clearances, default=math.nan), 6
        ),
        "bypass_wall_body_clearance_min_m": round(
            min(bypass_wall_clearances, default=math.nan), 6
        ),
        "bypass_hazard_body_clearance_min_m": round(
            min(bypass_hazard_clearances, default=math.nan), 6
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
