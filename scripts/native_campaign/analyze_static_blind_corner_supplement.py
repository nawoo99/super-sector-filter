#!/usr/bin/env python3
"""Validate and summarize the frozen 150-row blind-corner supplement."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


MAPS = tuple(f"occ_b_r{tier}" for tier in range(1, 6))
MODES = ("full", "sector", "adaptive")
RUNS = tuple(range(1, 11))


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


def values(rows: list[dict[str, str]], field: str) -> list[float]:
    result = []
    for row in rows:
        raw = row.get(field, "")
        if raw != "":
            result.append(float(raw))
    return result


def safe(row: dict[str, str]) -> bool:
    return as_bool(row["success"]) and as_int(row["safety_collisions"]) == 0


def quality_valid(row: dict[str, str]) -> bool:
    return (
        as_bool(row.get("run_valid", ""))
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
    )


def mean(rows: list[dict[str, str]], field: str) -> float | None:
    data = values(rows, field)
    return statistics.fmean(data) if data else None


def median(rows: list[dict[str, str]], field: str) -> float | None:
    data = values(rows, field)
    return statistics.median(data) if data else None


def minimum(rows: list[dict[str, str]], field: str) -> float | None:
    data = values(rows, field)
    return min(data) if data else None


def rounded(value: float | None, digits: int = 6):
    return "" if value is None else round(value, digits)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(campaign: Path, prefix: Path) -> dict:
    with campaign.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    indexed = {
        (row["map"], as_int(row["run"]), row["mode"]): row for row in rows
    }
    expected = {
        (map_name, run, mode)
        for map_name in MAPS
        for run in RUNS
        for mode in MODES
    }
    if len(rows) != len(expected) or set(indexed) != expected:
        raise ValueError(
            f"expected 150 exact unique keys, got rows={len(rows)} "
            f"unique={len(indexed)}"
        )

    map_rows: list[dict] = []
    for tier, map_name in enumerate(MAPS, start=1):
        for mode in MODES:
            cell = [indexed[(map_name, run, mode)] for run in RUNS]
            contacts = [as_int(row["safety_collisions"]) for row in cell]
            hazard_contacts = [
                as_int(row["static_hazard_collisions"]) for row in cell
            ]
            probe_valid = [
                row for row in cell
                if as_bool(row.get("filter_static_probe_enabled", ""))
                and as_bool(row.get("filter_static_probe_input_seen", ""))
                and as_int(row.get("filter_static_probe_first_point_count", "")) > 0
            ]
            map_rows.append(
                {
                    "radius_tier": tier,
                    "map": map_name,
                    "mode": mode,
                    "n": len(cell),
                    "complete": sum(as_bool(row["success"]) for row in cell),
                    "authoritative_contact_runs": sum(value > 0 for value in contacts),
                    "authoritative_contact_events": sum(contacts),
                    "hazard_contact_runs": sum(value > 0 for value in hazard_contacts),
                    "hazard_contact_events": sum(hazard_contacts),
                    "mission_time_mean_s": rounded(mean(cell, "mission_time_s"), 3),
                    "mission_time_median_s": rounded(median(cell, "mission_time_s"), 3),
                    "global_clearance_median_m": rounded(
                        median(cell, "static_pcd_clearance_m"), 3
                    ),
                    "global_clearance_min_m": rounded(
                        minimum(cell, "static_pcd_clearance_m"), 3
                    ),
                    "hazard_clearance_median_m": rounded(
                        median(cell, "static_hazard_min_clearance_m"), 3
                    ),
                    "hazard_clearance_min_m": rounded(
                        minimum(cell, "static_hazard_min_clearance_m"), 3
                    ),
                    "probe_valid": len(probe_valid),
                    "probe_distance_median_m": rounded(
                        median(
                            probe_valid,
                            "filter_static_probe_first_horizontal_distance_m",
                        ),
                        3,
                    ),
                    "probe_center_outside_count": sum(
                        not as_bool(
                            row.get("filter_static_probe_first_center_in_sector", "")
                        )
                        for row in probe_valid
                    ),
                    "effective_full_opens": sum(
                        as_int(row.get("filter_effective_full_open_transitions", ""))
                        for row in cell
                    ),
                    "trajectory_guard_opens": sum(
                        as_int(row.get("filter_trajectory_guard_open_transitions", ""))
                        for row in cell
                    ),
                    "trajectory_guard_active_runs": sum(
                        as_int(row.get("filter_trajectory_guard_open_transitions", "")) > 0
                        for row in cell
                    ),
                    "planner_ingress_mib_s_mean": rounded(
                        mean(cell, "planner_ingress_mib_s"), 6
                    ),
                    "map_compute_ms_per_frame_mean": rounded(
                        mean(cell, "map_compute_ms_per_frame"), 6
                    ),
                    "end_to_end_cores_mean": rounded(
                        mean(cell, "end_to_end_cores_mean"), 6
                    ),
                    "end_to_end_core_s_mean": rounded(
                        mean(cell, "end_to_end_core_s"), 6
                    ),
                    "end_to_end_peak_pss_mib_mean": rounded(
                        mean(cell, "end_to_end_peak_pss_mib"), 3
                    ),
                }
            )

    pair_rows: list[dict] = []
    desired = 0
    reverse = 0
    desired_maps: set[str] = set()
    map_clearance_advantages: list[float] = []
    map_clearance_wins = 0
    for tier, map_name in enumerate(MAPS, start=1):
        run_differences = []
        map_desired = 0
        map_reverse = 0
        for run in RUNS:
            sector = indexed[(map_name, run, "sector")]
            adaptive = indexed[(map_name, run, "adaptive")]
            sector_bad = not safe(sector)
            adaptive_bad = not safe(adaptive)
            if sector_bad and not adaptive_bad:
                desired += 1
                map_desired += 1
                desired_maps.add(map_name)
            if adaptive_bad and not sector_bad:
                reverse += 1
                map_reverse += 1
            run_differences.append(
                as_float(adaptive["static_hazard_min_clearance_m"])
                - as_float(sector["static_hazard_min_clearance_m"])
            )
        map_advantage = statistics.median(run_differences)
        map_clearance_advantages.append(map_advantage)
        if map_advantage > 0.0:
            map_clearance_wins += 1
        sector_rows = [indexed[(map_name, run, "sector")] for run in RUNS]
        adaptive_rows = [indexed[(map_name, run, "adaptive")] for run in RUNS]
        pair_rows.append(
            {
                "radius_tier": tier,
                "map": map_name,
                "desired_sector_bad_adaptive_safe": map_desired,
                "reverse_adaptive_bad_sector_safe": map_reverse,
                "sector_completion": sum(
                    as_bool(row["success"]) for row in sector_rows
                ),
                "adaptive_completion": sum(
                    as_bool(row["success"]) for row in adaptive_rows
                ),
                "sector_contact_runs": sum(
                    as_int(row["safety_collisions"]) > 0 for row in sector_rows
                ),
                "adaptive_contact_runs": sum(
                    as_int(row["safety_collisions"]) > 0 for row in adaptive_rows
                ),
                "sector_hazard_clearance_median_m": rounded(
                    median(sector_rows, "static_hazard_min_clearance_m"), 3
                ),
                "adaptive_hazard_clearance_median_m": rounded(
                    median(adaptive_rows, "static_hazard_min_clearance_m"), 3
                ),
                "adaptive_minus_sector_hazard_clearance_median_m": round(
                    map_advantage, 3
                ),
                "sector_probe_distance_median_m": rounded(
                    median(
                        sector_rows,
                        "filter_static_probe_first_horizontal_distance_m",
                    ),
                    3,
                ),
                "adaptive_probe_distance_median_m": rounded(
                    median(
                        adaptive_rows,
                        "filter_static_probe_first_horizontal_distance_m",
                    ),
                    3,
                ),
                "sector_probe_center_outside": sum(
                    not as_bool(
                        row["filter_static_probe_first_center_in_sector"]
                    )
                    for row in sector_rows
                ),
                "adaptive_trajectory_guard_active_runs": sum(
                    as_int(row["filter_trajectory_guard_open_transitions"]) > 0
                    for row in adaptive_rows
                ),
                "adaptive_effective_full_opens": sum(
                    as_int(row["filter_effective_full_open_transitions"])
                    for row in adaptive_rows
                ),
                "adaptive_trajectory_guard_opens": sum(
                    as_int(row["filter_trajectory_guard_open_transitions"])
                    for row in adaptive_rows
                ),
            }
        )

    quality_count = sum(quality_valid(row) for row in rows)
    probe_rows = [
        row for row in rows if row["mode"] != "full"
        and as_bool(row.get("filter_static_probe_enabled", ""))
        and as_bool(row.get("filter_static_probe_input_seen", ""))
        and as_int(row.get("filter_static_probe_first_point_count", "")) > 0
    ]
    hazard_rows = [
        row for row in rows
        if as_bool(row.get("static_hazard_enabled", ""))
        and abs(as_float(row.get("static_hazard_center_x")) - 18.8) < 1e-9
        and abs(as_float(row.get("static_hazard_center_y")) - 24.0) < 1e-9
        and abs(as_float(row.get("static_hazard_radius_m")) - 0.95) < 1e-9
        and abs(as_float(row.get("static_hazard_height_m")) - 3.2) < 1e-9
        and row.get("static_hazard_min_clearance_m", "") != ""
    ]
    validity = quality_count == 150 and len(probe_rows) == 100 and len(hazard_rows) == 150
    protected = all(
        safe(row) for row in rows if row["mode"] in ("full", "adaptive")
    )
    delivery_by_map = []
    for map_name in MAPS:
        sector = [indexed[(map_name, run, "sector")] for run in RUNS]
        adaptive = [indexed[(map_name, run, "adaptive")] for run in RUNS]
        distances = values(
            sector + adaptive,
            "filter_static_probe_first_horizontal_distance_m",
        )
        delivery_by_map.append(
            len(distances) == 20
            and 2.5 <= statistics.median(distances) <= 5.5
            and sum(
                not as_bool(row["filter_static_probe_first_center_in_sector"])
                for row in sector
            ) >= 8
            and sum(
                as_int(row["filter_trajectory_guard_open_transitions"]) > 0
                for row in adaptive
            ) >= 8
        )
    delivery = all(delivery_by_map)
    no_reverse = reverse == 0
    binary_separation = desired >= 5 and len(desired_maps) >= 2
    clearance_median = statistics.median(map_clearance_advantages)
    clearance_separation = map_clearance_wins >= 4 and clearance_median >= 0.10
    safety_separation = binary_separation or clearance_separation

    if not validity:
        decision = "SUPPLEMENT_INVALID_MEASUREMENT"
    elif not protected:
        decision = "SUPPLEMENT_PROTECTED_MODE_FAILURE"
    elif delivery and no_reverse and safety_separation:
        decision = "SUPPLEMENT_PASS_SAFETY_SEPARATION"
    else:
        decision = "SUPPLEMENT_COMPLETE_NO_SAFETY_SEPARATION"

    map_fields = list(map_rows[0])
    pair_fields = list(pair_rows[0])
    write_csv(Path(f"{prefix}_map_table.csv"), map_fields, map_rows)
    write_csv(Path(f"{prefix}_pair_table.csv"), pair_fields, pair_rows)
    gate = {
        "campaign": str(campaign),
        "expected_rows": 150,
        "observed_rows": len(rows),
        "unique_keys": len(indexed),
        "quality_valid_rows": quality_count,
        "probe_valid_rows": len(probe_rows),
        "hazard_metric_valid_rows": len(hazard_rows),
        "protected_full_adaptive_safe_rows": sum(
            safe(row) for row in rows if row["mode"] in ("full", "adaptive")
        ),
        "desired_binary_discordances": desired,
        "desired_discordant_maps": len(desired_maps),
        "reverse_binary_discordances": reverse,
        "adaptive_clearance_improved_maps": map_clearance_wins,
        "adaptive_minus_sector_map_median_clearance_median_m": round(
            clearance_median, 6
        ),
        "gates": {
            "validity": validity,
            "protected_modes": protected,
            "physical_delivery": delivery,
            "no_reverse_discordance": no_reverse,
            "binary_separation": binary_separation,
            "clearance_separation": clearance_separation,
            "safety_separation_either_route": safety_separation,
        },
        "decision": decision,
    }
    Path(f"{prefix}_gate.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    return gate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.campaign, args.prefix), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
