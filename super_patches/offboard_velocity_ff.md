# offboard.py velocity+acceleration feedforward (px4_control_ws)

The FAST-PLANNER path of `px4_keyboard_control/offboard.py` tracked SUPER's
trajectory with POSITION only -> altitude drooped into the ground on fast legs.
Fix: forward the planner's velocity + acceleration (already carried in the cmd by
cmd_bridge) as feedforward in the PX4 TrajectorySetpoint.

In `fastplanner_callback`, after the position/yaw conversion:
    vx, vy, vz = enu_pos_to_ned(msg.velocity.x, msg.velocity.y, msg.velocity.z)
    ax, ay, az = enu_pos_to_ned(msg.acceleration.x, msg.acceleration.y, msg.acceleration.z)
    self.fp_vel_ned[:] = [vx, vy, vz]; self.fp_acc_ned[:] = [ax, ay, az]
    self.fp_ff_valid = all(math.isfinite(v) for v in (vx, vy, vz, ax, ay, az))

In `publish_fastplanner_setpoint`, replace velocity/acceleration NaN with:
    if self.fp_ff_valid:
        msg.velocity = [float(self.fp_vel_ned[i]) for i in range(3)]
        msg.acceleration = [float(self.fp_acc_ned[i]) for i in range(3)]
