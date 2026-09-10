#!/usr/bin/env python3
"""Build the frozen eight-condition n=20 paper summary."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Callable


MODES = ("full", "sector", "adaptive")
NORMAL_CONDITIONS = {
    "R1_r0p150": ("seed1", "seed2"),
    "R2_r0p275": ("seed3", "seed4"),
    "R3_r0p400": ("seed5", "seed6"),
    "R4_r0p525": ("seed7", "seed8"),
    "R5_r0p650": ("seed9", "seed10"),
}
STRESS_CONDITIONS = {
    "C1_mirror": ("shc1_mirror_hazard",),
    "C2_wide_offset": ("shc2_wide_offset_hazard",),
    "C3_near_short": ("shc3_near_short_hazard",),
}


def boolean(value: object) -> bool:
    return str(value).strip().lower() == "true"


def number(row: dict[str, str], key: str) -> float | None:
    encoded = row.get(key, "").strip()
    if not encoded:
        return None
    value = float(encoded)
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {encoded!r}")
    return value


def mean(rows: list[dict[str, str]], key: str) -> float | None:
    values = [number(row, key) for row in rows]
    finite = [value for value in values if value is not None]
    return sum(finite) / len(finite) if finite else None


def wilson(successes: int, total: int,
           z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / denominator
    radius = z * math.sqrt(
        p * (1.0 - p) / total + z * z / (4.0 * total * total)
    ) / denominator
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def exact_mcnemar_two_sided(a: int, b: int) -> float:
    discordant = a + b
    if discordant == 0:
        return 1.0
    lower = min(a, b)
    tail = sum(math.comb(discordant, k) for k in range(lower + 1)) / 2**discordant
    return min(1.0, 2.0 * tail)


def safe_complete(row: dict[str, str]) -> bool:
    return boolean(row.get("success")) and number(row, "safety_collisions") == 0.0


def common_integrity(row: dict[str, str]) -> bool:
    return (
        boolean(row.get("run_valid"))
        and boolean(row.get("first_attempt_success"))
        and number(row, "attempt_count") == 1.0
        and number(row, "retry_count") == 0.0
        and boolean(row.get("resource_valid"))
        and boolean(row.get("speed_limit_valid"))
        and boolean(row.get("static_pcd_enabled"))
        and number(row, "oom_kill_delta") == 0.0
        and not boolean(row.get("infrastructure_failure"))
    )


def dropout_integrity(row: dict[str, str]) -> bool:
    run = int(float(row["run"]))
    expected_phase = round(0.2 * ((run - 1) % 10), 9)
    rendered = number(row, "sensor_rendered_frames")
    delivered = number(row, "sensor_delivered_frames")
    dropped = number(row, "sensor_dropped_frames")
    return (
        common_integrity(row)
        and boolean(row.get("sensor_dropout_enabled"))
        and boolean(row.get("sensor_dropout_phase_env_override"))
        and number(row, "sensor_dropout_expected_phase_s") is not None
        and math.isclose(number(row, "sensor_dropout_expected_phase_s"),
                         expected_phase, abs_tol=1e-6)
        and number(row, "sensor_dropout_phase_s") is not None
        and math.isclose(number(row, "sensor_dropout_phase_s"),
                         expected_phase, abs_tol=1e-6)
        and math.isclose(number(row, "sensor_dropout_warmup_s") or -1.0,
                         1.0, abs_tol=1e-6)
        and math.isclose(number(row, "sensor_dropout_period_s") or -1.0,
                         2.0, abs_tol=1e-6)
        and math.isclose(number(row, "sensor_dropout_duration_s") or -1.0,
                         0.5, abs_tol=1e-6)
        and rendered is not None and delivered is not None and dropped is not None
        and rendered == delivered + dropped
        and delivered > 0.0 and dropped > 0.0
        and (number(row, "sensor_dropout_bursts") or 0.0) >= 1.0
        and 4.0 <= (number(row, "sensor_dropout_max_consecutive_dropped")
                    or 0.0) <= 6.0
        and 0.45 <= (number(row, "sensor_dropout_max_delivered_gap_s")
                     or 0.0) <= 0.75
        and 9.5 <= (number(row, "sensor_hz") or 0.0) <= 10.5
    )


def summarize(rows: list[dict[str, str]],
              integrity: Callable[[dict[str, str]], bool]) -> dict[str, object]:
    safe = sum(safe_complete(row) for row in rows)
    contacts = sum(
        (number(row, "safety_collisions") or 0.0) > 0.0 for row in rows
    )
    result: dict[str, object] = {
        "runs": len(rows),
        "completion_count": sum(boolean(row.get("success")) for row in rows),
        "contact_run_count": contacts,
        "contact_run_rate": contacts / len(rows) if rows else None,
        "safe_completion_count": safe,
        "safe_completion_rate": safe / len(rows) if rows else None,
        "safe_completion_wilson_95": wilson(safe, len(rows)),
        "integrity_valid_count": sum(integrity(row) for row in rows),
    }
    for key in (
        "mission_time_s",
        "static_pcd_clearance_m",
        "planner_ingress_payload_mib_s",
        "total_ms_mean",
        "algorithm_cpu_cores_mean",
        "end_to_end_cpu_cores_mean",
        "end_to_end_cpu_core_s",
        "map_points_s",
        "filter_kept_pct",
        "filter_effective_full_open_transitions",
        "filter_trajectory_guard_open_transitions",
        "filter_replan_guard_open_transitions",
        "filter_open_duty_pct",
        "trajectory_audit_exact_fresh_occupied_verdicts",
    ):
        result[f"{key}_mean"] = mean(rows, key)
    return result


def paired(rows: list[dict[str, str]]) -> dict[str, object]:
    sector = {
        (row["map"], int(float(row["run"]))): safe_complete(row)
        for row in rows if row.get("mode") == "sector"
    }
    adaptive = {
        (row["map"], int(float(row["run"]))): safe_complete(row)
        for row in rows if row.get("mode") == "adaptive"
    }
    keys = set(sector) & set(adaptive)
    adaptive_favouring = sum(not sector[key] and adaptive[key] for key in keys)
    sector_favouring = sum(sector[key] and not adaptive[key] for key in keys)
    return {
        "pairs": len(keys),
        "sector_unsafe_adaptive_safe": adaptive_favouring,
        "sector_safe_adaptive_unsafe": sector_favouring,
        "exact_mcnemar_two_sided_p": exact_mcnemar_two_sided(
            adaptive_favouring, sector_favouring
        ),
    }


def reduction(full: object, adaptive: object) -> float | None:
    if not isinstance(full, (int, float)) or full <= 0:
        return None
    if not isinstance(adaptive, (int, float)):
        return None
    return 100.0 * (full - adaptive) / full


def expected_matrix(rows: list[dict[str, str]], maps: tuple[str, ...],
                    run_start: int, run_end: int) -> bool:
    expected = {
        (map_name, str(run), mode)
        for map_name in maps
        for run in range(run_start, run_end + 1)
        for mode in MODES
    }
    observed = {(row.get("map"), row.get("run"), row.get("mode")) for row in rows}
    return len(rows) == len(expected) and observed == expected


def summarize_group(rows: list[dict[str, str]],
                    integrity: Callable[[dict[str, str]], bool]) -> dict[str, object]:
    modes = {
        mode: summarize([row for row in rows if row.get("mode") == mode], integrity)
        for mode in MODES
    }
    full = modes["full"]
    adaptive = modes["adaptive"]
    return {
        "modes": modes,
        "paired_adaptive_vs_sector": paired(rows),
        "adaptive_vs_full": {
            "mission_time_reduction_pct": reduction(
                full["mission_time_s_mean"], adaptive["mission_time_s_mean"]
            ),
            "planner_ingress_reduction_pct": reduction(
                full["planner_ingress_payload_mib_s_mean"],
                adaptive["planner_ingress_payload_mib_s_mean"],
            ),
            "map_compute_per_frame_reduction_pct": reduction(
                full["total_ms_mean_mean"], adaptive["total_ms_mean_mean"]
            ),
            "end_to_end_cpu_mean_reduction_pct": reduction(
                full["end_to_end_cpu_cores_mean_mean"],
                adaptive["end_to_end_cpu_cores_mean_mean"],
            ),
            "end_to_end_core_seconds_reduction_pct": reduction(
                full["end_to_end_cpu_core_s_mean"],
                adaptive["end_to_end_cpu_core_s_mean"],
            ),
        },
    }


def analyze(normal_rows: list[dict[str, str]],
            normal_validation: dict[str, object],
            stress_rows: list[dict[str, str]],
            block1_rows: list[dict[str, str]],
            block1_result: dict[str, object]) -> dict[str, object]:
    normal_maps = tuple(
        map_name for maps in NORMAL_CONDITIONS.values() for map_name in maps
    )
    stress_maps = tuple(maps[0] for maps in STRESS_CONDITIONS.values())
    block2_rows = [row for row in stress_rows if int(float(row["run"])) >= 11]
    copied_block1_rows = [
        row for row in stress_rows if int(float(row["run"])) <= 10
    ]
    block1_by_key = {
        (row["map"], row["run"], row["mode"]): row for row in block1_rows
    }
    copied_by_key = {
        (row["map"], row["run"], row["mode"]): row for row in copied_block1_rows
    }

    normal_matrix = expected_matrix(normal_rows, normal_maps, 1, 10)
    block1_matrix = expected_matrix(block1_rows, stress_maps, 1, 10)
    block2_matrix = expected_matrix(block2_rows, stress_maps, 11, 20)
    stress_matrix = expected_matrix(stress_rows, stress_maps, 1, 20)
    normal_integrity = normal_matrix and all(common_integrity(row) for row in normal_rows)
    block2_integrity = block2_matrix and all(dropout_integrity(row) for row in block2_rows)

    conditions: dict[str, object] = {}
    for name, maps in NORMAL_CONDITIONS.items():
        rows = [row for row in normal_rows if row.get("map") in maps]
        conditions[name] = {
            "family": "normal_radius_tier",
            "physical_maps": list(maps),
            **summarize_group(rows, common_integrity),
        }
    for name, maps in STRESS_CONDITIONS.items():
        rows = [row for row in stress_rows if row.get("map") in maps]
        conditions[name] = {
            "family": "static_burst_dropout",
            "physical_maps": list(maps),
            **summarize_group(rows, dropout_integrity),
        }

    normal_group = summarize_group(normal_rows, common_integrity)
    stress_block1 = summarize_group(block1_rows, dropout_integrity)
    stress_block2 = summarize_group(block2_rows, dropout_integrity)
    stress_combined = summarize_group(stress_rows, dropout_integrity)

    block2_full_safe = all(
        sum(safe_complete(row) for row in block2_rows
            if row["map"] == map_name and row["mode"] == "full") == 10
        for map_name in stress_maps
    )
    block2_adaptive_safe = all(
        sum(safe_complete(row) for row in block2_rows
            if row["map"] == map_name and row["mode"] == "adaptive") == 10
        for map_name in stress_maps
    )
    block2_sector_unsafe = all(
        sum(safe_complete(row) for row in block2_rows
            if row["map"] == map_name and row["mode"] == "sector") < 10
        for map_name in stress_maps
    )
    block2_pair = stress_block2["paired_adaptive_vs_sector"]
    replication_checks = {
        "complete_unique_block2_matrix": block2_matrix,
        "all_block2_rows_integrity_valid": block2_integrity,
        "full_10_of_10_safe_each_map": block2_full_safe,
        "adaptive_10_of_10_safe_each_map": block2_adaptive_safe,
        "sector_unsafe_at_least_once_each_map": block2_sector_unsafe,
        "discordance_adaptive_favouring": (
            block2_pair["sector_unsafe_adaptive_safe"]
            > block2_pair["sector_safe_adaptive_unsafe"]
        ),
        "exact_mcnemar_p_below_0_05": (
            block2_pair["exact_mcnemar_two_sided_p"] < 0.05
        ),
    }
    if all(replication_checks.values()):
        replication_decision = "STRESS_REPLICATION_OBSERVED"
    elif block2_matrix and block2_integrity and (
        block2_pair["sector_unsafe_adaptive_safe"]
        > block2_pair["sector_safe_adaptive_unsafe"]
    ):
        replication_decision = "STRESS_REPLICATION_PARTIAL"
    else:
        replication_decision = "STRESS_REPLICATION_FAILED"

    complete_conditions = all(
        condition["modes"][mode]["runs"] == 20
        for condition in conditions.values() for mode in MODES
    )
    checks = {
        "normal_source_validation_passed": normal_validation.get("passed") is True,
        "normal_matrix_complete_and_integrity_valid": normal_integrity,
        "block1_matrix_complete": block1_matrix,
        "block1_result_confirmatory": (
            block1_result.get("decision") == "CONFIRMATORY_TRANSFER_OBSERVED"
        ),
        "block1_rows_copied_exactly": block1_by_key == copied_by_key,
        "stress_n20_matrix_complete": stress_matrix,
        "eight_conditions_have_20_rows_per_mode": complete_conditions,
        "block2_replication_observed": (
            replication_decision == "STRESS_REPLICATION_OBSERVED"
        ),
    }
    decision = (
        "EIGHT_CONDITION_N20_COMPLETE"
        if all(checks.values()) else "EIGHT_CONDITION_N20_INCOMPLETE"
    )
    return {
        "schema": "eight-condition-n20-result-v1",
        "decision": decision,
        "checks": checks,
        "failure_reasons": [name for name, passed in checks.items() if not passed],
        "stress_replication_decision": replication_decision,
        "stress_replication_checks": replication_checks,
        "conditions": conditions,
        "groups": {
            "normal_R1_R5": normal_group,
            "stress_C1_C3_block1": stress_block1,
            "stress_C1_C3_block2": stress_block2,
            "stress_C1_C3_combined_n20": stress_combined,
        },
        "row_accounting": {
            "normal_rows": len(normal_rows),
            "stress_block1_rows": len(block1_rows),
            "stress_block2_rows": len(block2_rows),
            "stress_combined_rows": len(stress_rows),
            "paper_table_rows": len(normal_rows) + len(stress_rows),
        },
        "claim_boundary": (
            "Eight reporting conditions: five normal radius tiers retain two "
            "physical layout replicates each; three static burst-dropout maps "
            "contain an original preregistered block and a post-outcome frozen "
            "replication block. Normal and stress metrics are not pooled."
        ),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-campaign", type=Path, required=True)
    parser.add_argument("--normal-validation", type=Path, required=True)
    parser.add_argument("--stress-campaign", type=Path, required=True)
    parser.add_argument("--stress-block1-campaign", type=Path, required=True)
    parser.add_argument("--stress-block1-result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        read_csv(args.normal_campaign),
        json.loads(args.normal_validation.read_text()),
        read_csv(args.stress_campaign),
        read_csv(args.stress_block1_campaign),
        json.loads(args.stress_block1_result.read_text()),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    return 0 if result["decision"] == "EIGHT_CONDITION_N20_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
