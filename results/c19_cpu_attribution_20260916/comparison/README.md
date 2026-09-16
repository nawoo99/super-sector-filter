# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c19_diagnostic_attribution — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 1 | 1 |
| Successes | 1 | 1 | 1 |
| Valid runs | 1 | 1 | 1 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Planned run count unavailable in supplied root manifest; observed counts above do not establish campaign completion.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 37.67 (n=1) [37.67, 37.67] | 36.76 (n=1) [36.76, 36.76] | 43.75 (n=1) [43.75, 43.75] | 2.42% | -16.14% |
| Path length (m) | 221.83 (n=1) [221.83, 221.83] | 219.39 (n=1) [219.39, 219.39] | 223.1 (n=1) [223.1, 223.1] | 1.10% | -0.57% |
| Minimum static-PC clearance (m) | 0.358 (n=1) [0.358, 0.358] | 0.306 (n=1) [0.306, 0.306] | 0.313 (n=1) [0.313, 0.313] | 14.53% | 12.57% |
| Experiment CPU (cores) | 0.53083 (n=1) [0.53083, 0.53083] | 0.34877 (n=1) [0.34877, 0.34877] | 0.36841 (n=1) [0.36841, 0.36841] | 34.30% | 30.60% |
| Experiment CPU (whole-host %) | 2.6542 (n=1) [2.6542, 2.6542] | 1.7438 (n=1) [1.7438, 1.7438] | 1.8421 (n=1) [1.8421, 1.8421] | 34.30% | 30.60% |
| Experiment measurement-window CPU (core-s) | 21.013 (n=1) [21.013, 21.013] | 13.457 (n=1) [13.457, 13.457] | 16.497 (n=1) [16.497, 16.497] | 35.96% | 21.49% |
| Accounting window (s) | 39.584 (n=1) [39.584, 39.584] | 38.584 (n=1) [38.584, 38.584] | 44.777 (n=1) [44.777, 44.777] | 2.53% | -13.12% |
| Experiment CPU 1 s p95 (cores) | 0.6839 (n=1) [0.6839, 0.6839] | 0.4165 (n=1) [0.4165, 0.4165] | 0.4739 (n=1) [0.4739, 0.4739] | 39.10% | 30.71% |
| Experiment CPU 1 s maximum (cores) | 0.73866 (n=1) [0.73866, 0.73866] | 0.42041 (n=1) [0.42041, 0.42041] | 0.5557 (n=1) [0.5557, 0.5557] | 43.09% | 24.77% |
| Composed runtime CPU (cores; includes simulator) | 0.49016 (n=1) [0.49016, 0.49016] | 0.30278 (n=1) [0.30278, 0.30278] | 0.32463 (n=1) [0.32463, 0.32463] | 38.23% | 33.77% |
| Composed runtime measurement-window CPU (core-s) | 19.403 (n=1) [19.403, 19.403] | 11.682 (n=1) [11.682, 11.682] | 14.536 (n=1) [14.536, 14.536] | 39.79% | 25.08% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.953 (n=1) [3.953, 3.953] | 4.0507 (n=1) [4.0507, 4.0507] | 4.1302 (n=1) [4.1302, 4.1302] | -2.47% | -4.48% |
| Whole-host CPU (%) | 9.9754 (n=1) [9.9754, 9.9754] | 10.281 (n=1) [10.281, 10.281] | 9.9306 (n=1) [9.9306, 9.9306] | -3.06% | 0.45% |
| Baseline whole-host CPU (%) | 7.9298 (n=1) [7.9298, 7.9298] | 9.081 (n=1) [9.081, 9.081] | 7.8381 (n=1) [7.8381, 7.8381] | -14.52% | 1.16% |
| Experiment sampled peak RSS (MiB) | 3381.7 (n=1) [3381.7, 3381.7] | 3373.7 (n=1) [3373.7, 3373.7] | 3379.6 (n=1) [3379.6, 3379.6] | 0.24% | 0.06% |
| Experiment sampled peak PSS (MiB) | 3342 (n=1) [3342, 3342] | 3333.7 (n=1) [3333.7, 3333.7] | 3339.7 (n=1) [3339.7, 3339.7] | 0.25% | 0.07% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5728 (n=1) [5728, 5728] | 5785.8 (n=1) [5785.8, 5785.8] | 5785.3 (n=1) [5785.3, 5785.3] | -1.01% | -1.00% |
| GPU device utilization (%) | 46.513 (n=1) [46.513, 46.513] | 45.897 (n=1) [45.897, 45.897] | 47.222 (n=1) [47.222, 47.222] | 1.32% | -1.53% |
| GPU device utilization p95 (%) | 51 (n=1) [51, 51] | 52 (n=1) [52, 52] | 53 (n=1) [53, 53] | -1.96% | -3.92% |
| GPU device memory-controller utilization (%) | 19.077 (n=1) [19.077, 19.077] | 19 (n=1) [19, 19] | 19.022 (n=1) [19.022, 19.022] | 0.40% | 0.29% |
| GPU device memory (MiB) | 1262.4 (n=1) [1262.4, 1262.4] | 1271 (n=1) [1271, 1271] | 1267.2 (n=1) [1267.2, 1267.2] | -0.69% | -0.38% |
| GPU device power (W; not flight attribution) | 18.904 (n=1) [18.904, 18.904] | 18.785 (n=1) [18.785, 18.785] | 18.832 (n=1) [18.832, 18.832] | 0.63% | 0.38% |
| Observed source frame records | 395 (n=1) [395, 395] | 384 (n=1) [384, 384] | 447 (n=1) [447, 447] | 2.78% | -13.16% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 288.42 (n=1) [288.42, 288.42] | 75.00% | 67.95% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.567e+05 (n=1) [2.567e+05, 2.567e+05] | 75.00% | 67.95% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 36918 (n=1) [36918, 36918] | 75.00% | 67.95% |
| Observed source generated points (/frame) | 15489 (n=1) [15489, 15489] | 4128.5 (n=1) [4128.5, 4128.5] | 4929.9 (n=1) [4929.9, 4929.9] | 73.35% | 68.17% |
| Observed source cloud payload (bytes/frame) | 4.9565e+05 (n=1) [4.9565e+05, 4.9565e+05] | 1.3211e+05 (n=1) [1.3211e+05, 1.3211e+05] | 1.5776e+05 (n=1) [1.5776e+05, 1.5776e+05] | 73.35% | 68.17% |
| Map total elapsed mean (ms/frame) | 25.453 (n=1) [25.453, 25.453] | 9.5744 (n=1) [9.5744, 9.5744] | 10.324 (n=1) [10.324, 10.324] | 62.38% | 59.44% |
| Map total elapsed p95 (ms/frame) | 33.131 (n=1) [33.131, 33.131] | 14.22 (n=1) [14.22, 14.22] | 22.214 (n=1) [22.214, 22.214] | 57.08% | 32.95% |
| Map total elapsed max (ms/frame) | 77.563 (n=1) [77.563, 77.563] | 22.083 (n=1) [22.083, 22.083] | 44.553 (n=1) [44.553, 44.553] | 71.53% | 42.56% |
| Map raycast elapsed mean (ms/frame) | 15.764 (n=1) [15.764, 15.764] | 6.321 (n=1) [6.321, 6.321] | 6.7117 (n=1) [6.7117, 6.7117] | 59.90% | 57.42% |
| Map update elapsed mean (ms/frame) | 9.6873 (n=1) [9.6873, 9.6873] | 3.2521 (n=1) [3.2521, 3.2521] | 3.6111 (n=1) [3.6111, 3.6111] | 66.43% | 62.72% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2526 (n=1) [1.2526, 1.2526] | 0.65949 (n=1) [0.65949, 0.65949] | 0.63844 (n=1) [0.63844, 0.63844] | 47.35% | 49.03% |
| Map processed frames / mission time (Hz proxy) | 10.459 (n=1) [10.459, 10.459] | 10.446 (n=1) [10.446, 10.446] | 10.217 (n=1) [10.217, 10.217] | 0.13% | 2.31% |
| Trajectory commits (Hz) | 3.1878 (n=1) [3.1878, 3.1878] | 3.3503 (n=1) [3.3503, 3.3503] | 3.2652 (n=1) [3.2652, 3.2652] | -5.10% | -2.43% |
| Goal retransmissions coalesced | 30 (n=1) [30, 30] | 30 (n=1) [30, 30] | 33 (n=1) [33, 33] | 0.00% | -10.00% |
| Demand replan checks (latest cumulative report) | 525 (n=1) [525, 525] | 528 (n=1) [528, 528] | 555 (n=1) [555, 555] | -0.57% | -5.71% |
| Demand replans skipped (latest cumulative report) | 389 (n=1) [389, 389] | 389 (n=1) [389, 389] | 380 (n=1) [380, 380] | 0.00% | 2.31% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.014617 (n=1) [0.014617, 0.014617] | 0.013919 (n=1) [0.013919, 0.013919] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.067 (n=1) [0.067, 0.067] | 0.118 (n=1) [0.118, 0.118] | N/A | N/A |
| Map points mean (/frame) | 15504 (n=1) [15504, 15504] | 4128.5 (n=1) [4128.5, 4128.5] | 4929.9 (n=1) [4929.9, 4929.9] | 73.37% | 68.20% |
| Map points / mission time (points/s proxy) | 1.6216e+05 (n=1) [1.6216e+05, 1.6216e+05] | 43127 (n=1) [43127, 43127] | 50369 (n=1) [50369, 50369] | 73.40% | 68.94% |
| Map payload / mission time (MiB/s proxy, logical edge) | 4.9487 (n=1) [4.9487, 4.9487] | 1.3161 (n=1) [1.3161, 1.3161] | 1.5371 (n=1) [1.5371, 1.5371] | 73.40% | 68.94% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.7658 (n=1) [4.7658, 4.7658] | 1.2869 (n=1) [1.2869, 1.2869] | 1.5739 (n=1) [1.5739, 1.5739] | 73.00% | 66.97% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 4.9487 (n=1) [4.9487, 4.9487] | 1.3161 (n=1) [1.3161, 1.3161] | 1.5371 (n=1) [1.5371, 1.5371] | 73.40% | 68.94% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | 10.001 (n=1) [10.001, 10.001] | 0.01% | 0.01% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 95.471 (n=1) [95.471, 95.471] | 93.924 (n=1) [93.924, 93.924] | 95.709 (n=1) [95.709, 95.709] | 1.62% | -0.25% |
| Odometry receipt p99 gap (ms) | 10.768 (n=1) [10.768, 10.768] | 10.892 (n=1) [10.892, 10.892] | 10.687 (n=1) [10.687, 10.687] | -1.15% | 0.76% |
| Odometry receipt max gap (ms) | 15.743 (n=1) [15.743, 15.743] | 11.291 (n=1) [11.291, 11.291] | 15.585 (n=1) [15.585, 15.585] | 28.28% | 1.00% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 9.438 (n=1) [9.438, 9.438] | N/A | N/A |
| Guard active duration (s) | 0.056209 (n=1) [0.056209, 0.056209] | 0.3723 (n=1) [0.3723, 0.3723] | 4.3231 (n=1) [4.3231, 4.3231] | -562.35% | -7591.24% |

## seed1 — c19_diagnostic_attribution — profiled_supplement

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 1 | 1 |
| Successes | 1 | 1 | 1 |
| Valid runs | 1 | 1 | 1 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Planned run count unavailable in supplied root manifest; observed counts above do not establish campaign completion.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 39.41 (n=1) [39.41, 39.41] | 38.97 (n=1) [38.97, 38.97] | 37.45 (n=1) [37.45, 37.45] | 1.12% | 4.97% |
| Path length (m) | 223.19 (n=1) [223.19, 223.19] | 220.81 (n=1) [220.81, 220.81] | 221.18 (n=1) [221.18, 221.18] | 1.07% | 0.90% |
| Minimum static-PC clearance (m) | 0.335 (n=1) [0.335, 0.335] | 0.281 (n=1) [0.281, 0.281] | 0.274 (n=1) [0.274, 0.274] | 16.12% | 18.21% |
| Experiment CPU (cores) | 0.54269 (n=1) [0.54269, 0.54269] | 0.34225 (n=1) [0.34225, 0.34225] | 0.34579 (n=1) [0.34579, 0.34579] | 36.93% | 36.28% |
| Experiment CPU (whole-host %) | 2.7135 (n=1) [2.7135, 2.7135] | 1.7113 (n=1) [1.7113, 1.7113] | 1.729 (n=1) [1.729, 1.729] | 36.93% | 36.28% |
| Experiment measurement-window CPU (core-s) | 22.042 (n=1) [22.042, 22.042] | 13.897 (n=1) [13.897, 13.897] | 13.322 (n=1) [13.322, 13.322] | 36.95% | 39.56% |
| Accounting window (s) | 40.616 (n=1) [40.616, 40.616] | 40.604 (n=1) [40.604, 40.604] | 38.526 (n=1) [38.526, 38.526] | 0.03% | 5.15% |
| Experiment CPU 1 s p95 (cores) | 0.63405 (n=1) [0.63405, 0.63405] | 0.43532 (n=1) [0.43532, 0.43532] | 0.47752 (n=1) [0.47752, 0.47752] | 31.34% | 24.69% |
| Experiment CPU 1 s maximum (cores) | 0.67708 (n=1) [0.67708, 0.67708] | 0.46468 (n=1) [0.46468, 0.46468] | 0.48002 (n=1) [0.48002, 0.48002] | 31.37% | 29.11% |
| Composed runtime CPU (cores; includes simulator) | 0.50326 (n=1) [0.50326, 0.50326] | 0.29844 (n=1) [0.29844, 0.29844] | 0.30099 (n=1) [0.30099, 0.30099] | 40.70% | 40.19% |
| Composed runtime measurement-window CPU (core-s) | 20.441 (n=1) [20.441, 20.441] | 12.118 (n=1) [12.118, 12.118] | 11.596 (n=1) [11.596, 11.596] | 40.72% | 43.27% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.9276 (n=1) [3.9276, 3.9276] | 3.9277 (n=1) [3.9277, 3.9277] | 4.0263 (n=1) [4.0263, 4.0263] | -0.00% | -2.51% |
| Whole-host CPU (%) | 9.6017 (n=1) [9.6017, 9.6017] | 9.0667 (n=1) [9.0667, 9.0667] | 9.0262 (n=1) [9.0262, 9.0262] | 5.57% | 5.99% |
| Baseline whole-host CPU (%) | 7.4989 (n=1) [7.4989, 7.4989] | 6.9097 (n=1) [6.9097, 6.9097] | 7.9896 (n=1) [7.9896, 7.9896] | 7.86% | -6.54% |
| Experiment sampled peak RSS (MiB) | 3383.2 (n=1) [3383.2, 3383.2] | 3378.3 (n=1) [3378.3, 3378.3] | 3380.3 (n=1) [3380.3, 3380.3] | 0.15% | 0.08% |
| Experiment sampled peak PSS (MiB) | 3343.5 (n=1) [3343.5, 3343.5] | 3338.3 (n=1) [3338.3, 3338.3] | 3340.3 (n=1) [3340.3, 3340.3] | 0.15% | 0.09% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5774.8 (n=1) [5774.8, 5774.8] | 5811.2 (n=1) [5811.2, 5811.2] | 5770.5 (n=1) [5770.5, 5770.5] | -0.63% | 0.07% |
| GPU device utilization (%) | 49 (n=1) [49, 49] | 49.22 (n=1) [49.22, 49.22] | 50.763 (n=1) [50.763, 50.763] | -0.45% | -3.60% |
| GPU device utilization p95 (%) | 54 (n=1) [54, 54] | 52 (n=1) [52, 52] | 54 (n=1) [54, 54] | 3.70% | 0.00% |
| GPU device memory-controller utilization (%) | 18.95 (n=1) [18.95, 18.95] | 19 (n=1) [19, 19] | 19.053 (n=1) [19.053, 19.053] | -0.26% | -0.54% |
| GPU device memory (MiB) | 1288.6 (n=1) [1288.6, 1288.6] | 1272.2 (n=1) [1272.2, 1272.2] | 1266.3 (n=1) [1266.3, 1266.3] | 1.27% | 1.73% |
| GPU device power (W; not flight attribution) | 18.665 (n=1) [18.665, 18.665] | 18.723 (n=1) [18.723, 18.723] | 18.73 (n=1) [18.73, 18.73] | -0.31% | -0.35% |
| Observed source frame records | 406 (n=1) [406, 406] | 406 (n=1) [406, 406] | 382 (n=1) [382, 382] | 0.00% | 5.91% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 246.2 (n=1) [246.2, 246.2] | 75.00% | 72.64% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1912e+05 (n=1) [2.1912e+05, 2.1912e+05] | 75.00% | 72.64% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31514 (n=1) [31514, 31514] | 75.00% | 72.64% |
| Observed source generated points (/frame) | 16417 (n=1) [16417, 16417] | 4318.4 (n=1) [4318.4, 4318.4] | 4631.9 (n=1) [4631.9, 4631.9] | 73.70% | 71.79% |
| Observed source cloud payload (bytes/frame) | 5.2536e+05 (n=1) [5.2536e+05, 5.2536e+05] | 1.3819e+05 (n=1) [1.3819e+05, 1.3819e+05] | 1.4822e+05 (n=1) [1.4822e+05, 1.4822e+05] | 73.70% | 71.79% |
| Map total elapsed mean (ms/frame) | 25.77 (n=1) [25.77, 25.77] | 9.264 (n=1) [9.264, 9.264] | 10.44 (n=1) [10.44, 10.44] | 64.05% | 59.49% |
| Map total elapsed p95 (ms/frame) | 34.047 (n=1) [34.047, 34.047] | 13.78 (n=1) [13.78, 13.78] | 16.08 (n=1) [16.08, 16.08] | 59.53% | 52.77% |
| Map total elapsed max (ms/frame) | 92.024 (n=1) [92.024, 92.024] | 17.177 (n=1) [17.177, 17.177] | 37.02 (n=1) [37.02, 37.02] | 81.33% | 59.77% |
| Map raycast elapsed mean (ms/frame) | 15.903 (n=1) [15.903, 15.903] | 6.1272 (n=1) [6.1272, 6.1272] | 6.8458 (n=1) [6.8458, 6.8458] | 61.47% | 56.95% |
| Map update elapsed mean (ms/frame) | 9.8653 (n=1) [9.8653, 9.8653] | 3.1354 (n=1) [3.1354, 3.1354] | 3.593 (n=1) [3.593, 3.593] | 68.22% | 63.58% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2811 (n=1) [1.2811, 1.2811] | 0.63096 (n=1) [0.63096, 0.63096] | 0.72095 (n=1) [0.72095, 0.72095] | 50.75% | 43.72% |
| Map processed frames / mission time (Hz proxy) | 10.277 (n=1) [10.277, 10.277] | 10.418 (n=1) [10.418, 10.418] | 10.2 (n=1) [10.2, 10.2] | -1.38% | 0.74% |
| Trajectory commits (Hz) | 3.3613 (n=1) [3.3613, 3.3613] | 3.1226 (n=1) [3.1226, 3.1226] | 3.06 (n=1) [3.06, 3.06] | 7.10% | 8.97% |
| Goal retransmissions coalesced | 30 (n=1) [30, 30] | 25 (n=1) [25, 25] | 31 (n=1) [31, 31] | 16.67% | -3.33% |
| Demand replan checks (latest cumulative report) | 576 (n=1) [576, 576] | 582 (n=1) [582, 582] | 512 (n=1) [512, 512] | -1.04% | 11.11% |
| Demand replans skipped (latest cumulative report) | 418 (n=1) [418, 418] | 419 (n=1) [419, 419] | 373 (n=1) [373, 373] | -0.24% | 10.77% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.02041 (n=1) [0.02041, 0.02041] | 0.057324 (n=1) [0.057324, 0.057324] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.144 (n=1) [0.144, 0.144] | 0.925 (n=1) [0.925, 0.925] | N/A | N/A |
| Map points mean (/frame) | 16432 (n=1) [16432, 16432] | 4318.4 (n=1) [4318.4, 4318.4] | 4631.9 (n=1) [4631.9, 4631.9] | 73.72% | 71.81% |
| Map points / mission time (points/s proxy) | 1.6886e+05 (n=1) [1.6886e+05, 1.6886e+05] | 44991 (n=1) [44991, 44991] | 47247 (n=1) [47247, 47247] | 73.36% | 72.02% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.1533 (n=1) [5.1533, 5.1533] | 1.373 (n=1) [1.373, 1.373] | 1.4419 (n=1) [1.4419, 1.4419] | 73.36% | 72.02% |
| Sensor report payload (MiB/s, logical edge; own span) | 5.045 (n=1) [5.045, 5.045] | 1.3331 (n=1) [1.3331, 1.3331] | 1.4449 (n=1) [1.4449, 1.4449] | 73.58% | 71.36% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.1533 (n=1) [5.1533, 5.1533] | 1.373 (n=1) [1.373, 1.373] | 1.4419 (n=1) [1.4419, 1.4419] | 73.36% | 72.02% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 9.9999 (n=1) [9.9999, 9.9999] | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | -0.01% | -0.01% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 95.705 (n=1) [95.705, 95.705] | 95.522 (n=1) [95.522, 95.522] | 95.763 (n=1) [95.763, 95.763] | 0.19% | -0.06% |
| Odometry receipt p99 gap (ms) | 10.613 (n=1) [10.613, 10.613] | 10.848 (n=1) [10.848, 10.848] | 10.919 (n=1) [10.919, 10.919] | -2.22% | -2.89% |
| Odometry receipt max gap (ms) | 22.996 (n=1) [22.996, 22.996] | 11.342 (n=1) [11.342, 11.342] | 11.883 (n=1) [11.883, 11.883] | 50.68% | 48.32% |
| Actual FSM main callback frequency (profiled only) | 99.969 (n=1) [99.969, 99.969] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | -0.03% | -0.03% |
| Actual FSM command callback frequency (profiled only) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | -0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.209 (n=1) [3.209, 3.209] | N/A | N/A |
| Guard active duration (s) | 1.8484 (n=1) [1.8484, 1.8484] | 1.2769 (n=1) [1.2769, 1.2769] | 1.2369 (n=1) [1.2369, 1.2369] | 30.92% | 33.08% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c19_cpu_attribution_20260916/profile_preflight_run9500/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 2.87474e-05 | 3.63952e-05 |
| frontend_cloud / 0 | N/A | 0.000123845 | 0.000131698 |
| frontend_enqueue / 0 | N/A | 4.71731e-05 | 6.00939e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.82317e-05 |
| frontend_odom / 0 | N/A | 0.000463963 | 0.000615454 |
| frontend_replan_status / 0 | N/A | N/A | 6.9949e-06 |
| frontend_report / 0 | N/A | 1.49641e-05 | 1.07582e-05 |
| frontend_stats / 0 | N/A | 0.000858234 | 0.000975534 |
| fsm_command_callback / 0 | 0.00915827 | 0.00840081 | 0.0103903 |
| fsm_main_callback / 0 | 0.000528431 | 0.00059491 | 0.000641996 |
| fsm_main_core / 0 | 0.000351813 | 0.000367664 | 0.000392683 |
| fsm_poly_publish / 0 | 2.44783e-05 | 2.28539e-05 | 2.47413e-05 |
| fsm_replan_callback / 0 | 0.000247695 | 0.000281159 | 0.000325907 |
| fsm_replan_core / 0 | 0.000155927 | 0.000165343 | 0.00017821 |
| guard_brake / 0 | 1.05815e-05 | 0 | 0 |
| guard_certificate / 0 | 0.00106098 | 0.00112087 | 0.00131702 |
| guard_recover / 0 | 1.56197e-05 | 0 | 0 |
| map_ack_and_log / 0 | 0.000756175 | 0.00121754 | 0.00134092 |
| map_cloud_enqueue / 0 | 5.90145e-05 | 7.70473e-05 | 7.56473e-05 |
| map_odom_callback / 0 | 0.000940081 | 0.000927195 | 0.000800724 |
| map_prob_update / 0 | 0.242786 | 0.0923833 | 0.0975139 |
| map_ros_to_pcl / 0 | 0.00413783 | 0.000903579 | 0.000927093 |
| map_snapshot_commit_health / 0 | 0.0480898 | 0.0202279 | 0.0205306 |
| map_worker / 0 | 7.58274e-05 | 6.4738e-05 | 6.67413e-05 |
| planner_backup_optimize / 0 | 0.0168517 | 0.015222 | 0.0105736 |
| planner_commit / 0 | 0.00026889 | 0.000251114 | 0.000264147 |
| planner_corridor_search / 0 | 0.00517394 | 0.00564077 | 0.00523138 |
| planner_exp_optimize / 0 | 0.033714 | 0.030204 | 0.0321566 |
| planner_generate_backup / 0 | 0.0105632 | 0.00961912 | 0.00910117 |
| planner_generate_exp / 0 | 0.000241219 | 0.000298738 | 0.000256166 |
| planner_path_search / 0 | 0.00880953 | 0.0138494 | 0.0117957 |
| planner_stop_viability / 0 | 0.00033098 | 0.000367027 | 0.000391066 |
| planner_validate_geometry / 0 | 0.00354303 | 0.00395698 | 0.00401406 |
| planner_velocity_extrema / 0 | 6.57082e-05 | 6.17004e-05 | 5.97287e-05 |
| planner_visualize_path / 0 | 0.000576664 | 0.000569224 | 0.000690738 |
| sim_odom_callback / 0 | 0.00830601 | 0.0114029 | 0.0104745 |
| sim_render_callback / 0 | 0.0446186 | 0.015054 | 0.0190555 |

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
