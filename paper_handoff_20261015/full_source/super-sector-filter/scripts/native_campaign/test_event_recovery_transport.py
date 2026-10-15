#!/usr/bin/env python3
"""Real ROS frontend handshake test; synthetic cloud only, no vehicle/planner.

Run explicitly after sourcing ROS/workspace, not as part of the flight matrix.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/root/super-sector-filter/results/event_recovery_transport_corrected_20260916'))
    args=parser.parse_args()
    os.environ['ROS_DOMAIN_ID']='194'
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import PointCloud2, PointField
    from std_msgs.msg import Bool, UInt64, UInt64MultiArray
    output=args.output
    output.mkdir(exist_ok=False)
    log=(output/'frontend.log').open('w')
    proc=subprocess.Popen([
        '/root/super_ws/install/mission_planner/lib/mission_planner/native_sector_cpp',
        'adaptive','45','--event-recovery','--full-refresh-generation-ack',
        '--replan-fail-streak-open','3',
        '--reliable-output','--near-field-radius-m','0',
        '--stats-json',str(output/'stats.json')],stdout=log,stderr=subprocess.STDOUT)
    rclpy.init()
    node=rclpy.create_node('event_recovery_contract_test')
    reliable=QoSProfile(depth=16,reliability=ReliabilityPolicy.RELIABLE)
    latched=QoSProfile(depth=16,reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL)
    raw=node.create_publisher(PointCloud2,'/cloud_registered',reliable)
    odom=node.create_publisher(Odometry,'/lidar_slam/odom',reliable)
    state=node.create_publisher(Bool,'/planning/trajectory_guard_recovery_active',latched)
    replan=node.create_publisher(Bool,'/planning/replan_status',reliable)
    ack=node.create_publisher(UInt64MultiArray,'/rog_map/cloud_process_ack',reliable)
    widths=[];requests=[];event_requests=[]
    subscriptions=[
        node.create_subscription(PointCloud2,'/cloud_sector',lambda m:widths.append(m.width),reliable),
        node.create_subscription(UInt64,'/sector/event_recovery_request',lambda m:event_requests.append(m.data),latched),
        node.create_subscription(UInt64MultiArray,'/sector/full_refresh_request',lambda m:requests.append(list(m.data)),latched)]
    next_cloud=0.0
    speed=0.0

    def pump(seconds,commit=False):
        nonlocal next_cloud
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            if proc.poll() is not None:raise RuntimeError('Frontend exited')
            if time.monotonic()>=next_cloud:
                next_cloud=time.monotonic()+.1
                pose=Odometry();pose.pose.pose.orientation.w=1.0
                pose.twist.twist.linear.x=speed
                pose.header.stamp=node.get_clock().now().to_msg();odom.publish(pose)
                cloud=PointCloud2();cloud.header.frame_id='world'
                cloud.header.stamp=node.get_clock().now().to_msg()
                cloud.height=1;cloud.width=4;cloud.point_step=16;cloud.row_step=64
                cloud.is_dense=True
                cloud.fields=[PointField(name=n,offset=4*i,datatype=7,count=1)
                              for i,n in enumerate(('x','y','z','intensity'))]
                cloud.data=b''.join(struct.pack('<ffff',x,y,0.,1.) for x,y in ((8.,0.),(0.,8.),(-8.,0.),(0.,-8.)))
                raw.publish(cloud)
                if commit and requests and requests[-1][0]>0:
                    ack.publish(UInt64MultiArray(data=[1,requests[-1][1],100,1]))
            rclpy.spin_once(node,timeout_sec=.02)

    try:
        pump(2)
        assert widths and widths[-1]==1, widths[-10:]
        for _ in range(3):
            replan.publish(Bool(data=False));pump(.15)
        assert event_requests==[1], 'Initial no-path failures did not request recovery'
        state.publish(Bool(data=True));pump(.7)
        assert widths[-1]==4 and requests[-1][0]>0
        # A processed-but-not-committed scan cannot satisfy the handshake.
        ack.publish(UInt64MultiArray(data=[1,requests[-1][1],100,0]));pump(.2)
        state.publish(Bool(data=False));pump(.5)
        assert widths[-1]==4, 'Closed on non-committed/absent ACK'
        pump(.8,commit=True)
        assert widths[-1]==1, 'Close-before-ACK did not converge to Sector'
        # A committed map without a new-path release must stay Full.
        state.publish(Bool(data=True));pump(.5)
        pump(.8,commit=True);pump(.7)
        assert widths[-1]==4, 'Map ACK alone incorrectly closed Full'
        state.publish(Bool(data=False));pump(.4)
        assert widths[-1]==1, 'ACK-before-close did not converge to Sector'
        speed=2.0;pump(.4)
        replan.publish(Bool(data=True));pump(.2)
        for _ in range(5):
            replan.publish(Bool(data=False));pump(.15)
        assert event_requests==[1] and widths[-1]==1, 'Routine optimizer failures incorrectly requested a stop'
        speed=0.0;pump(1.6)
        assert event_requests==[1,2], 'Persistent stall did not request recovery'
        result={'passed':True,'synthetic_only':True,'domain':194,
                'checks':['initial-sector','full-on-guard','no-commit-held',
                          'close-before-ack-held','ordered-release',
                          'map-ack-without-path-held','ack-before-close-release',
                          'initial-no-path-requests-recovery',
                          'routine-failure-during-progress-does-not-stop',
                          'persistent-stall-requests-recovery']}
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:
        proc.send_signal(signal.SIGINT)
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        node.destroy_node();rclpy.shutdown();log.close()


if __name__=='__main__':main()
