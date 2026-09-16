# C22: Normal 5-map staged validation (2026-09-16)

## Prospective protocol

User request: five Normal maps, five repetitions per mode; investigate and fix
problems, restart after a fix; only after passing, run twenty independent
repetitions per map/mode. Preserve all attempted flights and computational data.

| Label | Frozen map | Cylinder count | Diameter (m) | Height (m) | Minimum surface gap (m, approximate) |
|---|---|---:|---:|---:|---:|
| N1 | seed1 | 410 | 0.30 | 3 | 1 |
| N2 | seed3 | 410 | 0.55 | 3 | 1 |
| N3 | seed5 | 410 | 0.80 | 3 | 1 |
| N4 | seed7 | 410 | 1.05 | 3 | 1 |
| N5 | seed9 | 410 | 1.30 | 3 | 1 |

Initial runtime is the unchanged C21 three-side-worker candidate, common to all
modes. No map geometry, planner policy, speed, acquisition frequency, safety
threshold, or mission change is made for this initial iteration. Full is the
current guarded/optimized implementation, not an unmodified SUPER baseline.

Order: map-specific static-cloud transport and actual RViz checks (no flight),
then one instrumented three-mode preflight per map (15 flights), then profile-OFF
n5 (75 flights). Only a complete passing pilot permits a separate profile-OFF
n20 cohort (300 additional flights). Mode and map orders rotate prospectively.
The pilot, confirmation, instrumented preflights and historical Normal/C21
results are never pooled. A failure is retained; no automatic replacement.
Corrections require a new iteration and a fresh pilot, not selecting passing
runs from earlier attempts.

Inherited quality gates: completion/contact0, valid speed/resource/source/
recovery contracts; 9.5–10.5 Hz source; 98–102 Hz odometry, p99 <=20 ms and maximum
<=50 ms intervals, no source-header regressions/repeats or interval-record loss;
profiled FSM rates checked separately. Adaptive/Full paired mission time <=1.10.
Historical time ceilings also apply; historical CPU values are not controls for
this candidate. Seed1 retains its prior reference; other maps use the upper
median time row of all ten frozen physical-map/mode historical observations.

CPU savings are reported, not a run-selection criterion. The prior 30% cohort
mean engineering target does not redefine the original 40% request as achieved.
Finite successful simulation repetitions do not guarantee population-level
100% success or hard real-time deadlines.

## Measurement changes before flight

The older runner names refer to seed1. They now accept a map identity throughout:
static proof, profiler cgroup lookup, source/recovery audit and stage-log paths.
Previously the observer lookup would have searched a seed1 cgroup on every map.
Every run now requires nonempty process/thread and cgroup telemetry.

Static-cloud acceptance uses an explicit immutable map context. All five
serialized XYZ/intensity point-cloud hashes were independently reconstructed
from their frozen ASCII PCDs and checked in tests. Each map must additionally
pass six real DDS transport cases and actual RViz late-subscription/reconnect;
the independent canonical hashes are not mislabeled as newly measured legacy
control runs. Source/config/binary/map/evidence hashes are frozen before launch.

Recorded: completion/contact, mission time/path/clearance, mean experiment CPU
cores and host-capacity %, cumulative core-s and accounting-window duration,
individual sampled process/thread CPU, host/background CPU, RSS/PSS/swap/PSI,
device-wide GPU utilization, map update timings, logical point/payload volume,
source/odometry intervals, instrumented FSM and stage timing, adaptive switches
and certified recovery evidence. All raw rows/logs are retained, including
invalid attempts. Unmeasured quantities remain N/A, never zero.

Experiment CPU includes the composed simulator/frontend/planner plus mission
and launcher, excluding the external observer. This is not planner-only CPU.
Logical payload is not measured physical wire bandwidth; GPU scope is the whole
device. Instrumented stage timings are supplemental and not pooled with OFF
CPU measurements. Available GPU power readings are device-wide diagnostics;
per-algorithm power and energy are not measured.

## Execution and status

Controller: `scripts/native_campaign/run_c22_normal_campaign.py`.
Active root: `results/c22_normal_five_20260916/iteration02`.
The controller writes immutable plans, per-triplet acceptance, phase gates,
phase-specific all-metric reports and an atomic `status.json`.

Preparation tests: 116 Python tests passed after controller/report hardening
and the historical-reference regression check. Actual flight results are
not yet available at protocol creation. Follow `status.json` for progress; a
planned command is not evidence of execution or success.

Iteration01 stopped before any static test or flight: the runner incorrectly
required all historical timing references to have contact0. The frozen Normal
CSV actually contains one Sector contact in seed9 (all ten runs completed).
Historical data are used only for a mission-time ceiling, not safety acceptance.
The reference calculation now keeps all ten rows, discloses historical contact
counts, and takes their upper median without filtering the contact observation.
Current-flight acceptance is unchanged. The initial error log and partial
reference files are retained; iteration02 starts a new prospective cohort.
