import rclpy, numpy as np, sys, time, math
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs_py import point_cloud2 as pc2
DRONE_R=0.2
class M(Node):
  def __init__(s):
    super().__init__('native_speed')
    s.cloud=None; s.mind=float('inf'); s.coll=0; s.inc=False
    s.spd=[]; s.ymin=1e9; s.ymax=-1e9; s.n=0
    s.create_subscription(PointCloud2,'/cloud_registered',s.cb_c,qos_profile_sensor_data)
    s.create_subscription(Odometry,'/lidar_slam/odom',s.cb_o,qos_profile_sensor_data)
  def cb_c(s,m):
    try: a=pc2.read_points_numpy(m,field_names=('x','y','z'),skip_nans=True)
    except Exception: return
    s.cloud=a.reshape(-1,3) if a.size else None
  def cb_o(s,m):
    p=m.pose.pose.position; v=m.twist.twist.linear
    sp=math.hypot(v.x,v.y); s.spd.append(sp)
    s.ymin=min(s.ymin,p.y); s.ymax=max(s.ymax,p.y); s.n+=1
    if s.cloud is not None and len(s.cloud):
        q=np.array([p.x,p.y,p.z],dtype=np.float32)
        d=float(np.sqrt(((s.cloud-q)**2).sum(1)).min()); s.mind=min(s.mind,d)
        if d<DRONE_R:
            if not s.inc: s.coll+=1; s.inc=True
        else: s.inc=False
rclpy.init(); n=M(); dur=float(sys.argv[1]) if len(sys.argv)>1 else 60; t0=time.time()
while time.time()-t0<dur: rclpy.spin_once(n,timeout_sec=0.2)
sp=[x for x in n.spd if x>0.05]
avg=sum(sp)/len(sp) if sp else 0
prog=abs(n.ymax-n.ymin)
print(f"NATIVE_SPD avg_speed={avg:.2f}m/s prog={prog:.1f}m coll={n.coll} min_clr={n.mind:.2f} samples={n.n}")
