# Hybrid adaptive sector and recovery diagnostics

## Filter modes

`native_sector.py` now separates the final design from its ablations:

| mode | closed-view centre | stall expansion |
|---|---|---|
| `full` | 360 degrees | always full |
| `sector` | body yaw, +/-60 degrees | none |
| `velocity` | last reliable cruise velocity, +/-60 degrees | none |
| `trigger` | body yaw, +/-60 degrees | full view after a stall |
| `adaptive` | last reliable cruise velocity, +/-60 degrees | full view after a stall |

Both triggered modes use the same state thresholds:

1. Start closed. This prevents launch idle from being counted as a stall.
2. Arm only after speed stays above `1.5 m/s` for `2.0 s`.
3. Open to 360 degrees after armed speed stays below `0.6 m/s` for `1.2 s`.
4. Return to the closed sector after speed stays above `1.5 m/s` for `2.0 s`.

For `velocity` and closed `adaptive`, cone direction updates only above the
same `1.5 m/s` cruise threshold and is held below it. This avoids chasing a
noisy low-speed direction and makes the closed-policy ablation identical in
both modes. Seed12/13's 2--3 m/s preventive alignment is unchanged.

Thus `adaptive` keeps the already validated preventive behaviour on seed12/13
and adds a reactive recovery path. `velocity` preserves the previous
velocity-only adaptive implementation as a clean ablation.

## Seed14 and seed15

The two recovery cases are deterministic, mirrored state-machine diagnostics.
They combine an odometry-triggered barrier with a controlled approach and hold;
neither component reads filter mode, armed state, full-open state, or planner
state.

- The vehicle starts at `(0, 0, 1.5)` and receives an approach goal at
  `(20, 0, 1.5)`. On entering a `0.4 m` horizontal radius, the mission driver
  keeps that goal until odometry speed has stayed below `0.6 m/s` for `1.6 s`.
  It then releases seed14 toward `(40, 1, 1.5)` and seed15 toward
  `(40, -1, 1.5)`. The same goal sequence and hold rule are used for every
  filter mode.
- The static PCD contains only one harmless cylinder at `(-20, 0)`, outside the
  initial `15 m` horizon. The recovery barrier therefore cannot be pre-mapped.
- When odometry first crosses `x=18 m`, the injector permanently adds a
  47-cylinder rear-open U pocket to `/cloud_registered` before sector filtering. It is
  translated and rotated into the trigger velocity frame, so arbitrary bends
  in SUPER's obstacle-free prefix do not change the intended sensor geometry.
- The front wall is `6 m` forward, side walls are at lateral `+/-1.5 m`, and
  extend back to forward `-4 m`, where the pocket is open. Full view sees the
  rear exit immediately. A closed forward velocity sector sees only the front
  and forward side walls; the rear endpoints are about `156 degrees` away and
  remain hidden when low-speed cone direction is held. Seed14/15 reverse the
  endpoint ordering but are geometrically mirrored pairs.
- The x-crossing is accepted only after speed has previously stayed strictly
  above `1.5 m/s` for `2.1 s`, current speed is still above `1.5 m/s`, and a
  velocity direction is available. The cruise qualification latches just like
  the filter's armed state, so a later brief speed change does not erase valid
  prior cruise. These odometry-only checks are applied identically to every
  mode. A failed check
  records `recovery_spawn_invalid` and never spawns the wall later, preventing
  a launch-idle or post-stall run from being misclassified.
- The recovery configs use fixed map origin `(20, 0, 1.5)` and a `13 m`
  planning horizon. This covers the useful local bypass geometry without the
  A* blow-up observed with an `18 m` horizon. Recovery-only speed is capped at
  `2.0 m/s` (still above the `1.5 m/s` arm threshold), and the occupancy
  inflation margin is `0.6 m` so sampled tangent surfaces cannot become a
  numerical seam.

The `1.6 s` hold deliberately guarantees enough low-speed time to exercise the
`1.2 s` opening branch. This makes seed14/15 an integration and recovery-path
diagnostic, not evidence that the trigger detects an unexpected popup more
quickly or that the pocket naturally causes the stall. Seed12/13 remain the
unexpected-obstacle safety tests. A seed14/15 run is valid only if the full-view
baseline completes the same hold, the wall spawns after the hybrid has armed,
and adaptive records an open transition during HOLD before the final goal is
released.

## Run protocol

First inspect one run in RViz:

```bash
bash scripts/watch_native.sh adaptive seed14
bash scripts/watch_native.sh adaptive seed15
```

Then run a small signal check before any large campaign:

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed14 seed15 \
  --modes full sector velocity trigger adaptive \
  --runs 3 \
  --out results/native_recovery_seed14_15_n3.csv
```

Do not run `watch_native.sh` and `native_campaign.py` concurrently; both own the
same simulator and ROS node names. They now share an exclusive lock, so a
second launcher exits with an error instead of killing the first launcher's
nodes during cleanup.

The current one-run integration smoke is stored in
[`results/native_recovery_seed14_15_controlled_smoke.csv`](../results/native_recovery_seed14_15_controlled_smoke.csv):

| map | mode | success / collisions | mission time | kept points | full-view frame duty | open delay | pocket clearance |
|---|---|---:|---:|---:|---:|---:|---:|
| seed14 | full | true / 0 | 33.73 s | 100.00% | 100.00% | n/a | 0.316 m |
| seed14 | adaptive | true / 0 | 33.61 s | 30.54% | 9.78% | 1.200 s | 0.446 m |
| seed15 | full | true / 0 | 36.57 s | 100.00% | 100.00% | n/a | 0.323 m |
| seed15 | adaptive | true / 0 | 35.50 s | 24.49% | 8.83% | 1.216 s | 0.493 m |

Both adaptive rows also record one arm, open, and close transition in the
required time order. This is an `n=1` integration check, not a collision-rate or
timing comparison; use repeated runs for statistical claims.

For `adaptive`, the minimum acceptance evidence is:

- the event JSON records `valid_spawn = true` after cruise arming;
- `filter_arm_transitions >= 1`;
- `filter_open_transitions >= 1`;
- `recovery_open_after_spawn = true` (not an approach-waypoint stall);
- `recovery_open_during_hold = true` and `mission_driver_phase = final`;
- `recovery_reclosed = true` after the final goal releases motion;
- mission success without collision;

The CSV also records full-view frame/point duty, kept-point percentage, first
stall candidate time, first open time, and stall-to-open delay. Compare mission
success, collision/clearance, recovery time, full-view duty, and kept percentage
together. A successful mission without an open transition does **not** validate
the stall-recovery mechanism; it means the map needs redesign or should be
reported only as a nominal navigation case.

Seed12/13 remain the fast-turn blind-sector tests. In those maps the vehicle is
still moving quickly when the trap appears, so the stall branch should remain
closed and hybrid `adaptive` should behave like `velocity`. Seed14/15 isolate
the complementary recovery branch.

Existing CSV files produced when `adaptive` meant velocity-only must not be
silently pooled with new hybrid results. Keep the implementation/mode version
with every reported campaign and write new runs to a new output file.
