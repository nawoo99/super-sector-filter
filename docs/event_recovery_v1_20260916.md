# Event-only Adaptive v1 — seed1 smoke (2026-09-16)

## Scope and preservation

User requested preservation of the existing implementation/results and a separate
Adaptive variant: Sector during ordinary travel; Full after meaningful planning
failure, stalled progress, or a map-based safety stop; remain stopped if no route
exists; return to Sector only after a new Full observation is committed and a new
safe trajectory is obtained. Routine successful replanning is not an opening event.

Legacy profiles were NOT edited. All new runtime behavior is opt-in through
`fsm/event_recovery/enable` (default false) and frontend `--event-recovery`.
The original normal/stress datasets must not be merged with this smoke cohort.

Local pre-edit source/install-binary archive:
`results/event_recovery_v1_backup_20260916_kblK04/runtime_before.tar.gz`

SHA-256: `48d45a5c1860578795b5f6e7995d9eec33ec2220c8bd465030ad0da6bb20575f`.
This 80 MiB local recovery artifact is not intended for Git tracking. The prior
mirror/scripts revision is `20026ac`. Existing runtime changes in the SUPER clone
were preserved, not reset to upstream.

Frozen Normal300 CSV SHA-256:
`b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`.

## Protocol

1. Start in Sector: velocity-aligned half-angle45deg plus the existing bounded
   near-field retention. No continuous raw future-tail/body risk worker, no
   periodic pre-stale Full refresh, no timer-driven Full bursts.
2. Three consecutive initial planning failures before any successful plan, or
   speed below0.6 m/s for1.2 s after motion is armed, request an event recovery.
   After a successful plan exists, routine optimizer failures alone do NOT
   request a stop: the previously committed trajectory may still be viable.
   Existing map-based trajectory
   safety events also enter the same recovery boundary. These guard stops are
   not removed merely to reduce CPU. A stopped initial vehicle is not a stall;
   its PlanFromRest failures can still request recovery.
3. Planner activates its existing certified emergency brake and publishes the
   latched recovery-active signal. Frontend opens Full, without the old far-field
   point cap, and rejects queued/pre-event source scans for the refresh token.
4. Exact timestamp-token matching requires a committed ACK, not merely a
   processed scan, and a map version advanced after the planner's recovery edge.
   Missing ACKs retain Full; a fresh token may retry at a bounded0.30 s interval.
5. Existing brake completion, stable terminal hold, fresh-map check and bounded
   PlanFromRest retry remain active. No path means the brake/terminal hold remains
   active. Rejected/uncommitted candidates cannot release the recovery gate.
6. A new committed trajectory generation with a current map safety certificate
   permits the planner to release recovery. Frontend closes only after BOTH this
   release and its own exact committed-cloud ACK; either message order is valid.
   The planner emits `EVENT_RECOVERY_PATH_READY`; frontend emits
   `EVENT_RECOVERY_SECTOR`. A timeout alone never closes Full.

The source sensor remains the same360deg10Hz MARSIM sensor. This is not physical
sensor-FoV control and does not claim that raw-cloud generation cost was removed.
Unlike the legacy Adaptive's nominal5Hz cap, this variant follows the10Hz sensor
in Sector and Full, avoiding a lower nominal input-frequency explanation for the
new comparison. It therefore changes the deployed Adaptive policy and needs its
own results. The near-field retention and velocity direction remain unchanged.

This is still perfect-tracking simulation, not a real-vehicle stop guarantee.
If the underlying guard cannot certify a brake, its existing fail-closed behavior
remains; this patch does not invent a safe stop certificate for that case.

## Verification and experiment

- Pure C++ latch assertions: stale source sequence/stamp, absent/wrong ACK,
  processed-not-committed ACK, both delivery orders, superseded refresh,
  no-path/no-release hold and new-cycle invalidation.
- Real ROS frontend test, isolated domain194, synthetic four-direction cloud:
  seven checks passed, including remaining Full without a path release and
  closing only after the committed ACK. No vehicle or planner was launched in
  this protocol test. Artifacts: `results/event_recovery_transport_test_20260916/`.
- Legacy Python resource/diagnostic/monitor/filter-equivalence tests:24 passed.
- Build: mission_planner, super_planner and perfect_drone_sim, sequential with
  one compiler job to avoid concurrent-flight/memory pressure.

Separate smoke runner:
`scripts/native_campaign/event_recovery_seed1_smoke.py`.
It runs seed1 Full/Sector/event-Adaptive once each, retains failed outcomes,
stops on infrastructure-invalid evidence, collects native cgroup CPU plus
independent1Hz host/process/thread counters, and checks frozen hashes.
Static-PCD contact monitoring, v7, loop24 and seed1 geometry remain unchanged.
Full and Sector use their legacy configuration paths with event mode disabled.

## First prototype: preserved, not selected as final behavior

`results/event_recovery_seed1_n1_20260916/`, run9101, all three quality-valid,
first-attempt, no contact or speed violation. Build completed successfully in7min1s.

| seed1 mode | Completion | Contact | Mission s | Experiment CPU /20 CPUs | CPU core-s |
|---|---:|---:|---:|---:|---:|
| Full | 1/1 | 0 | 63.91 | 8.0613% | 105.900658 |
| Sector | 1/1 | 0 | 61.71 | 6.6513% | 84.357813 |
| Event Adaptive prototype | 1/1 | 0 | 80.84 | 6.1733% | 101.730677 |

Adaptive performed44 Full-open and44 Sector-return transitions; all44 had exact
committed Full-ACK and new-generation path certificates. Raw-risk verdicts0,
pre-stale periodic refreshes0, Full-open frame fraction55.095%.

The safety/closure protocol worked, but the initial trigger misclassified three
failed *routine optimizations* as a blocked route even while the old trajectory
was making progress. Of34 logged successful event-request brake constructions,
29 started above1.5m/s (up to7m/s). This needlessly stopped viable trajectories
and increased mission duration. This prototype is preserved in full, rather than
discarded because its performance was unfavorable.

Correction to test separately: keep the initial/no-path failure trigger, but
after a successful plan exists do not use optimization-failure streaks alone as
evidence of blockage. Require persistent observed low-speed/stall or a common
map-based safety/stop event. The handshake and stop/hold guards are unchanged.

## Corrected trigger: separate verification cohort

Prototype code and its three flights were committed together as `4cc4a0b`
before changing the trigger. The correction adds a successful-plan latch;
`event_recovery_ignored_replan_failures` records ignored optimizer-failure
notifications once that latch is set. Persistent observed stall and the common
map safety guard remain able to request recovery. Failed routine optimization
does not revoke a still-valid committed trajectory.

The ROS transport regression now additionally checks initial no-path failures
request recovery, five failed routine optimizations after a successful plan at
2m/s do not request a stop, and a subsequent persistent stall does request one.
Its artifacts use a new folder, preserving the original seven-check result.

New seed1 Full/Sector/event-Adaptive n1 run9102 uses
`results/event_recovery_seed1_corrected_n1_20260916/`. No trials from the prototype
or the frozen Normal300 dataset are pooled into this cohort.

### Completed run9102 results (2026-09-16 01:53 KST)

All three first-attempt runs were quality-valid, resource-valid and speed-valid;
retry0. The controller exited normally with `COMPLETE`, completed3. No flight
is left running. Corrected frontend build passed in1min50s. The isolated ROS
transport test passed all10 checks, alongside the pure C++ latch checks and24
existing Python tests. Transport artifacts:
`results/event_recovery_transport_corrected_20260916/`.

| Seed1 mode | Completion | Static-PCD contacts | Mission s | Experiment CPU /20 CPUs | CPU core-s | Map Total mean ms | Map updates/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 1/1 | 0 | 61.39 | 8.2757% | 105.369389 | 38.8303 | 10.2948 |
| Sector | 1/1 | 0 | 61.18 | 6.6935% | 84.771644 | 10.7641 | 10.3792 |
| Event Adaptive, corrected | 1/1 | 0 | 59.73 | 7.0292% | 86.123989 | 11.8827 | 10.2628 |

CPU core-s is the integrated native experimental cgroup user+system time,
including simulator, frontend when present, mapping/planner, mission and launch
processes. It excludes unrelated background and the external contact/profiling
observers consistently. Divide core-s by the measured cgroup duration to obtain
mean occupied logical CPUs, then divide by20 and multiply by100 for the CPU
share column. Map Total is stage wall time, NOT CPU execution time.

Whole-PC CPU including background was22.9651/18.8229/20.2147% (F/S/A), recorded
separately; it is not interchangeable with the experimental cgroup share. GPU
sampling remains device-wide and cannot be attributed solely to the flight.

For this single matched seed1 observation, corrected Adaptive vs Full reduced
integrated CPU core-s by18.2647%, mean occupied CPUs by15.0615%, and Map Total
wall time by69.3983%. Mission time was2.7040% shorter. These are descriptive n1
differences, not significant estimates or guarantees. No mapping-frequency cap
explains the difference in this new cohort: all three map rates were about10Hz.
Static-PCD minimum body clearance was0.217/0.306/0.305m (body radius0.20m).

### Actual Adaptive handshake evidence

Two Full openings and two Sector returns, both initiated by the common planner
safety guard. Frontend event-request count is0, not a missing transition:
the authoritative guard signal also opens recovery directly. The prototype's
optimization-failure stops disappeared.118 above-threshold routine failure
notifications were ignored after a successful plan;220 total replan failures
remain honestly counted, rather than being reclassified as successful plans.

| Cycle | Full observation stamp ns | Committed ACK map | New-path certified map | Trajectory generation | Full-to-Sector duration s |
|---|---:|---:|---:|---|---:|
| 1 | 1789491102225008052 | 16 | 24 | 1 -> 2 | 0.9926 |
| 2 | 1789491143327817510 | 427 | 431 | 94 -> 95 | 0.4836 |

The first event was `main_pre_uncertified`; the second was
`candidate_rejected_without_safe_follow`. Existing brake-certification retries
were observed before a certified zero-speed hold was obtained. No unsafe brake
candidate was newly accepted by this change. This perfect-tracking simulator
can freeze on withheld commands, so these logs must NOT be promoted into a
physical stopping/dynamics guarantee.

All7 flight audit checks passed: event mode active, raw-risk worker/verdicts
absent, no pre-stale periodic refresh, no timed replan opening, new trajectory
generation on release, certificate on a committed-or-later map, and a path
certificate for each closure.15 of634 frontend frames were Full (2.366% of
frames, not a duration metric). Input/output cadences were10.0003Hz. Raw-risk
messages0 and topic empty; filter cloud work mean0.7135ms, risk work0.

The simulated LiDAR still generates the original360deg10Hz scan before the
frontend crop. This implementation removes continuous raw-risk evaluation and
changes forwarding/recovery policy, not GPU ray generation or a physical LiDAR
driver. It is not a claim of sensor-side FoV/bandwidth savings.

Missing-path/no-release hold was covered in the pure latch and synthetic ROS
protocol tests. Seed1 recovered a path in both episodes; a deliberately
impossible-path closed-loop flight was NOT part of this requested n1 smoke.
Sector also completed without contact here, so this seed1 result does not show
an Adaptive safety advantage over Sector. The new policy requires its own
multi-map/repeat validation; old Normal300 conclusions cannot be transferred.

### Reproduce this separate three-mode smoke

```bash
cd /root/super-sector-filter
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 -u scripts/native_campaign/event_recovery_seed1_smoke.py \
  --output results/event_recovery_seed1_manual_9103 --run 9103
```

Use a new output directory and unused run number, with no other flight running.
The runner refuses an existing output directory and concurrent native flight.
Legacy Full and Sector profiles remain unchanged, and the new Adaptive profile
is `static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml`.
