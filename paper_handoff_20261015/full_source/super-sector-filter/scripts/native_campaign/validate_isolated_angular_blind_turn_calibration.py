#!/usr/bin/env python3
"""Fail-closed structural validator for ``abt2_cal_t1..t5``."""

from __future__ import annotations

import json
import math
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from validate_static_blind_corner_supplement import (
    point_segment_distance,
    point_wall_surface_distance,
    segment_hits_wall,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "isolated_angular_blind_turn_manifest.json"


def pcd_header(path: Path) -> dict[str, str]:
    header = {}
    with path.open() as stream:
        for line in stream:
            key, _, value = line.strip().partition(" ")
            header[key] = value
            if key == "DATA":
                break
    return header


def walls_for_map(manifest: dict, item: dict) -> list[dict]:
    geometry = manifest["wall_geometry"]
    half_gap = float(item["aperture_width_m"]) / 2.0
    gap_x = float(item["aperture_center_x_m"])
    common = {
        "thickness_m": geometry["thickness_m"],
        "height_m": geometry["height_m"],
    }
    return [
        {
            **common,
            "name": "lower_occluder_west",
            "start_xy_m": [geometry["west_x_m"], geometry["lower_y_m"]],
            "end_xy_m": [gap_x - half_gap, geometry["lower_y_m"]],
        },
        {
            **common,
            "name": "lower_occluder_east",
            "start_xy_m": [gap_x + half_gap, geometry["lower_y_m"]],
            "end_xy_m": [geometry["east_x_m"], geometry["lower_y_m"]],
        },
        {
            **common,
            "name": "upper_channel",
            "start_xy_m": [geometry["west_x_m"], geometry["upper_y_m"]],
            "end_xy_m": [geometry["east_x_m"], geometry["upper_y_m"]],
        },
    ]


def circle_samples(center: tuple[float, float], radius: float):
    # Match the generator's actual horizontal cylinder samples exactly.
    count = max(8, int(round(2.0 * math.pi * radius / 0.05)))
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        yield (
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle),
        )


def first_visible_on_northbound(
    walls: list[dict], center: tuple[float, float], radius: float
) -> tuple[float, float, tuple[float, float]] | None:
    # 5 mm longitudinal resolution is much finer than one 10 Hz LiDAR frame
    # at 7 m/s; target points match the generated PCD surface lattice.
    targets = tuple(circle_samples(center, radius))
    for index in range(2581):
        y = 10.0 + 0.005 * index
        origin = (24.0, y)
        visible = [
            target for target in targets
            if not any(segment_hits_wall(origin, target, wall) for wall in walls)
        ]
        if visible:
            def relative(target: tuple[float, float]) -> float:
                bearing = math.atan2(target[1] - y, target[0] - 24.0)
                delta = math.atan2(
                    math.sin(bearing - math.pi / 2.0),
                    math.cos(bearing - math.pi / 2.0),
                )
                return abs(math.degrees(delta))

            target = min(visible, key=relative)
            return y, relative(target), target
    return None


def body_clearance_to_geometry(
    point: tuple[float, float], walls: list[dict],
    hazard_center: tuple[float, float], hazard_radius: float,
    body_radius: float,
) -> float:
    clearance = math.dist(point, hazard_center) - hazard_radius - body_radius
    for wall in walls:
        clearance = min(
            clearance,
            point_wall_surface_distance(point, wall) - body_radius,
        )
    return clearance


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "isolated-angular-blind-turn-calibration-v2":
        errors.append("unexpected schema")
    maps = manifest.get("maps") or []
    if len(maps) != 5:
        errors.append(f"expected 5 maps, found {len(maps)}")
    if manifest["initial_position_xyz_m"] != [24.0, 0.0, 1.5]:
        errors.append("unexpected initial position")
    if not math.isclose(manifest["initial_yaw_rad"], math.pi / 2, abs_tol=1e-12):
        errors.append("initial yaw is not northbound")
    route = [tuple(point) for point in manifest["route_waypoints_xy_m"]]
    if route != [(24.0, 24.0), (0.0, 24.0)]:
        errors.append("unexpected isolated route")

    hazard = manifest["hazard"]
    center = tuple(hazard["center_xy_m"])
    radius = float(hazard["radius_m"])
    body_radius = float(manifest["body_radius_m"])
    reveal_y_values = []
    reveal_angles = []
    reveal_leads = []
    bypass_clearances = []
    for tier, item in enumerate(maps, start=1):
        map_name = item["map"]
        if map_name != f"abt2_cal_t{tier}":
            errors.append(f"unexpected map order/name: {map_name}")
        if not math.isclose(float(item["aperture_width_m"]), 0.38, abs_tol=1e-12):
            errors.append(f"aperture width changed: {map_name}")
        if float(item["aperture_width_m"]) >= 2.0 * body_radius:
            errors.append(f"aperture is body-passable: {map_name}")
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        if not pcd_path.is_file() or not config_path.is_file():
            errors.append(f"missing runtime asset: {map_name}")
            continue
        if sha256(pcd_path) != item["pcd_sha256"]:
            errors.append(f"PCD hash mismatch: {map_name}")
        if sha256(config_path) != item["config_sha256"]:
            errors.append(f"config hash mismatch: {map_name}")
        header = pcd_header(pcd_path)
        if header.get("DATA") != "ascii":
            errors.append(f"non-ASCII PCD: {map_name}")
        if int(header.get("POINTS", -1)) != int(item["point_count"]):
            errors.append(f"point-count mismatch: {map_name}")
        config = config_path.read_text()
        for fragment in (
            f'pcd_name: "seed_maps/{map_name}.pcd"',
            "  x: 24.0", "  y: 0.0", "  z: 1.5",
            "init_yaw: 1.570796326795",
        ):
            if fragment not in config:
                errors.append(f"config mismatch {fragment!r}: {map_name}")

        walls = walls_for_map(manifest, item)
        reveal = first_visible_on_northbound(walls, center, radius)
        if reveal is None:
            errors.append(f"hazard never revealed: {map_name}")
            continue
        reveal_y, relative_angle, target = reveal
        switch_y = 24.0 - float(manifest["waypoint_switch_distance_m"])
        lead_s = (switch_y - reveal_y) / float(manifest["design_max_speed_mps"])
        reveal_y_values.append(reveal_y)
        reveal_angles.append(relative_angle)
        reveal_leads.append(lead_s)
        if relative_angle <= 46.0:
            errors.append(f"insufficient 45-degree crop margin: {map_name}={relative_angle}")
        if lead_s < float(manifest["minimum_required_reveal_lead_s"]):
            errors.append(f"insufficient reveal lead: {map_name}={lead_s}")

        probe = tuple(item["probe_center_xy_m"])
        if math.dist(probe, target) > 0.20:
            errors.append(f"surface probe misses first reveal patch: {map_name}")
        if abs(math.dist(probe, center) - radius) > 0.01:
            errors.append(f"probe is not on hazard surface: {map_name}")
        probe_radius = float(item["probe_radius_m"])
        if any(point_wall_surface_distance(probe, wall) <= probe_radius for wall in walls):
            errors.append(f"probe overlaps a wall: {map_name}")

        if point_segment_distance(center, (24.0, 24.0), (0.0, 24.0)) > radius:
            errors.append(f"direct outgoing route misses hazard: {map_name}")
        bypass = [(24.0, 22.5), (24.0, 26.8), (13.0, 26.8), (13.0, 24.0), (0.0, 24.0)]
        minimum = math.inf
        for start, end in zip(bypass, bypass[1:]):
            for sample in range(201):
                t = sample / 200.0
                point = (
                    start[0] + t * (end[0] - start[0]),
                    start[1] + t * (end[1] - start[1]),
                )
                minimum = min(
                    minimum,
                    body_clearance_to_geometry(
                        point, walls, center, radius, body_radius
                    ),
                )
        bypass_clearances.append(minimum)
        if minimum < 0.44:
            errors.append(f"northern bypass too tight: {map_name}={minimum}")

    z_min, z_max = manifest["validated_flight_z_envelope_m"]
    if z_min < 0.0 or z_max + body_radius > float(hazard["height_m"]):
        errors.append("hazard does not cover validated 3D body envelope")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "map_count": len(maps),
        "first_visible_northbound_y_m": [round(v, 3) for v in reveal_y_values],
        "first_visible_min_relative_deg": [round(v, 3) for v in reveal_angles],
        "worst_case_reveal_lead_s_at_7mps": [round(v, 3) for v in reveal_leads],
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
