# offboard.py altitude-hold + corner-stability tuning (px4_control_ws)

`px4_keyboard_control/offboard.py` feeds SUPER's trajectory to PX4 as **position +
xy velocity/acceleration feed-forward** TrajectorySetpoints (PX4 position controller),
NOT via SUPER's native geometric (attitude+thrust) controller. This file records what
makes the drone hold altitude and where the position-level interface hits its limit.

## What was fixed (altitude hold on forward flight) — SOLVED

1. **The acceleration feed-forward was being IGNORED.** `OffboardControlMode` had
   `acceleration=False`, so PX4 dropped the accel setpoint and tracked on its position
   PID alone -> on a forward pitch it lost vertical thrust and sank. Fix — in
   `publish_offboard_control_heartbeat_signal`, FAST-PLANNER case:
       msg.position = True; msg.velocity = True; msg.acceleration = True
   The accel FF carries the gravity-compensated tilt thrust that holds altitude.

2. **Pin z to a fixed cruise altitude** (constant-altitude lateral study). SUPER's
   MINCO z dips on aggressive turns and the position controller can't recover in time:
       self.fp_hold_alt   = declare_parameter("hold_altitude", 1.5)
       self.fp_hold_z_ned = -self.fp_hold_alt
       # publish_fastplanner_setpoint:
       msg.position     = [fp_pos_ned[0], fp_pos_ned[1], self.fp_hold_z_ned]
       msg.velocity     = [fp_vel_ned[0], fp_vel_ned[1], 0.0]   # zero vertical FF
       msg.acceleration = [fp_acc_ned[0], fp_acc_ned[1], 0.0]   # az=0; PX4 adds gravity

3. **Gentle dynamics + tilt cap** so PX4 can track and can't pitch hard enough to sink:
   - config static_gazebo.yaml: `max_vel 1.5, max_acc 3.5, max_jerk 25, yaw_dot_max 1.5`
     (yaw lowered 3.0->1.5: a perimeter corner swings the velocity heading ~135 deg; the
     fast yaw snap coincided with the altitude sink).
   - PX4 params (g_bringup.sh): `MPC_TILTMAX_AIR 25` (cap tilt -> keep vertical thrust),
     `COM_DISARM_LAND -1` (never auto-disarm on a ground brush), `MPC_Z_VEL_MAX_UP 4`
     (climb back fast after a dip).

RESULT: in open / straight flight the drone now holds z ~= 1.5 m rock-steady, and it
reaches perimeter corners (verified on seed9: corners 1 and 3 reached at z ~= 1.5).

## What does NOT work yet — corner / obstacle-field thrashing (the limit)

A SO3 **acceleration-only** geometric controller was tried (PX4 converts accel ->
attitude+thrust; position/velocity flags off, a_des = a_ff + Kp*pos_err + Kv*vel_err).
It was **unstable** -- with no PX4 position anchor the PD + attitude lag oscillated and
the drone crashed. Reverted to the position+FF scheme above.

The residual failure mode is **thrashing**: near a corner / in the 100-obstacle field
SUPER replans rapidly and the drone weaves in 2-3 m swings; the position controller
lags the aggressive path, the altitude dips, and a deep dip can brush an obstacle/ground
and stick (below `virtual_ground` SUPER can no longer plan -> the run stalls). This
happens even on the *sparse* seed (seed9), so it is the **control-interface limit, not
obstacle density**: position-level offboard cannot faithfully track SUPER's native
aggressive MINCO trajectories.

## Recommended real fix

SUPER was designed for a **geometric attitude+thrust (SO3)** controller. To get fully
clean dense-field loops, drive PX4 with `VehicleAttitudeSetpoint` (desired quaternion +
normalised collective thrust) computed by an SO3 controller from `/planning/pos_cmd`
(force = m*(g*e3 + a_des + Kx*e_p + Kv*e_v); thrust_norm = MPC_THR_HOVER * |force|/(m*g)).
This is the architecturally correct interface; the position-level path here is a
workaround whose tracking envelope is the bottleneck. Alternatives if staying on the
position interface: lower obstacle count, or accept the A/B/C comparison with
matched dips (same control limits for sector ON/OFF, so the *relative* mapping-cost
comparison and the G6 fixed-pose result remain valid).
