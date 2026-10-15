#!/usr/bin/env python3
"""Fail closed on the preregistered sbd2 two-route topology."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from validate_angular_blind_turn_v3_gate import (
    astar,
    inflate_cells,
    path_length,
    point_segment_distance,
    point_to_cell,
    read_pcd,
)
from validate_static_blind_doorway_exploration import (
    in_forward_sector,
    visible_hazard_samples,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "static_two_route_blind_hazard_manifest.json"
EXPECTED_MAPS = {"sbd2_t1_clear", "sbd2_t1_hazard"}


def validate(
    manifest_path: Path = MANIFEST_PATH,
    expected_schema: str = "static-two-route-blind-hazard-v1",
    expected_maps: set[str] | tuple[str, ...] = EXPECTED_MAPS,
) -> dict:
    errors: list[str] = []
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema") != expected_schema:
        errors.append("unexpected manifest schema")
    rows = {item["map"]: item for item in manifest.get("maps", [])}
    if set(rows) != set(expected_maps):
        errors.append("unexpected map pair")

    loaded: dict[str, list[tuple[float, float, float]]] = {}
    for map_name, item in rows.items():
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        if not pcd_path.is_file() or not config_path.is_file():
            errors.append(f"{map_name}: runtime asset missing")
            continue
        if sha256(pcd_path) != item.get("pcd_sha256"):
            errors.append(f"{map_name}: PCD hash mismatch")
        if sha256(config_path) != item.get("config_sha256"):
            errors.append(f"{map_name}: config hash mismatch")
        header, points = read_pcd(pcd_path)
        if int(header.get("POINTS", -1)) != len(points):
            errors.append(f"{map_name}: PCD header/data mismatch")
        if len(points) != int(item.get("point_count", -1)):
            errors.append(f"{map_name}: manifest point count mismatch")
        loaded[map_name] = points

    pair_extra_points = None
    if len(loaded) == 2:
        clear_name = next(
            name for name, item in rows.items() if not item["include_hazard"]
        )
        hazard_name = next(
            name for name, item in rows.items() if item["include_hazard"]
        )
        clear = Counter(loaded[clear_name])
        hazard = Counter(loaded[hazard_name])
        if clear - hazard:
            errors.append("hazard member removed or changed clear-map points")
        pair_extra_points = sum((hazard - clear).values())
        expected = len(loaded[hazard_name]) - len(loaded[clear_name])
        if pair_extra_points != expected or expected <= 0:
            errors.append("map pair does not differ by one positive hazard set")

    hazard_name = next(
        (name for name, item in rows.items() if item.get("include_hazard")), ""
    )
    points = loaded.get(hazard_name, [])
    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    flight_z = float(route["flight_z_m"])
    z_slice = [
        (x, y)
        for x, y, z in points
        if abs(z - flight_z) <= resolution / 2.0 + 1e-9
    ]
    occupied = {point_to_cell(point, resolution) for point in z_slice}
    blocked = inflate_cells(occupied, int(route["inflation_step"]))
    bounds_m = [float(v) for v in route["bounds_xy_m"]]
    bounds = tuple(math.floor(v / resolution) for v in bounds_m)

    upper_paths = []
    upper_lengths = []
    anchors = [
        tuple(float(v) for v in point)
        for point in route["upper_route_anchors_xy_m"]
    ]
    for index, (start, goal) in enumerate(zip(anchors, anchors[1:])):
        path = astar(
            point_to_cell(start, resolution),
            point_to_cell(goal, resolution),
            blocked,
            bounds,
        )
        if path is None:
            errors.append(f"inflated upper-route segment {index} has NO_PATH")
            continue
        upper_paths.append(path)
        upper_lengths.append(path_length(path, resolution))

    lower_start, lower_goal = [
        tuple(float(v) for v in point)
        for point in route["lower_route_segment_xy_m"]
    ]
    # Restrict this check to the physical lower branch.  Its free-space band
    # lies between the inflated south wall and divider; leaving this band is
    # precisely taking the upper bypass rather than passing the closure.
    lower_bounds_m = (-1.5, 25.0, 18.4, 22.6)
    lower_bounds = tuple(math.floor(v / resolution) for v in lower_bounds_m)
    lower_path = astar(
        point_to_cell(lower_start, resolution),
        point_to_cell(lower_goal, resolution),
        blocked,
        lower_bounds,
    )
    if lower_path is not None:
        errors.append("inflated lower branch remains passable")

    hazard = manifest["hazard"]
    center = tuple(float(v) for v in hazard["center_xy_m"])
    direct_distance = point_segment_distance(center, lower_start, lower_goal)
    direct_body_clearance = (
        direct_distance
        - float(hazard["radius_m"])
        - float(manifest["body_radius_m"])
    )
    if direct_body_clearance >= 0.0:
        errors.append("nominal lower route does not body-intersect hazard")

    visibility = manifest["visibility_check"]
    decision = tuple(float(v) for v in visibility["decision_position_xyz_m"][:2])
    visible = visible_hazard_samples(manifest, decision)
    visible_inside = sum(
        in_forward_sector(
            point,
            decision,
            float(visibility["yaw_deg"]),
            float(visibility["sector_half_angle_deg"]),
            float(visibility["sensing_horizon_m"]),
        )
        for point in visible
    )
    if len(visible) < 20:
        errors.append("decision pose lacks line-of-sight hazard samples")
    if visible_inside:
        errors.append("decision-pose hazard leaks into Fixed Sector")

    liveness = manifest["liveness_check"]
    support = {}
    for station in liveness["stations"]:
        position = tuple(float(v) for v in station["position_xyz_m"][:2])
        count = sum(
            in_forward_sector(
                point,
                position,
                float(station["yaw_deg"]),
                float(liveness["sector_half_angle_deg"]),
                float(liveness["sensing_horizon_m"]),
            )
            for point in z_slice
        )
        support[station["name"]] = count
        if count < int(liveness["minimum_geometric_support_points"]):
            errors.append(f"insufficient liveness support at {station['name']}")

    return {
        "schema": "static-two-route-structure-gate-v" + expected_schema.rsplit("-v", 1)[-1],
        "status": "PASS" if not errors else "FAIL",
        "maps": sorted(rows),
        "pair_extra_hazard_points": pair_extra_points,
        "flight_height_point_count": len(z_slice),
        "upper_route_segment_lengths_m": [round(v, 6) for v in upper_lengths],
        "inflated_upper_route_exists": len(upper_paths) == len(anchors) - 1,
        "inflated_lower_branch_closed": lower_path is None,
        "direct_lower_route_body_clearance_m": round(direct_body_clearance, 6),
        "decision_visible_hazard_samples": len(visible),
        "decision_visible_samples_inside_sector": visible_inside,
        "station_geometric_support_points": support,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_suffix(args.out.suffix + ".tmp")
        temporary.write_text(rendered)
        os.replace(temporary, args.out)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
