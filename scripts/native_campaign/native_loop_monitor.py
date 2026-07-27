import rclpy, numpy as np, sys, time, json
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs_py import point_cloud2 as pc2

# args: <waypoints "x,y;x,y;..."> <switch_dist> <timeout_s> <out_json>
WPS = [tuple(float(v) for v in p.split(',')) for p in sys.argv[1].split(';')]
SWITCH = float(sys.argv[2])
TIMEOUT = float(sys.argv[3])
OUT = sys.argv[4]
DRONE_R = 0.2

class M(Node):
    def __init__(s):
        super().__init__('native_loop_monitor')
        s.cloud = None
        s.mind = float('inf')
        s.coll = 0
        s.inc = False
        s.n = 0
        s.wi = 0
        s.t0 = time.time()
        s.t_done = None
        s.create_subscription(PointCloud2, '/cloud_registered', s.cb_c, qos_profile_sensor_data)
        s.create_subscription(Odometry, '/lidar_slam/odom', s.cb_o, qos_profile_sensor_data)

    def cb_c(s, m):
        try:
            a = pc2.read_points_numpy(m, field_names=('x', 'y', 'z'), skip_nans=True)
        except Exception:
            return
        s.cloud = a.reshape(-1, 3) if a.size else None

    def cb_o(s, m):
        p = m.pose.pose.position
        if s.cloud is not None and len(s.cloud) > 0:
            q = np.array([p.x, p.y, p.z], dtype=np.float32)
            d = float(np.sqrt(((s.cloud - q) ** 2).sum(1)).min())
            s.mind = min(s.mind, d)
            s.n += 1
            if d < DRONE_R:
                if not s.inc:
                    s.coll += 1
                    s.inc = True
            else:
                s.inc = False
        if s.wi < len(WPS):
            tx, ty = WPS[s.wi]
            if (p.x - tx) ** 2 + (p.y - ty) ** 2 < SWITCH ** 2:
                s.wi += 1
                if s.wi >= len(WPS):
                    s.t_done = time.time()

rclpy.init()
node = M()
while (time.time() - node.t0) < TIMEOUT and node.t_done is None:
    rclpy.spin_once(node, timeout_sec=0.2)

success = node.t_done is not None
mission_time = (node.t_done - node.t0) if success else (time.time() - node.t0)
result = {
    "success": success,
    "mission_time_s": round(mission_time, 2),
    "waypoints_reached": node.wi,
    "n_waypoints": len(WPS),
    "collisions": node.coll,
    "min_clearance_m": round(node.mind, 3) if node.mind != float('inf') else None,
    "samples": node.n,
}
with open(OUT, 'w') as f:
    json.dump(result, f)
print("NATIVE_LOOP", json.dumps(result))
