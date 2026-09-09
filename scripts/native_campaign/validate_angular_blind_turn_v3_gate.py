#!/usr/bin/env python3
"""Validate the v3 fixture with the actual PCD and ROG inflation lattice."""

from __future__ import annotations

import argparse
import heapq
import json
import math
import os
from pathlib import Path
from typing import Iterable

from gen_static_blind_corner_supplement import sha256


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "angular_blind_turn_v3_gate_manifest.json"

Cell = tuple[int, int]


def read_pcd(path: Path) -> tuple[dict[str, str], list[tuple[float, float, float]]]:
    header: dict[str, str] = {}
    points: list[tuple[float, float, float]] = []
    in_data = False
    with path.open() as stream:
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not in_data:
                key, _, value = stripped.partition(" ")
                header[key] = value
                if key == "DATA":
                    if value != "ascii":
                        raise ValueError("only ASCII PCD is supported")
                    in_data = True
                continue
            fields = stripped.split()
            if len(fields) < 3:
                raise ValueError("malformed PCD point")
            point = tuple(float(value) for value in fields[:3])
            if not all(math.isfinite(value) for value in point):
                raise ValueError("non-finite PCD point")
            points.append(point)
    return header, points


def point_to_cell(point: tuple[float, float], resolution: float) -> Cell:
    return tuple(math.floor(value / resolution + 1e-9) for value in point)  # type: ignore[return-value]


def cell_center(cell: Cell, resolution: float) -> tuple[float, float]:
    return tuple((value + 0.5) * resolution for value in cell)  # type: ignore[return-value]


def inflate_cells(
    occupied: Iterable[Cell], inflation_step: int
) -> set[Cell]:
    offsets = [
        (dx, dy)
        for dx in range(-inflation_step, inflation_step + 1)
        for dy in range(-inflation_step, inflation_step + 1)
        if dx * dx + dy * dy <= inflation_step * inflation_step
    ]
    return {
        (cell[0] + offset[0], cell[1] + offset[1])
        for cell in occupied
        for offset in offsets
    }


def astar(
    start: Cell,
    goal: Cell,
    blocked: set[Cell],
    bounds: tuple[int, int, int, int],
) -> list[Cell] | None:
    if start in blocked or goal in blocked:
        return None
    min_x, max_x, min_y, max_y = bounds
    frontier: list[tuple[float, float, Cell]] = [(0.0, 0.0, start)]
    cost = {start: 0.0}
    parent: dict[Cell, Cell] = {}
    while frontier:
        _, current_cost, current = heapq.heappop(frontier)
        if current_cost > cost.get(current, math.inf) + 1e-12:
            continue
        if current == goal:
            path = [current]
            while path[-1] != start:
                path.append(parent[path[-1]])
            path.reverse()
            return path
        for dx, dy in (
            (-1, -1), (-1, 0), (-1, 1), (0, -1),
            (0, 1), (1, -1), (1, 0), (1, 1),
        ):
            neighbor = (current[0] + dx, current[1] + dy)
            if not (min_x <= neighbor[0] <= max_x and min_y <= neighbor[1] <= max_y):
                continue
            if neighbor in blocked:
                continue
            if dx and dy and (
                (current[0] + dx, current[1]) in blocked
                or (current[0], current[1] + dy) in blocked
            ):
                continue
            candidate = current_cost + math.hypot(dx, dy)
            if candidate + 1e-12 >= cost.get(neighbor, math.inf):
                continue
            cost[neighbor] = candidate
            parent[neighbor] = current
            heuristic = math.dist(neighbor, goal)
            heapq.heappush(frontier, (candidate + heuristic, candidate, neighbor))
    return None


def path_length(path: list[Cell], resolution: float) -> float:
    return sum(math.dist(a, b) for a, b in zip(path, path[1:])) * resolution


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 0.0:
        return math.dist(point, start)
    fraction = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / denominator
    fraction = min(1.0, max(0.0, fraction))
    return math.dist(
        point,
        (start[0] + fraction * dx, start[1] + fraction * dy),
    )


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "angular-blind-turn-v3-open-bypass-gate-v1":
        errors.append("unexpected manifest schema")
    map_name = manifest.get("map")
    pcd_path = PCD_DIR / f"{map_name}.pcd"
    config_path = CONFIG_DIR / f"{map_name}.yaml"
    if not pcd_path.is_file() or not config_path.is_file():
        return {"status": "FAIL", "errors": ["runtime asset missing"]}
    if sha256(pcd_path) != manifest.get("pcd_sha256"):
        errors.append("PCD hash mismatch")
    if sha256(config_path) != manifest.get("config_sha256"):
        errors.append("config hash mismatch")
    if manifest.get("upper_channel_wall_present") is not False:
        errors.append("upper channel wall was not removed")

    header, points = read_pcd(pcd_path)
    if int(header.get("POINTS", -1)) != len(points):
        errors.append("PCD header/data point count mismatch")
    if len(points) != int(manifest.get("point_count", -1)):
        errors.append("manifest/data point count mismatch")

    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    inflation_step = int(route["inflation_step"])
    if not math.isclose(resolution, 0.1, abs_tol=1e-12):
        errors.append("ROG inflation resolution changed")
    if inflation_step != 3:
        errors.append("ROG inflation step changed")
    flight_z = float(route["flight_z_m"])
    z_slice = [
        (x, y)
        for x, y, z in points
        if abs(z - flight_z) <= resolution / 2.0 + 1e-9
    ]
    if not z_slice:
        errors.append("empty flight-height PCD slice")
    occupied = {point_to_cell(point, resolution) for point in z_slice}
    blocked = inflate_cells(occupied, inflation_step)

    bounds_m = tuple(float(value) for value in route["bounds_xy_m"])
    bounds = (
        math.floor(bounds_m[0] / resolution),
        math.floor(bounds_m[1] / resolution),
        math.floor(bounds_m[2] / resolution),
        math.floor(bounds_m[3] / resolution),
    )
    anchors = [tuple(float(value) for value in point) for point in route["anchors_xy_m"]]
    local_anchor_distance = math.dist(anchors[0], anchors[1])
    if local_anchor_distance > float(route["planning_horizon_m"]) + 1e-12:
        errors.append("first bypass anchor lies outside planning horizon")

    paths: list[list[Cell]] = []
    segment_lengths: list[float] = []
    for index, (start_xy, goal_xy) in enumerate(zip(anchors, anchors[1:])):
        found = astar(
            point_to_cell(start_xy, resolution),
            point_to_cell(goal_xy, resolution),
            blocked,
            bounds,
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

    path_centers = [
        cell_center(cell, resolution) for path in paths for cell in path
    ]
    minimum_surface_distance = min(
        (
            math.dist(path_point, obstacle_point)
            for path_point in path_centers
            for obstacle_point in z_slice
        ),
        default=math.nan,
    )
    # Grid-centre discretisation can reduce a nominal 0.30 m lattice margin
    # by half a cell. Require 0.25 m against the actual PCD surface samples.
    if not math.isfinite(minimum_surface_distance) or minimum_surface_distance < 0.25:
        errors.append("inflated path has insufficient sampled-surface clearance")

    result = {
        "schema": "angular-blind-turn-v3-route-gate-v1",
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
        "errors": errors,
    }
    return result


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
