# Sector (Active-Yaw) replacement campaign: Map 1--5 and Forest, n=10

## Protocol

This is a fresh 60-flight cohort (run94101--94160), with ten runs per map,
rotated map order, one attempt per flight, no retry and no replacement. Contact
and incomplete missions were retained as outcomes and did not stop the batch.
All 60 runs passed the infrastructure, resource, speed and logging quality gates.
The legacy Fixed Sector data were preserved rather than overwritten.

## Results

| Map | Completion | Contact runs | Time, all runs (mean ± SD) | Time, completed only | Min clearance | Yaw views |
|---|---:|---:|---:|---:|---:|---:|
| Map 1 | 10/10 | 0/10 | 87.21 ± 17.13 s | 87.21 s | 0.162 m | 133 |
| Map 2 | 10/10 | 0/10 | 67.21 ± 7.89 s | 67.21 s | 0.187 m | 78 |
| Map 3 | **9/10** | **1/10** | 89.55 ± 34.54 s | 79.50 s | **-0.174 m** | 118 |
| Map 4 | 10/10 | 0/10 | 71.68 ± 11.43 s | 71.68 s | 0.029 m | 97 |
| Map 5 | 10/10 | 0/10 | 67.54 ± 9.99 s | 67.54 s | 0.251 m | 88 |
| Forest | **6/10** | **1/10** | 134.61 ± 41.14 s | 104.36 s | **-0.143 m** | 154 |

The five gap-free maps together produced 49/50 completions and 1/50 contact
runs. Forest produced 6/10 completions and 1/10 contact runs. Across all six maps
the result was 55/60 completions (91.67%) and 2/60 contact runs (3.33%). The five
incomplete runs were Map3 run94113 and Forest runs94121, 94142, 94152 and94157;
runs94113 and94157 were also the two contact runs.

## Failure reconstruction

Both contacts occurred while the vehicle was still translating, before an
active-yaw observation could begin. Map3 run94113 entered `cylinder_0238` at
about 4.71 m/s; immediately beforehand the guard repeatedly rejected candidates
whose appended backup intersected the newly observed obstacle, then rejected
the emergency brake because the motion generation was discontinuous. Forest
run94157 entered `trunk_024` at about 6.80 m/s; the guard activated recovery at
6.91 m/s only after the path became occupied, and again could not publish a
certified brake. Active-yaw is intentionally armed only after a certified
stationary hold, so it cannot prevent either class of blind-side in-motion
contact. The later prolonged contact samples are downstream of these first
entries, not independent contact episodes; each run contains one episode.

## Compute and input metrics

| Scope | Mean CPU | CPU time/run | Input bandwidth | Total input/run | Map update |
|---|---:|---:|---:|---:|---:|
| Map 1--5 (n=50) | 0.4267 cores | 33.17 core-s | 2.854 MiB/s | 228.14 MiB | 9.57 ms/frame |
| Forest (n=10) | 0.4077 cores | 54.81 core-s | 3.597 MiB/s | 520.34 MiB | 8.02 ms/frame |
| All six maps (n=60) | 0.4235 cores | 36.77 core-s | 2.978 MiB/s | 276.84 MiB | 9.31 ms/frame |

Against the retained Full controls on Map1--5, Active-Yaw Sector reduced mean
CPU by38.30%, cumulative CPU by13.66%, input bandwidth by74.54%, and map-update
time by62.34%, but increased mean mission time by47.63%. On Forest it reduced
mean CPU by44.17%, input by67.62%, and map-update time by70.95%, but its four
timeouts increased mission time by116.74% and cumulative CPU by13.89% relative
to Full.

## Replacement decision

The new method should not silently replace the legacy Fixed Sector result. On
Map1--5 both versions produced49/50 completions and1/50 contact runs, while the
new method was slower (76.64s versus54.96s mean). It moved the single failure
from Map4 to Map3 rather than eliminating it. In Forest, completion decreased
from8/10 to6/10, contact runs decreased from2/10 to1/10, and mean time increased
from88.19s to134.61s. Urban remains a separate favorable result (10/10,
contact0), but that benefit did not generalize to every map.

For publication, retain the original method as `Legacy Fixed Sector` and name
this method `Sector (Active-Yaw)` or `Fixed Sector + Active-Yaw Recovery`. It is
a useful ablation showing that topology-changing observation can remove Urban
deadlock, but post-stop yaw alone cannot match Adaptive's safety and completion
across dense Forest and all gap-free maps.
