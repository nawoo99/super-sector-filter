#!/usr/bin/env python3
"""Audit deployed brake-motion decisions and campaign integrity."""

import argparse
import csv
import glob
import json
import math
import os
import re


MOTION = re.compile(
    r"motion_pose_speed=([^ ]+) motion_twist_speed=([^ ]+) "
    r"motion_disagreement=([^ ]+) motion_source=([^ ]+) "
    r"motion_gen=([^ ]+) motion_gen_continuous=([^ ]+)"
)


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    return parser.parse_args()


def yes(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def finite(value):
    try:
        parsed = float(value.rstrip(";"))
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def main():
    options = args()
    with open(options.campaign, newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = {(row["map"], row["run"], row["mode"]) for row in rows}
    failures = [
        row for row in rows
        if not yes(row["success"]) or not yes(row["run_valid"])
        or yes(row["infrastructure_failure"])
        or not yes(row["resource_valid"])
    ]
    static_contact_rows = {
        mode: sum(
            float(row.get("static_pcd_collisions") or 0.0) > 0.0
            for row in rows if row["mode"] == mode
        )
        for mode in ("full", "sector", "adaptive")
    }
    reference_contact_violations = (
        static_contact_rows["full"] + static_contact_rows["adaptive"]
    )
    sources = {}
    motion_records = 0
    stationary_conflicts = 0
    stationary_conflict_odom = 0
    discontinuous_odom = 0
    logs = sorted(glob.glob(os.path.join(
        options.artifacts_dir, "*.attempt1.stack.log"
    )))
    for path in logs:
        with open(path, errors="replace") as stream:
            for line in stream:
                match = MOTION.search(line)
                if not match:
                    continue
                motion_records += 1
                pose = finite(match.group(1))
                twist = finite(match.group(2))
                source = match.group(4).rstrip(";")
                continuous = match.group(6).rstrip(";") == "true"
                sources[source] = sources.get(source, 0) + 1
                if pose is not None and twist is not None \
                        and pose <= 0.05 and twist > 0.05:
                    stationary_conflicts += 1
                    if source == "odom_twist":
                        stationary_conflict_odom += 1
                if source == "odom_twist" and not continuous:
                    discontinuous_odom += 1
    passed = (
        len(rows) == options.expected_rows
        and len(keys) == options.expected_rows
        and not failures
        and reference_contact_violations == 0
        and stationary_conflict_odom == 0
        and discontinuous_odom == 0
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "campaign": options.campaign,
        "expected_rows": options.expected_rows,
        "observed_rows": len(rows),
        "unique_rows": len(keys),
        "quality_failures": len(failures),
        "static_contact_rows_by_mode": static_contact_rows,
        "full_adaptive_static_contact_violations": (
            reference_contact_violations
        ),
        "attempt1_logs": len(logs),
        "motion_records": motion_records,
        "motion_sources": sources,
        "stationary_conflicts": stationary_conflicts,
        "stationary_conflict_odom_violations": stationary_conflict_odom,
        "discontinuous_odom_violations": discontinuous_odom,
    }
    with open(options.out, "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
