# Canonical Active-Yaw Sector: Urban no-cutoff n=10

## Protocol and audit

- `Sector` now resolves through the common scenario7 runner to **Sector
  (Active-Yaw)**; the legacy body-forward-only implementation is an explicitly
  named ablation.
- Active-Yaw and the zero-return scan heartbeat are enabled for every Sector
  run. A binary/header contract is checked before every ROS launch.
- Runs 94501--94510 are fresh observations, one attempt each, retry 0, with no
  mission-time cutoff. A measurement-only 60 s stationary terminal remained
  available but was not reached.
- All ten runs passed runtime `ACTIVE_YAW_SCAN enabled=true`, source, resource,
  speed, performance-log and exact-solid-contact audits.

## Urban result

| Metric | Canonical Active-Yaw Sector |
|---|---:|
| Completion | **10/10 (100%)** |
| Contact runs | **0/10 (0%)** |
| Safe completion | **10/10 (100%)** |
| Mission time | 78.075 ± 9.229 s |
| Cohort minimum solid clearance | 0.421 m |
| Mean CPU | 0.41935 cores |
| Cumulative CPU | 33.622 core-s/run |
| Input bandwidth | 2.552 MiB/s |
| Total input | 198.363 MiB/run |
| Map computation | 10.696 ms/frame |
| Active-Yaw arms / fresh-map ready | 96 / 96 |

Four `EXHAUSTED` diagnostic records occurred in two runs, while the aggregate
ARM and fresh-map-ready counts were both 96 and all ten missions completed
without contact. The diagnostic record count is not a mission failure count.

## Urban comparison

Full and Adaptive below are retained v12 controls; they are not run-ID paired
with the new Sector cohort, so this is a descriptive comparison only.

| Metric | Full | Sector (Active-Yaw) | Adaptive |
|---|---:|---:|---:|
| Completion | 10/10 | **10/10** | 10/10 |
| Contact runs | 0/10 | **0/10** | 0/10 |
| Mission time | 48.321 s | **78.075 s** | 51.303 s |
| Mean CPU | 0.69848 cores | **0.41935 cores (-39.96%)** | 0.51090 cores |
| Cumulative CPU | 37.023 core-s | **33.622 core-s (-9.19%)** | 28.627 core-s |
| Input bandwidth | 11.638 MiB/s | **2.552 MiB/s (-78.07%)** | 3.358 MiB/s |
| Total input | 562.314 MiB | **198.363 MiB (-64.72%)** | 173.131 MiB |
| Map computation | 27.609 ms/frame | **10.696 ms/frame (-61.26%)** | 11.334 ms/frame |

Active-Yaw Sector trades time for observation recovery: it is 61.58% slower
than Full and 52.18% slower than Adaptive in this Urban cohort.

## Existing Map 1--5 and Forest configuration audit

Every listed row was independently checked for exactly one runtime
`ACTIVE_YAW_SCAN enabled=true` contract and a valid source-acquisition audit.

| Scenario | Active-Yaw-valid runs | Completion | Contact runs | Yaw arms |
|---|---:|---:|---:|---:|
| Map 1 | 10/10 | 10/10 | 0/10 | 133 |
| Map 2 | 10/10 | 10/10 | 0/10 | 78 |
| Map 3 | 10/10 | 9/10 | 1/10 | 118 |
| Map 4 | 10/10 | 10/10 | 0/10 | 97 |
| Map 5 | 10/10 | 10/10 | 0/10 | 88 |
| Forest, retained first cohort | 10/10 | 6/10 | 1/10 | 154 |
| Forest, fresh no-cutoff cohort | 10/10 | **10/10** | **0/10** | 143 |

The fresh Forest cohort is the currently selected descriptive result, but the
earlier 6/10 and one-contact cohort remains preserved evidence. The difference
between independent stochastic cohorts cannot be attributed causally to removal
of the 180 s cutoff because every fresh run finished before 126 s.

Using Map1--5 from the completed replacement campaign, the fresh no-cutoff
Forest cohort, and this fresh Urban cohort gives a **descriptive composite** of
69/70 completion (98.57%) and 1/70 contact runs (1.43%). Its means are 80.059 s,
0.42425 CPU cores, 34.488 core-s/run, 2.804 MiB/s input, 231.465 MiB/run and
9.714 ms/map frame. This is not a single paired or preregistered 70-run cohort;
it must be labeled as a composite assembled from three independent campaigns.

The misconfigured Urban run94401--94410 cohort is retained under
`urban_fixed_sector_no_mission_timeout_n10_20260930` as a legacy Fixed Sector
ablation only and is excluded from canonical Sector tables.
