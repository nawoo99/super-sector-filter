# Static blind-fork burst-dropout confirmation preregistration

Date frozen: 2026-09-10 (Asia/Seoul), before asset generation, replay, or flight

Status: **frozen before observation; completed without post-outcome changes**

## Purpose and claim boundary

The developed `shm1_h1`--`shm1_h9` family is exploratory.  This experiment is
a held-out finite stress suite testing whether its observed ordering transfers
to three geometry variants under a nominal 10 Hz LiDAR stream containing
bounded 0.5 s burst losses.  It does not establish a population-level 100%
guarantee and it does not replace the normal Map1--10 efficiency campaign.

SUPER planning, Full/Sector/Adaptive policy parameters, v7 dynamics, the fixed
45-degree half-angle, the 1.5 m omnidirectional near-field bubble, risk
thresholds, and guard timing are frozen.  Only simulator-side static assets and
a mode-independent sensor-output fault injector may be added.  The injector
must be disabled by default and must act before raw DDS, direct Full handoff,
and direct filtered-frontend handoff, so every mode loses the same rendered
frames for the same map/run index.

## Frozen sensor fault

- renderer cadence: 10 Hz
- warm-up: 1.0 s of delivered frames
- loss pattern: recurrent 0.5 s output suppression every 2.0 s
- paired phase grid by run index 1--10: `0.0, 0.2, 0.4, ..., 1.8 s`
- phase definition: the first loss interval begins at
  `warmup + phase`; later intervals repeat every 2.0 s
- a frame exactly on the start boundary is dropped; a frame exactly on the end
  boundary is delivered
- rendering and vehicle dynamics continue during loss; only the completed
  PointCloud2 output/handoff is suppressed

The phase grid is deterministic and balanced, not selected after observing a
contact.  Full, Sector and Adaptive rows sharing `(map, run)` must use the same
phase.  Required integrity fields are configured phase, rendered/delivered/
dropped frame counts, burst count, maximum consecutive dropped frames, and
maximum delivered-frame gap.  No normal operational YAML enables this fault.

## Frozen held-out geometries

All scenes retain an always-present static background, one direct branch that
body-intersects a transverse closure, and an inflation-feasible alternative
branch.  Start is `(24.5, 0.0, 1.5)`, target is the existing northbound
`blind_heading_mismatch.txt` mission, obstacle height is 3.2 m, wall thickness
is 0.3 m, and the direct route is x=24.5.

### Map C1: `shc1_mirror`

Horizontal reflection of the developed topology about x=24.5, without using
new outcomes:

- outer walls x=21.0 and x=29.0, y=-3..23
- divider x=25.5, y=2..15
- west-branch closure `(20.65,4.0)` to `(25.5,4.0)`
- initial body yaw 0 degrees (east), velocity direction north
- east bypass anchors `(24.5,0) -> (26.5,1) -> (26.5,16) -> (24.5,20)`
- audit witness centre `(24.0,4.0)`, radius 1.0 m

### Map C2: `shc2_wide_offset`

Unmirrored variant with a wider corridor and shifted divider:

- outer walls x=19.5 and x=28.5, y=-3..23
- divider x=23.25, y=2.25..15.5
- east-branch closure `(23.25,4.4)` to `(28.35,4.4)`
- initial body yaw 180 degrees (west), velocity direction north
- west bypass anchors `(24.5,0) -> (21.75,1) -> (21.75,16.5) -> (24.5,20)`
- audit witness centre `(25.0,4.4)`, radius 1.0 m

### Map C3: `shc3_near_short`

Unmirrored variant with a nearer closure and shorter, offset divider:

- outer walls x=20.25 and x=28.25, y=-3..23
- divider x=23.8, y=2.5..14.5
- east-branch closure `(23.8,3.6)` to `(28.1,3.6)`
- initial body yaw 180 degrees (west), velocity direction north
- west bypass anchors `(24.5,0) -> (22.1,1) -> (22.1,15.5) -> (24.5,20)`
- audit witness centre `(25.0,3.6)`, radius 1.0 m

Each geometry has a clear control and hazard member differing only by the
closure wall.  Map names and dimensions cannot be replaced after a failed
gate.  A failed map remains a failed held-out map.

## Staged gates and stop rules

For each map in C1, C2, C3, in that order:

1. **Structure gate:** exact clear/hazard background equality, positive hazard
   delta, actual-PCD 0.1 m grid with three-cell inflation has the registered
   bypass, direct-route body clearance is negative, body-fixed initial Sector
   contains zero hazard samples, and the north-velocity Sector contains at
   least 20.
2. **Production C++ replay gate:** Sector and Adaptive consume the same actual
   MARSIM frames.  Raw hazard and trajectory-conflict counts are positive,
   Sector retains zero conflict points, Adaptive retains positive conflict
   points and produces at least one fresh `OCCUPIED` verdict.
3. **Fault-integrity smoke:** a short launch demonstrates default-off behavior
   in an ordinary config and the exact 10 Hz/0.5 s configured schedule in the
   held-out config.  Configured and observed phase must agree.
4. **Full feasibility gate:** exactly one new Full hazard flight.  It must
   complete on the first attempt, have zero static-PCD contacts, valid speed
   and resource gates, and exercise at least one dropout burst.  Failure stops
   that map; Sector/Adaptive and repetition are forbidden for it.
5. **Paired smoke:** for maps passing Full, one Sector and one Adaptive flight
   at run-1 phase.  This is a mechanism sanity check, not an outcome-selection
   gate: both rows are retained and the map proceeds to the frozen matrix even
   if Sector is safe.
6. **Frozen matrix:** all eligible maps receive ten new runs per mode in
   rotating mode order.  Gate/smoke rows are not pooled.  No outcome retry is
   allowed.  A demonstrable launch/infrastructure failure may be rerun once
   under a new attempt label but both records remain; it is not silently
   replaced.

No geometry, dropout timing, planner parameter, filter parameter, acceptance
criterion, or eligible-map subset may be changed after any flight outcome.

## Primary endpoints and decision

Safe completion means mission completion with zero static-PCD contact.  Report
every map separately before any aggregate.

The finite held-out suite is `CONFIRMATORY_TRANSFER_OBSERVED` only if:

- all three maps pass structure, replay, fault-integrity, and Full gates;
- Full and Adaptive each achieve 10/10 safe completion on every map;
- Fixed Sector has at least one unsafe paired row on every map;
- across the 30 paired Sector/Adaptive rows, the discordance direction is
  Adaptive-favouring and the exact two-sided paired McNemar p-value is below
  0.05; and
- every retained row passes the sensor-fault, speed, resource, static-PCD and
  first-attempt integrity checks.

If only some maps pass or separation is heterogeneous, the decision is
`PARTIAL_TRANSFER`; if Full/Adaptive safety or integrity fails, or no map-level
Sector degradation appears, it is `CONFIRMATION_FAILED`.  These decisions do
not authorize tuning this held-out suite.

Secondary endpoints are mission time, physical clearance, planner ingress,
algorithm cgroup CPU, point retention, Adaptive effective Full-open count and
duty, exact-risk verdicts, and dropout gap diagnostics.  Efficiency claims
continue to come from the normal-rate Map1--10 campaign; this suite is a
bounded safety-robustness test.

## Outcome record (appended after the frozen experiment)

The preregistered decision was `CONFIRMATORY_TRANSFER_OBSERVED`. All structure,
paired production replay, fault-integrity and Full-feasibility gates passed.
In the frozen 90-row matrix, Full and Adaptive each had 30/30 safe
completions; Fixed Sector had 13/30 safe completions and 17/30 contact runs.
The paired discordance was 17 Adaptive-favouring versus zero
Sector-favouring, with exact two-sided McNemar p=`1.52587890625e-05`.

All rows were unique first attempts with valid fault, speed, resource and
static-PCD integrity. No map, phase, policy, criterion or eligible subset was
changed after outcomes. Full analysis and the explicit claim boundary are in
`docs/static_burst_dropout_confirmation_result_20260910.md`.
