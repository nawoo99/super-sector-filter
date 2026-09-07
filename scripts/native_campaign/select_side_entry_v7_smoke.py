#!/usr/bin/env python3
"""Select the preregistered Map9 trajectory-intersection v7 smoke."""

import argparse
import ast
import csv
import json
import math
import os
import statistics


MAPS = ("seed7", "seed9", "seed10")
MODES = ("full", "sector", "adaptive")
RUNS = ("1", "2", "3")
DESIGN_MAP = "seed9"
CORNER = (24.0, 24.0)
GRID_PER_M = 20
CENTER_INDEX_MIN = 430  # 21.50 m
CENTER_INDEX_MAX = 480  # 24.00 m
RADIUS_CANDIDATES_M = (0.35, 0.40, 0.45, 0.50)
VEHICLE_RADIUS_M = 0.20
SOURCE_GAP_MIN_M = 0.30
INJECTION_CLEARANCE_MIN_M = 0.10
BODY_INNER_EDGE_MIN_DEG = 47.0
TRIGGER_DISTANCE_MIN_M = 0.8
TRIGGER_DISTANCE_MAX_M = 3.5
FOLLOWUP_CANDIDATE_COUNT = 6
FOLLOWUP_CENTER_SEPARATION_M = 0.20


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--manifest",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "seed9_static.csv",
        ),
    )
    return parser.parse_args()


def finite(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {row}")
    return value


def main():
    options = arguments()
    with open(options.campaign, newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {
        (map_name, run, mode)
        for map_name in MAPS for run in RUNS for mode in MODES
    }
    observed = {(r["map"], r["run"], r["mode"]) for r in rows}
    if len(rows) != 27 or observed != expected:
        raise ValueError("v6 design campaign must contain exactly 27 keys")
    for row in rows:
        if int(row["side_entry_scenario_version"]) != 6:
            raise ValueError("selector input contains a non-v6 row")
        if row["side_entry_v1_event_loaded"].lower() != "true":
            raise ValueError("selector input contains a missing v6 event")

    design_rows = [r for r in rows if r["map"] == DESIGN_MAP]
    with open(options.manifest, newline="") as stream:
        source_obstacles = list(csv.DictReader(stream))
    if not source_obstacles:
        raise ValueError("empty Map9 source manifest")

    candidates = []
    for x_index in range(CENTER_INDEX_MIN, CENTER_INDEX_MAX + 1):
        for y_index in range(CENTER_INDEX_MIN, CENTER_INDEX_MAX + 1):
            x = x_index / GRID_PER_M
            y = y_index / GRID_PER_M
            if math.hypot(x - CORNER[0], y - CORNER[1]) > 2.0:
                continue
            for radius in RADIUS_CANDIDATES_M:
                source_gap = min(
                    math.hypot(
                        x - float(obstacle["x"]),
                        y - float(obstacle["y"]),
                    ) - float(obstacle["r"]) - radius
                    for obstacle in source_obstacles
                )
                if source_gap < SOURCE_GAP_MIN_M - 1e-12:
                    continue

                injection_clearances = []
                geometry_valid = True
                for row in design_rows:
                    dx = x - finite(row, "side_entry_v1_trigger_x")
                    dy = y - finite(row, "side_entry_v1_trigger_y")
                    distance = math.hypot(dx, dy)
                    injection_clearances.append(
                        distance - radius - VEHICLE_RADIUS_M
                    )
                    if not (
                        TRIGGER_DISTANCE_MIN_M - 1e-12 <= distance <=
                        TRIGGER_DISTANCE_MAX_M + 1e-12
                    ) or distance <= radius:
                        geometry_valid = False
                        break
                    bearing = math.atan2(dy, dx)
                    body_yaw = math.radians(
                        finite(row, "side_entry_v1_trigger_body_yaw_deg")
                    )
                    relative = abs(math.atan2(
                        math.sin(bearing - body_yaw),
                        math.cos(bearing - body_yaw),
                    ))
                    angular_radius = math.asin(min(1.0, radius / distance))
                    inner_edge = math.degrees(relative - angular_radius)
                    if inner_edge < BODY_INNER_EDGE_MIN_DEG - 1e-9:
                        geometry_valid = False
                        break
                if not geometry_valid or min(injection_clearances) < (
                    INJECTION_CLEARANCE_MIN_M - 1e-12
                ):
                    continue

                proxies = {mode: [] for mode in MODES}
                for row in design_rows:
                    context = ast.literal_eval(
                        row["side_entry_v1_min_context"]
                    )
                    position = context.get("position")
                    if not isinstance(position, list) or len(position) < 2:
                        raise ValueError("invalid v6 closest context")
                    clearance = (
                        math.hypot(
                            float(position[0]) - x,
                            float(position[1]) - y,
                        ) - radius - VEHICLE_RADIUS_M
                    )
                    proxies[row["mode"]].append(clearance)
                sector_intersections = sum(
                    value < 0.0 for value in proxies["sector"]
                )
                key = (
                    -sector_intersections,
                    statistics.median(proxies["sector"]),
                    -min(injection_clearances),
                    radius,
                    x,
                    y,
                )
                candidates.append({
                    "key": key,
                    "x": x,
                    "y": y,
                    "radius_m": radius,
                    "source_gap_m": source_gap,
                    "injection_clearance_min_m": min(injection_clearances),
                    "proxy_clearance_m": proxies,
                    "sector_intersection_count": sector_intersections,
                })

    if not candidates:
        raise ValueError("no v7 smoke candidate satisfies the frozen gates")
    candidates.sort(key=lambda item: item["key"])
    selected = candidates[0]
    if selected["sector_intersection_count"] < 1:
        raise ValueError("no candidate intersects a nominal Sector trajectory")
    followup_candidates = []
    for candidate in candidates:
        if candidate["sector_intersection_count"] < 1:
            continue
        if any(
            math.hypot(
                candidate["x"] - existing["x"],
                candidate["y"] - existing["y"],
            ) < FOLLOWUP_CENTER_SEPARATION_M - 1e-12
            for existing in followup_candidates
        ):
            continue
        followup_candidates.append(candidate)
        if len(followup_candidates) == FOLLOWUP_CANDIDATE_COUNT:
            break
    if len(followup_candidates) != FOLLOWUP_CANDIDATE_COUNT:
        raise ValueError("fewer than six separated follow-up candidates")

    def compact(candidate):
        return {
            "center_x": candidate["x"],
            "center_y": candidate["y"],
            "radius_m": candidate["radius_m"],
            "source_gap_m": candidate["source_gap_m"],
            "injection_clearance_min_m": (
                candidate["injection_clearance_min_m"]
            ),
            "sector_intersection_count": (
                candidate["sector_intersection_count"]
            ),
            "proxy_clearance_m": candidate["proxy_clearance_m"],
            "selection_key": list(candidate["key"]),
        }
    result = {
        "status": "PASS",
        "campaign": options.campaign,
        "design_map": DESIGN_MAP,
        "observed_design_rows": len(design_rows),
        "eligible_candidates": len(candidates),
        "selected": compact(selected),
        "frozen_followup_candidates": [
            {"scenario": index, **compact(candidate)}
            for index, candidate in enumerate(followup_candidates, start=1)
        ],
        "frozen_constraints": {
            "center_grid_m": 1.0 / GRID_PER_M,
            "center_coordinate_range_m": [
                CENTER_INDEX_MIN / GRID_PER_M,
                CENTER_INDEX_MAX / GRID_PER_M,
            ],
            "radius_candidates_m": list(RADIUS_CANDIDATES_M),
            "source_gap_min_m": SOURCE_GAP_MIN_M,
            "injection_clearance_min_m": INJECTION_CLEARANCE_MIN_M,
            "body_inner_edge_min_deg": BODY_INNER_EDGE_MIN_DEG,
            "trigger_distance_range_m": [
                TRIGGER_DISTANCE_MIN_M,
                TRIGGER_DISTANCE_MAX_M,
            ],
            "followup_candidate_count": FOLLOWUP_CANDIDATE_COUNT,
            "followup_center_separation_m": FOLLOWUP_CENTER_SEPARATION_M,
            "objective": [
                "max_sector_nominal_intersections",
                "min_sector_median_proxy_clearance",
                "max_minimum_injection_clearance",
                "min_radius",
                "min_x",
                "min_y",
            ],
        },
        "interpretation": (
            "Exploratory feasibility selection only. Full and Adaptive "
            "nominal-path intersections are allowed because avoidance, not "
            "pre-existing path separation, is the mechanism under test."
        ),
    }
    with open(options.out, "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
