#!/usr/bin/env python3
"""Audit actual-raycast fixed-Sector liveness stations for v4."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path


EXPECTED = {
    "outgoing_x20": (20.0, 26.3, 1.2),
    "outgoing_x12": (12.0, 26.3, 1.2),
    "outgoing_x4": (4.0, 26.3, 1.2),
}


def analyze(paths: list[Path], minimum_points_per_frame: float = 50.0) -> dict:
    errors: list[str] = []
    metrics: dict[str, dict[str, float | int]] = {}
    if len(paths) != len(EXPECTED):
        errors.append(f"expected {len(EXPECTED)} station rows, got {len(paths)}")
    seen: set[str] = set()
    for path in paths:
        data = json.loads(path.read_text())
        position = tuple(float(value) for value in data.get("replay_position_xyz_m", []))
        name = next(
            (
                station
                for station, expected in EXPECTED.items()
                if len(position) == 3
                and all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(position, expected))
            ),
            None,
        )
        if name is None:
            errors.append(f"unexpected station pose in {path}")
            continue
        if name in seen:
            errors.append(f"duplicate station {name}")
            continue
        seen.add(name)
        if data.get("schema") != "frontend-replay-witness-v1":
            errors.append(f"{name}: unexpected schema")
        if data.get("mode") != "sector":
            errors.append(f"{name}: expected sector mode")
        if not math.isclose(float(data.get("replay_yaw_deg", math.nan)), 180.0, abs_tol=1e-6):
            errors.append(f"{name}: yaw contract mismatch")
        velocity = data.get("replay_velocity_xyz_mps", [])
        if velocity != [-7.0, 0.0, 0.0]:
            errors.append(f"{name}: velocity contract mismatch")
        raw_frames = int(data.get("raw", {}).get("frames", 0))
        filtered_frames = int(data.get("filtered", {}).get("frames", 0))
        filtered_points = int(data.get("filtered", {}).get("points", 0))
        points_per_frame = filtered_points / filtered_frames if filtered_frames else 0.0
        metrics[name] = {
            "raw_frames": raw_frames,
            "filtered_frames": filtered_frames,
            "filtered_points": filtered_points,
            "filtered_points_per_frame": round(points_per_frame, 6),
        }
        if raw_frames < 10 or filtered_frames != raw_frames:
            errors.append(f"{name}: missing raw/filtered frames")
        if points_per_frame < minimum_points_per_frame:
            errors.append(f"{name}: insufficient filtered points per frame")
    if seen != set(EXPECTED):
        errors.append("station set mismatch")
    return {
        "schema": "angular-blind-turn-v4-liveness-gate-v1",
        "status": "PASS" if not errors else "FAIL",
        "minimum_filtered_points_per_frame": minimum_points_per_frame,
        "stations": metrics,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stations", nargs="+", type=Path)
    parser.add_argument("--minimum-points-per-frame", type=float, default=50.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.stations, args.minimum_points_per_frame)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
