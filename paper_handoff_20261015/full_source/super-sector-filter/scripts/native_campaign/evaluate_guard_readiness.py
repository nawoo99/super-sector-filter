#!/usr/bin/env python3
"""Fail-closed gate for promoting shadow trajectory checks to enforcement."""

import argparse
import csv
import json


def load_campaigns(paths):
    rows = []
    for path in paths:
        with open(path, newline="") as stream:
            rows.extend(csv.DictReader(stream))
    return rows


def integer(row, name):
    value = row.get(name)
    return int(float(value)) if value not in (None, "") else 0


def evaluate(rate_ab_summary, dense_campaign_paths, dense_ab_summary=None):
    dense_rows = load_campaigns(dense_campaign_paths)
    dense_contacts = sum(integer(row, "shadow_contact_events_with_epoch")
                         for row in dense_rows)
    dense_matched = sum(integer(row, "shadow_contacts_with_prior_unsafe")
                        for row in dense_rows)
    dense_map_races = sum(integer(row, "shadow_map_race") for row in dense_rows)
    dense_recall = dense_matched / dense_contacts if dense_contacts else None
    dense_safe = sum(integer(row, "shadow_safe_candidates")
                     for row in dense_rows)
    dense_validated = sum(integer(row, "shadow_validated_candidates")
                          for row in dense_rows)
    dense_safe_fraction = (
        dense_safe / dense_validated if dense_validated else None
    )

    rate_pairs = int(rate_ab_summary.get("n_pairs", 0))
    rate_cpu_delta = rate_ab_summary.get("delta_fsm_cpu_pct_median")
    control_time = rate_ab_summary.get("control_mission_time_s_mean")
    mission_delta = rate_ab_summary.get("delta_mission_time_s_median")
    mission_overhead_pct = (
        100.0 * mission_delta / control_time
        if control_time not in (None, 0) and mission_delta is not None else None
    )

    checks = [
        {"name": "map_snapshot_races_zero", "passed": dense_map_races == 0,
         "value": dense_map_races, "requirement": "0"},
        {"name": "rate_limited_ab_pairs", "passed": rate_pairs >= 4,
         "value": rate_pairs, "requirement": ">=4"},
        {"name": "rate_limited_cpu_delta_median_pct_points",
         "passed": rate_cpu_delta is not None and rate_cpu_delta <= 5.0,
         "value": rate_cpu_delta, "requirement": "<=5.0"},
        {"name": "rate_limited_mission_overhead_pct",
         "passed": mission_overhead_pct is not None and mission_overhead_pct <= 5.0,
         "value": mission_overhead_pct, "requirement": "<=5.0"},
        {"name": "dense_contact_events",
         "passed": dense_contacts >= 20,
         "value": dense_contacts, "requirement": ">=20"},
        {"name": "dense_contact_recall",
         "passed": dense_recall is not None and dense_recall >= 0.95,
         "value": dense_recall, "requirement": ">=0.95"},
        {"name": "dense_safe_candidate_fraction",
         "passed": dense_safe_fraction is not None and
                   dense_safe_fraction >= 0.50,
         "value": dense_safe_fraction,
         "requirement": ">=0.50 (operational anti-stall floor)"},
        {"name": "dense_paired_ab_available",
         "passed": dense_ab_summary is not None and
                   int(dense_ab_summary.get("n_pairs", 0)) >= 10,
         "value": (None if dense_ab_summary is None
                   else dense_ab_summary.get("n_pairs")),
         "requirement": ">=10 pairs"},
    ]
    if dense_ab_summary is not None:
        dense_cpu = dense_ab_summary.get("delta_fsm_cpu_pct_median")
        dense_pairs = int(dense_ab_summary.get("n_pairs", 0))
        control_successes = int(dense_ab_summary.get("control_successes", 0))
        shadow_successes = int(dense_ab_summary.get("shadow_successes", 0))
        checks.append({
            "name": "dense_cpu_delta_median_pct_points",
            "passed": dense_cpu is not None and dense_cpu <= 10.0,
            "value": dense_cpu,
            "requirement": "<=10.0",
        })
        checks.append({
            "name": "dense_shadow_all_complete",
            "passed": dense_pairs >= 10 and shadow_successes == dense_pairs,
            "value": f"{shadow_successes}/{dense_pairs}",
            "requirement": "all paired shadow runs complete",
        })
        checks.append({
            "name": "dense_completion_parity",
            "passed": shadow_successes >= control_successes,
            "value": f"shadow={shadow_successes},control={control_successes}",
            "requirement": "shadow >= control",
        })
    return {
        "ready_for_enforcement": all(check["passed"] for check in checks),
        "checks": checks,
        "decision": (
            "proceed_to_enforcement_smoke"
            if all(check["passed"] for check in checks)
            else "keep_shadow_only"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-ab-summary", required=True)
    parser.add_argument("--dense-contact-campaign", action="append", required=True)
    parser.add_argument("--dense-ab-summary")
    parser.add_argument("--out")
    args = parser.parse_args()
    with open(args.rate_ab_summary) as stream:
        rate_summary = json.load(stream)
    dense_summary = None
    if args.dense_ab_summary:
        with open(args.dense_ab_summary) as stream:
            dense_summary = json.load(stream)
    result = evaluate(rate_summary, args.dense_contact_campaign, dense_summary)
    output = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as stream:
            stream.write(output + "\n")
    print(output)
    raise SystemExit(0 if result["ready_for_enforcement"] else 2)


if __name__ == "__main__":
    main()
