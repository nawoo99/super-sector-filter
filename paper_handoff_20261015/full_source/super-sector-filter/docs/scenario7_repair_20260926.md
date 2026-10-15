# Scenario7 repair cohort — 2026-09-26

## Scope and immutable baseline

The user authorized analysis and repair after the seven-map campaign. The completed
baseline is `results/scenario7_n10_20260925_213533_3120932`; its failures, source
inventory and original `/root/super_ws/install` binaries remain unchanged. This is
a **new candidate**, `c26_scenario7_repair_v1`, not a retroactive correction of
baseline outcomes. Maps, missions, sensor profiles, safety/timing thresholds and
resource limits are not tuned. Normal G1–G5 remain one reporting group; Urban and
Forest remain separate groups. Do not pool old/new cohorts.

## Findings and repairs

| Incident | Evidence | Repair / remaining uncertainty |
|---|---|---|
| G4 Sector r08 memory runaway | Planning thread captured in `SimplifySFC`; RSS 3375 to 4740 MiB within about 10 s. Disconnected real-box witness repeats the same bridge forever in the old implementation. | Require progress and a valid overlapping bridge; fail without mutating the input corridor. Normal and sanitizer regressions pass. Exact recorded corridor was not captured, so the witness is not a replay of its geometry. |
| G1 Adaptive r06 stopped until timeout | Repeated certified stopped-footprint departure commits immediately rejected by the live refresh, which lacked the admission exception. | Carry a generation-bound immutable receipt of only the initially exempted occupied centres, original origin and finite deadline. Live refresh cannot add cells or renew the window. |
| G1 Adaptive r08 contact / command discontinuity | About 0.913 m command/pose jump in 10.18 ms after a 1.25x slowed command was replaced using an unscaled EXP cache. | Reject stale cached-EXP reuse and P/V/A-discontinuous moving-command handoffs at the same absolute time. Preserve old certified command; existing stop/recovery handles rejection. Closed-loop liveness still requires testing. |
| G1 Adaptive r01 smooth contact | Eight analytic contact samples, minimum clearance about -0.0176 m; no corresponding command jump. Original ROI map/cloud traces were disabled. | **Not resolved or excused.** Missing sector observation vs voxel geometry cannot yet be distinguished from these logs. Keep this failure and collect targeted evidence. |
| Urban ON observer timing failure then all OFF children missing references | Adaptive ON completed with zero analytic contacts, but received odometry missed the unchanged timing gate. Later modes were not run. OFF raised missing-summary errors before flight. | Exact-semantics occupied-cell enumeration makes observer nearest-PCD queries cheaper. Preserve timing failures, independently check remaining modes where safe, and record structured BLOCKED_BY_PREFLIGHT for missing/invalid references before any OFF flight. |

The footprint receipt is not permission to ignore new obstacles, a moving-origin
mask, or a general relaxation of occupancy. The continuity tolerances (1 mm,
0.01 m/s, 0.1 m/s²) check numerical state agreement, not collision clearance.
Raw-cloud CIRI shadow stays default false and is not connected to brake decisions.

## Validation architecture

Runtime edits are in `/root/super_ws/src/SUPER`, mirrored under
`super_patches/native_seedmap_campaign`. The repair build is isolated at
`/root/super_ws/scenario7_repair_20260926/install` (rog_map, super_planner,
perfect_drone_sim). All three packages built successfully. The initial simulator
build exhausted memory because colcon appended `-j20 -l20` despite
CMAKE_BUILD_PARALLEL_LEVEL=1. Retrying with `MAKEFLAGS='-j1 -l1'` succeeded.
No old install binaries were replaced; build resource failure is not flight data.

New `run_scenario7_repair.py/.sh`, `scenario7_cpu_compare_v3.py` and
`scenario7_repair_runtime.py` bind actual launches, static tests, profiler and
reference audits to this overlay. Frozen previous scripts remain unchanged. The
controller compares the old evidence inventory and permits only explicitly
listed repairs, then records a new source/binary/observer inventory. `--rounds`
allows 1 through 10 (default 10); report denominators use the actual plan. Missing
or invalid preflight evidence never becomes an eligible OFF trial. There is no
automatic retry or replacement of failed trials; RSS guard remains 4608 MiB.

The new observer keeps the native observer's geometry, float32 distance, capped
search semantics, tie ordering, QoS and timing gates. It enumerates occupied hash
cells in the search box instead of iterating thousands of empty cells in Python.
Offline real-cloud equivalence tests passed; Urban initial-radius microbenchmark
median was 17.211 ms before versus 1.182 ms after (20 queries, not flight CPU).
This explains a credible observer-induced loss mechanism but does not substitute
for a received-odometry gate passing in a new flight. No SciPy upgrade was used.

## Test status and next gate

Standalone memory/progress, trajectory-handoff and receipt-helper normal and
sanitizer tests pass. Versioned runner/preflight/runtime/observer unit regressions
are being finalized. New flights have not yet run as of this protocol freeze.
First execute a separate G1/G4/Urban three-mode n=1 smoke with fresh static and ON
qualification. Preserve failures and inspect handoff/recovery/odometry traces;
do not launch a replacement 210-flight campaign or claim complete contact repair
before these checks. Store subsequent results and a report alongside the frozen
protocol rather than modifying a running cohort's frozen files.
