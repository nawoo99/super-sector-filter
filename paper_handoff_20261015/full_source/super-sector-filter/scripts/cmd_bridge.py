#!/usr/bin/env python3
# cmd_bridge.py
# -------------------------------------------------------------------
# SUPER publishes mars_quadrotor_msgs/PositionCommand; the PX4 offboard
# controller (offboard.py) subscribes quadrotor_msgs/PositionCommand on
# /planning/pos_cmd. The two message TYPES differ (different package =
# different type hash), so ROS2 will not connect them directly even though
# the field layouts mostly overlap. This node copies the common subset.
#
#   sub : /super/pos_cmd   (mars_quadrotor_msgs/PositionCommand)  <- SUPER (remapped)
#   pub : /planning/pos_cmd(quadrotor_msgs/PositionCommand)       -> offboard.py
#
# quadrotor_msgs/PositionCommand is a strict field-subset of the mars one,
# so every quad field has a mars source. offboard.py only actually reads
# position + yaw + yaw_dot, but we copy everything common for completeness.
# -------------------------------------------------------------------
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from mars_quadrotor_msgs.msg import PositionCommand as MarsCmd
from quadrotor_msgs.msg import PositionCommand as QuadCmd


class CmdBridge(Node):
    def __init__(self):
        super().__init__("super_cmd_bridge")
        self.declare_parameter("input_topic", "/super/pos_cmd")
        self.declare_parameter("output_topic", "/planning/pos_cmd")
        in_topic = self.get_parameter("input_topic").value
        out_topic = self.get_parameter("output_topic").value

        # SUPER publishes with QoS(1, best_effort, volatile); match it on the sub side.
        sub_qos = QoSProfile(depth=1)
        sub_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        sub_qos.history = HistoryPolicy.KEEP_LAST
        sub_qos.durability = DurabilityPolicy.VOLATILE

        self.pub = self.create_publisher(QuadCmd, out_topic, 10)
        self.sub = self.create_subscription(MarsCmd, in_topic, self.cb, sub_qos)
        self.n = 0
        self.get_logger().info(f"cmd_bridge: {in_topic} (mars) -> {out_topic} (quadrotor)")

    def cb(self, m: MarsCmd):
        q = QuadCmd()
        q.header = m.header
        q.position = m.position
        q.velocity = m.velocity
        q.acceleration = m.acceleration
        q.yaw = m.yaw
        q.yaw_dot = m.yaw_dot
        q.kx = m.kx
        q.kv = m.kv
        q.trajectory_id = m.trajectory_id
        q.trajectory_flag = m.trajectory_flag
        self.pub.publish(q)
        self.n += 1
        if self.n % 50 == 1:
            self.get_logger().info(
                f"fwd #{self.n}: pos=({m.position.x:.2f},{m.position.y:.2f},{m.position.z:.2f}) "
                f"yaw={m.yaw:.2f} flag={m.trajectory_flag}")


def main():
    rclpy.init()
    node = CmdBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
