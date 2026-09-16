# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c22_iteration02_preflight — profiled_supplement

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
| Mission time (s) | 39.1 (n=1) [39.1, 39.1] | 40.89 (n=1) [40.89, 40.89] | 38.39 (n=1) [38.39, 38.39] | -4.58% | 1.82% |
| Path length (m) | 221.27 (n=1) [221.27, 221.27] | 225.21 (n=1) [225.21, 225.21] | 222.36 (n=1) [222.36, 222.36] | -1.78% | -0.49% |
| Minimum static-PC clearance (m) | 0.318 (n=1) [0.318, 0.318] | 0.313 (n=1) [0.313, 0.313] | 0.376 (n=1) [0.376, 0.376] | 1.57% | -18.24% |
| Experiment CPU (cores) | 0.5575 (n=1) [0.5575, 0.5575] | 0.36278 (n=1) [0.36278, 0.36278] | 0.36893 (n=1) [0.36893, 0.36893] | 34.93% | 33.82% |
| Experiment CPU (whole-host %) | 2.7875 (n=1) [2.7875, 2.7875] | 1.8139 (n=1) [1.8139, 1.8139] | 1.8447 (n=1) [1.8447, 1.8447] | 34.93% | 33.82% |
| Experiment measurement-window CPU (core-s) | 22.675 (n=1) [22.675, 22.675] | 15.543 (n=1) [15.543, 15.543] | 14.659 (n=1) [14.659, 14.659] | 31.45% | 35.35% |
| Accounting window (s) | 40.673 (n=1) [40.673, 40.673] | 42.843 (n=1) [42.843, 42.843] | 39.734 (n=1) [39.734, 39.734] | -5.34% | 2.31% |
| Experiment CPU 1 s p95 (cores) | 0.67188 (n=1) [0.67188, 0.67188] | 0.46494 (n=1) [0.46494, 0.46494] | 0.4652 (n=1) [0.4652, 0.4652] | 30.80% | 30.76% |
| Experiment CPU 1 s maximum (cores) | 0.7279 (n=1) [0.7279, 0.7279] | 0.49567 (n=1) [0.49567, 0.49567] | 0.56953 (n=1) [0.56953, 0.56953] | 31.90% | 21.76% |
| Composed runtime CPU (cores; includes simulator) | 0.51633 (n=1) [0.51633, 0.51633] | 0.32136 (n=1) [0.32136, 0.32136] | 0.32234 (n=1) [0.32234, 0.32234] | 37.76% | 37.57% |
| Composed runtime measurement-window CPU (core-s) | 21.001 (n=1) [21.001, 21.001] | 13.768 (n=1) [13.768, 13.768] | 12.808 (n=1) [12.808, 12.808] | 34.44% | 39.01% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.1022 (n=1) [4.1022, 4.1022] | 4.2758 (n=1) [4.2758, 4.2758] | 4.4578 (n=1) [4.4578, 4.4578] | -4.23% | -8.67% |
| Whole-host CPU (%) | 10.089 (n=1) [10.089, 10.089] | 9.2612 (n=1) [9.2612, 9.2612] | 9.4758 (n=1) [9.4758, 9.4758] | 8.21% | 6.08% |
| Baseline whole-host CPU (%) | 7.9629 (n=1) [7.9629, 7.9629] | 7.655 (n=1) [7.655, 7.655] | 5.771 (n=1) [5.771, 5.771] | 3.87% | 27.53% |
| Experiment sampled peak RSS (MiB) | 3385.3 (n=1) [3385.3, 3385.3] | 3380.7 (n=1) [3380.7, 3380.7] | 3377.4 (n=1) [3377.4, 3377.4] | 0.14% | 0.23% |
| Experiment sampled peak PSS (MiB) | 3345.3 (n=1) [3345.3, 3345.3] | 3340.7 (n=1) [3340.7, 3340.7] | 3337.1 (n=1) [3337.1, 3337.1] | 0.14% | 0.24% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5638.6 (n=1) [5638.6, 5638.6] | 5693 (n=1) [5693, 5693] | 5663.9 (n=1) [5663.9, 5663.9] | -0.96% | -0.45% |
| GPU device utilization (%) | 47.625 (n=1) [47.625, 47.625] | 49.302 (n=1) [49.302, 49.302] | 52.487 (n=1) [52.487, 52.487] | -3.52% | -10.21% |
| GPU device utilization p95 (%) | 52 (n=1) [52, 52] | 53 (n=1) [53, 53] | 57 (n=1) [57, 57] | -1.92% | -9.62% |
| GPU device memory-controller utilization (%) | 19.025 (n=1) [19.025, 19.025] | 19.07 (n=1) [19.07, 19.07] | 19.026 (n=1) [19.026, 19.026] | -0.24% | -0.00% |
| GPU device memory (MiB) | 1280.7 (n=1) [1280.7, 1280.7] | 1278.9 (n=1) [1278.9, 1278.9] | 1279.1 (n=1) [1279.1, 1279.1] | 0.14% | 0.12% |
| GPU device power (W; not flight attribution) | 18.731 (n=1) [18.731, 18.731] | 18.783 (n=1) [18.783, 18.783] | 18.706 (n=1) [18.706, 18.706] | -0.28% | 0.14% |
| Observed source frame records | 407 (n=1) [407, 407] | 428 (n=1) [428, 428] | 396 (n=1) [396, 396] | -5.16% | 2.70% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 245.45 (n=1) [245.45, 245.45] | 75.00% | 72.73% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1845e+05 (n=1) [2.1845e+05, 2.1845e+05] | 75.00% | 72.73% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31418 (n=1) [31418, 31418] | 75.00% | 72.73% |
| Observed source generated points (/frame) | 16327 (n=1) [16327, 16327] | 4797 (n=1) [4797, 4797] | 4705.1 (n=1) [4705.1, 4705.1] | 70.62% | 71.18% |
| Observed source cloud payload (bytes/frame) | 5.2246e+05 (n=1) [5.2246e+05, 5.2246e+05] | 1.535e+05 (n=1) [1.535e+05, 1.535e+05] | 1.5056e+05 (n=1) [1.5056e+05, 1.5056e+05] | 70.62% | 71.18% |
| Map total elapsed mean (ms/frame) | 26.334 (n=1) [26.334, 26.334] | 9.2313 (n=1) [9.2313, 9.2313] | 10.075 (n=1) [10.075, 10.075] | 64.95% | 61.74% |
| Map total elapsed p95 (ms/frame) | 35.944 (n=1) [35.944, 35.944] | 14.301 (n=1) [14.301, 14.301] | 15.524 (n=1) [15.524, 15.524] | 60.21% | 56.81% |
| Map total elapsed max (ms/frame) | 73.345 (n=1) [73.345, 73.345] | 23.222 (n=1) [23.222, 23.222] | 35.684 (n=1) [35.684, 35.684] | 68.34% | 51.35% |
| Map raycast elapsed mean (ms/frame) | 16.356 (n=1) [16.356, 16.356] | 6.1184 (n=1) [6.1184, 6.1184] | 6.5491 (n=1) [6.5491, 6.5491] | 62.59% | 59.96% |
| Map update elapsed mean (ms/frame) | 9.9763 (n=1) [9.9763, 9.9763] | 3.1115 (n=1) [3.1115, 3.1115] | 3.5243 (n=1) [3.5243, 3.5243] | 68.81% | 64.67% |
| Map inflation elapsed mean (ms/frame; nested) | 1.269 (n=1) [1.269, 1.269] | 0.6224 (n=1) [0.6224, 0.6224] | 0.69443 (n=1) [0.69443, 0.69443] | 50.95% | 45.28% |
| Map processed frames / mission time (Hz proxy) | 10.384 (n=1) [10.384, 10.384] | 10.467 (n=1) [10.467, 10.467] | 10.315 (n=1) [10.315, 10.315] | -0.80% | 0.66% |
| Trajectory commits (Hz) | 3.0688 (n=1) [3.0688, 3.0688] | 3.3462 (n=1) [3.3462, 3.3462] | 3.2895 (n=1) [3.2895, 3.2895] | -9.04% | -7.19% |
| Goal retransmissions coalesced | 32 (n=1) [32, 32] | 28 (n=1) [28, 28] | 34 (n=1) [34, 34] | 12.50% | -6.25% |
| Demand replan checks (latest cumulative report) | 585 (n=1) [585, 585] | 571 (n=1) [571, 571] | 508 (n=1) [508, 508] | 2.39% | 13.16% |
| Demand replans skipped (latest cumulative report) | 439 (n=1) [439, 439] | 406 (n=1) [406, 406] | 360 (n=1) [360, 360] | 7.52% | 18.00% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.028462 (n=1) [0.028462, 0.028462] | 0.019894 (n=1) [0.019894, 0.019894] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 1.123 (n=1) [1.123, 1.123] | 0.111 (n=1) [0.111, 0.111] | N/A | N/A |
| Map points mean (/frame) | 16344 (n=1) [16344, 16344] | 4797 (n=1) [4797, 4797] | 4705.1 (n=1) [4705.1, 4705.1] | 70.65% | 71.21% |
| Map points / mission time (points/s proxy) | 1.6971e+05 (n=1) [1.6971e+05, 1.6971e+05] | 50211 (n=1) [50211, 50211] | 48534 (n=1) [48534, 48534] | 70.41% | 71.40% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.179 (n=1) [5.179, 5.179] | 1.5323 (n=1) [1.5323, 1.5323] | 1.4812 (n=1) [1.4812, 1.4812] | 70.41% | 71.40% |
| Sensor report payload (MiB/s, logical edge; own span) | 5.0251 (n=1) [5.0251, 5.0251] | 1.5008 (n=1) [1.5008, 1.5008] | 1.5032 (n=1) [1.5032, 1.5032] | 70.13% | 70.09% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.179 (n=1) [5.179, 5.179] | 1.5323 (n=1) [1.5323, 1.5323] | 1.4812 (n=1) [1.4812, 1.4812] | 70.41% | 71.40% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 9.9992 (n=1) [9.9992, 9.9992] | 10.001 (n=1) [10.001, 10.001] | 9.9996 (n=1) [9.9996, 9.9996] | -0.01% | -0.00% |
| Received odometry frequency (Hz) | 99.991 (n=1) [99.991, 99.991] | 99.993 (n=1) [99.993, 99.993] | 99.992 (n=1) [99.992, 99.992] | -0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 94.637 (n=1) [94.637, 94.637] | 91.748 (n=1) [91.748, 91.748] | 94.292 (n=1) [94.292, 94.292] | 3.05% | 0.37% |
| Odometry receipt p99 gap (ms) | 10.655 (n=1) [10.655, 10.655] | 10.817 (n=1) [10.817, 10.817] | 10.813 (n=1) [10.813, 10.813] | -1.52% | -1.48% |
| Odometry receipt max gap (ms) | 15.077 (n=1) [15.077, 15.077] | 11.529 (n=1) [11.529, 11.529] | 11.255 (n=1) [11.255, 11.255] | 23.53% | 25.35% |
| Actual FSM main callback frequency (profiled only) | 99.792 (n=1) [99.792, 99.792] | 99.936 (n=1) [99.936, 99.936] | 99.994 (n=1) [99.994, 99.994] | -0.14% | -0.20% |
| Actual FSM command callback frequency (profiled only) | 99.992 (n=1) [99.992, 99.992] | 99.993 (n=1) [99.993, 99.993] | 99.994 (n=1) [99.994, 99.994] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.038 (n=1) [3.038, 3.038] | N/A | N/A |
| Guard active duration (s) | 1.3642 (n=1) [1.3642, 1.3642] | 2.1323 (n=1) [2.1323, 2.1323] | 1.2645 (n=1) [1.2645, 1.2645] | -56.31% | 7.31% |

## seed3 — c22_iteration02_preflight — profiled_supplement

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
| Mission time (s) | 37.47 (n=1) [37.47, 37.47] | 39.35 (n=1) [39.35, 39.35] | 39.56 (n=1) [39.56, 39.56] | -5.02% | -5.58% |
| Path length (m) | 221.18 (n=1) [221.18, 221.18] | 224.48 (n=1) [224.48, 224.48] | 222.01 (n=1) [222.01, 222.01] | -1.49% | -0.38% |
| Minimum static-PC clearance (m) | 0.384 (n=1) [0.384, 0.384] | 0.284 (n=1) [0.284, 0.284] | 0.303 (n=1) [0.303, 0.303] | 26.04% | 21.09% |
| Experiment CPU (cores) | 0.63254 (n=1) [0.63254, 0.63254] | 0.36872 (n=1) [0.36872, 0.36872] | 0.37205 (n=1) [0.37205, 0.37205] | 41.71% | 41.18% |
| Experiment CPU (whole-host %) | 3.1627 (n=1) [3.1627, 3.1627] | 1.8436 (n=1) [1.8436, 1.8436] | 1.8602 (n=1) [1.8602, 1.8602] | 41.71% | 41.18% |
| Experiment measurement-window CPU (core-s) | 24.518 (n=1) [24.518, 24.518] | 15.196 (n=1) [15.196, 15.196] | 15.321 (n=1) [15.321, 15.321] | 38.02% | 37.51% |
| Accounting window (s) | 38.762 (n=1) [38.762, 38.762] | 41.213 (n=1) [41.213, 41.213] | 41.18 (n=1) [41.18, 41.18] | -6.32% | -6.24% |
| Experiment CPU 1 s p95 (cores) | 0.82069 (n=1) [0.82069, 0.82069] | 0.4722 (n=1) [0.4722, 0.4722] | 0.56578 (n=1) [0.56578, 0.56578] | 42.46% | 31.06% |
| Experiment CPU 1 s maximum (cores) | 0.87468 (n=1) [0.87468, 0.87468] | 0.55515 (n=1) [0.55515, 0.55515] | 0.63912 (n=1) [0.63912, 0.63912] | 36.53% | 26.93% |
| Composed runtime CPU (cores; includes simulator) | 0.59263 (n=1) [0.59263, 0.59263] | 0.32775 (n=1) [0.32775, 0.32775] | 0.32758 (n=1) [0.32758, 0.32758] | 44.70% | 44.72% |
| Composed runtime measurement-window CPU (core-s) | 22.972 (n=1) [22.972, 22.972] | 13.508 (n=1) [13.508, 13.508] | 13.49 (n=1) [13.49, 13.49] | 41.20% | 41.28% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.4371 (n=1) [4.4371, 4.4371] | 2.9097 (n=1) [2.9097, 2.9097] | 2.8371 (n=1) [2.8371, 2.8371] | 34.42% | 36.06% |
| Whole-host CPU (%) | 11.895 (n=1) [11.895, 11.895] | 8.8873 (n=1) [8.8873, 8.8873] | 9.199 (n=1) [9.199, 9.199] | 25.29% | 22.67% |
| Baseline whole-host CPU (%) | 7.6137 (n=1) [7.6137, 7.6137] | 7.1429 (n=1) [7.1429, 7.1429] | 7.6628 (n=1) [7.6628, 7.6628] | 6.18% | -0.64% |
| Experiment sampled peak RSS (MiB) | 3446 (n=1) [3446, 3446] | 3444 (n=1) [3444, 3444] | 3430.7 (n=1) [3430.7, 3430.7] | 0.06% | 0.44% |
| Experiment sampled peak PSS (MiB) | 3405.8 (n=1) [3405.8, 3405.8] | 3404.1 (n=1) [3404.1, 3404.1] | 3390.6 (n=1) [3390.6, 3390.6] | 0.05% | 0.45% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5358.4 (n=1) [5358.4, 5358.4] | 5591.6 (n=1) [5591.6, 5591.6] | 5626.9 (n=1) [5626.9, 5626.9] | -4.35% | -5.01% |
| GPU device utilization (%) | 53.154 (n=1) [53.154, 53.154] | 49.659 (n=1) [49.659, 49.659] | 49.634 (n=1) [49.634, 49.634] | 6.58% | 6.62% |
| GPU device utilization p95 (%) | 57 (n=1) [57, 57] | 53 (n=1) [53, 53] | 56 (n=1) [56, 56] | 7.02% | 1.75% |
| GPU device memory-controller utilization (%) | 19.077 (n=1) [19.077, 19.077] | 19.049 (n=1) [19.049, 19.049] | 19.146 (n=1) [19.146, 19.146] | 0.15% | -0.36% |
| GPU device memory (MiB) | 1273.2 (n=1) [1273.2, 1273.2] | 1270.9 (n=1) [1270.9, 1270.9] | 1273 (n=1) [1273, 1273] | 0.18% | 0.02% |
| GPU device power (W; not flight attribution) | 18.714 (n=1) [18.714, 18.714] | 18.815 (n=1) [18.815, 18.815] | 18.757 (n=1) [18.757, 18.757] | -0.54% | -0.23% |
| Observed source frame records | 385 (n=1) [385, 385] | 410 (n=1) [410, 410] | 409 (n=1) [409, 409] | -6.49% | -6.23% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 244.8 (n=1) [244.8, 244.8] | 75.00% | 72.80% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1788e+05 (n=1) [2.1788e+05, 2.1788e+05] | 75.00% | 72.80% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31335 (n=1) [31335, 31335] | 75.00% | 72.80% |
| Observed source generated points (/frame) | 22184 (n=1) [22184, 22184] | 6550.2 (n=1) [6550.2, 6550.2] | 6293.6 (n=1) [6293.6, 6293.6] | 70.47% | 71.63% |
| Observed source cloud payload (bytes/frame) | 7.0989e+05 (n=1) [7.0989e+05, 7.0989e+05] | 2.0961e+05 (n=1) [2.0961e+05, 2.0961e+05] | 2.0139e+05 (n=1) [2.0139e+05, 2.0139e+05] | 70.47% | 71.63% |
| Map total elapsed mean (ms/frame) | 33.187 (n=1) [33.187, 33.187] | 10.596 (n=1) [10.596, 10.596] | 11.579 (n=1) [11.579, 11.579] | 68.07% | 65.11% |
| Map total elapsed p95 (ms/frame) | 45.033 (n=1) [45.033, 45.033] | 15.314 (n=1) [15.314, 15.314] | 16.313 (n=1) [16.313, 16.313] | 65.99% | 63.78% |
| Map total elapsed max (ms/frame) | 99.449 (n=1) [99.449, 99.449] | 23.816 (n=1) [23.816, 23.816] | 47.94 (n=1) [47.94, 47.94] | 76.05% | 51.79% |
| Map raycast elapsed mean (ms/frame) | 20.737 (n=1) [20.737, 20.737] | 6.9656 (n=1) [6.9656, 6.9656] | 7.5894 (n=1) [7.5894, 7.5894] | 66.41% | 63.40% |
| Map update elapsed mean (ms/frame) | 12.448 (n=1) [12.448, 12.448] | 3.6292 (n=1) [3.6292, 3.6292] | 3.9881 (n=1) [3.9881, 3.9881] | 70.84% | 67.96% |
| Map inflation elapsed mean (ms/frame; nested) | 1.8915 (n=1) [1.8915, 1.8915] | 0.80164 (n=1) [0.80164, 0.80164] | 0.87648 (n=1) [0.87648, 0.87648] | 57.62% | 53.66% |
| Map processed frames / mission time (Hz proxy) | 10.275 (n=1) [10.275, 10.275] | 10.419 (n=1) [10.419, 10.419] | 10.339 (n=1) [10.339, 10.339] | -1.41% | -0.62% |
| Trajectory commits (Hz) | 2.9548 (n=1) [2.9548, 2.9548] | 3.2529 (n=1) [3.2529, 3.2529] | 3.1411 (n=1) [3.1411, 3.1411] | -10.09% | -6.30% |
| Goal retransmissions coalesced | 30 (n=1) [30, 30] | 34 (n=1) [34, 34] | 35 (n=1) [35, 35] | -13.33% | -16.67% |
| Demand replan checks (latest cumulative report) | 515 (n=1) [515, 515] | 603 (n=1) [603, 603] | 577 (n=1) [577, 577] | -17.09% | -12.04% |
| Demand replans skipped (latest cumulative report) | 388 (n=1) [388, 388] | 428 (n=1) [428, 428] | 426 (n=1) [426, 426] | -10.31% | -9.79% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.020094 (n=1) [0.020094, 0.020094] | 0.019287 (n=1) [0.019287, 0.019287] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.096 (n=1) [0.096, 0.096] | 0.156 (n=1) [0.156, 0.156] | N/A | N/A |
| Map points mean (/frame) | 22184 (n=1) [22184, 22184] | 6550.2 (n=1) [6550.2, 6550.2] | 6293.6 (n=1) [6293.6, 6293.6] | 70.47% | 71.63% |
| Map points / mission time (points/s proxy) | 2.2794e+05 (n=1) [2.2794e+05, 2.2794e+05] | 68249 (n=1) [68249, 68249] | 65068 (n=1) [65068, 65068] | 70.06% | 71.45% |
| Map payload / mission time (MiB/s proxy, logical edge) | 6.9561 (n=1) [6.9561, 6.9561] | 2.0828 (n=1) [2.0828, 2.0828] | 1.9857 (n=1) [1.9857, 1.9857] | 70.06% | 71.45% |
| Sensor report payload (MiB/s, logical edge; own span) | 6.8097 (n=1) [6.8097, 6.8097] | 2.0128 (n=1) [2.0128, 2.0128] | 1.9329 (n=1) [1.9329, 1.9329] | 70.44% | 71.62% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 6.9561 (n=1) [6.9561, 6.9561] | 2.0828 (n=1) [2.0828, 2.0828] | 1.9857 (n=1) [1.9857, 1.9857] | 70.06% | 71.45% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 9.9997 (n=1) [9.9997, 9.9997] | 0.00% | 0.00% |
| Received odometry frequency (Hz) | 99.993 (n=1) [99.993, 99.993] | 99.996 (n=1) [99.996, 99.996] | 99.995 (n=1) [99.995, 99.995] | -0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 93.805 (n=1) [93.805, 93.805] | 92.992 (n=1) [92.992, 92.992] | 93.515 (n=1) [93.515, 93.515] | 0.87% | 0.31% |
| Odometry receipt p99 gap (ms) | 10.612 (n=1) [10.612, 10.612] | 10.835 (n=1) [10.835, 10.835] | 10.834 (n=1) [10.834, 10.834] | -2.10% | -2.09% |
| Odometry receipt max gap (ms) | 11.283 (n=1) [11.283, 11.283] | 11.393 (n=1) [11.393, 11.393] | 13.589 (n=1) [13.589, 13.589] | -0.97% | -20.44% |
| Actual FSM main callback frequency (profiled only) | 99.927 (n=1) [99.927, 99.927] | 99.853 (n=1) [99.853, 99.853] | 99.995 (n=1) [99.995, 99.995] | 0.07% | -0.07% |
| Actual FSM command callback frequency (profiled only) | 99.994 (n=1) [99.994, 99.994] | 99.996 (n=1) [99.996, 99.996] | 99.995 (n=1) [99.995, 99.995] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 2.97 (n=1) [2.97, 2.97] | N/A | N/A |
| Guard active duration (s) | 0.7677 (n=1) [0.7677, 0.7677] | 0.46463 (n=1) [0.46463, 0.46463] | 1.2264 (n=1) [1.2264, 1.2264] | 39.48% | -59.75% |

## seed5 — c22_iteration02_preflight — profiled_supplement

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
| Mission time (s) | 37.83 (n=1) [37.83, 37.83] | 41.44 (n=1) [41.44, 41.44] | 43.94 (n=1) [43.94, 43.94] | -9.54% | -16.15% |
| Path length (m) | 221.49 (n=1) [221.49, 221.49] | 223 (n=1) [223, 223] | 227.05 (n=1) [227.05, 227.05] | -0.68% | -2.51% |
| Minimum static-PC clearance (m) | 0.288 (n=1) [0.288, 0.288] | 0.283 (n=1) [0.283, 0.283] | 0.247 (n=1) [0.247, 0.247] | 1.74% | 14.24% |
| Experiment CPU (cores) | 0.65045 (n=1) [0.65045, 0.65045] | 0.39724 (n=1) [0.39724, 0.39724] | 0.42045 (n=1) [0.42045, 0.42045] | 38.93% | 35.36% |
| Experiment CPU (whole-host %) | 3.2522 (n=1) [3.2522, 3.2522] | 1.9862 (n=1) [1.9862, 1.9862] | 2.1023 (n=1) [2.1023, 2.1023] | 38.93% | 35.36% |
| Experiment measurement-window CPU (core-s) | 26.134 (n=1) [26.134, 26.134] | 17.245 (n=1) [17.245, 17.245] | 19.106 (n=1) [19.106, 19.106] | 34.01% | 26.89% |
| Accounting window (s) | 40.178 (n=1) [40.178, 40.178] | 43.412 (n=1) [43.412, 43.412] | 45.441 (n=1) [45.441, 45.441] | -8.05% | -13.10% |
| Experiment CPU 1 s p95 (cores) | 0.77223 (n=1) [0.77223, 0.77223] | 0.54417 (n=1) [0.54417, 0.54417] | 0.52105 (n=1) [0.52105, 0.52105] | 29.53% | 32.53% |
| Experiment CPU 1 s maximum (cores) | 0.79357 (n=1) [0.79357, 0.79357] | 0.54938 (n=1) [0.54938, 0.54938] | 0.58154 (n=1) [0.58154, 0.58154] | 30.77% | 26.72% |
| Composed runtime CPU (cores; includes simulator) | 0.60993 (n=1) [0.60993, 0.60993] | 0.35099 (n=1) [0.35099, 0.35099] | 0.37596 (n=1) [0.37596, 0.37596] | 42.45% | 38.36% |
| Composed runtime measurement-window CPU (core-s) | 24.506 (n=1) [24.506, 24.506] | 15.237 (n=1) [15.237, 15.237] | 17.084 (n=1) [17.084, 17.084] | 37.82% | 30.29% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 2.9089 (n=1) [2.9089, 2.9089] | 3.2367 (n=1) [3.2367, 3.2367] | 3.1806 (n=1) [3.1806, 3.1806] | -11.27% | -9.34% |
| Whole-host CPU (%) | 10.105 (n=1) [10.105, 10.105] | 9.0795 (n=1) [9.0795, 9.0795] | 9.1646 (n=1) [9.1646, 9.1646] | 10.15% | 9.30% |
| Baseline whole-host CPU (%) | 7.9007 (n=1) [7.9007, 7.9007] | 7.8234 (n=1) [7.8234, 7.8234] | 8.1463 (n=1) [8.1463, 8.1463] | 0.98% | -3.11% |
| Experiment sampled peak RSS (MiB) | 3481 (n=1) [3481, 3481] | 3472.4 (n=1) [3472.4, 3472.4] | 3474.6 (n=1) [3474.6, 3474.6] | 0.24% | 0.18% |
| Experiment sampled peak PSS (MiB) | 3440.7 (n=1) [3440.7, 3440.7] | 3432.4 (n=1) [3432.4, 3432.4] | 3434.3 (n=1) [3434.3, 3434.3] | 0.24% | 0.19% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5583.1 (n=1) [5583.1, 5583.1] | 5567.9 (n=1) [5567.9, 5567.9] | 5581.4 (n=1) [5581.4, 5581.4] | 0.27% | 0.03% |
| GPU device utilization (%) | 47.65 (n=1) [47.65, 47.65] | 54.651 (n=1) [54.651, 54.651] | 52.733 (n=1) [52.733, 52.733] | -14.69% | -10.67% |
| GPU device utilization p95 (%) | 51 (n=1) [51, 51] | 58 (n=1) [58, 58] | 59 (n=1) [59, 59] | -13.73% | -15.69% |
| GPU device memory-controller utilization (%) | 19.1 (n=1) [19.1, 19.1] | 19.116 (n=1) [19.116, 19.116] | 19.067 (n=1) [19.067, 19.067] | -0.09% | 0.17% |
| GPU device memory (MiB) | 1274.1 (n=1) [1274.1, 1274.1] | 1273.5 (n=1) [1273.5, 1273.5] | 1273.2 (n=1) [1273.2, 1273.2] | 0.05% | 0.07% |
| GPU device power (W; not flight attribution) | 18.77 (n=1) [18.77, 18.77] | 18.864 (n=1) [18.864, 18.864] | 18.81 (n=1) [18.81, 18.81] | -0.50% | -0.21% |
| Observed source frame records | 399 (n=1) [399, 399] | 430 (n=1) [430, 430] | 451 (n=1) [451, 451] | -7.77% | -13.03% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 274.39 (n=1) [274.39, 274.39] | 75.00% | 69.51% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.4421e+05 (n=1) [2.4421e+05, 2.4421e+05] | 75.00% | 69.51% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 35122 (n=1) [35122, 35122] | 75.00% | 69.51% |
| Observed source generated points (/frame) | 28449 (n=1) [28449, 28449] | 7851.2 (n=1) [7851.2, 7851.2] | 8942.9 (n=1) [8942.9, 8942.9] | 72.40% | 68.56% |
| Observed source cloud payload (bytes/frame) | 9.1036e+05 (n=1) [9.1036e+05, 9.1036e+05] | 2.5124e+05 (n=1) [2.5124e+05, 2.5124e+05] | 2.8617e+05 (n=1) [2.8617e+05, 2.8617e+05] | 72.40% | 68.56% |
| Map total elapsed mean (ms/frame) | 34.309 (n=1) [34.309, 34.309] | 11.671 (n=1) [11.671, 11.671] | 13.197 (n=1) [13.197, 13.197] | 65.98% | 61.53% |
| Map total elapsed p95 (ms/frame) | 43.447 (n=1) [43.447, 43.447] | 17.391 (n=1) [17.391, 17.391] | 25.566 (n=1) [25.566, 25.566] | 59.97% | 41.16% |
| Map total elapsed max (ms/frame) | 81.96 (n=1) [81.96, 81.96] | 29.992 (n=1) [29.992, 29.992] | 56.645 (n=1) [56.645, 56.645] | 63.41% | 30.89% |
| Map raycast elapsed mean (ms/frame) | 21.375 (n=1) [21.375, 21.375] | 7.8134 (n=1) [7.8134, 7.8134] | 8.7137 (n=1) [8.7137, 8.7137] | 63.45% | 59.23% |
| Map update elapsed mean (ms/frame) | 12.932 (n=1) [12.932, 12.932] | 3.8565 (n=1) [3.8565, 3.8565] | 4.482 (n=1) [4.482, 4.482] | 70.18% | 65.34% |
| Map inflation elapsed mean (ms/frame; nested) | 2.1073 (n=1) [2.1073, 2.1073] | 0.95564 (n=1) [0.95564, 0.95564] | 0.98529 (n=1) [0.98529, 0.98529] | 54.65% | 53.24% |
| Map processed frames / mission time (Hz proxy) | 10.521 (n=1) [10.521, 10.521] | 10.376 (n=1) [10.376, 10.376] | 10.264 (n=1) [10.264, 10.264] | 1.37% | 2.44% |
| Trajectory commits (Hz) | 3.17 (n=1) [3.17, 3.17] | 3.259 (n=1) [3.259, 3.259] | 3.2443 (n=1) [3.2443, 3.2443] | -2.81% | -2.34% |
| Goal retransmissions coalesced | 28 (n=1) [28, 28] | 30 (n=1) [30, 30] | 32 (n=1) [32, 32] | -7.14% | -14.29% |
| Demand replan checks (latest cumulative report) | 515 (n=1) [515, 515] | 577 (n=1) [577, 577] | 554 (n=1) [554, 554] | -12.04% | -7.57% |
| Demand replans skipped (latest cumulative report) | 380 (n=1) [380, 380] | 409 (n=1) [409, 409] | 388 (n=1) [388, 388] | -7.63% | -2.11% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.021498 (n=1) [0.021498, 0.021498] | 0.020079 (n=1) [0.020079, 0.020079] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.162 (n=1) [0.162, 0.162] | 0.153 (n=1) [0.153, 0.153] | N/A | N/A |
| Map points mean (/frame) | 28483 (n=1) [28483, 28483] | 7851.2 (n=1) [7851.2, 7851.2] | 8942.9 (n=1) [8942.9, 8942.9] | 72.44% | 68.60% |
| Map points / mission time (points/s proxy) | 2.9966e+05 (n=1) [2.9966e+05, 2.9966e+05] | 81468 (n=1) [81468, 81468] | 91790 (n=1) [91790, 91790] | 72.81% | 69.37% |
| Map payload / mission time (MiB/s proxy, logical edge) | 9.145 (n=1) [9.145, 9.145] | 2.4862 (n=1) [2.4862, 2.4862] | 2.8012 (n=1) [2.8012, 2.8012] | 72.81% | 69.37% |
| Sensor report payload (MiB/s, logical edge; own span) | 8.8521 (n=1) [8.8521, 8.8521] | 2.4853 (n=1) [2.4853, 2.4853] | 2.7384 (n=1) [2.7384, 2.7384] | 71.92% | 69.06% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 9.145 (n=1) [9.145, 9.145] | 2.4862 (n=1) [2.4862, 2.4862] | 2.8012 (n=1) [2.8012, 2.8012] | 72.81% | 69.37% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 0.00% | 0.00% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 99.997 (n=1) [99.997, 99.997] | 99.996 (n=1) [99.996, 99.996] | 0.01% | 0.01% |
| Received command frequency (Hz; holds included) | 95.089 (n=1) [95.089, 95.089] | 94.289 (n=1) [94.289, 94.289] | 94.002 (n=1) [94.002, 94.002] | 0.84% | 1.14% |
| Odometry receipt p99 gap (ms) | 10.615 (n=1) [10.615, 10.615] | 10.985 (n=1) [10.985, 10.985] | 10.805 (n=1) [10.805, 10.805] | -3.48% | -1.79% |
| Odometry receipt max gap (ms) | 10.961 (n=1) [10.961, 10.961] | 12.044 (n=1) [12.044, 12.044] | 11.45 (n=1) [11.45, 11.45] | -9.88% | -4.46% |
| Actual FSM main callback frequency (profiled only) | 99.964 (n=1) [99.964, 99.964] | 99.796 (n=1) [99.796, 99.796] | 99.825 (n=1) [99.825, 99.825] | 0.17% | 0.14% |
| Actual FSM command callback frequency (profiled only) | 99.997 (n=1) [99.997, 99.997] | 99.996 (n=1) [99.996, 99.996] | 99.997 (n=1) [99.997, 99.997] | 0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 5 (n=1) [5, 5] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 7.449 (n=1) [7.449, 7.449] | N/A | N/A |
| Guard active duration (s) | 0.90222 (n=1) [0.90222, 0.90222] | 2.3539 (n=1) [2.3539, 2.3539] | 3.2777 (n=1) [3.2777, 3.2777] | -160.91% | -263.29% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration02/preflight/seed1/r01_run10100/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.86322e-05 | 3.13341e-05 |
| frontend_cloud / 0 | N/A | 0.000127278 | 0.000112085 |
| frontend_enqueue / 0 | N/A | 5.35417e-05 | 5.07051e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.58389e-05 |
| frontend_odom / 0 | N/A | 0.000497649 | 0.000621473 |
| frontend_replan_status / 0 | N/A | N/A | 7.52503e-06 |
| frontend_report / 0 | N/A | 1.32261e-05 | 1.62475e-05 |
| frontend_stats / 0 | N/A | 0.000913005 | 0.00079873 |
| fsm_command_callback / 0 | 0.00754058 | 0.00730285 | 0.00706156 |
| fsm_main_callback / 0 | 0.000544668 | 0.000636634 | 0.000639203 |
| fsm_main_core / 0 | 0.000355064 | 0.000420441 | 0.000392328 |
| fsm_poly_publish / 0 | 2.46297e-05 | 2.26365e-05 | 2.5507e-05 |
| fsm_replan_callback / 0 | 0.000261816 | 0.000315621 | 0.000309593 |
| fsm_replan_core / 0 | 0.000142874 | 0.00016633 | 0.000200309 |
| guard_brake / 0 | 3.4119e-06 | 2.61629e-05 | 0 |
| guard_certificate / 0 | 0.00104702 | 0.00106681 | 0.00103591 |
| guard_recover / 0 | 1.66366e-05 | 8.96489e-06 | 0 |
| map_ack_and_log / 0 | 0.000744863 | 0.00121818 | 0.0013615 |
| map_cloud_enqueue / 0 | 5.94342e-05 | 7.28035e-05 | 7.72081e-05 |
| map_odom_callback / 0 | 0.00109274 | 0.00111847 | 0.00115445 |
| map_prob_update / 0 | 0.247378 | 0.0909064 | 0.0947888 |
| map_ros_to_pcl / 0 | 0.00491134 | 0.000996804 | 0.000907508 |
| map_snapshot_commit_health / 0 | 0.0487908 | 0.0199126 | 0.0212222 |
| map_worker / 0 | 7.56074e-05 | 6.63014e-05 | 7.07786e-05 |
| planner_backup_optimize / 0 | 0.012197 | 0.0179158 | 0.0129215 |
| planner_commit / 0 | 0.000240808 | 0.00026271 | 0.000266837 |
| planner_corridor_search / 0 | 0.00487412 | 0.00619523 | 0.00537728 |
| planner_exp_optimize / 0 | 0.0410127 | 0.0352791 | 0.0315559 |
| planner_generate_backup / 0 | 0.00816901 | 0.00955292 | 0.0103986 |
| planner_generate_exp / 0 | 0.000221632 | 0.000288835 | 0.000275223 |
| planner_path_search / 0 | 0.0115429 | 0.0156067 | 0.0116641 |
| planner_stop_viability / 0 | 0.000318407 | 0.000391789 | 0.000380117 |
| planner_validate_geometry / 0 | 0.00399622 | 0.00450657 | 0.00434709 |
| planner_velocity_extrema / 0 | 5.60716e-05 | 6.08095e-05 | 6.49101e-05 |
| planner_visualize_path / 0 | 0.000463843 | 0.000455399 | 0.000419185 |
| sim_odom_callback / 0 | 0.0110973 | 0.0136492 | 0.0131829 |
| sim_render_callback / 0 | 0.0431316 | 0.0194986 | 0.0170994 |

Source: `/root/super-sector-filter/results/c22_normal_five_20260916/iteration02/preflight/seed3/r01_run10101/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 2.81641e-05 | 2.90231e-05 |
| frontend_cloud / 0 | N/A | 0.000124846 | 0.000114195 |
| frontend_enqueue / 0 | N/A | 4.66132e-05 | 4.63696e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.53276e-05 |
| frontend_odom / 0 | N/A | 0.000459065 | 0.00057357 |
| frontend_replan_status / 0 | N/A | N/A | 7.51507e-06 |
| frontend_report / 0 | N/A | 1.38675e-05 | 1.7754e-05 |
| frontend_stats / 0 | N/A | 0.00081391 | 0.000914879 |
| fsm_command_callback / 0 | 0.00670265 | 0.00771183 | 0.00703373 |
| fsm_main_callback / 0 | 0.000545178 | 0.000614074 | 0.000623177 |
| fsm_main_core / 0 | 0.000352802 | 0.000365781 | 0.000390834 |
| fsm_poly_publish / 0 | 2.2692e-05 | 2.15008e-05 | 2.24649e-05 |
| fsm_replan_callback / 0 | 0.000262041 | 0.000306473 | 0.000309296 |
| fsm_replan_core / 0 | 0.000151245 | 0.000164609 | 0.000177416 |
| guard_brake / 0 | 7.92953e-06 | 2.27074e-05 | 0 |
| guard_certificate / 0 | 0.00101661 | 0.00110737 | 0.00122226 |
| guard_recover / 0 | 7.34946e-06 | 1.30046e-06 | 0 |
| map_ack_and_log / 0 | 0.000743997 | 0.00124534 | 0.00147778 |
| map_cloud_enqueue / 0 | 5.38475e-05 | 7.32798e-05 | 7.2131e-05 |
| map_odom_callback / 0 | 0.00106394 | 0.00101451 | 0.00090945 |
| map_prob_update / 0 | 0.322935 | 0.107112 | 0.10949 |
| map_ros_to_pcl / 0 | 0.00572512 | 0.00140766 | 0.00126363 |
| map_snapshot_commit_health / 0 | 0.0553536 | 0.023693 | 0.0243146 |
| map_worker / 0 | 9.48269e-05 | 6.86427e-05 | 6.99766e-05 |
| planner_backup_optimize / 0 | 0.0152698 | 0.0133922 | 0.0181599 |
| planner_commit / 0 | 0.000255654 | 0.000262979 | 0.000243139 |
| planner_corridor_search / 0 | 0.00515167 | 0.00628302 | 0.00566141 |
| planner_exp_optimize / 0 | 0.0364299 | 0.0386965 | 0.033876 |
| planner_generate_backup / 0 | 0.0117543 | 0.00956984 | 0.00898258 |
| planner_generate_exp / 0 | 0.00023842 | 0.00027942 | 0.000241055 |
| planner_path_search / 0 | 0.0117624 | 0.0145024 | 0.012355 |
| planner_stop_viability / 0 | 0.000332869 | 0.000353608 | 0.000387033 |
| planner_validate_geometry / 0 | 0.00438807 | 0.00412519 | 0.00424801 |
| planner_velocity_extrema / 0 | 6.56535e-05 | 5.85395e-05 | 5.64493e-05 |
| planner_visualize_path / 0 | 0.000418299 | 0.000482052 | 0.00043495 |
| sim_odom_callback / 0 | 0.0115668 | 0.0120212 | 0.0123643 |
| sim_render_callback / 0 | 0.0444367 | 0.0157193 | 0.0198151 |

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
