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
