#!/usr/bin/env python3
"""Fail closed on the frozen shm1_h3 transverse-wall pair."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from gen_static_heading_mismatch_h3 import MANIFEST_PATH, PCD_DIR, CONFIG_DIR
from validate_angular_blind_turn_v3_gate import (
    astar, inflate_cells, path_length, point_to_cell, read_pcd,
)
from validate_static_blind_doorway_exploration import in_forward_sector


def point_segment_distance(point, start, end):
    px, py = point
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    scale = dx * dx + dy * dy
    if scale <= 1e-12:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / scale))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def validate(
    manifest_path: Path = MANIFEST_PATH,
    expected_schema: str = "static-heading-mismatch-v3",
    expected_maps: set[str] | tuple[str, ...] = (
        "shm1_h3_clear", "shm1_h3_hazard"
    ),
) -> dict:
    errors = []
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema") != expected_schema:
        errors.append("unexpected manifest schema")
    rows = {item["map"]: item for item in manifest.get("maps", [])}
    expected = set(expected_maps)
    if set(rows) != expected:
        errors.append("unexpected map pair")

    loaded = {}
    for name, item in rows.items():
        pcd = PCD_DIR / f"{name}.pcd"
        config = CONFIG_DIR / f"{name}.yaml"
        if not pcd.is_file() or not config.is_file():
            errors.append(f"{name}: runtime asset missing")
            continue
        if sha256(pcd) != item.get("pcd_sha256"):
            errors.append(f"{name}: PCD hash mismatch")
        if sha256(config) != item.get("config_sha256"):
            errors.append(f"{name}: config hash mismatch")
        header, points = read_pcd(pcd)
        if int(header.get("POINTS", -1)) != len(points):
            errors.append(f"{name}: PCD header/data mismatch")
        loaded[name] = points

    clear_name = next((name for name, item in rows.items()
                       if not item.get("include_hazard")), "")
    hazard_name = next((name for name, item in rows.items()
                        if item.get("include_hazard")), "")
    extra = Counter(loaded.get(hazard_name, [])) - Counter(
        loaded.get(clear_name, [])
    )
    removed = Counter(loaded.get(clear_name, [])) - Counter(
        loaded.get(hazard_name, [])
    )
    extra_points = sum(extra.values())
    if removed or extra_points <= 0:
        errors.append("pair does not differ only by a positive wall point set")

    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    flight_z = float(route["flight_z_m"])
    points = loaded.get(hazard_name, [])
    z_slice = [(x, y) for x, y, z in points
               if abs(z - flight_z) <= resolution / 2.0 + 1e-9]
    blocked = inflate_cells(
        {point_to_cell(p, resolution) for p in z_slice},
        int(route["inflation_step"]),
    )
    bounds = tuple(math.floor(float(v) / resolution)
                   for v in route["bounds_xy_m"])
    anchors = [tuple(map(float, p)) for p in route["bypass_anchors_xy_m"]]
    lengths = []
    for index, (start, goal) in enumerate(zip(anchors, anchors[1:])):
        path = astar(point_to_cell(start, resolution), point_to_cell(goal, resolution),
                     blocked, bounds)
        if path is None:
            errors.append(f"inflated bypass segment {index} has NO_PATH")
        else:
            lengths.append(path_length(path, resolution))

    hazard = manifest["hazard"]
    wall_start = tuple(map(float, hazard["start_xy_m"]))
    wall_end = tuple(map(float, hazard["end_xy_m"]))
    direct_start, direct_end = [tuple(map(float, p))
                                for p in route["direct_route_segment_xy_m"]]
    direct_surface_distance = min(
        point_segment_distance((x, y), direct_start, direct_end)
        for x, y, z in extra
        if abs(z - flight_z) <= resolution / 2.0 + 1e-9
    )
    direct_clearance = direct_surface_distance - float(manifest["body_radius_m"])
    if direct_clearance >= 0.0:
        errors.append("direct route does not body-intersect transverse wall")

    position = tuple(map(float, manifest["visibility_check"]["position_xyz_m"][:2]))
    visible = [(x, y) for x, y, _ in extra
               if math.dist(position, (x, y)) <= 15.0]
    vis = manifest["visibility_check"]
    body_inside = sum(in_forward_sector(
        p, position, float(vis["body_yaw_deg"]),
        float(vis["sector_half_angle_deg"]), float(vis["sensing_horizon_m"])
    ) for p in visible)
    velocity_inside = sum(in_forward_sector(
        p, position, float(vis["velocity_yaw_deg"]),
        float(vis["sector_half_angle_deg"]), float(vis["sensing_horizon_m"])
    ) for p in visible)
    if len(visible) < 20:
        errors.append("raw initial wall visibility insufficient")
    if body_inside:
        errors.append("wall leaks into body-fixed Sector at initial pose")
    if velocity_inside < 20:
        errors.append("wall absent from velocity-aligned Sector")

    return {
        "schema": "static-heading-mismatch-structure-gate-v" +
        expected_schema.rsplit("-v", 1)[-1],
        "status": "PASS" if not errors else "FAIL",
        "maps": sorted(rows),
        "pair_extra_hazard_points": extra_points,
        "inflated_bypass_segment_lengths_m": [round(v, 6) for v in lengths],
        "inflated_bypass_exists": len(lengths) == len(anchors) - 1,
        "direct_route_body_clearance_m": round(direct_clearance, 6),
        "raw_visible_hazard_samples": len(visible),
        "body_sector_visible_samples": body_inside,
        "velocity_sector_visible_samples": velocity_inside,
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
