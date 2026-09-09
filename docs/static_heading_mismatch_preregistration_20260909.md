# Static initial-heading mismatch preregistration

Date: 2026-09-09 (Asia/Seoul)

Status: **frozen before map generation or flight**

## Purpose

Test a static, physically plausible blind-zone mechanism for a holonomic UAV:
the airframe initially faces west while its commanded translation is north.
A full-height static obstacle lies on the northbound clear-control trajectory.
The raw 360-degree LiDAR sees it from startup, the 45-degree body-fixed Sector
does not, and Adaptive's deployed velocity-aligned crop can retain it as soon
as translation begins.  No obstacle moves and no planner/filter policy changes.

Candidate `shm1_h1` uses start `(24,0,1.5)`, initial yaw 180 degrees, goal
`(24,20,1.5)`, a cylinder at `(24,5)` with radius 1.2 m, and two static corridor
walls at x=20 and x=28.  The corridor leaves inflation-feasible bypasses on
both sides of the cylinder.

## Ordered gate

1. Clear/hazard maps differ only by the cylinder; an inflated bypass exists;
   the direct route body-intersects it; at the initial pose raw/velocity-sector
   visibility is positive and body-fixed-sector visibility is zero.
2. Actual C++ replay at yaw 180 degrees and north velocity must show raw hazard
   and conflict, zero Fixed-Sector hazard/conflict, positive Adaptive filtered
   hazard, and at least two fresh exact `OCCUPIED` verdicts.
3. Clear Fixed Sector must safely complete and commit a hypothetical
   hazard-intersecting trajectory.
4. Hazard Full must complete contact-free before filtered hazard modes run.
5. The single first attempts for Fixed Sector and Adaptive are then compared.
   The mechanism gate requires Sector contact or non-completion, Adaptive safe
   completion, and actual evidence that the first hazard observation was
   outside body Sector but inside the velocity Sector.  Adaptive may succeed
   by its deployed velocity-aligned crop or by a causally matched Full opening;
   this distinction is reported rather than conflated.

Only a complete mechanism pass permits repeated trials.  No failed row is
replaced, no generic wall verdict counts as hazard evidence, and this
exploratory topology is not pooled with `sbd1`, `sbd2`, or Map1--10.

## Frozen iteration log

### `shm1_h1`

All non-flight gates, clear control and Full feasibility passed.  The first
hazard Sector and Adaptive rows both completed contact-free.  The 1.2 m
cylinder centre began outside body Sector, but its large angular silhouette
entered the 45-degree boundary while yaw rotated; Sector therefore selected
the same right bypass as Full/Adaptive.  The result is retained as a failed
separation, not replaced.

### `shm1_h2` — frozen before generation

Change one causal factor: replace the broad centred cylinder with a narrow
static pole at `(24.75,3.4)`, radius 0.12 m.  The h1 clear trace passes at about
x=24.52, so the body-inflated pole intersects the unobserved path while the
pole's angular silhouette remains outside body Sector and inside the velocity
Sector during approach.  All walls, start, yaw, goal, speed and policies stay
fixed.  Because the smaller surface may be under-sampled, actual replay is a
mandatory fail-closed prerequisite before any h2 flight.

`shm1_h2` passed the structure and actual replay gates.  Full, Sector and
Adaptive nevertheless all completed contact-free on their first hazard run.
The Fixed-Sector committed trajectory initially intersected the pole, but the
executed trajectory wandered laterally by substantially more than the pole
diameter before reaching it.  This is a failed separation caused by a
single-point hazard being smaller than the clear-run trajectory dispersion;
the row is retained.

### `shm1_h3` — frozen before generation

This is a new exploratory topology, not a one-factor causal ablation of h2.
It makes the intended holonomic sensing condition persistent and removes the
single-pole luck mechanism:

- start and goal remain `(24,0)` and `(24,20)`, but the mission yaw is held at
  180 degrees throughout the northbound translation;
- a full-height transverse wall runs from `(23.0,2.5)` to `(27.85,2.5)` with
  0.30 m thickness and joins the east corridor wall;
- the west side retains an inflation-feasible opening between x=20 and x=23;
- Full sees the wall at startup and must use the west opening; Fixed Sector
  faces west and must not receive the wall before committing the intersecting
  route; Adaptive's velocity-aligned crop sees the central wall surface;
- the unchanged v7 planner/filter policies are used.  Only the map, mission
  yaw command and measurement registration change.

The authoritative contact oracle is the common static PCD, not an analytic
bounding circle.  A bounded central wall patch centred at `(24.2,2.5)` is used
only to attribute replay and trajectory-risk witnesses; it is not used to
classify contact.  Gate order remains structure, actual C++ replay, clear
Sector, hazard Full, then one Sector/Adaptive attempt.  Repetition is allowed
only if Full is contact-free, Sector degrades, Adaptive completes contact-free,
and the exact Adaptive witness precedes any Sector contact in the independent
runs.

`shm1_h3` passed structure, actual replay, clear control and Full feasibility.
The requested waypoint yaw did not remain locked: the existing mission stack
continued to rotate the body toward the flight direction.  Sector first
committed a wall-intersecting trajectory, but the wall's x=23 left endpoint
entered the rotating 45-degree Sector near y=1.19 m.  It stopped, searched
both sides and eventually used the west opening without contact.  Sector took
10.00 s versus Adaptive's 5.81 s, but the safety-separation gate failed, so no
repetition is allowed.

### `shm1_h4` — frozen before generation

Change one geometry factor from h3: move only the transverse wall's left
endpoint from x=23.0 to x=24.0; keep y=2.5, its x=27.85 east endpoint,
thickness, corridor, start, mission file, speed and all policies unchanged.
The wider west opening improves Full/Adaptive route feasibility.  At the same
time the only approaching wall endpoint is closer to the clear trajectory,
so it crosses the rotating body-sector boundary much later.  The direct clear
trajectory must still intersect the wall, actual Fixed-Sector replay must
still remove its central surface, and all prior h3 rows remain part of the
exploration record.

`shm1_h4` passed all pre-flight gates and Full again completed contact-free.
Sector also completed contact-free: despite the later angular edge reveal,
the unchanged 1.5 m omnidirectional near-field bubble retained the wall soon
enough to stop and move west.  Its minimum PCD clearance was 0.432 m versus
Adaptive's 0.536 m, but this is not the preregistered safety separation.

### `shm1_h5` — frozen topology redesign before generation

Stop translating the same transverse wall.  Preserve the deployed 1.5 m
near-field safety bubble and test topology selection instead.  Start at
`(24.5,0,1.5)`, initially facing west, with outer walls x=20 and x=28.  A
central divider at x=23.5 from y=2 to y=15 creates west/east branches.  A
full-height wall across the east branch at y=8, x=23.5..27.85, closes only the
natural east branch.  The goal is `(24.5,20)` above the divider.

Full and velocity-aligned Adaptive can observe the closure before the y=2
fork and choose west.  Fixed Sector initially sees neither the northbound
closure nor its central witness region; its near-field bubble may prevent
contact later, but by then the divider requires backtracking below y=2 before
changing topology.  The separation gate is therefore Sector contact **or
non-completion**, with Adaptive/Full contact-free completion.  No timeout is
shortened and no near-field, planner, guard or speed parameter is changed.

`shm1_h5` failed the mandatory Full gate.  Full entered the east branch,
stopped near y=7.15 and timed out at 60 s without contact despite the analytic
bypass.  This shows that a wall at y=8 was not incorporated early enough to
change the first local topology; no filtered hazard flight is admissible.

### `shm1_h6` — frozen before generation

Change only the east-branch closure y coordinate from 8.0 to 4.0 m.  Keep the
divider start at y=2, every x coordinate, corridor, start, goal, speed,
timeout and policy unchanged.  The close wall must make Full choose west
before the fork.  Fixed Sector's unchanged 1.5 m near-field bubble first
retains the closure only after it has passed the divider endpoint, preserving
the late-topology mechanism.  Full is tested first after structure/replay;
failure again stops the flight gate.

`shm1_h6` made Full select the west route and complete contact-free in 4.44 s.
Sector committed the central conflict, stopped after its 1.5 m near-field
bubble retained the wall, backtracked below the fork, and still completed in
12.38 s.  Adaptive detected an exact hazard-matched conflict at 0.227 s and
completed in 5.46 s.  This is strong route/time evidence but not the required
contact/non-completion separation.

### `shm1_h7` — frozen common sensor-cadence stress

Keep the complete h6 PCD topology and every planner/filter parameter.  Change
only the common simulated LiDAR rate from 10 Hz to 5 Hz for clear, Full,
Sector and Adaptive.  This is a separately labelled static sensor-cadence
stress, not pooled with the 10 Hz operational campaign.  Full/Adaptive retain
the closure at long range, whereas Fixed Sector first receives it through the
1.5 m omnidirectional bubble and may travel up to 1.4 m between scans at v7.
The same structure, actual-renderer replay, clear-control, Full-first and
Sector-degradation/Adaptive-recovery gates apply.

`shm1_h7` kept Full and Adaptive contact-free.  Sector again recovered, but
its minimum PCD clearance fell from 0.280 m at 10 Hz to 0.177 m at 5 Hz while
Adaptive retained 0.632 m.  The directional cadence response is present but
the contact/non-completion gate still fails.

### `shm1_h8` — frozen 4 Hz threshold stress

Keep h7 geometry and policies and change only the common LiDAR rate from 5 Hz
to 4 Hz.  At v7, one 4 Hz inter-frame displacement can reach 1.75 m, exceeding
the 1.5 m omnidirectional bubble.  This is the first physically motivated
cadence threshold at which late Fixed-Sector retention may occur after body
contact.  It remains a separately labelled degraded-sensor stress and is not
presented as the nominal 10 Hz result.

`shm1_h8` also completed in all three modes without contact.  The Sector
clearance was non-monotonic (0.477 m), showing that scan phase and trajectory
variation dominate a single 4 Hz row.  Adaptive changed its route before an
exact verdict was needed.  This does not pass the separation gate.

### `shm1_h9` — frozen severe dropout-equivalent stress

Keep h8 geometry and policies and change only the common LiDAR rate from 4 Hz
to 2 Hz.  Treat this strictly as a severe dropout-equivalent robustness test,
not nominal operation.  If it separates, the claim is limited to degraded
sensor cadence.  If it does not, map-only tuning stops: the next admissible
study must explicitly preregister a common delay/dropout injector or a pure
angular-Sector ablation instead of silently weakening the deployed baseline.

`shm1_h9` passed the structure and actual-MARSIM/C++ replay gates. The staged
first attempts produced Full contact-free completion, Fixed-Sector contact and
Adaptive contact-free completion, so the frozen repetition permission was
met. Ten new rotating-order rows per mode then gave Full 10/10 safe completion,
Sector 1/10 safe completion (9 contact runs), and Adaptive 10/10 safe
completion. Paired exact McNemar p=0.00390625. Adaptive used one effective
Full-open transition per row and 15.9 pre-stale Full refresh frames on average;
the natural closed-loop avoidance is therefore attributed to the deployed
bounded refresh/recovery policy, not solely to exact-risk braking. This is an
exploratory severe-cadence result and is not promoted to a nominal or
population guarantee.
