# Forest Active-Yaw Sector without a mission-time cutoff, n=10

## Protocol

This is a fresh Forest-only cohort (run94201--94210), not a retry or
replacement of the retained run941xx cohort. Each flight had one attempt and
failures would have been retained. The Sector half-angle, speed, map, planner
and Active-Yaw implementation were unchanged. Only the mission-time horizon was
set to positive infinity; resource and process-integrity guards remained
enabled. All ten flights passed run, resource, speed and logging quality gates.

## Per-run result

| Run | Complete | Contact | Time | Mean CPU | CPU time | Input | Map update | Minimum solid clearance |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 94201 | yes | 0 | 122.49 s | 0.4087 cores | 50.94 core-s | 3.164 MiB/s | 8.23 ms/frame | 0.147 m |
| 94202 | yes | 0 | 111.14 s | 0.3925 cores | 44.62 core-s | 2.941 MiB/s | 9.55 ms/frame | 0.101 m |
| 94203 | yes | 0 | 112.22 s | 0.4217 cores | 48.40 core-s | 2.461 MiB/s | 9.49 ms/frame | 0.206 m |
| 94204 | yes | 0 | 85.39 s | 0.4270 cores | 37.61 core-s | 2.701 MiB/s | 9.58 ms/frame | 0.308 m |
| 94205 | yes | 0 | 125.17 s | 0.3766 cores | 47.77 core-s | 3.156 MiB/s | 8.26 ms/frame | 0.242 m |
| 94206 | yes | 0 | 90.52 s | 0.4239 cores | 39.52 core-s | 2.887 MiB/s | 9.43 ms/frame | 0.263 m |
| 94207 | yes | 0 | 86.13 s | 0.4457 cores | 39.09 core-s | 2.476 MiB/s | 9.74 ms/frame | 0.255 m |
| 94208 | yes | 0 | 96.25 s | 0.4159 cores | 40.91 core-s | 3.077 MiB/s | 9.59 ms/frame | 0.227 m |
| 94209 | yes | 0 | 88.26 s | 0.4174 cores | 37.52 core-s | 2.444 MiB/s | 10.11 ms/frame | 0.254 m |
| 94210 | yes | 0 | 73.98 s | 0.4405 cores | 33.24 core-s | 2.490 MiB/s | 10.45 ms/frame | 0.311 m |

## Aggregate

- Completion: **10/10 (100%)**.
- Contact runs: **0/10 (0%)**.
- Mission time: **99.155 +/- 17.417 s**, range 73.98--125.17 s.
- Mean CPU: **0.4170 cores**; CPU time: **41.962 core-s/run**.
- Input: **2.780 MiB/s**, **280.792 MiB/run**.
- Map update: **9.444 ms/frame**.
- Minimum solid clearance: mean 0.232 m, cohort minimum **0.101 m**.
- Active-Yaw: 143 arms and 143 matching fresh-map acknowledgements. The 18
  exhaustion log records are diagnostics and are not interpreted as 18 unique
  mission failures; every flight subsequently completed.

## Interpretation

All ten flights finished before the old 180 s cutoff. The longest took 125.17 s.
Therefore this cohort does **not** demonstrate that removing the cutoff rescued
an execution after 180 s. It demonstrates only that a fresh, unpaired sample of
ten Forest Active-Yaw Sector flights happened to complete without contact.

The retained prior cohort remains 6/10 complete with 1/10 contact and
134.613 s all-run mean (104.355 s among completed runs). The new 10/10 result is
encouraging, but the cohorts use different run IDs and the same stochastic
system; their difference cannot be assigned causally to the timeout setting.
It also does not erase the previously observed blind-side in-motion contact or
provide a population-level safety guarantee. A causal timeout test would need
paired/replayed initial conditions or a run that is still making measurable
progress at 180 s and then completes after that point.

Raw run directories are retained beside this summary. `run_summary.csv` is the
compact table used above.
