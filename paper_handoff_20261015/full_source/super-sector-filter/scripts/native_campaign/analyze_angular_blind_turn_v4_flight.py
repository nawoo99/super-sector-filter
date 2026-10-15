#!/usr/bin/env python3
"""Fail-closed audit for v4 Full smoke and three-mode n=3 pilot."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import analyze_angular_blind_turn_calibration as base


MAP = "abt4_observed_exit"
MODES = ("full", "sector", "adaptive")


def exact_fresh_risk_brake(row: dict[str, str]) -> bool:
    brakes = base.integer(row, "frontend_risk_brake_events")
    enforced = base.integer(row, "frontend_risk_enforced")
    return brakes > 0 and enforced >= brakes


def analyze(raw: Path, phase: str) -> dict:
    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if phase == "full":
        expected = {(MAP, "1", "full")}
    else:
        expected = {
            (MAP, str(run), mode)
            for run in range(1, 4)
            for mode in MODES
        }
    actual = {(row.get("map"), row.get("run"), row.get("mode")) for row in rows}
    exact_rows = len(rows) == len(expected) and actual == expected and len(actual) == len(rows)
    checks: dict[str, bool] = {
        "exact_unique_first_attempt_rows": exact_rows,
        "all_rows_quality_valid": exact_rows and all(base.quality_valid(row) for row in rows),
    }
    counts: dict[str, int] = {
        "rows": len(rows),
        "duplicates": len(rows) - len(actual),
    }
    if phase == "full":
        full = rows[0] if exact_rows else None
        checks["full_contact_free_completion"] = full is not None and base.safe(full)
        counts["full_safe"] = int(full is not None and base.safe(full))
        pass_decision = "PROCEED_TO_THREE_MODE_N3"
        fail_decision = "STOP_V4_FULL_FEASIBILITY_GATE_FAILED"
    else:
        selected = {
            mode: [row for row in rows if row.get("mode") == mode]
            for mode in MODES
        }
        full_safe = sum(base.safe(row) for row in selected["full"])
        adaptive_safe = sum(base.safe(row) for row in selected["adaptive"])
        sector_degraded = sum(
            not base.safe(row) and base.integer(row, "waypoints_reached") >= 1
            for row in selected["sector"]
        )
        sector_map_stale = sum(
            base.integer(row, "guard_main_pre_map_stale") > 0
            for row in selected["sector"]
        )
        adaptive_risk = sum(
            exact_fresh_risk_brake(row) for row in selected["adaptive"]
        )
        filtered = selected["sector"] + selected["adaptive"]
        probe_seen = sum(
            base.boolean(row.get("filter_static_probe_input_seen", ""))
            for row in filtered
        )
        sector_probe_outside = sum(
            base.boolean(row.get("filter_static_probe_input_seen", ""))
            and not base.boolean(row.get("filter_static_probe_first_center_in_sector", ""))
            for row in selected["sector"]
        )
        checks.update(
            {
                "full_contact_free_completion_3_of_3": full_safe == 3,
                "adaptive_contact_free_completion_3_of_3": adaptive_safe == 3,
                "sector_degraded_after_target_at_least_2_of_3": sector_degraded >= 2,
                "sector_degradation_has_no_map_stale_confound": sector_map_stale == 0,
                "adaptive_exact_fresh_risk_brake_at_least_2_of_3": adaptive_risk >= 2,
                "surface_probe_seen_all_filtered_rows": probe_seen == 6,
                "surface_probe_outside_fixed_sector_3_of_3": sector_probe_outside == 3,
            }
        )
        counts.update(
            {
                "full_safe": full_safe,
                "sector_safe": sum(base.safe(row) for row in selected["sector"]),
                "adaptive_safe": adaptive_safe,
                "sector_degraded_after_target": sector_degraded,
                "sector_rows_with_map_stale": sector_map_stale,
                "adaptive_exact_fresh_risk_brake_rows": adaptive_risk,
                "surface_probe_seen_rows": probe_seen,
                "sector_surface_probe_outside_rows": sector_probe_outside,
            }
        )
        pass_decision = "PROCEED_TO_HELD_OUT_MAP_DESIGN"
        fail_decision = "STOP_V4_THREE_MODE_GATE_FAILED"
    return {
        "schema": "angular-blind-turn-v4-flight-gate-v1",
        "phase": phase,
        "decision": pass_decision if all(checks.values()) else fail_decision,
        "checks": checks,
        "counts": counts,
        "diagnostics": {
            "no_retry_or_replacement_rows": True,
            "no_mcnemar_test": True,
            "reason": "n=1/n=3 development gates; not inferential evidence",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--phase", choices=("full", "pilot"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.raw, args.phase)
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
