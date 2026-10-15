#!/usr/bin/env python3
"""Apply the frozen 2026-09-08 static-occlusion pilot expansion gates."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


MODES = ("full", "sector", "adaptive")
VISIBILITIES = ("nom", "occ")


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def as_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe(row: dict[str, str]) -> bool:
    return as_bool(row["success"]) and as_int(row["safety_collisions"]) == 0


def progress(row: dict[str, str]) -> float:
    return 0.5 * (
        as_float(row["filter_static_probe_first_drone_x"])
        + as_float(row["filter_static_probe_first_drone_y"])
    )


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(campaign: Path, prefix: Path) -> dict:
    with campaign.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    indexed = {(row["map"], row["mode"]): row for row in rows}
    expected = {
        (f"occ_p_r{tier}_{visibility}", mode)
        for tier in range(1, 6)
        for visibility in VISIBILITIES
        for mode in MODES
    }
    observed = set(indexed)

    quality_rows = [
        row
        for row in rows
        if as_bool(row.get("run_valid", ""))
        and as_bool(row.get("resource_valid", ""))
        and as_bool(row.get("speed_limit_valid", ""))
        and as_bool(row.get("perf_window_valid", ""))
        and as_bool(row.get("cgroup_cpu_accounting", ""))
        and not row.get("cgroup_accounting_error", "").strip()
        and not as_bool(row.get("infrastructure_failure", ""))
        and as_int(row.get("attempt_count", "")) == 1
        and as_int(row.get("retry_count", "")) == 0
        and as_int(row.get("resource_guard_abort_count", "")) == 0
        and as_int(row.get("oom_kill_delta", "")) == 0
    ]
    filtered_rows = [row for row in rows if row["mode"] != "full"]
    probe_rows = [
        row
        for row in filtered_rows
        if as_bool(row.get("filter_static_probe_enabled", ""))
        and as_bool(row.get("filter_static_probe_input_seen", ""))
        and as_int(row.get("filter_static_probe_first_point_count", "")) > 0
    ]

    map_rows: list[dict] = []
    for tier in range(1, 6):
        for visibility in VISIBILITIES:
            map_name = f"occ_p_r{tier}_{visibility}"
            for mode in MODES:
                row = indexed[(map_name, mode)]
                map_rows.append(
                    {
                        "radius_tier": tier,
                        "visibility": visibility,
                        "map": map_name,
                        "mode": mode,
                        "complete": int(as_bool(row["success"])),
                        "contact_events": as_int(row["safety_collisions"]),
                        "static_clearance_m": as_float(
                            row["static_pcd_clearance_m"]
                        ),
                        "mission_time_s": as_float(row["mission_time_s"]),
                        "probe_seen": (
                            "" if mode == "full" else
                            int(as_bool(row["filter_static_probe_input_seen"]))
                        ),
                        "probe_progress_m": (
                            "" if mode == "full" else round(progress(row), 6)
                        ),
                        "probe_distance_m": (
                            "" if mode == "full" else as_float(
                                row[
                                    "filter_static_probe_first_horizontal_distance_m"
                                ]
                            )
                        ),
                        "probe_center_in_sector": (
                            "" if mode == "full" else int(
                                as_bool(
                                    row[
                                        "filter_static_probe_first_center_in_sector"
                                    ]
                                )
                            )
                        ),
                        "effective_full_opens": (
                            as_int(row.get("filter_effective_full_open_transitions"))
                            if mode == "adaptive" else 0
                        ),
                        "trajectory_guard_opens": (
                            as_int(row.get("filter_trajectory_guard_open_transitions"))
                            if mode == "adaptive" else 0
                        ),
                        "planner_ingress_mib_s": as_float(
                            row["planner_ingress_payload_mib_s"]
                        ),
                        "map_compute_ms_per_frame": as_float(
                            row["total_ms_mean"]
                        ),
                        "end_to_end_cores_mean": as_float(
                            row["end_to_end_cpu_cores_mean"]
                        ),
                        "end_to_end_core_s": as_float(
                            row["end_to_end_cpu_core_s"]
                        ),
                    }
                )

    pair_rows: list[dict] = []
    desired_binary = 0
    desired_sector_contacts = 0
    reverse_binary = 0
    clearance_differences: list[float] = []
    improved_guard_ok = True
    for tier in range(1, 6):
        means = {}
        for visibility in VISIBILITIES:
            means[visibility] = statistics.mean(
                progress(indexed[(f"occ_p_r{tier}_{visibility}", mode)])
                for mode in ("sector", "adaptive")
            )
        sector = indexed[(f"occ_p_r{tier}_occ", "sector")]
        adaptive = indexed[(f"occ_p_r{tier}_occ", "adaptive")]
        sector_bad = not safe(sector)
        adaptive_bad = not safe(adaptive)
        if sector_bad and not adaptive_bad:
            desired_binary += 1
            if as_int(sector["safety_collisions"]) > 0:
                desired_sector_contacts += 1
        if adaptive_bad and not sector_bad:
            reverse_binary += 1
        clearance_difference = as_float(
            adaptive["static_pcd_clearance_m"]
        ) - as_float(sector["static_pcd_clearance_m"])
        clearance_differences.append(clearance_difference)
        guard_opens = as_int(
            adaptive["filter_trajectory_guard_open_transitions"]
        )
        if clearance_difference > 0.0 and guard_opens <= 0:
            improved_guard_ok = False
        pair_rows.append(
            {
                "radius_tier": tier,
                "nominal_probe_progress_mean_m": round(means["nom"], 6),
                "occluded_probe_progress_mean_m": round(means["occ"], 6),
                "occlusion_delay_m": round(means["occ"] - means["nom"], 6),
                "sector_complete": int(as_bool(sector["success"])),
                "sector_contacts": as_int(sector["safety_collisions"]),
                "sector_clearance_m": as_float(
                    sector["static_pcd_clearance_m"]
                ),
                "adaptive_complete": int(as_bool(adaptive["success"])),
                "adaptive_contacts": as_int(adaptive["safety_collisions"]),
                "adaptive_clearance_m": as_float(
                    adaptive["static_pcd_clearance_m"]
                ),
                "adaptive_minus_sector_clearance_m": round(
                    clearance_difference, 6
                ),
                "adaptive_effective_full_opens": as_int(
                    adaptive["filter_effective_full_open_transitions"]
                ),
                "adaptive_trajectory_guard_opens": guard_opens,
            }
        )

    all_keys_valid = observed == expected and len(rows) == len(expected)
    validity_gate = (
        all_keys_valid
        and len(quality_rows) == 30
        and len(probe_rows) == 20
    )
    protected_gate = all(
        safe(row) for row in rows if row["mode"] in ("full", "adaptive")
    )
    delivery_gate = all(item["occlusion_delay_m"] >= 2.0 for item in pair_rows)
    no_reverse_gate = reverse_binary == 0
    binary_discrimination_gate = (
        desired_binary >= 2 and desired_sector_contacts >= 1
    )
    improved_count = sum(value > 0.0 for value in clearance_differences)
    median_improvement = statistics.median(clearance_differences)
    clearance_discrimination_gate = (
        improved_count >= 4
        and median_improvement >= 0.10
        and improved_guard_ok
    )
    discrimination_gate = (
        binary_discrimination_gate or clearance_discrimination_gate
    )
    expansion_gate = all(
        (
            validity_gate,
            protected_gate,
            delivery_gate,
            no_reverse_gate,
            discrimination_gate,
        )
    )

    result = {
        "campaign": str(campaign),
        "expected_rows": 30,
        "observed_rows": len(rows),
        "unique_keys": len(observed),
        "quality_valid_rows": len(quality_rows),
        "probe_valid_rows": len(probe_rows),
        "protected_full_adaptive_safe_rows": sum(
            safe(row)
            for row in rows
            if row["mode"] in ("full", "adaptive")
        ),
        "desired_binary_discordances": desired_binary,
        "desired_sector_contact_discordances": desired_sector_contacts,
        "reverse_binary_discordances": reverse_binary,
        "adaptive_clearance_improved_strata": improved_count,
        "adaptive_minus_sector_clearance_median_m": round(
            median_improvement, 6
        ),
        "gates": {
            "validity": validity_gate,
            "protected_modes": protected_gate,
            "physical_occlusion_delivery": delivery_gate,
            "no_reverse_discordance": no_reverse_gate,
            "binary_discrimination": binary_discrimination_gate,
            "clearance_discrimination": clearance_discrimination_gate,
            "discrimination_either_route": discrimination_gate,
            "expand_to_independent_80_maps": expansion_gate,
        },
        "decision": (
            "EXPAND_TO_INDEPENDENT_CONFIRMATORY_80_MAPS"
            if expansion_gate
            else "STOP_AFTER_PILOT_NO_CONFIRMATORY_EXPANSION"
        ),
    }

    prefix.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        Path(str(prefix) + "_map_table.csv"),
        list(map_rows[0]),
        map_rows,
    )
    write_csv(
        Path(str(prefix) + "_pair_table.csv"),
        list(pair_rows[0]),
        pair_rows,
    )
    Path(str(prefix) + "_gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.campaign, args.prefix)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
