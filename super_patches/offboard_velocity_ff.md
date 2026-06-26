# offboard.py altitude-hold fix (px4_control_ws)

`px4_keyboard_control/offboard.py` feeds SUPER's trajectory to PX4 as **position**
TrajectorySetpoints (PX4 position controller), NOT via SUPER's native geometric
(attitude+thrust) controller. On forward legs the drone **sank into the ground**
(verified by logging: SUPER commanded z~1.5 but the drone fell to z<0), then —
below the virtual ground — SUPER could no longer plan (PlanFromRest TIME_OUT loop)
and the run stalled. Root cause + fix, in order of impact:

1. **The acceleration feed-forward was being IGNORED.** `OffboardControlMode` had
   `acceleration=False`, so PX4 dropped the accel setpoint and tracked on its
   position PID alone -> on a forward pitch it lost vertical thrust and sank.
   Fix — in `publish_offboard_control_heartbeat_signal`, add a FAST-PLANNER case:
       msg.position = True; msg.velocity = True; msg.acceleration = True
   The accel FF carries the gravity-compensated tilt thrust that holds altitude.

2. **Pin the z setpoint to a fixed cruise altitude.** This is a constant-altitude
   (lateral) study, but SUPER's MINCO z dips on aggressive avoidance turns and the
   position-level controller can't recover the altitude in time. Force z, let SUPER
   own xy:
       self.fp_hold_alt = float(self.declare_parameter("hold_altitude", 1.5).value)
       self.fp_hold_z_ned = -self.fp_hold_alt
       # in publish_fastplanner_setpoint:
       msg.position = [fp_pos_ned[0], fp_pos_ned[1], self.fp_hold_z_ned]
       msg.velocity = [fp_vel_ned[0], fp_vel_ned[1], 0.0]        # zero vertical FF
       msg.acceleration = [fp_acc_ned[0], fp_acc_ned[1], 0.0]    # az=0; PX4 adds gravity

3. **Gentle dynamics** so PX4 can actually track (config static_gazebo.yaml):
   max_vel ~2.5, max_acc ~5. Higher accel reaches corners but sinks; lower accel
   holds altitude but the drone circles waypoints -- a control-quality trade-off of
   the position-level offboard vs SUPER's native attitude+thrust controller.

RESULT: the drone now cruises at 1.5 m through the obstacle field and recovers from
dips (was: immediate, unrecoverable sink). NOT bulletproof -- prolonged aggressive
maneuvering (corner thrashing) can still sink it. A fully clean loop would need
SUPER's geometric controller (attitude+thrust) or PX4 controller tuning.
