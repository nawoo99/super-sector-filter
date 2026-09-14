#!/usr/bin/env python3
"""Generate the cylinder-only Stress R1--R5 maps and one development map.

The final maps retain exactly 410 vertical cylinders and the five Normal-map
radius tiers.  Their only deliberate treatment change is spatial topology:
some background cylinders are relocated into three post chains around the
north-east loop corner.  Two horizontal chains form a wide outgoing channel
and a shorter transverse chain blocks the nominal y=24 route while preserving
a validated northern bypass.  No wall primitive, mesh, dynamic obstacle, or
sensor fault is used.

The tier-3 development map uses seed5.  The frozen final maps use the unseen
even layouts seed2/4/6/8/10 so development and final background layouts remain
separate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from pathlib import Path
from typing import Iterable, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
SUPER_ROOT = Path("/root/super_ws/src/SUPER")
PCD_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/pcd/seed_maps"
CONFIG_DIR = SUPER_ROOT / "mars_uav_sim/perfect_drone_sim/config"
MANIFEST_PATH = SCRIPT_DIR / "cylinder_only_stress_manifest.json"

FINAL_SOURCE_SEEDS = (2, 4, 6, 8, 10)
RADIUS_TIERS_M = (0.150, 0.275, 0.400, 0.525, 0.650)
DEVELOPMENT_SOURCE_SEED = 5
DEVELOPMENT_RADIUS_M = 0.400
FINAL_MAP_PREFIX = "stress_cyl_r"
DEVELOPMENT_MAP_NAME = "stress_cyl_dev_r3"

FIELD_HALF_WIDTH_M = 32.0
TARGET_CYLINDER_COUNT = 410
OBSTACLE_HEIGHT_M = 3.0
CYLINDER_SURFACE_DS_M = 0.05
Z_STEP_M = 0.10
BODY_RADIUS_M = 0.20
PLANNER_MARGIN_M = 0.20

# Existing loop24 mission and a deliberately cleared tube around it.  The
# post-chain intervention is added back inside this tube after background
# removal, so unrelated inherited bottlenecks cannot explain a gate failure.
LOOP_WAYPOINTS = (
    (0.0, 0.0),
    (24.0, 24.0),
    (-24.0, 24.0),
    (-24.0, -24.0),
    (24.0, -24.0),
    (0.0, 0.0),
)
BACKGROUND_ROUTE_CLEARANCE_M = 2.0
ORIGIN_SURFACE_CLEARANCE_M = 3.0
WAYPOINT_SURFACE_CLEARANCE_M = 2.5
BACKGROUND_SURFACE_GAP_M = 1.0

# Cylinder-post topology around the first (north-east) corner.  Chain pitch is
# diameter + 0.20 m, below the 0.40 m vehicle diameter, so adjacent posts form
# a body-impenetrable boundary without using a wall primitive.
CHAIN_SURFACE_GAP_M = 0.20
INNER_ROW_Y_M = 21.35
OUTER_ROW_Y_M = 26.65
ROW_X_MIN_M = 6.0
ROW_JUNCTION_X_M = 19.5
ROW_X_MAX_M = 26.65
CLOSURE_TARGET_TOP_Y_M = 24.35

# Counterfactual/direct-path and feasible-bypass witnesses used by the
# fail-closed validator and production replay gate.
DIRECT_PATH = ((24.0, 24.0), (17.0, 24.0))
BYPASS_PATH = (
    (24.0, 24.0),
    (23.0, 25.50),
    (20.4, 25.50),
    (18.2, 25.50),
    (17.0, 24.0),
)
REPLAY = {
    "position_xyz_m": [24.0, 23.5, 1.5],
    "body_yaw_deg": 90.0,
    "velocity_xyz_mps": [0.0, 7.0, 0.0],
    "trajectory_end_xyz_m": [17.0, 24.0, 1.5],
    "trajectory_duration_s": 1.0,
    "risk_horizon_s": 1.0,
}


class Cylinder(NamedTuple):
    x: float
    y: float
    radius: float
    role: str = "background"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
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


def route_surface_distance(cylinder: Cylinder) -> float:
    return min(
        point_segment_distance((cylinder.x, cylinder.y), start, end)
        - cylinder.radius
        for start, end in zip(LOOP_WAYPOINTS, LOOP_WAYPOINTS[1:])
    )


def load_source(seed: int, expected_radius: float) -> list[Cylinder]:
    path = SCRIPT_DIR / f"seed{seed}_static.csv"
    with path.open(newline="") as stream:
        rows = [
            Cylinder(float(row["x"]), float(row["y"]), float(row["r"]))
            for row in csv.DictReader(stream)
        ]
    if len(rows) != TARGET_CYLINDER_COUNT:
        raise ValueError(f"{path}: expected 410 cylinders, found {len(rows)}")
    if any(
        not math.isclose(item.radius, expected_radius, abs_tol=1e-12)
        for item in rows
    ):
        raise ValueError(f"{path}: radius tier mismatch")
    return rows


def chain_axis(
    fixed: float,
    start: float,
    end: float,
    radius: float,
    role: str,
    vertical: bool = False,
) -> list[Cylinder]:
    direction = 1.0 if end >= start else -1.0
    pitch = 2.0 * radius + CHAIN_SURFACE_GAP_M
    count = int(math.floor(abs(end - start) / pitch + 1e-12))
    values = [start + direction * pitch * index for index in range(count + 1)]
    if vertical:
        return [Cylinder(fixed, value, radius, role) for value in values]
    return [Cylinder(value, fixed, radius, role) for value in values]


def structural_cylinders(radius: float) -> list[Cylinder]:
    cylinders = []
    cylinders.extend(
        chain_axis(
            INNER_ROW_Y_M,
            ROW_JUNCTION_X_M,
            ROW_X_MIN_M,
            radius,
            "inner_row",
        )
    )
    cylinders.extend(
        chain_axis(
            INNER_ROW_Y_M,
            ROW_JUNCTION_X_M,
            ROW_X_MAX_M,
            radius,
            "inner_row",
        )[1:]
    )
    cylinders.extend(
        chain_axis(
            OUTER_ROW_Y_M,
            ROW_X_MIN_M,
            ROW_X_MAX_M,
            radius,
            "outer_row",
        )
    )
    cylinders.extend(
        chain_axis(
            ROW_JUNCTION_X_M,
            INNER_ROW_Y_M,
            CLOSURE_TARGET_TOP_Y_M,
            radius,
            "closure",
            vertical=True,
        )[1:]
    )
    return cylinders


def surface_gap(a: Cylinder, b: Cylinder) -> float:
    return math.hypot(a.x - b.x, a.y - b.y) - a.radius - b.radius


def conflicts(
    candidate: Cylinder,
    others: Iterable[Cylinder],
    minimum_surface_gap: float,
) -> bool:
    return any(
        surface_gap(candidate, item) < minimum_surface_gap - 1e-9
        for item in others
    )


def protected_location(candidate: Cylinder) -> bool:
    if math.hypot(candidate.x, candidate.y) - candidate.radius < (
        ORIGIN_SURFACE_CLEARANCE_M
    ):
        return True
    return any(
        math.dist((candidate.x, candidate.y), waypoint) - candidate.radius
        < WAYPOINT_SURFACE_CLEARANCE_M
        for waypoint in LOOP_WAYPOINTS[1:-1]
    )


def refill_background(
    current: list[Cylinder],
    structural: list[Cylinder],
    radius: float,
    seed: int,
    target: int,
) -> list[Cylinder]:
    rng = random.Random(0xC7110000 + seed)
    output = list(current)
    attempts = 0
    while len(output) < target:
        attempts += 1
        if attempts > 2_000_000:
            raise RuntimeError(
                f"seed{seed}: could not refill {target - len(output)} cylinders"
            )
        candidate = Cylinder(
            rng.uniform(-FIELD_HALF_WIDTH_M + radius,
                        FIELD_HALF_WIDTH_M - radius),
            rng.uniform(-FIELD_HALF_WIDTH_M + radius,
                        FIELD_HALF_WIDTH_M - radius),
            radius,
            "supplement",
        )
        if protected_location(candidate):
            continue
        if route_surface_distance(candidate) <= BACKGROUND_ROUTE_CLEARANCE_M:
            continue
        if conflicts(candidate, structural, BACKGROUND_SURFACE_GAP_M):
            continue
        if conflicts(candidate, output, BACKGROUND_SURFACE_GAP_M):
            continue
        output.append(candidate)
    return output


def build_map(seed: int, radius: float) -> tuple[list[Cylinder], dict]:
    source = load_source(seed, radius)
    structural = structural_cylinders(radius)
    retained = [
        Cylinder(item.x, item.y, item.radius, "background")
        for item in source
        if route_surface_distance(item) > BACKGROUND_ROUTE_CLEARANCE_M
        and not conflicts(item, structural, BACKGROUND_SURFACE_GAP_M)
    ]
    background_target = TARGET_CYLINDER_COUNT - len(structural)
    if background_target <= 0:
        raise ValueError("structural topology exceeds the fixed count")
    retained = retained[:background_target]
    background = refill_background(
        retained, structural, radius, seed, background_target
    )
    cylinders = background + structural
    if len(cylinders) != TARGET_CYLINDER_COUNT:
        raise AssertionError("fixed cylinder count violated")
    return cylinders, {
        "source_count": len(source),
        "retained_source_count": len(retained),
        "supplement_count": len(background) - len(retained),
        "structural_count": len(structural),
    }


def cylinder_point_count(radius: float) -> int:
    theta_count = max(
        8, int(round(2.0 * math.pi * radius / CYLINDER_SURFACE_DS_M))
    )
    z_count = max(2, int(round(OBSTACLE_HEIGHT_M / Z_STEP_M)))
    return theta_count * (z_count + 1)


def write_pcd(path: Path, cylinders: list[Cylinder]) -> int:
    point_count = sum(cylinder_point_count(item.radius) for item in cylinders)
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\n"
        "VERSION 0.7\n"
        "FIELDS x y z intensity\n"
        "SIZE 4 4 4 4\n"
        "TYPE F F F F\n"
        "COUNT 1 1 1 1\n"
        f"WIDTH {point_count}\n"
        "HEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\n"
        f"POINTS {point_count}\n"
        "DATA ascii\n"
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        stream.write(header)
        for cylinder in cylinders:
            theta_count = max(
                8,
                int(round(
                    2.0 * math.pi * cylinder.radius
                    / CYLINDER_SURFACE_DS_M
                )),
            )
            z_count = max(2, int(round(OBSTACLE_HEIGHT_M / Z_STEP_M)))
            for iz in range(z_count + 1):
                z = iz * OBSTACLE_HEIGHT_M / z_count
                for it in range(theta_count):
                    angle = 2.0 * math.pi * it / theta_count
                    x = cylinder.x + cylinder.radius * math.cos(angle)
                    y = cylinder.y + cylinder.radius * math.sin(angle)
                    stream.write(f"{x:.6f} {y:.6f} {z:.6f} 1.0\n")
    os.replace(temporary, path)
    return point_count


def write_cylinder_csv(path: Path, cylinders: list[Cylinder]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("x", "y", "r", "role"))
        for item in cylinders:
            writer.writerow((
                f"{item.x:.6f}", f"{item.y:.6f}",
                f"{item.radius:.6f}", item.role,
            ))
    os.replace(temporary, path)


def write_config(path: Path, map_name: str) -> None:
    contents = f'''#############| For UAV simulation |#################################
pcd_name: "seed_maps/{map_name}.pcd"
mesh_resource: "package://perfect_drone_sim/meshes/yunque-M.dae"
init_position:
  x: 0
  y: 0
  z: 1.5
init_yaw: 0.0

#############|For LiDAR perception simulation |###############################
is_360lidar: true
polar_resolution: 0.4
downsample_res: 0.1
vertical_fov: 178.0
sensing_blind: 0.1
sensing_horizon: 15
sensing_rate: 10
print_time_consumption: false
lidar_type: 2
depth_image_en: false
'''
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(contents)
    os.replace(temporary, path)


def emit_map(map_name: str, seed: int, radius: float, role: str) -> dict:
    cylinders, accounting = build_map(seed, radius)
    csv_path = SCRIPT_DIR / f"{map_name}_static.csv"
    pcd_path = PCD_DIR / f"{map_name}.pcd"
    config_path = CONFIG_DIR / f"{map_name}.yaml"
    write_cylinder_csv(csv_path, cylinders)
    point_count = write_pcd(pcd_path, cylinders)
    write_config(config_path, map_name)
    closure = [item for item in cylinders if item.role == "closure"]
    return {
        "map": map_name,
        "role": role,
        "source_seed": seed,
        "radius_tier": RADIUS_TIERS_M.index(radius) + 1,
        "radius_m": radius,
        "diameter_m": 2.0 * radius,
        "height_m": OBSTACLE_HEIGHT_M,
        "cylinder_count": len(cylinders),
        "closure_cylinder_count": len(closure),
        "closure_top_center_y_m": max(item.y for item in closure),
        "accounting": accounting,
        "point_count": point_count,
        "cylinder_csv": str(csv_path.relative_to(SCRIPT_DIR.parent.parent)),
        "cylinder_csv_sha256": sha256(csv_path),
        "pcd_sha256": sha256(pcd_path),
        "config_sha256": sha256(config_path),
    }


def generate() -> dict:
    PCD_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    development = emit_map(
        DEVELOPMENT_MAP_NAME,
        DEVELOPMENT_SOURCE_SEED,
        DEVELOPMENT_RADIUS_M,
        "development-only geometry gate; excluded from final flights",
    )
    final_maps = [
        emit_map(f"{FINAL_MAP_PREFIX}{tier}", seed, radius, "frozen final")
        for tier, (seed, radius) in enumerate(
            zip(FINAL_SOURCE_SEEDS, RADIUS_TIERS_M), start=1
        )
    ]
    manifest = {
        "schema": "cylinder-only-static-stress-v1",
        "role": (
            "cylinder-only topology stress supplement; does not replace or "
            "pool with wall/dropout C1--C5"
        ),
        "generator_sha256": sha256(Path(__file__)),
        "normal_results_immutable": True,
        "wall_dropout_results_immutable": True,
        "sensor_fault_enabled": False,
        "dynamic_obstacles": False,
        "wall_primitives": 0,
        "target_cylinder_count": TARGET_CYLINDER_COUNT,
        "radius_tiers_m": list(RADIUS_TIERS_M),
        "final_source_seeds": list(FINAL_SOURCE_SEEDS),
        "development_source_seed": DEVELOPMENT_SOURCE_SEED,
        "loop_waypoints_xy_m": [list(point) for point in LOOP_WAYPOINTS],
        "background_route_surface_clearance_m": (
            BACKGROUND_ROUTE_CLEARANCE_M
        ),
        "background_surface_gap_m": BACKGROUND_SURFACE_GAP_M,
        "chain_surface_gap_m": CHAIN_SURFACE_GAP_M,
        "body_radius_m": BODY_RADIUS_M,
        "planner_margin_m": PLANNER_MARGIN_M,
        "topology": {
            "inner_row_y_m": INNER_ROW_Y_M,
            "outer_row_y_m": OUTER_ROW_Y_M,
            "row_x_min_m": ROW_X_MIN_M,
            "row_junction_x_m": ROW_JUNCTION_X_M,
            "row_x_max_m": ROW_X_MAX_M,
            "closure_target_top_y_m": CLOSURE_TARGET_TOP_Y_M,
            "direct_path_xy_m": [list(point) for point in DIRECT_PATH],
            "bypass_path_xy_m": [list(point) for point in BYPASS_PATH],
        },
        "replay": REPLAY,
        "development_map": development,
        "final_maps": final_maps,
    }
    temporary = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, MANIFEST_PATH)
    return manifest


def main() -> None:
    manifest = generate()
    for item in [manifest["development_map"], *manifest["final_maps"]]:
        print(
            f"{item['map']}: seed={item['source_seed']} "
            f"r={item['radius_m']:.3f} cylinders={item['cylinder_count']} "
            f"structural={item['accounting']['structural_count']} "
            f"supplement={item['accounting']['supplement_count']} "
            f"points={item['point_count']}"
        )
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
