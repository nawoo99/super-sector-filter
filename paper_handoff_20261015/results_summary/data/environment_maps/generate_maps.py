#!/usr/bin/env python3
"""Render seven frozen study maps; never modify runtime or frozen inputs.

Use /usr/bin/python3 -s to avoid mixing user-site NumPy and system Matplotlib.
All output paths are checked before rendering, so reruns need a new directory.
Dashed waypoint links are ordered mission targets, not flight trajectories.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
import numpy as np
from PIL import Image


REPO = Path("/root/super-sector-filter")
SIM = Path("/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim")
FROZEN = REPO / "results/v6_frozen_20261008"
NORMAL = REPO / "results/gapfree_d1_maps_20260921_r2/manifest.json"
SCENARIOS = REPO / "results/scenario7_maps_20260924/manifest.json"
MISSIONS = REPO / "results/scenario7_missions_20260924/manifest.json"
SPECS = [
    ("gapfree_d1_m01", "Map 1", "map1"),
    ("gapfree_d1_m02", "Map 2", "map2"),
    ("gapfree_d1_m03", "Map 3", "map3"),
    ("gapfree_d1_m04", "Map 4", "map4"),
    ("gapfree_d1_m05r2", "Map 5 (R2)", "map5_r2"),
    ("urban_blocks_u01", "Urban", "urban"),
    ("forest_cluster_f01", "Forest", "forest"),
]
FORMATS = ("png", "svg", "pdf")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"Source changed: {path}: {actual} != {expected}")
    return actual


def load_maps():
    registry = {item["map"]: item for item in read_json(NORMAL)["maps"]}
    registry.update({item["map"]: item for item in read_json(SCENARIOS)["maps"]})
    missions = read_json(MISSIONS)["missions"]
    frozen_hashes = read_json(FROZEN / "source_manifest.json")["sha256"]
    with (FROZEN / "main_210.csv").open(newline="", encoding="utf-8") as stream:
        cohort = list(csv.DictReader(stream))
    expected_ids = {spec[0] for spec in SPECS}
    assert len(cohort) == 210
    assert {row["map"] for row in cohort} == expected_ids
    maps = []
    for map_id, title, stem in SPECS:
        record = registry[map_id]
        stats = record["statistics"]
        suffix = "_cylinders.csv" if map_id.startswith("gapfree") else "_geometry.json"
        geometry_file = SIM / "pcd/seed_maps" / (map_id + suffix)
        geometry_hash = require_hash(geometry_file, record["assets_sha256"][str(geometry_file)])
        require_hash(geometry_file, frozen_hashes[str(geometry_file)])
        if suffix.endswith(".csv"):
            with geometry_file.open(newline="", encoding="utf-8") as stream:
                cylinders = [
                    {"x": float(row["x"]), "y": float(row["y"]),
                     "r": float(row["r"]), "z_min": 0.0,
                     "z_max": stats["height_m"], "role": row["role"]}
                    for row in csv.DictReader(stream)
                ]
            boxes = []
        else:
            geometry = read_json(geometry_file)
            assert geometry["map"] == map_id
            cylinders, boxes = geometry["cylinders"], geometry["boxes"]
        assert len(cylinders) == stats["cylinder_count"]
        assert len(boxes) == stats.get("box_count", 0)
        assert stats["field_area_m2"] == 64 * 64
        mission = missions[map_id]
        mission_file = Path(mission["mission_file"])
        mission_hash = require_hash(mission_file, mission["mission_sha256"])
        require_hash(mission_file, frozen_hashes[str(mission_file)])
        actual_points = np.loadtxt(mission_file, ndmin=2)
        np.testing.assert_array_equal(actual_points[:, :3], mission["waypoints_xyz"])
        np.testing.assert_array_equal(actual_points[:, :2], mission["waypoints_xy"])
        altitude = mission["height_m"]
        assert all(point[2] == altitude for point in mission["waypoints_xyz"])
        # All solids span the mission altitude: XY footprint is also the
        # geometric solid cross-section at z=1.5m, not a LiDAR occupancy map.
        assert all(solid["z_min"] <= altitude <= solid["z_max"] for solid in cylinders + boxes)
        counts = {mode: sum(row["map"] == map_id and row["mode"] == mode for row in cohort)
                  for mode in ("full", "sector", "adaptive")}
        assert set(counts.values()) == {10}
        maps.append({
            "map": map_id, "title": title, "file_stem": stem,
            "cylinders": cylinders, "boxes": boxes,
            "initial_position_xyz": mission["initial_position_xyz"],
            "waypoints_xyz": mission["waypoints_xyz"], "flight_altitude_m": altitude,
            "field_bounds_xy_m": [-32, 32, -32, 32],
            "geometry_file": str(geometry_file), "geometry_sha256": geometry_hash,
            "mission_file": str(mission_file), "mission_sha256": mission_hash,
            "statistics": {key: stats[key] for key in (
                "cylinder_count", "height_m", "field_area_m2", "min_surface_gap_m",
                "nearest_surface_gap_mean_m")},
            "cohort_runs_per_mode": counts,
            "building_display_numbers": [
                {"display_number": i, "geometry_id": box["id"]}
                for i, box in enumerate(sorted(boxes, key=lambda box: (-box["cy"], box["cx"])), 1)
            ],
        })
    return maps


def legend_handles():
    return [
        Line2D([], [], marker="s", linestyle="none", markerfacecolor="#A0AAB4",
               markeredgecolor="#4C5966", markersize=8, label="Static obstacle"),
        Line2D([], [], linestyle="--", color="#176AAB", linewidth=1.6,
               label="Waypoint order (not flight trajectory)"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
               markeredgecolor="#176AAB", markersize=8, label="Numbered waypoint"),
        Line2D([], [], marker="*", linestyle="none", color="#D45B12",
               markersize=11, label="Start / final waypoint"),
    ]


def draw_map(ax, item, compact=False):
    boxes, cylinders = item["boxes"], item["cylinders"]
    solids = [Circle((c["x"], c["y"]), c["r"]) for c in cylinders]
    solids += [Rectangle((b["cx"] - b["size_x"] / 2, b["cy"] - b["size_y"] / 2),
                         b["size_x"], b["size_y"]) for b in boxes]
    ax.add_collection(PatchCollection(solids, facecolor="#A0AAB4", edgecolor="#4C5966",
                                      linewidth=0.45, zorder=2))
    for i, box in enumerate(sorted(boxes, key=lambda b: (-b["cy"], b["cx"])), 1):
        ax.text(box["cx"], box["cy"], str(i), ha="center", va="center",
                fontsize=9 if compact else 12, color="#22303D", zorder=4)
    start = np.asarray(item["initial_position_xyz"][:2])
    points = np.asarray(item["waypoints_xyz"])[:, :2]
    ordered = np.vstack([start, points])
    ax.plot(ordered[:, 0], ordered[:, 1], "--", color="#176AAB", linewidth=1.7,
            dashes=(5, 3), zorder=3)
    ax.scatter(points[:, 0], points[:, 1], s=42 if compact else 80, facecolor="white",
               edgecolor="#176AAB", linewidth=1.5, zorder=5)
    for i, (x, y) in enumerate(points, 1):
        offset = (-19, 12) if np.array_equal([x, y], start) else (7, 7)
        ax.annotate(str(i), (x, y), xytext=offset, textcoords="offset points",
                    fontsize=10 if compact else 12, weight="bold", color="#075082",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.9},
                    zorder=7)
    ax.scatter(*start, marker="*", s=110 if compact else 180, color="#D45B12",
               edgecolor="white", linewidth=0.6, zorder=6)
    if not compact:
        ax.annotate("Start", start, xytext=(9, -18), textcoords="offset points",
                    fontsize=10, color="#A24006",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.8}, zorder=7)
    if boxes:
        subtitle = f"{len(boxes)} buildings | 6 x 8 m footprint | Height 6 m"
    else:
        diameters = [2 * c["r"] for c in cylinders]
        diameter = f"{min(diameters):g}" if min(diameters) == max(diameters) else f"{min(diameters):g}-{max(diameters):g}"
        subtitle = f"{len(cylinders)} cylinders | Diameter {diameter} m | Height {item['statistics']['height_m']:g} m"
    if compact:
        ax.set_title(item["title"], fontsize=13, weight="bold", pad=7)
    else:
        ax.set_title(item["title"] + " — Top-down map\n" + subtitle,
                     fontsize=14, pad=12, linespacing=1.5)
    ax.set_xlim(-32, 32)
    ax.set_ylim(-32, 32)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30])
    ax.set_yticks([-30, -20, -10, 0, 10, 20, 30])
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_axisbelow(True)
    ax.grid(color="#DCE3E9", linewidth=0.55)
    assert ax.get_xlim() == (-32, 32) and ax.get_ylim() == (-32, 32)
    assert ax.get_aspect() == 1.0


def save_figure(fig, out, stem):
    paths = []
    for suffix in FORMATS:
        path = out / f"{stem}.{suffix}"
        fig.savefig(path, dpi=240, facecolor="white")
        paths.append(path)
    plt.close(fig)
    with Image.open(out / (stem + ".png")) as image:
        image.verify()
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    out = args.output.resolve()
    protected = (FROZEN.resolve(), SIM.resolve())
    if any(out == path or path in out.parents for path in protected):
        raise ValueError("Do not write into frozen results or runtime source directories")
    names = [f"{stem}.{suffix}" for stem in [spec[2] for spec in SPECS] + ["all_maps_overview"]
             for suffix in FORMATS] + ["map_sources.json"]
    if any((out / name).exists() for name in names):
        raise FileExistsError("Images already exist; select a fresh --output directory")
    # Check all source inputs before creating any result files.
    maps = load_maps()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    out.mkdir(parents=True, exist_ok=True)
    output_paths = []
    for item in maps:
        fig, ax = plt.subplots(figsize=(8, 8.8))
        draw_map(ax, item)
        fig.legend(handles=legend_handles(), loc="lower center", ncol=2, frameon=False,
                   fontsize=10, bbox_to_anchor=(0.5, 0.06))
        fig.text(0.5, 0.025, "World-frame XY | Field 64 x 64 m | Flight altitude 1.5 m",
                 ha="center", fontsize=9, color="#556372")
        fig.subplots_adjust(left=0.11, right=0.96, bottom=0.17, top=0.88)
        output_paths.extend(save_figure(fig, out, item["file_stem"]))
    fig, axes = plt.subplots(2, 4, figsize=(18, 10.4))
    for ax, item in zip(axes.flat, maps):
        draw_map(ax, item, compact=True)
    axes.flat[7].axis("off")
    axes.flat[7].text(0.03, 0.75,
                     "Seven-map study suite\n\nNormal: Map 1-5 (Map 5 R2)\nUrban: 16 buildings\nForest: 410 cylinders\n\n"
                     "All panels: 64 x 64 m\nFlight altitude: 1.5 m\n\nDashed links show waypoint order,\nnot actual or certified flight paths.",
                     transform=axes.flat[7].transAxes, va="top", fontsize=12, linespacing=1.5)
    fig.suptitle("Experiment maps — Actual static geometry and mission waypoints", fontsize=18, y=0.97)
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, frameon=False,
               fontsize=11, bbox_to_anchor=(0.5, 0.025))
    fig.subplots_adjust(left=0.045, right=0.98, bottom=0.1, top=0.91, wspace=0.25, hspace=0.26)
    output_paths.extend(save_figure(fig, out, "all_maps_overview"))
    manifest = {
        "schema": "seven-map-visualizations-v1", "date_kst": "2026-10-10",
        "basis": "Current frozen V6 main cohort: seven maps, three modes, ten runs per map and mode",
        "view": "Exact static solid XY footprints at mission altitude, not sensed occupancy or visibility",
        "waypoint_lines": "Nominal visitation order only; not actual or certified collision-free flight trajectories",
        "urban_building_numbers": "Display-only row-major numbering from top-left (1) to bottom-right (16)",
        "source_registries": {str(path): sha256(path) for path in (
            NORMAL, SCENARIOS, MISSIONS, FROZEN / "source_manifest.json", FROZEN / "main_210.csv")},
        "checks": {"exact_frozen_geometry_hashes": True, "exact_frozen_mission_hashes": True,
                   "waypoints_equal_mission_files": True, "obstacle_counts_equal_registries": True,
                   "all_solids_span_mission_altitude": True, "main_cohort_map_ids_and_repetitions": True,
                   "equal_axes_and_scale": True, "png_integrity": True},
        "maps": maps,
        "outputs_sha256": {path.name: sha256(path) for path in output_paths},
    }
    (out / "map_sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    print(json.dumps({"output": str(out), "maps": len(maps), "image_files": len(output_paths),
                      "checks": manifest["checks"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
