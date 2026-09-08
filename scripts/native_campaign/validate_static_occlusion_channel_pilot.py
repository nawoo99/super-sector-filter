#!/usr/bin/env python3
"""Fail closed on the frozen channelized static-occlusion pilot assets."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "static_occlusion_channel_pilot_manifest.json"
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
    # Liang-Barsky clipping in wall-local coordinates.
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


def line_of_sight_blocked(
    origin: tuple[float, float],
    target: tuple[float, float],
    walls: list[dict],
    *,
    nominal: bool,
    z: float,
    slit: dict,
) -> bool:
    for wall in walls:
        if not segment_hits_wall(origin, target, wall):
            continue
        if (
            nominal
            and wall["sensor_slit"]
            and slit["z_min_m"] <= z <= slit["z_max_m"]
        ):
            continue
        return True
    return False


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


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "static-occlusion-channel-pilot-v2":
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
            errors.append(f"point-count mismatch: {item['map']}")
        reference = f'pcd_name: "seed_maps/{item["map"]}.pcd"'
        if reference not in config_path.read_text():
            errors.append(f"config reference mismatch: {item['map']}")

    point_deltas = set()
    for tier in range(1, 6):
        pair = by_tier.get(tier, [])
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
        if not nominal["sensor_slit_open"] or occluded["sensor_slit_open"]:
            errors.append(f"tier {tier}: slit treatment mismatch")
        delta = int(occluded["point_count"]) - int(nominal["point_count"])
        wall_delta = int(occluded["wall_point_count"]) - int(
            nominal["wall_point_count"]
        )
        if delta <= 0 or delta != wall_delta:
            errors.append(f"tier {tier}: invalid slit-only point delta {delta}")
        point_deltas.add(delta)
    if len(point_deltas) != 1:
        errors.append(f"pair slit deltas differ across tiers: {point_deltas}")

    body_radius = float(manifest["body_radius_m"])
    slit = manifest["nominal_sensor_slit"]
    slit_height = float(slit["height_m"])
    if slit_height >= 2.0 * body_radius or slit["body_traversable"]:
        errors.append("nominal sensor slit is body-traversable")

    walls = manifest["walls"]
    hazard = manifest["hazard"]
    hazard_center = tuple(hazard["center_xy_m"])
    hazard_radius = float(hazard["radius_m"])
    probe_z = 1.45
    hidden_stations = (11.0, 14.0, 17.0, 20.0)
    for station in hidden_stations:
        origin = (station, station)
        if line_of_sight_blocked(
            origin, hazard_center, walls, nominal=True, z=probe_z, slit=slit
        ):
            errors.append(f"nominal slit LOS blocked at x=y={station}")
        if not line_of_sight_blocked(
            origin, hazard_center, walls, nominal=False, z=probe_z, slit=slit
        ):
            errors.append(f"occluded LOS visible early at x=y={station}")

    reveal_station = (22.4, 22.4)
    if line_of_sight_blocked(
        reveal_station,
        hazard_center,
        walls,
        nominal=False,
        z=probe_z,
        slit=slit,
    ):
        errors.append("occluded LOS remains blocked in reveal chamber")
    nominal_horizon_distance = math.dist((11.0, 11.0), hazard_center)
    reveal_distance = math.dist(reveal_station, hazard_center)
    if nominal_horizon_distance > 15.0:
        errors.append("nominal hazard is outside the 15 m horizon at station 11")
    if not 4.0 <= reveal_distance <= 6.0:
        errors.append(f"unexpected reveal distance {reveal_distance:.6f}")

    approach = [(7.5, 7.5), (22.0, 22.0)]
    approach_wall_clearance, approach_hazard_clearance = sampled_path_clearance(
        approach, walls, hazard_center, hazard_radius, body_radius
    )
    if approach_wall_clearance < 1.50:
        errors.append(
            f"approach wall body clearance below 1.50 m: "
            f"{approach_wall_clearance:.6f}"
        )
    if approach_hazard_clearance < 3.0:
        errors.append(
            f"hazard intrudes on approach: {approach_hazard_clearance:.6f}"
        )

    bypass = [(24.0, 24.0), (21.0, 25.2), (15.0, 25.2), (6.2, 24.0)]
    bypass_wall_clearance, bypass_hazard_clearance = sampled_path_clearance(
        bypass, walls, hazard_center, hazard_radius, body_radius
    )
    if bypass_wall_clearance < 0.30:
        errors.append(
            f"bypass wall body clearance below 0.30 m: "
            f"{bypass_wall_clearance:.6f}"
        )
    if bypass_hazard_clearance < 0.20:
        errors.append(
            f"bypass hazard body clearance below 0.20 m: "
            f"{bypass_hazard_clearance:.6f}"
        )

    # Inner diagonal-to-south and outer diagonal-to-east-to-north joins must
    # overlap at wall thickness, preventing the broad edge bypass seen in v1.
    by_name = {wall["name"]: wall for wall in walls}
    joins = (
        (tuple(by_name["inner_diagonal"]["end_xy_m"]), by_name["inner_south"]),
        (tuple(by_name["outer_diagonal"]["end_xy_m"]), by_name["outer_east"]),
        (tuple(by_name["outer_north"]["end_xy_m"]), by_name["outer_east"]),
    )
    join_distances = [point_wall_surface_distance(point, wall) for point, wall in joins]
    if any(distance > 1e-6 for distance in join_distances):
        errors.append(f"channel wall join gap: {join_distances}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "map_count": len(maps),
        "pair_count": len(by_tier),
        "source_seeds": manifest.get("source_seeds"),
        "slit_height_m": slit_height,
        "body_diameter_m": 2.0 * body_radius,
        "nominal_horizon_distance_m": round(nominal_horizon_distance, 6),
        "occluded_reveal_distance_m": round(reveal_distance, 6),
        "approach_wall_body_clearance_m": round(approach_wall_clearance, 6),
        "approach_hazard_body_clearance_m": round(
            approach_hazard_clearance, 6
        ),
        "bypass_wall_body_clearance_m": round(bypass_wall_clearance, 6),
        "bypass_hazard_body_clearance_m": round(bypass_hazard_clearance, 6),
        "hidden_center_ray_stations_m": list(hidden_stations),
        "reveal_center_ray_station_xy_m": list(reveal_station),
        "pair_slit_point_delta": next(iter(point_deltas), None),
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
