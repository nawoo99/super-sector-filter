# SUPER-native SO3 flight control (px4_control_ws/offboard.py)

**Status: WORKING.** seed9 flies a full clean perimeter loop — `success=True,
corners_reached=4, timeouts=0`, holding z ~= 1.5 m on every open leg and recovering
from the dips near corners/clusters. The working controller is committed at
[controller/offboard.py](../controller/offboard.py).

## Why the earlier (position-setpoint) approach failed

Feeding SUPER's trajectory to PX4 as **position** TrajectorySetpoints (PX4 position
PID) could not track SUPER's aggressive avoidance: the drone thrashed and its altitude
sank/wedged. Pinning z + accel feed-forward + PX4 tilt caps helped straight flight but
corners still sank. Root cause is the interface: SUPER is a geometric planner meant for
an attitude+thrust controller, not a position PID.

## The fix: SO3 geometric controller -> PX4 VehicleAttitudeSetpoint

`offboard.py`, FAST-PLANNER mode, now drives PX4's attitude loop directly
(`OffboardControlMode.attitude=True`, publish `VehicleAttitudeSetpoint` on
`/fmu/in/vehicle_attitude_setpoint_v1`). Per tick, in world NED:

1. **Cascaded P(pos) -> saturated velocity -> P(vel) -> accel** (the saturation stops
   the over-speed that made the drone overshoot SUPER's path into a tight gap):
   `v_cmd = des_vel - Kp_pos*(pos-des_pos)`, clamp `|v_cmd|` to `vmax`;
   `a_des = des_acc + Kv*(v_cmd - vel)`. xy from SUPER, z pinned to 1.5 m.
2. **Altitude integral trim** on `a_des_z` — kills the steady-state sag from an
   imperfect hover-thrust estimate (reset on FAST-PLANNER re-activation).
3. **Altitude-floor protection** — below `alt_floor` (0.85 m) scale the horizontal
   `a_des` toward 0 so the drone stays level and puts all thrust into lift, climbing
   out BEFORE it sinks under `virtual_ground` (where SUPER stops planning -> wedge).
   This is what turns a clip/dip into a recovery instead of a dead run.
4. **Thrust direction & magnitude** (mass cancels!):
   `tdir = g*e3 - a_des`; `b3 = tdir/|tdir|`; cap tilt to 30 deg;
   `q_d` from `b3` + desired yaw; `thr = hover_thr*|tdir|/g`, clamp to `thr_max`.

### Two calibration facts that mattered

- **The x500 carries the 3D LiDAR -> it is heavy (true hover ~0.82 of full thrust,
  TWR ~1.2).** The thrust clamp must leave real head-room: at 0.90 the drone could not
  hold altitude once it tilted past ~20 deg (vertical thrust = thr*cos) and it sank.
  Fix: `thr_max = 0.98`, and keep `hover_thr = 0.70` as a LOW feed-forward and let the
  integrator trim up (setting 0.82 directly over-thrust and oscillated).
- **Collisions, not thrust, caused the deep sinks.** Diagnostic logging showed the
  controller commanding full up-thrust while the drone was still forced down = an
  external (obstacle) contact. The ~0.3 m position tracking error was clipping obstacles
  in the tight field. Addressed by the altitude-floor recovery + corner clearance +
  keeping inflation at 0.3 (0.4 over-constrained the field and SUPER took erratic
  detours).

## Companion changes (this repo)

- `config/static_gazebo.yaml`: `max_vel 1.2, max_acc 3.5, max_jerk 25, yaw_dot_max 1.5`,
  `inflation_step 3` (0.3 m).
- `scripts/g_bringup.sh` PX4 params: `MPC_TILTMAX_AIR 25` (unused in attitude offboard
  but harmless), `COM_DISARM_LAND -1` (survive a ground brush), `MPC_Z_VEL_MAX_UP 4`.
- `scripts/gen_world.py`: `CORNER_CLEAR 2.5` — room for the ~135 deg corner turn
  (obstacles at 1.5 m were being clipped mid-turn). Uniform across seeds -> fair A/B.

Enable/disable via the `use_so3` ROS param (default true; false = old position path).
Tunables are ROS params: `hover_thrust`, and in-code `so3_*` gains / `so3_alt_floor`.
