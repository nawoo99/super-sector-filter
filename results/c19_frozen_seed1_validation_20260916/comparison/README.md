# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c19_frozen_validation — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 5 | 5 | 5 |
| Successes | 5 | 5 | 5 |
| Valid runs | 5 | 5 | 5 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 5 runs per mode; all planned run rows observed. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 37.808 ± 1.183 [35.89, 39.06] | 38.288 ± 1.512 [36, 40.2] | 38.682 ± 1.012 [37.3, 39.55] | -1.27% | -2.31% |
| Path length (m) | 221.94 ± 0.9364 [220.38, 222.7] | 222.3 ± 1.505 [220, 223.96] | 222.24 ± 1.218 [221.11, 223.6] | -0.16% | -0.13% |
| Minimum static-PC clearance (m) | 0.3444 ± 0.0446 [0.282, 0.406] | 0.3254 ± 0.02334 [0.3, 0.354] | 0.3404 ± 0.01711 [0.32, 0.356] | 5.52% | 1.16% |
| Experiment CPU (cores) | 0.5345 ± 0.01413 [0.52012, 0.55751] | 0.34756 ± 0.01646 [0.32504, 0.36504] | 0.35144 ± 0.01919 [0.34141, 0.38568] | 34.97% | 34.25% |
| Experiment CPU (whole-host %) | 2.6725 ± 0.07064 [2.6006, 2.7876] | 1.7378 ± 0.08228 [1.6252, 1.8252] | 1.7572 ± 0.09593 [1.707, 1.9284] | 34.97% | 34.25% |
| Experiment measurement-window CPU (core-s) | 20.943 ± 1.086 [19.433, 22.482] | 13.928 ± 0.8168 [12.932, 14.633] | 14.059 ± 0.7091 [13.248, 15.18] | 33.50% | 32.87% |
| Accounting window (s) | 39.163 ± 1.088 [37.362, 40.326] | 40.067 ± 1.18 [38.407, 41.584] | 40.023 ± 1.158 [38.394, 41.377] | -2.31% | -2.19% |
| Experiment CPU 1 s p95 (cores) | 0.65482 ± 0.03847 [0.60501, 0.70732] | 0.4406 ± 0.04178 [0.38791, 0.48731] | 0.43699 ± 0.03074 [0.41275, 0.49034] | 32.71% | 33.27% |
| Experiment CPU 1 s maximum (cores) | 0.73543 ± 0.1013 [0.63926, 0.87139] | 0.48773 ± 0.04327 [0.44011, 0.55408] | 0.50401 ± 0.03798 [0.46945, 0.56738] | 33.68% | 31.47% |
| Composed runtime CPU (cores; includes simulator) | 0.4952 ± 0.01471 [0.47946, 0.5193] | 0.30405 ± 0.01713 [0.28152, 0.32083] | 0.30888 ± 0.01722 [0.29798, 0.33913] | 38.60% | 37.63% |
| Composed runtime measurement-window CPU (core-s) | 19.405 ± 1.074 [17.914, 20.941] | 12.185 ± 0.8164 [11.204, 12.871] | 12.355 ± 0.6169 [11.687, 13.348] | 37.21% | 36.33% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.4629 ± 0.1642 [3.2811, 3.6293] | 3.7052 ± 0.1766 [3.4524, 3.9496] | 3.6304 ± 0.1938 [3.3448, 3.8504] | -7.00% | -4.84% |
| Whole-host CPU (%) | 9.8836 ± 0.7642 [9.4141, 11.243] | 9.2943 ± 0.4321 [8.764, 9.7483] | 9.4405 ± 0.3195 [9.0674, 9.8335] | 5.96% | 4.48% |
| Baseline whole-host CPU (%) | 7.1366 ± 0.8336 [6.4715, 8.519] | 7.6072 ± 0.8878 [6.2544, 8.4692] | 7.7967 ± 0.3909 [7.1499, 8.1203] | -6.59% | -9.25% |
| Experiment sampled peak RSS (MiB) | 3383.4 ± 1.101 [3381.5, 3384.2] | 3376.9 ± 2.806 [3374.2, 3381.1] | 3377.5 ± 1.473 [3375.3, 3379.3] | 0.19% | 0.17% |
| Experiment sampled peak PSS (MiB) | 3343.6 ± 1.091 [3341.9, 3344.5] | 3337.2 ± 2.851 [3334.4, 3341.6] | 3337.7 ± 1.507 [3335.4, 3339.6] | 0.19% | 0.18% |
| Experiment sampled peak process swap (MiB) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5763.4 ± 6.175 [5754.7, 5771.6] | 5789.8 ± 12.18 [5774.8, 5808.3] | 5793.1 ± 14.34 [5781.3, 5817.5] | -0.46% | -0.51% |
| GPU device utilization (%) | 48.635 ± 2.939 [44.081, 51.375] | 49.633 ± 2.148 [46.308, 51.947] | 49.703 ± 3.368 [44.854, 53.103] | -2.05% | -2.20% |
| GPU device utilization p95 (%) | 52.6 ± 2.881 [49, 55] | 53.2 ± 0.8367 [52, 54] | 52.2 ± 3.114 [47, 55] | -1.14% | 0.76% |
| GPU device memory-controller utilization (%) | 19.246 ± 0.1986 [19.051, 19.462] | 19.199 ± 0.1892 [19.026, 19.488] | 19.24 ± 0.3723 [19, 19.875] | 0.24% | 0.03% |
| GPU device memory (MiB) | 1287.6 ± 2.784 [1283.3, 1290.5] | 1287.7 ± 2.116 [1284.1, 1289.6] | 1286.7 ± 2.753 [1282.9, 1289.3] | -0.01% | 0.06% |
| GPU device power (W; not flight attribution) | 18.913 ± 0.03458 [18.885, 18.967] | 18.87 ± 0.04343 [18.813, 18.935] | 18.875 ± 0.08359 [18.787, 18.988] | 0.22% | 0.20% |
| Observed source frame records | 390.8 ± 10.21 [373, 399] | 400 ± 12.55 [382, 416] | 399.8 ± 11.34 [384, 413] | -2.35% | -2.30% |
| Observed source readback width (pixels/frame) | 900 ± 0 [900, 900] | 225 ± 0 [225, 225] | 246.94 ± 3.618 [244.61, 253.33] | 75.00% | 72.56% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 ± 0 [8.01e+05, 8.01e+05] | 2.0025e+05 ± 0 [2.0025e+05, 2.0025e+05] | 2.1978e+05 ± 3220 [2.1771e+05, 2.2547e+05] | 75.00% | 72.56% |
| Observed source conversion rays (/frame) | 1.152e+05 ± 0 [1.152e+05, 1.152e+05] | 28800 ± 0 [28800, 28800] | 31608 ± 463.1 [31310, 32427] | 75.00% | 72.56% |
| Observed source generated points (/frame) | 15790 ± 524.3 [15340, 16538] | 4513 ± 277.8 [4116.2, 4880.5] | 4608 ± 194.3 [4299, 4827.2] | 71.42% | 70.82% |
| Observed source cloud payload (bytes/frame) | 5.0528e+05 ± 1.678e+04 [4.9087e+05, 5.2922e+05] | 1.4442e+05 ± 8890 [1.3172e+05, 1.5617e+05] | 1.4746e+05 ± 6217 [1.3757e+05, 1.5447e+05] | 71.42% | 70.82% |
| Map total elapsed mean (ms/frame) | 25.403 ± 0.9379 [24.108, 26.487] | 9.5 ± 0.383 [9.051, 9.9259] | 10.141 ± 0.4723 [9.3446, 10.609] | 62.60% | 60.08% |
| Map total elapsed p95 (ms/frame) | 32.866 ± 1.347 [31.163, 34.463] | 14.188 ± 0.5591 [13.333, 14.745] | 16.317 ± 1.041 [14.613, 17.168] | 56.83% | 50.35% |
| Map total elapsed max (ms/frame) | 74.985 ± 19.01 [54.156, 97.579] | 23.738 ± 4.05 [18.858, 27.447] | 38.11 ± 0.5664 [37.482, 38.662] | 68.34% | 49.18% |
| Map raycast elapsed mean (ms/frame) | 15.619 ± 0.6504 [14.644, 16.249] | 6.3115 ± 0.3032 [5.97, 6.6413] | 6.6385 ± 0.3484 [6.0605, 7.002] | 59.59% | 57.50% |
| Map update elapsed mean (ms/frame) | 9.7824 ± 0.3199 [9.4621, 10.237] | 3.187 ± 0.08861 [3.0795, 3.2831] | 3.5014 ± 0.1306 [3.2827, 3.6053] | 67.42% | 64.21% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2932 ± 0.03601 [1.2497, 1.3455] | 0.65371 ± 0.01994 [0.62586, 0.67641] | 0.68457 ± 0.02647 [0.64526, 0.71414] | 49.45% | 47.06% |
| Map processed frames / mission time (Hz proxy) | 10.317 ± 0.07329 [10.215, 10.406] | 10.435 ± 0.1275 [10.323, 10.611] | 10.33 ± 0.07647 [10.253, 10.442] | -1.15% | -0.13% |
| Trajectory commits (Hz) | 3.235 ± 0.1213 [3.1258, 3.4357] | 3.1659 ± 0.15 [3.0148, 3.3683] | 3.1164 ± 0.2012 [2.8792, 3.3981] | 2.14% | 3.67% |
| Goal retransmissions coalesced | 32.4 ± 0.8944 [31, 33] | 32.2 ± 1.304 [31, 34] | 31.4 ± 0.8944 [31, 33] | 0.62% | 3.09% |
| Demand replan checks (latest cumulative report) | 525.4 ± 1.673 [524, 528] | 567.6 ± 39.51 [520, 604] | 553.8 ± 40.47 [508, 585] | -8.03% | -5.41% |
| Demand replans skipped (latest cumulative report) | 386.6 ± 11.1 [375, 398] | 414.2 ± 21.35 [382, 433] | 410.2 ± 42.8 [359, 443] | -7.14% | -6.10% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.017302 ± 0.002521 [0.015471, 0.021673] | 0.015278 ± 0.001469 [0.013533, 0.017436] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.5318 ± 0.9511 [0.059, 2.232] | 0.1386 ± 0.04067 [0.097, 0.206] | N/A | N/A |
| Map points mean (/frame) | 15801 ± 518.4 [15354, 16538] | 4514.7 ± 275.9 [4116.2, 4874.8] | 4609.1 ± 194.5 [4299, 4827.2] | 71.43% | 70.83% |
| Map points / mission time (points/s proxy) | 1.6299e+05 ± 4289 [1.5978e+05, 1.6894e+05] | 47087 ± 2438 [43678, 50332] | 47608 ± 1938 [44386, 49494] | 71.11% | 70.79% |
| Map payload / mission time (MiB/s proxy, logical edge) | 4.974 ± 0.1309 [4.8761, 5.1555] | 1.437 ± 0.07441 [1.3329, 1.536] | 1.4529 ± 0.05915 [1.3545, 1.5104] | 71.11% | 70.79% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.867 ± 0.1972 [4.6989, 5.1361] | 1.4007 ± 0.1004 [1.2691, 1.5442] | 1.4321 ± 0.0659 [1.3217, 1.4899] | 71.22% | 70.57% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 4.974 ± 0.1309 [4.8761, 5.1555] | 1.437 ± 0.07441 [1.3329, 1.536] | 1.4529 ± 0.05915 [1.3545, 1.5104] | 71.11% | 70.79% |
| DDS cloud payload (MiB/s, logical messages) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 ± 0.0005215 [9.9993, 10.001] | 10.001 ± 0.0001076 [10, 10.001] | 10.001 ± 0.0002364 [10, 10.001] | -0.00% | -0.01% |
| Received odometry frequency (Hz) | 100 ± 0.001798 [99.998, 100] | 100 ± 0.001687 [99.999, 100] | 100 ± 0.001723 [99.999, 100] | -0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 94.413 ± 0.7656 [93.544, 95.177] | 93.687 ± 0.7839 [92.452, 94.424] | 95.098 ± 1.234 [92.998, 95.954] | 0.77% | -0.73% |
| Odometry receipt p99 gap (ms) | 10.655 ± 0.06613 [10.572, 10.716] | 10.785 ± 0.07686 [10.71, 10.905] | 10.774 ± 0.04374 [10.73, 10.826] | -1.21% | -1.12% |
| Odometry receipt max gap (ms) | 12.203 ± 2.06 [11.156, 15.886] | 12.09 ± 1.233 [11.119, 13.851] | 11.684 ± 0.4815 [11.183, 12.197] | 0.92% | 4.25% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1 ± 0 [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 ± 0 [0, 0] | 3.3226 ± 0.5552 [2.963, 4.304] | N/A | N/A |
| Guard active duration (s) | 0.12296 ± 0.1542 [0.041893, 0.3983] | 0.86644 ± 0.4852 [0.37679, 1.3564] | 1.3332 ± 0.2305 [1.2123, 1.745] | -604.66% | -984.24% |

## seed1 — c19_frozen_validation — profiled_supplement

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 1 | 1 |
| Successes | 1 | 1 | 1 |
| Valid runs | 1 | 1 | 1 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 1 runs per mode; all planned run rows observed. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 38.89 (n=1) [38.89, 38.89] | 37.23 (n=1) [37.23, 37.23] | 38.57 (n=1) [38.57, 38.57] | 4.27% | 0.82% |
| Path length (m) | 224.28 (n=1) [224.28, 224.28] | 220.67 (n=1) [220.67, 220.67] | 222.37 (n=1) [222.37, 222.37] | 1.61% | 0.85% |
| Minimum static-PC clearance (m) | 0.346 (n=1) [0.346, 0.346] | 0.276 (n=1) [0.276, 0.276] | 0.365 (n=1) [0.365, 0.365] | 20.23% | -5.49% |
| Experiment CPU (cores) | 0.50973 (n=1) [0.50973, 0.50973] | 0.34352 (n=1) [0.34352, 0.34352] | 0.36414 (n=1) [0.36414, 0.36414] | 32.61% | 28.56% |
| Experiment CPU (whole-host %) | 2.5487 (n=1) [2.5487, 2.5487] | 1.7176 (n=1) [1.7176, 1.7176] | 1.8207 (n=1) [1.8207, 1.8207] | 32.61% | 28.56% |
| Experiment measurement-window CPU (core-s) | 20.491 (n=1) [20.491, 20.491] | 13.128 (n=1) [13.128, 13.128] | 14.677 (n=1) [14.677, 14.677] | 35.93% | 28.37% |
| Accounting window (s) | 40.2 (n=1) [40.2, 40.2] | 38.217 (n=1) [38.217, 38.217] | 40.307 (n=1) [40.307, 40.307] | 4.93% | -0.27% |
| Experiment CPU 1 s p95 (cores) | 0.64803 (n=1) [0.64803, 0.64803] | 0.44657 (n=1) [0.44657, 0.44657] | 0.45323 (n=1) [0.45323, 0.45323] | 31.09% | 30.06% |
| Experiment CPU 1 s maximum (cores) | 0.67891 (n=1) [0.67891, 0.67891] | 0.48666 (n=1) [0.48666, 0.48666] | 0.47958 (n=1) [0.47958, 0.47958] | 28.32% | 29.36% |
| Composed runtime CPU (cores; includes simulator) | 0.47113 (n=1) [0.47113, 0.47113] | 0.29901 (n=1) [0.29901, 0.29901] | 0.31986 (n=1) [0.31986, 0.31986] | 36.53% | 32.11% |
| Composed runtime measurement-window CPU (core-s) | 18.94 (n=1) [18.94, 18.94] | 11.427 (n=1) [11.427, 11.427] | 12.892 (n=1) [12.892, 12.892] | 39.67% | 31.93% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 2.9845 (n=1) [2.9845, 2.9845] | 3.2683 (n=1) [3.2683, 3.2683] | 3.3293 (n=1) [3.3293, 3.3293] | -9.51% | -11.55% |
| Whole-host CPU (%) | 9.9047 (n=1) [9.9047, 9.9047] | 9.0146 (n=1) [9.0146, 9.0146] | 9.8719 (n=1) [9.8719, 9.8719] | 8.99% | 0.33% |
| Baseline whole-host CPU (%) | 8.4712 (n=1) [8.4712, 8.4712] | 8.5978 (n=1) [8.5978, 8.5978] | 7.3308 (n=1) [7.3308, 7.3308] | -1.49% | 13.46% |
| Experiment sampled peak RSS (MiB) | 3382.7 (n=1) [3382.7, 3382.7] | 3375.9 (n=1) [3375.9, 3375.9] | 3378.6 (n=1) [3378.6, 3378.6] | 0.20% | 0.12% |
| Experiment sampled peak PSS (MiB) | 3342.7 (n=1) [3342.7, 3342.7] | 3335.9 (n=1) [3335.9, 3335.9] | 3339.1 (n=1) [3339.1, 3339.1] | 0.20% | 0.11% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5749.8 (n=1) [5749.8, 5749.8] | 5810.4 (n=1) [5810.4, 5810.4] | 5781.5 (n=1) [5781.5, 5781.5] | -1.05% | -0.55% |
| GPU device utilization (%) | 46.5 (n=1) [46.5, 46.5] | 51.342 (n=1) [51.342, 51.342] | 52.45 (n=1) [52.45, 52.45] | -10.41% | -12.80% |
| GPU device utilization p95 (%) | 53 (n=1) [53, 53] | 54 (n=1) [54, 54] | 56 (n=1) [56, 56] | -1.89% | -5.66% |
| GPU device memory-controller utilization (%) | 18.825 (n=1) [18.825, 18.825] | 19.184 (n=1) [19.184, 19.184] | 19.35 (n=1) [19.35, 19.35] | -1.91% | -2.79% |
| GPU device memory (MiB) | 1294.4 (n=1) [1294.4, 1294.4] | 1288.3 (n=1) [1288.3, 1288.3] | 1290.1 (n=1) [1290.1, 1290.1] | 0.47% | 0.33% |
| GPU device power (W; not flight attribution) | 18.806 (n=1) [18.806, 18.806] | 18.777 (n=1) [18.777, 18.777] | 18.835 (n=1) [18.835, 18.835] | 0.16% | -0.15% |
| Observed source frame records | 402 (n=1) [402, 402] | 382 (n=1) [382, 382] | 401 (n=1) [401, 401] | 4.98% | 0.25% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 245.2 (n=1) [245.2, 245.2] | 75.00% | 72.76% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1823e+05 (n=1) [2.1823e+05, 2.1823e+05] | 75.00% | 72.76% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31386 (n=1) [31386, 31386] | 75.00% | 72.76% |
| Observed source generated points (/frame) | 15628 (n=1) [15628, 15628] | 4583.4 (n=1) [4583.4, 4583.4] | 4605.7 (n=1) [4605.7, 4605.7] | 70.67% | 70.53% |
| Observed source cloud payload (bytes/frame) | 5.0009e+05 (n=1) [5.0009e+05, 5.0009e+05] | 1.4667e+05 (n=1) [1.4667e+05, 1.4667e+05] | 1.4738e+05 (n=1) [1.4738e+05, 1.4738e+05] | 70.67% | 70.53% |
| Map total elapsed mean (ms/frame) | 23.989 (n=1) [23.989, 23.989] | 9.2749 (n=1) [9.2749, 9.2749] | 10.186 (n=1) [10.186, 10.186] | 61.34% | 57.54% |
| Map total elapsed p95 (ms/frame) | 31.638 (n=1) [31.638, 31.638] | 13.906 (n=1) [13.906, 13.906] | 15.668 (n=1) [15.668, 15.668] | 56.05% | 50.48% |
| Map total elapsed max (ms/frame) | 68.301 (n=1) [68.301, 68.301] | 25.303 (n=1) [25.303, 25.303] | 40.226 (n=1) [40.226, 40.226] | 62.95% | 41.10% |
| Map raycast elapsed mean (ms/frame) | 14.794 (n=1) [14.794, 14.794] | 6.0407 (n=1) [6.0407, 6.0407] | 6.6795 (n=1) [6.6795, 6.6795] | 59.17% | 54.85% |
| Map update elapsed mean (ms/frame) | 9.1937 (n=1) [9.1937, 9.1937] | 3.2329 (n=1) [3.2329, 3.2329] | 3.5045 (n=1) [3.5045, 3.5045] | 64.84% | 61.88% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2182 (n=1) [1.2182, 1.2182] | 0.67897 (n=1) [0.67897, 0.67897] | 0.68553 (n=1) [0.68553, 0.68553] | 44.27% | 43.73% |
| Map processed frames / mission time (Hz proxy) | 10.337 (n=1) [10.337, 10.337] | 10.261 (n=1) [10.261, 10.261] | 10.397 (n=1) [10.397, 10.397] | 0.74% | -0.58% |
| Trajectory commits (Hz) | 3.1602 (n=1) [3.1602, 3.1602] | 3.2885 (n=1) [3.2885, 3.2885] | 3.214 (n=1) [3.214, 3.214] | -4.06% | -1.70% |
| Goal retransmissions coalesced | 31 (n=1) [31, 31] | 30 (n=1) [30, 30] | 32 (n=1) [32, 32] | 3.23% | -3.23% |
| Demand replan checks (latest cumulative report) | 527 (n=1) [527, 527] | 526 (n=1) [526, 526] | 511 (n=1) [511, 511] | 0.19% | 3.04% |
| Demand replans skipped (latest cumulative report) | 397 (n=1) [397, 397] | 379 (n=1) [379, 379] | 376 (n=1) [376, 376] | 4.53% | 5.29% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.017691 (n=1) [0.017691, 0.017691] | 0.018823 (n=1) [0.018823, 0.018823] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.043 (n=1) [0.043, 0.043] | 0.097 (n=1) [0.097, 0.097] | N/A | N/A |
| Map points mean (/frame) | 15628 (n=1) [15628, 15628] | 4583.4 (n=1) [4583.4, 4583.4] | 4605.7 (n=1) [4605.7, 4605.7] | 70.67% | 70.53% |
| Map points / mission time (points/s proxy) | 1.6154e+05 (n=1) [1.6154e+05, 1.6154e+05] | 47028 (n=1) [47028, 47028] | 47884 (n=1) [47884, 47884] | 70.89% | 70.36% |
| Map payload / mission time (MiB/s proxy, logical edge) | 4.9298 (n=1) [4.9298, 4.9298] | 1.4352 (n=1) [1.4352, 1.4352] | 1.4613 (n=1) [1.4613, 1.4613] | 70.89% | 70.36% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.7886 (n=1) [4.7886, 4.7886] | 1.4198 (n=1) [1.4198, 1.4198] | 1.4112 (n=1) [1.4112, 1.4112] | 70.35% | 70.53% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 4.9298 (n=1) [4.9298, 4.9298] | 1.4352 (n=1) [1.4352, 1.4352] | 1.4613 (n=1) [1.4613, 1.4613] | 70.89% | 70.36% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 0.00% | -0.00% |
| Received odometry frequency (Hz) | 99.992 (n=1) [99.992, 99.992] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | -0.01% | -0.01% |
| Received command frequency (Hz; holds included) | 95.243 (n=1) [95.243, 95.243] | 96.001 (n=1) [96.001, 96.001] | 96.223 (n=1) [96.223, 96.223] | -0.80% | -1.03% |
| Odometry receipt p99 gap (ms) | 10.671 (n=1) [10.671, 10.671] | 10.679 (n=1) [10.679, 10.679] | 10.847 (n=1) [10.847, 10.847] | -0.07% | -1.65% |
| Odometry receipt max gap (ms) | 40.648 (n=1) [40.648, 40.648] | 16.86 (n=1) [16.86, 16.86] | 13.659 (n=1) [13.659, 13.659] | 58.52% | 66.40% |
| Actual FSM main callback frequency (profiled only) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 0.00% | 0.00% |
| Actual FSM command callback frequency (profiled only) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.038 (n=1) [3.038, 3.038] | N/A | N/A |
| Guard active duration (s) | 0.98618 (n=1) [0.98618, 0.98618] | 0.34531 (n=1) [0.34531, 0.34531] | 1.2396 (n=1) [1.2396, 1.2396] | 64.98% | -25.70% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c19_frozen_seed1_validation_20260916/profile_preflight_run9400/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| fsm_command_callback / 0 | 0.00739882 | 0.00980319 | 0.00727121 |
| fsm_main_callback / 0 | 0.000507995 | 0.000590677 | 0.000564187 |
| fsm_main_core / 0 | 0.000358616 | 0.000375155 | 0.000382494 |
| fsm_poly_publish / 0 | 2.04907e-05 | 2.27421e-05 | 2.4382e-05 |
| fsm_replan_callback / 0 | 0.000256983 | 0.000278562 | 0.000293068 |
| fsm_replan_core / 0 | 0.00014143 | 0.000157048 | 0.000172156 |
| guard_brake / 0 | 0 | 0 | 0 |
| guard_certificate / 0 | 0.0010154 | 0.00116263 | 0.00101661 |
| guard_recover / 0 | N/A | 0 | 0 |
| map_ack_and_log / 0 | 0.000711554 | 0.00119513 | 0.00129828 |
| map_cloud_enqueue / 0 | 6.51702e-05 | 7.63319e-05 | 8.94411e-05 |
| map_prob_update / 0 | 0.220713 | 0.0899091 | 0.095547 |
| map_ros_to_pcl / 0 | 0.00419191 | 0.000885334 | 0.000919568 |
| map_snapshot_commit_health / 0 | 0.0454966 | 0.0203962 | 0.0206738 |
| map_worker / 0 | 7.06381e-05 | 6.35463e-05 | 6.9243e-05 |
| planner_backup_optimize / 0 | 0.0108873 | 0.00918259 | 0.0148517 |
| planner_commit / 0 | 0.000216796 | 0.000248892 | 0.000251894 |
| planner_corridor_search / 0 | 0.00426692 | 0.00515538 | 0.00535689 |
| planner_exp_optimize / 0 | 0.0278297 | 0.0345229 | 0.0324034 |
| planner_generate_backup / 0 | 0.00844871 | 0.00871616 | 0.00930746 |
| planner_generate_exp / 0 | 0.000201017 | 0.000246361 | 0.000253982 |
| planner_path_search / 0 | 0.00895063 | 0.0108547 | 0.012121 |
| planner_stop_viability / 0 | 0.000342715 | 0.000339251 | 0.000403173 |
| planner_validate_geometry / 0 | 0.00343562 | 0.00368693 | 0.00420256 |
| planner_velocity_extrema / 0 | 5.24519e-05 | 5.94628e-05 | 6.03721e-05 |
| planner_visualize_path / 0 | 0.000478242 | 0.000586747 | 0.000433799 |
| sim_odom_callback / 0 | 0.0094547 | 0.00907402 | 0.0130421 |
| sim_render_callback / 0 | 0.0439352 | 0.0160878 | 0.0195986 |

## Interpretation and measurement boundaries

- Primary = cpu_profile:false; instrumented preflight/stage results are separate supplemental cohorts.
- Each observation is one run. Means and sample SD are across run-level values, never pooled 1 Hz samples. SD is unavailable for n=1.
- All recorded attempts remain, including failed/invalid runs. Missing, NaN and infinity are unavailable, never zero. Aborted slots with no raw.csv row cannot be inferred; inspect campaign status.
- Reduction = 100*(Full run-mean - mode run-mean)/Full run-mean. No reduction is defined for zero Full or missing values. A decrease is not automatically a benefit.
- CPU cores are average utilized logical cores; whole-host capacity percent = 100*cores/logical_cpus. Cgroup CPU excludes the external measurement observer but includes simulator, frontend/planner, mission and launch processes. Core-s covers cgroup_cpu_duration_s, a measurement window slightly wider than mission_time_s; do not divide it by mission time to recompute mean CPU.
- The algorithm cgroup is a composed simulator+planner(+frontend) process here, NOT autonomy-only CPU. fsm_cpu_pct is also not pure planner CPU in this configuration.
- GPU utilization, GPU memory and GPU power are whole-device observations including background. Host CPU is whole-host including background. Baseline subtraction would not establish causal attribution.
- PointCloud payload counts measure logical data at the named pipeline edge, not physical NIC/PCIe/DRAM bandwidth. Same shared buffer may be counted on multiple edges; do not add nested delivery totals as unique bytes.
- Map frames/points/payload rates use mission duration as denominator although the captured performance slice includes startup; these are historical mission-normalized proxies, not exact source frequency. sensor_hz uses its own source-report span; latest periodic source byte/frame counters are not necessarily full-flight totals.
- source_logged metrics describe only observed SOURCE_ACQUISITION log records: per-frame rays/readback/points/bytes and coverage checks, not inferred full-flight totals or time duty. Readback pixels and converted rays are different work counters, not executed GPU instructions.
- Event-recovery cycles, certified closures and observed source Sector-to-Full/Full-to-Sector changes are distinct from legacy filter risk-switch counters. Initial recovery is not evidence of an avoided collision; no collision-avoidance count is inferred.
- Map callback timing is elapsed wall time, not thread CPU time. Inflation is nested within update/total; do not add the timing columns. Sum of callback wall time is not CPU core-s.
- Command/odometry received frequencies and intervals include transport and observer jitter; command holds may be intentional. They are not producer callback frequency. Actual callback counts are unavailable with CPU profiling OFF unless independently instrumented.
- Per-run p95/max are summarized across runs, not represented as a pooled campaign p95/max. Per-process percentages are sampled diagnostics, not a substitute for cumulative cgroup accounting.
- RSS/PSS/swap peaks are sampled peaks (periodic plus boundary samples), not continuous maxima. Summed RSS can count shared pages more than once; PSS is preferable for aggregate physical-memory comparisons.
- Success/contact observations are finite-run results, not population guarantees. CPU-to-completion comparisons are outcome-confounded if a mode does not complete all attempts.
- A candidate name is not proof of identical configuration. Asset hash/policy fingerprints are reported; inspect differing fingerprints before pooling scientifically.

## Complete data

- `all_metrics.csv`: all available numeric metrics, run-weighted statistics and signed reductions.
- `run_metrics.csv`: original run identity and per-run numeric observations, including failures.
- `metric_inventory.csv`: coverage and unavailable fields.
- `comparison.json`: full machine-readable report and separately tagged profiled stage supplements.
- Per-process/TID identities, trace event arrays, configuration strings remain in linked original artifacts; they are not cross-run scalar measurements.
- [Detailed measurement-scope audit](/root/super-sector-filter/docs/cpu_metric_scope_audit_20260916.md).
