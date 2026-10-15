#!/usr/bin/env python3
"""Summarize the frozen shm1_h9 repeated three-mode exploration."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path


MODES = ("full", "sector", "adaptive")


def boolean(value: object) -> bool:
    return str(value).strip().lower() == "true"


def number(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "").strip()
    if not value:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite {key}: {value!r}")
    return result


def mean(rows: list[dict[str, str]], key: str) -> float | None:
    values = [number(row, key) for row in rows]
    finite = [value for value in values if value is not None]
    return sum(finite) / len(finite) if finite else None


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    proportion = successes / total
    denominator = 1.0 + z * z / total
    centre = (proportion + z * z / (2.0 * total)) / denominator
    radius = z * math.sqrt(
        proportion * (1.0 - proportion) / total
        + z * z / (4.0 * total * total)
    ) / denominator
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def exact_mcnemar_two_sided(discordant_a: int, discordant_b: int) -> float:
    total = discordant_a + discordant_b
    if total == 0:
        return 1.0
    tail = min(discordant_a, discordant_b)
    probability = sum(math.comb(total, k) for k in range(tail + 1)) / (2 ** total)
    return min(1.0, 2.0 * probability)


def safe_complete(row: dict[str, str]) -> bool:
    collisions = number(row, "safety_collisions")
    return boolean(row.get("success")) and collisions == 0.0


def summarize_mode(rows: list[dict[str, str]]) -> dict[str, object]:
    safe_count = sum(safe_complete(row) for row in rows)
    contact_count = sum((number(row, "safety_collisions") or 0.0) > 0.0 for row in rows)
    summary: dict[str, object] = {
        "runs": len(rows),
        "completion_count": sum(boolean(row.get("success")) for row in rows),
        "safe_completion_count": safe_count,
        "safe_completion_rate": safe_count / len(rows),
        "safe_completion_wilson_95": wilson_interval(safe_count, len(rows)),
        "contact_run_count": contact_count,
        "contact_run_rate": contact_count / len(rows),
        "first_attempt_success_count": sum(
            boolean(row.get("first_attempt_success")) for row in rows
        ),
    }
    for key in (
        "mission_time_s",
        "static_pcd_clearance_m",
        "planner_ingress_payload_mib_s",
        "algorithm_delivery_payload_mib_s",
        "fsm_cpu_pct",
        "algorithm_cpu_cores_mean",
        "end_to_end_cpu_cores_mean",
        "map_points_s",
        "filter_kept_pct",
        "filter_effective_full_open_transitions",
        "filter_trajectory_guard_open_transitions",
        "filter_replan_guard_open_transitions",
        "filter_pre_stale_full_refresh_frames",
        "filter_pre_stale_full_refresh_ack_committed_count",
        "filter_full_refresh_request_count",
        "filter_open_duty_pct",
        "filter_open_point_duty_pct",
    ):
        summary[f"{key}_mean"] = mean(rows, key)
    return summary


def analyze(rows: list[dict[str, str]], replay_gate: dict[str, object],
            expected_map: str, expected_runs: int) -> dict[str, object]:
    grouped = {mode: [row for row in rows if row.get("mode") == mode]
               for mode in MODES}
    unexpected_modes = sorted({row.get("mode", "") for row in rows} - set(MODES))
    all_expected_map = all(row.get("map") == expected_map for row in rows)
    unique_keys = {(row.get("run"), row.get("mode")) for row in rows}
    complete_matrix = (
        len(rows) == expected_runs * len(MODES)
        and len(unique_keys) == len(rows)
        and all(len(grouped[mode]) == expected_runs for mode in MODES)
    )
    integrity_rows = all(
        boolean(row.get("first_attempt_success"))
        and boolean(row.get("resource_valid"))
        and boolean(row.get("speed_limit_valid"))
        and boolean(row.get("static_pcd_enabled"))
        for row in rows
    )
    summaries = {mode: summarize_mode(grouped[mode]) for mode in MODES}

    by_mode_run = {
        mode: {int(float(row["run"])): safe_complete(row) for row in grouped[mode]}
        for mode in MODES
    }
    sector_unsafe_adaptive_safe = sum(
        (not by_mode_run["sector"][run]) and by_mode_run["adaptive"][run]
        for run in range(1, expected_runs + 1)
    ) if complete_matrix else 0
    sector_safe_adaptive_unsafe = sum(
        by_mode_run["sector"][run] and (not by_mode_run["adaptive"][run])
        for run in range(1, expected_runs + 1)
    ) if complete_matrix else 0
    mcnemar_p = exact_mcnemar_two_sided(
        sector_unsafe_adaptive_safe, sector_safe_adaptive_unsafe
    )

    full_cpu = summaries["full"]["algorithm_cpu_cores_mean_mean"]
    adaptive_cpu = summaries["adaptive"]["algorithm_cpu_cores_mean_mean"]
    cpu_reduction = (
        100.0 * (float(full_cpu) - float(adaptive_cpu)) / float(full_cpu)
        if isinstance(full_cpu, (int, float)) and full_cpu > 0
        and isinstance(adaptive_cpu, (int, float)) else None
    )
    full_ingress = summaries["full"]["planner_ingress_payload_mib_s_mean"]
    adaptive_ingress = summaries["adaptive"]["planner_ingress_payload_mib_s_mean"]
    ingress_change = (
        100.0 * (float(adaptive_ingress) - float(full_ingress)) / float(full_ingress)
        if isinstance(full_ingress, (int, float)) and full_ingress > 0
        and isinstance(adaptive_ingress, (int, float)) else None
    )

    checks = {
        "replay_component_gate_passed": replay_gate.get("decision") == "PASS",
        "only_expected_map": all_expected_map,
        "only_expected_modes": not unexpected_modes,
        "complete_paired_matrix": complete_matrix,
        "all_rows_first_attempt_resource_and_speed_valid": integrity_rows,
        "full_all_safe_complete": summaries["full"]["safe_completion_count"] == expected_runs,
        "adaptive_all_safe_complete": summaries["adaptive"]["safe_completion_count"] == expected_runs,
        "sector_has_safety_degradation": summaries["sector"]["safe_completion_count"] < expected_runs,
        "paired_adaptive_vs_sector_exact_p_below_0_05": mcnemar_p < 0.05,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "static-heading-mismatch-campaign-result-v1",
        "decision": "EXPLORATORY_SEPARATION_OBSERVED" if not failed else "GATE_FAILED",
        "map": expected_map,
        "checks": checks,
        "failure_reasons": failed,
        "modes": summaries,
        "paired_adaptive_vs_sector": {
            "sector_unsafe_adaptive_safe": sector_unsafe_adaptive_safe,
            "sector_safe_adaptive_unsafe": sector_safe_adaptive_unsafe,
            "exact_mcnemar_two_sided_p": mcnemar_p,
        },
        "adaptive_vs_full": {
            "algorithm_cpu_mean_reduction_pct": cpu_reduction,
            "planner_ingress_payload_change_pct": ingress_change,
        },
        "interpretation": (
            "This is a frozen exploratory severe 2 Hz dropout-equivalent stress. "
            "It establishes a mechanism-specific separation, not a nominal-rate "
            "population guarantee or a replacement for held-out confirmation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--replay-gate", type=Path, required=True)
    parser.add_argument("--map", default="shm1_h9_hazard")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.campaign.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = analyze(rows, json.loads(args.replay_gate.read_text()), args.map, args.runs)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    return 0 if result["decision"] != "GATE_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
