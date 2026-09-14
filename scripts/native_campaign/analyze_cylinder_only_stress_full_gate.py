#!/usr/bin/env python3
"""Fail-closed audit of the frozen cylinder-only Stress Full feasibility gate."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


MAPS = tuple(f"stress_cyl_r{tier}" for tier in range(1, 6))


def boolean(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def integer(row: dict[str, str], field: str) -> int:
    try:
        return int(float(row.get(field, "")))
    except (TypeError, ValueError):
        return -1


def number(row: dict[str, str], field: str) -> float | None:
    try:
        return float(row.get(field, ""))
    except (TypeError, ValueError):
        return None


def quality_valid(row: dict[str, str]) -> bool:
    return (
        boolean(row.get("run_valid"))
        and boolean(row.get("resource_valid"))
        and not boolean(row.get("infrastructure_failure"))
        and boolean(row.get("speed_limit_valid"))
        and integer(row, "attempt_count") == 1
        and integer(row, "retry_count") == 0
    )


def contact_free(row: dict[str, str]) -> bool:
    return (
        integer(row, "safety_collisions") == 0
        and integer(row, "static_pcd_collisions") == 0
    )


def analyze(raw: Path) -> dict:
    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(map_name, "1", "full") for map_name in MAPS}
    actual = {(row.get("map"), row.get("run"), row.get("mode")) for row in rows}
    exact_rows = len(rows) == len(expected) and actual == expected
    ordered = {row.get("map"): row for row in rows}
    all_quality = exact_rows and all(quality_valid(row) for row in rows)
    all_contact_free = exact_rows and all(contact_free(row) for row in rows)
    all_complete = exact_rows and all(boolean(row.get("success")) for row in rows)
    checks = {
        "exact_five_unique_full_rows": exact_rows,
        "all_single_attempt_no_retry": exact_rows and all(
            integer(row, "attempt_count") == 1
            and integer(row, "retry_count") == 0
            for row in rows
        ),
        "all_rows_quality_valid": all_quality,
        "all_rows_contact_free": all_contact_free,
        "all_rows_complete": all_complete,
    }
    per_map = []
    for map_name in MAPS:
        row = ordered.get(map_name, {})
        per_map.append(
            {
                "map": map_name,
                "complete": boolean(row.get("success")),
                "mission_time_s": number(row, "mission_time_s"),
                "waypoints_reached": integer(row, "waypoints_reached"),
                "static_pcd_collisions": integer(row, "static_pcd_collisions"),
                "static_pcd_clearance_m": number(row, "static_pcd_clearance_m"),
                "path_length_m": number(row, "path_length_m"),
                "final_xy_m": [number(row, "final_x"), number(row, "final_y")],
                "trajectory_audit_min_clearance_m": number(
                    row, "trajectory_audit_min_clearance_m"
                ),
                "quality_valid": quality_valid(row) if row else False,
                "attempt_count": integer(row, "attempt_count"),
                "retry_count": integer(row, "retry_count"),
                "algorithm_cpu_cores_mean": number(
                    row, "algorithm_cpu_cores_mean"
                ),
                "system_min_available_mib": number(
                    row, "system_min_available_mib"
                ),
                "system_peak_swap_used_mib": number(
                    row, "system_peak_swap_used_mib"
                ),
                "memory_psi_some_avg10_max": number(
                    row, "memory_psi_some_avg10_max"
                ),
            }
        )
    passed = all(checks.values())
    return {
        "schema": "cylinder-only-static-stress-full-gate-v1",
        "decision": (
            "PROCEED_TO_PAIRED_THREE_MODE_PILOT"
            if passed
            else "STOP_PAIRED_CAMPAIGN_FULL_FEASIBILITY_GATE_FAILED"
        ),
        "checks": checks,
        "counts": {
            "rows": len(rows),
            "complete": sum(boolean(row.get("success")) for row in rows),
            "contact_free": sum(contact_free(row) for row in rows),
            "quality_valid": sum(quality_valid(row) for row in rows),
        },
        "per_map": per_map,
        "diagnostics": {
            "confirmatory_sector_adaptive_allowed": passed,
            "no_retry_or_replacement_rows": True,
            "inferential_test": None,
            "scope": "five-map n=1 feasibility gate, not population evidence",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.raw)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    if not all(result["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
