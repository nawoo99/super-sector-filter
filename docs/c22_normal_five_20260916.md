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
Active root: `results/c22_normal_five_20260916/iteration03` (short-lease candidate).
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

### Iteration02: first flight-stage rejection

All five maps passed static transport and RViz proof. Instrumented N1/N2 triplets
passed. N3(seed5) completed all three modes with contact0 and valid source,
resource, speed, recovery and odometry gates, but Adaptive43.94s/Full37.83s =
1.1615 exceeded the unchanged paired time1.10 gate (Sector41.44s). Controller
stopped after nine preflight flights, before any n5/n20 OFF flight. N4/N5
preflight flights have not run. This is not a completion/contact failure.

Adaptive had five certified Full cycles, including startup. Its four moving
episodes reported CLEARANCE_MARGIN, not VERSION_CHANGED. Full dwell durations
were approximately0.359/0.711/0.381/0.944/0.883s; these do not include the whole
deceleration/reacceleration loss. Paths F/S/A221.488/223.004/227.048m also differ.
Full had one accepted brake; Sector three; Adaptive five. Limited observations,
path selection, repeated braking and solver scheduling all remain possible
contributors; the logs do not prove a single cause of the entire time gap.

Next diagnostic, declared before execution: seed5 F/S/A one instrumented flight
each, common replan lease shortened from the opt-in0.5s to its existing0.25s
default. No runtime source/binary changes, speed/map/safety/publication/Full-ACK-
new-path gates unchanged. Hypothesis: less deferred replanning can reduce stale
path use and braking; this is not established until measured. Diagnostic is
separate, not a replacement pilot row. If adopted, start a new full five-map
preflight/pilot before considering n20. A failure is retained and investigated.

### Short-lease diagnostic and iteration03 candidate

Diagnostic `diagnostic_lease025_seed5`, run10250, ON only:

| seed5 | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Time s | 40.55 | 42.63 | 42.75 |
| CPU cores (instrumented) | 0.660145 | 0.422426 | 0.439510 |
| Cumulative CPU core-s (instrumented) | 27.875458 | 18.763855 | 19.546003 |
| Accepted brakes | 1 | 3 | 4 |
| Contact events | 0 | 0 | 0 |

All three completed with valid contracts; A/F1.0543. Adaptive is1.19s faster
than iteration02 and has one fewer Full cycle, but Full is2.72s slower and takes
a longer path. The improved ratio is therefore NOT proof of eliminating the
original delay; n1 cannot establish causality. CPU savings are instrumented
diagnostic only, not final OFF results. All old observations remain.

Iteration03 prospectively adopts the existing common0.25s lease as a conservative
candidate (less deferred replanning), not a proven fix. It reruns every static,
five-map ON preflight and OFF n5 slot before n20. No runtime/source/binary/map
changes; only the common environment option changes. Keep the original timing
gates unless the user explicitly authorizes a prospective protocol change.
