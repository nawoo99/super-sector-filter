import rclpy, numpy as np, math, sys
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs_py import point_cloud2 as pc2
MODE = sys.argv[1] if len(sys.argv)>1 else 'sector'   # full | sector | adaptive | trigger
HALF = math.radians(float(sys.argv[2]) if len(sys.argv)>2 else 60.0)  # half-angle deg
# trigger-based adaptive: default sector, open to full-view when SUPER stalls (safe-stop / replan starvation)
STALL_V=0.6   # m/s below this = stalled
STALL_T=1.2   # s stalled -> OPEN full-view
RESUME_V=1.5  # m/s above this
RESUME_T=2.0  # s recovered -> back to sector
class F(Node):
  def __init__(s):
    super().__init__('native_sector')
    s.drone=None; s.yaw=0.0; s.vyaw=None; s.kept=0; s.tot=0; s.frames=0
    s.open=False; s.slow_since=None; s.fast_since=None; s.open_frames=0
    s.create_subscription(PointCloud2,'/cloud_registered',s.cb_c,qos_profile_sensor_data)
    s.create_subscription(Odometry,'/lidar_slam/odom',s.cb_o,qos_profile_sensor_data)
    s.pub=s.create_publisher(PointCloud2,'/cloud_sector',qos_profile_sensor_data)
    s.create_timer(5.0,s.report)
  def now(s): return s.get_clock().now().nanoseconds*1e-9
  def cb_o(s,m):
    p=m.pose.pose.position; q=m.pose.pose.orientation
    s.drone=np.array([p.x,p.y,p.z],dtype=np.float32)
    s.yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    v=m.twist.twist.linear; spd=math.hypot(v.x,v.y)
    if spd>0.2: s.vyaw=math.atan2(v.y,v.x)
    if MODE=='trigger':   # hysteresis stall detection
      t=s.now()
      if not s.open:
        if spd<STALL_V:
          s.slow_since = s.slow_since or t
          if t-s.slow_since>STALL_T: s.open=True; s.fast_since=None
        else: s.slow_since=None
      else:
        if spd>RESUME_V:
          s.fast_since = s.fast_since or t
          if t-s.fast_since>RESUME_T: s.open=False; s.slow_since=None
        else: s.fast_since=None
  def cb_c(s,m):
    if MODE=='full' or s.drone is None or (MODE=='trigger' and s.open):
      if MODE=='trigger' and s.open: s.open_frames+=1; s.frames+=1
      s.pub.publish(m); return
    a=pc2.read_points_numpy(m,field_names=('x','y','z','intensity'),skip_nans=True)
    if a.size==0: s.pub.publish(m); return
    a=a.reshape(-1,4)
    center = s.vyaw if MODE=='adaptive' and s.vyaw is not None else s.yaw
    rel=np.arctan2(a[:,1]-s.drone[1], a[:,0]-s.drone[0]) - center
    rel=(rel+np.pi)%(2*np.pi)-np.pi
    out=a[np.abs(rel)<=HALF]
    s.tot+=len(a); s.kept+=len(out); s.frames+=1
    s.pub.publish(pc2.create_cloud(m.header, m.fields, out))
  def report(s):
    ext = f" open={s.open_frames/max(1,s.frames)*100:.0f}%" if MODE=='trigger' else ""
    if s.frames: print(f"[native_sector {MODE}] frames={s.frames} kept {s.kept/max(1,s.tot)*100:.0f}% ({s.kept//max(1,s.frames)}/{s.tot//max(1,s.frames)} pts/frame){ext}",flush=True)
rclpy.init(); rclpy.spin(F())
