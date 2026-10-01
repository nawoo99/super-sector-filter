# c40 no-mission-cutoff seven-map results

Provenance: 72 preserved original flights plus 138 unflown slots completed in a separate session; the original run96445 fixed-count audit verdict remains untouched. The corrected event-chain audit passes all 210 physical flights. There were no retries or replacements.

All 210 planned flights used an infinite mission horizon. A declared,
measurement-only 60 s/2 cm no-progress event terminates absorbing stalls
as failures. Completion time below uses completed flights only; outcome
time includes any no-progress terminal and is not traversal time.

| Map | Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | No-progress terminal | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame | Full opens |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gapfree_d1_m01 | full | 10/10 | 0/10 | 55.25/53.61 | 55.25 | 0 | 0.748 | 44.57 | 11.241 | 624.84 | 30.24 | — |
| gapfree_d1_m01 | sector | 9/10 | 1/10 | 95.12/83.43 | 99.00 | 1 | 0.412 | 41.65 | 3.225 | 337.52 | 8.47 | — |
| gapfree_d1_m01 | adaptive | 10/10 | 0/10 | 55.80/55.53 | 55.80 | 0 | 0.507 | 30.28 | 3.955 | 221.37 | 12.42 | 9.00 |
| gapfree_d1_m02 | full | 10/10 | 0/10 | 48.39/48.49 | 48.39 | 0 | 0.762 | 40.10 | 10.939 | 529.99 | 32.24 | — |
| gapfree_d1_m02 | sector | 10/10 | 0/10 | 65.39/64.67 | 65.39 | 0 | 0.433 | 29.95 | 2.606 | 170.16 | 9.98 | — |
| gapfree_d1_m02 | adaptive | 10/10 | 0/10 | 50.95/50.64 | 50.95 | 0 | 0.510 | 27.98 | 3.584 | 184.09 | 12.13 | 6.00 |
| gapfree_d1_m03 | full | 10/10 | 0/10 | 47.89/46.33 | 47.89 | 0 | 0.731 | 38.06 | 11.037 | 528.52 | 31.08 | — |
| gapfree_d1_m03 | sector | 10/10 | 0/10 | 79.69/74.73 | 79.69 | 0 | 0.424 | 35.27 | 2.808 | 223.10 | 9.50 | — |
| gapfree_d1_m03 | adaptive | 10/10 | 0/10 | 58.42/53.64 | 58.42 | 0 | 0.511 | 32.04 | 4.349 | 264.22 | 12.21 | 8.50 |
| gapfree_d1_m04 | full | 10/10 | 0/10 | 53.91/53.75 | 53.91 | 0 | 0.732 | 42.44 | 10.884 | 587.42 | 29.36 | — |
| gapfree_d1_m04 | sector | 10/10 | 0/10 | 70.09/67.10 | 70.09 | 0 | 0.431 | 31.86 | 2.858 | 200.95 | 9.24 | — |
| gapfree_d1_m04 | adaptive | 10/10 | 0/10 | 55.40/50.03 | 55.40 | 0 | 0.504 | 29.83 | 4.232 | 248.94 | 12.38 | 7.60 |
| gapfree_d1_m05r2 | full | 10/10 | 0/10 | 46.63/45.52 | 46.63 | 0 | 0.700 | 35.37 | 11.365 | 529.21 | 28.45 | — |
| gapfree_d1_m05r2 | sector | 10/10 | 0/10 | 69.60/68.26 | 69.60 | 0 | 0.429 | 31.42 | 3.019 | 210.71 | 9.05 | — |
| gapfree_d1_m05r2 | adaptive | 10/10 | 0/10 | 50.41/50.39 | 50.41 | 0 | 0.493 | 26.82 | 3.974 | 201.15 | 11.74 | 6.60 |
| urban_blocks_u01 | full | 10/10 | 0/10 | 50.46/49.87 | 50.46 | 0 | 0.746 | 41.72 | 11.729 | 591.00 | 32.11 | — |
| urban_blocks_u01 | sector | 10/10 | 0/10 | 86.15/84.24 | 86.15 | 0 | 0.417 | 37.92 | 2.594 | 222.80 | 10.06 | — |
| urban_blocks_u01 | adaptive | 10/10 | 0/10 | 52.09/50.86 | 52.09 | 0 | 0.507 | 28.90 | 3.267 | 170.41 | 12.32 | 6.50 |
| forest_cluster_f01 | full | 10/10 | 0/10 | 60.77/58.47 | 60.77 | 0 | 0.771 | 50.64 | 11.014 | 672.18 | 32.33 | — |
| forest_cluster_f01 | sector | 8/10 | 0/10 | 101.02/88.04 | 103.63 | 2 | 0.416 | 44.90 | 2.878 | 307.50 | 8.65 | — |
| forest_cluster_f01 | adaptive | 10/10 | 0/10 | 63.31/62.53 | 63.31 | 0 | 0.508 | 34.61 | 3.898 | 251.50 | 12.59 | 9.80 |

## Cohorts

### Normal Map1–5

| Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 50/50 | 0/50 | 50.41/48.71 | 50.41 | 0.735 | 40.11 | 11.093 | 560.00 | 30.27 |
| sector | 49/50 | 1/50 | 75.59/69.95 | 76.75 | 0.426 | 34.03 | 2.903 | 228.49 | 9.25 |
| adaptive | 50/50 | 0/50 | 54.19/52.64 | 54.19 | 0.505 | 29.39 | 4.019 | 223.95 | 12.18 |

### Urban

| Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 10/10 | 0/10 | 50.46/49.87 | 50.46 | 0.746 | 41.72 | 11.729 | 591.00 | 32.11 |
| sector | 10/10 | 0/10 | 86.15/84.24 | 86.15 | 0.417 | 37.92 | 2.594 | 222.80 | 10.06 |
| adaptive | 10/10 | 0/10 | 52.09/50.86 | 52.09 | 0.507 | 28.90 | 3.267 | 170.41 | 12.32 |

### Forest

| Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 10/10 | 0/10 | 60.77/58.47 | 60.77 | 0.771 | 50.64 | 11.014 | 672.18 | 32.33 |
| sector | 8/10 | 0/10 | 101.02/88.04 | 103.63 | 0.416 | 44.90 | 2.878 | 307.50 | 8.65 |
| adaptive | 10/10 | 0/10 | 63.31/62.53 | 63.31 | 0.508 | 34.61 | 3.898 | 251.50 | 12.59 |

### All seven maps

| Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 70/70 | 0/70 | 51.90/50.59 | 51.90 | 0.741 | 41.84 | 11.173 | 580.45 | 30.83 |
| sector | 67/70 | 1/70 | 80.20/73.23 | 81.93 | 0.423 | 36.14 | 2.855 | 238.96 | 9.28 |
| adaptive | 70/70 | 0/70 | 55.20/53.72 | 55.20 | 0.506 | 30.07 | 3.894 | 220.24 | 12.26 |
