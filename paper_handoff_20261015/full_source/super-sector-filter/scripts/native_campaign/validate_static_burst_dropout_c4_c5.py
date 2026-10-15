#!/usr/bin/env python3
"""Fail closed on the frozen C4/C5 static burst-dropout map pairs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

from gen_static_blind_corner_supplement import sha256
from gen_static_burst_dropout_c4_c5 import (
    CONFIG_DIR,
    MANIFEST_PATH,
    PCD_DIR,
)
from validate_angular_blind_turn_v3_gate import (
    astar,
    inflate_cells,
    path_length,
    point_to_cell,
    read_pcd,
)
from validate_static_blind_doorway_exploration import in_forward_sector
from validate_static_heading_mismatch_h3 import point_segment_distance


EXPECTED_VARIANTS = {
    "c4_deep_mirror": {
        "shc4_deep_mirror_clear", "shc4_deep_mirror_hazard"
    },
    "c5_asymmetric_offset": {
        "shc5_asymmetric_offset_clear", "shc5_asymmetric_offset_hazard"
    },
}


def validate_variant(manifest: dict, variant: dict) -> dict:
    errors = []
    variant_id = variant.get("id", "")
    rows = {item["map"]: item for item in variant.get("maps", [])}
    if set(rows) != EXPECTED_VARIANTS.get(variant_id, set()):
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
        config_text = config_path.read_text()
        required_config = (
            f'pcd_name: "seed_maps/{map_name}.pcd"',
            "sensing_rate: 10",
            "sensor_burst_dropout:",
            "  enabled: true",
            "  warmup_s: 1.0",
            "  period_s: 2.0",
            "  duration_s: 0.5",
            "  phase_s: 0.0",
        )
        missing = [line for line in required_config if line not in config_text]
        if missing:
            errors.append(f"{map_name}: invalid dropout config {missing}")
        header, points = read_pcd(pcd_path)
        if int(header.get("POINTS", -1)) != len(points):
            errors.append(f"{map_name}: PCD header/data mismatch")
        loaded[map_name] = points

    clear_name = next((name for name, item in rows.items()
                       if not item.get("include_hazard")), "")
    hazard_name = next((name for name, item in rows.items()
                        if item.get("include_hazard")), "")
    clear = Counter(loaded.get(clear_name, []))
    hazard_cloud = Counter(loaded.get(hazard_name, []))
    extra = hazard_cloud - clear
    removed = clear - hazard_cloud
    extra_points = sum(extra.values())
    expected_extra = sum(hazard_cloud.values()) - sum(clear.values())
    if removed or extra_points <= 0 or extra_points != expected_extra:
        errors.append("pair does not differ only by a positive closure wall")

    route = variant["route_check"]
    resolution = float(route["resolution_m"])
    flight_z = float(route["flight_z_m"])
    points = loaded.get(hazard_name, [])
    z_slice = [(x, y) for x, y, z in points
               if abs(z - flight_z) <= resolution / 2.0 + 1e-9]
    blocked = inflate_cells(
        {point_to_cell(point, resolution) for point in z_slice},
        int(route["inflation_step"]),
    )
    bounds = tuple(math.floor(float(value) / resolution)
                   for value in route["bounds_xy_m"])
    anchors = [tuple(map(float, point))
               for point in route["bypass_anchors_xy_m"]]
    lengths = []
    for index, (start, goal) in enumerate(zip(anchors, anchors[1:])):
        path = astar(
            point_to_cell(start, resolution),
            point_to_cell(goal, resolution),
            blocked,
            bounds,
        )
        if path is None:
            errors.append(f"inflated bypass segment {index} has NO_PATH")
        else:
            lengths.append(path_length(path, resolution))

    direct_start, direct_end = [tuple(map(float, point))
                                for point in route["direct_route_segment_xy_m"]]
    surface_distances = [
        point_segment_distance((x, y), direct_start, direct_end)
        for x, y, z in extra
        if abs(z - flight_z) <= resolution / 2.0 + 1e-9
    ]
    direct_clearance = (
        min(surface_distances) - float(manifest["body_radius_m"])
        if surface_distances else math.inf
    )
    if not math.isfinite(direct_clearance) or direct_clearance >= 0.0:
        errors.append("direct route does not body-intersect closure")

    visibility = variant["visibility_check"]
    position = tuple(map(float, visibility["position_xyz_m"][:2]))
    horizon = float(visibility["sensing_horizon_m"])
    visible = [(x, y) for x, y, _ in extra
               if math.dist(position, (x, y)) <= horizon]
    body_inside = sum(in_forward_sector(
        point, position, float(visibility["body_yaw_deg"]),
        float(visibility["sector_half_angle_deg"]), horizon
    ) for point in visible)
    velocity_inside = sum(in_forward_sector(
        point, position, float(visibility["velocity_yaw_deg"]),
        float(visibility["sector_half_angle_deg"]), horizon
    ) for point in visible)
    if len(visible) < 20:
        errors.append("raw initial closure visibility insufficient")
    if body_inside:
        errors.append("closure leaks into body-fixed initial Sector")
    if velocity_inside < 20:
        errors.append("closure absent from north-velocity Sector")

    return {
        "status": "PASS" if not errors else "FAIL",
        "maps": sorted(rows),
        "pair_extra_hazard_points": extra_points,
        "inflated_bypass_segment_lengths_m": [
            round(value, 6) for value in lengths
        ],
        "inflated_bypass_exists": len(lengths) == len(anchors) - 1,
        "direct_route_body_clearance_m": (
            round(direct_clearance, 6)
            if math.isfinite(direct_clearance) else None
        ),
        "raw_visible_hazard_samples": len(visible),
        "body_sector_visible_samples": body_inside,
        "velocity_sector_visible_samples": velocity_inside,
        "errors": errors,
    }


def validate(manifest_path: Path = MANIFEST_PATH) -> dict:
    manifest = json.loads(Path(manifest_path).read_text())
    global_errors = []
    if manifest.get("schema") != "static-burst-dropout-c4-c5-extension-v1":
        global_errors.append("unexpected manifest schema")
    dropout = manifest.get("sensor_burst_dropout", {})
    if dropout != {
        "enabled": True,
        "warmup_s": 1.0,
        "period_s": 2.0,
        "duration_s": 0.5,
        "yaml_phase_s": 0.0,
        "paired_run_phase_grid_s": [
            round(0.2 * (index % 10), 1) for index in range(20)
        ],
    }:
        global_errors.append("dropout schedule differs from preregistration")
    variants = {variant.get("id", ""): variant
                for variant in manifest.get("variants", [])}
    if set(variants) != set(EXPECTED_VARIANTS):
        global_errors.append("unexpected extension variant set")
    results = {
        variant_id: validate_variant(manifest, variants[variant_id])
        for variant_id in sorted(set(variants) & set(EXPECTED_VARIANTS))
    }
    errors = global_errors + [
        f"{variant_id}: {error}"
        for variant_id, result in results.items()
        for error in result["errors"]
    ]
    return {
        "schema": "static-burst-dropout-c4-c5-structure-gate-v1",
        "status": "PASS" if not errors else "FAIL",
        "variants": results,
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
