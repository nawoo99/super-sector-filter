#!/usr/bin/env python3
"""Summarize paired full_control_v10 versus full_shadow_v10 runs."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict


CONTROL = "full_control_v10"
SHADOW = "full_shadow_v10"
CONTINUOUS = (
    "mission_time_s",
    "path_length_m",
    "fsm_cpu_pct",
    "monitor_cpu_pct",
    "total_ms_mean",
    "raycast_ms_mean",
    "update_ms_mean",
    "inflation_ms_mean",
)


def optional_float(value):
    if value is None or str(value).strip() == "":
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def required_bool(value, field):
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"{field} must be True or False, got {value!r}")


def load_pairs(path):
    grouped = defaultdict(dict)
    order = defaultdict(list)
    with open(path, newline="") as stream:
        for row in csv.DictReader(stream):
            mode = row.get("mode")
            if mode not in (CONTROL, SHADOW):
                continue
            key = (row.get("map"), row.get("run"))
            if mode in grouped[key]:
                raise ValueError(f"duplicate {mode} for pair {key}")
            grouped[key][mode] = row
            order[key].append(mode)
    incomplete = [key for key, arms in grouped.items() if set(arms) != {CONTROL, SHADOW}]
    if incomplete:
        raise ValueError(f"incomplete A/B pairs: {incomplete}")
    if not grouped:
        raise ValueError("no full_control_v10/full_shadow_v10 pairs found")
    return [(key, grouped[key][CONTROL], grouped[key][SHADOW], order[key])
            for key in sorted(grouped)]


def summarize(path):
    pairs = load_pairs(path)
    pair_rows = []
    for (map_name, run), control, shadow, order in pairs:
        output = {
            "map": map_name,
            "run": run,
            "order": "control_shadow" if order[0] == CONTROL else "shadow_control",
        }
        for name in CONTINUOUS:
            a = optional_float(control.get(name))
            b = optional_float(shadow.get(name))
            output[f"control_{name}"] = a
            output[f"shadow_{name}"] = b
            output[f"delta_{name}"] = b - a if a is not None and b is not None else None
        for name in ("success", "contact_event_count"):
            if name == "success":
                a = required_bool(control.get(name), name)
                b = required_bool(shadow.get(name), name)
            else:
                a = int(float(control.get(name) or 0))
                b = int(float(shadow.get(name) or 0))
            output[f"control_{name}"] = a
            output[f"shadow_{name}"] = b
            output[f"delta_{name}"] = int(b) - int(a)
        pair_rows.append(output)

    summary = {"n_pairs": len(pair_rows)}
    summary["n_control_first"] = sum(row["order"] == "control_shadow" for row in pair_rows)
    summary["n_shadow_first"] = len(pair_rows) - summary["n_control_first"]
    for name in CONTINUOUS:
        control_values = [row[f"control_{name}"] for row in pair_rows
                          if row[f"control_{name}"] is not None]
        shadow_values = [row[f"shadow_{name}"] for row in pair_rows
                         if row[f"shadow_{name}"] is not None]
        values = [row[f"delta_{name}"] for row in pair_rows
                  if row[f"delta_{name}"] is not None]
        summary[f"control_{name}_mean"] = (
            statistics.mean(control_values) if control_values else None
        )
        summary[f"shadow_{name}_mean"] = (
            statistics.mean(shadow_values) if shadow_values else None
        )
        summary[f"delta_{name}_n"] = len(values)
        summary[f"delta_{name}_mean"] = statistics.mean(values) if values else None
        summary[f"delta_{name}_median"] = statistics.median(values) if values else None
    summary["control_successes"] = sum(row["control_success"] for row in pair_rows)
    summary["shadow_successes"] = sum(row["shadow_success"] for row in pair_rows)
    summary["control_contacts"] = sum(row["control_contact_event_count"] for row in pair_rows)
    summary["shadow_contacts"] = sum(row["shadow_contact_event_count"] for row in pair_rows)
    return pair_rows, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign")
    parser.add_argument("--pairs-out")
    parser.add_argument("--summary-out")
    args = parser.parse_args()
    pair_rows, summary = summarize(args.campaign)
    if args.pairs_out:
        with open(args.pairs_out, "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(pair_rows[0]))
            writer.writeheader()
            writer.writerows(pair_rows)
    if args.summary_out:
        with open(args.summary_out, "w") as stream:
            json.dump(summary, stream, indent=2)
            stream.write("\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
