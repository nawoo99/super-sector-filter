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
2. Three consecutive planning failures or speed below0.6 m/s for1.2 s after
   motion is armed request an event recovery. Existing map-based trajectory
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
