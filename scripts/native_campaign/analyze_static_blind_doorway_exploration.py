#!/usr/bin/env python3
"""Summarize the frozen c1--c3 static blind-doorway exploration."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import os
from pathlib import Path


def read_one(path: Path) -> dict:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one row, got {len(rows)}")
    return rows[0]


def boolean(value) -> bool:
    return str(value).strip().lower() == "true"


def number(row: dict, key: str):
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def context(row: dict, key: str):
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    return ast.literal_eval(value)


def summarize_candidate(name: str, clear: dict, sector: dict,
                        adaptive: dict | None) -> dict:
    clear_conflict = number(clear, "trajectory_audit_min_clearance_m")
    sector_conflict = number(sector, "trajectory_audit_min_clearance_m")
    sector_collisions = int(float(sector.get("safety_collisions") or 0))
    sector_success = boolean(sector.get("success"))
    hazard_exact = (
        int(float(adaptive.get(
            "trajectory_audit_hazard_matched_exact_occupied_verdicts"
        ) or 0))
        if adaptive is not None
        and "trajectory_audit_hazard_matched_exact_occupied_verdicts" in adaptive
        else None
    )
    first_exact = (
        context(adaptive, "trajectory_audit_first_exact_fresh_occupied_context")
        if adaptive is not None else None
    )
    generic_exact = (
        int(float(adaptive.get(
            "trajectory_audit_exact_fresh_occupied_verdicts"
        ) or 0)) if adaptive is not None else None
    )
    # C1 predates the explicit hazard-matched counter. It emitted exactly one
    # exact verdict, so its recorded first witness is also its only witness and
    # can be classified without guessing about any unrecorded verdict.
    if hazard_exact is None and generic_exact == 1 and first_exact:
        witness = first_exact.get("witness_position")
        center_x = number(adaptive, "static_hazard_center_x")
        center_y = number(adaptive, "static_hazard_center_y")
        radius = number(adaptive, "static_hazard_radius_m")
        height = number(adaptive, "static_hazard_height_m")
        if witness and None not in (center_x, center_y, radius, height):
            radial_outside = max(
                0.0, math.hypot(witness[0] - center_x, witness[1] - center_y)
                - radius
            )
            vertical_outside = max(0.0, -witness[2], witness[2] - height)
            hazard_exact = int(
                math.hypot(radial_outside, vertical_outside) - 0.2 < 0.0
            )
    return {
        "candidate": name,
        "clear_sector_success": boolean(clear.get("success")),
        "clear_sector_safety_collisions": int(
            float(clear.get("safety_collisions") or 0)
        ),
        "clear_sector_hypothetical_min_clearance_m": clear_conflict,
        "clear_sector_committed_conflict": (
            clear_conflict is not None and clear_conflict < 0.0
        ),
        "hazard_sector_success": sector_success,
        "hazard_sector_safety_collisions": sector_collisions,
        "hazard_sector_min_clearance_m": number(
            sector, "static_hazard_min_clearance_m"
        ),
        "hazard_sector_committed_min_clearance_m": sector_conflict,
        "hazard_sector_degraded": (not sector_success or sector_collisions > 0),
        "adaptive_shadow_success": (
            boolean(adaptive.get("success")) if adaptive is not None else None
        ),
        "adaptive_shadow_hazard_min_clearance_m": (
            number(adaptive, "static_hazard_min_clearance_m")
            if adaptive is not None else None
        ),
        "adaptive_shadow_generic_exact_occupied": (
            generic_exact
        ),
        "adaptive_shadow_hazard_matched_exact_occupied": hazard_exact,
        "adaptive_shadow_first_exact_witness": (
            first_exact.get("witness_position") if first_exact else None
        ),
    }


def analyze(candidates: list[dict], replay_gate: dict) -> dict:
    all_clear_conflict = all(
        item["clear_sector_committed_conflict"] for item in candidates
    )
    degraded = [item["candidate"] for item in candidates
                if item["hazard_sector_degraded"]]
    hazard_exact_candidates = [
        item["candidate"] for item in candidates
        if (item["adaptive_shadow_hazard_matched_exact_occupied"] or 0) >= 2
    ]
    checks = {
        "all_clear_controls_commit_hypothetical_conflict": all_clear_conflict,
        "actual_raycast_frontend_component_gate_passed": (
            replay_gate.get("decision") == "PASS"
        ),
        "at_least_one_hazard_sector_degraded": bool(degraded),
        "at_least_one_closed_loop_hazard_matched_exact_pair": bool(
            hazard_exact_candidates
        ),
    }
    return {
        "schema": "static-blind-doorway-exploration-result-v1",
        "decision": (
            "PROCEED_TO_PREREGISTRATION" if all(checks.values())
            else "STOP_C1_C3_NO_STATIC_SAFETY_SEPARATION"
        ),
        "checks": checks,
        "sector_degraded_candidates": degraded,
        "hazard_exact_candidates": hazard_exact_candidates,
        "candidates": candidates,
        "interpretation": (
            "C1-C3 are exploratory design data. Do not pool them with a "
            "future evaluation and do not infer a safety-rate advantage."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c1-clear", type=Path, required=True)
    parser.add_argument("--c1-sector", type=Path, required=True)
    parser.add_argument("--c1-adaptive", type=Path, required=True)
    parser.add_argument("--c2-clear", type=Path, required=True)
    parser.add_argument("--c2-sector", type=Path, required=True)
    parser.add_argument("--c3-clear", type=Path, required=True)
    parser.add_argument("--c3-sector", type=Path, required=True)
    parser.add_argument("--c3-adaptive", type=Path, required=True)
    parser.add_argument("--replay-gate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidates = [
        summarize_candidate(
            "c1", read_one(args.c1_clear), read_one(args.c1_sector),
            read_one(args.c1_adaptive)
        ),
        summarize_candidate(
            "c2", read_one(args.c2_clear), read_one(args.c2_sector), None
        ),
        summarize_candidate(
            "c3", read_one(args.c3_clear), read_one(args.c3_sector),
            read_one(args.c3_adaptive)
        ),
    ]
    result = analyze(candidates, json.loads(args.replay_gate.read_text()))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)


if __name__ == "__main__":
    main()
