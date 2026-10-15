#!/usr/bin/env python3
"""Fail closed on the preregistered shm1_h1 scenario pair."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from validate_angular_blind_turn_v3_gate import (
    astar, inflate_cells, path_length, point_segment_distance, point_to_cell, read_pcd,
)
from validate_static_blind_doorway_exploration import (
    in_forward_sector, visible_hazard_samples,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "static_heading_mismatch_manifest.json"


def validate(
    manifest_path: Path = MANIFEST_PATH,
    expected_schema: str = "static-heading-mismatch-v1",
    expected_maps: tuple[str, ...] | set[str] = ("shm1_h1_clear", "shm1_h1_hazard"),
) -> dict:
    errors = []
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema") != expected_schema:
        errors.append("unexpected manifest schema")
    rows = {item["map"]: item for item in manifest.get("maps", [])}
    if set(rows) != set(expected_maps):
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

    extra_points = None
    if len(loaded) == 2:
        clear_name = next(name for name, item in rows.items() if not item["include_hazard"])
        hazard_name = next(name for name, item in rows.items() if item["include_hazard"])
        clear = Counter(loaded[clear_name])
        hazard = Counter(loaded[hazard_name])
        if clear - hazard:
            errors.append("hazard member changed background points")
        extra_points = sum((hazard - clear).values())
        expected_extra = sum(hazard.values()) - sum(clear.values())
        if extra_points <= 0 or extra_points != expected_extra:
            errors.append("pair does not differ by a positive hazard set")

    hazard_name = next((name for name, item in rows.items() if item.get("include_hazard")), "")
    points = loaded.get(hazard_name, [])
    route = manifest["route_check"]
    resolution = float(route["resolution_m"])
    z = float(route["flight_z_m"])
    z_slice = [(x, y) for x, y, pz in points if abs(pz - z) <= resolution / 2 + 1e-9]
    blocked = inflate_cells(
        {point_to_cell(point, resolution) for point in z_slice},
        int(route["inflation_step"]),
    )
    bounds = tuple(math.floor(float(v) / resolution) for v in route["bounds_xy_m"])
    anchors = [tuple(map(float, point)) for point in route["bypass_anchors_xy_m"]]
    lengths = []
    for index, (start, goal) in enumerate(zip(anchors, anchors[1:])):
        path = astar(point_to_cell(start, resolution), point_to_cell(goal, resolution), blocked, bounds)
        if path is None:
            errors.append(f"inflated bypass segment {index} has NO_PATH")
        else:
            lengths.append(path_length(path, resolution))

    start, goal = [tuple(map(float, point)) for point in route["direct_route_segment_xy_m"]]
    hazard = manifest["hazard"]
    center = tuple(map(float, hazard["center_xy_m"]))
    direct_clearance = (
        point_segment_distance(center, start, goal)
        - float(hazard["radius_m"])
        - float(manifest["body_radius_m"])
    )
    if direct_clearance >= 0:
        errors.append("direct route does not body-intersect hazard")

    visibility = manifest["visibility_check"]
    position = tuple(map(float, visibility["position_xyz_m"][:2]))
    visible = visible_hazard_samples(manifest, position)
    body_inside = sum(in_forward_sector(
        point, position, float(visibility["body_yaw_deg"]),
        float(visibility["sector_half_angle_deg"]), float(visibility["sensing_horizon_m"]),
    ) for point in visible)
    velocity_inside = sum(in_forward_sector(
        point, position, float(visibility["velocity_yaw_deg"]),
        float(visibility["sector_half_angle_deg"]), float(visibility["sensing_horizon_m"]),
    ) for point in visible)
    if len(visible) < 20:
        errors.append("raw initial hazard visibility insufficient")
    if body_inside:
        errors.append("hazard leaks into body-fixed Sector")
    if velocity_inside < 20:
        errors.append("hazard absent from velocity-aligned Sector")

    return {
        "schema": "static-heading-mismatch-structure-gate-v" + expected_schema.rsplit("-v", 1)[-1],
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
