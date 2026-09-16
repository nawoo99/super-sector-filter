# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c22_iteration04_preflight — profiled_supplement

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
| Mission time (s) | 37.99 (n=1) [37.99, 37.99] | 39.62 (n=1) [39.62, 39.62] | 38.5 (n=1) [38.5, 38.5] | -4.29% | -1.34% |
| Path length (m) | 222.5 (n=1) [222.5, 222.5] | 223.6 (n=1) [223.6, 223.6] | 223.03 (n=1) [223.03, 223.03] | -0.49% | -0.24% |
| Minimum static-PC clearance (m) | 0.322 (n=1) [0.322, 0.322] | 0.302 (n=1) [0.302, 0.302] | 0.279 (n=1) [0.279, 0.279] | 6.21% | 13.35% |
| Experiment CPU (cores) | 0.60353 (n=1) [0.60353, 0.60353] | 0.40029 (n=1) [0.40029, 0.40029] | 0.39793 (n=1) [0.39793, 0.39793] | 33.68% | 34.07% |
| Experiment CPU (whole-host %) | 3.0176 (n=1) [3.0176, 3.0176] | 2.0014 (n=1) [2.0014, 2.0014] | 1.9897 (n=1) [1.9897, 1.9897] | 33.68% | 34.07% |
| Experiment measurement-window CPU (core-s) | 23.681 (n=1) [23.681, 23.681] | 16.553 (n=1) [16.553, 16.553] | 16.037 (n=1) [16.037, 16.037] | 30.10% | 32.28% |
| Accounting window (s) | 39.237 (n=1) [39.237, 39.237] | 41.354 (n=1) [41.354, 41.354] | 40.301 (n=1) [40.301, 40.301] | -5.40% | -2.71% |
| Experiment CPU 1 s p95 (cores) | 0.7111 (n=1) [0.7111, 0.7111] | 0.47428 (n=1) [0.47428, 0.47428] | 0.4755 (n=1) [0.4755, 0.4755] | 33.30% | 33.13% |
| Experiment CPU 1 s maximum (cores) | 0.97529 (n=1) [0.97529, 0.97529] | 0.59876 (n=1) [0.59876, 0.59876] | 0.49952 (n=1) [0.49952, 0.49952] | 38.61% | 48.78% |
| Composed runtime CPU (cores; includes simulator) | 0.56145 (n=1) [0.56145, 0.56145] | 0.35401 (n=1) [0.35401, 0.35401] | 0.35084 (n=1) [0.35084, 0.35084] | 36.95% | 37.51% |
| Composed runtime measurement-window CPU (core-s) | 22.03 (n=1) [22.03, 22.03] | 14.64 (n=1) [14.64, 14.64] | 14.139 (n=1) [14.139, 14.139] | 33.55% | 35.82% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.136 (n=1) [3.136, 3.136] | 3.1521 (n=1) [3.1521, 3.1521] | 3.3036 (n=1) [3.3036, 3.3036] | -0.51% | -5.35% |
| Whole-host CPU (%) | 9.6668 (n=1) [9.6668, 9.6668] | 9.157 (n=1) [9.157, 9.157] | 9.2289 (n=1) [9.2289, 9.2289] | 5.27% | 4.53% |
| Baseline whole-host CPU (%) | 7.5571 (n=1) [7.5571, 7.5571] | 7.9333 (n=1) [7.9333, 7.9333] | 7.73 (n=1) [7.73, 7.73] | -4.98% | -2.29% |
| Experiment sampled peak RSS (MiB) | 3386.5 (n=1) [3386.5, 3386.5] | 3383.1 (n=1) [3383.1, 3383.1] | 3379.1 (n=1) [3379.1, 3379.1] | 0.10% | 0.22% |
| Experiment sampled peak PSS (MiB) | 3346.1 (n=1) [3346.1, 3346.1] | 3342.7 (n=1) [3342.7, 3342.7] | 3338.6 (n=1) [3338.6, 3338.6] | 0.10% | 0.22% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5589.9 (n=1) [5589.9, 5589.9] | 5587.7 (n=1) [5587.7, 5587.7] | 5595.5 (n=1) [5595.5, 5595.5] | 0.04% | -0.10% |
| GPU device utilization (%) | 52.128 (n=1) [52.128, 52.128] | 53.659 (n=1) [53.659, 53.659] | 50.55 (n=1) [50.55, 50.55] | -2.94% | 3.03% |
| GPU device utilization p95 (%) | 57 (n=1) [57, 57] | 58 (n=1) [58, 58] | 56 (n=1) [56, 56] | -1.75% | 1.75% |
| GPU device memory-controller utilization (%) | 19.026 (n=1) [19.026, 19.026] | 19.024 (n=1) [19.024, 19.024] | 19.05 (n=1) [19.05, 19.05] | 0.01% | -0.13% |
| GPU device memory (MiB) | 1269.1 (n=1) [1269.1, 1269.1] | 1265.8 (n=1) [1265.8, 1265.8] | 1267.8 (n=1) [1267.8, 1267.8] | 0.25% | 0.10% |
| GPU device power (W; not flight attribution) | 18.729 (n=1) [18.729, 18.729] | 18.757 (n=1) [18.757, 18.757] | 18.728 (n=1) [18.728, 18.728] | -0.15% | 0.01% |
| Observed source frame records | 391 (n=1) [391, 391] | 413 (n=1) [413, 413] | 402 (n=1) [402, 402] | -5.63% | -2.81% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 231.72 (n=1) [231.72, 231.72] | 75.00% | 74.25% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.0623e+05 (n=1) [2.0623e+05, 2.0623e+05] | 75.00% | 74.25% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 29660 (n=1) [29660, 29660] | 75.00% | 74.25% |
| Observed source generated points (/frame) | 16685 (n=1) [16685, 16685] | 4250.5 (n=1) [4250.5, 4250.5] | 4275.6 (n=1) [4275.6, 4275.6] | 74.53% | 74.37% |
| Observed source cloud payload (bytes/frame) | 5.3393e+05 (n=1) [5.3393e+05, 5.3393e+05] | 1.3602e+05 (n=1) [1.3602e+05, 1.3602e+05] | 1.3682e+05 (n=1) [1.3682e+05, 1.3682e+05] | 74.53% | 74.37% |
| Map total elapsed mean (ms/frame) | 25.359 (n=1) [25.359, 25.359] | 9.7024 (n=1) [9.7024, 9.7024] | 9.3454 (n=1) [9.3454, 9.3454] | 61.74% | 63.15% |
| Map total elapsed p95 (ms/frame) | 32.324 (n=1) [32.324, 32.324] | 14.64 (n=1) [14.64, 14.64] | 13.472 (n=1) [13.472, 13.472] | 54.71% | 58.32% |
| Map total elapsed max (ms/frame) | 61.455 (n=1) [61.455, 61.455] | 25.611 (n=1) [25.611, 25.611] | 38.816 (n=1) [38.816, 38.816] | 58.33% | 36.84% |
| Map raycast elapsed mean (ms/frame) | 15.36 (n=1) [15.36, 15.36] | 6.4706 (n=1) [6.4706, 6.4706] | 6.1181 (n=1) [6.1181, 6.1181] | 57.87% | 60.17% |
| Map update elapsed mean (ms/frame) | 9.9977 (n=1) [9.9977, 9.9977] | 3.2303 (n=1) [3.2303, 3.2303] | 3.226 (n=1) [3.226, 3.226] | 67.69% | 67.73% |
| Map inflation elapsed mean (ms/frame; nested) | 1.3484 (n=1) [1.3484, 1.3484] | 0.65142 (n=1) [0.65142, 0.65142] | 0.65606 (n=1) [0.65606, 0.65606] | 51.69% | 51.35% |
| Map processed frames / mission time (Hz proxy) | 10.292 (n=1) [10.292, 10.292] | 10.424 (n=1) [10.424, 10.424] | 10.442 (n=1) [10.442, 10.442] | -1.28% | -1.45% |
| Trajectory commits (Hz) | 5.5715 (n=1) [5.5715, 5.5715] | 5.4052 (n=1) [5.4052, 5.4052] | 5.4213 (n=1) [5.4213, 5.4213] | 2.98% | 2.69% |
| Goal retransmissions coalesced | 30 (n=1) [30, 30] | 32 (n=1) [32, 32] | 31 (n=1) [31, 31] | -6.67% | -3.33% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.021948 (n=1) [0.021948, 0.021948] | 0.03122 (n=1) [0.03122, 0.03122] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.055 (n=1) [0.055, 0.055] | 1.001 (n=1) [1.001, 1.001] | N/A | N/A |
| Map points mean (/frame) | 16685 (n=1) [16685, 16685] | 4250.5 (n=1) [4250.5, 4250.5] | 4275.6 (n=1) [4275.6, 4275.6] | 74.53% | 74.37% |
| Map points / mission time (points/s proxy) | 1.7173e+05 (n=1) [1.7173e+05, 1.7173e+05] | 44308 (n=1) [44308, 44308] | 44644 (n=1) [44644, 44644] | 74.20% | 74.00% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.2407 (n=1) [5.2407, 5.2407] | 1.3522 (n=1) [1.3522, 1.3522] | 1.3624 (n=1) [1.3624, 1.3624] | 74.20% | 74.00% |
| Sensor report payload (MiB/s, logical edge; own span) | 5.1696 (n=1) [5.1696, 5.1696] | 1.3229 (n=1) [1.3229, 1.3229] | 1.3119 (n=1) [1.3119, 1.3119] | 74.41% | 74.62% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.2407 (n=1) [5.2407, 5.2407] | 1.3522 (n=1) [1.3522, 1.3522] | 1.3624 (n=1) [1.3624, 1.3624] | 74.20% | 74.00% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 9.9999 (n=1) [9.9999, 9.9999] | 9.9996 (n=1) [9.9996, 9.9996] | 9.9995 (n=1) [9.9995, 9.9995] | 0.00% | 0.00% |
| Received odometry frequency (Hz) | 99.993 (n=1) [99.993, 99.993] | 99.991 (n=1) [99.991, 99.991] | 99.993 (n=1) [99.993, 99.993] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.713 (n=1) [94.713, 94.713] | 93.611 (n=1) [93.611, 93.611] | 93.502 (n=1) [93.502, 93.502] | 1.16% | 1.28% |
| Odometry receipt p99 gap (ms) | 10.549 (n=1) [10.549, 10.549] | 10.779 (n=1) [10.779, 10.779] | 10.737 (n=1) [10.737, 10.737] | -2.18% | -1.78% |
| Odometry receipt max gap (ms) | 11.636 (n=1) [11.636, 11.636] | 12.639 (n=1) [12.639, 12.639] | 11.637 (n=1) [11.637, 11.637] | -8.62% | -0.01% |
| Actual FSM main callback frequency (profiled only) | 99.992 (n=1) [99.992, 99.992] | 99.908 (n=1) [99.908, 99.908] | 99.994 (n=1) [99.994, 99.994] | 0.08% | -0.00% |
| Actual FSM command callback frequency (profiled only) | 99.992 (n=1) [99.992, 99.992] | 99.993 (n=1) [99.993, 99.993] | 99.994 (n=1) [99.994, 99.994] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 1.013 (n=1) [1.013, 1.013] | N/A | N/A |
| Guard active duration (s) | 0 (n=1) [0, 0] | 1.3601 (n=1) [1.3601, 1.3601] | 0.46286 (n=1) [0.46286, 0.46286] | N/A | N/A |

## seed3 — c22_iteration04_preflight — profiled_supplement

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
| Mission time (s) | 38.17 (n=1) [38.17, 38.17] | 38.35 (n=1) [38.35, 38.35] | 39.92 (n=1) [39.92, 39.92] | -0.47% | -4.58% |
| Path length (m) | 225.92 (n=1) [225.92, 225.92] | 225.22 (n=1) [225.22, 225.22] | 225.11 (n=1) [225.11, 225.11] | 0.31% | 0.36% |
| Minimum static-PC clearance (m) | 0.326 (n=1) [0.326, 0.326] | 0.343 (n=1) [0.343, 0.343] | 0.287 (n=1) [0.287, 0.287] | -5.21% | 11.96% |
| Experiment CPU (cores) | 0.63094 (n=1) [0.63094, 0.63094] | 0.40532 (n=1) [0.40532, 0.40532] | 0.43553 (n=1) [0.43553, 0.43553] | 35.76% | 30.97% |
| Experiment CPU (whole-host %) | 3.1547 (n=1) [3.1547, 3.1547] | 2.0266 (n=1) [2.0266, 2.0266] | 2.1776 (n=1) [2.1776, 2.1776] | 35.76% | 30.97% |
| Experiment measurement-window CPU (core-s) | 24.784 (n=1) [24.784, 24.784] | 16.35 (n=1) [16.35, 16.35] | 18.033 (n=1) [18.033, 18.033] | 34.03% | 27.24% |
| Accounting window (s) | 39.281 (n=1) [39.281, 39.281] | 40.339 (n=1) [40.339, 40.339] | 41.404 (n=1) [41.404, 41.404] | -2.69% | -5.40% |
| Experiment CPU 1 s p95 (cores) | 0.77853 (n=1) [0.77853, 0.77853] | 0.51351 (n=1) [0.51351, 0.51351] | 0.57737 (n=1) [0.57737, 0.57737] | 34.04% | 25.84% |
| Experiment CPU 1 s maximum (cores) | 0.80845 (n=1) [0.80845, 0.80845] | 0.59869 (n=1) [0.59869, 0.59869] | 0.79444 (n=1) [0.79444, 0.79444] | 25.95% | 1.73% |
| Composed runtime CPU (cores; includes simulator) | 0.59119 (n=1) [0.59119, 0.59119] | 0.36189 (n=1) [0.36189, 0.36189] | 0.39146 (n=1) [0.39146, 0.39146] | 38.79% | 33.78% |
| Composed runtime measurement-window CPU (core-s) | 23.222 (n=1) [23.222, 23.222] | 14.598 (n=1) [14.598, 14.598] | 16.208 (n=1) [16.208, 16.208] | 37.14% | 30.21% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.1873 (n=1) [3.1873, 3.1873] | 3.3053 (n=1) [3.3053, 3.3053] | 3.3695 (n=1) [3.3695, 3.3695] | -3.70% | -5.72% |
| Whole-host CPU (%) | 9.9285 (n=1) [9.9285, 9.9285] | 8.8105 (n=1) [8.8105, 8.8105] | 9.2066 (n=1) [9.2066, 9.2066] | 11.26% | 7.27% |
| Baseline whole-host CPU (%) | 7.6988 (n=1) [7.6988, 7.6988] | 7.2029 (n=1) [7.2029, 7.2029] | 7.7937 (n=1) [7.7937, 7.7937] | 6.44% | -1.23% |
| Experiment sampled peak RSS (MiB) | 3433.1 (n=1) [3433.1, 3433.1] | 3434.9 (n=1) [3434.9, 3434.9] | 3453.2 (n=1) [3453.2, 3453.2] | -0.05% | -0.59% |
| Experiment sampled peak PSS (MiB) | 3392.8 (n=1) [3392.8, 3392.8] | 3394.6 (n=1) [3394.6, 3394.6] | 3412.9 (n=1) [3412.9, 3412.9] | -0.05% | -0.59% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5508.4 (n=1) [5508.4, 5508.4] | 5547.2 (n=1) [5547.2, 5547.2] | 5540.2 (n=1) [5540.2, 5540.2] | -0.70% | -0.58% |
| GPU device utilization (%) | 49.41 (n=1) [49.41, 49.41] | 50.825 (n=1) [50.825, 50.825] | 51.659 (n=1) [51.659, 51.659] | -2.86% | -4.55% |
| GPU device utilization p95 (%) | 55 (n=1) [55, 55] | 56 (n=1) [56, 56] | 57 (n=1) [57, 57] | -1.82% | -3.64% |
| GPU device memory-controller utilization (%) | 19.026 (n=1) [19.026, 19.026] | 19.05 (n=1) [19.05, 19.05] | 19 (n=1) [19, 19] | -0.13% | 0.13% |
| GPU device memory (MiB) | 1268 (n=1) [1268, 1268] | 1264.1 (n=1) [1264.1, 1264.1] | 1267.8 (n=1) [1267.8, 1267.8] | 0.30% | 0.02% |
| GPU device power (W; not flight attribution) | 18.692 (n=1) [18.692, 18.692] | 18.674 (n=1) [18.674, 18.674] | 18.657 (n=1) [18.657, 18.657] | 0.09% | 0.18% |
| Observed source frame records | 392 (n=1) [392, 392] | 401 (n=1) [401, 401] | 412 (n=1) [412, 412] | -2.30% | -5.10% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 239.75 (n=1) [239.75, 239.75] | 75.00% | 73.36% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1337e+05 (n=1) [2.1337e+05, 2.1337e+05] | 75.00% | 73.36% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 30687 (n=1) [30687, 30687] | 75.00% | 73.36% |
| Observed source generated points (/frame) | 22114 (n=1) [22114, 22114] | 6492.2 (n=1) [6492.2, 6492.2] | 7125 (n=1) [7125, 7125] | 70.64% | 67.78% |
| Observed source cloud payload (bytes/frame) | 7.0764e+05 (n=1) [7.0764e+05, 7.0764e+05] | 2.0775e+05 (n=1) [2.0775e+05, 2.0775e+05] | 2.28e+05 (n=1) [2.28e+05, 2.28e+05] | 70.64% | 67.78% |
| Map total elapsed mean (ms/frame) | 30.6 (n=1) [30.6, 30.6] | 10.893 (n=1) [10.893, 10.893] | 11.153 (n=1) [11.153, 11.153] | 64.40% | 63.55% |
| Map total elapsed p95 (ms/frame) | 38.696 (n=1) [38.696, 38.696] | 16.072 (n=1) [16.072, 16.072] | 17.117 (n=1) [17.117, 17.117] | 58.47% | 55.77% |
| Map total elapsed max (ms/frame) | 76.485 (n=1) [76.485, 76.485] | 26.676 (n=1) [26.676, 26.676] | 27.557 (n=1) [27.557, 27.557] | 65.12% | 63.97% |
| Map raycast elapsed mean (ms/frame) | 18.953 (n=1) [18.953, 18.953] | 7.2413 (n=1) [7.2413, 7.2413] | 7.3508 (n=1) [7.3508, 7.3508] | 61.79% | 61.22% |
| Map update elapsed mean (ms/frame) | 11.646 (n=1) [11.646, 11.646] | 3.6501 (n=1) [3.6501, 3.6501] | 3.8008 (n=1) [3.8008, 3.8008] | 68.66% | 67.36% |
| Map inflation elapsed mean (ms/frame; nested) | 1.7632 (n=1) [1.7632, 1.7632] | 0.83757 (n=1) [0.83757, 0.83757] | 0.83675 (n=1) [0.83675, 0.83675] | 52.50% | 52.54% |
| Map processed frames / mission time (Hz proxy) | 10.244 (n=1) [10.244, 10.244] | 10.456 (n=1) [10.456, 10.456] | 10.321 (n=1) [10.321, 10.321] | -2.08% | -0.75% |
| Trajectory commits (Hz) | 5.396 (n=1) [5.396, 5.396] | 5.2623 (n=1) [5.2623, 5.2623] | 5.5164 (n=1) [5.5164, 5.5164] | 2.48% | -2.23% |
| Goal retransmissions coalesced | 34 (n=1) [34, 34] | 32 (n=1) [32, 32] | 36 (n=1) [36, 36] | 5.88% | -5.88% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.02 (n=1) [0.02, 0.02] | 0.018629 (n=1) [0.018629, 0.018629] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.043 (n=1) [0.043, 0.043] | 0.163 (n=1) [0.163, 0.163] | N/A | N/A |
| Map points mean (/frame) | 22123 (n=1) [22123, 22123] | 6492.2 (n=1) [6492.2, 6492.2] | 7125 (n=1) [7125, 7125] | 70.65% | 67.79% |
| Map points / mission time (points/s proxy) | 2.2663e+05 (n=1) [2.2663e+05, 2.2663e+05] | 67884 (n=1) [67884, 67884] | 73534 (n=1) [73534, 73534] | 70.05% | 67.55% |
| Map payload / mission time (MiB/s proxy, logical edge) | 6.9161 (n=1) [6.9161, 6.9161] | 2.0717 (n=1) [2.0717, 2.0717] | 2.2441 (n=1) [2.2441, 2.2441] | 70.05% | 67.55% |
| Sensor report payload (MiB/s, logical edge; own span) | 6.7332 (n=1) [6.7332, 6.7332] | 1.9881 (n=1) [1.9881, 1.9881] | 2.1983 (n=1) [2.1983, 2.1983] | 70.47% | 67.35% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 6.9161 (n=1) [6.9161, 6.9161] | 2.0717 (n=1) [2.0717, 2.0717] | 2.2441 (n=1) [2.2441, 2.2441] | 70.05% | 67.55% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 9.9999 (n=1) [9.9999, 9.9999] | 9.9998 (n=1) [9.9998, 9.9998] | 10 (n=1) [10, 10] | 0.00% | -0.00% |
| Received odometry frequency (Hz) | 99.996 (n=1) [99.996, 99.996] | 99.995 (n=1) [99.995, 99.995] | 100 (n=1) [100, 100] | 0.00% | -0.01% |
| Received command frequency (Hz; holds included) | 95.182 (n=1) [95.182, 95.182] | 95.17 (n=1) [95.17, 95.17] | 95.501 (n=1) [95.501, 95.501] | 0.01% | -0.33% |
| Odometry receipt p99 gap (ms) | 10.697 (n=1) [10.697, 10.697] | 10.608 (n=1) [10.608, 10.608] | 10.694 (n=1) [10.694, 10.694] | 0.83% | 0.03% |
| Odometry receipt max gap (ms) | 11.055 (n=1) [11.055, 11.055] | 11.975 (n=1) [11.975, 11.975] | 15.679 (n=1) [15.679, 15.679] | -8.32% | -41.82% |
| Actual FSM main callback frequency (profiled only) | 99.695 (n=1) [99.695, 99.695] | 99.896 (n=1) [99.896, 99.896] | 99.996 (n=1) [99.996, 99.996] | -0.20% | -0.30% |
| Actual FSM command callback frequency (profiled only) | 99.995 (n=1) [99.995, 99.995] | 99.996 (n=1) [99.996, 99.996] | 99.996 (n=1) [99.996, 99.996] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 2.228 (n=1) [2.228, 2.228] | N/A | N/A |
| Guard active duration (s) | 1.4483 (n=1) [1.4483, 1.4483] | 1.8518 (n=1) [1.8518, 1.8518] | 0.95776 (n=1) [0.95776, 0.95776] | -27.85% | 33.87% |

## seed5 — c22_iteration04_preflight — profiled_supplement

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
| Mission time (s) | 39.3 (n=1) [39.3, 39.3] | 45.2 (n=1) [45.2, 45.2] | 42.12 (n=1) [42.12, 42.12] | -15.01% | -7.18% |
| Path length (m) | 225.15 (n=1) [225.15, 225.15] | 228.52 (n=1) [228.52, 228.52] | 229.07 (n=1) [229.07, 229.07] | -1.50% | -1.74% |
| Minimum static-PC clearance (m) | 0.328 (n=1) [0.328, 0.328] | 0.212 (n=1) [0.212, 0.212] | 0.26 (n=1) [0.26, 0.26] | 35.37% | 20.73% |
| Experiment CPU (cores) | 0.72278 (n=1) [0.72278, 0.72278] | 0.41803 (n=1) [0.41803, 0.41803] | 0.4537 (n=1) [0.4537, 0.4537] | 42.16% | 37.23% |
| Experiment CPU (whole-host %) | 3.6139 (n=1) [3.6139, 3.6139] | 2.0902 (n=1) [2.0902, 2.0902] | 2.2685 (n=1) [2.2685, 2.2685] | 42.16% | 37.23% |
| Experiment measurement-window CPU (core-s) | 29.922 (n=1) [29.922, 29.922] | 19.43 (n=1) [19.43, 19.43] | 19.739 (n=1) [19.739, 19.739] | 35.06% | 34.03% |
| Accounting window (s) | 41.399 (n=1) [41.399, 41.399] | 46.481 (n=1) [46.481, 46.481] | 43.507 (n=1) [43.507, 43.507] | -12.28% | -5.09% |
| Experiment CPU 1 s p95 (cores) | 0.82883 (n=1) [0.82883, 0.82883] | 0.54495 (n=1) [0.54495, 0.54495] | 0.56065 (n=1) [0.56065, 0.56065] | 34.25% | 32.36% |
| Experiment CPU 1 s maximum (cores) | 1.2574 (n=1) [1.2574, 1.2574] | 0.6603 (n=1) [0.6603, 0.6603] | 0.7264 (n=1) [0.7264, 0.7264] | 47.49% | 42.23% |
| Composed runtime CPU (cores; includes simulator) | 0.68228 (n=1) [0.68228, 0.68228] | 0.37248 (n=1) [0.37248, 0.37248] | 0.4101 (n=1) [0.4101, 0.4101] | 45.41% | 39.89% |
| Composed runtime measurement-window CPU (core-s) | 28.246 (n=1) [28.246, 28.246] | 17.313 (n=1) [17.313, 17.313] | 17.842 (n=1) [17.842, 17.842] | 38.71% | 36.83% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.2273 (n=1) [3.2273, 3.2273] | 3.2622 (n=1) [3.2622, 3.2622] | 3.5485 (n=1) [3.5485, 3.5485] | -1.08% | -9.95% |
| Whole-host CPU (%) | 10.09 (n=1) [10.09, 10.09] | 9.0788 (n=1) [9.0788, 9.0788] | 9.429 (n=1) [9.429, 9.429] | 10.02% | 6.55% |
| Baseline whole-host CPU (%) | 8.4611 (n=1) [8.4611, 8.4611] | 8.319 (n=1) [8.319, 8.319] | 7.1562 (n=1) [7.1562, 7.1562] | 1.68% | 15.42% |
| Experiment sampled peak RSS (MiB) | 3473.2 (n=1) [3473.2, 3473.2] | 3477.7 (n=1) [3477.7, 3477.7] | 3479.9 (n=1) [3479.9, 3479.9] | -0.13% | -0.19% |
| Experiment sampled peak PSS (MiB) | 3432.8 (n=1) [3432.8, 3432.8] | 3437.5 (n=1) [3437.5, 3437.5] | 3439.6 (n=1) [3439.6, 3439.6] | -0.14% | -0.20% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5498.5 (n=1) [5498.5, 5498.5] | 5499.3 (n=1) [5499.3, 5499.3] | 5469.4 (n=1) [5469.4, 5469.4] | -0.01% | 0.53% |
| GPU device utilization (%) | 53.805 (n=1) [53.805, 53.805] | 52.087 (n=1) [52.087, 52.087] | 50 (n=1) [50, 50] | 3.19% | 7.07% |
| GPU device utilization p95 (%) | 58 (n=1) [58, 58] | 59 (n=1) [59, 59] | 55 (n=1) [55, 55] | -1.72% | 5.17% |
| GPU device memory-controller utilization (%) | 19 (n=1) [19, 19] | 19.065 (n=1) [19.065, 19.065] | 19.136 (n=1) [19.136, 19.136] | -0.34% | -0.72% |
| GPU device memory (MiB) | 1269.5 (n=1) [1269.5, 1269.5] | 1268.8 (n=1) [1268.8, 1268.8] | 1268.5 (n=1) [1268.5, 1268.5] | 0.05% | 0.07% |
| GPU device power (W; not flight attribution) | 18.652 (n=1) [18.652, 18.652] | 18.774 (n=1) [18.774, 18.774] | 18.698 (n=1) [18.698, 18.698] | -0.65% | -0.25% |
| Observed source frame records | 410 (n=1) [410, 410] | 462 (n=1) [462, 462] | 432 (n=1) [432, 432] | -12.68% | -5.37% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 248.44 (n=1) [248.44, 248.44] | 75.00% | 72.40% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.2111e+05 (n=1) [2.2111e+05, 2.2111e+05] | 75.00% | 72.40% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31800 (n=1) [31800, 31800] | 75.00% | 72.40% |
| Observed source generated points (/frame) | 27768 (n=1) [27768, 27768] | 7786.8 (n=1) [7786.8, 7786.8] | 8614.8 (n=1) [8614.8, 8614.8] | 71.96% | 68.98% |
| Observed source cloud payload (bytes/frame) | 8.8858e+05 (n=1) [8.8858e+05, 8.8858e+05] | 2.4918e+05 (n=1) [2.4918e+05, 2.4918e+05] | 2.7567e+05 (n=1) [2.7567e+05, 2.7567e+05] | 71.96% | 68.98% |
| Map total elapsed mean (ms/frame) | 35.195 (n=1) [35.195, 35.195] | 10.924 (n=1) [10.924, 10.924] | 12.09 (n=1) [12.09, 12.09] | 68.96% | 65.65% |
| Map total elapsed p95 (ms/frame) | 48.704 (n=1) [48.704, 48.704] | 16.423 (n=1) [16.423, 16.423] | 18.28 (n=1) [18.28, 18.28] | 66.28% | 62.47% |
| Map total elapsed max (ms/frame) | 86.969 (n=1) [86.969, 86.969] | 52.714 (n=1) [52.714, 52.714] | 55.366 (n=1) [55.366, 55.366] | 39.39% | 36.34% |
| Map raycast elapsed mean (ms/frame) | 21.981 (n=1) [21.981, 21.981] | 7.2747 (n=1) [7.2747, 7.2747] | 7.8583 (n=1) [7.8583, 7.8583] | 66.90% | 64.25% |
| Map update elapsed mean (ms/frame) | 13.212 (n=1) [13.212, 13.212] | 3.6474 (n=1) [3.6474, 3.6474] | 4.2304 (n=1) [4.2304, 4.2304] | 72.39% | 67.98% |
| Map inflation elapsed mean (ms/frame; nested) | 2.147 (n=1) [2.147, 2.147] | 0.8743 (n=1) [0.8743, 0.8743] | 0.98876 (n=1) [0.98876, 0.98876] | 59.28% | 53.95% |
| Map processed frames / mission time (Hz proxy) | 10.433 (n=1) [10.433, 10.433] | 10.199 (n=1) [10.199, 10.199] | 10.256 (n=1) [10.256, 10.256] | 2.24% | 1.69% |
| Trajectory commits (Hz) | 5.5305 (n=1) [5.5305, 5.5305] | 4.8592 (n=1) [4.8592, 4.8592] | 5.1506 (n=1) [5.1506, 5.1506] | 12.14% | 6.87% |
| Goal retransmissions coalesced | 33 (n=1) [33, 33] | 33 (n=1) [33, 33] | 35 (n=1) [35, 35] | 0.00% | -6.06% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.02155 (n=1) [0.02155, 0.02155] | 0.021619 (n=1) [0.021619, 0.021619] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 1.056 (n=1) [1.056, 1.056] | 1.263 (n=1) [1.263, 1.263] | N/A | N/A |
| Map points mean (/frame) | 27768 (n=1) [27768, 27768] | 7794.5 (n=1) [7794.5, 7794.5] | 8614.8 (n=1) [8614.8, 8614.8] | 71.93% | 68.98% |
| Map points / mission time (points/s proxy) | 2.8969e+05 (n=1) [2.8969e+05, 2.8969e+05] | 79497 (n=1) [79497, 79497] | 88357 (n=1) [88357, 88357] | 72.56% | 69.50% |
| Map payload / mission time (MiB/s proxy, logical edge) | 8.8407 (n=1) [8.8407, 8.8407] | 2.4261 (n=1) [2.4261, 2.4261] | 2.6965 (n=1) [2.6965, 2.6965] | 72.56% | 69.50% |
| Sensor report payload (MiB/s, logical edge; own span) | 8.586 (n=1) [8.586, 8.586] | 2.4128 (n=1) [2.4128, 2.4128] | 2.719 (n=1) [2.719, 2.719] | 71.90% | 68.33% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 8.8407 (n=1) [8.8407, 8.8407] | 2.4261 (n=1) [2.4261, 2.4261] | 2.6965 (n=1) [2.6965, 2.6965] | 72.56% | 69.50% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 9.9998 (n=1) [9.9998, 9.9998] | 10 (n=1) [10, 10] | 0.00% | -0.00% |
| Received odometry frequency (Hz) | 99.997 (n=1) [99.997, 99.997] | 99.996 (n=1) [99.996, 99.996] | 99.996 (n=1) [99.996, 99.996] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.478 (n=1) [94.478, 94.478] | 90.836 (n=1) [90.836, 90.836] | 93.792 (n=1) [93.792, 93.792] | 3.86% | 0.73% |
| Odometry receipt p99 gap (ms) | 10.665 (n=1) [10.665, 10.665] | 10.863 (n=1) [10.863, 10.863] | 10.838 (n=1) [10.838, 10.838] | -1.86% | -1.63% |
| Odometry receipt max gap (ms) | 13.872 (n=1) [13.872, 13.872] | 12.227 (n=1) [12.227, 12.227] | 11.292 (n=1) [11.292, 11.292] | 11.86% | 18.60% |
| Actual FSM main callback frequency (profiled only) | 99.968 (n=1) [99.968, 99.968] | 99.622 (n=1) [99.622, 99.622] | 99.798 (n=1) [99.798, 99.798] | 0.35% | 0.17% |
| Actual FSM command callback frequency (profiled only) | 99.997 (n=1) [99.997, 99.997] | 100.02 (n=1) [100.02, 100.02] | 99.998 (n=1) [99.998, 99.998] | -0.02% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.546 (n=1) [3.546, 3.546] | N/A | N/A |
| Guard active duration (s) | 0.87814 (n=1) [0.87814, 0.87814] | 5.3777 (n=1) [5.3777, 5.3777] | 1.4817 (n=1) [1.4817, 1.4817] | -512.40% | -68.73% |

## seed7 — c22_iteration04_preflight — profiled_supplement

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
| Mission time (s) | 39.64 (n=1) [39.64, 39.64] | 50.79 (n=1) [50.79, 50.79] | 43.97 (n=1) [43.97, 43.97] | -28.13% | -10.92% |
| Path length (m) | 227.12 (n=1) [227.12, 227.12] | 232.94 (n=1) [232.94, 232.94] | 229.17 (n=1) [229.17, 229.17] | -2.56% | -0.90% |
| Minimum static-PC clearance (m) | 0.284 (n=1) [0.284, 0.284] | 0.294 (n=1) [0.294, 0.294] | 0.302 (n=1) [0.302, 0.302] | -3.52% | -6.34% |
| Experiment CPU (cores) | 0.76703 (n=1) [0.76703, 0.76703] | 0.44451 (n=1) [0.44451, 0.44451] | 0.47573 (n=1) [0.47573, 0.47573] | 42.05% | 37.98% |
| Experiment CPU (whole-host %) | 3.8352 (n=1) [3.8352, 3.8352] | 2.2225 (n=1) [2.2225, 2.2225] | 2.3787 (n=1) [2.3787, 2.3787] | 42.05% | 37.98% |
| Experiment measurement-window CPU (core-s) | 31.788 (n=1) [31.788, 31.788] | 23.461 (n=1) [23.461, 23.461] | 21.654 (n=1) [21.654, 21.654] | 26.19% | 31.88% |
| Accounting window (s) | 41.442 (n=1) [41.442, 41.442] | 52.779 (n=1) [52.779, 52.779] | 45.518 (n=1) [45.518, 45.518] | -27.36% | -9.83% |
| Experiment CPU 1 s p95 (cores) | 1.0224 (n=1) [1.0224, 1.0224] | 0.65492 (n=1) [0.65492, 0.65492] | 0.59299 (n=1) [0.59299, 0.59299] | 35.94% | 42.00% |
| Experiment CPU 1 s maximum (cores) | 1.0922 (n=1) [1.0922, 1.0922] | 0.72688 (n=1) [0.72688, 0.72688] | 0.64209 (n=1) [0.64209, 0.64209] | 33.45% | 41.21% |
| Composed runtime CPU (cores; includes simulator) | 0.72674 (n=1) [0.72674, 0.72674] | 0.39802 (n=1) [0.39802, 0.39802] | 0.43008 (n=1) [0.43008, 0.43008] | 45.23% | 40.82% |
| Composed runtime measurement-window CPU (core-s) | 30.118 (n=1) [30.118, 30.118] | 21.007 (n=1) [21.007, 21.007] | 19.576 (n=1) [19.576, 19.576] | 30.25% | 35.00% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.2255 (n=1) [3.2255, 3.2255] | 3.4588 (n=1) [3.4588, 3.4588] | 3.3067 (n=1) [3.3067, 3.3067] | -7.23% | -2.52% |
| Whole-host CPU (%) | 10.469 (n=1) [10.469, 10.469] | 9.448 (n=1) [9.448, 9.448] | 9.055 (n=1) [9.055, 9.055] | 9.76% | 13.51% |
| Baseline whole-host CPU (%) | 8.2699 (n=1) [8.2699, 8.2699] | 7.5011 (n=1) [7.5011, 7.5011] | 7.3804 (n=1) [7.3804, 7.3804] | 9.30% | 10.76% |
| Experiment sampled peak RSS (MiB) | 3481 (n=1) [3481, 3481] | 3477.8 (n=1) [3477.8, 3477.8] | 3459.8 (n=1) [3459.8, 3459.8] | 0.09% | 0.61% |
| Experiment sampled peak PSS (MiB) | 3441.2 (n=1) [3441.2, 3441.2] | 3437.8 (n=1) [3437.8, 3437.8] | 3419.5 (n=1) [3419.5, 3419.5] | 0.10% | 0.63% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5475.2 (n=1) [5475.2, 5475.2] | 5434 (n=1) [5434, 5434] | 5466.8 (n=1) [5466.8, 5466.8] | 0.75% | 0.15% |
| GPU device utilization (%) | 52.854 (n=1) [52.854, 52.854] | 52.558 (n=1) [52.558, 52.558] | 50.152 (n=1) [50.152, 50.152] | 0.56% | 5.11% |
| GPU device utilization p95 (%) | 58 (n=1) [58, 58] | 57 (n=1) [57, 57] | 55 (n=1) [55, 55] | 1.72% | 5.17% |
| GPU device memory-controller utilization (%) | 19.244 (n=1) [19.244, 19.244] | 19.481 (n=1) [19.481, 19.481] | 19.109 (n=1) [19.109, 19.109] | -1.23% | 0.70% |
| GPU device memory (MiB) | 1274.2 (n=1) [1274.2, 1274.2] | 1270.1 (n=1) [1270.1, 1270.1] | 1272.5 (n=1) [1272.5, 1272.5] | 0.33% | 0.14% |
| GPU device power (W; not flight attribution) | 18.707 (n=1) [18.707, 18.707] | 18.717 (n=1) [18.717, 18.717] | 18.795 (n=1) [18.795, 18.795] | -0.05% | -0.47% |
| Observed source frame records | 409 (n=1) [409, 409] | 523 (n=1) [523, 523] | 451 (n=1) [451, 451] | -27.87% | -10.27% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 271.4 (n=1) [271.4, 271.4] | 75.00% | 69.84% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.4154e+05 (n=1) [2.4154e+05, 2.4154e+05] | 75.00% | 69.84% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 34739 (n=1) [34739, 34739] | 75.00% | 69.84% |
| Observed source generated points (/frame) | 36170 (n=1) [36170, 36170] | 10492 (n=1) [10492, 10492] | 11956 (n=1) [11956, 11956] | 70.99% | 66.95% |
| Observed source cloud payload (bytes/frame) | 1.1574e+06 (n=1) [1.1574e+06, 1.1574e+06] | 3.3575e+05 (n=1) [3.3575e+05, 3.3575e+05] | 3.8258e+05 (n=1) [3.8258e+05, 3.8258e+05] | 70.99% | 66.95% |
| Map total elapsed mean (ms/frame) | 35.596 (n=1) [35.596, 35.596] | 10.598 (n=1) [10.598, 10.598] | 12.628 (n=1) [12.628, 12.628] | 70.23% | 64.52% |
| Map total elapsed p95 (ms/frame) | 43.649 (n=1) [43.649, 43.649] | 17.064 (n=1) [17.064, 17.064] | 24.82 (n=1) [24.82, 24.82] | 60.91% | 43.14% |
| Map total elapsed max (ms/frame) | 150.44 (n=1) [150.44, 150.44] | 67.445 (n=1) [67.445, 67.445] | 37.676 (n=1) [37.676, 37.676] | 55.17% | 74.96% |
| Map raycast elapsed mean (ms/frame) | 22.557 (n=1) [22.557, 22.557] | 7.2366 (n=1) [7.2366, 7.2366] | 8.5702 (n=1) [8.5702, 8.5702] | 67.92% | 62.01% |
| Map update elapsed mean (ms/frame) | 13.037 (n=1) [13.037, 13.037] | 3.3602 (n=1) [3.3602, 3.3602] | 4.0565 (n=1) [4.0565, 4.0565] | 74.23% | 68.88% |
| Map inflation elapsed mean (ms/frame; nested) | 2.5015 (n=1) [2.5015, 2.5015] | 0.9095 (n=1) [0.9095, 0.9095] | 1.0115 (n=1) [1.0115, 1.0115] | 63.64% | 59.56% |
| Map processed frames / mission time (Hz proxy) | 10.318 (n=1) [10.318, 10.318] | 10.297 (n=1) [10.297, 10.297] | 10.257 (n=1) [10.257, 10.257] | 0.20% | 0.59% |
| Trajectory commits (Hz) | 5.3934 (n=1) [5.3934, 5.3934] | 4.8501 (n=1) [4.8501, 4.8501] | 5.269 (n=1) [5.269, 5.269] | 10.07% | 2.31% |
| Goal retransmissions coalesced | 31 (n=1) [31, 31] | 31 (n=1) [31, 31] | 31 (n=1) [31, 31] | 0.00% | 0.00% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.019804 (n=1) [0.019804, 0.019804] | 0.020737 (n=1) [0.020737, 0.020737] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.162 (n=1) [0.162, 0.162] | 0.175 (n=1) [0.175, 0.175] | N/A | N/A |
| Map points mean (/frame) | 36170 (n=1) [36170, 36170] | 10492 (n=1) [10492, 10492] | 11956 (n=1) [11956, 11956] | 70.99% | 66.95% |
| Map points / mission time (points/s proxy) | 3.732e+05 (n=1) [3.732e+05, 3.732e+05] | 1.0804e+05 (n=1) [1.0804e+05, 1.0804e+05] | 1.2263e+05 (n=1) [1.2263e+05, 1.2263e+05] | 71.05% | 67.14% |
| Map payload / mission time (MiB/s proxy, logical edge) | 11.389 (n=1) [11.389, 11.389] | 3.2972 (n=1) [3.2972, 3.2972] | 3.7423 (n=1) [3.7423, 3.7423] | 71.05% | 67.14% |
| Sensor report payload (MiB/s, logical edge; own span) | 11.109 (n=1) [11.109, 11.109] | 3.2159 (n=1) [3.2159, 3.2159] | 3.6614 (n=1) [3.6614, 3.6614] | 71.05% | 67.04% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 11.389 (n=1) [11.389, 11.389] | 3.2972 (n=1) [3.2972, 3.2972] | 3.7423 (n=1) [3.7423, 3.7423] | 71.05% | 67.14% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.003 (n=1) [10.003, 10.003] | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | 0.02% | 0.03% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100.01 (n=1) [100.01, 100.01] | -0.00% | -0.01% |
| Received command frequency (Hz; holds included) | 94.133 (n=1) [94.133, 94.133] | 94.449 (n=1) [94.449, 94.449] | 93.957 (n=1) [93.957, 93.957] | -0.34% | 0.19% |
| Odometry receipt p99 gap (ms) | 10.568 (n=1) [10.568, 10.568] | 10.712 (n=1) [10.712, 10.712] | 10.997 (n=1) [10.997, 10.997] | -1.36% | -4.06% |
| Odometry receipt max gap (ms) | 10.952 (n=1) [10.952, 10.952] | 17.182 (n=1) [17.182, 17.182] | 12.778 (n=1) [12.778, 12.778] | -56.88% | -16.67% |
| Actual FSM main callback frequency (profiled only) | 99.998 (n=1) [99.998, 99.998] | 99.464 (n=1) [99.464, 99.464] | 99.77 (n=1) [99.77, 99.77] | 0.53% | 0.23% |
| Actual FSM command callback frequency (profiled only) | 99.998 (n=1) [99.998, 99.998] | 99.998 (n=1) [99.998, 99.998] | 99.998 (n=1) [99.998, 99.998] | 0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 4 (n=1) [4, 4] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 7.029 (n=1) [7.029, 7.029] | N/A | N/A |
| Guard active duration (s) | 0.96972 (n=1) [0.96972, 0.96972] | 8.3614 (n=1) [8.3614, 8.3614] | 3.2925 (n=1) [3.2925, 3.2925] | -762.25% | -239.53% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration04/preflight/seed1/r01_run14000/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.2371e-05 | 2.27169e-05 |
| frontend_cloud / 0 | N/A | 0.000129232 | 0.000112898 |
| frontend_enqueue / 0 | N/A | 5.35487e-05 | 4.73791e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.55031e-05 |
| frontend_odom / 0 | N/A | 0.000468913 | 0.000555989 |
| frontend_replan_status / 0 | N/A | N/A | 1.42781e-05 |
| frontend_report / 0 | N/A | 1.61078e-05 | 1.74372e-05 |
| frontend_stats / 0 | N/A | 0.000891672 | 0.000961854 |
| fsm_command_callback / 0 | 0.00941424 | 0.00769542 | 0.00998478 |
| fsm_main_callback / 0 | 0.000595346 | 0.000623087 | 0.000687969 |
| fsm_main_core / 0 | 0.000383282 | 0.000382857 | 0.000408663 |
| fsm_poly_publish / 0 | 4.12505e-05 | 3.75085e-05 | 4.04807e-05 |
| fsm_replan_callback / 0 | 0.000303124 | 0.000304969 | 0.000322308 |
| fsm_replan_core / 0 | 0.000289867 | 0.000282256 | 0.000310843 |
| guard_brake / 0 | N/A | 3.94791e-06 | 0 |
| guard_certificate / 0 | 0.00120563 | 0.00107691 | 0.00126142 |
| guard_recover / 0 | N/A | 6.67856e-06 | 0 |
| map_ack_and_log / 0 | 0.000747035 | 0.00121806 | 0.00130833 |
| map_cloud_enqueue / 0 | 6.2592e-05 | 8.37806e-05 | 9.65806e-05 |
| map_odom_callback / 0 | 0.00104671 | 0.00103623 | 0.000972326 |
| map_prob_update / 0 | 0.242563 | 0.0959884 | 0.0902965 |
| map_ros_to_pcl / 0 | 0.00417727 | 0.000966164 | 0.000906652 |
| map_snapshot_commit_health / 0 | 0.0499505 | 0.0203749 | 0.0203666 |
| map_worker / 0 | 8.00567e-05 | 7.1353e-05 | 6.31748e-05 |
| planner_backup_optimize / 0 | 0.0282487 | 0.0225686 | 0.0185377 |
| planner_commit / 0 | 0.000458936 | 0.000412267 | 0.000427327 |
| planner_corridor_search / 0 | 0.00930106 | 0.0106196 | 0.0100774 |
| planner_exp_optimize / 0 | 0.062035 | 0.0515467 | 0.0521551 |
| planner_generate_backup / 0 | 0.0177546 | 0.0156541 | 0.0167124 |
| planner_generate_exp / 0 | 0.000466321 | 0.000493578 | 0.000490068 |
| planner_path_search / 0 | 0.0116018 | 0.0190867 | 0.0145192 |
| planner_stop_viability / 0 | 0.000368541 | 0.000357288 | 0.000406947 |
| planner_validate_geometry / 0 | 0.0046876 | 0.00466501 | 0.00525358 |
| planner_velocity_extrema / 0 | 0.000111922 | 0.000100913 | 0.000102907 |
| planner_visualize_path / 0 | 0.000561135 | 0.000470251 | 0.000648103 |
| sim_odom_callback / 0 | 0.00923686 | 0.0123207 | 0.0100048 |
| sim_render_callback / 0 | 0.0433323 | 0.0165322 | 0.0153596 |

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration04/preflight/seed3/r01_run14001/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 2.71338e-05 | 2.30372e-05 |
| frontend_cloud / 0 | N/A | 0.00012269 | 0.000113257 |
| frontend_enqueue / 0 | N/A | 4.70246e-05 | 5.35275e-05 |
| frontend_guard_status / 0 | N/A | N/A | 6.2254e-06 |
| frontend_map_ack / 0 | N/A | N/A | 1.77265e-05 |
| frontend_odom / 0 | N/A | 0.000433167 | 0.00056197 |
| frontend_replan_status / 0 | N/A | N/A | 1.05e-05 |
| frontend_report / 0 | N/A | 1.35703e-05 | 1.41467e-05 |
| frontend_stats / 0 | N/A | 0.000751753 | 0.000826914 |
| fsm_command_callback / 0 | 0.0062412 | 0.0101516 | 0.00960841 |
| fsm_main_callback / 0 | 0.000509232 | 0.000643959 | 0.000629048 |
| fsm_main_core / 0 | 0.00033707 | 0.000363705 | 0.000364707 |
| fsm_poly_publish / 0 | 3.70258e-05 | 3.4691e-05 | 3.88566e-05 |
| fsm_replan_callback / 0 | 0.000251683 | 0.000285591 | 0.000304661 |
| fsm_replan_core / 0 | 0.000242005 | 0.000249993 | 0.000327538 |
| guard_brake / 0 | 4.45033e-06 | 9.53415e-06 | 6.79512e-06 |
| guard_certificate / 0 | 0.000922857 | 0.00118143 | 0.00120064 |
| guard_recover / 0 | 1.55838e-05 | 1.73772e-05 | 9.70028e-06 |
| map_ack_and_log / 0 | 0.000754395 | 0.00127999 | 0.00135366 |
| map_cloud_enqueue / 0 | 5.64955e-05 | 7.48848e-05 | 7.18452e-05 |
| map_odom_callback / 0 | 0.00104078 | 0.000909445 | 0.000946669 |
| map_prob_update / 0 | 0.288861 | 0.107006 | 0.112997 |
| map_ros_to_pcl / 0 | 0.0052744 | 0.00137508 | 0.00152994 |
| map_snapshot_commit_health / 0 | 0.0539201 | 0.0228463 | 0.0243397 |
| map_worker / 0 | 7.66687e-05 | 6.98141e-05 | 6.76142e-05 |
| planner_backup_optimize / 0 | 0.0170946 | 0.0263773 | 0.0418596 |
| planner_commit / 0 | 0.000402836 | 0.00038431 | 0.000432941 |
| planner_corridor_search / 0 | 0.00854798 | 0.00930972 | 0.0113933 |
| planner_exp_optimize / 0 | 0.0457639 | 0.0524317 | 0.0518606 |
| planner_generate_backup / 0 | 0.0180057 | 0.016629 | 0.0174782 |
| planner_generate_exp / 0 | 0.000399097 | 0.000433132 | 0.000491315 |
| planner_path_search / 0 | 0.011135 | 0.0135048 | 0.0146221 |
| planner_stop_viability / 0 | 0.000319286 | 0.000354659 | 0.000401631 |
| planner_validate_geometry / 0 | 0.00441429 | 0.00449314 | 0.00466751 |
| planner_velocity_extrema / 0 | 0.000102954 | 9.37863e-05 | 9.82418e-05 |
| planner_visualize_path / 0 | 0.000369963 | 0.00061436 | 0.000576949 |
| sim_odom_callback / 0 | 0.0114213 | 0.00963382 | 0.00982452 |
| sim_render_callback / 0 | 0.0471064 | 0.0155391 | 0.0182125 |

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration04/preflight/seed5/r01_run14002/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.2053e-05 | 2.77298e-05 |
| frontend_cloud / 0 | N/A | 0.000120066 | 0.000109241 |
| frontend_enqueue / 0 | N/A | 4.74659e-05 | 4.87665e-05 |
| frontend_guard_status / 0 | N/A | N/A | 3.01749e-06 |
| frontend_map_ack / 0 | N/A | N/A | 1.58979e-05 |
| frontend_odom / 0 | N/A | 0.000462097 | 0.000573569 |
| frontend_replan_status / 0 | N/A | N/A | 1.11303e-05 |
| frontend_report / 0 | N/A | 1.16158e-05 | 1.00775e-05 |
| frontend_stats / 0 | N/A | 0.000635439 | 0.000854692 |
| fsm_command_callback / 0 | 0.00943835 | 0.00555477 | 0.00635422 |
| fsm_main_callback / 0 | 0.000553276 | 0.000565571 | 0.00056773 |
| fsm_main_core / 0 | 0.000362624 | 0.000353483 | 0.000388093 |
| fsm_poly_publish / 0 | 4.14254e-05 | 3.49949e-05 | 4.46606e-05 |
| fsm_replan_callback / 0 | 0.000273535 | 0.000296108 | 0.00031165 |
| fsm_replan_core / 0 | 0.000282699 | 0.000266241 | 0.000334441 |
| guard_brake / 0 | 2.59414e-06 | 5.72759e-05 | 1.96665e-05 |
| guard_certificate / 0 | 0.0011269 | 0.000897696 | 0.000988183 |
| guard_recover / 0 | 7.70029e-06 | 2.33742e-05 | 1.74606e-06 |
| map_ack_and_log / 0 | 0.000760551 | 0.00132851 | 0.00137808 |
| map_cloud_enqueue / 0 | 6.9173e-05 | 6.82434e-05 | 7.05723e-05 |
| map_odom_callback / 0 | 0.000931102 | 0.001089 | 0.00104067 |
| map_prob_update / 0 | 0.342752 | 0.107626 | 0.113857 |
| map_ros_to_pcl / 0 | 0.00684164 | 0.00148823 | 0.00153079 |
| map_snapshot_commit_health / 0 | 0.0591299 | 0.0236326 | 0.025593 |
| map_worker / 0 | 8.45169e-05 | 6.97117e-05 | 6.93292e-05 |
| planner_backup_optimize / 0 | 0.0442923 | 0.0270838 | 0.0341361 |
| planner_commit / 0 | 0.000450936 | 0.000402192 | 0.000437329 |
| planner_corridor_search / 0 | 0.00955521 | 0.0107459 | 0.0111008 |
| planner_exp_optimize / 0 | 0.0566852 | 0.0505627 | 0.0645024 |
| planner_generate_backup / 0 | 0.0196664 | 0.0157781 | 0.0173954 |
| planner_generate_exp / 0 | 0.000445611 | 0.000459402 | 0.000519453 |
| planner_path_search / 0 | 0.0188096 | 0.0229702 | 0.0161504 |
| planner_stop_viability / 0 | 0.000346108 | 0.000357186 | 0.000355737 |
| planner_validate_geometry / 0 | 0.00474867 | 0.00448654 | 0.00437258 |
| planner_velocity_extrema / 0 | 0.000118643 | 9.18685e-05 | 0.000104138 |
| planner_visualize_path / 0 | 0.000556186 | 0.00026574 | 0.000366922 |
| sim_odom_callback / 0 | 0.00716197 | 0.0132623 | 0.012857 |
| sim_render_callback / 0 | 0.0460089 | 0.0168309 | 0.0171928 |

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
