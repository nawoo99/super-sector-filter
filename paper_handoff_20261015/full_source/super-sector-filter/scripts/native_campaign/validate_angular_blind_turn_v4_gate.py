#!/usr/bin/env python3
"""Validate v4 with the actual PCD and ROG-equivalent inflation lattice."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from validate_angular_blind_turn_v3_gate import (
    astar,
    cell_center,
    inflate_cells,
    path_length,
    point_segment_distance,
    point_to_cell,
    read_pcd,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "angular_blind_turn_v4_gate_manifest.json"


def in_forward_sector(
    point: tuple[float, float],
    position: tuple[float, float],
    yaw_deg: float,
    half_angle_deg: float,
    horizon_m: float,
) -> bool:
    dx, dy = point[0] - position[0], point[1] - position[1]
    distance = math.hypot(dx, dy)
    if distance > horizon_m or distance <= 1e-12:
        return distance <= horizon_m
    yaw = math.radians(yaw_deg)
    return dx * math.cos(yaw) + dy * math.sin(yaw) >= (
        distance * math.cos(math.radians(half_angle_deg))
    )


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "angular-blind-turn-v4-observed-exit-gate-v1":
        errors.append("unexpected manifest schema")
    if manifest.get("change_from_parent") != "add north observation wall only":
        errors.append("v4 change scope is not frozen")
    map_name = manifest.get("map")
    pcd_path = PCD_DIR / f"{map_name}.pcd"
    config_path = CONFIG_DIR / f"{map_name}.yaml"
    if not pcd_path.is_file() or not config_path.is_file():
        return {"status": "FAIL", "errors": ["runtime asset missing"]}
    if sha256(pcd_path) != manifest.get("pcd_sha256"):
        errors.append("PCD hash mismatch")
    if sha256(config_path) != manifest.get("config_sha256"):
        errors.append("config hash mismatch")
    observation_wall = manifest.get("observation_wall", {})
    if observation_wall.get("start_xy_m") != [-10.0, 29.0] or (
        observation_wall.get("end_xy_m") != [24.0, 29.0]
    ):
        errors.append("observation wall geometry changed")

    header, points = read_pcd(pcd_path)
    if int(header.get("POINTS", -1)) != len(points):
        errors.append("PCD header/data point count mismatch")
    if len(points) != int(manifest.get("point_count", -1)):
        errors.append("manifest/data point count mismatch")

    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    inflation_step = int(route["inflation_step"])
    flight_z = float(route["flight_z_m"])
    z_slice = [
        (x, y)
        for x, y, z in points
        if abs(z - flight_z) <= resolution / 2.0 + 1e-9
    ]
    occupied = {point_to_cell(point, resolution) for point in z_slice}
    blocked = inflate_cells(occupied, inflation_step)
    bounds_m = tuple(float(value) for value in route["bounds_xy_m"])
    bounds = tuple(math.floor(value / resolution) for value in bounds_m)
    anchors = [tuple(float(value) for value in point) for point in route["anchors_xy_m"]]
    local_anchor_distance = math.dist(anchors[0], anchors[1])
    if local_anchor_distance > float(route["planning_horizon_m"]) + 1e-12:
        errors.append("first bypass anchor lies outside planning horizon")

    paths: list[list[tuple[int, int]]] = []
    segment_lengths: list[float] = []
    for index, (start_xy, goal_xy) in enumerate(zip(anchors, anchors[1:])):
        found = astar(
            point_to_cell(start_xy, resolution),
            point_to_cell(goal_xy, resolution),
            blocked,
            bounds,  # type: ignore[arg-type]
        )
        if found is None:
            errors.append(f"inflated A* segment {index} has NO_PATH")
            continue
        paths.append(found)
        segment_lengths.append(path_length(found, resolution))

    hazard = manifest["hazard"]
    hazard_center = tuple(float(value) for value in hazard["center_xy_m"])
    hazard_radius = float(hazard["radius_m"])
    direct_distance = point_segment_distance(
        hazard_center,
        tuple(manifest["route_waypoints_xy_m"][0]),
        tuple(manifest["route_waypoints_xy_m"][1]),
    )
    if direct_distance > hazard_radius:
        errors.append("direct outgoing route does not intersect hazard")

    path_centers = [cell_center(cell, resolution) for path in paths for cell in path]
    minimum_surface_distance = min(
        (
            math.dist(path_point, obstacle_point)
            for path_point in path_centers
            for obstacle_point in z_slice
        ),
        default=math.nan,
    )
    if not math.isfinite(minimum_surface_distance) or minimum_surface_distance < 0.25:
        errors.append("inflated path has insufficient sampled-surface clearance")

    liveness = manifest["liveness_check"]
    station_support_counts: dict[str, int] = {}
    for station in liveness["stations"]:
        position = tuple(float(value) for value in station["position_xyz_m"][:2])
        count = sum(
            in_forward_sector(
                point,
                position,
                float(liveness["yaw_deg"]),
                float(liveness["sector_half_angle_deg"]),
                float(liveness["sensing_horizon_m"]),
            )
            for point in z_slice
        )
        station_support_counts[station["name"]] = count
        if count < 10:
            errors.append(f"insufficient geometric liveness support at {station['name']}")

    return {
        "schema": "angular-blind-turn-v4-route-gate-v1",
        "status": "PASS" if not errors else "FAIL",
        "map": map_name,
        "pcd_point_count": len(points),
        "flight_height_point_count": len(z_slice),
        "base_occupied_cells": len(occupied),
        "inflated_blocked_cells": len(blocked),
        "inflation_resolution_m": resolution,
        "inflation_step": inflation_step,
        "inflation_radius_m": resolution * inflation_step,
        "local_anchor_euclidean_distance_m": round(local_anchor_distance, 6),
        "planning_horizon_m": float(route["planning_horizon_m"]),
        "segment_path_lengths_m": [round(value, 6) for value in segment_lengths],
        "total_forced_bypass_path_length_m": round(sum(segment_lengths), 6),
        "minimum_path_to_sampled_surface_m": round(minimum_surface_distance, 6),
        "direct_route_hazard_centerline_distance_m": round(direct_distance, 6),
        "station_geometric_support_points": station_support_counts,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_suffix(args.out.suffix + ".tmp")
        temporary.write_text(rendered)
        os.replace(temporary, args.out)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
