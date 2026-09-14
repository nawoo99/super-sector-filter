#!/usr/bin/env python3
"""Descriptive ledger of pre-launch SOLID-observer flights; no old-row pooling."""
import csv
import json
from statistics import mean

import cylinder_solid_campaign as campaign
import confirm_cylinder_search_n20 as confirmation
from analyze_cylinder_only_stress_full_gate import boolean, integer, quality_valid


def summarize(rows):
    modes = []
    for mode in confirmation.MODES:
        group = [r for r in rows if r["mode"] == mode]
        if not group:
            continue
        modes.append(dict(mode=mode, n=len(group),
                          complete=sum(boolean(r["success"]) for r in group),
                          solid_contact_trials=sum(integer(r,"solid_collision_episodes") > 0 for r in group),
                          solid_contact_episodes=sum(max(0, integer(r,"solid_collision_episodes")) for r in group),
                          safe_complete=sum(confirmation.safe(r) for r in group),
                          valid=sum(quality_valid(r) and confirmation.known_outcome(r) for r in group),
                          mean_time_s=mean(float(r["mission_time_s"]) for r in group),
                          min_solid_clearance_m=min(float(r["solid_min_clearance_m"]) for r in group)))
    return modes


def main():
    maps = []
    for raw in sorted(campaign.OUT.glob("cyl2_*/raw.csv")):
        rows = list(csv.DictReader(raw.open()))
        eligible = confirmation.eligible(rows)
        valid = all(quality_valid(r) and confirmation.known_outcome(r) for r in rows)
        failed_reference = any(not confirmation.safe(r) for r in rows if r["mode"] in ("full","adaptive"))
        all_modes = {r["mode"] for r in rows} == set(confirmation.MODES)
        decision = ("INVALID_MEASUREMENT_OR_INFRASTRUCTURE" if not valid else
                    "REJECT_FULL_OR_ADAPTIVE_FAILURE" if failed_reference else
                    "ELIGIBLE_FOR_NEW_N20" if eligible else
                    "NO_ACTUAL_OUTCOME_SEPARATION" if all_modes else "PILOT_INCOMPLETE")
        maps.append(dict(map=raw.parent.name, raw=str(raw), rows=len(rows),
                         decision=decision, eligible_for_new_n20=eligible,
                         per_mode=summarize(rows)))
    result = dict(measurement="prelaunch-solid-cylinder-observer-v1", legacy_rows_pooled=False,
                  total_completed_rows=sum(m["rows"] for m in maps), maps=maps,
                  population_guarantee=False)
    (campaign.OUT / "summary.json").write_text(json.dumps(result,indent=2)+"\n")
    flat = [dict(map=m["map"],decision=m["decision"],**r) for m in maps for r in m["per_mode"]]
    if flat:
        with (campaign.OUT / "summary.csv").open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(flat[0]),lineterminator="\n")
            writer.writeheader(); writer.writerows(flat)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
