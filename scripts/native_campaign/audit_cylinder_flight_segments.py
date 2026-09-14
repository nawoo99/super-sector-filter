#!/usr/bin/env python3
"""Read-only actual-pose segment timing, including failed/censored legs.

These measurements localize delay; neither stillness nor a planned path is
relabeled as collision. The signed-volume observer supplies actual contact.
"""
import argparse
import csv
import json
import math
from pathlib import Path


def segments(report_path):
    report=json.loads(report_path.read_text())
    poses=list(csv.DictReader(report_path.with_suffix(".poses.csv").open()))
    if not poses:
        return []
    boundaries=[float(poses[0]["receive_epoch_s"]),*report["waypoint_epoch_s"]]
    if report["waypoints_reached"]<5:
        boundaries.append(float(poses[-1]["receive_epoch_s"]))
    result=[]
    for i,(start,end) in enumerate(zip(boundaries,boundaries[1:])):
        points=[p for p in poses if start<=float(p["receive_epoch_s"])<=end]
        distance=hold=longest=current=0.
        for a,b in zip(points,points[1:]):
            dt=float(b["odom_stamp_s"])-float(a["odom_stamp_s"])
            if dt<=0 or dt>.15:
                current=0.; continue
            step=math.dist([float(a[k]) for k in "xyz"],[float(b[k]) for k in "xyz"])
            distance+=step
            if step/dt<=.05:
                hold+=dt; current+=dt; longest=max(longest,current)
            else:
                current=0.
        result.append(dict(leg=i+1,completed=i<report["waypoints_reached"],
                           elapsed_s=end-start,observed_xyz_path_length_m=distance,
                           near_stationary_pose_time_s=hold,longest_pose_hold_s=longest,
                           speed_threshold_mps=.05))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path,nargs="+")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    results=[]
    for raw in args.raw:
        for r in csv.DictReader(raw.open()):
            results.append(dict(map=r["map"],run=int(r["run"]),mode=r["mode"],
                                success=r["success"],solid_contacts=r["solid_collision_episodes"],
                                raw=str(raw),segments=segments(Path(r["solid_report_json"]))))
    result=dict(causal_claim=False,metric="actual-XYZ segments with pose-derived stillness",rows=results)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    for r in results:
        print(r["map"],r["run"],r["mode"],
              [(s["leg"],s["completed"],round(s["elapsed_s"],1),round(s["near_stationary_pose_time_s"],1)) for s in r["segments"]])


if __name__=="__main__":
    main()
