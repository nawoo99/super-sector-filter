# Adaptive source-acquisition CPU optimization, seed1 (2026-09-16)

## Authorization and experiment contract

The user authorizes algorithm/planner changes and one seed1 flight per candidate
mode, followed by diagnosis/redesign. The clarified target is **>=40% reduction
in mean experimental CPU use relative to matched Full**; cumulative CPU time is
also reported, but need not independently reach40%. This is exploratory tuning
on seed1, not independent confirmation or population-level safety evidence.

Frozen preceding source-acquisition v2: mirror commit `de3562d`. Runtime source
and installed files were backed up before changes to
`results/adaptive_cpu40_backup_20260916_aloDDu/runtime_before.tar.gz`, SHA256
`a257ef96fa30c734c39d24e39019b21afd0856e5a5e9e4197a4dd6750b8761a8`.
PCD assets are excluded from this archive and remain unchanged. Old Normal300
SHA256 remains `b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`.

- Keep seed1 map, loop24 waypoints, v7 speed limit, 45deg half-angle and source
  0.4deg/10Hz settings unchanged for initial optimization candidates.
- Retain each unsuccessful candidate, infrastructure-invalid attempt and raw
  log. No automatic infrastructure retry or favorable-result overwrite.
- Full and Adaptive must both complete with zero static-PCD contacts, valid
  speed/resource/measurement and source/recovery contract audits.
- Guard against artificially reduced mean CPU due to stationary waiting:
  declare an additional maximum A/F mission time ratio1.10 for target acceptance.
- Fresh Full observation -> exact committed-map ACK -> newly certified path
  remains the release condition. No path means hold. No outside-Sector data.
- A common optimization must also be applied to Full. Do not preserve
  deliberately inefficient Full behavior to enlarge relative savings.
- Compare experiment cgroup totals, not whole-PC background or falsely
  planner-only CPU from a process containing the simulator.
- No changes are pushed to upstream SUPER. No GitHub push requested this turn.

## Candidate1: same-process acquired cloud delivery + CPU instrumentation

Opt-in new `perfect_drone_adaptive_node` composes source renderer, frontend and
FSM/map. Source mode/cycle metadata and exact Full request handling remain;
frontend submits the same acquired PointCloud2 SharedPtr to existing latest-only
map admission. Heavy map work stays on its dedicated worker, GLFW on main
thread, side executor10threads matching Full. No cloud DDS publisher in the
new direct-output path. Old two-argument component API/default profiles remain.
New launch option `use_sensor_planner:=true`, campaign option
`sensor_planner_intra_process=True`. Logical payload is still measured; actual
cloud DDS payload is zero in both composed Full and composed Adaptive.

`SUPER_CPU_PROFILE=1` opt-in CLOCK_THREAD_CPUTIME_ID scopes measure CPU in map
conversion/update/snapshot/ACK, FSM/replan/command and guard stages. Reports every
5s are cumulative; inclusive fields overlap, exclusive fields do not within an
instrumented thread. Other worker/simulator/middleware CPU is not attributed by
these scopes. Both compared modes use identical instrumentation. Disabled mode
does not read clocks/log/update counters. Final no-instrumentation confirmation
is required if an exploratory candidate meets the target.

Runner: `scripts/native_campaign/adaptive_cpu40_seed1.py`. Each output directory
is new and records configurations/source/binary hashes and clarified objective.
Stage analysis: `scripts/native_campaign/analyze_thread_cpu_profile.py`.

Initial checks:22Python tests pass (runner acceptance/accounting/resource guard);
standalone profiler tests pass disabled/enabled, nested exclusive accounting,
sleep exclusion and concurrent aggregation. The direct-sink ROS test passes
pointer/payload/stamp identity, no second crop, explicit stale mode/cycle/missing
metadata rejection, no cloud ROS publisher, and legacy two-argument delivery.
Its first two manual link commands lacked ROS statistics libraries; those were
test-build failures (not flight failures). Corrected third build/run passes,
evidence `/tmp/native_direct_sink_test_qrBShi` and `native_direct_sink_test_run3.log`.
Existing synthetic ROS Full recovery handshake passes all10checks. Sequential
4-package build finished in12min29s (existing compiler/CMake warnings, no errors):
`results/adaptive_cpu40_20260916/build_candidate1.log`. Source Normal300 hash
matches; MemAvailable9360MiB after compiler exit. Launch argument check passes.

### Candidate1 measured result (run9301, one flight per mode)

| Mode | Complete/contact | Mission s | Mean used cores | Whole20CPU equivalent % | CPU core-s |
|---|---|---:|---:|---:|---:|
| Full | 1/1,0 | 63.22 | 1.620519 | 8.1026 | 106.159269 |
| Adaptive | 1/1,0 | 60.87 | 1.353746 | 6.7687 | 84.659005 |

Mean CPU reduction16.4622%; cumulative reduction20.2528%; time ratio0.96283.
Both quality/resource/speed/source-recovery audits pass, no infrastructure
retry. **40% target not met.** Results: `c01_composed_profile/` under the dated
result directory. This instrumentation-enabled candidate is not a repeat of
the earlier v2 and is not proof that composition alone improves CPU.

Thread CPU within common periodic report windows (not exact whole-flight
cgroup windows): Full/Adaptive replanning0.73940/0.70965used cores;
FSM main0.15012/0.14781; map update0.37194/0.11162; snapshot0.05480/0.02557.
The map-stage savings are real, but the almost unchanged replanning cost
dominates. Inclusive and exclusive counters must not be added together.

## Candidate2: shared discarded replay / unsubscribed path publication removal

Code audit found the operational backup solve is followed by an unconditional
second solve whose bool/trajectory/start-time outputs are discarded. The old
BACK_TRAJ_OPT timer stops before this second solve. Following decisions use
only the first outputs; optimizer setup resets state before the next
operational solve. Next step: optional removal applied equally to Full and
Adaptive, state-reset regression, deeper nested CPU scopes,
then another matched seed1 pair. This does not disable operational backup or
safety checks. Default behavior remains unchanged during exploration.

Also opt-in: retain every100Hz `fsm/path` pose, but skip publishing the entire
growing path when both inter/intra-process subscriber counts are zero. With a
subscriber present the existing cadence/content remains unchanged. Native
campaign monitors consume odometry/commands and other risk topics, not this
RViz visualization path. Apply the same option to both modes; this optimizes
headless runs, not a claimed sensor-filter advantage. Deeper profile scopes
include path visualization and polynomial velocity extrema checks.

Regression caveat discovered before flight: strict coefficient equality in
two optimizer instances failed after a failure/recovery sequence. The initial
member-state audit missed a global RNG in `src/utils/sdlp.cpp::rand_permutation`:
the discarded replay advances it through corridor vertex enumeration. Therefore
removing replay can alter subsequent LP plane order, interior solution and
optimizer numerics. **Production bitwise trajectory equivalence is not claimed.**
State-reset testing needs controlled geometry randomness plus native-variation
controls; operational acceptance and downstream safety checks remain required.

Controlled test result: test-only linker wrapper supplies an analytic interior
point for axis-aligned box fixtures and calls the real explicit-interior vertex
enumeration. This shim is **not linked into production**. At configured2048
iterations, uniform/nonuniform x2/3pieces each exercised5successes,2failures and
2failure-to-success transitions. Replay/no-replay and no-replay/no-replay controls
each passed1614scalar comparisons (max absolute difference0). Native rectangular
and insufficient512-iteration variants remain as failed diagnostic artifacts;
the production global-RNG numerical difference is not hidden or reclassified.
Path/ordinary-command/brake-motion policy gtests pass3executables, and the
extended thread CPU profiler passes disabled/nested/concurrent cases.
Candidate2 sequential build completed3packages in9min32s; no errors, existing
warning streams retained in `build_candidate2.log`. Ccache enabled only as a
compiler cache (not a runtime change); after build MemAvailable9100MiB.

### Candidate2 measured result (run9302, one flight per mode)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 62.26 | 1.630290 | 103.872415 |
| Adaptive | 1/1,0 | 61.15 | 1.357637 | 85.023065 |

Mean reduction16.7242%, cumulative18.1466%, time ratio0.98217; all quality,
resource, speed and source/recovery audits pass; no retry. **40% still unmet.**
Mean CPU is essentially unchanged from candidate1 despite reduced diagnostic
work; these are separate stochastic closed-loop flights, not isolated overhead
ablations. Source: `c02_common_overhead_profile/`.

Exclusive profile Full/Adaptive (common periodic window, used cores): backup
frontend0.5655/0.5673; EXP corridor0.1232/0.1327; EXP optimizer0.0715/0.0916;
path search0.0500/0.0516; operational backup optimizer0.0463/0.0507;
map update0.3845/0.1059. Exact polynomial extrema is negligible, so caching it
is not prioritized. Unsubscribed path publication work is now negligible.

Main lead: backup visibility casts many rays, each voxel checks257 body-sphere
neighbors, and each neighbor atomically reloads the same shared snapshot.
Next candidates optimize raw occupied-box scans and per-ray snapshot queries,
without removing body-neighbor, virtual boundary or distance checks. A query
using one snapshot must reject on a commit-version change before returning
clear; it is not a long-lived stale map cache.

## Candidate3: exact occupied-box bitmap scan

Opt-in `SUPER_FAST_OCCUPIED_BOX_SCAN=1` traverses occupied bitmap words instead
of testing every raw voxel. Only OCCUPIED queries use it; original bounds,
exclusive index endpoints, signed ring mapping, point conversion and output
order remain. Mutable maps/UNKNOWN/FRONTIER follow the old implementation.
Standalone ordered-output differential corpus passed19191queries, also under
ASan+UBSan. Synthetic whole-query speedups are2.3–44.7x depending on occupancy;
these are **not measured planner/end-to-end savings**.

`SUPER_COMPARE_OCCUPIED_BOX_SCAN=1` runs both implementations against the same
captured snapshot and already-computed bounds, compares ordered XYZ bitwise,
and falls back to baseline on any mismatch. Such dual-query flight probes are
marked ineligible for CPU-target acceptance, even if their numerical reduction
exceeds40%. Run a Full correctness probe before the next ordinary matched pair.
Command/evidence bundle: `c03_preflight/`.

Build completed3packages in30.6s. Full same-snapshot flight probe run9303
completed58.83s/contact0, all source/speed/resource checks pass. Last periodic
comparison counter6144/mismatches0; all mismatches would have been logged, none
were. This is a lower bound on compared queries, not an exact final count.
Probe mean1.634731cores/99.172245core-s is **diagnostic only**, excluded from
target acceptance. Source: `c03_box_correctness_probe/`. Proceed to ordinary
Full/Adaptive candidate3 with comparison disabled.

### Candidate3 measured result (run9304, one flight per mode)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 59.50 | 1.622260 | 100.007307 |
| Adaptive | 1/1,0 | 63.28 | 1.345714 | 87.158267 |

Mean reduction17.0470%, cumulative12.8481%, time ratio1.06353; all declared
quality checks pass; no retry. Target not met. The synthetic box-query speedup
did not translate into a large end-to-end reduction. Backup frontend remains
0.5633/0.5558cores; EXP corridor0.1098/0.1058cores. Prioritize repeated line
occupancy queries, not further claims based on a microbenchmark.

## Candidate4: one immutable snapshot per line-of-sight query

Opt-in `SUPER_SNAPSHOT_LINE_QUERY=1` changes only the bool max-distance +
neighbor-list overload. Preserve 257 body-sphere neighbors, RayCaster, distance
limits, outside-map behavior, distinct float/integer virtual bounds, and
division versus reciprocal-multiply index semantics. Load one immutable
snapshot per line instead of once per neighbor; before returning free, require
unchanged publication owner/pointer and version. A changed publication rejects
conservatively; this is not equivalence under concurrent commits or a guarantee
against a commit after return. No persistent cache in this candidate.

Corpus:16832line cases/43197133ordered predicates,198index-conversion boundary
distinctions,10publication-change rejections; optimized and final ASan/UBSan
pass. Synthetic query CPU speedup4.24–4.94x is not a flight result. Sequential
build3packages completed25.8s. Evidence: `c04_line_preflight/`.

Measurement audit confirmed cgroup mean=CPU-seconds/duration and no composed
double counting; independent process sums agree within about0.4% in C1/C2.
The runner now explicitly prevents a **profiled** threshold pass from being
reported as final `target_met`: unprofiled confirmation is mandatory. Also
records effective per-mode launch options separately from inherited base-policy
defaults. Earlier plan files retain their original nested defaults; top-level
overrides and actual acquisition logs, not those base defaults, establish the
source10Hz/event-only/45deg experiment configuration. Bandwidth remains logical
payload, not NIC or memory bandwidth.

### Candidate4 measured result (run9305, one flight per mode)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 41.29 | 1.077889 | 45.764834 |
| Adaptive | 1/1,0 | 42.27 | 1.016868 | 44.415111 |

Mean reduction5.6612%, cumulative2.9493%, time ratio1.02373. Strict source and
recovery audit passes (Adaptive completed1Full recovery cycle), speed/resource
checks pass, no retry. Both modes use less CPU and finish sooner than C3, but
**relative40% target remains unmet**; separate n1 flights do not isolate causality.
Exclusive Full/Adaptive profile: backup frontend0.1988/0.2391cores,
EXP optimizer0.1265/0.1846, map update0.2468/0.1026, operational BACK optimizer
0.0736/0.0816, corridor0.0687/0.0765. Adaptive's larger planning cost offsets
much of its map savings. Source: `c04_snapshot_line_profile/`.

## Candidate5 preparation: exact snapshot-scoped neighborhood reuse

The next opt-in candidate caches the boolean OR over the complete body-neighbor
list for a voxel, only within the same immutable snapshot, predicate settings
and ordered neighbor contents. Cache collisions recompute; changes invalidate;
empty-neighbor float queries bypass; C4 final publication validation remains.
No sensor/planner frequency, body radius, map resolution or guard is reduced.
Bounded thread-local storage and weak snapshot ownership avoid retaining old
maps. Tests/build and flight results will be recorded before effectiveness claims.

Preflight passed7,456real-RayCaster comparisons, context mutation, true/false
hits, collisions, weak lifetime, alias/control-block ABA, bypass/reentry and
epoch wrap; optimized and ASan+UBSan passes. Cache88,136bytes/thread,4096entries,
maximum512neighbors. Synthetic repeated-ray CPU11.64x faster is not a flight
claim. Sequential3-package build26.1s;39Python audit/accounting tests pass.
Evidence: `c05_preflight/`, `build_candidate5.log`.

### Candidate5 measured result (run9306, one flight per mode)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 41.59 | 0.920618 | 40.108006 |
| Adaptive | 1/1,0 | 43.96 | 0.776242 | 35.464695 |

Mean reduction15.6825%, cumulative11.5770%, time ratio1.05698. All declared
source/recovery/resource/speed/quality checks pass; Adaptive completed3recovery
cycles; no retry. **Target not met.** Exclusive backup frontend falls to
0.0453/0.0532cores, versus C4's0.1988/0.2391; EXP optimizer0.1410/0.1629,
operational BACK optimizer0.0738/0.0884, map update0.2526/0.0953. The exact-query
optimization substantially reduces this measured stage, but common optimization
and runtime overhead still limit relative savings. Source:`c05_neighbor_cache_profile/`.

## Candidate6 preparation: common static-map publication polling

The simulator polls static `/global_pc` subscriber count every1ms, independent
of10Hz acquired LiDAR and100Hz odometry/commands. `SUPER_STATIC_PC_POLL_MS=100`
opts into a real100ms timer and one bootstrap publication at>=5s, retaining full
geometry, original QoS and publication on observed nonzero count changes.
Legacy1ms remains default. This is a common simulator-overhead optimization,
not an Adaptive sensing contribution. It deliberately removes repeated startup
publications and can delay a new subscriber by100ms plus scheduling; volatile
best-effort delivery is not guaranteed. Late-subscriber ROS tests required.

A separate common `SUPER_SIDE_EXECUTOR_THREADS` accepts4..16(default10), built
at the same time but **kept10 for candidate6**. Any4-thread flight is a separate
candidate. Both settings are logged and audited. Existing monitor subscriptions
optionally collect bounded command/odometry header and receipt intervals;
these measure received messages, not executor callback latency. Intentional
certified holds can suppress ordinary commands. No new subscriptions added.
Preflight design/unit evidence:`executor_preflight/`.

### Static-poll candidate rejected before CPU flight; executor-only trial next

Simulator build passed5min51s; C++ policy parser/state tests and43Python tests
passed. However real ROS late-reader test failed:100ms policy logged complete
241,490point publication but subscriber received nothing. Unchanged1ms legacy
late-reader control also failed. Reader-before-start legacy bootstrap delivered
6completeidentical7,727,680byte clouds out of20publications;100ms one-shot
control delivered0/2. Warm subscriber-count pulse control delivered1/6, only
atbootstrap, and0of4spacedcount-change sends. Payload is transportable, but these
observations do not distinguish all FastDDS discovery/history/fragment/resource
loss causes. Host buffers/QoS not modified; no speculative retry declared a fix.
One legacy shutdown control aborted after invalid-context graph query; retained.

**Do not enable100ms static polling based on these results.** Source option
remains experimental/defaultoff, and no C6static CPU comparison was run.
The next actual candidate is `c06_executor4_legacy_poll_profile`:common4-thread
executor only, static poll remains exactlegacy1ms, C1–C5flags retained. Match
Full/Adaptive instrumentation and inspect command/odom received-message gaps.
No claim that unchanged legacy best-effort global-map delivery is guaranteed.

### Candidate6 actual executor-only result (run9307)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 39.23 | 0.861363 | 35.778029 |
| Adaptive | 1/1,0 | 43.37 | 0.735408 | 32.933434 |

Mean reduction14.6228%, cumulative7.9507%, A/Ftime1.10553: **CPU target unmet,
and predeclared1.10time guardrail failed**. Completion/contact/resource/speed/
source/recovery checks pass (Adaptive4cycles), no retry. Not adopted as final.
Recorded unchanged boundary rather than raising the threshold after observing.

F/A odometry received99.9877/99.9852Hz, headerp99 10.154/10.169ms;
command received94.253/94.562Hz, headerp99 20.038/20.035ms,
receiptmax20.620/30.034ms. No repeated/backwards stamps or truncation.
Profiled command callback counts~99.98Hz: received messages are not callback
invocations, and guarded command suppression is expected. No identical message
interval baseline exists for old10-thread flights, so no causal jitter claim.
See `c06_executor4_legacy_poll_profile/`, `executor_preflight/c06_timing.json`.

Next candidate design retains C5's10threads/legacy1ms and15Hz demand checks,
100Hz guards/commands, but permits bounded deferral of a redundant ordinary
moving solve only with exact generation/current-map geometry and renewed sampled
stop-viability evidence, sufficient trajectory/backup horizon, no pending goal/
recovery/rejection, and a fixed dispatch deadline. It is not a blind timer
reduction. Existing sampled viability allows unknown and clearance-margin stops,
unlike stricter runtime emergency braking; no continuous stop-safety theorem.
Before flight also compare each mode's duration against C5 (<=1.10) in addition
to the matched A/Ftime guard, and report reference cumulativeCPU differences.
Design/prototypes in `demand_replan_preflight/`; not flight-validated yet.

## Candidate7 implementation: guarded demand-driven ordinary replanning

`SUPER_GUARDED_DEMAND_REPLAN=1` defaults off. It preserves15Hz demand checks,
100Hz guards/commands and source settings. Intentional solve deferral is bounded
by0.25s from the last successful ordinary solve's dispatch, with one timer tick,
scheduling allowance, configured solve budget and command-handoff reserve.
Only an actual own-generation commit can earn a lease; failure/NO_NEED/another
callback's commit cannot. Over-budget dispatch-to-own-commit cannot earn one.
There is no hard real-time guarantee against OS stalls.

Explicit SAFE geometry/current map, remaining EXP-before-backup/trajectory
coverage, finite clocks, no goal queue/update, unhandled recovery, rejection,
brake or revalidation are required. Goal metadata uses its existing mutex and
a consume-to-accept RAII scope; event completion is published atomically only
after existing main-FSM handling. Final state is rechecked. Backwards simulator
time invalidates the lease. The weaker legacy same-map coalescer is bypassed
while the new policy is enabled, so rejection cannot silently fall through.

Skip-only stop-viability renewal checks every requested state in the configured
2s horizon and actual final endpoint against an unchanged map/generation; an
unevaluated/nonfinite state invalidates its receipt. At most one renewal occurs
per demand check, on the replanning callback, and evidence/time is recollected
afterward. This does not alter normal candidate acceptance or relax the existing
sampled stop policy. The unknown/clearance caveat described above still applies.

Two independent code reviews addressed pending-event and commit-attribution
races before application. Pure helper:41gate cases,21nonfinite cases, boundary
checks and fake100Hz cadence preservation; optimized and ASan/UBSan pass.
These are not flight proof. The workspace build passed in6min43s; a final
immutable-only renewal restriction rebuilt successfully in28.2s. Renewal is
disabled for mutable map backends because slides/partial updates can change
occupancy without a committed-map version increment. Immutable profiles used
here are supported. Actual-Fsm metadata integration checks passed:17checks,
2000concurrent enqueues and4actual early moving-replan outcomes. Successful
solver-commit attribution and mixed-map/state-evaluation renewal failures were
reviewed in code, not dynamically integration-tested.45Python tests pass.
Runner now requires same-mode reference time<=1.10 (C5) for this candidate,
alongside matchedA/F<=1.10. Same-mode mean/cumulativeCPU are also recorded.

A separate opt-in `SUPER_STATIC_PC_DEDICATED_EXECUTOR=1` routes the existing
global-PC callback group to a dedicated single-thread executor. It retains the
exact1ms timer, geometry, QoS and bootstrap behavior; defaults off with no extra
thread. Cancellation/join precedes object teardown. This is a later candidate,
**off for C7**, not a claimed fix for existing best-effort map delivery failures.

### Candidate7 observed result and disqualifying lifecycle finding (run9308)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 38.12 | 0.875257 | 34.663321 |
| Adaptive | 1/1,0 | 39.43 | 0.574662 | 23.432585 |

Observed mean reduction34.3436%, cumulative32.3995%, A/Ftime1.03437;
all automated source/recovery/resource/speed/time audits pass, no retry.
**Not adopted, and below40%.** Full's last periodic counters show0skips/526checks;
Adaptive315skips/569checks,258renewal attempts. These exclude early-gated timer
callbacks and the final<5s tail; reason lines are not rejection histograms.

Read-only diagnosis found a pre-existing recovery lifecycle hole: Full's initial
PlanFromRest clearance rejection announces recovery, brake construction fails
without a fresh state, and later ordinary PlanFromRest succeeds. The announcement
is cleared only by successful active-brake recovery, so remains true for this
flight. This blocks every new demand lease in Full; the sampled NEW_GOAL reason
merely reflects its never-initialized successful-goal record. Thus the new common
optimization did not function in both modes, and34.34% is not accepted as a fair
comparison of the intended optimized policy. Repair must preserve Full-refresh/
new-path release requirements, not just remove a recovery gate.

### Candidate8 independent common-overhead ablation

While the lifecycle repair is reviewed, run the already-built dedicated static-PC
executor with C5's policy (guarded-demand OFF),1ms original static timer,10general
threads and unchanged geometry/QoS. Both modes use the same dedicated executor.
This isolates the prepared execution change without the defective demand lease.
C5 same-mode<=1.10 and matched A/F<=1.10 guards remain.

Run9309 result: Full39.36s/0.821220cores/33.353473core-s;
Adaptive43.92s/0.672997cores/30.936708core-s; both completed/contact0,
source/recovery/resource/speed checks pass, no retry. Mean reduction18.0491%,
cumulative7.2459%, A/Ftime1.11585 **fails1.10 guardrail**, though both same-mode
C5time guards pass. Not adopted as a final candidate. No guarantee inferred for
best-effort global-PC delivery from these flights. Runtime option stays off.
Adaptive has4completed source/ACK/path/release cycles; received odometry stays
~100Hz with header max10.287ms, but command header max440.047ms (p99=20.083ms).
These message-gap aggregates do not establish its cause or control-loop callback
latency; intentional guarded command suppression is possible, not proven for
this particular gap. Do not describe all command output as a guaranteed100Hz.

C9 will first repair the narrowly identified startup announcement lifecycle,
then retest demand with C7's original10thread pool/dedicated-static OFF. A new
prospective acceptance coverage check requires the common demand optimization
to have actually skipped at least once in BOTH modes; absence is not a collision
or unsafe-flight verdict, but cannot establish this intended common-policy
comparison. C7's original raw summary is preserved unchanged.

## Candidate9: startup recovery lifecycle repair

The common repair is limited to pre-first-trajectory brake state-selection failure:
generation0, empty command snapshot, no prior published command, startup state
and no active brake. Each activation invalidates the previous startup episode;
true-edge publication now occurs under the existing activation mutex. Before
retrying initial planning, supported event frontends must have an exact committed
post-event Full ACK; Full without a frontend explicitly requires none. Legacy
advertised non-event frontends are excluded because their ACK cache does not
retain committed-bit evidence. Pending goal/topology work is never held merely
because it cannot yet earn a completion proof. Activation-lock contention only
defers empty-generation0 GENERATE planning until the next main tick.

Completion requires unchanged activation/goal/event/ACK identity, current fresh
immutable map and explicit SAFE current-generation sample, no active brake/
revalidation/rejection/topology demand, and a final current-state check. A short
Full-refresh transaction emits PATH_READY before the false recovery edge and
consumes only its exact gate. Existing active-brake recovery remains unchanged.
An invalidated proof conservatively leaves the episode open; this does not repair
all possible failed-brake lifecycle cases or prove continuous runtime safety.

Pure startup helper tests:104checks pass optimized and ASan/UBSan. Independent
binding/lock review passes;46Python tests pass. Initial package build was
deliberately interrupted by root after1min24s to incorporate the reviewed lock-
contention fix; that is not a compiler failure. Final build passed in7min59s
(planner1min59s, simulator6min00s).
Evidence:`demand_replan_preflight/startup_recovery_*`, `build_candidate9*.log`.

C9 retains C7 settings:10side threads, dedicated static executor OFF,1ms static
poll,0.25s bounded demand deferral, optimizer memory trace ON. Source10Hz and
guard/command timer100Hz unchanged; real received intervals and sampled callback
counts are inspected separately. Same-mode C5 and matched timing guards remain.

Future opt-ins prepared but **not enabled for C9**: side-thread parser accepts
2..16(default10), optimized/ASan tests pass; campaign pools below4 require
dedicated static executor and message-interval audit. Two workers can still be
occupied by expensive planning/braking, so no latency guarantee follows from
the parser. `--no-optimizer-phase-memory-trace` explicitly disables only optional
per-solve /proc reads/logging in both modes; external cgroup/memory guards and
all source/ACK/path/guard evidence remain. Actual trace setting is audited.

Before any<4worker trial, predeclare extra finite-run engineering guards:
source9.5–10.5Hz; received odometry98–102Hz with headerp99<=20ms,max<=50ms,
no reordered/repeated/dropped interval records; when profiling is enabled,
main/command callback counts98–102Hz over>=5s common report window with no clock
errors. Missing evidence fails closed. Unprofiled confirmation explicitly lacks
callback counters and relies on the separate profiled validation plus its own
source/odometry audit; command message gaps alone cannot distinguish intentional
holds from delayed callbacks. These checks are not hard real-time guarantees.
The limits were specified before any2worker flight;48Python tests now pass.

### Candidate9 measured result (run9310)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 36.88 | 0.713513 | 27.430641 |
| Adaptive | 1/1,0 | 38.72 | 0.580143 | 23.527604 |

Mean reduction18.6920%, cumulative14.2287%, A/Ftime1.04989. All declared
safety/resource/speed/source/recovery/time and common-demand execution checks
pass; no retry. **40% unmet.** Full startup pendingrevision1/gen0 is completed
after42.5ms with explicit newgen1/map13. Last periodic counters Full294skips/
523checks/253renewals, Adaptive309/582/277: common optimization now works in both.
Counters exclude early-gated ticks/final partial reporting interval. Adaptive's
single completed recovery has exact FullACKmap16 then newpathgen3→4/certmap26
before false/release. Its new startup-completion branch was not exercised here.

C7's34.34% is superseded for adoption by the fair functioning-policy C9 result,
not used as a final savings claim. C10 will test the same demand policy with
dedicated static executor and2general workers, preserving traceON and all source/
guard settings. In addition to earlier small-pool gates, inspect receiver gaps
as well as producer-header gaps, and require a matching profiled preflight before
accepting an unprofiled small-pool confirmation.

### Candidate10 measured result (run9311)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 36.84 | 0.648614 | 24.920355 |
| Adaptive | 1/1,0 | 39.34 | 0.478033 | 19.869999 |

Mean reduction26.2993%, cumulative20.2660%, A/Ftime1.06786; all original and
small-pool guards pass, no retry. **40% unmet**. Main/command callbacks measured
100.0035Hz Full/100.0027Hz Adaptive; odom receiptp99/max10.521/11.572ms and
10.614/11.247ms. Source10Hz preserved. Adaptive2exact committed FullACK→newpath→
Sector cycles, no outstanding cycle or ACK timeout. Its maximum command-message
gap340.015ms corresponds to logged fail-closed brake rejection/suppression followed
by a certified stationary hold withcmd_age=.340s; callback/odom100Hz does not mean
uninterrupted100Hz command messages. See `executor_preflight/c10_timing.json`.

Exclusive middle-window profile totals F0.4474/A0.2651cores, while whole-flight
cgroup means F0.6486/A0.4780; windows differ and this residual is not pure executor
cost. C11 disables only optional per-solve optimizer memory diagnostics equally
in both modes, retaining external memory/cgroup guards and all operational logs.
Demand cap remains0.25,2workers+dedicated-static retained; profile stays ON.

### Candidate11 measured result (run9312)

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 39.69 | 0.630825 | 26.241412 |
| Adaptive | 1/1,0 | 41.38 | 0.473869 | 20.234247 |

Only optional optimizer per-solve memory trace is disabled relative to C10.
Mean reduction24.8810%, cumulative22.8919%, A/Ftime1.04258. All original and
small-pool gates pass, no retries; **40% unmet**. This n1 variation does not
establish that diagnostic removal caused a throughput improvement. C11 retains
external cgroup/resource checks and operational source/ACK/path/guard evidence.
Raw evidence:`c11_no_phase_trace_profile/`, independent timing extraction:
`executor_preflight/c11_timing.json`. Trace remains off in the next candidate.

## Candidate12 prospective: extended bounded dispatch lease and attribution

Extra opt-in `SUPER_GUARDED_DEMAND_EXTENDED_LEASE=1`, requiring the existing
demand opt-in, extends only the maximum successful ordinary-dispatch age from
0.25s to0.5s. Default remains0.25s. This is NOT a blind0.5s trajectory hold:
every eligible15Hz skip still needs current immutable map/generation, explicit
SAFE geometry covering the next approximately0.206s, renewed stop-viability
evidence, sufficient remaining EXP motion, and no new goal/recovery/rejection.
Source10Hz and main/command100Hz timers remain unchanged. All existing safety
limitations of sampled stop evidence remain; no continuous-safety theorem.

Final post-renewal decisions receive a callback-owned19-bin histogram; every
existing5s report must reconcile sum==checks and SKIP==aggregate skips, with
monotonic counters. The runner freezes the extra option, checks the actual cap,
and requires matching cap/options/binaries for any unprofiled small-pool retest.
Focused optimized and ASan/UBSan policy tests pass the original41decisions/
21nonfinite cases plus40extended unchanged-gate cases and boundary/accounting
tests. Independent policy review identified no new blocker; flight evidence
remains required. This mechanism alone is not predicted to guarantee40%.

Append-only thread CPU scopes will also cover composed simulator static-cloud,
odometry and render callbacks, with actual running-thread role/TID markers.
This separates callback CPU from executor/middleware residual; GPU device time
is not thread CPU. Profiling stays opt-in/defaultoff, and unprofiled confirmation
is still mandatory before target acceptance. Both compared modes receive the
same policy and instrumentation changes, then the same declared timing gates.

### Candidate12 measured result (run9313)

Build passed3packages in9min37s.50focused Python tests and the recorded C++
optimized/sanitizer tests pass. Each mode flown once, no retries:

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 37.48 | 0.607148 | 24.136908 |
| Adaptive | 1/1,0 | 38.48 | 0.447553 | 17.764726 |

Mean reduction26.2860%, cumulative26.4002%, A/Ftime1.02668. All safety/source/
resource/recovery/time/callback and19-bin accounting gates pass; **40% unmet**.
Main/command~100.001Hz both; odom receiptmax11.848/14.080ms. Adaptive1exact
Full observation→ACK→newpath→Sector cycle, no outstanding cycle; full episode
1057.85ms. Command-message maxgap29.96/25.03ms. Evidence:`c12_extended_lease_profile/`
and `executor_preflight/c12_timing.json`; this is still profiled n1 exploration.

Final periodic reasons F/A: SKIP379/360, checks528/514; stale-certificate10/12,
insufficient_geometry0/0, deadline31/26, motion-horizon28/23, new-goal43/38,
viability-renewal-rejected15/22. Cache refresh is therefore low priority and has
NOT been implemented. No unsafe current-map certificate may be overwritten to
increase skip rates. See `demand_replan_preflight/certificate_refresh_review.md`.

Actual labeled static executor thread CPU F0.04831/A0.04933cores; callback CPU
only0.017315/0.017366, with the remaining thread CPU including executor work.
Actual render thread0.04900/0.02329cores. The /proc averages cover wholly enclosed
sample intervals29.18/29.19s, while scope windows30.04/30.03s; never subtract as
exact full-flight attribution. Map update0.23580/0.09325cores. Static optimization
alone is not expected to guarantee40%; measured end-to-end comparison remains
the acceptance metric, not a favorable subset of instrumented stages.

## Candidate13 prospective: preserve bootstrap, reduce idle static polling

New default-off `SUPER_STATIC_PC_TWO_PHASE=1` preserves original1ms timer and
complete legacy publication behavior until an executed postbootstrap callback
at node-relative time>=5.1s. It then actually cancels that timer and invokes the
same publication/subscriber-state function from a100ms timer in the same
MutuallyExclusive group. This is distinct from the rejected100ms single-shot
bootstrap. No planner/LiDAR/odom/guard timer or geometry/QoS is changed.
Observed clock rollback/invalid time or simulated time permanently falls back
to1ms; arbitrary clock jumps between coarse samples are not equivalent timing.
Postbootstrap discovery gains up to a nominal100ms poll delay plus scheduling/
DDS delay, not a hard100ms delivery guarantee. Default remains unchanged.

Preflight requires exact complete reader-first payload/layout/SHA matching the
legacy control. Late and reconnect controls must retain/report any failure:
the existing large best-effort cloud transport failure is not repaired by this
timer change. Do not label the whole delivery suite passed from startup evidence,
or promote this exploratory batch-only option as a general late-viewer fix.
Before any candidate flight, run both reader-first and late controls/candidate
with no FSM. Matched flight also requires ready truth observer and all previous
source/quality gates; stable phase handoff and actual timer cancellation are
audited. Profiling additionally requires reduced static callback rate5..20Hz
over>=10s (allow boundary bootstrap fragments), with no clock errors. Any
unprofiled small-pool confirmation must match the passed profiled candidate.

Pure optimized/ASan/UBSan phase-policy tests and harness syntax pass;51focused
Python accounting/audit tests pass. Actual simulator build/ROS preflight pending.

### Candidate13 preflight and diagnostic result (run9314)

Simulator build passed5min57s. Reader-first legacy and two-phase both delivered
identical complete geometry/layout/SHA. Both subsequently timed out for a second
reader; both separate late-reader trials timed out. All children exited0; later
disconnect/reconnect phases were NOT reached. Whole delivery suite therefore
FAILS for both, not a validated late-viewer fix. Raw evidence and predeclared
diagnostic-only decision:`static_two_phase_preflight/ROS_FINDINGS.md`.

The runner was updated BEFORE flight to disqualify unresolved two-phase delivery
from target acceptance/unprofiled preflight eligibility;52Python tests pass.
Startup-ready CPU diagnostic, one flight/mode, no retry:

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 39.64 | 0.569059 | 23.643770 |
| Adaptive | 1/1,0 | 38.17 | 0.417815 | 16.896414 |

Mean reduction26.5779%, cumulative28.5376%, A/Ftime0.96292. Flight safety/source/
resource/recovery/time/timing and timer-cancellation checks pass; late-delivery
preservation is explicitly false, **40% unmet and candidate not adopted**.
Actual static executor CPU drops to0.001169/0.001369cores in sampled middle
windows, so the static-cost hypothesis is supported, but the relative savings
remain limited. The next functional candidate returns to default legacy1ms
static polling. Keep this optional prototype/evidence; no default promotion.

New independently quantified cause: the actual benchmark `waypoint.yaml` repeats
goals every1s. C12 Full accepted40goals (5distinct targets+35duplicates), Adaptive
41 (5+36); each duplicate is followed by a real ordinary replan commit before
the next accepted goal. Acceptance sets `gi_.new_goal`, bypassing goal-connected
NO_NEED exits. Association is by log order, not exact per-decision CPU attribution.
Next proposal uses explicit retransmission identity, not pose-only inference:
fresh user intent must remain distinguishable and blocked/recovery retries must
stay active. Producer/receiver changes remain outside runtime pending review.

## Candidate14 prospective: explicit goal retransmission identity

Return to legacy1ms static polling (two-phase OFF). New paired, default-off
`SUPER_GOAL_RETRANSMIT_IDENTITY=1` gives each mission intent a positive creation
stamp retained on its existing1Hz retransmissions. A fresh same-pose request or
waypoint advance gets a fresh ID. Exact raw position/quaternion/frame must also
match; malformed/nonfinite/unsupported IDs use ordinary goal admission. Opt-in
mission callbacks use one serialized executor; default execution is unchanged.
This candidate therefore combines command identity and mission serialization,
not an isolated causal estimate of deduplication alone.

Receiver coalescing requires an own successful ordinary replan token, unchanged
goal/state/brake/event/Full-request epochs, ordinary FOLLOW, fresh immutable map,
an exact-current SAFE certificate without escape exceptions, and a finite
unfinished nonbackup command sample within its certified interval. New/pending
goals, failure/recovery/stop/refresh or contended outer locks fall back to the
existing queue. Coalescing never renews a demand lease or mutates trajectory,
certification, goal revisions, or recovery state. Both modes must demonstrate
actual coalescing linked to producer retransmissions; zero Full coverage is not
a valid common-optimization comparison.

The same explicit intent no longer repeats original-raw-goal projection during
healthy following. Ordinary replanning still remaps its current effective goal.
This is a declared command-idempotence algorithm change, not bitwise/behavioral
equivalence to the previous repeated-intent interpretation. The outer activation,
refresh and certificate locks are try-only, but inner metadata/trajectory/map
reads can briefly block; live callback timing must still pass existing gates.

Producer Release build and direct actual-ROS controls passed: unchanged legacy
stamp behavior; opt-in three repeats share an ID, same-pose retrigger and next
waypoint each allocate a fresh ID, each then repeats correctly. Nine messages
per first attempt, no retries, receipt cadence1.00045–1.01001s opt-in. Pure helper
optimized and ASan/UBSan tests pass94checks. These tests do not validate combined
receiver/flight safety. Receiver build/integration and launch-output capture are
being checked before the new matched flight. Evidence:
`results/adaptive_cpu40_20260916/goal_retransmit_preflight/`.

### Candidate14 measured result (run9315)

Sequential planner/simulator build passed6min25s. Actual-Fsm metadata tests
passed54checks/4000concurrent requests, with existing demand regression passing
both flagOFF/ON. Pure policy optimized and ASan/UBSan tests pass. The metadata
test stubs its live proof; actual ROS/solver evidence is the separate flight.
Launch-style producer INFO capture works; its earlier fixture double-SIGINT
cleanup failure remains explicitly preserved, not claimed as clean-pass.

| Mode | Complete/contact | Mission s | Mean used cores | CPU core-s |
|---|---|---:|---:|---:|
| Full | 1/1,0 | 37.54 | 0.579354 | 22.889422 |
| Adaptive | 1/1,0 | 39.65 | 0.423070 | 17.650004 |

Mean reduction26.9756%, cumulative22.8901%, A/Ftime1.05621. All flight/source/
resource/recovery/time/callback/identity gates pass; **40% unmet**. No retries.
Full coalesces34of36 retransmissions; Adaptive33of38. Both retain5fresh intent
IDs and visit5targets. Accepted-goal logs drop to6/9, with119/128 ordinary
replan commits (C12:40/41acceptances,138/137commits). This supports the repeated
intent cause but is not an isolated causal CPU estimate from n1 trajectories.
All67coalesces link to producer repeats and nearby same-gen/map SAFE logs;
mixed stdout/stderr log ordering is NOT a strict concurrency proof.

Evidence:`c14_goal_identity_profile/`, `executor_preflight/c14_timing.json`, and
receiver flight review. Legacy1ms static polling restored; no two-phase option.
Next bounded candidate will disable unused remote ROS parameter services/event
publishers equally for composed Full/Adaptive nodes, preserving local startup
parameters, source/control periods and safety gates. This changes remote
introspection availability under an explicit headless-only opt-in, not the
planner's physical observation contract. Static durable transport and extra
frontend residual attribution remain separate unimplemented proposals.
