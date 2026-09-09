#!/usr/bin/env python3
"""Fail-closed gate for the deterministic MARSIM/front-end witness pair."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any


SCHEMA = "frontend-replay-witness-v1"
FROZEN_FIELDS = (
    "replay_position_xyz_m",
    "replay_yaw_deg",
    "replay_velocity_xyz_mps",
    "trajectory_end_xyz_m",
    "trajectory_duration_s",
    "risk_horizon_s",
    "trajectory_generation",
    "conflict_clearance_m",
    "hazard_xy_radius_m",
)


class InvalidWitness(ValueError):
    """Raised when an input is structurally incomplete or non-finite."""


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidWitness(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise InvalidWitness(f"{label} must be finite")
    return number


def _nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidWitness(f"{label} must be a non-negative integer")
    return value


def _load(path: Path, expected_mode: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidWitness(f"cannot load {path}: {error}") from error
    if not isinstance(payload, dict):
        raise InvalidWitness(f"{path}: root must be an object")
    if payload.get("schema") != SCHEMA:
        raise InvalidWitness(f"{path}: unexpected schema")
    if payload.get("mode") != expected_mode:
        raise InvalidWitness(
            f"{path}: expected mode {expected_mode!r}, got {payload.get('mode')!r}"
        )
    for field in FROZEN_FIELDS:
        if field not in payload:
            raise InvalidWitness(f"{path}: missing {field}")
    for cloud_name in ("raw", "filtered"):
        cloud = payload.get(cloud_name)
        if not isinstance(cloud, dict):
            raise InvalidWitness(f"{path}: missing {cloud_name} object")
        for field in (
            "frames",
            "points",
            "hazard_frames",
            "hazard_points",
            "conflict_frames",
            "conflict_points",
            "max_conflict_points_per_frame",
        ):
            _nonnegative_integer(cloud.get(field), f"{path}:{cloud_name}.{field}")
    for field in (
        "verdict_messages",
        "future_verdict_messages",
        "occupied_verdicts",
        "fresh_occupied_verdicts",
        "max_consecutive_fresh_occupied",
        "last_verdict_generation",
        "last_verdict_status",
    ):
        value = payload.get(field)
        if field == "last_verdict_status" and value == -1:
            continue
        _nonnegative_integer(value, f"{path}:{field}")
    return payload


def _same_value(left: Any, right: Any, *, tolerance: float = 1e-9) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_value(a, b, tolerance=tolerance) for a, b in zip(left, right)
        )
    if isinstance(left, (int, float)) and not isinstance(left, bool):
        if not isinstance(right, (int, float)) or isinstance(right, bool):
            return False
        return math.isclose(float(left), float(right), abs_tol=tolerance, rel_tol=0.0)
    return left == right


def analyze(sector: dict[str, Any], adaptive: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["identical_replay_contract"] = all(
        _same_value(sector[field], adaptive[field]) for field in FROZEN_FIELDS
    )
    checks["sector_raw_hazard_visible"] = (
        sector["raw"]["hazard_frames"] >= 2
        and sector["raw"]["hazard_points"] > 0
    )
    checks["sector_raw_evaluated_path_conflict"] = (
        sector["raw"]["conflict_frames"] >= 2
        and sector["raw"]["conflict_points"] > 0
    )
    checks["sector_filter_output_observed"] = sector["filtered"]["frames"] >= 2
    checks["sector_removes_hazard"] = sector["filtered"]["hazard_points"] == 0
    checks["sector_removes_evaluated_path_conflict"] = (
        sector["filtered"]["conflict_points"] == 0
    )
    checks["adaptive_raw_hazard_visible"] = (
        adaptive["raw"]["hazard_frames"] >= 2
        and adaptive["raw"]["hazard_points"] > 0
    )
    checks["adaptive_raw_evaluated_path_conflict"] = (
        adaptive["raw"]["conflict_frames"] >= 2
        and adaptive["raw"]["conflict_points"] > 0
    )
    checks["adaptive_future_verdict_stream"] = (
        adaptive["future_verdict_messages"] >= 2
    )
    checks["adaptive_two_consecutive_fresh_occupied"] = (
        adaptive["fresh_occupied_verdicts"] >= 2
        and adaptive["max_consecutive_fresh_occupied"] >= 2
    )
    checks["adaptive_last_verdict_generation_matches"] = (
        adaptive["last_verdict_generation"] == adaptive["trajectory_generation"]
    )
    checks["adaptive_last_verdict_occupied"] = adaptive["last_verdict_status"] == 6
    age = adaptive.get("last_verdict_source_cloud_age_s")
    checks["adaptive_last_source_fresh"] = (
        isinstance(age, (int, float))
        and not isinstance(age, bool)
        and math.isfinite(float(age))
        and 0.0 <= float(age) <= 0.75
    )
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "frontend-replay-witness-gate-v1",
        "decision": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failure_reasons": failed,
        "metrics": {
            "sector_raw_hazard_frames": sector["raw"]["hazard_frames"],
            "sector_raw_conflict_frames": sector["raw"]["conflict_frames"],
            "sector_filtered_hazard_points": sector["filtered"]["hazard_points"],
            "sector_filtered_conflict_points": sector["filtered"]["conflict_points"],
            "adaptive_raw_hazard_frames": adaptive["raw"]["hazard_frames"],
            "adaptive_raw_conflict_frames": adaptive["raw"]["conflict_frames"],
            "adaptive_future_verdict_messages": adaptive[
                "future_verdict_messages"
            ],
            "adaptive_fresh_occupied_verdicts": adaptive[
                "fresh_occupied_verdicts"
            ],
            "adaptive_max_consecutive_fresh_occupied": adaptive[
                "max_consecutive_fresh_occupied"
            ],
            "adaptive_last_minimum_distance_m": adaptive.get(
                "last_verdict_minimum_distance_m"
            ),
        },
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sector", type=Path, required=True)
    parser.add_argument("--adaptive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        sector = _load(arguments.sector, "sector")
        adaptive = _load(arguments.adaptive, "adaptive")
        result = analyze(sector, adaptive)
    except InvalidWitness as error:
        result = {
            "schema": "frontend-replay-witness-gate-v1",
            "decision": "INVALID",
            "checks": {},
            "failure_reasons": [str(error)],
            "metrics": {},
        }
        _atomic_write(arguments.out, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    _atomic_write(arguments.out, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
