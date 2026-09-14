#!/usr/bin/env python3
"""Descriptive map-search ledger: includes failed candidates, no p-values."""
import csv
import json
import math
from pathlib import Path

from analyze_cylinder_only_stress_full_gate import boolean, contact_free, quality_valid
from cylinder_map_search import OUT, frozen_policy


def number(row,key):
    try:
        value=float(row.get(key,""))
        return value if math.isfinite(value) else None
    except (ValueError,TypeError): return None


def main():
    current=frozen_policy()
    fields=["map","run","mode","success","static_pcd_collisions",
            "mission_time_s","static_pcd_clearance_m","quality_valid",
            "end_to_end_cpu_cores_mean","end_to_end_cpu_core_s",
            "planner_ingress_payload_mib_s","filter_effective_full_open_transitions",
            "frontend_risk_brake_events","frontend_body_brake_events",
            "waypoints_reached","final_x","final_y","policy_unchanged"]
    combined=[]; decisions=[]
    for folder in sorted(OUT.iterdir()):
        if not folder.is_dir() or not (folder/"manifest.json").exists(): continue
        manifest=json.loads((folder/"manifest.json").read_text())
        raw=folder/"raw.csv"
        rows=list(csv.DictReader(raw.open())) if raw.exists() else []
        valid=all(quality_valid(r) for r in rows)
        safe=lambda r: boolean(r.get("success")) and contact_free(r)
        mode_rows={mode:[r for r in rows if r["mode"]==mode] for mode in ("full","sector","adaptive")}
        decision="PENDING"
        if rows and not valid: decision="INFRASTRUCTURE_OR_QUALITY_INVALID"
        elif any(not safe(r) for m in ("full","adaptive") for r in mode_rows[m]):
            decision="REJECT_FULL_OR_ADAPTIVE_UNSAFE_OR_INCOMPLETE"
        elif all(mode_rows.values()):
            decision=("EXPLORATORY_SEPARATION_REPEAT_REQUIRED" if any(not safe(r) for r in mode_rows["sector"])
                      else "NO_SAFE_COMPLETION_SEPARATION")
        decisions.append({"map":folder.name,"decision":decision,"rows":len(rows),
                          "runtime_policy_unchanged":manifest["policy"]==current})
        for r in rows:
            rec={k:r.get(k,"") for k in fields}
            rec["quality_valid"]=quality_valid(r)
            rec["policy_unchanged"]=manifest["policy"]==current
            combined.append(rec)
    with (OUT/"summary.csv").open("w",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(combined)
    (OUT/"decisions.json").write_text(json.dumps(decisions,indent=2)+"\n")
    print("map | run | mode | complete | contacts | time(s) | clearance(m) | E2E CPU(cores) | ingress(MiB/s) | open | valid")
    for r in combined:
        print(" | ".join(str(r[k]) for k in ("map","run","mode","success","static_pcd_collisions",
                         "mission_time_s","static_pcd_clearance_m","end_to_end_cpu_cores_mean",
                         "planner_ingress_payload_mib_s","filter_effective_full_open_transitions","quality_valid")))
    print(json.dumps(decisions,indent=2))


if __name__=="__main__":main()
