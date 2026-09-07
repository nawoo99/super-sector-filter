#!/usr/bin/env python3
"""Create compact map-labelled summaries for a frozen side-entry campaign."""

import argparse
import csv
import math
import statistics


MODES = ("full", "sector", "adaptive")
METRICS = (
    ("mission_time_s", "mission_time_s"),
    ("side_entry_clearance_m", "side_entry_v1_min_clearance_m"),
    ("planner_ingress_mib_s", "planner_ingress_payload_mib_s"),
    ("map_compute_ms_per_frame", "total_ms_mean"),
    ("algorithm_cores_mean", "algorithm_cpu_cores_mean"),
    ("end_to_end_cores_mean", "end_to_end_cpu_cores_mean"),
)


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--maps", nargs="+", required=True)
    parser.add_argument("--runs", type=int, required=True)
    return parser.parse_args()


def yes(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def number(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {row}")
    return value


def optional_number(row, key, default=0.0):
    value = row.get(key)
    if value in (None, ""):
        return default
    return number(row, key)


def mean(rows, key):
    return statistics.mean(number(row, key) for row in rows)


def reduction(reference, treatment):
    return None if reference == 0.0 else 100.0 * (reference - treatment) / reference


def main():
    options = args()
    with open(options.campaign, newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {
        (map_name, str(run), mode)
        for map_name in options.maps
        for run in range(1, options.runs + 1)
        for mode in MODES
    }
    observed = {(row["map"], row["run"], row["mode"]) for row in rows}
    if len(rows) != len(expected) or observed != expected:
        raise ValueError(
            f"scope mismatch: rows={len(rows)}, expected={len(expected)}, "
            f"missing={sorted(expected-observed)}, extra={sorted(observed-expected)}"
        )
    for row in rows:
        if int(row["side_entry_scenario_version"]) != options.version:
            raise ValueError("mixed scenario versions")
        if not yes(row["run_valid"]):
            raise ValueError(
                f"invalid row: {row['map']}/{row['run']}/{row['mode']}"
            )

    summary_fields = [
        "map", "mode", "n", "complete", "completion_pct",
        "static_contact_runs", "side_entry_contact_runs",
        "overall_contact_runs", "event_valid_count", "retry_total",
        "mission_time_mean_s", "mission_time_min_s", "mission_time_max_s",
        "side_entry_clearance_mean_m", "side_entry_clearance_min_m",
        "planner_ingress_mib_s", "map_compute_ms_per_frame",
        "algorithm_cores_mean", "end_to_end_cores_mean",
        "effective_full_open_total", "trajectory_guard_open_total",
    ]
    summary = []
    means = {}
    for map_name in options.maps:
        for mode in MODES:
            group = [
                row for row in rows
                if row["map"] == map_name and row["mode"] == mode
            ]
            complete = sum(yes(row["success"]) for row in group)
            static_contacts = sum(
                number(row, "static_pcd_collisions") > 0.0 for row in group
            )
            side_contacts = sum(
                yes(row["side_entry_v1_collision"]) for row in group
            )
            overall_contacts = sum(
                number(row, "static_pcd_collisions") > 0.0
                or yes(row["side_entry_v1_collision"])
                for row in group
            )
            metric_means = {name: mean(group, key) for name, key in METRICS}
            means[(map_name, mode)] = metric_means
            times = [number(row, "mission_time_s") for row in group]
            clearances = [
                number(row, "side_entry_v1_min_clearance_m") for row in group
            ]
            summary.append({
                "map": map_name,
                "mode": mode,
                "n": len(group),
                "complete": complete,
                "completion_pct": 100.0 * complete / len(group),
                "static_contact_runs": static_contacts,
                "side_entry_contact_runs": side_contacts,
                "overall_contact_runs": overall_contacts,
                "event_valid_count": sum(
                    yes(row["side_entry_v1_event_loaded"])
                    and yes(row["side_entry_v1_geometry_valid"])
                    for row in group
                ),
                "retry_total": sum(int(number(row, "retry_count")) for row in group),
                "mission_time_mean_s": statistics.mean(times),
                "mission_time_min_s": min(times),
                "mission_time_max_s": max(times),
                "side_entry_clearance_mean_m": statistics.mean(clearances),
                "side_entry_clearance_min_m": min(clearances),
                "planner_ingress_mib_s": metric_means["planner_ingress_mib_s"],
                "map_compute_ms_per_frame": metric_means["map_compute_ms_per_frame"],
                "algorithm_cores_mean": metric_means["algorithm_cores_mean"],
                "end_to_end_cores_mean": metric_means["end_to_end_cores_mean"],
                "effective_full_open_total": sum(
                    int(optional_number(
                        row, "filter_effective_full_open_transitions"
                    ))
                    for row in group
                ),
                "trajectory_guard_open_total": sum(
                    int(optional_number(
                        row, "filter_trajectory_guard_open_transitions"
                    ))
                    for row in group
                ),
            })

    summary_path = options.prefix + "_summary.csv"
    with open(summary_path, "w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=summary_fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(summary)

    reduction_fields = [
        "map", "metric", "full", "sector", "adaptive",
        "sector_vs_full_reduction_pct",
        "adaptive_vs_full_reduction_pct",
        "adaptive_vs_sector_reduction_pct",
    ]
    reductions = []
    for map_name in options.maps:
        for metric, _ in METRICS:
            values = {mode: means[(map_name, mode)][metric] for mode in MODES}
            reductions.append({
                "map": map_name,
                "metric": metric,
                **values,
                "sector_vs_full_reduction_pct": reduction(
                    values["full"], values["sector"]
                ),
                "adaptive_vs_full_reduction_pct": reduction(
                    values["full"], values["adaptive"]
                ),
                "adaptive_vs_sector_reduction_pct": reduction(
                    values["sector"], values["adaptive"]
                ),
            })
    for metric, key in METRICS:
        values = {
            mode: mean([row for row in rows if row["mode"] == mode], key)
            for mode in MODES
        }
        reductions.append({
            "map": "ALL",
            "metric": metric,
            **values,
            "sector_vs_full_reduction_pct": reduction(
                values["full"], values["sector"]
            ),
            "adaptive_vs_full_reduction_pct": reduction(
                values["full"], values["adaptive"]
            ),
            "adaptive_vs_sector_reduction_pct": reduction(
                values["sector"], values["adaptive"]
            ),
        })
    reductions_path = options.prefix + "_reductions.csv"
    with open(reductions_path, "w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=reduction_fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(reductions)

    print(summary_path)
    print(reductions_path)


if __name__ == "__main__":
    main()
