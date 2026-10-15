#!/usr/bin/env python3
import math
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    HistoryPolicy,
    DurabilityPolicy,
    qos_profile_sensor_data,
)

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleAttitudeSetpoint,
    VehicleCommand,
    VehicleLocalPosition,
    VehicleStatus,
)

from geometry_msgs.msg import PoseStamped, Twist, Vector3, Point
from std_msgs.msg import String
from quadrotor_msgs.msg import PositionCommand


def wrap_pi(a: float) -> float:
    """wrap angle to [-pi, pi]."""
    a = (a + math.pi) % (2.0 * math.pi) - math.pi
    return a


def enu_pos_to_ned(x_enu: float, y_enu: float, z_enu: float):
    """
    ENU(world) -> NED(world)
      ENU: x=E, y=N, z=U
      NED: x=N, y=E, z=D
    """
    x_ned = y_enu
    y_ned = x_enu
    z_ned = -z_enu
    return x_ned, y_ned, z_ned


def enu_yaw_to_ned(yaw_enu: float) -> float:
    """
    yaw ENU -> yaw NED
    (일반적으로 PX4 heading과 맞추려면)
      yaw_ned = pi/2 - yaw_enu
    """
    return wrap_pi((math.pi / 2.0) - yaw_enu)


class OffboardControl(Node):
    def __init__(self) -> None:
        super().__init__("offboard_control_takeoff_and_land")

        # -------------------------------
        # ✅ QoS 정리 (중요!)
        #  - PX4가 publish 하는 /fmu/out/* 는 ROS2 기본 QoS로는 종종 안 맞아서
        #    "sensor_data QoS"로 subscribe 하는 게 안전.
        #  - /fmu/in/* 으로 publish 하는 건 ROS 기본 QoS(=reliable)가 보통 호환됨.
        # -------------------------------

        # PX4 IN publishers (/fmu/in/*)
        qos_px4_in = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,   # ✅ best_effort 말고 reliable로 (호환성 더 안전)
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # PX4 OUT subscribers (/fmu/out/*)
        # ✅ sensor_data QoS: best_effort + volatile (ROS2에서 자주 쓰는 표준)
        qos_px4_out = qos_profile_sensor_data

        # Planner topic (/planning/pos_cmd)
        qos_planner = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        qos_cmd = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,   # (중요) VOLATILE 추천: TRANSIENT_LOCAL은 "마지막 명령이 재전송"될 수 있어 위험
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Publishers
        self.offboard_control_mode_pub = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", qos_px4_in
        )
        self.trajectory_setpoint_pub = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", qos_px4_in
        )
        self.attitude_setpoint_pub = self.create_publisher(
            VehicleAttitudeSetpoint, "/fmu/in/vehicle_attitude_setpoint_v1", qos_px4_in
        )
        self.vehicle_command_pub = self.create_publisher(
            VehicleCommand, "/fmu/in/vehicle_command", qos_px4_in
        )

        # Subscribers
        self.vehicle_local_position_sub = self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.vehicle_local_position_callback,
            qos_px4_out,
        )

        self.vehicle_status_sub = self.create_subscription(
            VehicleStatus,
            "/fmu/out/vehicle_status_v1",
            self.vehicle_status_callback,
            qos_px4_out,
        )

        self.fastplanner_sub = self.create_subscription(
            PositionCommand, "/planning/pos_cmd", self.fastplanner_callback, qos_planner
        )

        self.setpoint_target_sub_pos = self.create_subscription(
            PoseStamped, "/position_cmd", self.position_command_callback, qos_cmd
        )

        self.setpoint_target_sub_vel = self.create_subscription(
            Twist, "/velocity_cmd", self.velocity_command_callback, qos_cmd
        )

        self.keyboard_cmd_sub = self.create_subscription(
            String, "/keyboard_cmd", self.keyboard_command_callback, qos_cmd
        )

        # -------------------------------
        # 상태/변수
        # -------------------------------
        self.got_local_pos = False

        self.vehicle_local_position = VehicleLocalPosition()
        self.vehicle_status = VehicleStatus()

        # 현재 기체 yaw(heading), NED 기준
        self.trueYaw = 0.0

        # 기본 takeoff: "현재 z에서 0.5m 올라가기" (NED: 위로 = z 감소)
        self.takeoff_delta_z = -0.5

        # Control mode: POSITION / VELOCITY / FAST-PLANNER
        self.control_mode = "POSITION"

        # 요청 플래그 (키보드로)
        self.req_offboard = False
        self.req_arm = False

        # command rate limit
        self.last_mode_cmd_ns = 0
        self.last_arm_cmd_ns = 0

        # offboard 진입 전에 setpoint 몇 번 보냈는지
        self.offboard_setpoint_counter = 0

        # -------------------------------
        # POSITION setpoint (NED)
        # -------------------------------
        self.sp_pos_ned = np.array([0.0, 0.0, 0.0], dtype=float)
        self.sp_yaw_ned = 0.0

        # -------------------------------
        # VELOCITY command (body FLU 입력 -> body FRD -> world NED)
        # -------------------------------
        self.body_vel_frd = np.array([0.0, 0.0, 0.0], dtype=float)  # [forward, right, down]
        self.yaw_rate_ned = 0.0  # NED 기준 yaw rate

        # -------------------------------
        # FAST-PLANNER setpoint (ENU 입력 -> NED 저장)
        # -------------------------------
        self.fp_pos_ned = np.array([0.0, 0.0, 0.0], dtype=float)
        self.fp_vel_ned = np.array([0.0, 0.0, 0.0], dtype=float)   # velocity feedforward
        self.fp_acc_ned = np.array([0.0, 0.0, 0.0], dtype=float)   # acceleration feedforward
        self.fp_ff_valid = False                                   # planner provided finite vel/acc
        self.fp_yaw_ned = 0.0
        self.fp_yaw_dot_ned = 0.0
        self.last_fp_time_ns = 0
        self.last_log_ns = 0

        # Constant-altitude (lateral) study: hold the FAST-PLANNER z setpoint at a fixed
        # altitude instead of following SUPER's z. SUPER's MINCO trajectory dips in z on
        # aggressive avoidance turns, and our position-level offboard can't recover the
        # altitude in time -> the drone sank into the ground mid-maneuver. The obstacles
        # are 3 m pillars, so a fixed cruise altitude still requires the same lateral
        # avoidance; SUPER handles xy, we pin z. Latched once FAST-PLANNER first activates.
        self.fp_hold_alt = float(self.declare_parameter("hold_altitude", 1.5).value)  # [m]
        self.fp_hold_z_ned = -self.fp_hold_alt   # fixed NED z setpoint (down = +)

        # --- SUPER-native SO3 geometric controller (attitude + collective thrust) ---
        # The position-level interface (PX4 position PID) lagged SUPER's aggressive
        # avoidance -> the drone thrashed and dipped in the obstacle field. Here we close
        # the position/velocity loop ourselves and drive PX4's ATTITUDE controller directly
        # (VehicleAttitudeSetpoint), which is how SUPER was designed to be flown. Mass
        # cancels in the thrust normalisation, so only the hover-thrust ratio is needed:
        #     a_des      = a_ff - Kp*(pos-pos_des) - Kv*(vel-vel_des)      [world NED]
        #     thrust_dir = g*e3 - a_des            (e3 = down)            -> body z axis
        #     q_d        = attitude from (thrust_dir, desired yaw)
        #     thr_norm   = THR_HOVER * |thrust_dir| / g
        self.use_so3 = bool(self.declare_parameter("use_so3", True).value)
        # FIXED-YAW mode: hold heading at fixed_yaw_deg (NED) instead of tracking velocity.
        # 999 (default) = disabled = track SUPER's yaw. Set e.g. 0 to face NED-north the whole
        # loop -> the forward sector points away from motion on 3 of the 4 legs (blindspot test).
        _fy = float(self.declare_parameter("fixed_yaw_deg", 999.0).value)
        self.fixed_yaw_en = abs(_fy) <= 360.0
        self.fixed_yaw_ned = math.radians(_fy) if self.fixed_yaw_en else 0.0
        # NOTE the x500 carries the 3D LiDAR -> it is heavy, true hover is ~0.82 of full
        # thrust (weak TWR ~1.2). Keep the feed-forward hover a touch LOW (0.70) and let
        # the altitude integrator trim up to the true value (this gave clean, non-bouncy
        # tracking; setting hover_thr=0.82 directly over-thrust and oscillated). The thrust
        # CLAMP must leave real head-room above true hover or the drone can't hold altitude
        # once it tilts (vertical thrust = thr*cos(tilt)); 0.90 starved it -> sink.
        self.so3_hover_thr = float(self.declare_parameter("hover_thrust", 0.70).value)
        self.so3_thr_max = 0.98      # thrust clamp: must exceed hover/cos(tilt_max)
        self.so3_grav = 9.81
        # Cascaded P(position)->saturated velocity->P(velocity)->accel. The velocity
        # saturation is the key: it stops the drone over-speeding to catch up after a
        # transient, which is what made it overshoot SUPER's path into a tight obstacle
        # gap and clip/sink. v_cmd = des_vel - Kp_pos*(pos-des_pos), |v_cmd| capped.
        self.so3_Kp_pos = np.array([1.6, 1.6, 2.4], dtype=float)   # pos err -> vel [1/s]
        self.so3_Kv = np.array([3.2, 3.2, 4.2], dtype=float)       # vel err -> accel [1/s]
        self.so3_vmax_h = 1.8        # max horizontal speed command [m/s] (>= config max_vel)
        self.so3_vmax_v = 1.4        # max vertical speed command [m/s]
        self.so3_tilt_max = math.radians(30.0)                 # cap commanded tilt (safety)
        # altitude-floor protection: if the drone drops near virtual_ground it must climb
        # out BEFORE it sinks below it (there SUPER stops planning and the drone wedges).
        # Below the floor we suppress horizontal accel (a level drone puts all thrust into
        # lift) and let the strong vertical feedback climb it back.
        self.so3_alt_floor = 0.85    # [m] engage altitude protection below this
        # altitude integrator: kills the steady-state altitude sag from an imperfect
        # hover-thrust estimate (the sim's true hover thrust differs from MPC_THR_HOVER).
        self.so3_Ki_z = 1.2          # accel per (m*s) of integrated z error
        self.so3_iz = 0.0            # integrator state
        self.so3_iz_max = 1.5        # |iz| clamp (anti-windup): max ~1.8 m/s^2 of trim
        self.so3_dt = 0.05           # timer period [s]
        self._fp_was_alive = False   # reset integrator on FAST-PLANNER (re)activation

        # Timer: 20Hz
        self.timer = self.create_timer(0.05, self.timer_callback)

    # -------------------------------
    # Callbacks
    # -------------------------------
    def vehicle_local_position_callback(self, msg: VehicleLocalPosition):
        self.vehicle_local_position = msg
        self.trueYaw = msg.heading  # PX4 heading (NED)

        # xy_valid/z_valid 체크: EKF 초기화 완료 전에는 setpoint 잡지 않음
        xy_ok = getattr(msg, 'xy_valid', True)
        z_ok  = getattr(msg, 'z_valid',  True)
        if not (xy_ok and z_ok):
            return

        if not self.got_local_pos:
            self.got_local_pos = True

            # 최초 1회: 현재 위치 기준으로 takeoff setpoint 잡기
            # NED: 위로 0.5m = z에 (-0.5) 더하기
            self.sp_pos_ned[0] = msg.x
            self.sp_pos_ned[1] = msg.y
            self.sp_pos_ned[2] = msg.z + self.takeoff_delta_z
            self.sp_yaw_ned = msg.heading

    def vehicle_status_callback(self, msg: VehicleStatus):
        self.vehicle_status = msg

    def position_command_callback(self, msg: PoseStamped):
        # /position_cmd 는 ROS(보통 ENU)라고 가정 -> PX4 NED로 변환
        x_ned, y_ned, z_ned = enu_pos_to_ned(
            msg.pose.position.x, msg.pose.position.y, msg.pose.position.z
        )

        # quaternion -> yaw(ENU) -> yaw(NED)
        q = msg.pose.orientation
        yaw_enu = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        yaw_ned = enu_yaw_to_ned(yaw_enu)

        self.sp_pos_ned[0] = x_ned
        self.sp_pos_ned[1] = y_ned
        self.sp_pos_ned[2] = z_ned
        self.sp_yaw_ned = yaw_ned

    def velocity_command_callback(self, msg: Twist):
        # /velocity_cmd 는 "ROS body FLU"로 들어온다고 가정
        # FLU (x forward, y left, z up) -> FRD (x forward, y right, z down)
        vx_frd = msg.linear.x
        vy_frd = -msg.linear.y
        vz_frd = -msg.linear.z

        self.body_vel_frd[0] = vx_frd
        self.body_vel_frd[1] = vy_frd
        self.body_vel_frd[2] = vz_frd

        # yaw rate: ENU(+z up) -> NED(+z down) 이므로 부호 반대가 안전
        self.yaw_rate_ned = -msg.angular.z

    def fastplanner_callback(self, msg: PositionCommand):
        now_ns = self.get_clock().now().nanoseconds

        # 1Hz 로그
        if now_ns - self.last_log_ns > int(1e9):
            self.get_logger().info(
                f"FP recv(ENU): pos=({msg.position.x:.2f},{msg.position.y:.2f},{msg.position.z:.2f}) yaw={msg.yaw:.2f}"
            )
            self.last_log_ns = now_ns

        # planner는 ENU(world)라고 가정 -> NED(world)
        x_ned, y_ned, z_ned = enu_pos_to_ned(msg.position.x, msg.position.y, msg.position.z)
        self.fp_pos_ned[0] = x_ned
        self.fp_pos_ned[1] = y_ned
        self.fp_pos_ned[2] = z_ned

        self.fp_yaw_ned = enu_yaw_to_ned(msg.yaw)
        self.fp_yaw_dot_ned = -msg.yaw_dot

        # velocity + acceleration feedforward (ENU vector -> NED, same transform as position)
        vx, vy, vz = enu_pos_to_ned(msg.velocity.x, msg.velocity.y, msg.velocity.z)
        ax, ay, az = enu_pos_to_ned(msg.acceleration.x, msg.acceleration.y, msg.acceleration.z)
        self.fp_vel_ned[:] = [vx, vy, vz]
        self.fp_acc_ned[:] = [ax, ay, az]
        self.fp_ff_valid = all(math.isfinite(v) for v in (vx, vy, vz, ax, ay, az))

        self.last_fp_time_ns = now_ns

    def keyboard_command_callback(self, msg: String):
        cmd = msg.data.strip().upper()

        if cmd == "OFFBOARD":
            if not self.req_offboard:
                # 새로 OFFBOARD 요청 시 counter 초기화 → setpoint 10회 재적립 보장
                self.offboard_setpoint_counter = 0
            self.req_offboard = True

        elif cmd == "ARM":
            self.req_arm = True

        elif cmd == "DISARM":
            self.req_arm = False
            self.req_offboard = False
            self.disarm()
            # 위치 기준 재초기화 (EKF valid 이후에 재취득)
            self.got_local_pos = False
            # counter는 OFFBOARD 명령 시점에 초기화하므로 여기선 건드리지 않음

        elif cmd == "LAND":
            self.req_arm = False
            self.req_offboard = False
            self.land()

        elif cmd == "POS":
            self.control_mode = "POSITION"
            # 현재 위치 hold
            self.sp_pos_ned[0] = self.vehicle_local_position.x
            self.sp_pos_ned[1] = self.vehicle_local_position.y
            self.sp_pos_ned[2] = self.vehicle_local_position.z
            self.sp_yaw_ned = self.vehicle_local_position.heading

        elif cmd == "VEL":
            self.control_mode = "VELOCITY"
            self.body_vel_frd[:] = 0.0
            self.yaw_rate_ned = 0.0

        elif cmd == "BREAK":
            # 속도 0으로 정지
            self.body_vel_frd[:] = 0.0
            self.yaw_rate_ned = 0.0

        elif cmd == "FAST-PLANNER":
            self.control_mode = "FAST-PLANNER"

    # -------------------------------
    # PX4 command helpers
    # -------------------------------
    def publish_vehicle_command(self, command: int, **params):
        msg = VehicleCommand()
        msg.command = command
        msg.param1 = float(params.get("param1", 0.0))
        msg.param2 = float(params.get("param2", 0.0))
        msg.param3 = float(params.get("param3", 0.0))
        msg.param4 = float(params.get("param4", 0.0))
        msg.param5 = float(params.get("param5", 0.0))
        msg.param6 = float(params.get("param6", 0.0))
        msg.param7 = float(params.get("param7", 0.0))
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)  # us
        self.vehicle_command_pub.publish(msg)

    def arm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
        self.get_logger().info("Arm command sent")

    def disarm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=0.0)
        self.get_logger().info("Disarm command sent")

    def engage_offboard_mode(self):
        # param1=1: custom mode, param2=6: PX4 offboard
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)
        self.get_logger().info("Switching to offboard mode")

    def land(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info("Switching to land mode")

    # -------------------------------
    # Publishing setpoints
    # -------------------------------
    def publish_offboard_control_heartbeat_signal(self, effective_mode: str):
        msg = OffboardControlMode()
        if effective_mode == "VELOCITY":
            msg.position = False
            msg.velocity = True
            msg.acceleration = False
        elif effective_mode == "FAST-PLANNER":
            if self.use_so3:
                # SO3 geometric control: we publish a desired attitude + collective thrust
                # (PX4 runs only its attitude/rate loop). Faithful tracking of SUPER's path.
                msg.position = False
                msg.velocity = False
                msg.acceleration = False
                msg.attitude = True
                msg.body_rate = False
                msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
                self.offboard_control_mode_pub.publish(msg)
                return
            # position (z pinned) + velocity + acceleration FF. The accel flag must be set
            # for PX4 to USE the accel FF (gravity-compensated tilt thrust that holds
            # altitude on a forward pitch).
            msg.position = True
            msg.velocity = True
            msg.acceleration = True
        else:  # POSITION (hover hold)
            msg.position = True
            msg.velocity = False
            msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)  # us
        self.offboard_control_mode_pub.publish(msg)

    def publish_position_setpoint(self):
        nan3 = [float("nan"), float("nan"), float("nan")]

        msg = TrajectorySetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)

        msg.position = [float(self.sp_pos_ned[0]), float(self.sp_pos_ned[1]), float(self.sp_pos_ned[2])]
        msg.velocity = nan3
        msg.acceleration = nan3
        if hasattr(msg, "jerk"):
            msg.jerk = nan3

        msg.yaw = float(self.sp_yaw_ned)
        msg.yawspeed = float("nan")

        self.trajectory_setpoint_pub.publish(msg)

    def publish_velocity_setpoint(self):
        nan3 = [float("nan"), float("nan"), float("nan")]

        # body FRD -> world NED (heading만 사용: roll/pitch 무시)
        vx = float(self.body_vel_frd[0])  # forward
        vy = float(self.body_vel_frd[1])  # right
        vz = float(self.body_vel_frd[2])  # down

        cy = math.cos(self.trueYaw)
        sy = math.sin(self.trueYaw)

        vN = vx * cy - vy * sy
        vE = vx * sy + vy * cy
        vD = vz

        msg = TrajectorySetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)

        msg.position = nan3
        msg.velocity = [vN, vE, vD]
        msg.acceleration = nan3
        if hasattr(msg, "jerk"):
            msg.jerk = nan3

        msg.yaw = float("nan")
        msg.yawspeed = float(self.yaw_rate_ned)

        self.trajectory_setpoint_pub.publish(msg)

    def publish_fastplanner_setpoint(self):
        nan3 = [float("nan"), float("nan"), float("nan")]

        msg = TrajectorySetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)

        # xy from SUPER, z PINNED to the fixed cruise altitude (constant-altitude study).
        msg.position = [float(self.fp_pos_ned[0]), float(self.fp_pos_ned[1]), float(self.fp_hold_z_ned)]
        # xy velocity + acceleration feed-forward (with the accel flag set in the heartbeat
        # so PX4 actually USES it: the accel FF carries the gravity-compensated tilt thrust
        # that holds altitude on a forward pitch). Vertical FF zeroed -- z is held by the
        # pinned position setpoint. PX4 MPC_TILTMAX_AIR is lowered (g_bringup) so the drone
        # can't pitch hard enough to lose altitude on sharp corner turns.
        if self.fp_ff_valid:
            msg.velocity = [float(self.fp_vel_ned[0]), float(self.fp_vel_ned[1]), 0.0]
            msg.acceleration = [float(self.fp_acc_ned[0]), float(self.fp_acc_ned[1]), 0.0]
        else:
            msg.velocity = nan3
            msg.acceleration = nan3
        if hasattr(msg, "jerk"):
            msg.jerk = nan3

        msg.yaw = float(self.fp_yaw_ned)
        msg.yawspeed = float(self.fp_yaw_dot_ned)

        self.trajectory_setpoint_pub.publish(msg)

    @staticmethod
    def _rotmat_to_quat(R):
        """world-from-body rotation matrix (columns = body axes in world) -> [w,x,y,z]."""
        tr = R[0, 0] + R[1, 1] + R[2, 2]
        if tr > 0.0:
            S = math.sqrt(tr + 1.0) * 2.0
            w = 0.25 * S
            x = (R[2, 1] - R[1, 2]) / S
            y = (R[0, 2] - R[2, 0]) / S
            z = (R[1, 0] - R[0, 1]) / S
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
            w = (R[2, 1] - R[1, 2]) / S
            x = 0.25 * S
            y = (R[0, 1] + R[1, 0]) / S
            z = (R[0, 2] + R[2, 0]) / S
        elif R[1, 1] > R[2, 2]:
            S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
            w = (R[0, 2] - R[2, 0]) / S
            x = (R[0, 1] + R[1, 0]) / S
            y = 0.25 * S
            z = (R[1, 2] + R[2, 1]) / S
        else:
            S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
            w = (R[1, 0] - R[0, 1]) / S
            x = (R[0, 2] + R[2, 0]) / S
            y = (R[1, 2] + R[2, 1]) / S
            z = 0.25 * S
        n = math.sqrt(w * w + x * x + y * y + z * z)
        return [w / n, x / n, y / n, z / n]

    def publish_fastplanner_so3(self):
        """SUPER-native SO3 geometric controller -> PX4 VehicleAttitudeSetpoint."""
        g = self.so3_grav
        lp = self.vehicle_local_position
        pos = np.array([lp.x, lp.y, lp.z], dtype=float)        # world NED
        vel = np.array([lp.vx, lp.vy, lp.vz], dtype=float)

        # desired state (world NED): xy/yaw from SUPER, z pinned to cruise altitude
        des_pos = np.array([self.fp_pos_ned[0], self.fp_pos_ned[1], self.fp_hold_z_ned], dtype=float)
        if self.fp_ff_valid:
            des_vel = np.array([self.fp_vel_ned[0], self.fp_vel_ned[1], 0.0], dtype=float)
            des_acc = np.array([self.fp_acc_ned[0], self.fp_acc_ned[1], 0.0], dtype=float)
        else:
            des_vel = np.zeros(3)
            des_acc = np.zeros(3)

        e_p = pos - des_pos
        # position -> velocity command, SATURATED (prevents the over-speed/overshoot that
        # pushed the drone off SUPER's path into a tight obstacle gap)
        v_cmd = des_vel - self.so3_Kp_pos * e_p
        vh = math.hypot(v_cmd[0], v_cmd[1])
        if vh > self.so3_vmax_h:
            v_cmd[0] *= self.so3_vmax_h / vh
            v_cmd[1] *= self.so3_vmax_h / vh
        v_cmd[2] = max(-self.so3_vmax_v, min(self.so3_vmax_v, v_cmd[2]))

        # altitude integral trim (e_p[2] > 0 means too low -> negative a_des_z = up)
        self.so3_iz = max(-self.so3_iz_max,
                          min(self.so3_iz_max, self.so3_iz + e_p[2] * self.so3_dt))

        # velocity -> acceleration
        a_des = des_acc + self.so3_Kv * (v_cmd - vel)            # world NED
        a_des[2] += -self.so3_Ki_z * self.so3_iz

        # altitude-floor protection: below the floor, suppress horizontal accel so the
        # drone stays level and climbs out (avoids sinking below virtual_ground -> wedge)
        alt = -pos[2]
        if alt < self.so3_alt_floor:
            k = max(0.0, alt / self.so3_alt_floor) * 0.5   # 0 at ground .. 0.5 at floor
            a_des[0] *= k
            a_des[1] *= k

        # T*b3 = g*e3 - a_des  (e3 = [0,0,1] down). b3 = desired body-z (down) axis.
        tdir = np.array([-a_des[0], -a_des[1], g - a_des[2]], dtype=float)
        T_mag = float(np.linalg.norm(tdir))
        if T_mag < 1e-3:
            tdir = np.array([0.0, 0.0, 1.0], dtype=float)
            T_mag = g
        b3 = tdir / T_mag

        # cap the commanded tilt (PX4 MPC_TILTMAX_AIR does NOT apply in attitude offboard)
        tilt = math.acos(max(min(b3[2], 1.0), -1.0))
        if tilt > self.so3_tilt_max:
            hdir = np.array([b3[0], b3[1], 0.0])
            hn = float(np.linalg.norm(hdir))
            if hn > 1e-6:
                hdir = hdir / hn
                b3 = np.array([hdir[0] * math.sin(self.so3_tilt_max),
                               hdir[1] * math.sin(self.so3_tilt_max),
                               math.cos(self.so3_tilt_max)], dtype=float)

        # build desired attitude from b3 + desired yaw (NED)
        # FIXED-YAW mode: hold a constant heading (decoupled from velocity). This exposes
        # the forward ±60° sector's blindspot on legs where motion is NOT along the heading
        # (the cone faces away from where the drone is going) -> forward-only sensing misses
        # obstacles in the path -> the regime where adaptive full-view recovery is needed.
        yaw = self.fixed_yaw_ned if self.fixed_yaw_en else self.fp_yaw_ned
        b1_des = np.array([math.cos(yaw), math.sin(yaw), 0.0], dtype=float)
        b2 = np.cross(b3, b1_des)
        b2n = float(np.linalg.norm(b2))
        if b2n < 1e-4:                       # b3 ~ parallel to b1_des: pick any heading
            b1_des = np.array([1.0, 0.0, 0.0], dtype=float)
            b2 = np.cross(b3, b1_des)
            b2n = float(np.linalg.norm(b2))
        b2 = b2 / b2n
        b1 = np.cross(b2, b3)
        R = np.column_stack((b1, b2, b3))
        q = self._rotmat_to_quat(R)

        thr_norm = self.so3_hover_thr * T_mag / g
        thr_norm = max(0.05, min(self.so3_thr_max, thr_norm))

        msg = VehicleAttitudeSetpoint()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        msg.q_d = [float(q[0]), float(q[1]), float(q[2]), float(q[3])]
        msg.thrust_body = [0.0, 0.0, float(-thr_norm)]   # body FRD: up = -z
        msg.yaw_sp_move_rate = 0.0 if self.fixed_yaw_en else float(self.fp_yaw_dot_ned)
        self.attitude_setpoint_pub.publish(msg)

        # diagnostic (3 Hz): why does altitude sink during maneuvers?
        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self.last_log_ns > int(0.33 * 1e9):
            self.last_log_ns = now_ns
            self.get_logger().info(
                "SO3 z=%.2f zdes=%.2f vz=%.2f aZ=%.2f thr=%.2f tilt=%.0f ff=%d eP=%.2f" % (
                    -pos[2], -des_pos[2], vel[2], a_des[2], thr_norm,
                    math.degrees(math.acos(max(min(b3[2], 1.0), -1.0))),
                    int(self.fp_ff_valid), float(np.linalg.norm(e_p))))

    # -------------------------------
    # Main loop
    # -------------------------------
    def timer_callback(self):
        # local position 아직 못 받았으면(heading/원점 불명) setpoint 발행하지 않는게 안전
        if not self.got_local_pos:
            return

        now_ns = self.get_clock().now().nanoseconds

        # planner alive 판단
        fp_alive = (now_ns - self.last_fp_time_ns) < int(0.5 * 1e9)

        # effective mode 결정
        if fp_alive:
            effective_mode = "FAST-PLANNER"
        else:
            effective_mode = self.control_mode

        # heartbeat
        self.publish_offboard_control_heartbeat_signal(effective_mode)

        # setpoint publish
        if effective_mode == "FAST-PLANNER":
            if self.use_so3:
                if not self._fp_was_alive:
                    self.so3_iz = 0.0          # fresh integrator on (re)activation
                self.publish_fastplanner_so3()
            else:
                self.publish_fastplanner_setpoint()
            self._fp_was_alive = True
        elif effective_mode == "VELOCITY":
            self._fp_was_alive = False
            self.publish_velocity_setpoint()
        else:
            self._fp_was_alive = False
            self.publish_position_setpoint()

        # offboard 요구 시: 먼저 setpoint 10번 이상 보낸 뒤에 mode 전환
        self.offboard_setpoint_counter = min(self.offboard_setpoint_counter + 1, 50)

        if self.req_offboard and self.vehicle_status.nav_state != VehicleStatus.NAVIGATION_STATE_OFFBOARD:
            if self.offboard_setpoint_counter >= 10:
                if now_ns - self.last_mode_cmd_ns > int(1e9):
                    self.engage_offboard_mode()
                    self.last_mode_cmd_ns = now_ns

        # arm 요구 시: offboard 상태에서 arm 반복
        ARMED_STATE = getattr(VehicleStatus, "ARMING_STATE_ARMED", 2)
        if self.req_arm and self.vehicle_status.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD:
            if self.vehicle_status.arming_state != ARMED_STATE:
                if now_ns - self.last_arm_cmd_ns > int(1e9):
                    self.arm()
                    self.last_arm_cmd_ns = now_ns


def main(args=None):
    rclpy.init(args=args)
    node = OffboardControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node interrupted, shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()