# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c22_iteration03_preflight — profiled_supplement

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
| Mission time (s) | 38.82 (n=1) [38.82, 38.82] | 38.8 (n=1) [38.8, 38.8] | 39.24 (n=1) [39.24, 39.24] | 0.05% | -1.08% |
| Path length (m) | 225.13 (n=1) [225.13, 225.13] | 223.44 (n=1) [223.44, 223.44] | 223.7 (n=1) [223.7, 223.7] | 0.75% | 0.63% |
| Minimum static-PC clearance (m) | 0.368 (n=1) [0.368, 0.368] | 0.318 (n=1) [0.318, 0.318] | 0.309 (n=1) [0.309, 0.309] | 13.59% | 16.03% |
| Experiment CPU (cores) | 0.60076 (n=1) [0.60076, 0.60076] | 0.39883 (n=1) [0.39883, 0.39883] | 0.40553 (n=1) [0.40553, 0.40553] | 33.61% | 32.50% |
| Experiment CPU (whole-host %) | 3.0038 (n=1) [3.0038, 3.0038] | 1.9942 (n=1) [1.9942, 1.9942] | 2.0276 (n=1) [2.0276, 2.0276] | 33.61% | 32.50% |
| Experiment measurement-window CPU (core-s) | 24.138 (n=1) [24.138, 24.138] | 16.022 (n=1) [16.022, 16.022] | 16.321 (n=1) [16.321, 16.321] | 33.63% | 32.38% |
| Accounting window (s) | 40.179 (n=1) [40.179, 40.179] | 40.171 (n=1) [40.171, 40.171] | 40.247 (n=1) [40.247, 40.247] | 0.02% | -0.17% |
| Experiment CPU 1 s p95 (cores) | 0.67697 (n=1) [0.67697, 0.67697] | 0.47396 (n=1) [0.47396, 0.47396] | 0.48516 (n=1) [0.48516, 0.48516] | 29.99% | 28.33% |
| Experiment CPU 1 s maximum (cores) | 0.76795 (n=1) [0.76795, 0.76795] | 0.51379 (n=1) [0.51379, 0.51379] | 0.49086 (n=1) [0.49086, 0.49086] | 33.10% | 36.08% |
| Composed runtime CPU (cores; includes simulator) | 0.55898 (n=1) [0.55898, 0.55898] | 0.35254 (n=1) [0.35254, 0.35254] | 0.35797 (n=1) [0.35797, 0.35797] | 36.93% | 35.96% |
| Composed runtime measurement-window CPU (core-s) | 22.459 (n=1) [22.459, 22.459] | 14.162 (n=1) [14.162, 14.162] | 14.407 (n=1) [14.407, 14.407] | 36.94% | 35.85% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 2.934 (n=1) [2.934, 2.934] | 2.9816 (n=1) [2.9816, 2.9816] | 3.1806 (n=1) [3.1806, 3.1806] | -1.62% | -8.41% |
| Whole-host CPU (%) | 9.7405 (n=1) [9.7405, 9.7405] | 9.3886 (n=1) [9.3886, 9.3886] | 9.5695 (n=1) [9.5695, 9.5695] | 3.61% | 1.76% |
| Baseline whole-host CPU (%) | 7.9712 (n=1) [7.9712, 7.9712] | 7.6314 (n=1) [7.6314, 7.6314] | 7.5808 (n=1) [7.5808, 7.5808] | 4.26% | 4.90% |
| Experiment sampled peak RSS (MiB) | 3390.5 (n=1) [3390.5, 3390.5] | 3379.5 (n=1) [3379.5, 3379.5] | 3379.2 (n=1) [3379.2, 3379.2] | 0.32% | 0.33% |
| Experiment sampled peak PSS (MiB) | 3350.3 (n=1) [3350.3, 3350.3] | 3339.1 (n=1) [3339.1, 3339.1] | 3338.8 (n=1) [3338.8, 3338.8] | 0.33% | 0.34% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5679.1 (n=1) [5679.1, 5679.1] | 5720.9 (n=1) [5720.9, 5720.9] | 5717.1 (n=1) [5717.1, 5717.1] | -0.74% | -0.67% |
| GPU device utilization (%) | 46.55 (n=1) [46.55, 46.55] | 53.8 (n=1) [53.8, 53.8] | 50.075 (n=1) [50.075, 50.075] | -15.57% | -7.57% |
| GPU device utilization p95 (%) | 49 (n=1) [49, 49] | 58 (n=1) [58, 58] | 54 (n=1) [54, 54] | -18.37% | -10.20% |
| GPU device memory-controller utilization (%) | 19.05 (n=1) [19.05, 19.05] | 18.95 (n=1) [18.95, 18.95] | 19 (n=1) [19, 19] | 0.52% | 0.26% |
| GPU device memory (MiB) | 1274.4 (n=1) [1274.4, 1274.4] | 1275.2 (n=1) [1275.2, 1275.2] | 1274.8 (n=1) [1274.8, 1274.8] | -0.06% | -0.03% |
| GPU device power (W; not flight attribution) | 18.697 (n=1) [18.697, 18.697] | 18.698 (n=1) [18.698, 18.698] | 18.724 (n=1) [18.724, 18.724] | -0.01% | -0.15% |
| Observed source frame records | 400 (n=1) [400, 400] | 401 (n=1) [401, 401] | 402 (n=1) [402, 402] | -0.25% | -0.50% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 246.83 (n=1) [246.83, 246.83] | 75.00% | 72.57% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1968e+05 (n=1) [2.1968e+05, 2.1968e+05] | 75.00% | 72.57% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31594 (n=1) [31594, 31594] | 75.00% | 72.57% |
| Observed source generated points (/frame) | 16108 (n=1) [16108, 16108] | 4583.9 (n=1) [4583.9, 4583.9] | 4622.7 (n=1) [4622.7, 4622.7] | 71.54% | 71.30% |
| Observed source cloud payload (bytes/frame) | 5.1547e+05 (n=1) [5.1547e+05, 5.1547e+05] | 1.4669e+05 (n=1) [1.4669e+05, 1.4669e+05] | 1.4793e+05 (n=1) [1.4793e+05, 1.4793e+05] | 71.54% | 71.30% |
| Map total elapsed mean (ms/frame) | 26.661 (n=1) [26.661, 26.661] | 9.8219 (n=1) [9.8219, 9.8219] | 10.06 (n=1) [10.06, 10.06] | 63.16% | 62.27% |
| Map total elapsed p95 (ms/frame) | 33.319 (n=1) [33.319, 33.319] | 15.169 (n=1) [15.169, 15.169] | 16.348 (n=1) [16.348, 16.348] | 54.47% | 50.93% |
| Map total elapsed max (ms/frame) | 51.262 (n=1) [51.262, 51.262] | 26.282 (n=1) [26.282, 26.282] | 37.233 (n=1) [37.233, 37.233] | 48.73% | 27.37% |
| Map raycast elapsed mean (ms/frame) | 16.367 (n=1) [16.367, 16.367] | 6.5364 (n=1) [6.5364, 6.5364] | 6.5119 (n=1) [6.5119, 6.5119] | 60.06% | 60.21% |
| Map update elapsed mean (ms/frame) | 10.293 (n=1) [10.293, 10.293] | 3.284 (n=1) [3.284, 3.284] | 3.5463 (n=1) [3.5463, 3.5463] | 68.09% | 65.55% |
| Map inflation elapsed mean (ms/frame; nested) | 1.3307 (n=1) [1.3307, 1.3307] | 0.67227 (n=1) [0.67227, 0.67227] | 0.69496 (n=1) [0.69496, 0.69496] | 49.48% | 47.78% |
| Map processed frames / mission time (Hz proxy) | 10.304 (n=1) [10.304, 10.304] | 10.335 (n=1) [10.335, 10.335] | 10.219 (n=1) [10.219, 10.219] | -0.30% | 0.82% |
| Trajectory commits (Hz) | 5.1273 (n=1) [5.1273, 5.1273] | 5.515 (n=1) [5.515, 5.515] | 5.3179 (n=1) [5.3179, 5.3179] | -7.56% | -3.72% |
| Goal retransmissions coalesced | 35 (n=1) [35, 35] | 33 (n=1) [33, 33] | 30 (n=1) [30, 30] | 5.71% | 14.29% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.022301 (n=1) [0.022301, 0.022301] | 0.019853 (n=1) [0.019853, 0.019853] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.239 (n=1) [0.239, 0.239] | 0.118 (n=1) [0.118, 0.118] | N/A | N/A |
| Map points mean (/frame) | 16108 (n=1) [16108, 16108] | 4583.9 (n=1) [4583.9, 4583.9] | 4630.3 (n=1) [4630.3, 4630.3] | 71.54% | 71.26% |
| Map points / mission time (points/s proxy) | 1.6598e+05 (n=1) [1.6598e+05, 1.6598e+05] | 47375 (n=1) [47375, 47375] | 47318 (n=1) [47318, 47318] | 71.46% | 71.49% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.0653 (n=1) [5.0653, 5.0653] | 1.4458 (n=1) [1.4458, 1.4458] | 1.444 (n=1) [1.444, 1.444] | 71.46% | 71.49% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.9282 (n=1) [4.9282, 4.9282] | 1.4044 (n=1) [1.4044, 1.4044] | 1.4192 (n=1) [1.4192, 1.4192] | 71.50% | 71.20% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.0653 (n=1) [5.0653, 5.0653] | 1.4458 (n=1) [1.4458, 1.4458] | 1.444 (n=1) [1.444, 1.444] | 71.46% | 71.49% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 10.001 (n=1) [10.001, 10.001] | -0.00% | -0.01% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.708 (n=1) [94.708, 94.708] | 93.371 (n=1) [93.371, 93.371] | 95.362 (n=1) [95.362, 95.362] | 1.41% | -0.69% |
| Odometry receipt p99 gap (ms) | 10.651 (n=1) [10.651, 10.651] | 10.772 (n=1) [10.772, 10.772] | 10.786 (n=1) [10.786, 10.786] | -1.14% | -1.27% |
| Odometry receipt max gap (ms) | 11.731 (n=1) [11.731, 11.731] | 11.751 (n=1) [11.751, 11.751] | 11.894 (n=1) [11.894, 11.894] | -0.17% | -1.39% |
| Actual FSM main callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | -0.00% | 0.00% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | -0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.291 (n=1) [3.291, 3.291] | N/A | N/A |
| Guard active duration (s) | 1.1498 (n=1) [1.1498, 1.1498] | 0.36016 (n=1) [0.36016, 0.36016] | 1.2827 (n=1) [1.2827, 1.2827] | 68.68% | -11.56% |

## seed3 — c22_iteration03_preflight — profiled_supplement

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
| Mission time (s) | 39.68 (n=1) [39.68, 39.68] | 40.66 (n=1) [40.66, 40.66] | 40.98 (n=1) [40.98, 40.98] | -2.47% | -3.28% |
| Path length (m) | 225.05 (n=1) [225.05, 225.05] | 224.42 (n=1) [224.42, 224.42] | 225.31 (n=1) [225.31, 225.31] | 0.28% | -0.12% |
| Minimum static-PC clearance (m) | 0.281 (n=1) [0.281, 0.281] | 0.303 (n=1) [0.303, 0.303] | 0.278 (n=1) [0.278, 0.278] | -7.83% | 1.07% |
| Experiment CPU (cores) | 0.66443 (n=1) [0.66443, 0.66443] | 0.40042 (n=1) [0.40042, 0.40042] | 0.43941 (n=1) [0.43941, 0.43941] | 39.73% | 33.87% |
| Experiment CPU (whole-host %) | 3.3221 (n=1) [3.3221, 3.3221] | 2.0021 (n=1) [2.0021, 2.0021] | 2.197 (n=1) [2.197, 2.197] | 39.73% | 33.87% |
| Experiment measurement-window CPU (core-s) | 27.477 (n=1) [27.477, 27.477] | 16.987 (n=1) [16.987, 16.987] | 18.584 (n=1) [18.584, 18.584] | 38.18% | 32.37% |
| Accounting window (s) | 41.355 (n=1) [41.355, 41.355] | 42.423 (n=1) [42.423, 42.423] | 42.293 (n=1) [42.293, 42.293] | -2.58% | -2.27% |
| Experiment CPU 1 s p95 (cores) | 0.81545 (n=1) [0.81545, 0.81545] | 0.52907 (n=1) [0.52907, 0.52907] | 0.51971 (n=1) [0.51971, 0.51971] | 35.12% | 36.27% |
| Experiment CPU 1 s maximum (cores) | 1.2411 (n=1) [1.2411, 1.2411] | 0.63533 (n=1) [0.63533, 0.63533] | 0.83097 (n=1) [0.83097, 0.83097] | 48.81% | 33.05% |
| Composed runtime CPU (cores; includes simulator) | 0.62354 (n=1) [0.62354, 0.62354] | 0.35626 (n=1) [0.35626, 0.35626] | 0.39292 (n=1) [0.39292, 0.39292] | 42.86% | 36.98% |
| Composed runtime measurement-window CPU (core-s) | 25.786 (n=1) [25.786, 25.786] | 15.114 (n=1) [15.114, 15.114] | 16.618 (n=1) [16.618, 16.618] | 41.39% | 35.55% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.1771 (n=1) [3.1771, 3.1771] | 3.384 (n=1) [3.384, 3.384] | 3.1226 (n=1) [3.1226, 3.1226] | -6.51% | 1.72% |
| Whole-host CPU (%) | 10.039 (n=1) [10.039, 10.039] | 9.2818 (n=1) [9.2818, 9.2818] | 9.4653 (n=1) [9.4653, 9.4653] | 7.54% | 5.71% |
| Baseline whole-host CPU (%) | 5.9755 (n=1) [5.9755, 5.9755] | 7.5858 (n=1) [7.5858, 7.5858] | 6.7963 (n=1) [6.7963, 6.7963] | -26.95% | -13.74% |
| Experiment sampled peak RSS (MiB) | 3433.5 (n=1) [3433.5, 3433.5] | 3423.2 (n=1) [3423.2, 3423.2] | 3432.5 (n=1) [3432.5, 3432.5] | 0.30% | 0.03% |
| Experiment sampled peak PSS (MiB) | 3393.2 (n=1) [3393.2, 3393.2] | 3383 (n=1) [3383, 3383] | 3392.3 (n=1) [3392.3, 3392.3] | 0.30% | 0.03% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5645.6 (n=1) [5645.6, 5645.6] | 5637.1 (n=1) [5637.1, 5637.1] | 5604.8 (n=1) [5604.8, 5604.8] | 0.15% | 0.72% |
| GPU device utilization (%) | 45.073 (n=1) [45.073, 45.073] | 54.31 (n=1) [54.31, 54.31] | 55.119 (n=1) [55.119, 55.119] | -20.49% | -22.29% |
| GPU device utilization p95 (%) | 50 (n=1) [50, 50] | 59 (n=1) [59, 59] | 58 (n=1) [58, 58] | -18.00% | -16.00% |
| GPU device memory-controller utilization (%) | 19.049 (n=1) [19.049, 19.049] | 19 (n=1) [19, 19] | 19 (n=1) [19, 19] | 0.26% | 0.26% |
| GPU device memory (MiB) | 1278 (n=1) [1278, 1278] | 1277.9 (n=1) [1277.9, 1277.9] | 1278.6 (n=1) [1278.6, 1278.6] | 0.00% | -0.05% |
| GPU device power (W; not flight attribution) | 18.663 (n=1) [18.663, 18.663] | 18.808 (n=1) [18.808, 18.808] | 18.736 (n=1) [18.736, 18.736] | -0.78% | -0.39% |
| Observed source frame records | 412 (n=1) [412, 412] | 423 (n=1) [423, 423] | 421 (n=1) [421, 421] | -2.67% | -2.18% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 252.26 (n=1) [252.26, 252.26] | 75.00% | 71.97% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.2451e+05 (n=1) [2.2451e+05, 2.2451e+05] | 75.00% | 71.97% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 32289 (n=1) [32289, 32289] | 75.00% | 71.97% |
| Observed source generated points (/frame) | 22797 (n=1) [22797, 22797] | 6753.8 (n=1) [6753.8, 6753.8] | 6517 (n=1) [6517, 6517] | 70.37% | 71.41% |
| Observed source cloud payload (bytes/frame) | 7.2951e+05 (n=1) [7.2951e+05, 7.2951e+05] | 2.1612e+05 (n=1) [2.1612e+05, 2.1612e+05] | 2.0854e+05 (n=1) [2.0854e+05, 2.0854e+05] | 70.37% | 71.41% |
| Map total elapsed mean (ms/frame) | 30.813 (n=1) [30.813, 30.813] | 10.904 (n=1) [10.904, 10.904] | 11.733 (n=1) [11.733, 11.733] | 64.61% | 61.92% |
| Map total elapsed p95 (ms/frame) | 39.736 (n=1) [39.736, 39.736] | 16.802 (n=1) [16.802, 16.802] | 19.878 (n=1) [19.878, 19.878] | 57.72% | 49.97% |
| Map total elapsed max (ms/frame) | 101.13 (n=1) [101.13, 101.13] | 24.957 (n=1) [24.957, 24.957] | 32.88 (n=1) [32.88, 32.88] | 75.32% | 67.49% |
| Map raycast elapsed mean (ms/frame) | 19.003 (n=1) [19.003, 19.003] | 7.3027 (n=1) [7.3027, 7.3027] | 7.8898 (n=1) [7.8898, 7.8898] | 61.57% | 58.48% |
| Map update elapsed mean (ms/frame) | 11.808 (n=1) [11.808, 11.808] | 3.5994 (n=1) [3.5994, 3.5994] | 3.8421 (n=1) [3.8421, 3.8421] | 69.52% | 67.46% |
| Map inflation elapsed mean (ms/frame; nested) | 1.7494 (n=1) [1.7494, 1.7494] | 0.8156 (n=1) [0.8156, 0.8156] | 0.8146 (n=1) [0.8146, 0.8146] | 53.38% | 53.43% |
| Map processed frames / mission time (Hz proxy) | 10.358 (n=1) [10.358, 10.358] | 10.403 (n=1) [10.403, 10.403] | 10.273 (n=1) [10.273, 10.273] | -0.44% | 0.82% |
| Trajectory commits (Hz) | 5.2437 (n=1) [5.2437, 5.2437] | 5.0654 (n=1) [5.0654, 5.0654] | 5.2166 (n=1) [5.2166, 5.2166] | 3.40% | 0.52% |
| Goal retransmissions coalesced | 35 (n=1) [35, 35] | 34 (n=1) [34, 34] | 33 (n=1) [33, 33] | 2.86% | 5.71% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.022447 (n=1) [0.022447, 0.022447] | 0.021785 (n=1) [0.021785, 0.021785] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.132 (n=1) [0.132, 0.132] | 0.224 (n=1) [0.224, 0.224] | N/A | N/A |
| Map points mean (/frame) | 22819 (n=1) [22819, 22819] | 6753.8 (n=1) [6753.8, 6753.8] | 6517 (n=1) [6517, 6517] | 70.40% | 71.44% |
| Map points / mission time (points/s proxy) | 2.3635e+05 (n=1) [2.3635e+05, 2.3635e+05] | 70262 (n=1) [70262, 70262] | 66951 (n=1) [66951, 66951] | 70.27% | 71.67% |
| Map payload / mission time (MiB/s proxy, logical edge) | 7.213 (n=1) [7.213, 7.213] | 2.1442 (n=1) [2.1442, 2.1442] | 2.0432 (n=1) [2.0432, 2.0432] | 70.27% | 71.67% |
| Sensor report payload (MiB/s, logical edge; own span) | 7.0004 (n=1) [7.0004, 7.0004] | 2.0929 (n=1) [2.0929, 2.0929] | 2.0249 (n=1) [2.0249, 2.0249] | 70.10% | 71.07% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 7.213 (n=1) [7.213, 7.213] | 2.1442 (n=1) [2.1442, 2.1442] | 2.0432 (n=1) [2.0432, 2.0432] | 70.27% | 71.67% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10.002 (n=1) [10.002, 10.002] | 10.002 (n=1) [10.002, 10.002] | -0.01% | -0.01% |
| Received odometry frequency (Hz) | 100.01 (n=1) [100.01, 100.01] | 100.02 (n=1) [100.02, 100.02] | 100.01 (n=1) [100.01, 100.01] | -0.01% | -0.01% |
| Received command frequency (Hz; holds included) | 94.154 (n=1) [94.154, 94.154] | 93.967 (n=1) [93.967, 93.967] | 95.192 (n=1) [95.192, 95.192] | 0.20% | -1.10% |
| Odometry receipt p99 gap (ms) | 10.706 (n=1) [10.706, 10.706] | 10.875 (n=1) [10.875, 10.875] | 10.818 (n=1) [10.818, 10.818] | -1.58% | -1.05% |
| Odometry receipt max gap (ms) | 14.114 (n=1) [14.114, 14.114] | 13.477 (n=1) [13.477, 13.477] | 11.629 (n=1) [11.629, 11.629] | 4.52% | 17.61% |
| Actual FSM main callback frequency (profiled only) | 99.748 (n=1) [99.748, 99.748] | 99.897 (n=1) [99.897, 99.897] | 99.955 (n=1) [99.955, 99.955] | -0.15% | -0.21% |
| Actual FSM command callback frequency (profiled only) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | -0.01% | -0.01% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 4.106 (n=1) [4.106, 4.106] | N/A | N/A |
| Guard active duration (s) | 0.94412 (n=1) [0.94412, 0.94412] | 2.4779 (n=1) [2.4779, 2.4779] | 1.7373 (n=1) [1.7373, 1.7373] | -162.46% | -84.01% |

## seed5 — c22_iteration03_preflight — profiled_supplement

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
| Mission time (s) | 42.19 (n=1) [42.19, 42.19] | 40.85 (n=1) [40.85, 40.85] | 41.95 (n=1) [41.95, 41.95] | 3.18% | 0.57% |
| Path length (m) | 227.08 (n=1) [227.08, 227.08] | 226.27 (n=1) [226.27, 226.27] | 226.66 (n=1) [226.66, 226.66] | 0.36% | 0.18% |
| Minimum static-PC clearance (m) | 0.279 (n=1) [0.279, 0.279] | 0.273 (n=1) [0.273, 0.273] | 0.348 (n=1) [0.348, 0.348] | 2.15% | -24.73% |
| Experiment CPU (cores) | 0.69982 (n=1) [0.69982, 0.69982] | 0.43272 (n=1) [0.43272, 0.43272] | 0.44374 (n=1) [0.44374, 0.44374] | 38.17% | 36.59% |
| Experiment CPU (whole-host %) | 3.4991 (n=1) [3.4991, 3.4991] | 2.1636 (n=1) [2.1636, 2.1636] | 2.2187 (n=1) [2.2187, 2.2187] | 38.17% | 36.59% |
| Experiment measurement-window CPU (core-s) | 30.397 (n=1) [30.397, 30.397] | 18.346 (n=1) [18.346, 18.346] | 19.291 (n=1) [19.291, 19.291] | 39.65% | 36.54% |
| Accounting window (s) | 43.436 (n=1) [43.436, 43.436] | 42.397 (n=1) [42.397, 42.397] | 43.473 (n=1) [43.473, 43.473] | 2.39% | -0.09% |
| Experiment CPU 1 s p95 (cores) | 0.80162 (n=1) [0.80162, 0.80162] | 0.56197 (n=1) [0.56197, 0.56197] | 0.55854 (n=1) [0.55854, 0.55854] | 29.90% | 30.32% |
| Experiment CPU 1 s maximum (cores) | 0.87622 (n=1) [0.87622, 0.87622] | 0.58665 (n=1) [0.58665, 0.58665] | 0.7659 (n=1) [0.7659, 0.7659] | 33.05% | 12.59% |
| Composed runtime CPU (cores; includes simulator) | 0.65801 (n=1) [0.65801, 0.65801] | 0.39386 (n=1) [0.39386, 0.39386] | 0.40275 (n=1) [0.40275, 0.40275] | 40.14% | 38.79% |
| Composed runtime measurement-window CPU (core-s) | 28.581 (n=1) [28.581, 28.581] | 16.698 (n=1) [16.698, 16.698] | 17.509 (n=1) [17.509, 17.509] | 41.58% | 38.74% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.3299 (n=1) [3.3299, 3.3299] | 3.3135 (n=1) [3.3135, 3.3135] | 3.3993 (n=1) [3.3993, 3.3993] | 0.49% | -2.08% |
| Whole-host CPU (%) | 10.064 (n=1) [10.064, 10.064] | 9.6931 (n=1) [9.6931, 9.6931] | 8.8925 (n=1) [8.8925, 8.8925] | 3.69% | 11.64% |
| Baseline whole-host CPU (%) | 6.5011 (n=1) [6.5011, 6.5011] | 6.9628 (n=1) [6.9628, 6.9628] | 8.6835 (n=1) [8.6835, 8.6835] | -7.10% | -33.57% |
| Experiment sampled peak RSS (MiB) | 3478.4 (n=1) [3478.4, 3478.4] | 3471 (n=1) [3471, 3471] | 3474.6 (n=1) [3474.6, 3474.6] | 0.21% | 0.11% |
| Experiment sampled peak PSS (MiB) | 3438.2 (n=1) [3438.2, 3438.2] | 3430.8 (n=1) [3430.8, 3430.8] | 3434.4 (n=1) [3434.4, 3434.4] | 0.22% | 0.11% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5552.4 (n=1) [5552.4, 5552.4] | 5548.1 (n=1) [5548.1, 5548.1] | 5564.8 (n=1) [5564.8, 5564.8] | 0.08% | -0.22% |
| GPU device utilization (%) | 54.465 (n=1) [54.465, 54.465] | 46.619 (n=1) [46.619, 46.619] | 50.488 (n=1) [50.488, 50.488] | 14.41% | 7.30% |
| GPU device utilization p95 (%) | 59 (n=1) [59, 59] | 52 (n=1) [52, 52] | 56 (n=1) [56, 56] | 11.86% | 5.08% |
| GPU device memory-controller utilization (%) | 19 (n=1) [19, 19] | 19.119 (n=1) [19.119, 19.119] | 19.07 (n=1) [19.07, 19.07] | -0.63% | -0.37% |
| GPU device memory (MiB) | 1272.5 (n=1) [1272.5, 1272.5] | 1279.8 (n=1) [1279.8, 1279.8] | 1271.7 (n=1) [1271.7, 1271.7] | -0.57% | 0.06% |
| GPU device power (W; not flight attribution) | 18.775 (n=1) [18.775, 18.775] | 18.791 (n=1) [18.791, 18.791] | 18.789 (n=1) [18.789, 18.789] | -0.08% | -0.07% |
| Observed source frame records | 432 (n=1) [432, 432] | 420 (n=1) [420, 420] | 430 (n=1) [430, 430] | 2.78% | 0.46% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 257.97 (n=1) [257.97, 257.97] | 75.00% | 71.34% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.2959e+05 (n=1) [2.2959e+05, 2.2959e+05] | 75.00% | 71.34% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 33020 (n=1) [33020, 33020] | 75.00% | 71.34% |
| Observed source generated points (/frame) | 28337 (n=1) [28337, 28337] | 7559.2 (n=1) [7559.2, 7559.2] | 8548.6 (n=1) [8548.6, 8548.6] | 73.32% | 69.83% |
| Observed source cloud payload (bytes/frame) | 9.0679e+05 (n=1) [9.0679e+05, 9.0679e+05] | 2.4189e+05 (n=1) [2.4189e+05, 2.4189e+05] | 2.7356e+05 (n=1) [2.7356e+05, 2.7356e+05] | 73.32% | 69.83% |
| Map total elapsed mean (ms/frame) | 33.778 (n=1) [33.778, 33.778] | 11.861 (n=1) [11.861, 11.861] | 11.917 (n=1) [11.917, 11.917] | 64.89% | 64.72% |
| Map total elapsed p95 (ms/frame) | 42.742 (n=1) [42.742, 42.742] | 17.301 (n=1) [17.301, 17.301] | 19.282 (n=1) [19.282, 19.282] | 59.52% | 54.89% |
| Map total elapsed max (ms/frame) | 68.404 (n=1) [68.404, 68.404] | 42.831 (n=1) [42.831, 42.831] | 47.801 (n=1) [47.801, 47.801] | 37.39% | 30.12% |
| Map raycast elapsed mean (ms/frame) | 21.195 (n=1) [21.195, 21.195] | 7.849 (n=1) [7.849, 7.849] | 7.8279 (n=1) [7.8279, 7.8279] | 62.97% | 63.07% |
| Map update elapsed mean (ms/frame) | 12.581 (n=1) [12.581, 12.581] | 4.0101 (n=1) [4.0101, 4.0101] | 4.0875 (n=1) [4.0875, 4.0875] | 68.13% | 67.51% |
| Map inflation elapsed mean (ms/frame; nested) | 2.0194 (n=1) [2.0194, 2.0194] | 0.96328 (n=1) [0.96328, 0.96328] | 0.93022 (n=1) [0.93022, 0.93022] | 52.30% | 53.93% |
| Map processed frames / mission time (Hz proxy) | 10.216 (n=1) [10.216, 10.216] | 10.282 (n=1) [10.282, 10.282] | 10.25 (n=1) [10.25, 10.25] | -0.64% | -0.34% |
| Trajectory commits (Hz) | 5.1217 (n=1) [5.1217, 5.1217] | 5.2183 (n=1) [5.2183, 5.2183] | 5.0822 (n=1) [5.0822, 5.0822] | -1.89% | 0.77% |
| Goal retransmissions coalesced | 31 (n=1) [31, 31] | 30 (n=1) [30, 30] | 34 (n=1) [34, 34] | 3.23% | -9.68% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.020408 (n=1) [0.020408, 0.020408] | 0.020126 (n=1) [0.020126, 0.020126] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.042 (n=1) [0.042, 0.042] | 0.198 (n=1) [0.198, 0.198] | N/A | N/A |
| Map points mean (/frame) | 28354 (n=1) [28354, 28354] | 7559.2 (n=1) [7559.2, 7559.2] | 8548.6 (n=1) [8548.6, 8548.6] | 73.34% | 69.85% |
| Map points / mission time (points/s proxy) | 2.8966e+05 (n=1) [2.8966e+05, 2.8966e+05] | 77720 (n=1) [77720, 77720] | 87626 (n=1) [87626, 87626] | 73.17% | 69.75% |
| Map payload / mission time (MiB/s proxy, logical edge) | 8.8396 (n=1) [8.8396, 8.8396] | 2.3718 (n=1) [2.3718, 2.3718] | 2.6741 (n=1) [2.6741, 2.6741] | 73.17% | 69.75% |
| Sensor report payload (MiB/s, logical edge; own span) | 8.7569 (n=1) [8.7569, 8.7569] | 2.3711 (n=1) [2.3711, 2.3711] | 2.7307 (n=1) [2.7307, 2.7307] | 72.92% | 68.82% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 8.8396 (n=1) [8.8396, 8.8396] | 2.3718 (n=1) [2.3718, 2.3718] | 2.6741 (n=1) [2.6741, 2.6741] | 73.17% | 69.75% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10.002 (n=1) [10.002, 10.002] | 10.001 (n=1) [10.001, 10.001] | -0.00% | 0.00% |
| Received odometry frequency (Hz) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | -0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 93.3 (n=1) [93.3, 93.3] | 96.057 (n=1) [96.057, 96.057] | 92.261 (n=1) [92.261, 92.261] | -2.96% | 1.11% |
| Odometry receipt p99 gap (ms) | 10.607 (n=1) [10.607, 10.607] | 10.833 (n=1) [10.833, 10.833] | 11.16 (n=1) [11.16, 11.16] | -2.13% | -5.21% |
| Odometry receipt max gap (ms) | 13.181 (n=1) [13.181, 13.181] | 11.226 (n=1) [11.226, 11.226] | 16.057 (n=1) [16.057, 16.057] | 14.83% | -21.82% |
| Actual FSM main callback frequency (profiled only) | 99.581 (n=1) [99.581, 99.581] | 99.953 (n=1) [99.953, 99.953] | 99.837 (n=1) [99.837, 99.837] | -0.37% | -0.26% |
| Actual FSM command callback frequency (profiled only) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | -0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 4.976 (n=1) [4.976, 4.976] | N/A | N/A |
| Guard active duration (s) | 4.0273 (n=1) [4.0273, 4.0273] | 1.8221 (n=1) [1.8221, 1.8221] | 2.2073 (n=1) [2.2073, 2.2073] | 54.76% | 45.19% |

## seed7 — c22_iteration03_preflight — profiled_supplement

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
| Mission time (s) | 40.58 (n=1) [40.58, 40.58] | 44.12 (n=1) [44.12, 44.12] | 45.43 (n=1) [45.43, 45.43] | -8.72% | -11.95% |
| Path length (m) | 228.34 (n=1) [228.34, 228.34] | 228.04 (n=1) [228.04, 228.04] | 228.56 (n=1) [228.56, 228.56] | 0.13% | -0.09% |
| Minimum static-PC clearance (m) | 0.287 (n=1) [0.287, 0.287] | 0.279 (n=1) [0.279, 0.279] | 0.289 (n=1) [0.289, 0.289] | 2.79% | -0.70% |
| Experiment CPU (cores) | 0.77269 (n=1) [0.77269, 0.77269] | 0.45151 (n=1) [0.45151, 0.45151] | 0.47786 (n=1) [0.47786, 0.47786] | 41.57% | 38.16% |
| Experiment CPU (whole-host %) | 3.8635 (n=1) [3.8635, 3.8635] | 2.2575 (n=1) [2.2575, 2.2575] | 2.3893 (n=1) [2.3893, 2.3893] | 41.57% | 38.16% |
| Experiment measurement-window CPU (core-s) | 32.745 (n=1) [32.745, 32.745] | 20.94 (n=1) [20.94, 20.94] | 22.633 (n=1) [22.633, 22.633] | 36.05% | 30.88% |
| Accounting window (s) | 42.378 (n=1) [42.378, 42.378] | 46.379 (n=1) [46.379, 46.379] | 47.362 (n=1) [47.362, 47.362] | -9.44% | -11.76% |
| Experiment CPU 1 s p95 (cores) | 0.96871 (n=1) [0.96871, 0.96871] | 0.6348 (n=1) [0.6348, 0.6348] | 0.63079 (n=1) [0.63079, 0.63079] | 34.47% | 34.88% |
| Experiment CPU 1 s maximum (cores) | 1.0149 (n=1) [1.0149, 1.0149] | 0.70489 (n=1) [0.70489, 0.70489] | 0.77403 (n=1) [0.77403, 0.77403] | 30.55% | 23.73% |
| Composed runtime CPU (cores; includes simulator) | 0.73054 (n=1) [0.73054, 0.73054] | 0.41329 (n=1) [0.41329, 0.41329] | 0.43438 (n=1) [0.43438, 0.43438] | 43.43% | 40.54% |
| Composed runtime measurement-window CPU (core-s) | 30.959 (n=1) [30.959, 30.959] | 19.168 (n=1) [19.168, 19.168] | 20.573 (n=1) [20.573, 20.573] | 38.09% | 33.55% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.1722 (n=1) [3.1722, 3.1722] | 2.9821 (n=1) [2.9821, 2.9821] | 2.9402 (n=1) [2.9402, 2.9402] | 5.99% | 7.31% |
| Whole-host CPU (%) | 10.138 (n=1) [10.138, 10.138] | 9.5071 (n=1) [9.5071, 9.5071] | 8.9149 (n=1) [8.9149, 8.9149] | 6.22% | 12.07% |
| Baseline whole-host CPU (%) | 7.8327 (n=1) [7.8327, 7.8327] | 5.9622 (n=1) [5.9622, 5.9622] | 7.5231 (n=1) [7.5231, 7.5231] | 23.88% | 3.95% |
| Experiment sampled peak RSS (MiB) | 3479.9 (n=1) [3479.9, 3479.9] | 3480.6 (n=1) [3480.6, 3480.6] | 3458.6 (n=1) [3458.6, 3458.6] | -0.02% | 0.61% |
| Experiment sampled peak PSS (MiB) | 3439.6 (n=1) [3439.6, 3439.6] | 3440.4 (n=1) [3440.4, 3440.4] | 3418.1 (n=1) [3418.1, 3418.1] | -0.03% | 0.63% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5542.1 (n=1) [5542.1, 5542.1] | 5557.3 (n=1) [5557.3, 5557.3] | 5568.1 (n=1) [5568.1, 5568.1] | -0.28% | -0.47% |
| GPU device utilization (%) | 53.143 (n=1) [53.143, 53.143] | 49.63 (n=1) [49.63, 49.63] | 53.83 (n=1) [53.83, 53.83] | 6.61% | -1.29% |
| GPU device utilization p95 (%) | 57 (n=1) [57, 57] | 54 (n=1) [54, 54] | 59 (n=1) [59, 59] | 5.26% | -3.51% |
| GPU device memory-controller utilization (%) | 19.429 (n=1) [19.429, 19.429] | 19.065 (n=1) [19.065, 19.065] | 19.021 (n=1) [19.021, 19.021] | 1.87% | 2.10% |
| GPU device memory (MiB) | 1276.3 (n=1) [1276.3, 1276.3] | 1279.5 (n=1) [1279.5, 1279.5] | 1276.6 (n=1) [1276.6, 1276.6] | -0.25% | -0.03% |
| GPU device power (W; not flight attribution) | 18.725 (n=1) [18.725, 18.725] | 18.826 (n=1) [18.826, 18.826] | 18.827 (n=1) [18.827, 18.827] | -0.54% | -0.54% |
| Observed source frame records | 419 (n=1) [419, 419] | 460 (n=1) [460, 460] | 469 (n=1) [469, 469] | -9.79% | -11.93% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 286.89 (n=1) [286.89, 286.89] | 75.00% | 68.12% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.5533e+05 (n=1) [2.5533e+05, 2.5533e+05] | 75.00% | 68.12% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 36722 (n=1) [36722, 36722] | 75.00% | 68.12% |
| Observed source generated points (/frame) | 37052 (n=1) [37052, 37052] | 10267 (n=1) [10267, 10267] | 11563 (n=1) [11563, 11563] | 72.29% | 68.79% |
| Observed source cloud payload (bytes/frame) | 1.1857e+06 (n=1) [1.1857e+06, 1.1857e+06] | 3.2855e+05 (n=1) [3.2855e+05, 3.2855e+05] | 3.7001e+05 (n=1) [3.7001e+05, 3.7001e+05] | 72.29% | 68.79% |
| Map total elapsed mean (ms/frame) | 34.182 (n=1) [34.182, 34.182] | 11.207 (n=1) [11.207, 11.207] | 12.631 (n=1) [12.631, 12.631] | 67.21% | 63.05% |
| Map total elapsed p95 (ms/frame) | 43.008 (n=1) [43.008, 43.008] | 17.739 (n=1) [17.739, 17.739] | 28.718 (n=1) [28.718, 28.718] | 58.75% | 33.23% |
| Map total elapsed max (ms/frame) | 141.65 (n=1) [141.65, 141.65] | 25.642 (n=1) [25.642, 25.642] | 37.85 (n=1) [37.85, 37.85] | 81.90% | 73.28% |
| Map raycast elapsed mean (ms/frame) | 21.772 (n=1) [21.772, 21.772] | 7.5017 (n=1) [7.5017, 7.5017] | 8.2807 (n=1) [8.2807, 8.2807] | 65.54% | 61.97% |
| Map update elapsed mean (ms/frame) | 12.408 (n=1) [12.408, 12.408] | 3.7039 (n=1) [3.7039, 3.7039] | 4.3482 (n=1) [4.3482, 4.3482] | 70.15% | 64.96% |
| Map inflation elapsed mean (ms/frame; nested) | 2.3938 (n=1) [2.3938, 2.3938] | 0.97156 (n=1) [0.97156, 0.97156] | 1.0457 (n=1) [1.0457, 1.0457] | 59.41% | 56.31% |
| Map processed frames / mission time (Hz proxy) | 10.301 (n=1) [10.301, 10.301] | 10.426 (n=1) [10.426, 10.426] | 10.324 (n=1) [10.324, 10.324] | -1.22% | -0.22% |
| Trajectory commits (Hz) | 5.5219 (n=1) [5.5219, 5.5219] | 5.2796 (n=1) [5.2796, 5.2796] | 5.4781 (n=1) [5.4781, 5.4781] | 4.39% | 0.79% |
| Goal retransmissions coalesced | 31 (n=1) [31, 31] | 31 (n=1) [31, 31] | 35 (n=1) [35, 35] | 0.00% | -12.90% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.032783 (n=1) [0.032783, 0.032783] | 0.018816 (n=1) [0.018816, 0.018816] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 5.075 (n=1) [5.075, 5.075] | 0.105 (n=1) [0.105, 0.105] | N/A | N/A |
| Map points mean (/frame) | 37096 (n=1) [37096, 37096] | 10267 (n=1) [10267, 10267] | 11563 (n=1) [11563, 11563] | 72.32% | 68.83% |
| Map points / mission time (points/s proxy) | 3.8211e+05 (n=1) [3.8211e+05, 3.8211e+05] | 1.0705e+05 (n=1) [1.0705e+05, 1.0705e+05] | 1.1937e+05 (n=1) [1.1937e+05, 1.1937e+05] | 71.99% | 68.76% |
| Map payload / mission time (MiB/s proxy, logical edge) | 11.661 (n=1) [11.661, 11.661] | 3.2668 (n=1) [3.2668, 3.2668] | 3.6429 (n=1) [3.6429, 3.6429] | 71.99% | 68.76% |
| Sensor report payload (MiB/s, logical edge; own span) | 11.403 (n=1) [11.403, 11.403] | 3.1736 (n=1) [3.1736, 3.1736] | 3.5775 (n=1) [3.5775, 3.5775] | 72.17% | 68.63% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 11.661 (n=1) [11.661, 11.661] | 3.2668 (n=1) [3.2668, 3.2668] | 3.6429 (n=1) [3.6429, 3.6429] | 71.99% | 68.76% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.004 (n=1) [10.004, 10.004] | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 0.03% | 0.03% |
| Received odometry frequency (Hz) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 0.01% | 0.01% |
| Received command frequency (Hz; holds included) | 94.553 (n=1) [94.553, 94.553] | 93.758 (n=1) [93.758, 93.758] | 92.152 (n=1) [92.152, 92.152] | 0.84% | 2.54% |
| Odometry receipt p99 gap (ms) | 10.659 (n=1) [10.659, 10.659] | 10.856 (n=1) [10.856, 10.856] | 10.742 (n=1) [10.742, 10.742] | -1.85% | -0.78% |
| Odometry receipt max gap (ms) | 11.168 (n=1) [11.168, 11.168] | 15.823 (n=1) [15.823, 15.823] | 11.266 (n=1) [11.266, 11.266] | -41.68% | -0.88% |
| Actual FSM main callback frequency (profiled only) | 100.01 (n=1) [100.01, 100.01] | 99.583 (n=1) [99.583, 99.583] | 99.033 (n=1) [99.033, 99.033] | 0.42% | 0.97% |
| Actual FSM command callback frequency (profiled only) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 9.328 (n=1) [9.328, 9.328] | N/A | N/A |
| Guard active duration (s) | 0 (n=1) [0, 0] | 4.2803 (n=1) [4.2803, 4.2803] | 4.4751 (n=1) [4.4751, 4.4751] | N/A | N/A |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration03/preflight/seed1/r01_run12000/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.45094e-05 | 2.66442e-05 |
| frontend_cloud / 0 | N/A | 0.000124475 | 0.000116247 |
| frontend_enqueue / 0 | N/A | 4.94909e-05 | 5.83326e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.41234e-05 |
| frontend_odom / 0 | N/A | 0.000484095 | 0.000547539 |
| frontend_replan_status / 0 | N/A | N/A | 9.94505e-06 |
| frontend_report / 0 | N/A | 1.52301e-05 | 1.16425e-05 |
| frontend_stats / 0 | N/A | 0.000897522 | 0.000767032 |
| fsm_command_callback / 0 | 0.00889546 | 0.00763539 | 0.00676674 |
| fsm_main_callback / 0 | 0.000586451 | 0.000633306 | 0.000579873 |
| fsm_main_core / 0 | 0.000347378 | 0.000380404 | 0.000380281 |
| fsm_poly_publish / 0 | 3.80979e-05 | 3.75534e-05 | 3.87596e-05 |
| fsm_replan_callback / 0 | 0.000272232 | 0.000312896 | 0.000312467 |
| fsm_replan_core / 0 | 0.000257461 | 0.000272528 | 0.000318512 |
| guard_brake / 0 | 0 | 0 | 0 |
| guard_certificate / 0 | 0.00115451 | 0.00108104 | 0.00103062 |
| guard_recover / 0 | 0 | 0 | 0 |
| map_ack_and_log / 0 | 0.000744656 | 0.00123164 | 0.00126924 |
| map_cloud_enqueue / 0 | 5.90521e-05 | 7.79143e-05 | 7.4674e-05 |
| map_odom_callback / 0 | 0.00102923 | 0.00113827 | 0.00107111 |
| map_prob_update / 0 | 0.258231 | 0.0941032 | 0.0949372 |
| map_ros_to_pcl / 0 | 0.00439204 | 0.000999603 | 0.000945435 |
| map_snapshot_commit_health / 0 | 0.0506116 | 0.0209466 | 0.0214297 |
| map_worker / 0 | 7.38543e-05 | 6.59176e-05 | 6.75452e-05 |
| planner_backup_optimize / 0 | 0.0228555 | 0.0203866 | 0.0210513 |
| planner_commit / 0 | 0.000414285 | 0.000414376 | 0.000427809 |
| planner_corridor_search / 0 | 0.0090084 | 0.0099868 | 0.00932544 |
| planner_exp_optimize / 0 | 0.0485462 | 0.0536752 | 0.0471856 |
| planner_generate_backup / 0 | 0.0176285 | 0.0154631 | 0.0165139 |
| planner_generate_exp / 0 | 0.000415973 | 0.000472817 | 0.000482622 |
| planner_path_search / 0 | 0.010222 | 0.00949335 | 0.0164771 |
| planner_stop_viability / 0 | 0.000338916 | 0.000429134 | 0.00037437 |
| planner_validate_geometry / 0 | 0.00460613 | 0.00526077 | 0.00473546 |
| planner_velocity_extrema / 0 | 0.000101762 | 0.00010366 | 0.000105763 |
| planner_visualize_path / 0 | 0.000571767 | 0.000471686 | 0.00039093 |
| sim_odom_callback / 0 | 0.00934747 | 0.0129401 | 0.0122386 |
| sim_render_callback / 0 | 0.0443399 | 0.0167649 | 0.0199122 |

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration03/preflight/seed3/r01_run12001/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 4.02748e-05 | 2.94527e-05 |
| frontend_cloud / 0 | N/A | 0.000134081 | 0.000125796 |
| frontend_enqueue / 0 | N/A | 4.58082e-05 | 5.03928e-05 |
| frontend_guard_status / 0 | N/A | N/A | 5.64663e-06 |
| frontend_map_ack / 0 | N/A | N/A | 1.74503e-05 |
| frontend_odom / 0 | N/A | 0.00046928 | 0.0005838 |
| frontend_replan_status / 0 | N/A | N/A | 1.03323e-05 |
| frontend_report / 0 | N/A | 1.61055e-05 | 1.43996e-05 |
| frontend_stats / 0 | N/A | 0.000874585 | 0.000776184 |
| fsm_command_callback / 0 | 0.00600887 | 0.0106433 | 0.00794828 |
| fsm_main_callback / 0 | 0.000535109 | 0.000650062 | 0.000602274 |
| fsm_main_core / 0 | 0.000356455 | 0.000385372 | 0.0003742 |
| fsm_poly_publish / 0 | 3.87158e-05 | 3.45852e-05 | 4.38286e-05 |
| fsm_replan_callback / 0 | 0.000262727 | 0.000320817 | 0.000298282 |
| fsm_replan_core / 0 | 0.000272265 | 0.000269378 | 0.000301578 |
| guard_brake / 0 | 3.40723e-06 | 9.28595e-06 | 1.10248e-05 |
| guard_certificate / 0 | 0.000937981 | 0.00121938 | 0.00108352 |
| guard_recover / 0 | 5.88824e-06 | 2.47839e-05 | 1.59087e-05 |
| map_ack_and_log / 0 | 0.000771524 | 0.00136843 | 0.00130097 |
| map_cloud_enqueue / 0 | 6.17384e-05 | 8.45819e-05 | 8.42698e-05 |
| map_odom_callback / 0 | 0.00102896 | 0.000939319 | 0.00107813 |
| map_prob_update / 0 | 0.29933 | 0.108587 | 0.119015 |
| map_ros_to_pcl / 0 | 0.00578211 | 0.00178681 | 0.00141433 |
| map_snapshot_commit_health / 0 | 0.055452 | 0.0230634 | 0.0234889 |
| map_worker / 0 | 7.54887e-05 | 7.0822e-05 | 7.19827e-05 |
| planner_backup_optimize / 0 | 0.043227 | 0.024478 | 0.0255928 |
| planner_commit / 0 | 0.000418525 | 0.000408721 | 0.000408728 |
| planner_corridor_search / 0 | 0.00960321 | 0.0101839 | 0.0109674 |
| planner_exp_optimize / 0 | 0.0522824 | 0.0581145 | 0.0619217 |
| planner_generate_backup / 0 | 0.0195895 | 0.0155136 | 0.0156365 |
| planner_generate_exp / 0 | 0.000437715 | 0.00045071 | 0.000471592 |
| planner_path_search / 0 | 0.0159965 | 0.0169573 | 0.015837 |
| planner_stop_viability / 0 | 0.000339368 | 0.000361609 | 0.000363549 |
| planner_validate_geometry / 0 | 0.00459215 | 0.00447014 | 0.00465282 |
| planner_velocity_extrema / 0 | 0.000104597 | 9.1223e-05 | 9.69112e-05 |
| planner_visualize_path / 0 | 0.000338396 | 0.000598608 | 0.000496883 |
| sim_odom_callback / 0 | 0.0121205 | 0.00992361 | 0.011906 |
| sim_render_callback / 0 | 0.0427505 | 0.0196192 | 0.0180642 |

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration03/preflight/seed5/r01_run12002/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 2.96585e-05 | 2.43038e-05 |
| frontend_cloud / 0 | N/A | 0.000126703 | 0.000124007 |
| frontend_enqueue / 0 | N/A | 4.75284e-05 | 4.99802e-05 |
| frontend_guard_status / 0 | N/A | N/A | 1.15713e-05 |
| frontend_map_ack / 0 | N/A | N/A | 1.77605e-05 |
| frontend_odom / 0 | N/A | 0.000425276 | 0.000544697 |
| frontend_replan_status / 0 | N/A | N/A | 1.10128e-05 |
| frontend_report / 0 | N/A | 1.84509e-05 | 2.16787e-05 |
| frontend_stats / 0 | N/A | 0.000998399 | 0.00118911 |
| fsm_command_callback / 0 | 0.00895332 | 0.00930629 | 0.00965979 |
| fsm_main_callback / 0 | 0.000556109 | 0.000604438 | 0.000615706 |
| fsm_main_core / 0 | 0.000352233 | 0.000378897 | 0.000384425 |
| fsm_poly_publish / 0 | 3.94453e-05 | 3.57613e-05 | 3.80085e-05 |
| fsm_replan_callback / 0 | 0.000266805 | 0.0002964 | 0.000306674 |
| fsm_replan_core / 0 | 0.000268689 | 0.000292952 | 0.000322821 |
| guard_brake / 0 | 6.98532e-05 | 5.99318e-06 | 5.78373e-05 |
| guard_certificate / 0 | 0.0010358 | 0.00118308 | 0.00119966 |
| guard_recover / 0 | 2.36569e-05 | 8.25939e-06 | 2.17068e-05 |
| map_ack_and_log / 0 | 0.000754047 | 0.00125823 | 0.00148122 |
| map_cloud_enqueue / 0 | 6.29106e-05 | 7.56205e-05 | 7.62811e-05 |
| map_odom_callback / 0 | 0.00099683 | 0.000967029 | 0.000910513 |
| map_prob_update / 0 | 0.328618 | 0.117641 | 0.12027 |
| map_ros_to_pcl / 0 | 0.00642439 | 0.00147963 | 0.00174129 |
| map_snapshot_commit_health / 0 | 0.0564746 | 0.0249586 | 0.0254531 |
| map_worker / 0 | 7.93075e-05 | 6.98937e-05 | 7.07523e-05 |
| planner_backup_optimize / 0 | 0.0270888 | 0.0225199 | 0.0289448 |
| planner_commit / 0 | 0.000429573 | 0.00043073 | 0.000417159 |
| planner_corridor_search / 0 | 0.0102112 | 0.0104657 | 0.0109227 |
| planner_exp_optimize / 0 | 0.0588873 | 0.0676079 | 0.0651394 |
| planner_generate_backup / 0 | 0.0183914 | 0.0165506 | 0.0164648 |
| planner_generate_exp / 0 | 0.000441226 | 0.000477516 | 0.000498739 |
| planner_path_search / 0 | 0.0150967 | 0.019399 | 0.0222988 |
| planner_stop_viability / 0 | 0.000311814 | 0.000362481 | 0.000339102 |
| planner_validate_geometry / 0 | 0.00434538 | 0.00442635 | 0.00430033 |
| planner_velocity_extrema / 0 | 0.000104177 | 0.000100916 | 9.37626e-05 |
| planner_visualize_path / 0 | 0.000520108 | 0.000570326 | 0.000641891 |
| sim_odom_callback / 0 | 0.00887463 | 0.010565 | 0.00765145 |
| sim_render_callback / 0 | 0.0472215 | 0.0153305 | 0.0186958 |

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
