#!/usr/bin/env python3
"""Read-only ground truth: sphere versus SOLID capped vertical cylinders.

Started before the simulator. Subscribes to odometry only; never publishes a
command, sensor cloud, planner input, or decision. Collision counts refer to
observed poses, not to hypothetical old-path counterfactuals.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import signal
import time

import numpy as np


def solid_clearances(position, cylinders, height=3., body_radius=.2):
    """Exact signed distance to capped cylinders, minus spherical body radius."""
    xyz = np.asarray(position, dtype=float)
    cols = np.asarray(cylinders, dtype=float)
    radial = np.hypot(xyz[0]-cols[:,0], xyz[1]-cols[:,1])-cols[:,2]
    vertical = abs(xyz[2]-height/2)-height/2
    outside = np.hypot(np.maximum(radial,0), max(vertical,0))
    inside = np.minimum(np.maximum(radial,vertical),0)
    return outside+inside-body_radius


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cylinders",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--ready",type=Path,required=True)
    parser.add_argument("--height",type=float,default=3.)
    parser.add_argument("--body-radius",type=float,default=.2)
    parser.add_argument("--max-wall-s",type=float,default=300.)
    args=parser.parse_args()
    if args.output.exists() or args.ready.exists():
        raise RuntimeError("Observer output exists; never overwrite a flight")
    cylinders=np.asarray([(float(r["x"]),float(r["y"]),float(r["r"]))
                          for r in csv.DictReader(args.cylinders.open())])
    if not len(cylinders) or not np.isfinite(cylinders).all() or np.any(cylinders[:,2]<=0):
        raise ValueError("Invalid solid cylinder geometry")
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from nav_msgs.msg import Odometry
    rclpy.init()
    node=Node("cylinder_solid_observer")
    stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    started=time.time()
    report=dict(schema="solid-cylinder-observer-v1", started_epoch_s=started,
                geometry=str(args.cylinders), body_radius_m=args.body_radius,
                cylinder_height_m=args.height, samples=0, invalid_samples=0,
                collision_episodes=0, contact_samples=0, min_clearance_m=None,
                first_pose=None, first_contact=None, min_context=None,
                max_odom_header_gap_s=0., max_position_step_m=0.,
                waypoints_reached=0, waypoint_epoch_s=[],
                publishes_nothing=True, sampled_pose_metric=True)
    previous_stamp=None; previous_position=None; in_contact=False
    args.output.parent.mkdir(parents=True,exist_ok=True)
    trace=args.output.with_suffix(".poses.csv")
    with trace.open("x",newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(("receive_epoch_s","odom_stamp_s","x","y","z","vx","vy","vz","solid_clearance_m","nearest_cylinder_index"))
        def odom(msg):
            nonlocal previous_stamp,previous_position,in_contact
            p,v=msg.pose.pose.position,msg.twist.twist.linear
            position=np.array((p.x,p.y,p.z)); velocity=np.array((v.x,v.y,v.z))
            if not np.isfinite(position).all() or not np.isfinite(velocity).all():
                report["invalid_samples"]+=1; return
            stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
            values=solid_clearances(position,cylinders,args.height,args.body_radius)
            index=int(np.argmin(values)); margin=float(values[index]); now=time.time()
            context=dict(receive_epoch_s=now,odom_stamp_s=stamp,position=position.tolist(),
                         velocity=velocity.tolist(),clearance_m=margin,
                         cylinder_index=index,cylinder=cylinders[index].tolist())
            report["samples"]+=1
            if report["first_pose"] is None:
                report["first_pose"]=context
            if previous_stamp is not None:
                report["max_odom_header_gap_s"]=max(report["max_odom_header_gap_s"],stamp-previous_stamp)
                report["max_position_step_m"]=max(report["max_position_step_m"],float(np.linalg.norm(position-previous_position)))
            previous_stamp,previous_position=stamp,position
            if report["min_clearance_m"] is None or margin<report["min_clearance_m"]:
                report["min_clearance_m"]=margin; report["min_context"]=context
            contact=margin<=0.
            if contact:
                report["contact_samples"]+=1
                if not in_contact: report["collision_episodes"]+=1
                if report["first_contact"] is None: report["first_contact"]=context
            in_contact=contact
            waypoints=((24,24),(-24,24),(-24,-24),(24,-24),(0,0))
            wi=report["waypoints_reached"]
            if wi<len(waypoints) and math.dist(position[:2],waypoints[wi])<1.5:
                report["waypoints_reached"]+=1; report["waypoint_epoch_s"].append(now)
            writer.writerow((now,stamp,*position,*velocity,margin,index))
            if report["samples"]%100==0: stream.flush()
        subscription=node.create_subscription(Odometry,"/lidar_slam/odom",odom,
            QoSProfile(depth=100,reliability=ReliabilityPolicy.BEST_EFFORT))
        args.ready.write_text(json.dumps({"ready_epoch_s":time.time(),"subscriber_created":True})+"\n")
        try:
            while not stopped and rclpy.ok() and time.time()-started<args.max_wall_s:
                rclpy.spin_once(node,timeout_sec=.05)
        finally:
            first=report["first_pose"]
            report["initial_pose_ok"]=bool(first and math.dist(first["position"],(0,0,1.5))<=.25
                                           and np.linalg.norm(first["velocity"])<=.25)
            report["valid"]=bool(report["samples"]>=10 and report["invalid_samples"]==0
                                  and report["initial_pose_ok"] and report["max_odom_header_gap_s"]<=.15)
            report["finished_epoch_s"]=time.time()
            report["success"]=report["waypoints_reached"]==5
            args.output.write_text(json.dumps(report,indent=2)+"\n")
            node.destroy_node()
            if rclpy.ok(): rclpy.shutdown()


if __name__=="__main__": main()
