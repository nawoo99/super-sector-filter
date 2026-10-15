#!/usr/bin/env python3
"""Read-only audit of rejected moving brakes and perfect-tracking pose holds.

Not an actual-collision counter or a dynamics simulation. Closely spaced log
records are clustered only to avoid calling retries independent events.
"""
import csv
import json
import re
from pathlib import Path

from cylinder_map_search import OUT


def scalar(line,key):
    match=re.search(r"(?:^|\s)"+re.escape(key)+r"=([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|inf|nan)",line)
    if not match:return None
    try:return float(match[1])
    except ValueError:return None


def audit_log(text):
    rejected=[]; episodes=[]; frozen=[]
    for line in text.splitlines():
        if "[TRAJ_GUARD_BRAKE_REJECTED]" not in line:continue
        stamp=re.search(r"\[(\d{10}\.\d+)\]",line)
        if not stamp:continue
        t=float(stamp[1]);speed=scalar(line,"speed0")
        rejected.append(t)
        if speed is not None and speed>.5:
            if not episodes or t-episodes[-1]["last_rejection_epoch_s"]>.75:
                episodes.append(dict(start_epoch_s=t,last_rejection_epoch_s=t,max_rejected_speed_mps=speed,
                                     moving_rejection_log_records=1))
            else:
                episodes[-1]["last_rejection_epoch_s"]=t
                episodes[-1]["max_rejected_speed_mps"]=max(episodes[-1]["max_rejected_speed_mps"],speed)
                episodes[-1]["moving_rejection_log_records"]+=1
        pose=scalar(line,"motion_pose_speed");twist=scalar(line,"motion_twist_speed")
        dt=scalar(line,"motion_dt")
        if (pose is not None and twist is not None and dt is not None
                and pose<=.05 and twist>1 and dt>=.05
                and "motion_source=position_difference" in line
                and "no brake command published" in line):
            frozen.append(dict(epoch_s=t,pose_speed_mps=pose,reported_twist_mps=twist,
                               differencing_dt_s=dt))
    return dict(rejection_log_records=len(rejected),moving_rejection_episodes=episodes,
                frozen_pose_moving_twist_records=frozen,
                note="Diagnostic only: not an observed collision or proof that collision was inevitable.")


def main():
    results=[]
    for folder in sorted(OUT.iterdir()):
        if not folder.is_dir():continue
        rows=list(csv.DictReader((folder/"raw.csv").open())) if (folder/"raw.csv").exists() else []
        for row in rows:
            path=folder/f"artifacts/{folder.name}_run{row['run']}_{row['mode']}.attempt1.stack.log"
            if not path.exists():continue
            audit=audit_log(path.read_text(errors="replace"))
            result=dict(map=folder.name,run=int(row["run"]),mode=row["mode"],
                        reported_complete=row["success"],static_pcd_contacts=row.get("static_pcd_collisions"),
                        **audit)
            results.append(result)
            print(folder.name,row["run"],row["mode"],
                  "moving_rejection_episodes=",len(audit["moving_rejection_episodes"]),
                  "frozen_pose_records=",len(audit["frozen_pose_moving_twist_records"]))
    (OUT/"stop_audit.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__":main()
