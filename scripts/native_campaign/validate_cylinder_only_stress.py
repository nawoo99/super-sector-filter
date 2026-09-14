#!/usr/bin/env python3
"""Fail-closed structural and analytic audit for cylinder-only Stress maps."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "cylinder_only_stress_manifest.json"
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
STRUCTURAL_ROLES = {"inner_row", "outer_row", "closure"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pcd_header(path: Path) -> dict[str, str]:
    header = {}
    with path.open() as stream:
        for line in stream:
            key, _, value = line.strip().partition(" ")
            header[key] = value
            if key == "DATA":
                break
    return header


def point_segment_distance(point, start, end) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0:
        return math.dist(point, start)
    fraction = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / length_sq
    fraction = min(1.0, max(0.0, fraction))
    closest = (start[0] + fraction * dx, start[1] + fraction * dy)
    return math.dist(point, closest)


def path_body_clearance(path, cylinders, body_radius: float) -> float:
    return min(
        point_segment_distance((item["x"], item["y"]), start, end)
        - item["r"] - body_radius
        for start, end in zip(path, path[1:])
        for item in cylinders
    )


def angular_delta_deg(value: float) -> float:
    return abs(math.degrees(math.atan2(math.sin(value), math.cos(value))))


def load_cylinders(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return [
            {
                "x": float(row["x"]),
                "y": float(row["y"]),
                "r": float(row["r"]),
                "role": row["role"],
            }
            for row in csv.DictReader(stream)
        ]


def validate() -> dict:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("schema") != "cylinder-only-static-stress-v1":
        errors.append("unexpected manifest schema")
    if manifest.get("wall_primitives") != 0:
        errors.append("wall primitive count is not zero")
    if manifest.get("sensor_fault_enabled") is not False:
        errors.append("sensor fault must remain disabled")
    if manifest.get("dynamic_obstacles") is not False:
        errors.append("dynamic obstacles must remain disabled")
    if not manifest.get("normal_results_immutable"):
        errors.append("Normal result preservation flag missing")
    if not manifest.get("wall_dropout_results_immutable"):
        errors.append("wall/dropout result preservation flag missing")

    maps = [manifest["development_map"], *manifest.get("final_maps", [])]
    if len(manifest.get("final_maps", [])) != 5:
        errors.append("expected five final maps")
    body_radius = float(manifest["body_radius_m"])
    planner_margin = float(manifest["planner_margin_m"])
    direct_path = manifest["topology"]["direct_path_xy_m"]
    bypass_path = manifest["topology"]["bypass_path_xy_m"]
    replay = manifest["replay"]
    replay_xy = replay["position_xyz_m"][:2]
    replay_yaw = math.radians(float(replay["body_yaw_deg"]))
    replay_end = replay["trajectory_end_xyz_m"][:2]
    sensing_horizon = 15.0

    audit_maps = []
    for item in maps:
        map_name = item["map"]
        csv_path = SCRIPT_DIR / f"{map_name}_static.csv"
        pcd_path = PCD_DIR / f"{map_name}.pcd"
        config_path = CONFIG_DIR / f"{map_name}.yaml"
        for path in (csv_path, pcd_path, config_path):
            if not path.is_file():
                errors.append(f"missing asset: {path}")
        if errors and not all(
            path.is_file() for path in (csv_path, pcd_path, config_path)
        ):
            continue
        cylinders = load_cylinders(csv_path)
        radius = float(item["radius_m"])
        if len(cylinders) != int(manifest["target_cylinder_count"]):
            errors.append(f"{map_name}: cylinder count is not 410")
        if any(not math.isclose(c["r"], radius, abs_tol=1e-9)
               for c in cylinders):
            errors.append(f"{map_name}: mixed or incorrect cylinder radius")
        if any(c["role"] not in STRUCTURAL_ROLES | {"background", "supplement"}
               for c in cylinders):
            errors.append(f"{map_name}: unknown cylinder role")
        if sum(c["role"] == "closure" for c in cylinders) != int(
            item["closure_cylinder_count"]
        ):
            errors.append(f"{map_name}: closure count mismatch")

        minimum_all_gap = math.inf
        minimum_background_gap = math.inf
        for index, first in enumerate(cylinders):
            for second in cylinders[index + 1:]:
                gap = (
                    math.hypot(first["x"] - second["x"],
                               first["y"] - second["y"])
                    - first["r"] - second["r"]
                )
                minimum_all_gap = min(minimum_all_gap, gap)
                if not (
                    first["role"] in STRUCTURAL_ROLES
                    and second["role"] in STRUCTURAL_ROLES
                ):
                    minimum_background_gap = min(minimum_background_gap, gap)
        if minimum_all_gap < -1e-6:
            errors.append(f"{map_name}: cylinders overlap")
        expected_chain_gap = float(manifest["chain_surface_gap_m"])
        if minimum_all_gap > expected_chain_gap + 1e-6:
            errors.append(f"{map_name}: post chain is not body-impenetrable")
        expected_background_gap = float(manifest["background_surface_gap_m"])
        if minimum_background_gap < expected_background_gap - 1e-6:
            errors.append(f"{map_name}: background gap below 1.0 m")

        direct_clearance = path_body_clearance(
            direct_path, cylinders, body_radius
        )
        bypass_clearance = path_body_clearance(
            bypass_path, cylinders, body_radius
        )
        if direct_clearance >= 0.0:
            errors.append(f"{map_name}: direct path does not body-intersect")
        if bypass_clearance < planner_margin - 1e-6:
            errors.append(
                f"{map_name}: bypass below body+planner margin: "
                f"{bypass_clearance:.6f}"
            )

        conflict_closure = [
            cylinder for cylinder in cylinders
            if cylinder["role"] == "closure"
            and point_segment_distance(
                (cylinder["x"], cylinder["y"]), replay_xy, replay_end
            ) <= cylinder["r"] + body_radius + planner_margin
        ]
        if not conflict_closure:
            errors.append(f"{map_name}: replay trajectory misses closure")
        minimum_sector_edge = math.inf
        raw_visible_conflicts = 0
        for cylinder in conflict_closure:
            dx = cylinder["x"] - replay_xy[0]
            dy = cylinder["y"] - replay_xy[1]
            distance = math.hypot(dx, dy)
            if distance <= sensing_horizon + cylinder["r"]:
                raw_visible_conflicts += 1
            bearing = math.atan2(dy, dx)
            centre_delta = angular_delta_deg(bearing - replay_yaw)
            angular_radius = math.degrees(math.asin(min(1.0, cylinder["r"] / distance)))
            minimum_sector_edge = min(
                minimum_sector_edge, centre_delta - angular_radius
            )
        if raw_visible_conflicts == 0:
            errors.append(f"{map_name}: raw replay cannot see closure")
        if minimum_sector_edge <= 45.0:
            errors.append(
                f"{map_name}: conflict leaks into fixed 45-degree Sector: "
                f"{minimum_sector_edge:.6f}"
            )

        if sha256(csv_path) != item["cylinder_csv_sha256"]:
            errors.append(f"{map_name}: cylinder CSV hash mismatch")
        if sha256(pcd_path) != item["pcd_sha256"]:
            errors.append(f"{map_name}: PCD hash mismatch")
        if sha256(config_path) != item["config_sha256"]:
            errors.append(f"{map_name}: config hash mismatch")
        header = pcd_header(pcd_path)
        if header.get("DATA") != "ascii":
            errors.append(f"{map_name}: PCD is not ASCII")
        if int(header.get("POINTS", -1)) != int(item["point_count"]):
            errors.append(f"{map_name}: PCD point count mismatch")
        if f'pcd_name: "seed_maps/{map_name}.pcd"' not in config_path.read_text():
            errors.append(f"{map_name}: config PCD reference mismatch")

        audit_maps.append({
            "map": map_name,
            "source_seed": item["source_seed"],
            "radius_m": radius,
            "cylinder_count": len(cylinders),
            "structural_count": item["accounting"]["structural_count"],
            "minimum_all_surface_gap_m": round(minimum_all_gap, 6),
            "minimum_background_surface_gap_m": round(
                minimum_background_gap, 6
            ),
            "direct_path_body_clearance_m": round(direct_clearance, 6),
            "bypass_body_clearance_m": round(bypass_clearance, 6),
            "replay_conflicting_closure_cylinders": len(conflict_closure),
            "minimum_conflict_sector_edge_deg": round(
                minimum_sector_edge, 6
            ),
            "raw_visible_conflict_cylinders": raw_visible_conflicts,
        })

    return {
        "schema": "cylinder-only-static-stress-structure-gate-v1",
        "decision": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checks": {
            "five_final_maps": len(manifest.get("final_maps", [])) == 5,
            "only_cylinders": manifest.get("wall_primitives") == 0,
            "no_sensor_fault": manifest.get("sensor_fault_enabled") is False,
            "no_dynamic_obstacles": manifest.get("dynamic_obstacles") is False,
            "fixed_count": all(
                row["cylinder_count"] == 410 for row in audit_maps
            ),
            "direct_path_blocked": all(
                row["direct_path_body_clearance_m"] < 0
                for row in audit_maps
            ),
            "bypass_body_and_margin_feasible": all(
                row["bypass_body_clearance_m"] >= planner_margin - 1e-6
                for row in audit_maps
            ),
            "fixed_sector_excludes_conflict": all(
                row["minimum_conflict_sector_edge_deg"] > 45.0
                for row in audit_maps
            ),
        },
        "maps": audit_maps,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered)
    print(rendered, end="")
    raise SystemExit(0 if result["decision"] == "PASS" else 1)


if __name__ == "__main__":
    main()
