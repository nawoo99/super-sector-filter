#!/usr/bin/env python3
"""Analyze the preregistered three-map burst-dropout confirmation matrix."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path


MODES = ("full", "sector", "adaptive")
MAPS = (
    "shc1_mirror_hazard",
    "shc2_wide_offset_hazard",
    "shc3_near_short_hazard",
)


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


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        raise ValueError("Wilson interval requires at least one row")
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


def row_integrity(row: dict[str, str]) -> bool:
    run = int(float(row["run"]))
    expected_phase = round(0.2 * ((run - 1) % 10), 9)
    rendered = number(row, "sensor_rendered_frames")
    delivered = number(row, "sensor_delivered_frames")
    dropped = number(row, "sensor_dropped_frames")
    return (
        boolean(row.get("first_attempt_success"))
        and number(row, "attempt_count") == 1.0
        and number(row, "retry_count") == 0.0
        and boolean(row.get("resource_valid"))
        and not boolean(row.get("resource_guard_triggered"))
        and boolean(row.get("speed_limit_valid"))
        and boolean(row.get("static_pcd_enabled"))
        and number(row, "oom_kill_delta") == 0.0
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
        and delivered > 0 and dropped > 0
        and (number(row, "sensor_dropout_bursts") or 0.0) >= 1.0
        and (number(row, "sensor_dropout_max_consecutive_dropped") or 0.0) >= 4.0
        and 0.45 <= (number(row, "sensor_dropout_max_delivered_gap_s") or 0.0) <= 0.75
        and 9.5 <= (number(row, "sensor_hz") or 0.0) <= 10.5
    )


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    safe = sum(safe_complete(row) for row in rows)
    contact = sum((number(row, "safety_collisions") or 0.0) > 0.0 for row in rows)
    result: dict[str, object] = {
        "runs": len(rows),
        "completion_count": sum(boolean(row.get("success")) for row in rows),
        "safe_completion_count": safe,
        "safe_completion_rate": safe / len(rows) if rows else None,
        "safe_completion_wilson_95": wilson(safe, len(rows)) if rows else None,
        "contact_run_count": contact,
        "contact_run_rate": contact / len(rows) if rows else None,
        "integrity_valid_count": sum(row_integrity(row) for row in rows),
    }
    for key in (
        "mission_time_s",
        "static_pcd_clearance_m",
        "sensor_hz",
        "sensor_dropout_bursts",
        "sensor_dropout_max_consecutive_dropped",
        "sensor_dropout_max_delivered_gap_s",
        "sensor_payload_mib_s",
        "planner_ingress_payload_mib_s",
        "algorithm_delivery_payload_mib_s",
        "dds_total_algorithm_payload_mib_s",
        "algorithm_cpu_cores_mean",
        "end_to_end_cpu_cores_mean",
        "map_points_s",
        "filter_kept_pct",
        "filter_effective_full_open_transitions",
        "filter_trajectory_guard_open_transitions",
        "filter_replan_guard_open_transitions",
        "filter_open_duty_pct",
        "filter_open_point_duty_pct",
        "trajectory_audit_exact_fresh_occupied_verdicts",
    ):
        result[f"{key}_mean"] = mean(rows, key)
    return result


def gate_full_rows(rows: list[dict[str, str]], maps: tuple[str, ...]) -> bool:
    keys = {(row.get("map"), row.get("mode"), row.get("run")) for row in rows}
    return (
        len(rows) == len(maps)
        and len(keys) == len(rows)
        and {row.get("map") for row in rows} == set(maps)
        and all(row.get("mode") == "full" and row.get("run") == "1" for row in rows)
        and all(safe_complete(row) and row_integrity(row) for row in rows)
    )


def analyze(
    rows: list[dict[str, str]],
    full_gate_rows: list[dict[str, str]],
    structure_gate: dict[str, object],
    replay_gates: list[dict[str, object]],
    fault_gate: dict[str, object],
    maps: tuple[str, ...] = MAPS,
    expected_runs: int = 10,
) -> dict[str, object]:
    expected_keys = {
        (map_name, str(run), mode)
        for map_name in maps
        for run in range(1, expected_runs + 1)
        for mode in MODES
    }
    observed_keys = {(row.get("map"), row.get("run"), row.get("mode")) for row in rows}
    complete_matrix = len(rows) == len(expected_keys) and observed_keys == expected_keys
    all_integrity = complete_matrix and all(row_integrity(row) for row in rows)

    by_map: dict[str, object] = {}
    adaptive_favouring = 0
    sector_favouring = 0
    for map_name in maps:
        map_rows = [row for row in rows if row.get("map") == map_name]
        modes = {
            mode: summarize([row for row in map_rows if row.get("mode") == mode])
            for mode in MODES
        }
        sector_by_run = {
            int(float(row["run"])): safe_complete(row)
            for row in map_rows if row.get("mode") == "sector"
        }
        adaptive_by_run = {
            int(float(row["run"])): safe_complete(row)
            for row in map_rows if row.get("mode") == "adaptive"
        }
        map_a = sum(
            not sector_by_run.get(run, False) and adaptive_by_run.get(run, False)
            for run in range(1, expected_runs + 1)
        )
        map_b = sum(
            sector_by_run.get(run, False) and not adaptive_by_run.get(run, False)
            for run in range(1, expected_runs + 1)
        )
        adaptive_favouring += map_a
        sector_favouring += map_b
        by_map[map_name] = {
            "modes": modes,
            "paired_adaptive_vs_sector": {
                "sector_unsafe_adaptive_safe": map_a,
                "sector_safe_adaptive_unsafe": map_b,
                "exact_mcnemar_two_sided_p": exact_mcnemar_two_sided(map_a, map_b),
            },
        }

    aggregate_modes = {
        mode: summarize([row for row in rows if row.get("mode") == mode])
        for mode in MODES
    }
    mcnemar_p = exact_mcnemar_two_sided(adaptive_favouring, sector_favouring)
    full_cpu = aggregate_modes["full"]["algorithm_cpu_cores_mean_mean"]
    adaptive_cpu = aggregate_modes["adaptive"]["algorithm_cpu_cores_mean_mean"]
    full_end_to_end_cpu = aggregate_modes["full"]["end_to_end_cpu_cores_mean_mean"]
    adaptive_end_to_end_cpu = aggregate_modes["adaptive"]["end_to_end_cpu_cores_mean_mean"]
    full_ingress = aggregate_modes["full"]["planner_ingress_payload_mib_s_mean"]
    adaptive_ingress = aggregate_modes["adaptive"]["planner_ingress_payload_mib_s_mean"]
    cpu_reduction = (
        100.0 * (float(full_cpu) - float(adaptive_cpu)) / float(full_cpu)
        if isinstance(full_cpu, (int, float)) and full_cpu > 0
        and isinstance(adaptive_cpu, (int, float)) else None
    )
    end_to_end_cpu_reduction = (
        100.0 * (float(full_end_to_end_cpu) - float(adaptive_end_to_end_cpu))
        / float(full_end_to_end_cpu)
        if isinstance(full_end_to_end_cpu, (int, float))
        and full_end_to_end_cpu > 0
        and isinstance(adaptive_end_to_end_cpu, (int, float)) else None
    )
    ingress_change = (
        100.0 * (float(adaptive_ingress) - float(full_ingress)) / float(full_ingress)
        if isinstance(full_ingress, (int, float)) and full_ingress > 0
        and isinstance(adaptive_ingress, (int, float)) else None
    )

    map_full_safe = {
        map_name: by_map[map_name]["modes"]["full"]["safe_completion_count"]
        == expected_runs for map_name in maps
    }
    map_adaptive_safe = {
        map_name: by_map[map_name]["modes"]["adaptive"]["safe_completion_count"]
        == expected_runs for map_name in maps
    }
    map_sector_degraded = {
        map_name: by_map[map_name]["modes"]["sector"]["safe_completion_count"]
        < expected_runs for map_name in maps
    }
    checks = {
        "structure_gate_passed": structure_gate.get("status") == "PASS",
        "all_three_replay_gates_passed": (
            len(replay_gates) == len(maps)
            and all(gate.get("decision") == "PASS" for gate in replay_gates)
        ),
        "fault_integrity_smoke_passed": fault_gate.get("decision") == "PASS",
        "full_feasibility_gate_passed": gate_full_rows(full_gate_rows, maps),
        "complete_unique_paired_matrix": complete_matrix,
        "all_rows_integrity_valid": all_integrity,
        "full_10_of_10_safe_each_map": all(map_full_safe.values()),
        "adaptive_10_of_10_safe_each_map": all(map_adaptive_safe.values()),
        "sector_unsafe_at_least_once_each_map": all(map_sector_degraded.values()),
        "aggregate_discordance_adaptive_favouring": adaptive_favouring > sector_favouring,
        "aggregate_exact_mcnemar_p_below_0_05": mcnemar_p < 0.05,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if not failed:
        decision = "CONFIRMATORY_TRANSFER_OBSERVED"
    elif (
        all(checks[name] for name in (
            "structure_gate_passed",
            "all_three_replay_gates_passed",
            "fault_integrity_smoke_passed",
            "full_feasibility_gate_passed",
            "complete_unique_paired_matrix",
            "all_rows_integrity_valid",
            "full_10_of_10_safe_each_map",
            "adaptive_10_of_10_safe_each_map",
        ))
        and any(map_sector_degraded.values())
    ):
        decision = "PARTIAL_TRANSFER"
    else:
        decision = "CONFIRMATION_FAILED"
    return {
        "schema": "static-burst-dropout-confirmation-result-v1",
        "decision": decision,
        "checks": checks,
        "failure_reasons": failed,
        "per_map": by_map,
        "aggregate": {
            "modes": aggregate_modes,
            "paired_adaptive_vs_sector": {
                "sector_unsafe_adaptive_safe": adaptive_favouring,
                "sector_safe_adaptive_unsafe": sector_favouring,
                "exact_mcnemar_two_sided_p": mcnemar_p,
            },
            "adaptive_vs_full": {
                "end_to_end_cpu_mean_reduction_pct": end_to_end_cpu_reduction,
                "algorithm_cpu_mean_reduction_pct": cpu_reduction,
                "planner_ingress_payload_change_pct": ingress_change,
                "cpu_scope_note": (
                    "End-to-end CPU is the fair primary comparison and includes "
                    "simulator+frontend+planner+mission. Algorithm CPU is secondary: "
                    "Full composition includes simulator while filtered modes report "
                    "planner-only scope."
                ),
            },
        },
        "claim_boundary": (
            "Finite three-map, ten-phase, simulation-only held-out stress suite; "
            "not a population guarantee and not nominal Map1-10 efficiency evidence."
        ),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--full-gate", type=Path, required=True)
    parser.add_argument("--structure-gate", type=Path, required=True)
    parser.add_argument("--replay-gates", type=Path, nargs=3, required=True)
    parser.add_argument("--fault-gate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        read_csv(args.campaign),
        read_csv(args.full_gate),
        json.loads(args.structure_gate.read_text()),
        [json.loads(path.read_text()) for path in args.replay_gates],
        json.loads(args.fault_gate.read_text()),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.out)
    print(rendered, end="")
    return 0 if result["decision"] != "CONFIRMATION_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
