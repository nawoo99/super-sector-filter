#!/usr/bin/env python3
"""Validate a frozen side-entry profile and optional spawn events."""

import argparse
import csv
import json
import math
import os

import yaml


MAPS = (7, 9, 10)
EXPECTED = {
    "enabled": True,
    "speed_min_mps": 2.0,
    "yaw_velocity_mismatch_min_deg": 50.0,
    "hold_s": 0.02,
    "prediction_s": 0.8,
    "trigger_distance_min_m": 0.8,
    "trigger_distance_max_m": 3.5,
    "trigger_waypoint_x": 24.0,
    "trigger_waypoint_y": 24.0,
    "trigger_waypoint_radius_m": 2.0,
    "trap_waypoint_radius_m": 2.0,
    "sector_half_angle_deg": 45.0,
    "angular_margin_deg": 2.0,
    "max_nudge_deg": 20.0,
    "radius_m": 0.25,
    "height_m": 3.0,
    "point_spacing_m": 0.05,
    "z_spacing_m": 0.10,
    "sensing_horizon_m": 15.0,
    "intensity": 14545.0,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        type=int,
        choices=(1, 2, 3, 4),
        default=1,
    )
    parser.add_argument(
        "--config-dir",
        default=(
            "/root/super_ws/src/SUPER/mars_uav_sim/"
            "perfect_drone_sim/config"
        ),
    )
    parser.add_argument(
        "--manifest-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
    )
    parser.add_argument(
        "--event-json",
        action="append",
        default=[],
        help="optional runtime spawn event; may be repeated",
    )
    return parser.parse_args()


def load_profile(config_dir, map_number, version):
    path = os.path.join(
        config_dir, f"seed{map_number}_side_entry_v{version}.yaml"
    )
    with open(path) as stream:
        config = yaml.safe_load(stream)
    profile = config.get(f"side_entry_v{version}")
    if not isinstance(profile, dict):
        raise ValueError(f"missing side_entry_v{version} block: {path}")
    if config.get("pcd_name") != f"seed_maps/seed{map_number}.pcd":
        raise ValueError(f"wrong source PCD in {path}")
    expected_profile = dict(EXPECTED)
    if version == 2:
        expected_profile["prediction_s"] = 0.6
    elif version in (3, 4):
        expected_profile.update(
            {
                "hold_s": 0.015,
                "prediction_s": 0.6,
                "fixed_center_enabled": True,
                "fixed_center_x": 22.5,
                "fixed_center_y": 23.0,
                "max_nudge_deg": 0.0,
            }
        )
        if version == 4:
            expected_profile["require_velocity_inside"] = False
    for key, expected in expected_profile.items():
        actual = profile.get(key)
        if isinstance(expected, float):
            valid = isinstance(actual, (int, float)) and math.isclose(
                float(actual), expected, rel_tol=0.0, abs_tol=1e-12
            )
        else:
            valid = actual is expected
        if not valid:
            raise ValueError(
                f"{path}: {key}={actual!r}, expected {expected!r}"
            )
    return path, profile


def source_clearance(manifest_dir, map_number, profile):
    waypoint = (
        float(profile["trigger_waypoint_x"]),
        float(profile["trigger_waypoint_y"]),
    )
    path = os.path.join(manifest_dir, f"seed{map_number}_static.csv")
    with open(path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty manifest: {path}")
    source_surface_radius = min(
        math.hypot(float(row["x"]) - waypoint[0],
                   float(row["y"]) - waypoint[1])
        - float(row["r"])
        for row in rows
    )
    if profile.get("fixed_center_enabled") is True:
        synthetic_outer_radius = (
            math.hypot(
                float(profile["fixed_center_x"]) - waypoint[0],
                float(profile["fixed_center_y"]) - waypoint[1],
            )
            + float(profile["radius_m"])
        )
    else:
        synthetic_outer_radius = (
            float(profile["trap_waypoint_radius_m"])
            + float(profile["radius_m"])
        )
    guaranteed_gap = source_surface_radius - synthetic_outer_radius
    if guaranteed_gap <= 0.0:
        raise ValueError(
            f"Map{map_number}: synthetic disk overlaps the source manifest"
        )
    return {
        "map": f"Map{map_number}",
        "source_surface_radius_m": round(source_surface_radius, 6),
        "synthetic_outer_radius_m": round(synthetic_outer_radius, 6),
        "guaranteed_source_gap_m": round(guaranteed_gap, 6),
    }


def validate_event(path, version):
    with open(path) as stream:
        event = json.load(stream)
    half_angle = float(event["side_entry_v1_sector_half_angle_deg"])
    inner_edge = float(event["side_entry_v1_inner_edge_deg"])
    velocity_edge = (
        abs(float(event["side_entry_v1_velocity_relative_deg"]))
        + float(event["side_entry_v1_angular_radius_deg"])
    )
    waypoint_distance = float(
        event["side_entry_v1_trap_waypoint_distance_m"]
    )
    nudge = abs(float(event["side_entry_v1_nudge_deg"]))
    checks = {
        "scenario_version_matches": (
            int(event.get("side_entry_scenario_version", -1)) == version
        ),
        "geometry_valid": event.get("side_entry_v1_geometry_valid") is True,
        "body_inner_edge_at_least_47_deg": inner_edge >= 47.0 - 1e-6,
        "center_inside_2m_clear_disk": waypoint_distance <= 2.0 + 1e-6,
        "nudge_within_20_deg": nudge <= 20.0 + 1e-6,
    }
    if version <= 3:
        checks["velocity_outer_edge_within_45_deg"] = (
            velocity_edge <= half_angle + 1e-6
        )
    else:
        checks["velocity_requirement_disabled"] = (
            event.get("side_entry_require_velocity_inside") is False
        )
    if version in (3, 4):
        checks.update(
            {
                "fixed_center_enabled": (
                    event.get("side_entry_fixed_center_enabled") is True
                ),
                "fixed_x_matches": math.isclose(
                    float(event["side_entry_v1_trap_x"]),
                    22.5,
                    rel_tol=0.0,
                    abs_tol=1e-6,
                ),
                "fixed_y_matches": math.isclose(
                    float(event["side_entry_v1_trap_y"]),
                    23.0,
                    rel_tol=0.0,
                    abs_tol=1e-6,
                ),
                "zero_nudge": nudge <= 1e-6,
            }
        )
    if not all(checks.values()):
        raise ValueError(f"invalid event {path}: {checks}")
    return {"event_json": path, **checks}


def main():
    args = parse_args()
    loaded = [
        load_profile(args.config_dir, number, args.version)
        for number in MAPS
    ]
    reference = loaded[0][1]
    if any(profile != reference for _, profile in loaded[1:]):
        raise ValueError("side_entry_v1 blocks differ across Map7/9/10")
    result = {
        "status": "PASS",
        "maps": [
            source_clearance(args.manifest_dir, number, reference)
            for number in MAPS
        ],
        "frozen_body_inner_edge_min_deg": (
            float(reference["sector_half_angle_deg"])
            + float(reference["angular_margin_deg"])
        ),
        "scenario_version": args.version,
        "events": [
            validate_event(path, args.version) for path in args.event_json
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
