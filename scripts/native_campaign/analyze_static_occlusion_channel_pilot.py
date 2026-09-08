#!/usr/bin/env python3
"""Apply the frozen channelized static-occlusion pilot expansion gates."""

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
        (f"occ_c_r{tier}_{visibility}", mode)
        for tier in range(1, 6)
        for visibility in VISIBILITIES
        for mode in MODES
    }
    observed = set(indexed)
    if observed != expected or len(rows) != len(expected):
        raise ValueError(
            f"expected 30 exact keys, got rows={len(rows)} unique={len(observed)}"
        )

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
    hazard_rows = [
        row
        for row in rows
        if as_bool(row.get("static_hazard_enabled", ""))
        and abs(as_float(row.get("static_hazard_center_x")) - 18.0) < 1e-9
        and abs(as_float(row.get("static_hazard_center_y")) - 24.0) < 1e-9
        and abs(as_float(row.get("static_hazard_radius_m")) - 0.75) < 1e-9
        and abs(as_float(row.get("static_hazard_height_m")) - 3.2) < 1e-9
        and row.get("static_hazard_min_clearance_m", "") != ""
    ]

    map_rows: list[dict] = []
    for tier in range(1, 6):
        for visibility in VISIBILITIES:
            map_name = f"occ_c_r{tier}_{visibility}"
            for mode in MODES:
                row = indexed[(map_name, mode)]
                map_rows.append(
                    {
                        "radius_tier": tier,
                        "visibility": visibility,
                        "map": map_name,
                        "mode": mode,
                        "complete": int(as_bool(row["success"])),
                        "authoritative_contacts": as_int(
                            row["safety_collisions"]
                        ),
                        "global_static_clearance_m": as_float(
                            row["static_pcd_clearance_m"]
                        ),
                        "hazard_contacts": as_int(
                            row["static_hazard_collisions"]
                        ),
                        "hazard_clearance_m": as_float(
                            row["static_hazard_min_clearance_m"]
                        ),
                        "mission_time_s": as_float(row["mission_time_s"]),
                        "probe_seen": (
                            "" if mode == "full" else
                            int(as_bool(row["filter_static_probe_input_seen"]))
                        ),
                        "probe_progress_m": (
                            "" if mode == "full" else round(progress(row), 6)
                        ),
                        "probe_x_m": (
                            "" if mode == "full" else as_float(
                                row["filter_static_probe_first_drone_x"]
                            )
                        ),
                        "probe_y_m": (
                            "" if mode == "full" else as_float(
                                row["filter_static_probe_first_drone_y"]
                            )
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
                            as_int(row["filter_effective_full_open_transitions"])
                            if mode == "adaptive" else 0
                        ),
                        "trajectory_guard_opens": (
                            as_int(row["filter_trajectory_guard_open_transitions"])
                            if mode == "adaptive" else 0
                        ),
                    }
                )

    pair_rows: list[dict] = []
    desired_binary = 0
    desired_hazard_contacts = 0
    reverse_binary = 0
    occ_clearance_differences: list[float] = []
    clearance_dids: list[float] = []
    improved_guard_ok = True
    for tier in range(1, 6):
        values = {
            (visibility, mode): indexed[
                (f"occ_c_r{tier}_{visibility}", mode)
            ]
            for visibility in VISIBILITIES
            for mode in MODES
        }
        sector_nom = values[("nom", "sector")]
        sector_occ = values[("occ", "sector")]
        adaptive_nom = values[("nom", "adaptive")]
        adaptive_occ = values[("occ", "adaptive")]
        sector_delay = progress(sector_occ) - progress(sector_nom)
        adaptive_delay = progress(adaptive_occ) - progress(adaptive_nom)
        cross_policy_progress = abs(progress(sector_occ) - progress(adaptive_occ))
        sector_occ_bad = not safe(sector_occ)
        adaptive_occ_bad = not safe(adaptive_occ)
        if safe(sector_nom) and sector_occ_bad and not adaptive_occ_bad:
            desired_binary += 1
            if as_int(sector_occ["static_hazard_collisions"]) > 0:
                desired_hazard_contacts += 1
        if adaptive_occ_bad and not sector_occ_bad:
            reverse_binary += 1

        sector_nom_clearance = as_float(
            sector_nom["static_hazard_min_clearance_m"]
        )
        sector_occ_clearance = as_float(
            sector_occ["static_hazard_min_clearance_m"]
        )
        adaptive_nom_clearance = as_float(
            adaptive_nom["static_hazard_min_clearance_m"]
        )
        adaptive_occ_clearance = as_float(
            adaptive_occ["static_hazard_min_clearance_m"]
        )
        occ_difference = adaptive_occ_clearance - sector_occ_clearance
        did = occ_difference - (
            adaptive_nom_clearance - sector_nom_clearance
        )
        occ_clearance_differences.append(occ_difference)
        clearance_dids.append(did)
        guard_opens = as_int(
            adaptive_occ["filter_trajectory_guard_open_transitions"]
        )
        if occ_difference > 0.0 and guard_opens <= 0:
            improved_guard_ok = False

        pair_rows.append(
            {
                "radius_tier": tier,
                "sector_probe_delay_m": round(sector_delay, 6),
                "adaptive_probe_delay_m": round(adaptive_delay, 6),
                "occluded_probe_progress_difference_m": round(
                    cross_policy_progress, 6
                ),
                "sector_occluded_probe_distance_m": as_float(
                    sector_occ[
                        "filter_static_probe_first_horizontal_distance_m"
                    ]
                ),
                "adaptive_occluded_probe_distance_m": as_float(
                    adaptive_occ[
                        "filter_static_probe_first_horizontal_distance_m"
                    ]
                ),
                "sector_occluded_center_in_crop": int(
                    as_bool(
                        sector_occ[
                            "filter_static_probe_first_center_in_sector"
                        ]
                    )
                ),
                "sector_nominal_safe": int(safe(sector_nom)),
                "sector_occluded_safe": int(safe(sector_occ)),
                "adaptive_occluded_safe": int(safe(adaptive_occ)),
                "sector_occluded_hazard_contacts": as_int(
                    sector_occ["static_hazard_collisions"]
                ),
                "sector_nominal_hazard_clearance_m": sector_nom_clearance,
                "adaptive_nominal_hazard_clearance_m": adaptive_nom_clearance,
                "sector_occluded_hazard_clearance_m": sector_occ_clearance,
                "adaptive_occluded_hazard_clearance_m": adaptive_occ_clearance,
                "adaptive_minus_sector_occluded_hazard_clearance_m": round(
                    occ_difference, 6
                ),
                "hazard_clearance_difference_in_differences_m": round(did, 6),
                "adaptive_occluded_effective_full_opens": as_int(
                    adaptive_occ["filter_effective_full_open_transitions"]
                ),
                "adaptive_occluded_trajectory_guard_opens": guard_opens,
            }
        )

    validity_gate = (
        len(quality_rows) == 30
        and len(probe_rows) == 20
        and len(hazard_rows) == 30
    )
    protected_gate = all(
        safe(row) for row in rows if row["mode"] in ("full", "adaptive")
    )
    nominal_control_gate = all(
        safe(row) for row in rows if row["map"].endswith("_nom")
    )
    delivery_gate = all(
        item["sector_probe_delay_m"] >= 6.0
        and item["adaptive_probe_delay_m"] >= 6.0
        and item["occluded_probe_progress_difference_m"] <= 2.0
        and 3.5 <= item["sector_occluded_probe_distance_m"] <= 7.0
        and 3.5 <= item["adaptive_occluded_probe_distance_m"] <= 7.0
        and item["sector_occluded_center_in_crop"] == 0
        for item in pair_rows
    )
    no_reverse_gate = reverse_binary == 0
    binary_discrimination_gate = (
        desired_binary >= 2 and desired_hazard_contacts >= 1
    )
    improved_count = sum(value > 0.0 for value in occ_clearance_differences)
    median_improvement = statistics.median(occ_clearance_differences)
    median_did = statistics.median(clearance_dids)
    clearance_discrimination_gate = (
        improved_count >= 4
        and median_improvement >= 0.10
        and median_did >= 0.10
        and improved_guard_ok
    )
    discrimination_gate = (
        binary_discrimination_gate or clearance_discrimination_gate
    )
    expansion_gate = all(
        (
            validity_gate,
            protected_gate,
            nominal_control_gate,
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
        "hazard_metric_valid_rows": len(hazard_rows),
        "protected_full_adaptive_safe_rows": sum(
            safe(row)
            for row in rows
            if row["mode"] in ("full", "adaptive")
        ),
        "nominal_safe_rows": sum(
            safe(row) for row in rows if row["map"].endswith("_nom")
        ),
        "desired_binary_discordances": desired_binary,
        "desired_sector_hazard_contact_discordances": desired_hazard_contacts,
        "reverse_binary_discordances": reverse_binary,
        "adaptive_hazard_clearance_improved_strata": improved_count,
        "adaptive_minus_sector_occluded_hazard_clearance_median_m": round(
            median_improvement, 6
        ),
        "hazard_clearance_difference_in_differences_median_m": round(
            median_did, 6
        ),
        "gates": {
            "validity": validity_gate,
            "protected_modes": protected_gate,
            "nominal_all_modes_safe": nominal_control_gate,
            "channelized_occlusion_delivery": delivery_gate,
            "no_reverse_discordance": no_reverse_gate,
            "binary_discrimination": binary_discrimination_gate,
            "hazard_clearance_discrimination": clearance_discrimination_gate,
            "discrimination_either_route": discrimination_gate,
            "expand_to_independent_confirmatory_maps": expansion_gate,
        },
        "decision": (
            "EXPAND_TO_INDEPENDENT_CONFIRMATORY_MAPS"
            if expansion_gate
            else "STOP_AFTER_CHANNEL_PILOT_NO_CONFIRMATORY_EXPANSION"
        ),
    }

    prefix.parent.mkdir(parents=True, exist_ok=True)
    write_csv(Path(str(prefix) + "_map_table.csv"), list(map_rows[0]), map_rows)
    write_csv(
        Path(str(prefix) + "_pair_table.csv"), list(pair_rows[0]), pair_rows
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
