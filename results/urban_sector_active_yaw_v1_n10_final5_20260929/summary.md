# Urban Fixed Sector active-yaw recovery, n=10

- Map: `urban_blocks_u01`
- Waypoints: `urban_building_corners_v3.txt`
- Speed limit: 7 m/s
- Sector: body-yaw-centered horizontal half-angle 45 degrees
- Candidate: `sector_active_yaw_scan_v1`
- Valid runs: 10/10; infrastructure retries: 0

## Outcome

| Mode | Completion | Contact runs | Mission time (mean ± sample SD) | Difference from Full |
|---|---:|---:|---:|---:|
| Full (existing control) | 10/10 | 0/10 | 48.321 ± 1.493 s | baseline |
| Adaptive (existing control) | 10/10 | 0/10 | 51.303 ± 4.534 s | +2.982 s (+6.17%) |
| Fixed Sector (old control) | 1/10 | 3/10 | 168.424 ± 36.631 s | +120.103 s (+248.55%) |
| Fixed Sector + active yaw scan | 10/10 | 0/10 | 75.446 ± 7.361 s | +27.125 s (+56.14%) |

The new Fixed Sector recovery removed the urban deadlock in this cohort and
reduced mean mission time by 92.978 s (55.20%) relative to the old Fixed
Sector cohort. It remains 24.143 s (47.06%) slower than Adaptive because it
must stop and physically rotate before acquiring off-axis observations.

## Recovery activity

| Run | Mission time (s) | Active-yaw episodes | Yaw views acquired | Complete | Contacts |
|---:|---:|---:|---:|---:|---:|
| 93701 | 87.16 | 5 | 11 | yes | 0 |
| 93702 | 64.78 | 5 | 6 | yes | 0 |
| 93703 | 68.16 | 5 | 6 | yes | 0 |
| 93704 | 73.19 | 6 | 8 | yes | 0 |
| 93705 | 71.79 | 6 | 8 | yes | 0 |
| 93706 | 70.77 | 7 | 8 | yes | 0 |
| 93707 | 75.69 | 7 | 10 | yes | 0 |
| 93708 | 86.03 | 8 | 14 | yes | 0 |
| 93709 | 75.87 | 7 | 9 | yes | 0 |
| 93710 | 81.02 | 7 | 11 | yes | 0 |
| Mean ± SD | 75.446 ± 7.361 | 6.3 ± 1.059 | 9.1 ± 2.470 | 10/10 | 0/10 |

All ten logs have zero `MAP_NOT_READY` and zero
`ACTIVE_YAW_SCAN_EXHAUSTED` events. Valid zero-return sector frames are
recorded as committed no-op observations: they refresh scan/commit health but
do not change occupancy, `map_version`, or the immutable map snapshot.

Existing controls are from
`results/scenario7_velocity_centered_v12_n10_20260928/summary_by_map.csv`.
The active-yaw and empty-scan behaviors are opt-in for the Fixed Sector test;
the Full and Adaptive default paths remain disabled and unchanged.
