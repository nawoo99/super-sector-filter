# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c20_bounded_certificate_refresh — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 3 | 2 | 3 |
| Successes | 3 | 2 | 3 |
| Valid runs | 3 | 2 | 3 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 5 runs per mode; INCOMPLETE — planned rows still missing. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 38.523 ± 0.9097 [37.7, 39.5] | 39.735 ± 0.1768 [39.61, 39.86] | 38.39 ± 0.3751 [37.96, 38.65] | -3.15% | 0.35% |
| Path length (m) | 224.1 ± 1.591 [222.49, 225.67] | 222.34 ± 0.9737 [221.65, 223.03] | 222.67 ± 0.9385 [221.6, 223.36] | 0.79% | 0.64% |
| Minimum static-PC clearance (m) | 0.31967 ± 0.03002 [0.289, 0.349] | 0.288 ± 0.116 [0.206, 0.37] | 0.33967 ± 0.01079 [0.332, 0.352] | 9.91% | -6.26% |
| Experiment CPU (cores) | 0.52368 ± 0.001188 [0.52232, 0.52448] | 0.35056 ± 0.006712 [0.34581, 0.35531] | 0.35706 ± 0.007054 [0.34915, 0.36269] | 33.06% | 31.82% |
| Experiment CPU (whole-host %) | 2.6184 ± 0.005942 [2.6116, 2.6224] | 1.7528 ± 0.03356 [1.7291, 1.7765] | 1.7853 ± 0.03527 [1.7457, 1.8134] | 33.06% | 31.82% |
| Experiment measurement-window CPU (core-s) | 20.887 ± 0.3359 [20.69, 21.275] | 14.594 ± 0.3001 [14.381, 14.806] | 14.386 ± 0.4718 [13.848, 14.729] | 30.13% | 31.13% |
| Accounting window (s) | 39.885 ± 0.6078 [39.46, 40.581] | 41.629 ± 0.05904 [41.587, 41.67] | 40.282 ± 0.5383 [39.661, 40.609] | -4.37% | -1.00% |
| Experiment CPU 1 s p95 (cores) | 0.63913 ± 0.05028 [0.60712, 0.69708] | 0.43285 ± 0.0384 [0.4057, 0.46] | 0.47204 ± 0.02335 [0.44551, 0.48949] | 32.27% | 26.14% |
| Experiment CPU 1 s maximum (cores) | 0.81263 ± 0.2535 [0.66054, 1.1053] | 0.49292 ± 0.03908 [0.46529, 0.52056] | 0.50584 ± 0.06177 [0.45485, 0.57452] | 39.34% | 37.75% |
| Composed runtime CPU (cores; includes simulator) | 0.48399 ± 0.0002583 [0.4838, 0.48428] | 0.30477 ± 0.006782 [0.29998, 0.30957] | 0.31321 ± 0.009909 [0.30187, 0.32022] | 37.03% | 35.29% |
| Composed runtime measurement-window CPU (core-s) | 19.304 ± 0.3041 [19.095, 19.653] | 12.687 ± 0.3003 [12.475, 12.9] | 12.62 ± 0.5631 [11.972, 12.993] | 34.28% | 34.62% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.8199 ± 0.1284 [3.6975, 3.9536] | 3.9381 ± 0.2213 [3.7817, 4.0946] | 4.0119 ± 0.1709 [3.8782, 4.2044] | -3.09% | -5.03% |
| Whole-host CPU (%) | 9.0618 ± 0.272 [8.8508, 9.3688] | 9.3177 ± 0.2234 [9.1597, 9.4756] | 9.291 ± 0.09027 [9.1924, 9.3697] | -2.82% | -2.53% |
| Baseline whole-host CPU (%) | 7.7005 ± 0.461 [7.2281, 8.1492] | 8.0096 ± 0.6084 [7.5794, 8.4399] | 7.045 ± 0.4887 [6.6742, 7.5987] | -4.01% | 8.51% |
| Experiment sampled peak RSS (MiB) | 3384 ± 1.789 [3382.6, 3386] | 3376.4 ± 1.594 [3375.3, 3377.6] | 3377.7 ± 2.492 [3374.9, 3379.7] | 0.22% | 0.19% |
| Experiment sampled peak PSS (MiB) | 3343.8 ± 1.929 [3342.3, 3346] | 3336.4 ± 1.628 [3335.3, 3337.6] | 3337.5 ± 2.485 [3334.8, 3339.7] | 0.22% | 0.19% |
| Experiment sampled peak process swap (MiB) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5771.4 ± 33.26 [5739, 5805.4] | 5717.1 ± 35.51 [5692, 5742.2] | 5781.4 ± 52.06 [5722.5, 5821.4] | 0.94% | -0.17% |
| GPU device utilization (%) | 51.78 ± 1.897 [50.317, 53.923] | 53.564 ± 0.2801 [53.366, 53.762] | 50.305 ± 4.873 [47.282, 55.927] | -3.45% | 2.85% |
| GPU device utilization p95 (%) | 55.333 ± 2.309 [54, 58] | 57.5 ± 0.7071 [57, 58] | 53.333 ± 4.041 [51, 58] | -3.92% | 3.61% |
| GPU device memory-controller utilization (%) | 18.991 ± 0.03862 [18.949, 19.024] | 19 ± 0 [19, 19] | 19.009 ± 0.0148 [19, 19.026] | -0.05% | -0.09% |
| GPU device memory (MiB) | 1266.8 ± 4.449 [1264.2, 1271.9] | 1267.4 ± 3.78 [1264.8, 1270.1] | 1266.7 ± 2.389 [1265.3, 1269.5] | -0.05% | 0.01% |
| GPU device power (W; not flight attribution) | 18.832 ± 0.02198 [18.81, 18.853] | 18.809 ± 0.01633 [18.798, 18.821] | 18.806 ± 0.01556 [18.796, 18.824] | 0.12% | 0.14% |
| Observed source frame records | 398 ± 6.083 [394, 405] | 415.5 ± 0.7071 [415, 416] | 401.67 ± 5.774 [395, 405] | -4.40% | -0.92% |
| Observed source readback width (pixels/frame) | 900 ± 0 [900, 900] | 225 ± 0 [225, 225] | 249.61 ± 3.928 [245.51, 253.33] | 75.00% | 72.27% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 ± 0 [8.01e+05, 8.01e+05] | 2.0025e+05 ± 0 [2.0025e+05, 2.0025e+05] | 2.2216e+05 ± 3496 [2.185e+05, 2.2547e+05] | 75.00% | 72.27% |
| Observed source conversion rays (/frame) | 1.152e+05 ± 0 [1.152e+05, 1.152e+05] | 28800 ± 0 [28800, 28800] | 31950 ± 502.8 [31425, 32427] | 75.00% | 72.27% |
| Observed source generated points (/frame) | 15869 ± 773.1 [15109, 16654] | 4248 ± 27.82 [4228.3, 4267.6] | 4787.8 ± 164.8 [4609, 4933.6] | 73.23% | 69.83% |
| Observed source cloud payload (bytes/frame) | 5.0782e+05 ± 2.474e+04 [4.8349e+05, 5.3294e+05] | 1.3593e+05 ± 890.2 [1.3531e+05, 1.3656e+05] | 1.5321e+05 ± 5273 [1.4749e+05, 1.5787e+05] | 73.23% | 69.83% |
| Map total elapsed mean (ms/frame) | 24.425 ± 0.4946 [23.871, 24.822] | 9.4059 ± 0.03145 [9.3837, 9.4282] | 10.204 ± 0.2526 [9.9438, 10.448] | 61.49% | 58.22% |
| Map total elapsed p95 (ms/frame) | 31.883 ± 0.579 [31.218, 32.274] | 14.304 ± 0.05614 [14.264, 14.343] | 16.135 ± 0.8854 [15.13, 16.799] | 55.14% | 49.39% |
| Map total elapsed max (ms/frame) | 59.542 ± 17.41 [48.934, 79.636] | 23.944 ± 8.673 [17.812, 30.077] | 40.828 ± 3.731 [36.805, 44.174] | 59.79% | 31.43% |
| Map raycast elapsed mean (ms/frame) | 15.062 ± 0.2968 [14.769, 15.362] | 6.2893 ± 0.02232 [6.2735, 6.3051] | 6.6689 ± 0.1943 [6.4666, 6.854] | 58.24% | 55.72% |
| Map update elapsed mean (ms/frame) | 9.3611 ± 0.228 [9.1006, 9.5247] | 3.1151 ± 0.009143 [3.1087, 3.1216] | 3.5336 ± 0.0585 [3.4759, 3.5928] | 66.72% | 62.25% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2302 ± 0.02757 [1.2003, 1.2546] | 0.63024 ± 0.004593 [0.62699, 0.63349] | 0.69054 ± 0.01878 [0.67373, 0.71081] | 48.77% | 43.87% |
| Map processed frames / mission time (Hz proxy) | 10.333 ± 0.1253 [10.253, 10.477] | 10.457 ± 0.02873 [10.437, 10.477] | 10.462 ± 0.05068 [10.406, 10.503] | -1.20% | -1.25% |
| Trajectory commits (Hz) | 3.0509 ± 0.1416 [2.9387, 3.21] | 3.1527 ± 0.07276 [3.1013, 3.2042] | 3.2321 ± 0.1183 [3.1612, 3.3687] | -3.34% | -5.94% |
| Goal retransmissions coalesced | 33 ± 2 [31, 35] | 29.5 ± 0.7071 [29, 30] | 30.667 ± 0.5774 [30, 31] | 10.61% | 7.07% |
| Demand replan checks (latest cumulative report) | 545.33 ± 31.82 [525, 582] | 576.5 ± 7.778 [571, 582] | 553.33 ± 40.2 [507, 579] | -5.72% | -1.47% |
| Demand replans skipped (latest cumulative report) | 407.33 ± 24.83 [393, 436] | 421.5 ± 7.778 [416, 427] | 399.67 ± 26.27 [370, 420] | -3.48% | 1.88% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.01605 ± 4.312e-06 [0.016047, 0.016053] | 0.01674 ± 0.003784 [0.014106, 0.021076] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.059 ± 0.02404 [0.042, 0.076] | 0.94833 ± 1.418 [0.105, 2.586] | N/A | N/A |
| Map points mean (/frame) | 15869 ± 773.1 [15109, 16654] | 4248 ± 27.82 [4228.3, 4267.6] | 4787.8 ± 164.8 [4609, 4933.6] | 73.23% | 69.83% |
| Map points / mission time (points/s proxy) | 1.6404e+05 ± 9860 [1.5491e+05, 1.745e+05] | 44420 ± 168.9 [44300, 44539] | 50098 ± 1963 [47960, 51818] | 72.92% | 69.46% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.006 ± 0.3009 [4.7276, 5.3252] | 1.3556 ± 0.005153 [1.3519, 1.3592] | 1.5289 ± 0.05989 [1.4636, 1.5814] | 72.92% | 69.46% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.9021 ± 0.2841 [4.6292, 5.1963] | 1.3303 ± 0.0103 [1.323, 1.3375] | 1.493 ± 0.02581 [1.4703, 1.5211] | 72.86% | 69.54% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.006 ± 0.3009 [4.7276, 5.3252] | 1.3556 ± 0.005153 [1.3519, 1.3592] | 1.5289 ± 0.05989 [1.4636, 1.5814] | 72.92% | 69.46% |
| DDS cloud payload (MiB/s, logical messages) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 ± 0.0002018 [10, 10.001] | 10 ± 0.0002206 [10, 10.001] | 10.001 ± 0.0002249 [10, 10.001] | -0.00% | -0.00% |
| Received odometry frequency (Hz) | 99.967 ± 0.05675 [99.902, 100] | 99.999 ± 0.00167 [99.998, 100] | 100 ± 0.002248 [99.998, 100] | -0.03% | -0.03% |
| Received command frequency (Hz; holds included) | 95.289 ± 0.4408 [94.828, 95.706] | 93.989 ± 0.4259 [93.688, 94.29] | 95.415 ± 0.5481 [94.818, 95.895] | 1.36% | -0.13% |
| Odometry receipt p99 gap (ms) | 10.701 ± 0.1858 [10.551, 10.909] | 10.814 ± 0.00912 [10.807, 10.82] | 10.979 ± 0.2661 [10.792, 11.284] | -1.05% | -2.60% |
| Odometry receipt max gap (ms) | 26.812 ± 26.65 [10.901, 57.574] | 11.766 ± 0.5553 [11.373, 12.158] | 12.733 ± 2.252 [11.332, 15.331] | 56.12% | 52.51% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.3333 ± 0.5774 [1, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 ± 0 [0, 0] | 3.713 ± 0.6372 [3.038, 4.304] | N/A | N/A |
| Guard active duration (s) | 0.29524 ± 0.4256 [0.033009, 0.78625] | 1.5634 ± 0.4022 [1.279, 1.8478] | 1.5344 ± 0.2676 [1.2408, 1.7646] | -429.54% | -419.72% |

## seed1 — c20_bounded_certificate_refresh — profiled_supplement

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
| Mission time (s) | 36.6 (n=1) [36.6, 36.6] | 39.31 (n=1) [39.31, 39.31] | 39.83 (n=1) [39.83, 39.83] | -7.40% | -8.83% |
| Path length (m) | 220.73 (n=1) [220.73, 220.73] | 222.84 (n=1) [222.84, 222.84] | 223.42 (n=1) [223.42, 223.42] | -0.95% | -1.22% |
| Minimum static-PC clearance (m) | 0.343 (n=1) [0.343, 0.343] | 0.262 (n=1) [0.262, 0.262] | 0.329 (n=1) [0.329, 0.329] | 23.62% | 4.08% |
| Experiment CPU (cores) | 0.54412 (n=1) [0.54412, 0.54412] | 0.33483 (n=1) [0.33483, 0.33483] | 0.35364 (n=1) [0.35364, 0.35364] | 38.46% | 35.01% |
| Experiment CPU (whole-host %) | 2.7206 (n=1) [2.7206, 2.7206] | 1.6741 (n=1) [1.6741, 1.6741] | 1.7682 (n=1) [1.7682, 1.7682] | 38.46% | 35.01% |
| Experiment measurement-window CPU (core-s) | 20.91 (n=1) [20.91, 20.91] | 13.584 (n=1) [13.584, 13.584] | 14.722 (n=1) [14.722, 14.722] | 35.04% | 29.60% |
| Accounting window (s) | 38.429 (n=1) [38.429, 38.429] | 40.569 (n=1) [40.569, 40.569] | 41.629 (n=1) [41.629, 41.629] | -5.57% | -8.33% |
| Experiment CPU 1 s p95 (cores) | 0.71278 (n=1) [0.71278, 0.71278] | 0.41173 (n=1) [0.41173, 0.41173] | 0.45055 (n=1) [0.45055, 0.45055] | 42.24% | 36.79% |
| Experiment CPU 1 s maximum (cores) | 0.71646 (n=1) [0.71646, 0.71646] | 0.42147 (n=1) [0.42147, 0.42147] | 0.46807 (n=1) [0.46807, 0.46807] | 41.17% | 34.67% |
| Composed runtime CPU (cores; includes simulator) | 0.50156 (n=1) [0.50156, 0.50156] | 0.29254 (n=1) [0.29254, 0.29254] | 0.31497 (n=1) [0.31497, 0.31497] | 41.67% | 37.20% |
| Composed runtime measurement-window CPU (core-s) | 19.274 (n=1) [19.274, 19.274] | 11.868 (n=1) [11.868, 11.868] | 13.112 (n=1) [13.112, 13.112] | 38.43% | 31.97% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.69 (n=1) [3.69, 3.69] | 3.9254 (n=1) [3.9254, 3.9254] | 3.8576 (n=1) [3.8576, 3.8576] | -6.38% | -4.54% |
| Whole-host CPU (%) | 9.7119 (n=1) [9.7119, 9.7119] | 9.6621 (n=1) [9.6621, 9.6621] | 9.2672 (n=1) [9.2672, 9.2672] | 0.51% | 4.58% |
| Baseline whole-host CPU (%) | 7.6549 (n=1) [7.6549, 7.6549] | 7.4857 (n=1) [7.4857, 7.4857] | 7.0606 (n=1) [7.0606, 7.0606] | 2.21% | 7.76% |
| Experiment sampled peak RSS (MiB) | 3381.9 (n=1) [3381.9, 3381.9] | 3376.1 (n=1) [3376.1, 3376.1] | 3379.6 (n=1) [3379.6, 3379.6] | 0.17% | 0.07% |
| Experiment sampled peak PSS (MiB) | 3341.4 (n=1) [3341.4, 3341.4] | 3336 (n=1) [3336, 3336] | 3339.3 (n=1) [3339.3, 3339.3] | 0.16% | 0.06% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5723 (n=1) [5723, 5723] | 5742.3 (n=1) [5742.3, 5742.3] | 5723.7 (n=1) [5723.7, 5723.7] | -0.34% | -0.01% |
| GPU device utilization (%) | 53.711 (n=1) [53.711, 53.711] | 51.55 (n=1) [51.55, 51.55] | 47.667 (n=1) [47.667, 47.667] | 4.02% | 11.25% |
| GPU device utilization p95 (%) | 59 (n=1) [59, 59] | 56 (n=1) [56, 56] | 52 (n=1) [52, 52] | 5.08% | 11.86% |
| GPU device memory-controller utilization (%) | 18.868 (n=1) [18.868, 18.868] | 18.95 (n=1) [18.95, 18.95] | 19.024 (n=1) [19.024, 19.024] | -0.43% | -0.82% |
| GPU device memory (MiB) | 1280.7 (n=1) [1280.7, 1280.7] | 1279.1 (n=1) [1279.1, 1279.1] | 1279 (n=1) [1279, 1279] | 0.13% | 0.13% |
| GPU device power (W; not flight attribution) | 18.766 (n=1) [18.766, 18.766] | 18.81 (n=1) [18.81, 18.81] | 18.733 (n=1) [18.733, 18.733] | -0.23% | 0.17% |
| Observed source frame records | 384 (n=1) [384, 384] | 405 (n=1) [405, 405] | 415 (n=1) [415, 415] | -5.47% | -8.07% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 257.53 (n=1) [257.53, 257.53] | 75.00% | 71.39% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.292e+05 (n=1) [2.292e+05, 2.292e+05] | 75.00% | 71.39% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 32964 (n=1) [32964, 32964] | 75.00% | 71.39% |
| Observed source generated points (/frame) | 15260 (n=1) [15260, 15260] | 4457.1 (n=1) [4457.1, 4457.1] | 5124.7 (n=1) [5124.7, 5124.7] | 70.79% | 66.42% |
| Observed source cloud payload (bytes/frame) | 4.8831e+05 (n=1) [4.8831e+05, 4.8831e+05] | 1.4263e+05 (n=1) [1.4263e+05, 1.4263e+05] | 1.6399e+05 (n=1) [1.6399e+05, 1.6399e+05] | 70.79% | 66.42% |
| Map total elapsed mean (ms/frame) | 25.918 (n=1) [25.918, 25.918] | 9.6077 (n=1) [9.6077, 9.6077] | 10.168 (n=1) [10.168, 10.168] | 62.93% | 60.77% |
| Map total elapsed p95 (ms/frame) | 32.913 (n=1) [32.913, 32.913] | 14.469 (n=1) [14.469, 14.469] | 18.112 (n=1) [18.112, 18.112] | 56.04% | 44.97% |
| Map total elapsed max (ms/frame) | 61.554 (n=1) [61.554, 61.554] | 29.733 (n=1) [29.733, 29.733] | 38.339 (n=1) [38.339, 38.339] | 51.69% | 37.71% |
| Map raycast elapsed mean (ms/frame) | 15.956 (n=1) [15.956, 15.956] | 6.3967 (n=1) [6.3967, 6.3967] | 6.6245 (n=1) [6.6245, 6.6245] | 59.91% | 58.48% |
| Map update elapsed mean (ms/frame) | 9.9605 (n=1) [9.9605, 9.9605] | 3.2099 (n=1) [3.2099, 3.2099] | 3.542 (n=1) [3.542, 3.542] | 67.77% | 64.44% |
| Map inflation elapsed mean (ms/frame; nested) | 1.3118 (n=1) [1.3118, 1.3118] | 0.66287 (n=1) [0.66287, 0.66287] | 0.68213 (n=1) [0.68213, 0.68213] | 49.47% | 48.00% |
| Map processed frames / mission time (Hz proxy) | 10.464 (n=1) [10.464, 10.464] | 10.303 (n=1) [10.303, 10.303] | 10.419 (n=1) [10.419, 10.419] | 1.55% | 0.43% |
| Trajectory commits (Hz) | 3.2743 (n=1) [3.2743, 3.2743] | 3.1076 (n=1) [3.1076, 3.1076] | 3.093 (n=1) [3.093, 3.093] | 5.09% | 5.54% |
| Goal retransmissions coalesced | 28 (n=1) [28, 28] | 35 (n=1) [35, 35] | 32 (n=1) [32, 32] | -25.00% | -14.29% |
| Demand replan checks (latest cumulative report) | 525 (n=1) [525, 525] | 600 (n=1) [600, 600] | 573 (n=1) [573, 573] | -14.29% | -9.14% |
| Demand replans skipped (latest cumulative report) | 396 (n=1) [396, 396] | 447 (n=1) [447, 447] | 426 (n=1) [426, 426] | -12.88% | -7.58% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.01962 (n=1) [0.01962, 0.01962] | 0.022822 (n=1) [0.022822, 0.022822] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.115 (n=1) [0.115, 0.115] | 0.858 (n=1) [0.858, 0.858] | N/A | N/A |
| Map points mean (/frame) | 15274 (n=1) [15274, 15274] | 4457.1 (n=1) [4457.1, 4457.1] | 5124.7 (n=1) [5124.7, 5124.7] | 70.82% | 66.45% |
| Map points / mission time (points/s proxy) | 1.5984e+05 (n=1) [1.5984e+05, 1.5984e+05] | 45920 (n=1) [45920, 45920] | 53396 (n=1) [53396, 53396] | 71.27% | 66.59% |
| Map payload / mission time (MiB/s proxy, logical edge) | 4.8779 (n=1) [4.8779, 4.8779] | 1.4014 (n=1) [1.4014, 1.4014] | 1.6295 (n=1) [1.6295, 1.6295] | 71.27% | 66.59% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.6718 (n=1) [4.6718, 4.6718] | 1.3722 (n=1) [1.3722, 1.3722] | 1.5993 (n=1) [1.5993, 1.5993] | 70.63% | 65.77% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 4.8779 (n=1) [4.8779, 4.8779] | 1.4014 (n=1) [1.4014, 1.4014] | 1.6295 (n=1) [1.6295, 1.6295] | 71.27% | 66.59% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | 10.001 (n=1) [10.001, 10.001] | 0.01% | -0.00% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 99.998 (n=1) [99.998, 99.998] | 99.999 (n=1) [99.999, 99.999] | 0.01% | 0.00% |
| Received command frequency (Hz; holds included) | 95.905 (n=1) [95.905, 95.905] | 96.476 (n=1) [96.476, 96.476] | 95.498 (n=1) [95.498, 95.498] | -0.59% | 0.43% |
| Odometry receipt p99 gap (ms) | 10.663 (n=1) [10.663, 10.663] | 10.745 (n=1) [10.745, 10.745] | 10.813 (n=1) [10.813, 10.813] | -0.77% | -1.41% |
| Odometry receipt max gap (ms) | 10.902 (n=1) [10.902, 10.902] | 11.905 (n=1) [11.905, 11.905] | 11.042 (n=1) [11.042, 11.042] | -9.20% | -1.28% |
| Actual FSM main callback frequency (profiled only) | 100 (n=1) [100, 100] | 99.999 (n=1) [99.999, 99.999] | 99.971 (n=1) [99.971, 99.971] | 0.00% | 0.03% |
| Actual FSM command callback frequency (profiled only) | 100 (n=1) [100, 100] | 99.999 (n=1) [99.999, 99.999] | 100 (n=1) [100, 100] | 0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 4.819 (n=1) [4.819, 4.819] | N/A | N/A |
| Guard active duration (s) | 0.035916 (n=1) [0.035916, 0.035916] | 0.34544 (n=1) [0.34544, 0.34544] | 2.1038 (n=1) [2.1038, 2.1038] | -861.80% | -5757.59% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

No separately analyzed profiled stage file available yet; stage CPU is N/A, not zero.

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
