#!/usr/bin/env python3
"""Frozen flight policy with a separate pre-launch, read-only solid observer.

The existing native runner, launch arguments and monitor are unchanged. Its
surface-only rows remain separate from this stronger measurement protocol.
"""
import argparse
import csv
import json
from pathlib import Path
import shlex
import time

import cylinder_map_search as search
from analyze_cylinder_only_stress_full_gate import boolean, quality_valid

OUT=search.ROOT/"results/cylinder_solid_map_search_20260915"
OBSERVER=Path(__file__).with_name("cylinder_solid_observer.py")
EXTRA_FIELDS=("solid_observer_valid","solid_initial_pose_ok","solid_samples",
              "solid_collision_episodes","solid_min_clearance_m","solid_max_odom_gap_s",
              "solid_success","solid_waypoints_reached","solid_completion_agrees",
              "solid_report_json","solid_observer_sha256")
FIELDS=list(search.campaign.FIELDS)+list(EXTRA_FIELDS)


def run_trial(name,mode,run,output):
    candidate=json.loads((search.OUT/name/"manifest.json").read_text())
    if search.frozen_policy()!=candidate["policy"]:
        raise RuntimeError("Frozen runtime policy changed")
    if any(search.geometry.sha256(Path(p))!=sha for p,sha in candidate["assets"].items()):
        raise RuntimeError("Map asset changed")
    campaign=search.campaign
    original_spawn=campaign.spawn_process_group
    original_monitor=campaign.build_loop_monitor_command
    observation=output/"solid"/f"{name}_run{run}_{mode}.json"
    ready=observation.with_suffix(".ready.json")
    if observation.exists() or ready.exists():
        raise RuntimeError("Solid flight evidence exists; use a new run, never overwrite")
    observation.parent.mkdir(parents=True,exist_ok=True)
    observer=None; launched=None
    log_stream=observation.with_suffix(".log").open("x")
    def spawn(*args,**kwargs):
        nonlocal observer,launched
        command=" ".join(map(str,args[0])) if args else str(kwargs.get("args",""))
        if "ros2 launch mission_planner benchmark_seedmap.launch.py" in command:
            if observer is not None: raise RuntimeError("Unexpected second simulator launch")
            observer_command=(f"{campaign.ROS_ENV} && exec python3 {shlex.quote(str(OBSERVER))}"
                f" --cylinders {shlex.quote(str(search.OUT/name/'cylinders.csv'))}"
                f" --height {candidate['height_m']} --body-radius 0.2"
                f" --output {shlex.quote(str(observation))} --ready {shlex.quote(str(ready))}")
            observer=original_spawn(["bash","-c",observer_command],stdout=log_stream,stderr=log_stream)
            deadline=time.monotonic()+20
            while not ready.exists():
                if observer.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError("Solid observer did not become ready before launch")
                time.sleep(.05)
            launched=time.time()
        return original_spawn(*args,**kwargs)
    if "monitor_witness" in candidate:
        x,y,r,h=candidate["monitor_witness"]
        def monitor(wps,switch,timeout,out_json,monitor_options=""):
            monitor_options+=(f" --trajectory-risk-audit --trajectory-audit-center-x {x}"
                f" --trajectory-audit-center-y {y} --trajectory-audit-radius-m {r}"
                f" --trajectory-audit-height-m {h}")
            return original_monitor(wps,switch,timeout,out_json,monitor_options)
        campaign.build_loop_monitor_command=monitor
    campaign.spawn_process_group=spawn
    try:
        rec=campaign.run_one(name,mode,run,**search.OPTIONS,
            artifacts_dir=str(output/"artifacts"),seedmap_super_config_override=search.PROFILES[mode])
    finally:
        campaign.spawn_process_group=original_spawn
        campaign.build_loop_monitor_command=original_monitor
        campaign.terminate_group(observer,grace_s=3.)
        log_stream.close()
    evidence=json.loads(observation.read_text()) if observation.exists() else {}
    ready_data=json.loads(ready.read_text()) if ready.exists() else {}
    ready_before=bool(launched and ready_data.get("ready_epoch_s",float("inf"))<launched)
    agrees=bool(evidence and boolean(rec.get("success"))==evidence.get("success"))
    rec.update(solid_observer_valid=bool(evidence.get("valid") and ready_before and agrees),
               solid_initial_pose_ok=evidence.get("initial_pose_ok",False),
               solid_samples=evidence.get("samples",0),
               solid_collision_episodes=evidence.get("collision_episodes"),
               solid_min_clearance_m=evidence.get("min_clearance_m"),
               solid_max_odom_gap_s=evidence.get("max_odom_header_gap_s"),
               solid_success=evidence.get("success"),
               solid_waypoints_reached=evidence.get("waypoints_reached"),
               solid_completion_agrees=agrees,solid_report_json=str(observation),
               solid_observer_sha256=search.geometry.sha256(OBSERVER))
    if search.frozen_policy()!=candidate["policy"]:
        raise RuntimeError("Runtime policy changed during solid trial")
    return rec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--run",type=int,default=1)
    parser.add_argument("--modes",nargs="+",choices=tuple(search.PROFILES),default=list(search.PROFILES))
    args=parser.parse_args()
    if not args.map.startswith("cyl2_") or not args.map.replace("_","").isalnum() or args.run<1:
        parser.error("Use a generated cyl2_ map and positive run index")
    import confirm_cylinder_search_n20 as confirmation
    output=OUT/args.map; output.mkdir(parents=True,exist_ok=True)
    raw=output/"raw.csv"
    rows=list(csv.DictReader(raw.open())) if raw.exists() else []
    existing={(int(r["run"]),r["mode"]) for r in rows}
    if len(existing)!=len(rows): raise RuntimeError("Duplicate existing rows")
    search.campaign.install_campaign_signal_handlers()
    with raw.open("a",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore",lineterminator="\n")
        if not rows: writer.writeheader(); stream.flush()
        try:
            for mode in args.modes:
                if (args.run,mode) in existing: raise RuntimeError("Flight already exists")
                rec=run_trial(args.map,mode,args.run,output)
                writer.writerow(rec); stream.flush(); rows.append(rec)
                print("SOLID_RESULT "+json.dumps({k:rec.get(k) for k in
                    ("map","mode","success","mission_time_s","static_pcd_collisions",*EXTRA_FIELDS)}),flush=True)
                if not quality_valid(rec) or not boolean(rec["solid_observer_valid"]):
                    raise RuntimeError("Observer/infrastructure invalid; evidence retained for diagnosis")
                if mode=="full" and not confirmation.safe(rec):
                    print("SOLID_FULL_GATE_STOP",flush=True); break
        finally:
            search.campaign.cleanup_active_process_groups()
    print("SOLID_ELIGIBLE "+str(confirmation.eligible(rows)),flush=True)


if __name__=="__main__": main()
