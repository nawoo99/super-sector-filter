# G1 Full: ordinary handoff rejection cause audit

Date: 2026-09-26. The original read-only partial snapshot below is preserved;
the **finalized Full addendum** at the end supersedes its live counts. No source,
configuration, gate or flight process was modified during this audit.

Run: `gapfree_d1_m01_run80000_full.attempt1`.
Live evidence prefix: `/tmp/scenario7_n10_zqj6l8k6/`.
Captured stack log size: 2,364,227 characters; last parsed result WT
1790433610.3005903, id 1086. Odometry cutoff: elapsed 144.785534 s.

## Findings at the partial cutoff

| Observation | Value |
|---|---:|
| Async results computed | 1086 |
| Completed/accepted async results | 0 |
| Handoff rejection log entries | 1086 |
| Reported handoff reason | POSITION_DISCONTINUITY for all 1086 |
| Position error min / median / max | 0.043510213 / 0.045424912 / 0.261345435 m |
| Velocity error min / median / max | 0.023653921 / 0.122603762 / 2.686828751 m/s |
| Acceleration error min / median / max | 1.395315402 / 4.379949706 / 19.647409598 m/s^2 |
| Odometry samples | 14,478 |
| Every recorded position | (0, 0, 1.5) m |
| Every recorded odometry velocity | (0, 0, 0) m/s |
| Emergency async requests / recovered markers | 0 / 0 |

`computed=true` means PlanFromRest ran, not that every attempt constructed a
new valid path. The last observed candidate generation was 1076 versus request
1086; the rejection statistics include finalization attempts without generation
advance. The first attempt did advance generation 0 → 1 and was rejected with
P=0.044039532 m, V=0.060479913 m/s, A=2.820458656 m/s^2.

Using the first/last periodic profiler snapshots over 140.130584130 seconds:

| Callback | Calls delta | Measured callback frequency |
|---|---:|---:|
| main FSM | 14,013 | 99.999583 Hz |
| command timer | 14,013 | 99.999583 Hz |
| replan executor | 2,103 | 15.007430 Hz |

These are callback invocation counts, **not published PositionCommand counts**.
The partial log has no enabled command-trace publication counter from which an
actual command count can be established. The planner remains in the initial
quarantine (generation-zero prior hold), and its gated ordinary path therefore
does not authorize an executable new trajectory. Odometry confirms no movement.
Restored timer frequency does not imply planning progress or a passed mission.

## Independent spatial-origin mismatch, not just the solve clock

The production source path is explicit:

1. `super_planner/src/super_core/super_planner.cpp:2701` calls
   `getNearestCellNot(OCCUPIED, robot_state_.p, local_star_pt, 3.0)` even when
   the physical starting pose is already unoccupied.
2. `rog_map/src/rog_map/rog_map.cpp:704–718` converts that position to an index,
   iterates candidate index offsets, converts each index back to a **cell
   centre**, and returns the first nonoccupied centre. There is no return of
   the original continuous position.
3. `rog_map/CMakeLists.txt:21` selects `ORIGIN_AT_CORNER`;
   `rog_map/src/rog_map/sliding_map.cpp:177–205` uses floor(position/resolution)
   and reconstructs `(index + 0.5) * resolution`.
4. Runtime log confirms resolution=0.05 m. For the actual held pose (0,0,1.5),
   every grid centre has at least 0.025 m absolute offset in each coordinate.
   Even the nearest possible centre is sqrt(3)*0.025 = **0.043301270189 m** away.
   This lower bound does not depend on whether that nearest centre is free:
   choosing another centre cannot reduce it.
5. `super_planner.cpp:2793` copies this snapped point into `local_start_p_`.
   At `3222–3223`, fresh EXP initialization is zero PVAJ except position exactly
   `local_start_p_`; it is not the pinned physical/commanded held position.

Thus a hypothetical perfect zero-delay solve or timestamp rebase to tt=0 would
still start the commanded trajectory at least 43.3 mm away from the held pose,
far beyond the unchanged 1 mm handoff tolerance. The approximately 43.5 mm
observed minimum is consistent with this separate geometric-start defect.
This is not proof of the exact returned nearest centre in every attempt; those
coordinates were not emitted in the partial log. The source and grid arithmetic
do establish that no returned centre can equal this physical starting pose.

The source already recognizes this distinction in the separate certified
vertical-recovery branch (`super_planner.cpp:2579`): it constructs its lift from
the actual stationary odometry position rather than the nearest grid start.
That fix is local to the lift, not ordinary EXP initialization.

## The clock mismatch also remains real

`generateExpTraj` assigns the candidate's start wall time to the solve-start
time (`super_planner.cpp:3846–3858`). Finalization samples it later while the
physical vehicle has remained held. Nonzero velocity and acceleration in the
rejection diagnostics are consequently a separate temporal departure issue.
At the observed cutoff even the minimum velocity and acceleration errors exceed
the unchanged 0.01 m/s and 0.1 m/s^2 tolerances. Fixing only the spatial start or
only the clock does not establish a continuous departure.

## Required next repair, not implemented here

Preserve the exact physical held origin/PVA as the optimizer's commanded start;
use the grid centre only as a path-search seed. Search-to-physical-start corridor
or connector handling must still pass the real geometric/stopping guard. Do not
teleport to a supposedly free cell or enlarge the continuity tolerance.

Also implement a coherent stopped-release clock contract shared by ordinary and
emergency departures: full relative-prefix validation, matching position/yaw,
CmdTraj/EXP/backup clocks and receipts, atomic generation/certificate binding,
then release from the held state. See `stopped_clock_rebase_design.md`.

Any subsequent revision needs separately bound source/binary identity and a new
prospective smoke; this running cohort must remain unchanged and be reported
honestly even if it reaches its configured timeout.

## Finalized Full addendum

The Full run subsequently completed at its 180.01-second configured timeout.
Archived evidence directory:

`results/scenario7_guard_contract_smoke_20260926_v3_g1/preflight/gapfree_d1_m01/r01_run80000/`

The entries below come from `full_summary.json`,
`artifacts/gapfree_d1_m01_run80000_full.attempt1.json`, and the matching archived
`.stack.log`. The parent status is `STOPPED_FOR_DIAGNOSIS`; no Sector/Adaptive
archived result was present at this audit. Do not extrapolate the Full outcome
into measured results for those modes.

| Final observation | Value |
|---|---:|
| Completion | Failed, timeout 180.01 s |
| Run/resource/speed validity | true / true / true |
| Waypoints / path length | 0 of 5 / 0 m |
| Safety collisions | 0, while stationary throughout |
| Observed PositionCommand messages | **0** |
| Observed odometry messages | 18,000 |
| Final position and velocity | (0,0,1.5) m; (0,0,0) m/s |
| Async results computed / accepted | 1362 / 0 |
| Handoff rejection reasons | 1362 POSITION_DISCONTINUITY |
| Position error min / median / max | 0.043510213 / 0.045453144 / 0.261345435 m |
| Velocity error min / median / max | 0.023653921 / 0.1238940295 / 2.686828751 m/s |
| Acceleration error min / median / max | 1.395315402 / 4.394225627 / 19.647409598 m/s^2 |
| Last rejected candidate generation | 1350, request 1362 |

The finalized observer supplies the previously unavailable actual command
message count. This zero-message result is distinct from the command timer's
roughly 100 Hz invocation rate.

The final available periodic profiler interval is 175.150671247 s, from the
first recorded interval to the last periodic record (`final=0`, not a claimed
shutdown footer). Both main and command callbacks have 17,515 invocations over
that interval: **99.999616760 Hz** each. Replan callbacks: 2,628 / 15.004224542 Hz.
The generated `small_pool_timing` report independently reports those same
main/command rates and `valid=true`. This passes the scoped timer test, not the
mission-completion gate.

Odometry receive rate is 100.001332677 Hz. Header p99/max intervals are
10.10796916/10.942013 ms; receipt p99/max are 10.53693816/21.124198 ms. One observed
receipt gap exceeds 20 ms; at that exact event the corresponding header delta
was 10.021996 ms. Do not conflate this observation-side gap with a proven missed
producer callback or hide it behind the mean frequency.

Final conclusion: the prospective v3 ordinary gate prevents this inconsistent
departure but exposes deterministic no-progress. The next implementation must
repair **both** physical held-origin preservation and the stopped-release clock
contract. A timestamp-only adjustment cannot cure the 43.3 mm spatial mismatch;
loosening the handoff thresholds would conceal rather than repair it.
