#!/usr/bin/env python3
"""Apply the preregistered v5-design to v6-centre selection rule."""

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
OLD_CENTER = (22.5, 23.0)
CORNER = (24.0, 24.0)
GRID_PER_M = 20
MAX_SHIFT_M = 0.40
CYLINDER_RADIUS_M = 0.25
VEHICLE_RADIUS_M = 0.20
REFERENCE_CLEARANCE_MIN_M = 0.10
SOURCE_GAP_MIN_M = 0.30
BODY_INNER_EDGE_MIN_DEG = 49.0
TRIGGER_DISTANCE_MIN_M = 0.8
TRIGGER_DISTANCE_MAX_M = 3.5


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--manifest-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
    )
    return parser.parse_args()


def source_surface_radius(path):
    with open(path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty source manifest: {path}")
    return min(
        math.hypot(float(row["x"]) - CORNER[0],
                   float(row["y"]) - CORNER[1])
        - float(row["r"])
        for row in rows
    )


def finite(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {row}")
    return value


def main():
    args = arguments()
    with open(args.campaign, newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(m, r, mode) for m in MAPS for r in RUNS for mode in MODES}
    observed = {(row["map"], row["run"], row["mode"]) for row in rows}
    if len(rows) != 27 or observed != expected:
        raise ValueError(
            f"campaign scope mismatch: rows={len(rows)}, "
            f"missing={sorted(expected - observed)}, "
            f"unexpected={sorted(observed - expected)}"
        )
    for row in rows:
        if row["side_entry_v1_event_loaded"].lower() != "true":
            raise ValueError(f"missing event: {row['map']}/{row['run']}/{row['mode']}")
        if row["side_entry_v1_geometry_valid"].lower() != "true":
            raise ValueError(f"invalid event: {row['map']}/{row['run']}/{row['mode']}")
        if int(row["side_entry_scenario_version"]) != 5:
            raise ValueError(f"not a v5 row: {row['map']}/{row['run']}/{row['mode']}")
        if int(row["side_entry_qualifying_samples_required"]) != 3:
            raise ValueError("v5 row does not require three samples")
        if int(row["side_entry_qualifying_samples_observed"]) < 3:
            raise ValueError("v5 row did not observe three samples")

    contexts = []
    for row in rows:
        context = ast.literal_eval(row["side_entry_v1_min_context"])
        position = context.get("position")
        if not isinstance(position, list) or len(position) < 2:
            raise ValueError(f"invalid closest context: {context!r}")
        contexts.append((row, float(position[0]), float(position[1])))

    source_radii = {
        map_name: source_surface_radius(
            os.path.join(args.manifest_dir, f"{map_name}_static.csv")
        )
        for map_name in MAPS
    }
    candidates = []
    x_first = round((OLD_CENTER[0] - MAX_SHIFT_M) * GRID_PER_M)
    x_last = round((OLD_CENTER[0] + MAX_SHIFT_M) * GRID_PER_M)
    y_first = round((OLD_CENTER[1] - MAX_SHIFT_M) * GRID_PER_M)
    y_last = round((OLD_CENTER[1] + MAX_SHIFT_M) * GRID_PER_M)
    for x_index in range(x_first, x_last + 1):
        for y_index in range(y_first, y_last + 1):
            x = x_index / GRID_PER_M
            y = y_index / GRID_PER_M
            if math.hypot(x - OLD_CENTER[0], y - OLD_CENTER[1]) > MAX_SHIFT_M + 1e-12:
                continue
            corner_distance = math.hypot(x - CORNER[0], y - CORNER[1])
            if corner_distance > 2.0 + 1e-12:
                continue
            gaps = {
                map_name: radius - (corner_distance + CYLINDER_RADIUS_M)
                for map_name, radius in source_radii.items()
            }
            if min(gaps.values()) < SOURCE_GAP_MIN_M - 1e-12:
                continue

            geometry_ok = True
            for row in rows:
                dx = x - finite(row, "side_entry_v1_trigger_x")
                dy = y - finite(row, "side_entry_v1_trigger_y")
                distance = math.hypot(dx, dy)
                if not (TRIGGER_DISTANCE_MIN_M - 1e-12 <= distance <=
                        TRIGGER_DISTANCE_MAX_M + 1e-12):
                    geometry_ok = False
                    break
                angular_radius = math.asin(min(1.0, CYLINDER_RADIUS_M / distance))
                body_yaw = math.radians(
                    finite(row, "side_entry_v1_trigger_body_yaw_deg")
                )
                bearing = math.atan2(dy, dx)
                relative = math.atan2(
                    math.sin(bearing - body_yaw),
                    math.cos(bearing - body_yaw),
                )
                inner_edge = math.degrees(abs(relative) - angular_radius)
                if inner_edge < BODY_INNER_EDGE_MIN_DEG - 1e-9:
                    geometry_ok = False
                    break
            if not geometry_ok:
                continue

            proxy = {mode: [] for mode in MODES}
            for row, closest_x, closest_y in contexts:
                proxy[row["mode"]].append(
                    math.hypot(closest_x - x, closest_y - y)
                    - CYLINDER_RADIUS_M - VEHICLE_RADIUS_M
                )
            if min(proxy["full"] + proxy["adaptive"]) < \
                    REFERENCE_CLEARANCE_MIN_M - 1e-12:
                continue
            key = (
                statistics.median(proxy["sector"]),
                -min(proxy["adaptive"]),
                -min(proxy["full"]),
                x,
                y,
            )
            candidates.append((key, x, y, proxy, gaps))

    if not candidates:
        raise ValueError("no candidate satisfies the frozen constraints")
    candidates.sort(key=lambda item: item[0])
    key, x, y, proxy, gaps = candidates[0]
    result = {
        "status": "PASS",
        "campaign": args.campaign,
        "observed_rows": len(rows),
        "eligible_candidates": len(candidates),
        "selected_center": {"x": x, "y": y},
        "selection_key": list(key),
        "guaranteed_source_gap_m": gaps,
        "proxy_clearance_m": {
            mode: {
                "min": min(values),
                "median": statistics.median(values),
                "mean": statistics.mean(values),
                "max": max(values),
            }
            for mode, values in proxy.items()
        },
        "frozen_constraints": {
            "grid_m": 1.0 / GRID_PER_M,
            "max_shift_m": MAX_SHIFT_M,
            "reference_clearance_min_m": REFERENCE_CLEARANCE_MIN_M,
            "source_gap_min_m": SOURCE_GAP_MIN_M,
            "body_inner_edge_min_deg": BODY_INNER_EDGE_MIN_DEG,
            "qualifying_samples": 3,
        },
    }
    with open(args.out, "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
