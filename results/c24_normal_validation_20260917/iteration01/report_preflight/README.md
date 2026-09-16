# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c24_iteration01 — profiled_supplement

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
| Mission time (s) | 38.16 (n=1) [38.16, 38.16] | 38.72 (n=1) [38.72, 38.72] | 39.69 (n=1) [39.69, 39.69] | -1.47% | -4.01% |
| Path length (m) | 224.41 (n=1) [224.41, 224.41] | 224.38 (n=1) [224.38, 224.38] | 224.94 (n=1) [224.94, 224.94] | 0.01% | -0.24% |
| Minimum static-PC clearance (m) | 0.323 (n=1) [0.323, 0.323] | 0.374 (n=1) [0.374, 0.374] | 0.335 (n=1) [0.335, 0.335] | -15.79% | -3.72% |
| Experiment CPU (cores) | 0.60703 (n=1) [0.60703, 0.60703] | 0.38788 (n=1) [0.38788, 0.38788] | 0.39474 (n=1) [0.39474, 0.39474] | 36.10% | 34.97% |
| Experiment CPU (whole-host %) | 3.0352 (n=1) [3.0352, 3.0352] | 1.9394 (n=1) [1.9394, 1.9394] | 1.9737 (n=1) [1.9737, 1.9737] | 36.10% | 34.97% |
| Experiment measurement-window CPU (core-s) | 24.064 (n=1) [24.064, 24.064] | 15.781 (n=1) [15.781, 15.781] | 16.472 (n=1) [16.472, 16.472] | 34.42% | 31.55% |
| Accounting window (s) | 39.642 (n=1) [39.642, 39.642] | 40.686 (n=1) [40.686, 40.686] | 41.73 (n=1) [41.73, 41.73] | -2.63% | -5.27% |
| Experiment CPU 1 s p95 (cores) | 0.79175 (n=1) [0.79175, 0.79175] | 0.47681 (n=1) [0.47681, 0.47681] | 0.47185 (n=1) [0.47185, 0.47185] | 39.78% | 40.40% |
| Experiment CPU 1 s maximum (cores) | 0.82515 (n=1) [0.82515, 0.82515] | 0.48303 (n=1) [0.48303, 0.48303] | 0.53145 (n=1) [0.53145, 0.53145] | 41.46% | 35.59% |
| Composed runtime CPU (cores; includes simulator) | 0.56576 (n=1) [0.56576, 0.56576] | 0.34207 (n=1) [0.34207, 0.34207] | 0.35071 (n=1) [0.35071, 0.35071] | 39.54% | 38.01% |
| Composed runtime measurement-window CPU (core-s) | 22.428 (n=1) [22.428, 22.428] | 13.917 (n=1) [13.917, 13.917] | 14.635 (n=1) [14.635, 14.635] | 37.95% | 34.75% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.1538 (n=1) [4.1538, 4.1538] | 4.1211 (n=1) [4.1211, 4.1211] | 4.1224 (n=1) [4.1224, 4.1224] | 0.79% | 0.76% |
| Whole-host CPU (%) | 9.9928 (n=1) [9.9928, 9.9928] | 9.6359 (n=1) [9.6359, 9.6359] | 9.5417 (n=1) [9.5417, 9.5417] | 3.57% | 4.51% |
| Baseline whole-host CPU (%) | 8.0415 (n=1) [8.0415, 8.0415] | 7.4288 (n=1) [7.4288, 7.4288] | 7.0117 (n=1) [7.0117, 7.0117] | 7.62% | 12.81% |
| Experiment sampled peak RSS (MiB) | 3387.2 (n=1) [3387.2, 3387.2] | 3384.8 (n=1) [3384.8, 3384.8] | 3381.9 (n=1) [3381.9, 3381.9] | 0.07% | 0.16% |
| Experiment sampled peak PSS (MiB) | 3348.1 (n=1) [3348.1, 3348.1] | 3345.4 (n=1) [3345.4, 3345.4] | 3342.7 (n=1) [3342.7, 3342.7] | 0.08% | 0.16% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5506.9 (n=1) [5506.9, 5506.9] | 5534.1 (n=1) [5534.1, 5534.1] | 5550.1 (n=1) [5550.1, 5550.1] | -0.49% | -0.79% |
| GPU device utilization (%) | 49.846 (n=1) [49.846, 49.846] | 47.293 (n=1) [47.293, 47.293] | 52.951 (n=1) [52.951, 52.951] | 5.12% | -6.23% |
| GPU device utilization p95 (%) | 55 (n=1) [55, 55] | 50 (n=1) [50, 50] | 58 (n=1) [58, 58] | 9.09% | -5.45% |
| GPU device memory-controller utilization (%) | 19 (n=1) [19, 19] | 19.098 (n=1) [19.098, 19.098] | 18.976 (n=1) [18.976, 18.976] | -0.51% | 0.13% |
| GPU device memory (MiB) | 1259 (n=1) [1259, 1259] | 1258.4 (n=1) [1258.4, 1258.4] | 1257.2 (n=1) [1257.2, 1257.2] | 0.05% | 0.14% |
| GPU device power (W; not flight attribution) | 18.678 (n=1) [18.678, 18.678] | 18.672 (n=1) [18.672, 18.672] | 18.656 (n=1) [18.656, 18.656] | 0.03% | 0.12% |
| Observed source frame records | 396 (n=1) [396, 396] | 406 (n=1) [406, 406] | 416 (n=1) [416, 416] | -2.53% | -5.05% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 229.87 (n=1) [229.87, 229.87] | 75.00% | 74.46% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.0458e+05 (n=1) [2.0458e+05, 2.0458e+05] | 75.00% | 74.46% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 29423 (n=1) [29423, 29423] | 75.00% | 74.46% |
| Observed source generated points (/frame) | 16356 (n=1) [16356, 16356] | 4484.2 (n=1) [4484.2, 4484.2] | 4661.7 (n=1) [4661.7, 4661.7] | 72.58% | 71.50% |
| Observed source cloud payload (bytes/frame) | 5.234e+05 (n=1) [5.234e+05, 5.234e+05] | 1.4349e+05 (n=1) [1.4349e+05, 1.4349e+05] | 1.4917e+05 (n=1) [1.4917e+05, 1.4917e+05] | 72.58% | 71.50% |
| Map total elapsed mean (ms/frame) | 25.868 (n=1) [25.868, 25.868] | 10.072 (n=1) [10.072, 10.072] | 9.0133 (n=1) [9.0133, 9.0133] | 61.06% | 65.16% |
| Map total elapsed p95 (ms/frame) | 33.935 (n=1) [33.935, 33.935] | 14.828 (n=1) [14.828, 14.828] | 13.914 (n=1) [13.914, 13.914] | 56.30% | 59.00% |
| Map total elapsed max (ms/frame) | 56.995 (n=1) [56.995, 56.995] | 29.084 (n=1) [29.084, 29.084] | 37.95 (n=1) [37.95, 37.95] | 48.97% | 33.42% |
| Map raycast elapsed mean (ms/frame) | 15.713 (n=1) [15.713, 15.713] | 6.7044 (n=1) [6.7044, 6.7044] | 5.7844 (n=1) [5.7844, 5.7844] | 57.33% | 63.19% |
| Map update elapsed mean (ms/frame) | 10.154 (n=1) [10.154, 10.154] | 3.3662 (n=1) [3.3662, 3.3662] | 3.2274 (n=1) [3.2274, 3.2274] | 66.85% | 68.22% |
| Map inflation elapsed mean (ms/frame; nested) | 1.3579 (n=1) [1.3579, 1.3579] | 0.67412 (n=1) [0.67412, 0.67412] | 0.65158 (n=1) [0.65158, 0.65158] | 50.35% | 52.01% |
| Map processed frames / mission time (Hz proxy) | 10.377 (n=1) [10.377, 10.377] | 10.486 (n=1) [10.486, 10.486] | 10.481 (n=1) [10.481, 10.481] | -1.04% | -1.00% |
| Trajectory commits (Hz) | 5.4138 (n=1) [5.4138, 5.4138] | 5.4478 (n=1) [5.4478, 5.4478] | 5.36 (n=1) [5.36, 5.36] | -0.63% | 0.99% |
| Goal retransmissions coalesced | 29 (n=1) [29, 29] | 27 (n=1) [27, 27] | 32 (n=1) [32, 32] | 6.90% | -10.34% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.022284 (n=1) [0.022284, 0.022284] | 0.018096 (n=1) [0.018096, 0.018096] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.079 (n=1) [0.079, 0.079] | 0.15 (n=1) [0.15, 0.15] | N/A | N/A |
| Map points mean (/frame) | 16356 (n=1) [16356, 16356] | 4484.2 (n=1) [4484.2, 4484.2] | 4661.7 (n=1) [4661.7, 4661.7] | 72.58% | 71.50% |
| Map points / mission time (points/s proxy) | 1.6973e+05 (n=1) [1.6973e+05, 1.6973e+05] | 47019 (n=1) [47019, 47019] | 48860 (n=1) [48860, 48860] | 72.30% | 71.21% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.1799 (n=1) [5.1799, 5.1799] | 1.4349 (n=1) [1.4349, 1.4349] | 1.4911 (n=1) [1.4911, 1.4911] | 72.30% | 71.21% |
| Sensor report payload (MiB/s, logical edge; own span) | 5.1067 (n=1) [5.1067, 5.1067] | 1.3851 (n=1) [1.3851, 1.3851] | 1.465 (n=1) [1.465, 1.465] | 72.88% | 71.31% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.1799 (n=1) [5.1799, 5.1799] | 1.4349 (n=1) [1.4349, 1.4349] | 1.4911 (n=1) [1.4911, 1.4911] | 72.30% | 71.21% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | -0.00% | 0.00% |
| Received odometry frequency (Hz) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.724 (n=1) [94.724, 94.724] | 93.161 (n=1) [93.161, 93.161] | 94.585 (n=1) [94.585, 94.585] | 1.65% | 0.15% |
| Odometry receipt p99 gap (ms) | 10.642 (n=1) [10.642, 10.642] | 10.893 (n=1) [10.893, 10.893] | 10.74 (n=1) [10.74, 10.74] | -2.36% | -0.92% |
| Odometry receipt max gap (ms) | 11.016 (n=1) [11.016, 11.016] | 12.051 (n=1) [12.051, 12.051] | 13.703 (n=1) [13.703, 13.703] | -9.39% | -24.38% |
| Actual FSM main callback frequency (profiled only) | 100 (n=1) [100, 100] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Actual FSM command callback frequency (profiled only) | 100 (n=1) [100, 100] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 1 (n=1) [1, 1] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 0.723 (n=1) [0.723, 0.723] | N/A | N/A |
| Guard active duration (s) | 0.03574 (n=1) [0.03574, 0.03574] | 1.7099 (n=1) [1.7099, 1.7099] | 0.36987 (n=1) [0.36987, 0.36987] | -4684.19% | -934.89% |

## seed3 — c24_iteration01 — profiled_supplement

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
| Mission time (s) | 38.08 (n=1) [38.08, 38.08] | 39.3 (n=1) [39.3, 39.3] | 40.29 (n=1) [40.29, 40.29] | -3.20% | -5.80% |
| Path length (m) | 223.94 (n=1) [223.94, 223.94] | 225.51 (n=1) [225.51, 225.51] | 223.35 (n=1) [223.35, 223.35] | -0.70% | 0.26% |
| Minimum static-PC clearance (m) | 0.331 (n=1) [0.331, 0.331] | 0.325 (n=1) [0.325, 0.325] | 0.284 (n=1) [0.284, 0.284] | 1.81% | 14.20% |
| Experiment CPU (cores) | 0.66677 (n=1) [0.66677, 0.66677] | 0.40238 (n=1) [0.40238, 0.40238] | 0.43615 (n=1) [0.43615, 0.43615] | 39.65% | 34.59% |
| Experiment CPU (whole-host %) | 3.3338 (n=1) [3.3338, 3.3338] | 2.0119 (n=1) [2.0119, 2.0119] | 2.1808 (n=1) [2.1808, 2.1808] | 39.65% | 34.59% |
| Experiment measurement-window CPU (core-s) | 26.48 (n=1) [26.48, 26.48] | 16.825 (n=1) [16.825, 16.825] | 18.249 (n=1) [18.249, 18.249] | 36.46% | 31.08% |
| Accounting window (s) | 39.714 (n=1) [39.714, 39.714] | 41.813 (n=1) [41.813, 41.813] | 41.84 (n=1) [41.84, 41.84] | -5.29% | -5.35% |
| Experiment CPU 1 s p95 (cores) | 0.83353 (n=1) [0.83353, 0.83353] | 0.49777 (n=1) [0.49777, 0.49777] | 0.52204 (n=1) [0.52204, 0.52204] | 40.28% | 37.37% |
| Experiment CPU 1 s maximum (cores) | 0.98186 (n=1) [0.98186, 0.98186] | 0.51568 (n=1) [0.51568, 0.51568] | 0.63454 (n=1) [0.63454, 0.63454] | 47.48% | 35.37% |
| Composed runtime CPU (cores; includes simulator) | 0.62664 (n=1) [0.62664, 0.62664] | 0.35722 (n=1) [0.35722, 0.35722] | 0.38843 (n=1) [0.38843, 0.38843] | 42.99% | 38.01% |
| Composed runtime measurement-window CPU (core-s) | 24.886 (n=1) [24.886, 24.886] | 14.936 (n=1) [14.936, 14.936] | 16.252 (n=1) [16.252, 16.252] | 39.98% | 34.69% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.3988 (n=1) [4.3988, 4.3988] | 4.5657 (n=1) [4.5657, 4.5657] | 4.26 (n=1) [4.26, 4.26] | -3.79% | 3.16% |
| Whole-host CPU (%) | 10.792 (n=1) [10.792, 10.792] | 8.8986 (n=1) [8.8986, 8.8986] | 9.9655 (n=1) [9.9655, 9.9655] | 17.54% | 7.66% |
| Baseline whole-host CPU (%) | 7.4861 (n=1) [7.4861, 7.4861] | 8.0158 (n=1) [8.0158, 8.0158] | 7.5502 (n=1) [7.5502, 7.5502] | -7.08% | -0.86% |
| Experiment sampled peak RSS (MiB) | 3437.7 (n=1) [3437.7, 3437.7] | 3423.8 (n=1) [3423.8, 3423.8] | 3444.4 (n=1) [3444.4, 3444.4] | 0.40% | -0.20% |
| Experiment sampled peak PSS (MiB) | 3398.4 (n=1) [3398.4, 3398.4] | 3384.7 (n=1) [3384.7, 3384.7] | 3405.3 (n=1) [3405.3, 3405.3] | 0.40% | -0.20% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5459.9 (n=1) [5459.9, 5459.9] | 5448.9 (n=1) [5448.9, 5448.9] | 5435.6 (n=1) [5435.6, 5435.6] | 0.20% | 0.44% |
| GPU device utilization (%) | 52.5 (n=1) [52.5, 52.5] | 54.286 (n=1) [54.286, 54.286] | 45.738 (n=1) [45.738, 45.738] | -3.40% | 12.88% |
| GPU device utilization p95 (%) | 58 (n=1) [58, 58] | 58 (n=1) [58, 58] | 49 (n=1) [49, 49] | 0.00% | 15.52% |
| GPU device memory-controller utilization (%) | 19 (n=1) [19, 19] | 19 (n=1) [19, 19] | 19.048 (n=1) [19.048, 19.048] | 0.00% | -0.25% |
| GPU device memory (MiB) | 1262.8 (n=1) [1262.8, 1262.8] | 1261.4 (n=1) [1261.4, 1261.4] | 1260.8 (n=1) [1260.8, 1260.8] | 0.11% | 0.16% |
| GPU device power (W; not flight attribution) | 18.656 (n=1) [18.656, 18.656] | 18.721 (n=1) [18.721, 18.721] | 18.62 (n=1) [18.62, 18.62] | -0.34% | 0.20% |
| Observed source frame records | 396 (n=1) [396, 396] | 416 (n=1) [416, 416] | 416 (n=1) [416, 416] | -5.05% | -5.05% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 255.83 (n=1) [255.83, 255.83] | 75.00% | 71.57% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.2769e+05 (n=1) [2.2769e+05, 2.2769e+05] | 75.00% | 71.57% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 32746 (n=1) [32746, 32746] | 75.00% | 71.57% |
| Observed source generated points (/frame) | 22917 (n=1) [22917, 22917] | 6097.4 (n=1) [6097.4, 6097.4] | 7213.9 (n=1) [7213.9, 7213.9] | 73.39% | 68.52% |
| Observed source cloud payload (bytes/frame) | 7.3333e+05 (n=1) [7.3333e+05, 7.3333e+05] | 1.9512e+05 (n=1) [1.9512e+05, 1.9512e+05] | 2.3085e+05 (n=1) [2.3085e+05, 2.3085e+05] | 73.39% | 68.52% |
| Map total elapsed mean (ms/frame) | 31.458 (n=1) [31.458, 31.458] | 10.718 (n=1) [10.718, 10.718] | 12.178 (n=1) [12.178, 12.178] | 65.93% | 61.29% |
| Map total elapsed p95 (ms/frame) | 40.17 (n=1) [40.17, 40.17] | 15.907 (n=1) [15.907, 15.907] | 20.705 (n=1) [20.705, 20.705] | 60.40% | 48.46% |
| Map total elapsed max (ms/frame) | 76.944 (n=1) [76.944, 76.944] | 23.122 (n=1) [23.122, 23.122] | 38.62 (n=1) [38.62, 38.62] | 69.95% | 49.81% |
| Map raycast elapsed mean (ms/frame) | 19.611 (n=1) [19.611, 19.611] | 7.0993 (n=1) [7.0993, 7.0993] | 8.0701 (n=1) [8.0701, 8.0701] | 63.80% | 58.85% |
| Map update elapsed mean (ms/frame) | 11.845 (n=1) [11.845, 11.845] | 3.6171 (n=1) [3.6171, 3.6171] | 4.1057 (n=1) [4.1057, 4.1057] | 69.46% | 65.34% |
| Map inflation elapsed mean (ms/frame; nested) | 1.8437 (n=1) [1.8437, 1.8437] | 0.81103 (n=1) [0.81103, 0.81103] | 0.88205 (n=1) [0.88205, 0.88205] | 56.01% | 52.16% |
| Map processed frames / mission time (Hz proxy) | 10.373 (n=1) [10.373, 10.373] | 10.585 (n=1) [10.585, 10.585] | 10.3 (n=1) [10.3, 10.3] | -2.05% | 0.70% |
| Trajectory commits (Hz) | 5.5121 (n=1) [5.5121, 5.5121] | 5.4713 (n=1) [5.4713, 5.4713] | 5.2451 (n=1) [5.2451, 5.2451] | 0.74% | 4.84% |
| Goal retransmissions coalesced | 32 (n=1) [32, 32] | 27 (n=1) [27, 27] | 31 (n=1) [31, 31] | 15.62% | 3.12% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.020297 (n=1) [0.020297, 0.020297] | 0.022403 (n=1) [0.022403, 0.022403] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.057 (n=1) [0.057, 0.057] | 0.175 (n=1) [0.175, 0.175] | N/A | N/A |
| Map points mean (/frame) | 22939 (n=1) [22939, 22939] | 6097.4 (n=1) [6097.4, 6097.4] | 7195 (n=1) [7195, 7195] | 73.42% | 68.63% |
| Map points / mission time (points/s proxy) | 2.3795e+05 (n=1) [2.3795e+05, 2.3795e+05] | 64542 (n=1) [64542, 64542] | 74110 (n=1) [74110, 74110] | 72.88% | 68.85% |
| Map payload / mission time (MiB/s proxy, logical edge) | 7.2616 (n=1) [7.2616, 7.2616] | 1.9697 (n=1) [1.9697, 1.9697] | 2.2617 (n=1) [2.2617, 2.2617] | 72.88% | 68.85% |
| Sensor report payload (MiB/s, logical edge; own span) | 7.0382 (n=1) [7.0382, 7.0382] | 1.8852 (n=1) [1.8852, 1.8852] | 2.2343 (n=1) [2.2343, 2.2343] | 73.22% | 68.25% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 7.2616 (n=1) [7.2616, 7.2616] | 1.9697 (n=1) [1.9697, 1.9697] | 2.2617 (n=1) [2.2617, 2.2617] | 72.88% | 68.85% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 0.00% | 0.00% |
| Received odometry frequency (Hz) | 99.997 (n=1) [99.997, 99.997] | 99.998 (n=1) [99.998, 99.998] | 99.998 (n=1) [99.998, 99.998] | -0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 93.447 (n=1) [93.447, 93.447] | 92.704 (n=1) [92.704, 92.704] | 95.905 (n=1) [95.905, 95.905] | 0.79% | -2.63% |
| Odometry receipt p99 gap (ms) | 10.882 (n=1) [10.882, 10.882] | 10.676 (n=1) [10.676, 10.676] | 10.837 (n=1) [10.837, 10.837] | 1.89% | 0.41% |
| Odometry receipt max gap (ms) | 15.641 (n=1) [15.641, 15.641] | 15.341 (n=1) [15.341, 15.341] | 13.182 (n=1) [13.182, 13.182] | 1.92% | 15.72% |
| Actual FSM main callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 4.348 (n=1) [4.348, 4.348] | N/A | N/A |
| Guard active duration (s) | 0 (n=1) [0, 0] | 0.97001 (n=1) [0.97001, 0.97001] | 1.8903 (n=1) [1.8903, 1.8903] | N/A | N/A |

## seed5 — c24_iteration01 — profiled_supplement

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
| Mission time (s) | 45.83 (n=1) [45.83, 45.83] | 45.84 (n=1) [45.84, 45.84] | 40.84 (n=1) [40.84, 40.84] | -0.02% | 10.89% |
| Path length (m) | 229.23 (n=1) [229.23, 229.23] | 233.17 (n=1) [233.17, 233.17] | 224.91 (n=1) [224.91, 224.91] | -1.72% | 1.88% |
| Minimum static-PC clearance (m) | 0.328 (n=1) [0.328, 0.328] | 0.245 (n=1) [0.245, 0.245] | 0.307 (n=1) [0.307, 0.307] | 25.30% | 6.40% |
| Experiment CPU (cores) | 0.71948 (n=1) [0.71948, 0.71948] | 0.43548 (n=1) [0.43548, 0.43548] | 0.44151 (n=1) [0.44151, 0.44151] | 39.47% | 38.63% |
| Experiment CPU (whole-host %) | 3.5974 (n=1) [3.5974, 3.5974] | 2.1774 (n=1) [2.1774, 2.1774] | 2.2075 (n=1) [2.2075, 2.2075] | 39.47% | 38.63% |
| Experiment measurement-window CPU (core-s) | 34.628 (n=1) [34.628, 34.628] | 20.515 (n=1) [20.515, 20.515] | 18.951 (n=1) [18.951, 18.951] | 40.76% | 45.27% |
| Accounting window (s) | 48.13 (n=1) [48.13, 48.13] | 47.11 (n=1) [47.11, 47.11] | 42.922 (n=1) [42.922, 42.922] | 2.12% | 10.82% |
| Experiment CPU 1 s p95 (cores) | 0.98157 (n=1) [0.98157, 0.98157] | 0.59894 (n=1) [0.59894, 0.59894] | 0.57664 (n=1) [0.57664, 0.57664] | 38.98% | 41.25% |
| Experiment CPU 1 s maximum (cores) | 1.2278 (n=1) [1.2278, 1.2278] | 0.67244 (n=1) [0.67244, 0.67244] | 0.62999 (n=1) [0.62999, 0.62999] | 45.23% | 48.69% |
| Composed runtime CPU (cores; includes simulator) | 0.68154 (n=1) [0.68154, 0.68154] | 0.39082 (n=1) [0.39082, 0.39082] | 0.39794 (n=1) [0.39794, 0.39794] | 42.66% | 41.61% |
| Composed runtime measurement-window CPU (core-s) | 32.802 (n=1) [32.802, 32.802] | 18.411 (n=1) [18.411, 18.411] | 17.081 (n=1) [17.081, 17.081] | 43.87% | 47.93% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.3905 (n=1) [4.3905, 4.3905] | 4.3797 (n=1) [4.3797, 4.3797] | 4.5446 (n=1) [4.5446, 4.5446] | 0.24% | -3.51% |
| Whole-host CPU (%) | 10.322 (n=1) [10.322, 10.322] | 9.0926 (n=1) [9.0926, 9.0926] | 9.8336 (n=1) [9.8336, 9.8336] | 11.91% | 4.73% |
| Baseline whole-host CPU (%) | 7.9786 (n=1) [7.9786, 7.9786] | 8.1061 (n=1) [8.1061, 8.1061] | 7.631 (n=1) [7.631, 7.631] | -1.60% | 4.36% |
| Experiment sampled peak RSS (MiB) | 3481.7 (n=1) [3481.7, 3481.7] | 3477.8 (n=1) [3477.8, 3477.8] | 3480.8 (n=1) [3480.8, 3480.8] | 0.11% | 0.03% |
| Experiment sampled peak PSS (MiB) | 3442.5 (n=1) [3442.5, 3442.5] | 3438.3 (n=1) [3438.3, 3438.3] | 3441.5 (n=1) [3441.5, 3441.5] | 0.12% | 0.03% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5382.3 (n=1) [5382.3, 5382.3] | 5407.2 (n=1) [5407.2, 5407.2] | 5390.1 (n=1) [5390.1, 5390.1] | -0.46% | -0.14% |
| GPU device utilization (%) | 48.583 (n=1) [48.583, 48.583] | 48.447 (n=1) [48.447, 48.447] | 54.286 (n=1) [54.286, 54.286] | 0.28% | -11.74% |
| GPU device utilization p95 (%) | 55 (n=1) [55, 55] | 51 (n=1) [51, 51] | 56 (n=1) [56, 56] | 7.27% | -1.82% |
| GPU device memory-controller utilization (%) | 19.125 (n=1) [19.125, 19.125] | 19 (n=1) [19, 19] | 19.024 (n=1) [19.024, 19.024] | 0.65% | 0.53% |
| GPU device memory (MiB) | 1261.5 (n=1) [1261.5, 1261.5] | 1261.4 (n=1) [1261.4, 1261.4] | 1262.3 (n=1) [1262.3, 1262.3] | 0.01% | -0.07% |
| GPU device power (W; not flight attribution) | 18.672 (n=1) [18.672, 18.672] | 18.783 (n=1) [18.783, 18.783] | 18.902 (n=1) [18.902, 18.902] | -0.59% | -1.23% |
| Observed source frame records | 478 (n=1) [478, 478] | 468 (n=1) [468, 468] | 424 (n=1) [424, 424] | 2.09% | 11.30% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 263.21 (n=1) [263.21, 263.21] | 75.00% | 70.75% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.3425e+05 (n=1) [2.3425e+05, 2.3425e+05] | 75.00% | 70.75% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 33691 (n=1) [33691, 33691] | 75.00% | 70.75% |
| Observed source generated points (/frame) | 30624 (n=1) [30624, 30624] | 8137.8 (n=1) [8137.8, 8137.8] | 8686.9 (n=1) [8686.9, 8686.9] | 73.43% | 71.63% |
| Observed source cloud payload (bytes/frame) | 9.7997e+05 (n=1) [9.7997e+05, 9.7997e+05] | 2.6041e+05 (n=1) [2.6041e+05, 2.6041e+05] | 2.7798e+05 (n=1) [2.7798e+05, 2.7798e+05] | 73.43% | 71.63% |
| Map total elapsed mean (ms/frame) | 34.571 (n=1) [34.571, 34.571] | 10.864 (n=1) [10.864, 10.864] | 12.65 (n=1) [12.65, 12.65] | 68.57% | 63.41% |
| Map total elapsed p95 (ms/frame) | 45.15 (n=1) [45.15, 45.15] | 16.445 (n=1) [16.445, 16.445] | 21.651 (n=1) [21.651, 21.651] | 63.58% | 52.05% |
| Map total elapsed max (ms/frame) | 82.077 (n=1) [82.077, 82.077] | 54.286 (n=1) [54.286, 54.286] | 52.507 (n=1) [52.507, 52.507] | 33.86% | 36.03% |
| Map raycast elapsed mean (ms/frame) | 21.874 (n=1) [21.874, 21.874] | 7.1466 (n=1) [7.1466, 7.1466] | 8.1444 (n=1) [8.1444, 8.1444] | 67.33% | 62.77% |
| Map update elapsed mean (ms/frame) | 12.695 (n=1) [12.695, 12.695] | 3.716 (n=1) [3.716, 3.716] | 4.5036 (n=1) [4.5036, 4.5036] | 70.73% | 64.52% |
| Map inflation elapsed mean (ms/frame; nested) | 1.9431 (n=1) [1.9431, 1.9431] | 0.87446 (n=1) [0.87446, 0.87446] | 1.0165 (n=1) [1.0165, 1.0165] | 55.00% | 47.69% |
| Map processed frames / mission time (Hz proxy) | 10.43 (n=1) [10.43, 10.43] | 10.209 (n=1) [10.209, 10.209] | 10.382 (n=1) [10.382, 10.382] | 2.11% | 0.46% |
| Trajectory commits (Hz) | 4.6712 (n=1) [4.6712, 4.6712] | 4.7123 (n=1) [4.7123, 4.7123] | 5.3509 (n=1) [5.3509, 5.3509] | -0.88% | -14.55% |
| Goal retransmissions coalesced | 34 (n=1) [34, 34] | 32 (n=1) [32, 32] | 31 (n=1) [31, 31] | 5.88% | 8.82% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.018706 (n=1) [0.018706, 0.018706] | 0.019699 (n=1) [0.019699, 0.019699] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.113 (n=1) [0.113, 0.113] | 0.131 (n=1) [0.131, 0.131] | N/A | N/A |
| Map points mean (/frame) | 30624 (n=1) [30624, 30624] | 8137.8 (n=1) [8137.8, 8137.8] | 8686.9 (n=1) [8686.9, 8686.9] | 73.43% | 71.63% |
| Map points / mission time (points/s proxy) | 3.194e+05 (n=1) [3.194e+05, 3.194e+05] | 83082 (n=1) [83082, 83082] | 90187 (n=1) [90187, 90187] | 73.99% | 71.76% |
| Map payload / mission time (MiB/s proxy, logical edge) | 9.7474 (n=1) [9.7474, 9.7474] | 2.5355 (n=1) [2.5355, 2.5355] | 2.7523 (n=1) [2.7523, 2.7523] | 73.99% | 71.76% |
| Sensor report payload (MiB/s, logical edge; own span) | 9.5396 (n=1) [9.5396, 9.5396] | 2.5402 (n=1) [2.5402, 2.5402] | 2.745 (n=1) [2.745, 2.745] | 73.37% | 71.23% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 9.7474 (n=1) [9.7474, 9.7474] | 2.5355 (n=1) [2.5355, 2.5355] | 2.7523 (n=1) [2.7523, 2.7523] | 73.99% | 71.76% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 10.002 (n=1) [10.002, 10.002] | 0.00% | -0.01% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 99.997 (n=1) [99.997, 99.997] | 99.999 (n=1) [99.999, 99.999] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 92.946 (n=1) [92.946, 92.946] | 91.743 (n=1) [91.743, 91.743] | 93.654 (n=1) [93.654, 93.654] | 1.29% | -0.76% |
| Odometry receipt p99 gap (ms) | 10.614 (n=1) [10.614, 10.614] | 10.698 (n=1) [10.698, 10.698] | 10.745 (n=1) [10.745, 10.745] | -0.79% | -1.24% |
| Odometry receipt max gap (ms) | 12.048 (n=1) [12.048, 12.048] | 11.149 (n=1) [11.149, 11.149] | 16.527 (n=1) [16.527, 16.527] | 7.46% | -37.18% |
| Actual FSM main callback frequency (profiled only) | 99.95 (n=1) [99.95, 99.95] | 99.923 (n=1) [99.923, 99.923] | 100 (n=1) [100, 100] | 0.03% | -0.05% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | 100 (n=1) [100, 100] | 0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 5.687 (n=1) [5.687, 5.687] | N/A | N/A |
| Guard active duration (s) | 6.493 (n=1) [6.493, 6.493] | 5.1286 (n=1) [5.1286, 5.1286] | 2.4601 (n=1) [2.4601, 2.4601] | 21.01% | 62.11% |

## seed7 — c24_iteration01 — profiled_supplement

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
| Mission time (s) | 46.05 (n=1) [46.05, 46.05] | 47.27 (n=1) [47.27, 47.27] | 46.2 (n=1) [46.2, 46.2] | -2.65% | -0.33% |
| Path length (m) | 231.62 (n=1) [231.62, 231.62] | 234.32 (n=1) [234.32, 234.32] | 231.39 (n=1) [231.39, 231.39] | -1.16% | 0.10% |
| Minimum static-PC clearance (m) | 0.313 (n=1) [0.313, 0.313] | 0.275 (n=1) [0.275, 0.275] | 0.307 (n=1) [0.307, 0.307] | 12.14% | 1.92% |
| Experiment CPU (cores) | 0.71837 (n=1) [0.71837, 0.71837] | 0.45338 (n=1) [0.45338, 0.45338] | 0.4834 (n=1) [0.4834, 0.4834] | 36.89% | 32.71% |
| Experiment CPU (whole-host %) | 3.5919 (n=1) [3.5919, 3.5919] | 2.2669 (n=1) [2.2669, 2.2669] | 2.417 (n=1) [2.417, 2.417] | 36.89% | 32.71% |
| Experiment measurement-window CPU (core-s) | 34.555 (n=1) [34.555, 34.555] | 22.292 (n=1) [22.292, 22.292] | 23.248 (n=1) [23.248, 23.248] | 35.49% | 32.72% |
| Accounting window (s) | 48.101 (n=1) [48.101, 48.101] | 49.169 (n=1) [49.169, 49.169] | 48.093 (n=1) [48.093, 48.093] | -2.22% | 0.02% |
| Experiment CPU 1 s p95 (cores) | 0.93126 (n=1) [0.93126, 0.93126] | 0.63659 (n=1) [0.63659, 0.63659] | 0.65482 (n=1) [0.65482, 0.65482] | 31.64% | 29.68% |
| Experiment CPU 1 s maximum (cores) | 0.99687 (n=1) [0.99687, 0.99687] | 0.72095 (n=1) [0.72095, 0.72095] | 0.72227 (n=1) [0.72227, 0.72227] | 27.68% | 27.55% |
| Composed runtime CPU (cores; includes simulator) | 0.67906 (n=1) [0.67906, 0.67906] | 0.41739 (n=1) [0.41739, 0.41739] | 0.44027 (n=1) [0.44027, 0.44027] | 38.53% | 35.16% |
| Composed runtime measurement-window CPU (core-s) | 32.664 (n=1) [32.664, 32.664] | 20.523 (n=1) [20.523, 20.523] | 21.174 (n=1) [21.174, 21.174] | 37.17% | 35.18% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.4117 (n=1) [4.4117, 4.4117] | 4.463 (n=1) [4.463, 4.463] | 4.3101 (n=1) [4.3101, 4.3101] | -1.16% | 2.30% |
| Whole-host CPU (%) | 10.057 (n=1) [10.057, 10.057] | 9.9333 (n=1) [9.9333, 9.9333] | 9.3806 (n=1) [9.3806, 9.3806] | 1.23% | 6.73% |
| Baseline whole-host CPU (%) | 8.0207 (n=1) [8.0207, 8.0207] | 7.8593 (n=1) [7.8593, 7.8593] | 7.4601 (n=1) [7.4601, 7.4601] | 2.01% | 6.99% |
| Experiment sampled peak RSS (MiB) | 3494.9 (n=1) [3494.9, 3494.9] | 3479.8 (n=1) [3479.8, 3479.8] | 3486.6 (n=1) [3486.6, 3486.6] | 0.43% | 0.24% |
| Experiment sampled peak PSS (MiB) | 3455.8 (n=1) [3455.8, 3455.8] | 3440.3 (n=1) [3440.3, 3440.3] | 3447.7 (n=1) [3447.7, 3447.7] | 0.45% | 0.23% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5398.3 (n=1) [5398.3, 5398.3] | 5419.6 (n=1) [5419.6, 5419.6] | 5424.5 (n=1) [5424.5, 5424.5] | -0.39% | -0.48% |
| GPU device utilization (%) | 50.292 (n=1) [50.292, 50.292] | 50.592 (n=1) [50.592, 50.592] | 50.438 (n=1) [50.438, 50.438] | -0.60% | -0.29% |
| GPU device utilization p95 (%) | 58 (n=1) [58, 58] | 56 (n=1) [56, 56] | 57 (n=1) [57, 57] | 3.45% | 1.72% |
| GPU device memory-controller utilization (%) | 19.021 (n=1) [19.021, 19.021] | 19.143 (n=1) [19.143, 19.143] | 19.458 (n=1) [19.458, 19.458] | -0.64% | -2.30% |
| GPU device memory (MiB) | 1266.6 (n=1) [1266.6, 1266.6] | 1266.2 (n=1) [1266.2, 1266.2] | 1266.3 (n=1) [1266.3, 1266.3] | 0.03% | 0.02% |
| GPU device power (W; not flight attribution) | 18.75 (n=1) [18.75, 18.75] | 18.817 (n=1) [18.817, 18.817] | 18.792 (n=1) [18.792, 18.792] | -0.36% | -0.23% |
| Observed source frame records | 475 (n=1) [475, 475] | 487 (n=1) [487, 487] | 476 (n=1) [476, 476] | -2.53% | -0.21% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 307.25 (n=1) [307.25, 307.25] | 75.00% | 65.86% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.7345e+05 (n=1) [2.7345e+05, 2.7345e+05] | 75.00% | 65.86% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 39328 (n=1) [39328, 39328] | 75.00% | 65.86% |
| Observed source generated points (/frame) | 37069 (n=1) [37069, 37069] | 10700 (n=1) [10700, 10700] | 13612 (n=1) [13612, 13612] | 71.14% | 63.28% |
| Observed source cloud payload (bytes/frame) | 1.1862e+06 (n=1) [1.1862e+06, 1.1862e+06] | 3.4239e+05 (n=1) [3.4239e+05, 3.4239e+05] | 4.3557e+05 (n=1) [4.3557e+05, 4.3557e+05] | 71.14% | 63.28% |
| Map total elapsed mean (ms/frame) | 33.002 (n=1) [33.002, 33.002] | 10.843 (n=1) [10.843, 10.843] | 13.582 (n=1) [13.582, 13.582] | 67.14% | 58.85% |
| Map total elapsed p95 (ms/frame) | 43.392 (n=1) [43.392, 43.392] | 16.481 (n=1) [16.481, 16.481] | 30.737 (n=1) [30.737, 30.737] | 62.02% | 29.16% |
| Map total elapsed max (ms/frame) | 137.52 (n=1) [137.52, 137.52] | 26.25 (n=1) [26.25, 26.25] | 64.752 (n=1) [64.752, 64.752] | 80.91% | 52.91% |
| Map raycast elapsed mean (ms/frame) | 21.294 (n=1) [21.294, 21.294] | 7.2247 (n=1) [7.2247, 7.2247] | 8.9976 (n=1) [8.9976, 8.9976] | 66.07% | 57.75% |
| Map update elapsed mean (ms/frame) | 11.706 (n=1) [11.706, 11.706] | 3.6169 (n=1) [3.6169, 3.6169] | 4.5826 (n=1) [4.5826, 4.5826] | 69.10% | 60.85% |
| Map inflation elapsed mean (ms/frame; nested) | 2.0981 (n=1) [2.0981, 2.0981] | 0.95244 (n=1) [0.95244, 0.95244] | 1.0624 (n=1) [1.0624, 1.0624] | 54.60% | 49.36% |
| Map processed frames / mission time (Hz proxy) | 10.315 (n=1) [10.315, 10.315] | 10.281 (n=1) [10.281, 10.281] | 10.303 (n=1) [10.303, 10.303] | 0.32% | 0.11% |
| Trajectory commits (Hz) | 5.0608 (n=1) [5.0608, 5.0608] | 5.0044 (n=1) [5.0044, 5.0044] | 5.1504 (n=1) [5.1504, 5.1504] | 1.11% | -1.77% |
| Goal retransmissions coalesced | 35 (n=1) [35, 35] | 35 (n=1) [35, 35] | 31 (n=1) [31, 31] | 0.00% | 11.43% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.017877 (n=1) [0.017877, 0.017877] | 0.01865 (n=1) [0.01865, 0.01865] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.042 (n=1) [0.042, 0.042] | 0.109 (n=1) [0.109, 0.109] | N/A | N/A |
| Map points mean (/frame) | 37069 (n=1) [37069, 37069] | 10711 (n=1) [10711, 10711] | 13612 (n=1) [13612, 13612] | 71.11% | 63.28% |
| Map points / mission time (points/s proxy) | 3.8237e+05 (n=1) [3.8237e+05, 3.8237e+05] | 1.1013e+05 (n=1) [1.1013e+05, 1.1013e+05] | 1.4024e+05 (n=1) [1.4024e+05, 1.4024e+05] | 71.20% | 63.32% |
| Map payload / mission time (MiB/s proxy, logical edge) | 11.669 (n=1) [11.669, 11.669] | 3.3608 (n=1) [3.3608, 3.3608] | 4.2798 (n=1) [4.2798, 4.2798] | 71.20% | 63.32% |
| Sensor report payload (MiB/s, logical edge; own span) | 11.35 (n=1) [11.35, 11.35] | 3.268 (n=1) [3.268, 3.268] | 4.2191 (n=1) [4.2191, 4.2191] | 71.21% | 62.83% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 11.669 (n=1) [11.669, 11.669] | 3.3608 (n=1) [3.3608, 3.3608] | 4.2798 (n=1) [4.2798, 4.2798] | 71.20% | 63.32% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.003 (n=1) [10.003, 10.003] | 10 (n=1) [10, 10] | 9.9995 (n=1) [9.9995, 9.9995] | 0.03% | 0.03% |
| Received odometry frequency (Hz) | 99.999 (n=1) [99.999, 99.999] | 99.998 (n=1) [99.998, 99.998] | 100.01 (n=1) [100.01, 100.01] | 0.00% | -0.02% |
| Received command frequency (Hz; holds included) | 93.043 (n=1) [93.043, 93.043] | 92.603 (n=1) [92.603, 92.603] | 94.014 (n=1) [94.014, 94.014] | 0.47% | -1.04% |
| Odometry receipt p99 gap (ms) | 10.793 (n=1) [10.793, 10.793] | 11.221 (n=1) [11.221, 11.221] | 10.601 (n=1) [10.601, 10.601] | -3.97% | 1.78% |
| Odometry receipt max gap (ms) | 17.268 (n=1) [17.268, 17.268] | 12.493 (n=1) [12.493, 12.493] | 16.066 (n=1) [16.066, 16.066] | 27.65% | 6.96% |
| Actual FSM main callback frequency (profiled only) | 99.949 (n=1) [99.949, 99.949] | 99.949 (n=1) [99.949, 99.949] | 99.924 (n=1) [99.924, 99.924] | -0.00% | 0.02% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 12.314 (n=1) [12.314, 12.314] | N/A | N/A |
| Guard active duration (s) | 4.4675 (n=1) [4.4675, 4.4675] | 3.9835 (n=1) [3.9835, 3.9835] | 5.8909 (n=1) [5.8909, 5.8909] | 10.84% | -31.86% |

## seed9 — c24_iteration01 — profiled_supplement

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
| Mission time (s) | 50.23 (n=1) [50.23, 50.23] | 49.5 (n=1) [49.5, 49.5] | 54.9 (n=1) [54.9, 54.9] | 1.45% | -9.30% |
| Path length (m) | 234.24 (n=1) [234.24, 234.24] | 235.08 (n=1) [235.08, 235.08] | 243.23 (n=1) [243.23, 243.23] | -0.36% | -3.84% |
| Minimum static-PC clearance (m) | 0.27 (n=1) [0.27, 0.27] | 0.257 (n=1) [0.257, 0.257] | 0.264 (n=1) [0.264, 0.264] | 4.81% | 2.22% |
| Experiment CPU (cores) | 0.73781 (n=1) [0.73781, 0.73781] | 0.43014 (n=1) [0.43014, 0.43014] | 0.5206 (n=1) [0.5206, 0.5206] | 41.70% | 29.44% |
| Experiment CPU (whole-host %) | 3.689 (n=1) [3.689, 3.689] | 2.1507 (n=1) [2.1507, 2.1507] | 2.603 (n=1) [2.603, 2.603] | 41.70% | 29.44% |
| Experiment measurement-window CPU (core-s) | 38.701 (n=1) [38.701, 38.701] | 22.071 (n=1) [22.071, 22.071] | 29.463 (n=1) [29.463, 29.463] | 42.97% | 23.87% |
| Accounting window (s) | 52.454 (n=1) [52.454, 52.454] | 51.311 (n=1) [51.311, 51.311] | 56.595 (n=1) [56.595, 56.595] | 2.18% | -7.89% |
| Experiment CPU 1 s p95 (cores) | 0.9712 (n=1) [0.9712, 0.9712] | 0.60011 (n=1) [0.60011, 0.60011] | 0.75181 (n=1) [0.75181, 0.75181] | 38.21% | 22.59% |
| Experiment CPU 1 s maximum (cores) | 1.1499 (n=1) [1.1499, 1.1499] | 0.76742 (n=1) [0.76742, 0.76742] | 0.85071 (n=1) [0.85071, 0.85071] | 33.26% | 26.02% |
| Composed runtime CPU (cores; includes simulator) | 0.69521 (n=1) [0.69521, 0.69521] | 0.38458 (n=1) [0.38458, 0.38458] | 0.47575 (n=1) [0.47575, 0.47575] | 44.68% | 31.57% |
| Composed runtime measurement-window CPU (core-s) | 36.466 (n=1) [36.466, 36.466] | 19.733 (n=1) [19.733, 19.733] | 26.925 (n=1) [26.925, 26.925] | 45.89% | 26.17% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.5513 (n=1) [4.5513, 4.5513] | 4.4635 (n=1) [4.4635, 4.4635] | 4.6157 (n=1) [4.6157, 4.6157] | 1.93% | -1.42% |
| Whole-host CPU (%) | 10.288 (n=1) [10.288, 10.288] | 9.0202 (n=1) [9.0202, 9.0202] | 9.6206 (n=1) [9.6206, 9.6206] | 12.32% | 6.49% |
| Baseline whole-host CPU (%) | 8.3848 (n=1) [8.3848, 8.3848] | 7.7065 (n=1) [7.7065, 7.7065] | 8.3832 (n=1) [8.3832, 8.3832] | 8.09% | 0.02% |
| Experiment sampled peak RSS (MiB) | 3519.8 (n=1) [3519.8, 3519.8] | 3490.8 (n=1) [3490.8, 3490.8] | 3525.6 (n=1) [3525.6, 3525.6] | 0.82% | -0.17% |
| Experiment sampled peak PSS (MiB) | 3480.5 (n=1) [3480.5, 3480.5] | 3451.4 (n=1) [3451.4, 3451.4] | 3486.6 (n=1) [3486.6, 3486.6] | 0.84% | -0.17% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5386.1 (n=1) [5386.1, 5386.1] | 5395.8 (n=1) [5395.8, 5395.8] | 5364.1 (n=1) [5364.1, 5364.1] | -0.18% | 0.41% |
| GPU device utilization (%) | 56.038 (n=1) [56.038, 56.038] | 49.216 (n=1) [49.216, 49.216] | 46.5 (n=1) [46.5, 46.5] | 12.18% | 17.02% |
| GPU device utilization p95 (%) | 59 (n=1) [59, 59] | 53 (n=1) [53, 53] | 51 (n=1) [51, 51] | 10.17% | 13.56% |
| GPU device memory-controller utilization (%) | 19.019 (n=1) [19.019, 19.019] | 19.078 (n=1) [19.078, 19.078] | 19.232 (n=1) [19.232, 19.232] | -0.31% | -1.12% |
| GPU device memory (MiB) | 1272 (n=1) [1272, 1272] | 1271.4 (n=1) [1271.4, 1271.4] | 1270 (n=1) [1270, 1270] | 0.05% | 0.16% |
| GPU device power (W; not flight attribution) | 18.776 (n=1) [18.776, 18.776] | 18.765 (n=1) [18.765, 18.765] | 18.731 (n=1) [18.731, 18.731] | 0.06% | 0.24% |
| Observed source frame records | 518 (n=1) [518, 518] | 506 (n=1) [506, 506] | 558 (n=1) [558, 558] | 2.32% | -7.72% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 329.03 (n=1) [329.03, 329.03] | 75.00% | 63.44% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.9284e+05 (n=1) [2.9284e+05, 2.9284e+05] | 75.00% | 63.44% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 42116 (n=1) [42116, 42116] | 75.00% | 63.44% |
| Observed source generated points (/frame) | 42511 (n=1) [42511, 42511] | 11548 (n=1) [11548, 11548] | 15930 (n=1) [15930, 15930] | 72.84% | 62.53% |
| Observed source cloud payload (bytes/frame) | 1.3603e+06 (n=1) [1.3603e+06, 1.3603e+06] | 3.6953e+05 (n=1) [3.6953e+05, 3.6953e+05] | 5.0976e+05 (n=1) [5.0976e+05, 5.0976e+05] | 72.84% | 62.53% |
| Map total elapsed mean (ms/frame) | 31.526 (n=1) [31.526, 31.526] | 10.574 (n=1) [10.574, 10.574] | 13.244 (n=1) [13.244, 13.244] | 66.46% | 57.99% |
| Map total elapsed p95 (ms/frame) | 43.074 (n=1) [43.074, 43.074] | 16.231 (n=1) [16.231, 16.231] | 29.67 (n=1) [29.67, 29.67] | 62.32% | 31.12% |
| Map total elapsed max (ms/frame) | 80.86 (n=1) [80.86, 80.86] | 24.041 (n=1) [24.041, 24.041] | 61.458 (n=1) [61.458, 61.458] | 70.27% | 23.99% |
| Map raycast elapsed mean (ms/frame) | 20.706 (n=1) [20.706, 20.706] | 7.3125 (n=1) [7.3125, 7.3125] | 8.8108 (n=1) [8.8108, 8.8108] | 64.68% | 57.45% |
| Map update elapsed mean (ms/frame) | 10.818 (n=1) [10.818, 10.818] | 3.2598 (n=1) [3.2598, 3.2598] | 4.432 (n=1) [4.432, 4.432] | 69.87% | 59.03% |
| Map inflation elapsed mean (ms/frame; nested) | 2.1429 (n=1) [2.1429, 2.1429] | 0.92409 (n=1) [0.92409, 0.92409] | 1.0924 (n=1) [1.0924, 1.0924] | 56.88% | 49.02% |
| Map processed frames / mission time (Hz proxy) | 10.293 (n=1) [10.293, 10.293] | 10.222 (n=1) [10.222, 10.222] | 10.164 (n=1) [10.164, 10.164] | 0.68% | 1.25% |
| Trajectory commits (Hz) | 4.6845 (n=1) [4.6845, 4.6845] | 5.1829 (n=1) [5.1829, 5.1829] | 4.6243 (n=1) [4.6243, 4.6243] | -10.64% | 1.29% |
| Goal retransmissions coalesced | 32 (n=1) [32, 32] | 37 (n=1) [37, 37] | 37 (n=1) [37, 37] | -15.62% | -15.62% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.02008 (n=1) [0.02008, 0.02008] | 0.019491 (n=1) [0.019491, 0.019491] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.094 (n=1) [0.094, 0.094] | 0.134 (n=1) [0.134, 0.134] | N/A | N/A |
| Map points mean (/frame) | 42553 (n=1) [42553, 42553] | 11548 (n=1) [11548, 11548] | 15930 (n=1) [15930, 15930] | 72.86% | 62.56% |
| Map points / mission time (points/s proxy) | 4.3798e+05 (n=1) [4.3798e+05, 4.3798e+05] | 1.1804e+05 (n=1) [1.1804e+05, 1.1804e+05] | 1.6191e+05 (n=1) [1.6191e+05, 1.6191e+05] | 73.05% | 63.03% |
| Map payload / mission time (MiB/s proxy, logical edge) | 13.366 (n=1) [13.366, 13.366] | 3.6024 (n=1) [3.6024, 3.6024] | 4.9412 (n=1) [4.9412, 4.9412] | 73.05% | 63.03% |
| Sensor report payload (MiB/s, logical edge; own span) | 13.158 (n=1) [13.158, 13.158] | 3.554 (n=1) [3.554, 3.554] | 4.9218 (n=1) [4.9218, 4.9218] | 72.99% | 62.59% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 13.366 (n=1) [13.366, 13.366] | 3.6024 (n=1) [3.6024, 3.6024] | 4.9412 (n=1) [4.9412, 4.9412] | 73.05% | 63.03% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | 10 (n=1) [10, 10] | -0.00% | -0.00% |
| Received odometry frequency (Hz) | 99.999 (n=1) [99.999, 99.999] | 99.997 (n=1) [99.997, 99.997] | 99.998 (n=1) [99.998, 99.998] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.026 (n=1) [94.026, 94.026] | 95.057 (n=1) [95.057, 95.057] | 94.727 (n=1) [94.727, 94.727] | -1.10% | -0.75% |
| Odometry receipt p99 gap (ms) | 10.645 (n=1) [10.645, 10.645] | 10.955 (n=1) [10.955, 10.955] | 10.792 (n=1) [10.792, 10.792] | -2.91% | -1.38% |
| Odometry receipt max gap (ms) | 15.865 (n=1) [15.865, 15.865] | 11.935 (n=1) [11.935, 11.935] | 15.62 (n=1) [15.62, 15.62] | 24.78% | 1.55% |
| Actual FSM main callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.924 (n=1) [99.924, 99.924] | 99.932 (n=1) [99.932, 99.932] | 0.08% | 0.07% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 9 (n=1) [9, 9] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 15.693 (n=1) [15.693, 15.693] | N/A | N/A |
| Guard active duration (s) | 6.893 (n=1) [6.893, 6.893] | 6.9169 (n=1) [6.9169, 6.9169] | 8.7641 (n=1) [8.7641, 8.7641] | -0.35% | -27.14% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c24_normal_validation_20260917/iteration01/preflight/seed1/r01_run18000/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.86029e-05 | 2.34238e-05 |
| frontend_cloud / 0 | N/A | 0.00013345 | 0.000110067 |
| frontend_enqueue / 0 | N/A | 5.83622e-05 | 4.81409e-05 |
| frontend_guard_status / 0 | N/A | N/A | 0 |
| frontend_map_ack / 0 | N/A | N/A | 1.29516e-05 |
| frontend_odom / 0 | N/A | 0.000461872 | 0.00052817 |
| frontend_replan_status / 0 | N/A | N/A | 1.06705e-05 |
| frontend_report / 0 | N/A | 1.59006e-05 | 1.53686e-05 |
| frontend_stats / 0 | N/A | 0.000930655 | 0.000808825 |
| fsm_command_callback / 0 | 0.0087204 | 0.010379 | 0.00966147 |
| fsm_main_callback / 0 | 0.000561677 | 0.000652875 | 0.000620091 |
| fsm_main_core / 0 | 0.000355627 | 0.000406597 | 0.000380288 |
| fsm_poly_publish / 0 | 4.30361e-05 | 4.33083e-05 | 4.1721e-05 |
| fsm_replan_callback / 0 | 0.000294403 | 0.00034973 | 0.000320886 |
| fsm_replan_core / 0 | 0.000289668 | 0.000290573 | 0.000322327 |
| guard_brake / 0 | 0 | 0 | 0 |
| guard_certificate / 0 | 0.00115846 | 0.00134632 | 0.00129737 |
| guard_recover / 0 | N/A | 0 | 0 |
| map_ack_and_log / 0 | 0.000755796 | 0.00129801 | 0.00132605 |
| map_cloud_enqueue / 0 | 6.4337e-05 | 7.96152e-05 | 6.55639e-05 |
| map_odom_callback / 0 | 0.00101019 | 0.000919616 | 0.000943937 |
| map_prob_update / 0 | 0.248821 | 0.100347 | 0.0875018 |
| map_ros_to_pcl / 0 | 0.00405283 | 0.00103625 | 0.000891864 |
| map_snapshot_commit_health / 0 | 0.0502527 | 0.02137 | 0.020682 |
| map_worker / 0 | 7.30396e-05 | 7.45382e-05 | 6.44834e-05 |
| planner_backup_optimize / 0 | 0.029101 | 0.0225533 | 0.0241303 |
| planner_commit / 0 | 0.000463881 | 0.000462687 | 0.000442589 |
| planner_corridor_search / 0 | 0.0093269 | 0.0102408 | 0.0103456 |
| planner_exp_optimize / 0 | 0.0587387 | 0.0441099 | 0.0471954 |
| planner_generate_backup / 0 | 0.0187529 | 0.0173222 | 0.0173327 |
| planner_generate_exp / 0 | 0.000472843 | 0.000503764 | 0.000542154 |
| planner_path_search / 0 | 0.00937143 | 0.0198948 | 0.0166172 |
| planner_stop_viability / 0 | 0.000376278 | 0.000384434 | 0.000395535 |
| planner_validate_geometry / 0 | 0.00491511 | 0.00497714 | 0.00494228 |
| planner_velocity_extrema / 0 | 0.000119131 | 0.000108712 | 0.000106291 |
| planner_visualize_path / 0 | 0.000534063 | 0.000672746 | 0.000591961 |
| sim_odom_callback / 0 | 0.00957325 | 0.0107142 | 0.00982908 |
| sim_render_callback / 0 | 0.0419256 | 0.0217366 | 0.0153503 |

Source: `/root/super-sector-filter/results/c24_normal_validation_20260917/iteration01/preflight/seed3/r01_run18001/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.33346e-05 | 3.47466e-05 |
| frontend_cloud / 0 | N/A | 0.000123644 | 0.000129536 |
| frontend_enqueue / 0 | N/A | 4.61522e-05 | 6.99362e-05 |
| frontend_guard_status / 0 | N/A | N/A | 7.0661e-06 |
| frontend_map_ack / 0 | N/A | N/A | 1.76771e-05 |
| frontend_odom / 0 | N/A | 0.000458664 | 0.000575852 |
| frontend_replan_status / 0 | N/A | N/A | 1.04474e-05 |
| frontend_report / 0 | N/A | 1.06434e-05 | 1.11293e-05 |
| frontend_stats / 0 | N/A | 0.000636541 | 0.000716333 |
| fsm_command_callback / 0 | 0.0100028 | 0.00588946 | 0.00724813 |
| fsm_main_callback / 0 | 0.000584522 | 0.000539502 | 0.000567773 |
| fsm_main_core / 0 | 0.000362528 | 0.000352051 | 0.000370969 |
| fsm_poly_publish / 0 | 4.42429e-05 | 4.2471e-05 | 3.93874e-05 |
| fsm_replan_callback / 0 | 0.000312199 | 0.000327948 | 0.000315795 |
| fsm_replan_core / 0 | 0.00031301 | 0.000280008 | 0.000299767 |
| guard_brake / 0 | N/A | 3.06957e-06 | 9.07938e-06 |
| guard_certificate / 0 | 0.0012872 | 0.000965131 | 0.00102234 |
| guard_recover / 0 | N/A | 1.17036e-05 | 3.01403e-05 |
| map_ack_and_log / 0 | 0.000784736 | 0.00135828 | 0.00133205 |
| map_cloud_enqueue / 0 | 6.4701e-05 | 7.74385e-05 | 8.62623e-05 |
| map_odom_callback / 0 | 0.00100885 | 0.00112237 | 0.00110593 |
| map_prob_update / 0 | 0.301957 | 0.10849 | 0.121427 |
| map_ros_to_pcl / 0 | 0.00514925 | 0.00136793 | 0.00181636 |
| map_snapshot_commit_health / 0 | 0.0536663 | 0.0230692 | 0.0247845 |
| map_worker / 0 | 8.05715e-05 | 6.80505e-05 | 7.55455e-05 |
| planner_backup_optimize / 0 | 0.0287997 | 0.0267085 | 0.0195565 |
| planner_commit / 0 | 0.000495949 | 0.000436145 | 0.00041185 |
| planner_corridor_search / 0 | 0.0104842 | 0.0102203 | 0.00997407 |
| planner_exp_optimize / 0 | 0.0594504 | 0.045109 | 0.0510586 |
| planner_generate_backup / 0 | 0.0212613 | 0.0179923 | 0.0155957 |
| planner_generate_exp / 0 | 0.000489245 | 0.00048063 | 0.000466243 |
| planner_path_search / 0 | 0.0141084 | 0.0162218 | 0.0161315 |
| planner_stop_viability / 0 | 0.000350547 | 0.000372691 | 0.00032957 |
| planner_validate_geometry / 0 | 0.00511926 | 0.00497731 | 0.00421292 |
| planner_velocity_extrema / 0 | 0.000124417 | 0.000106042 | 9.76548e-05 |
| planner_visualize_path / 0 | 0.000645083 | 0.000309092 | 0.000416252 |
| sim_odom_callback / 0 | 0.00676939 | 0.0130739 | 0.0130971 |
| sim_render_callback / 0 | 0.045761 | 0.0172486 | 0.02343 |

Source: `/root/super-sector-filter/results/c24_normal_validation_20260917/iteration01/preflight/seed5/r01_run18002/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.09636e-05 | 2.54731e-05 |
| frontend_cloud / 0 | N/A | 0.000115873 | 0.000112295 |
| frontend_enqueue / 0 | N/A | 5.07447e-05 | 4.42744e-05 |
| frontend_guard_status / 0 | N/A | N/A | 6.26482e-06 |
| frontend_map_ack / 0 | N/A | N/A | 1.69962e-05 |
| frontend_odom / 0 | N/A | 0.000442126 | 0.000561295 |
| frontend_replan_status / 0 | N/A | N/A | 1.17665e-05 |
| frontend_report / 0 | N/A | 1.50517e-05 | 9.55113e-06 |
| frontend_stats / 0 | N/A | 0.000797932 | 0.000621845 |
| fsm_command_callback / 0 | 0.00974945 | 0.00618476 | 0.00694307 |
| fsm_main_callback / 0 | 0.000537391 | 0.000513296 | 0.000557294 |
| fsm_main_core / 0 | 0.000319859 | 0.000326869 | 0.000340234 |
| fsm_poly_publish / 0 | 3.73585e-05 | 3.34476e-05 | 4.35107e-05 |
| fsm_replan_callback / 0 | 0.00026644 | 0.000297624 | 0.000292316 |
| fsm_replan_core / 0 | 0.000296154 | 0.000300255 | 0.000334442 |
| guard_brake / 0 | 2.8667e-05 | 4.2001e-05 | 2.94663e-05 |
| guard_certificate / 0 | 0.0011195 | 0.000919164 | 0.0010212 |
| guard_recover / 0 | 7.74016e-05 | 6.15149e-05 | 2.41296e-05 |
| map_ack_and_log / 0 | 0.00078317 | 0.00134332 | 0.00133793 |
| map_cloud_enqueue / 0 | 6.18266e-05 | 6.55069e-05 | 7.32764e-05 |
| map_odom_callback / 0 | 0.000956157 | 0.00102898 | 0.000975146 |
| map_prob_update / 0 | 0.341703 | 0.106696 | 0.11993 |
| map_ros_to_pcl / 0 | 0.00739499 | 0.00153874 | 0.00167349 |
| map_snapshot_commit_health / 0 | 0.0579774 | 0.024229 | 0.0265462 |
| map_worker / 0 | 8.106e-05 | 6.68467e-05 | 7.03554e-05 |
| planner_backup_optimize / 0 | 0.0364352 | 0.0384173 | 0.0277723 |
| planner_commit / 0 | 0.000439535 | 0.00040686 | 0.00041894 |
| planner_corridor_search / 0 | 0.0109971 | 0.0112418 | 0.00994904 |
| planner_exp_optimize / 0 | 0.071764 | 0.0600181 | 0.0523185 |
| planner_generate_backup / 0 | 0.0185098 | 0.0173563 | 0.0169804 |
| planner_generate_exp / 0 | 0.000430912 | 0.00048313 | 0.000454598 |
| planner_path_search / 0 | 0.0196671 | 0.0192333 | 0.0157276 |
| planner_stop_viability / 0 | 0.000293248 | 0.000297776 | 0.000352377 |
| planner_validate_geometry / 0 | 0.00416954 | 0.00397945 | 0.00453942 |
| planner_velocity_extrema / 0 | 0.000102698 | 9.23173e-05 | 0.000106889 |
| planner_visualize_path / 0 | 0.000554729 | 0.000333368 | 0.00043744 |
| sim_odom_callback / 0 | 0.00714445 | 0.012507 | 0.0115683 |
| sim_render_callback / 0 | 0.0422405 | 0.0151087 | 0.0195076 |

Source: `/root/super-sector-filter/results/c24_normal_validation_20260917/iteration01/preflight/seed7/r01_run18003/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 2.67741e-05 | 2.09985e-05 |
| frontend_cloud / 0 | N/A | 0.000112704 | 0.000113521 |
| frontend_enqueue / 0 | N/A | 4.37365e-05 | 5.14737e-05 |
| frontend_guard_status / 0 | N/A | N/A | 1.22688e-05 |
| frontend_map_ack / 0 | N/A | N/A | 2.22247e-05 |
| frontend_odom / 0 | N/A | 0.000413357 | 0.000517975 |
| frontend_replan_status / 0 | N/A | N/A | 1.13514e-05 |
| frontend_report / 0 | N/A | 1.8159e-05 | 1.08435e-05 |
| frontend_stats / 0 | N/A | 0.000988822 | 0.000738882 |
| fsm_command_callback / 0 | 0.00940993 | 0.0106029 | 0.00941771 |
| fsm_main_callback / 0 | 0.000553234 | 0.000611609 | 0.000558718 |
| fsm_main_core / 0 | 0.000309959 | 0.000369443 | 0.000331691 |
| fsm_poly_publish / 0 | 3.72092e-05 | 3.73782e-05 | 4.39776e-05 |
| fsm_replan_callback / 0 | 0.000272541 | 0.000309819 | 0.00030544 |
| fsm_replan_core / 0 | 0.000307874 | 0.000308146 | 0.000347409 |
| guard_brake / 0 | 4.60108e-05 | 2.81029e-05 | 3.28527e-05 |
| guard_certificate / 0 | 0.00105272 | 0.00127532 | 0.0010768 |
| guard_recover / 0 | 9.17076e-05 | 4.68529e-05 | 5.92266e-05 |
| map_ack_and_log / 0 | 0.000775958 | 0.00135154 | 0.00144157 |
| map_cloud_enqueue / 0 | 6.39856e-05 | 6.30077e-05 | 6.80338e-05 |
| map_odom_callback / 0 | 0.000958491 | 0.000874116 | 0.000879634 |
| map_prob_update / 0 | 0.319938 | 0.108858 | 0.126229 |
| map_ros_to_pcl / 0 | 0.00780062 | 0.00189492 | 0.00252872 |
| map_snapshot_commit_health / 0 | 0.0527474 | 0.0233338 | 0.0263132 |
| map_worker / 0 | 7.92163e-05 | 7.1515e-05 | 6.81599e-05 |
| planner_backup_optimize / 0 | 0.034027 | 0.0344651 | 0.0327712 |
| planner_commit / 0 | 0.000464041 | 0.00045053 | 0.000452948 |
| planner_corridor_search / 0 | 0.0126144 | 0.0119487 | 0.0123288 |
| planner_exp_optimize / 0 | 0.0651657 | 0.0670761 | 0.0621921 |
| planner_generate_backup / 0 | 0.0197015 | 0.0164363 | 0.0197139 |
| planner_generate_exp / 0 | 0.000469264 | 0.000473089 | 0.000508905 |
| planner_path_search / 0 | 0.0291721 | 0.0279502 | 0.0305425 |
| planner_stop_viability / 0 | 0.000293995 | 0.0003403 | 0.000331409 |
| planner_validate_geometry / 0 | 0.0039983 | 0.00411418 | 0.00395856 |
| planner_velocity_extrema / 0 | 0.000107841 | 9.61178e-05 | 0.000104409 |
| planner_visualize_path / 0 | 0.000543883 | 0.000679384 | 0.000526703 |
| sim_odom_callback / 0 | 0.00716874 | 0.00776405 | 0.0085358 |
| sim_render_callback / 0 | 0.0513267 | 0.0162129 | 0.0182843 |

Source: `/root/super-sector-filter/results/c24_normal_validation_20260917/iteration01/preflight/seed9/r01_run18004/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | 3.17877e-05 | 2.70733e-05 |
| frontend_cloud / 0 | N/A | 0.000125125 | 0.000119989 |
| frontend_enqueue / 0 | N/A | 4.89972e-05 | 4.73019e-05 |
| frontend_guard_status / 0 | N/A | N/A | 2.17646e-05 |
| frontend_map_ack / 0 | N/A | N/A | 2.09445e-05 |
| frontend_odom / 0 | N/A | 0.000447436 | 0.000544488 |
| frontend_replan_status / 0 | N/A | N/A | 1.1183e-05 |
| frontend_report / 0 | N/A | 1.44351e-05 | 1.29351e-05 |
| frontend_stats / 0 | N/A | 0.000631936 | 0.000832386 |
| fsm_command_callback / 0 | 0.00761584 | 0.0111141 | 0.00849183 |
| fsm_main_callback / 0 | 0.000498891 | 0.000592614 | 0.00056098 |
| fsm_main_core / 0 | 0.000304332 | 0.000322039 | 0.000314746 |
| fsm_poly_publish / 0 | 3.49685e-05 | 3.66082e-05 | 3.38582e-05 |
| fsm_replan_callback / 0 | 0.000253788 | 0.000312338 | 0.000285429 |
| fsm_replan_core / 0 | 0.000317213 | 0.000298266 | 0.000349106 |
| guard_brake / 0 | 1.34455e-05 | 1.82432e-05 | 5.58745e-05 |
| guard_certificate / 0 | 0.000963956 | 0.00118008 | 0.00104272 |
| guard_recover / 0 | 0.000105497 | 0.000123055 | 8.913e-05 |
| map_ack_and_log / 0 | 0.000768437 | 0.00137886 | 0.00136224 |
| map_cloud_enqueue / 0 | 5.69674e-05 | 7.39281e-05 | 7.08752e-05 |
| map_odom_callback / 0 | 0.0010271 | 0.000901585 | 0.00101513 |
| map_prob_update / 0 | 0.31093 | 0.107237 | 0.127784 |
| map_ros_to_pcl / 0 | 0.00948052 | 0.00224642 | 0.00284309 |
| map_snapshot_commit_health / 0 | 0.0520243 | 0.0218278 | 0.0268277 |
| map_worker / 0 | 9.02153e-05 | 7.30722e-05 | 7.11908e-05 |
| planner_backup_optimize / 0 | 0.0500118 | 0.0258151 | 0.0371173 |
| planner_commit / 0 | 0.000436047 | 0.000426318 | 0.000399879 |
| planner_corridor_search / 0 | 0.0122299 | 0.0112015 | 0.0128182 |
| planner_exp_optimize / 0 | 0.0734935 | 0.0545179 | 0.0714249 |
| planner_generate_backup / 0 | 0.0224438 | 0.0152769 | 0.0183064 |
| planner_generate_exp / 0 | 0.000479212 | 0.000449772 | 0.00048166 |
| planner_path_search / 0 | 0.0329688 | 0.0306673 | 0.0390319 |
| planner_stop_viability / 0 | 0.000295532 | 0.000302283 | 0.00027662 |
| planner_validate_geometry / 0 | 0.00405793 | 0.00374353 | 0.0035462 |
| planner_velocity_extrema / 0 | 0.000107134 | 9.28232e-05 | 9.32728e-05 |
| planner_visualize_path / 0 | 0.000432345 | 0.000592841 | 0.000486172 |
| sim_odom_callback / 0 | 0.0101287 | 0.00931191 | 0.0117519 |
| sim_render_callback / 0 | 0.0493877 | 0.0172051 | 0.0207895 |

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
