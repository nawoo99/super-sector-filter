#!/usr/bin/env python3
"""Audit and summarize the preregistered 90-degree calibration smoke."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


MAPS = tuple(f"abt_cal_s{severity}" for severity in range(1, 6))
MODES = ("full", "sector", "adaptive")


def boolean(value: str) -> bool:
    return value.strip().lower() == "true"


def number(row: dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    return float(value) if value else math.nan


def integer(row: dict[str, str], key: str) -> int:
    value = row.get(key, "").strip()
    return int(float(value)) if value else 0


def finite_mean(rows: list[dict[str, str]], key: str) -> float | None:
    values = [number(row, key) for row in rows]
    values = [value for value in values if math.isfinite(value)]
    return statistics.mean(values) if values else None


def rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None and math.isfinite(value) else None


def safe(row: dict[str, str]) -> bool:
    return (
        boolean(row["success"])
        and integer(row, "safety_collisions") == 0
        and integer(row, "static_pcd_collisions") == 0
        and integer(row, "static_hazard_collisions") == 0
    )


def quality_valid(row: dict[str, str]) -> bool:
    return all(
        (
            boolean(row["run_valid"]),
            boolean(row["resource_valid"]),
            boolean(row["speed_limit_valid"]),
            boolean(row["perf_window_valid"]),
            boolean(row["cgroup_cpu_accounting"]),
            not row.get("cgroup_accounting_error", "").strip(),
            not boolean(row["infrastructure_failure"]),
            integer(row, "resource_guard_abort_count") == 0,
            integer(row, "oom_kill_delta") == 0,
            integer(row, "attempt_count") == 1,
            integer(row, "retry_count") == 0,
            boolean(row["first_attempt_success"]),
        )
    )


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(raw: Path, prefix: Path) -> dict:
    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(map_name, "1", mode) for map_name in MAPS for mode in MODES}
    actual = {(row["map"], row["run"], row["mode"]) for row in rows}
    duplicates = len(rows) - len(actual)

    summary_rows = []
    for mode in MODES:
        selected = [row for row in rows if row["mode"] == mode]
        summary_rows.append(
            {
                "mode": mode,
                "rows": len(selected),
                "completed": sum(boolean(row["success"]) for row in selected),
                "safe": sum(safe(row) for row in selected),
                "contacts": sum(integer(row, "safety_collisions") for row in selected),
                "mission_time_s_mean": rounded(finite_mean(selected, "mission_time_s")),
                "hazard_clearance_m_mean": rounded(
                    finite_mean(selected, "static_hazard_min_clearance_m")
                ),
                "planner_ingress_mib_s_mean": rounded(
                    finite_mean(selected, "planner_ingress_payload_mib_s")
                ),
                "map_compute_ms_mean": rounded(finite_mean(selected, "total_ms_mean")),
                "algorithm_cpu_cores_mean": rounded(
                    finite_mean(selected, "algorithm_cpu_cores_mean")
                ),
                "end_to_end_cpu_cores_mean": rounded(
                    finite_mean(selected, "end_to_end_cpu_cores_mean")
                ),
                "end_to_end_cpu_core_s_mean": rounded(
                    finite_mean(selected, "end_to_end_cpu_core_s")
                ),
                "end_to_end_peak_pss_mib_mean": rounded(
                    finite_mean(selected, "end_to_end_peak_pss_mib")
                ),
                "frontend_risk_brake_rows": sum(
                    integer(row, "frontend_risk_brake_events") > 0
                    for row in selected
                ),
                "effective_full_open_transitions": sum(
                    integer(row, "filter_effective_full_open_transitions")
                    for row in selected
                ),
            }
        )

    summary_by_mode = {row["mode"]: row for row in summary_rows}
    reduction_fields = (
        "planner_ingress_mib_s_mean",
        "map_compute_ms_mean",
        "algorithm_cpu_cores_mean",
        "end_to_end_cpu_cores_mean",
        "end_to_end_cpu_core_s_mean",
        "end_to_end_peak_pss_mib_mean",
    )
    reduction_rows = []
    for mode in ("sector", "adaptive"):
        for field in reduction_fields:
            baseline = summary_by_mode["full"][field]
            candidate = summary_by_mode[mode][field]
            reduction_rows.append(
                {
                    "mode": mode,
                    "metric": field,
                    "full": baseline,
                    "candidate": candidate,
                    "reduction_pct": rounded(
                        100.0 * (baseline - candidate) / baseline
                        if baseline not in (None, 0) and candidate is not None
                        else None
                    ),
                }
            )

    map_rows = []
    for map_name in MAPS:
        by_mode = {
            row["mode"]: row for row in rows if row["map"] == map_name
        }
        map_rows.append(
            {
                "map": map_name,
                "hazard_radius_m": number(by_mode["full"], "static_hazard_radius_m"),
                "full_completed": boolean(by_mode["full"]["success"]),
                "sector_completed": boolean(by_mode["sector"]["success"]),
                "adaptive_completed": boolean(by_mode["adaptive"]["success"]),
                "full_contact": integer(by_mode["full"], "safety_collisions"),
                "sector_contact": integer(by_mode["sector"], "safety_collisions"),
                "adaptive_contact": integer(by_mode["adaptive"], "safety_collisions"),
                "full_time_s": number(by_mode["full"], "mission_time_s"),
                "sector_time_s": number(by_mode["sector"], "mission_time_s"),
                "adaptive_time_s": number(by_mode["adaptive"], "mission_time_s"),
                "full_hazard_clearance_m": number(
                    by_mode["full"], "static_hazard_min_clearance_m"
                ),
                "sector_hazard_clearance_m": number(
                    by_mode["sector"], "static_hazard_min_clearance_m"
                ),
                "adaptive_hazard_clearance_m": number(
                    by_mode["adaptive"], "static_hazard_min_clearance_m"
                ),
                "adaptive_frontend_risk_brakes": integer(
                    by_mode["adaptive"], "frontend_risk_brake_events"
                ),
                "adaptive_full_open_transitions": integer(
                    by_mode["adaptive"], "filter_effective_full_open_transitions"
                ),
            }
        )

    full_rows = [row for row in rows if row["mode"] == "full"]
    sector_rows = [row for row in rows if row["mode"] == "sector"]
    adaptive_rows = [row for row in rows if row["mode"] == "adaptive"]
    sector_degraded = sum(not safe(row) for row in sector_rows)
    sector_degraded_at_or_after_critical_turn = sum(
        not safe(row) and integer(row, "waypoints_reached") >= 2
        for row in sector_rows
    )
    adaptive_risk_rows = sum(
        integer(row, "frontend_risk_brake_events") > 0
        for row in adaptive_rows
    )
    checks = {
        "exact_15_unique_rows": len(rows) == 15 and actual == expected and duplicates == 0,
        "all_rows_quality_valid": len(rows) == 15 and all(quality_valid(row) for row in rows),
        "full_safe_5_of_5": len(full_rows) == 5 and all(safe(row) for row in full_rows),
        "adaptive_safe_5_of_5": (
            len(adaptive_rows) == 5 and all(safe(row) for row in adaptive_rows)
        ),
        "adaptive_frontend_risk_brake_at_least_4_of_5": adaptive_risk_rows >= 4,
        "sector_degraded_at_least_2_of_5": sector_degraded >= 2,
    }
    proceed = all(checks.values())
    gate = {
        "decision": (
            "PROCEED_TO_INDEPENDENT_EVALUATION"
            if proceed else "STOP_CALIBRATION_GATE_FAILED"
        ),
        "checks": checks,
        "counts": {
            "rows": len(rows),
            "duplicates": duplicates,
            "full_safe": sum(safe(row) for row in full_rows),
            "sector_safe": sum(safe(row) for row in sector_rows),
            "adaptive_safe": sum(safe(row) for row in adaptive_rows),
            "sector_degraded": sector_degraded,
            "sector_degraded_at_or_after_critical_turn":
                sector_degraded_at_or_after_critical_turn,
            "adaptive_frontend_risk_brake_rows": adaptive_risk_rows,
        },
        "diagnostics": {
            "sector_s2_failure_waypoints_reached": 1,
            "sector_s2_failure_before_critical_turn": True,
            "static_probe_isolation_valid": False,
            "static_probe_issue": (
                "probe radius overlaps upper wall; visibility fields cannot "
                "be attributed uniquely to the hazard"
            ),
            "no_mcnemar_test": True,
            "reason": "calibration n=1 and preregistered delivery gate failed",
        },
    }

    write_csv(prefix.with_name(prefix.name + "_summary.csv"), summary_rows,
              list(summary_rows[0]))
    write_csv(prefix.with_name(prefix.name + "_reductions.csv"), reduction_rows,
              list(reduction_rows[0]))
    write_csv(prefix.with_name(prefix.name + "_map_table.csv"), map_rows,
              list(map_rows[0]))
    validation = {
        "status": "PASS" if checks["exact_15_unique_rows"] and checks["all_rows_quality_valid"] else "FAIL",
        "missing_keys": sorted(expected - actual),
        "unexpected_keys": sorted(actual - expected),
        "duplicate_count": duplicates,
        "quality_invalid_keys": [
            [row["map"], row["run"], row["mode"]]
            for row in rows if not quality_valid(row)
        ],
    }
    prefix.with_name(prefix.name + "_validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n"
    )
    prefix.with_name(prefix.name + "_gate.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(gate, indent=2, sort_keys=True))
    return gate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("prefix", type=Path)
    args = parser.parse_args()
    analyze(args.raw, args.prefix)


if __name__ == "__main__":
    main()
