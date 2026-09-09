#!/usr/bin/env python3
"""Fail closed on the first static blind-doorway exploratory fixture."""

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
MANIFEST_PATH = SCRIPT_DIR / "static_blind_doorway_exploration_manifest.json"


def in_forward_sector(point, position, yaw_deg, half_angle_deg, horizon_m):
    dx, dy = point[0] - position[0], point[1] - position[1]
    distance = math.hypot(dx, dy)
    if distance > horizon_m or distance <= 1e-12:
        return distance <= horizon_m
    yaw = math.radians(yaw_deg)
    return dx * math.cos(yaw) + dy * math.sin(yaw) >= (
        distance * math.cos(math.radians(half_angle_deg))
    )


def segment_intersects_box(start, end, bounds):
    """Return whether the open ray segment crosses an axis-aligned wall box."""
    xmin, xmax, ymin, ymax = bounds
    dx, dy = end[0] - start[0], end[1] - start[1]
    lo, hi = 0.0, 1.0
    for p, q0, q1 in ((dx, xmin - start[0], xmax - start[0]),
                      (dy, ymin - start[1], ymax - start[1])):
        if abs(p) <= 1e-12:
            if q0 > 0.0 or q1 < 0.0:
                return False
            continue
        a, b = sorted((q0 / p, q1 / p))
        lo, hi = max(lo, a), min(hi, b)
        if lo > hi:
            return False
    return hi > 1e-6 and lo < 1.0 - 1e-6


def visible_hazard_samples(manifest, position):
    hazard = manifest["hazard"]
    cx, cy = (float(v) for v in hazard["center_xy_m"])
    radius = float(hazard["radius_m"])
    half = float(manifest["walls"][0]["thickness_m"]) / 2.0
    wall_boxes = []
    for wall in manifest["walls"]:
        (x0, y0), (x1, y1) = wall["start_xy_m"], wall["end_xy_m"]
        wall_boxes.append((min(x0, x1) - half, max(x0, x1) + half,
                           min(y0, y1) - half, max(y0, y1) + half))
    samples = [
        (cx + radius * math.cos(2.0 * math.pi * i / 1440),
         cy + radius * math.sin(2.0 * math.pi * i / 1440))
        for i in range(1440)
    ]
    return [
        point for point in samples
        if not any(segment_intersects_box(position, point, box)
                   for box in wall_boxes)
    ]


def validate(
    manifest_path=MANIFEST_PATH,
    expected_schema="static-blind-doorway-exploration-v1",
    expected_maps=("sbd1_c1_clear", "sbd1_c1_hazard"),
):
    errors = []
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema") != expected_schema:
        errors.append("unexpected manifest schema")
    rows = {item["map"]: item for item in manifest.get("maps", [])}
    if set(rows) != set(expected_maps):
        errors.append("unexpected map pair")

    loaded = {}
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
        clear_names = [name for name, item in rows.items()
                       if not item.get("include_hazard")]
        hazard_names = [name for name, item in rows.items()
                        if item.get("include_hazard")]
        if len(clear_names) != 1 or len(hazard_names) != 1:
            errors.append("map pair needs one clear and one hazard member")
            clear_names = list(rows)[:1]
            hazard_names = list(rows)[1:2]
        clear_name = clear_names[0]
        hazard_name = hazard_names[0]
        clear = Counter(loaded[clear_name])
        hazard = Counter(loaded[hazard_name])
        if clear - hazard:
            errors.append("hazard member removed or changed clear-map points")
        pair_extra_points = sum((hazard - clear).values())
        expected = rows[hazard_name]["point_count"] - rows[clear_name][
            "point_count"
        ]
        if pair_extra_points != expected or expected <= 0:
            errors.append("map pair does not differ by one positive hazard set")

    hazard_name = next(
        (name for name, item in rows.items() if item.get("include_hazard")),
        "",
    )
    points = loaded.get(hazard_name, [])
    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    flight_z = float(route["flight_z_m"])
    z_slice = [(x, y) for x, y, z in points
               if abs(z - flight_z) <= resolution / 2.0 + 1e-9]
    occupied = {point_to_cell(point, resolution) for point in z_slice}
    blocked = inflate_cells(occupied, int(route["inflation_step"]))
    bounds = tuple(math.floor(float(v) / resolution)
                   for v in route["bounds_xy_m"])
    anchors = [tuple(float(v) for v in point)
               for point in route["anchors_xy_m"]]
    paths = []
    lengths = []
    for index, (start, goal) in enumerate(zip(anchors, anchors[1:])):
        path = astar(point_to_cell(start, resolution),
                     point_to_cell(goal, resolution), blocked, bounds)
        if path is None:
            errors.append(f"inflated A* segment {index} has NO_PATH")
            continue
        paths.append(path)
        lengths.append(path_length(path, resolution))
    path_centers = [cell_center(cell, resolution) for path in paths for cell in path]
    min_surface = min((math.dist(a, b) for a in path_centers for b in z_slice),
                      default=math.nan)
    if not math.isfinite(min_surface) or min_surface < 0.25:
        errors.append("inflated bypass lacks sampled-surface clearance")

    hazard = manifest["hazard"]
    center = tuple(float(v) for v in hazard["center_xy_m"])
    direct_distance = point_segment_distance(
        center, tuple(manifest["route_waypoints_xy_m"][0]),
        tuple(manifest["route_waypoints_xy_m"][1]))
    direct_body_clearance = (
        direct_distance
        - float(hazard["radius_m"])
        - float(manifest["body_radius_m"])
    )
    if direct_body_clearance >= 0.0:
        errors.append("nominal outgoing route does not body-intersect hazard")

    visibility = manifest["visibility_check"]
    pre = visible_hazard_samples(manifest, tuple(visibility["pre_reveal_position_xy_m"]))
    reveal_position = tuple(visibility["reveal_position_xy_m"])
    reveal = visible_hazard_samples(manifest, reveal_position)
    reveal_inside = sum(in_forward_sector(
        point, reveal_position, float(visibility["yaw_deg"]),
        float(visibility["sector_half_angle_deg"]), 15.0) for point in reveal)
    if pre:
        errors.append("analytic pre-reveal pose can see hazard")
    if len(reveal) < 20:
        errors.append("analytic reveal pose lacks hazard surface")
    if reveal_inside:
        errors.append("analytic reveal surface leaks into fixed Sector")

    liveness = manifest["liveness_check"]
    support = {}
    for station in liveness["stations"]:
        position = tuple(float(v) for v in station["position_xyz_m"][:2])
        count = sum(in_forward_sector(
            point, position, float(liveness["yaw_deg"]),
            float(liveness["sector_half_angle_deg"]),
            float(liveness["sensing_horizon_m"])) for point in z_slice)
        support[station["name"]] = count
        if count < int(liveness["minimum_geometric_support_points"]):
            errors.append(f"insufficient liveness support at {station['name']}")

    probe = tuple(float(v) for v in hazard["probe_center_xy_m"])
    wall_surface_distance = min(
        point_segment_distance(probe, tuple(w["start_xy_m"]),
                               tuple(w["end_xy_m"]))
        - float(w["thickness_m"]) / 2.0
        for w in manifest["walls"]
    )
    if wall_surface_distance <= float(hazard["probe_radius_m"]):
        errors.append("hazard probe overlaps a wall")

    return {
        "schema": "static-blind-doorway-structure-gate-v" +
        expected_schema.rsplit("-v", 1)[-1],
        "status": "PASS" if not errors else "FAIL",
        "maps": sorted(rows),
        "pair_extra_hazard_points": pair_extra_points,
        "flight_height_point_count": len(z_slice),
        "inflated_path_segment_lengths_m": [round(v, 6) for v in lengths],
        "minimum_path_to_sampled_surface_m": round(min_surface, 6),
        "direct_route_hazard_centerline_distance_m": round(direct_distance, 6),
        "direct_route_hazard_body_clearance_m": round(
            direct_body_clearance, 6
        ),
        "analytic_pre_reveal_visible_samples": len(pre),
        "analytic_reveal_visible_samples": len(reveal),
        "analytic_reveal_samples_inside_sector": reveal_inside,
        "probe_to_wall_surface_m": round(wall_surface_distance, 6),
        "station_geometric_support_points": support,
        "errors": errors,
    }


def main():
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
