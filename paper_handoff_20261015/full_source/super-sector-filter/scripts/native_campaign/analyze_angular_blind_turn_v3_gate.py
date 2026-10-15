#!/usr/bin/env python3
"""Fail-closed audit for the staged ``abt3_gate_open`` flight smoke."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import analyze_angular_blind_turn_calibration as base


MAP = "abt3_gate_open"


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, path)


def exact_fresh_risk_brake(row: dict[str, str]) -> bool:
    brakes = base.integer(row, "frontend_risk_brake_events")
    enforced = base.integer(row, "frontend_risk_enforced")
    return brakes > 0 and enforced >= brakes


def analyze(raw: Path, phase: str) -> dict:
    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))

    expected_modes = ("full",) if phase == "full" else ("sector", "adaptive")
    expected = {(MAP, "1", mode) for mode in expected_modes}
    actual = {(row.get("map"), row.get("run"), row.get("mode")) for row in rows}
    row_by_mode = {row.get("mode", ""): row for row in rows}
    exact_rows = len(rows) == len(expected) and actual == expected and len(actual) == len(rows)
    all_quality = exact_rows and all(base.quality_valid(row) for row in rows)

    checks: dict[str, bool] = {
        "exact_unique_first_attempt_rows": exact_rows,
        "all_rows_quality_valid": all_quality,
    }
    counts: dict[str, int] = {
        "rows": len(rows),
        "duplicates": len(rows) - len(actual),
    }
    if phase == "full":
        full = row_by_mode.get("full")
        checks["full_contact_free_completion"] = full is not None and base.safe(full)
        counts["full_safe"] = int(full is not None and base.safe(full))
        success_decision = "PROCEED_TO_PAIRED_MECHANISM_SMOKE"
        failure_decision = "STOP_FULL_FEASIBILITY_GATE_FAILED"
    else:
        sector = row_by_mode.get("sector")
        adaptive = row_by_mode.get("adaptive")
        sector_degraded = (
            sector is not None
            and not base.safe(sector)
            and base.integer(sector, "waypoints_reached") >= 1
        )
        adaptive_safe = adaptive is not None and base.safe(adaptive)
        adaptive_brake = adaptive is not None and exact_fresh_risk_brake(adaptive)
        filtered_rows = [row for row in rows if row.get("mode") in expected_modes]
        probe_outside = (
            len(filtered_rows) == 2
            and all(
                base.boolean(row.get("filter_static_probe_input_seen", ""))
                and not base.boolean(
                    row.get("filter_static_probe_first_center_in_sector", "")
                )
                for row in filtered_rows
            )
        )
        checks.update(
            {
                "sector_degraded_at_or_after_target": sector_degraded,
                "adaptive_contact_free_completion": adaptive_safe,
                "adaptive_exact_fresh_frontend_risk_brake": adaptive_brake,
                "surface_probe_seen_outside_sector_both_rows": probe_outside,
            }
        )
        counts.update(
            {
                "sector_safe": int(sector is not None and base.safe(sector)),
                "adaptive_safe": int(adaptive_safe),
                "adaptive_exact_fresh_frontend_risk_brake_rows": int(adaptive_brake),
            }
        )
        success_decision = "PROCEED_TO_LARGER_CALIBRATION"
        failure_decision = "STOP_PAIRED_MECHANISM_GATE_FAILED"

    return {
        "schema": "angular-blind-turn-v3-flight-gate-v1",
        "phase": phase,
        "decision": success_decision if all(checks.values()) else failure_decision,
        "checks": checks,
        "counts": counts,
        "diagnostics": {
            "no_retry_or_replacement_rows": True,
            "no_mcnemar_test": True,
            "reason": "n=1 development gate; not inferential evidence",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--phase", choices=("full", "comparison"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.raw, args.phase)
    write_atomic(args.out, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not all(result["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
