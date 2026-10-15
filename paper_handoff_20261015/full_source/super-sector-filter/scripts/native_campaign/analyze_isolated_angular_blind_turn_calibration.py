#!/usr/bin/env python3
"""Audit the preregistered ``abt2_cal_t1..t5`` 15-row gate."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
from pathlib import Path

import analyze_angular_blind_turn_calibration as base


MAPS = tuple(f"abt2_cal_t{tier}" for tier in range(1, 6))
MODES = ("full", "sector", "adaptive")


def analyze(raw: Path, prefix: Path) -> dict:
    # Reuse the frozen tabular reduction implementation, then replace only
    # the v1-specific decision block with this family's preregistered gate.
    base.MAPS = MAPS
    with contextlib.redirect_stdout(io.StringIO()):
        base.analyze(raw, prefix)

    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(map_name, "1", mode) for map_name in MAPS for mode in MODES}
    actual = {(row["map"], row["run"], row["mode"]) for row in rows}
    full_rows = [row for row in rows if row["mode"] == "full"]
    sector_rows = [row for row in rows if row["mode"] == "sector"]
    adaptive_rows = [row for row in rows if row["mode"] == "adaptive"]
    filtered_rows = [row for row in rows if row["mode"] != "full"]

    def degraded_after_target(row: dict[str, str]) -> bool:
        return not base.safe(row) and base.integer(row, "waypoints_reached") >= 1

    def exact_fresh_risk_brake(row: dict[str, str]) -> bool:
        brakes = base.integer(row, "frontend_risk_brake_events")
        enforced = base.integer(row, "frontend_risk_enforced")
        # A planner-side brake is counted only after the frontend verdict has
        # passed generation, source-age and time-coverage checks.  Requiring
        # a corresponding enforced verdict makes that provenance explicit.
        return brakes > 0 and enforced >= brakes

    sector_degraded_after = sum(degraded_after_target(row) for row in sector_rows)
    adaptive_risk_rows = sum(exact_fresh_risk_brake(row) for row in adaptive_rows)
    probe_seen_rows = sum(
        base.boolean(row.get("filter_static_probe_input_seen", ""))
        for row in filtered_rows
    )
    probe_outside_rows = sum(
        base.boolean(row.get("filter_static_probe_input_seen", ""))
        and not base.boolean(row.get("filter_static_probe_first_center_in_sector", ""))
        for row in filtered_rows
    )
    checks = {
        "exact_15_unique_rows": (
            len(rows) == 15 and actual == expected and len(actual) == len(rows)
        ),
        "all_rows_quality_valid": (
            len(rows) == 15 and all(base.quality_valid(row) for row in rows)
        ),
        "full_safe_5_of_5": len(full_rows) == 5 and all(base.safe(row) for row in full_rows),
        "adaptive_safe_5_of_5": (
            len(adaptive_rows) == 5 and all(base.safe(row) for row in adaptive_rows)
        ),
        "adaptive_exact_fresh_frontend_risk_brake_at_least_4_of_5": (
            adaptive_risk_rows >= 4
        ),
        "sector_degraded_at_or_after_target_at_least_2_of_5": (
            sector_degraded_after >= 2
        ),
        "isolated_surface_probe_seen_and_outside_sector_10_of_10": (
            len(filtered_rows) == 10
            and probe_seen_rows == 10
            and probe_outside_rows == 10
        ),
    }
    gate = {
        "decision": (
            "PROCEED_TO_INDEPENDENT_EVALUATION"
            if all(checks.values()) else "STOP_CALIBRATION_GATE_FAILED"
        ),
        "checks": checks,
        "counts": {
            "rows": len(rows),
            "duplicates": len(rows) - len(actual),
            "full_safe": sum(base.safe(row) for row in full_rows),
            "sector_safe": sum(base.safe(row) for row in sector_rows),
            "adaptive_safe": sum(base.safe(row) for row in adaptive_rows),
            "sector_degraded_at_or_after_target": sector_degraded_after,
            "adaptive_exact_fresh_frontend_risk_brake_rows": adaptive_risk_rows,
            "isolated_surface_probe_seen_rows": probe_seen_rows,
            "isolated_surface_probe_outside_sector_rows": probe_outside_rows,
        },
        "diagnostics": {
            "critical_waypoints_reached_threshold": 1,
            "static_probe_isolation_valid_by_construction": True,
            "no_mcnemar_test": True,
            "reason": "calibration n=1 is a mechanism gate, not inferential evidence",
        },
    }
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
