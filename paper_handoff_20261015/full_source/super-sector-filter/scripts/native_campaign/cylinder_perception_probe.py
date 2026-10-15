#!/usr/bin/env python3
"""Separate diagnostic: early actual yaw and filtered clouds, no flight inputs.

This extra subscriber is NOT part of the standard comparison protocol and
its diagnostic row must not be pooled into development/n20 qualification.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import shlex
import time


def observe(output, ready):
    import numpy as np
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import PointCloud2
    if output.exists() or ready.exists():
        raise RuntimeError("Diagnostic evidence already exists")
    rclpy.init(); node=Node("cylinder_early_perception_probe")
    qos=QoSProfile(depth=100,reliability=ReliabilityPolicy.BEST_EFFORT)
    started=time.time(); first=None; latest=None
    poses=[]; clouds=[]
    def odom(msg):
        nonlocal first,latest
        now=time.time()
        if first is None: first=now
        p,v,q=msg.pose.pose.position,msg.twist.twist.linear,msg.pose.pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        latest=dict(epoch_s=now,stamp_s=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,
                    position=[p.x,p.y,p.z],velocity=[v.x,v.y,v.z],yaw_rad=yaw)
        poses.append(latest)
    def cloud(msg):
        now=time.time(); pose=latest
        record=dict(receive_epoch_s=now,stamp_s=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,
                    points=msg.width*msg.height,odom_available=pose is not None)
        if pose is not None:
            fields={f.name:f for f in msg.fields}
            if all(k in fields and fields[k].datatype==7 for k in "xyz"):
                dtype=np.dtype(dict(names=list("xyz"),formats=[">f4" if msg.is_bigendian else "<f4"]*3,
                                    offsets=[fields[k].offset for k in "xyz"],itemsize=msg.point_step))
                points=np.ndarray((msg.height,msg.width),dtype=dtype,buffer=msg.data,
                                  strides=(msg.row_step,msg.point_step))
                dx,dy,dz=[points[k].ravel()-pose["position"][i] for i,k in enumerate("xyz")]
                far=(dx*dx+dy*dy+dz*dz>1.5**2)&np.isfinite(dx)&np.isfinite(dy)&np.isfinite(dz)
                relative=np.arctan2(dy,dx)-pose["yaw_rad"]
                relative=np.arctan2(np.sin(relative),np.cos(relative))
                record.update(odom_age_s=now-pose["epoch_s"],position=pose["position"],
                              body_yaw_deg=math.degrees(pose["yaw_rad"]),
                              initial_stationary=(math.dist(pose["position"],(0,0,1.5))<.01
                                  and np.linalg.norm(pose["velocity"])<.01 and now-pose["epoch_s"]<.05),
                              far_points=int(np.count_nonzero(far)),
                              far_outside_47deg=int(np.count_nonzero(far&(np.abs(relative)>math.radians(47)))))
        clouds.append(record)
    node.create_subscription(Odometry,"/lidar_slam/odom",odom,qos)
    node.create_subscription(PointCloud2,"/cloud_sector",cloud,qos)
    ready.write_text(json.dumps(dict(ready_epoch_s=time.time(),subscriptions_created=True))+"\n")
    try:
        while rclpy.ok() and time.time()-started<35 and (first is None or time.time()-first<12):
            rclpy.spin_once(node,timeout_sec=.05)
    finally:
        report=dict(protocol="extra-read-only-early-yaw-cloud-diagnostic-v1",publishes_flight_inputs=False,
                    comparison_row=False,started_epoch_s=started,first_odom_epoch_s=first,
                    poses=poses,clouds=clouds,
                    caution="Nonstationary cloud bearings use latest received odom, not exact internal filter state")
        output.write_text(json.dumps(report,indent=2)+"\n")
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


def flight(name,mode,run):
    import cylinder_solid_campaign as solid
    campaign=solid.search.campaign
    output=solid.search.ROOT/"results/cylinder_perception_audit_20260915"/f"{name}_run{run}_{mode}"
    output.mkdir(parents=True,exist_ok=False)
    report=output/"early_perception.json"; ready=output/"early_perception.ready.json"
    original=campaign.spawn_process_group; probe=None
    log=(output/"early_perception.log").open("x")
    def spawn(*args,**kwargs):
        nonlocal probe
        command=" ".join(map(str,args[0])) if args else str(kwargs.get("args",""))
        if "ros2 launch mission_planner benchmark_seedmap.launch.py" in command:
            if probe is not None: raise RuntimeError("Unexpected second launch")
            cmd=(f"{campaign.ROS_ENV} && exec python3 {shlex.quote(str(Path(__file__).resolve()))}"
                 f" --observe --output {shlex.quote(str(report))} --ready {shlex.quote(str(ready))}")
            probe=original(["bash","-c",cmd],stdout=log,stderr=log)
            deadline=time.monotonic()+15
            while not ready.exists():
                if probe.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError("Early diagnostic subscriber not ready")
                time.sleep(.05)
        return original(*args,**kwargs)
    campaign.install_campaign_signal_handlers()
    campaign.spawn_process_group=spawn
    try:
        row=solid.run_trial(name,mode,run,output)
        with (output/"diagnostic_raw.csv").open("x",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=solid.FIELDS,extrasaction="ignore",lineterminator="\n")
            writer.writeheader(); writer.writerow(row)
    finally:
        campaign.spawn_process_group=original
        campaign.terminate_group(probe,grace_s=3.)
        campaign.cleanup_active_process_groups(); log.close()
    evidence=json.loads(report.read_text())
    stationary=[r for r in evidence["clouds"] if r.get("initial_stationary")]
    moving=next((r for r in evidence["poses"] if math.hypot(*r["velocity"][:2])>.2),None)
    print("PERCEPTION_DIAGNOSTIC "+json.dumps(dict(map=name,mode=mode,
          complete=row["success"],solid_contacts=row["solid_collision_episodes"],
          stationary_clouds=stationary,first_moving_pose=moving)),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map",nargs="?")
    parser.add_argument("--mode",choices=("sector","adaptive"),default="sector")
    parser.add_argument("--run",type=int,default=201)
    parser.add_argument("--observe",action="store_true")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--ready",type=Path)
    args=parser.parse_args()
    if args.observe:
        if args.output is None or args.ready is None: parser.error("Observer paths required")
        observe(args.output,args.ready)
    else:
        if not args.map or not args.map.startswith("cyl2_") or not args.map.replace("_","").isalnum():
            parser.error("An emitted cyl2_ map is required")
        flight(args.map,args.mode,args.run)


if __name__=="__main__": main()
