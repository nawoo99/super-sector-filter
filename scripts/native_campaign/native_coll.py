import rclpy, numpy as np, sys, time
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
try:
    from sensor_msgs_py import point_cloud2 as pc2
except Exception as e:
    print("no sensor_msgs_py:",e); sys.exit(1)
DRONE_R=0.2
class M(Node):
  def __init__(s):
    super().__init__('native_coll')
    s.cloud=None; s.mind=float('inf'); s.coll=0; s.inc=False; s.n=0
    s.ymin=1e9; s.ymax=-1e9
    s.create_subscription(PointCloud2,'/cloud_registered',s.cb_c,qos_profile_sensor_data)
    s.create_subscription(Odometry,'/lidar_slam/odom',s.cb_o,qos_profile_sensor_data)
  def cb_c(s,m):
    try: a=pc2.read_points_numpy(m,field_names=('x','y','z'),skip_nans=True)
    except Exception: return
    s.cloud=a.reshape(-1,3) if a.size else None
  def cb_o(s,m):
    p=m.pose.pose.position; s.ymin=min(s.ymin,p.y); s.ymax=max(s.ymax,p.y)
    if s.cloud is None or len(s.cloud)==0: return
    q=np.array([p.x,p.y,p.z],dtype=np.float32)
    d=float(np.sqrt(((s.cloud-q)**2).sum(1)).min()); s.mind=min(s.mind,d); s.n+=1
    if d<DRONE_R:
      if not s.inc: s.coll+=1; s.inc=True
    else: s.inc=False
rclpy.init(); n=M(); dur=float(sys.argv[1]) if len(sys.argv)>1 else 120; t0=time.time()
while time.time()-t0<dur: rclpy.spin_once(n,timeout_sec=0.2)
print(f"NATIVE_COLL samples={n.n} min_clearance={n.mind:.3f} collisions={n.coll} y_range=[{n.ymin:.1f},{n.ymax:.1f}]")
