# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c21_timing_validation_3workers — unprofiled_primary

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
| Mission time (s) | 38.152 ± 0.828 [37.07, 39.37] | 39.32 ± 1.219 [37.85, 40.73] | 38.452 ± 0.6991 [37.57, 39.52] | -3.06% | -0.79% |
| Path length (m) | 222.63 ± 0.6826 [221.88, 223.73] | 222.08 ± 2.011 [219.77, 224.65] | 221.86 ± 1.156 [220.13, 223.25] | 0.25% | 0.35% |
| Minimum static-PC clearance (m) | 0.3112 ± 0.003701 [0.305, 0.314] | 0.313 ± 0.0202 [0.288, 0.343] | 0.2882 ± 0.04454 [0.234, 0.353] | -0.58% | 7.39% |
| Experiment CPU (cores) | 0.53882 ± 0.006961 [0.5318, 0.55046] | 0.35202 ± 0.005047 [0.34801, 0.36051] | 0.37018 ± 0.01111 [0.35785, 0.38678] | 34.67% | 31.30% |
| Experiment CPU (whole-host %) | 2.6941 ± 0.03481 [2.659, 2.7523] | 1.7601 ± 0.02524 [1.7401, 1.8025] | 1.8509 ± 0.05555 [1.7893, 1.9339] | 34.67% | 31.30% |
| Experiment measurement-window CPU (core-s) | 21.415 ± 0.471 [20.853, 21.933] | 14.373 ± 0.4377 [13.877, 14.792] | 14.798 ± 0.5855 [14.245, 15.746] | 32.88% | 30.90% |
| Accounting window (s) | 39.745 ± 0.739 [38.739, 40.827] | 40.831 ± 1.083 [39.766, 41.951] | 39.966 ± 0.418 [39.699, 40.709] | -2.73% | -0.56% |
| Experiment CPU 1 s p95 (cores) | 0.63911 ± 0.02397 [0.6067, 0.66905] | 0.45223 ± 0.02105 [0.42804, 0.47317] | 0.47966 ± 0.02536 [0.44578, 0.51539] | 29.24% | 24.95% |
| Experiment CPU 1 s maximum (cores) | 0.74152 ± 0.1221 [0.65554, 0.95571] | 0.49458 ± 0.03635 [0.46458, 0.5386] | 0.52088 ± 0.02546 [0.48638, 0.55806] | 33.30% | 29.75% |
| Composed runtime CPU (cores; includes simulator) | 0.50075 ± 0.008751 [0.49112, 0.51465] | 0.30949 ± 0.004759 [0.30434, 0.31558] | 0.32482 ± 0.01025 [0.31326, 0.33978] | 38.19% | 35.13% |
| Composed runtime measurement-window CPU (core-s) | 19.902 ± 0.4804 [19.331, 20.446] | 12.636 ± 0.3497 [12.108, 12.938] | 12.984 ± 0.5317 [12.47, 13.832] | 36.51% | 34.76% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.3173 ± 0.05967 [4.234, 4.4004] | 4.3852 ± 0.1014 [4.2421, 4.4949] | 4.4583 ± 0.1694 [4.1985, 4.6197] | -1.57% | -3.27% |
| Whole-host CPU (%) | 9.3987 ± 0.2317 [9.1696, 9.7075] | 9.1515 ± 0.2576 [8.9169, 9.5909] | 9.2636 ± 0.35 [8.6578, 9.5622] | 2.63% | 1.44% |
| Baseline whole-host CPU (%) | 7.6394 ± 0.8042 [6.3132, 8.3087] | 7.3377 ± 0.5193 [6.6783, 7.8122] | 7.6361 ± 0.9295 [6.1497, 8.5416] | 3.95% | 0.04% |
| Experiment sampled peak RSS (MiB) | 3385.3 ± 1.231 [3383.7, 3387.2] | 3378.2 ± 2.314 [3374.4, 3380.4] | 3379.6 ± 1.825 [3378.2, 3382.3] | 0.21% | 0.17% |
| Experiment sampled peak PSS (MiB) | 3345.3 ± 1.272 [3343.6, 3347.1] | 3338.1 ± 2.323 [3334.1, 3340.2] | 3339.5 ± 1.9 [3337.9, 3342.4] | 0.21% | 0.17% |
| Experiment sampled peak process swap (MiB) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5737.8 ± 19.17 [5726.9, 5772] | 5742.3 ± 21.97 [5715, 5771.2] | 5766.1 ± 25.02 [5744.8, 5796.1] | -0.08% | -0.49% |
| GPU device utilization (%) | 48.853 ± 1.58 [46.538, 50.641] | 50.316 ± 3.203 [46.927, 53.619] | 53.16 ± 2.956 [48, 55.4] | -2.99% | -8.82% |
| GPU device utilization p95 (%) | 54.2 ± 2.588 [51, 57] | 54.4 ± 3.209 [50, 58] | 56.6 ± 2.702 [52, 59] | -0.37% | -4.43% |
| GPU device memory-controller utilization (%) | 19.031 ± 0.04934 [18.974, 19.103] | 19.01 ± 0.03636 [18.952, 19.048] | 19.015 ± 0.03354 [19, 19.075] | 0.11% | 0.08% |
| GPU device memory (MiB) | 1265.2 ± 5.011 [1262.4, 1274.1] | 1265.5 ± 4.708 [1261.1, 1272.7] | 1263.3 ± 4.663 [1259, 1270.5] | -0.03% | 0.15% |
| GPU device power (W; not flight attribution) | 18.817 ± 0.06021 [18.739, 18.907] | 18.715 ± 0.04718 [18.657, 18.784] | 18.7 ± 0.06259 [18.59, 18.743] | 0.55% | 0.63% |
| Observed source frame records | 397.2 ± 7.43 [387, 408] | 407.4 ± 10.5 [397, 418] | 398.4 ± 3.209 [396, 404] | -2.57% | -0.30% |
| Observed source readback width (pixels/frame) | 900 ± 0 [900, 900] | 225 ± 0 [225, 225] | 248.36 ± 4.373 [245.35, 255.07] | 75.00% | 72.40% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 ± 0 [8.01e+05, 8.01e+05] | 2.0025e+05 ± 0 [2.0025e+05, 2.0025e+05] | 2.2104e+05 ± 3892 [2.1836e+05, 2.2702e+05] | 75.00% | 72.40% |
| Observed source conversion rays (/frame) | 1.152e+05 ± 0 [1.152e+05, 1.152e+05] | 28800 ± 0 [28800, 28800] | 31790 ± 559.8 [31405, 32650] | 75.00% | 72.40% |
| Observed source generated points (/frame) | 15954 ± 395.4 [15402, 16297] | 4547.3 ± 99.35 [4441.3, 4686] | 4754.9 ± 220.4 [4443.2, 5063] | 71.50% | 70.20% |
| Observed source cloud payload (bytes/frame) | 5.1053e+05 ± 1.265e+04 [4.9285e+05, 5.215e+05] | 1.4551e+05 ± 3179 [1.4212e+05, 1.4995e+05] | 1.5216e+05 ± 7053 [1.4218e+05, 1.6201e+05] | 71.50% | 70.20% |
| Map total elapsed mean (ms/frame) | 25.359 ± 0.3358 [25.046, 25.923] | 9.4996 ± 0.1711 [9.3041, 9.7736] | 10.322 ± 0.343 [9.8858, 10.673] | 62.54% | 59.30% |
| Map total elapsed p95 (ms/frame) | 31.939 ± 0.5512 [31.414, 32.821] | 14.222 ± 0.3523 [13.919, 14.78] | 16.72 ± 1.358 [15.607, 18.904] | 55.47% | 47.65% |
| Map total elapsed max (ms/frame) | 79.423 ± 16.86 [56.274, 94.934] | 25.705 ± 4.861 [19.6, 33.176] | 39.176 ± 1.396 [37.551, 41.334] | 67.64% | 50.67% |
| Map raycast elapsed mean (ms/frame) | 15.574 ± 0.2069 [15.295, 15.85] | 6.301 ± 0.165 [6.1596, 6.5869] | 6.8121 ± 0.3023 [6.4076, 7.1201] | 59.54% | 56.26% |
| Map update elapsed mean (ms/frame) | 9.7827 ± 0.2308 [9.5331, 10.071] | 3.1972 ± 0.03602 [3.1429, 3.2297] | 3.5086 ± 0.05669 [3.4281, 3.5672] | 67.32% | 64.13% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2772 ± 0.02966 [1.2416, 1.2999] | 0.65228 ± 0.01221 [0.63956, 0.66583] | 0.68581 ± 0.007909 [0.67648, 0.69605] | 48.93% | 46.30% |
| Map processed frames / mission time (Hz proxy) | 10.396 ± 0.05345 [10.338, 10.451] | 10.363 ± 0.08863 [10.263, 10.489] | 10.363 ± 0.1294 [10.223, 10.567] | 0.32% | 0.32% |
| Trajectory commits (Hz) | 3.2304 ± 0.166 [3.0457, 3.3852] | 3.1937 ± 0.09567 [3.0661, 3.2962] | 3.1912 ± 0.2027 [2.8961, 3.4576] | 1.14% | 1.21% |
| Goal retransmissions coalesced | 31.4 ± 1.342 [30, 33] | 31.4 ± 0.8944 [30, 32] | 29.8 ± 3.701 [25, 34] | 0.00% | 5.10% |
| Demand replan checks (latest cumulative report) | 532.4 ± 26.12 [512, 577] | 551 ± 37.85 [503, 596] | 522 ± 31.38 [505, 578] | -3.49% | 1.95% |
| Demand replans skipped (latest cumulative report) | 389.2 ± 24.75 [371, 430] | 404.8 ± 31.55 [371, 446] | 383.4 ± 28.01 [364, 432] | -4.01% | 1.49% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.016199 ± 0.0004664 [0.015742, 0.016906] | 0.020888 ± 0.011 [0.014899, 0.040514] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.1236 ± 0.04125 [0.054, 0.158] | 0.6094 ± 0.988 [0.106, 2.374] | N/A | N/A |
| Map points mean (/frame) | 15963 ± 395.6 [15416, 16297] | 4547.3 ± 99.35 [4441.3, 4686] | 4754.9 ± 220.4 [4443.2, 5063] | 71.51% | 70.21% |
| Map points / mission time (points/s proxy) | 1.6596e+05 ± 4408 [1.5937e+05, 1.6963e+05] | 47122 ± 1070 [45880, 48508] | 49253 ± 1748 [46951, 51757] | 71.61% | 70.32% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.0647 ± 0.1345 [4.8635, 5.1768] | 1.438 ± 0.03265 [1.4002, 1.4803] | 1.5031 ± 0.05335 [1.4328, 1.5795] | 71.61% | 70.32% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.9311 ± 0.147 [4.7379, 5.0619] | 1.4233 ± 0.04421 [1.3746, 1.4586] | 1.5094 ± 0.05659 [1.4126, 1.5605] | 71.14% | 69.39% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.0647 ± 0.1345 [4.8635, 5.1768] | 1.438 ± 0.03265 [1.4002, 1.4803] | 1.5031 ± 0.05335 [1.4328, 1.5795] | 71.61% | 70.32% |
| DDS cloud payload (MiB/s, logical messages) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 ± 0.001118 [10, 10.003] | 10.001 ± 0.0001733 [10, 10.001] | 10 ± 0.0005601 [10, 10.001] | 0.00% | 0.01% |
| Received odometry frequency (Hz) | 100 ± 0.002347 [99.999, 100] | 99.999 ± 0.001748 [99.997, 100] | 100 ± 0.006396 [99.997, 100.01] | 0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 95.184 ± 0.7395 [94.147, 95.935] | 92.385 ± 1.312 [90.262, 93.681] | 94.367 ± 0.8336 [93.397, 95.58] | 2.94% | 0.86% |
| Odometry receipt p99 gap (ms) | 10.717 ± 0.1187 [10.617, 10.914] | 10.896 ± 0.1684 [10.767, 11.191] | 10.957 ± 0.2839 [10.744, 11.451] | -1.67% | -2.24% |
| Odometry receipt max gap (ms) | 12.965 ± 2.791 [11.069, 17.735] | 12.286 ± 1.423 [11.333, 14.783] | 12.515 ± 2.144 [10.962, 16.09] | 5.24% | 3.47% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.4 ± 0.5477 [1, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 ± 0 [0, 0] | 3.4936 ± 0.6793 [3.038, 4.557] | N/A | N/A |
| Guard active duration (s) | 1.0888 ± 0.6542 [0.066777, 1.8358] | 1.4154 ± 1.047 [0.35355, 2.7871] | 1.4474 ± 0.305 [1.2241, 1.9018] | -30.00% | -32.94% |

## seed1 — c21_timing_validation_3workers — profiled_supplement

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
| Mission time (s) | 38.26 (n=1) [38.26, 38.26] | 39.4 (n=1) [39.4, 39.4] | 39.46 (n=1) [39.46, 39.46] | -2.98% | -3.14% |
| Path length (m) | 222.7 (n=1) [222.7, 222.7] | 222.2 (n=1) [222.2, 222.2] | 222.81 (n=1) [222.81, 222.81] | 0.22% | -0.05% |
| Minimum static-PC clearance (m) | 0.329 (n=1) [0.329, 0.329] | 0.365 (n=1) [0.365, 0.365] | 0.323 (n=1) [0.323, 0.323] | -10.94% | 1.82% |
| Experiment CPU (cores) | 0.54525 (n=1) [0.54525, 0.54525] | 0.35111 (n=1) [0.35111, 0.35111] | 0.38336 (n=1) [0.38336, 0.38336] | 35.61% | 29.69% |
| Experiment CPU (whole-host %) | 2.7263 (n=1) [2.7263, 2.7263] | 1.7556 (n=1) [1.7556, 1.7556] | 1.9168 (n=1) [1.9168, 1.9168] | 35.61% | 29.69% |
| Experiment measurement-window CPU (core-s) | 21.667 (n=1) [21.667, 21.667] | 14.283 (n=1) [14.283, 14.283] | 15.605 (n=1) [15.605, 15.605] | 34.08% | 27.98% |
| Accounting window (s) | 39.737 (n=1) [39.737, 39.737] | 40.679 (n=1) [40.679, 40.679] | 40.707 (n=1) [40.707, 40.707] | -2.37% | -2.44% |
| Experiment CPU 1 s p95 (cores) | 0.70881 (n=1) [0.70881, 0.70881] | 0.44202 (n=1) [0.44202, 0.44202] | 0.50557 (n=1) [0.50557, 0.50557] | 37.64% | 28.67% |
| Experiment CPU 1 s maximum (cores) | 0.90088 (n=1) [0.90088, 0.90088] | 0.48102 (n=1) [0.48102, 0.48102] | 0.54616 (n=1) [0.54616, 0.54616] | 46.61% | 39.38% |
| Composed runtime CPU (cores; includes simulator) | 0.50472 (n=1) [0.50472, 0.50472] | 0.30873 (n=1) [0.30873, 0.30873] | 0.34063 (n=1) [0.34063, 0.34063] | 38.83% | 32.51% |
| Composed runtime measurement-window CPU (core-s) | 20.056 (n=1) [20.056, 20.056] | 12.559 (n=1) [12.559, 12.559] | 13.866 (n=1) [13.866, 13.866] | 37.38% | 30.86% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 4.4744 (n=1) [4.4744, 4.4744] | 4.169 (n=1) [4.169, 4.169] | 4.2233 (n=1) [4.2233, 4.2233] | 6.83% | 5.61% |
| Whole-host CPU (%) | 9.5065 (n=1) [9.5065, 9.5065] | 8.8252 (n=1) [8.8252, 8.8252] | 9.1184 (n=1) [9.1184, 9.1184] | 7.17% | 4.08% |
| Baseline whole-host CPU (%) | 8.2623 (n=1) [8.2623, 8.2623] | 7.6465 (n=1) [7.6465, 7.6465] | 7.0822 (n=1) [7.0822, 7.0822] | 7.45% | 14.28% |
| Experiment sampled peak RSS (MiB) | 3390.8 (n=1) [3390.8, 3390.8] | 3374.6 (n=1) [3374.6, 3374.6] | 3381 (n=1) [3381, 3381] | 0.48% | 0.29% |
| Experiment sampled peak PSS (MiB) | 3350.6 (n=1) [3350.6, 3350.6] | 3334.4 (n=1) [3334.4, 3334.4] | 3340.8 (n=1) [3340.8, 3340.8] | 0.48% | 0.29% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5779.7 (n=1) [5779.7, 5779.7] | 5813.4 (n=1) [5813.4, 5813.4] | 5729.6 (n=1) [5729.6, 5729.6] | -0.58% | 0.87% |
| GPU device utilization (%) | 51.525 (n=1) [51.525, 51.525] | 49.366 (n=1) [49.366, 49.366] | 55.2 (n=1) [55.2, 55.2] | 4.19% | -7.13% |
| GPU device utilization p95 (%) | 56 (n=1) [56, 56] | 53 (n=1) [53, 53] | 57 (n=1) [57, 57] | 5.36% | -1.79% |
| GPU device memory-controller utilization (%) | 19 (n=1) [19, 19] | 19 (n=1) [19, 19] | 19.025 (n=1) [19.025, 19.025] | 0.00% | -0.13% |
| GPU device memory (MiB) | 1276.2 (n=1) [1276.2, 1276.2] | 1274.8 (n=1) [1274.8, 1274.8] | 1274.9 (n=1) [1274.9, 1274.9] | 0.11% | 0.11% |
| GPU device power (W; not flight attribution) | 18.802 (n=1) [18.802, 18.802] | 18.802 (n=1) [18.802, 18.802] | 18.8 (n=1) [18.8, 18.8] | -0.00% | 0.01% |
| Observed source frame records | 397 (n=1) [397, 397] | 406 (n=1) [406, 406] | 404 (n=1) [404, 404] | -2.27% | -1.76% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 260.09 (n=1) [260.09, 260.09] | 75.00% | 71.10% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.3148e+05 (n=1) [2.3148e+05, 2.3148e+05] | 75.00% | 71.10% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 33291 (n=1) [33291, 33291] | 75.00% | 71.10% |
| Observed source generated points (/frame) | 15809 (n=1) [15809, 15809] | 4302.9 (n=1) [4302.9, 4302.9] | 5059.7 (n=1) [5059.7, 5059.7] | 72.78% | 68.00% |
| Observed source cloud payload (bytes/frame) | 5.059e+05 (n=1) [5.059e+05, 5.059e+05] | 1.3769e+05 (n=1) [1.3769e+05, 1.3769e+05] | 1.6191e+05 (n=1) [1.6191e+05, 1.6191e+05] | 72.78% | 68.00% |
| Map total elapsed mean (ms/frame) | 25.329 (n=1) [25.329, 25.329] | 9.314 (n=1) [9.314, 9.314] | 10.407 (n=1) [10.407, 10.407] | 63.23% | 58.91% |
| Map total elapsed p95 (ms/frame) | 33.01 (n=1) [33.01, 33.01] | 14.106 (n=1) [14.106, 14.106] | 24.043 (n=1) [24.043, 24.043] | 57.27% | 27.17% |
| Map total elapsed max (ms/frame) | 90.495 (n=1) [90.495, 90.495] | 27.459 (n=1) [27.459, 27.459] | 38.641 (n=1) [38.641, 38.641] | 69.66% | 57.30% |
| Map raycast elapsed mean (ms/frame) | 15.537 (n=1) [15.537, 15.537] | 6.1486 (n=1) [6.1486, 6.1486] | 6.7231 (n=1) [6.7231, 6.7231] | 60.43% | 56.73% |
| Map update elapsed mean (ms/frame) | 9.7906 (n=1) [9.7906, 9.7906] | 3.164 (n=1) [3.164, 3.164] | 3.6827 (n=1) [3.6827, 3.6827] | 67.68% | 62.39% |
| Map inflation elapsed mean (ms/frame; nested) | 1.2755 (n=1) [1.2755, 1.2755] | 0.63596 (n=1) [0.63596, 0.63596] | 0.71136 (n=1) [0.71136, 0.71136] | 50.14% | 44.23% |
| Map processed frames / mission time (Hz proxy) | 10.376 (n=1) [10.376, 10.376] | 10.305 (n=1) [10.305, 10.305] | 10.238 (n=1) [10.238, 10.238] | 0.69% | 1.33% |
| Trajectory commits (Hz) | 3.2137 (n=1) [3.2137, 3.2137] | 3.2002 (n=1) [3.2002, 3.2002] | 3.3939 (n=1) [3.3939, 3.3939] | 0.42% | -5.61% |
| Goal retransmissions coalesced | 31 (n=1) [31, 31] | 32 (n=1) [32, 32] | 32 (n=1) [32, 32] | -3.23% | -3.23% |
| Demand replan checks (latest cumulative report) | 518 (n=1) [518, 518] | 587 (n=1) [587, 587] | 569 (n=1) [569, 569] | -13.32% | -9.85% |
| Demand replans skipped (latest cumulative report) | 372 (n=1) [372, 372] | 438 (n=1) [438, 438] | 413 (n=1) [413, 413] | -17.74% | -11.02% |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.020501 (n=1) [0.020501, 0.020501] | 0.020152 (n=1) [0.020152, 0.020152] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.13 (n=1) [0.13, 0.13] | 0.144 (n=1) [0.144, 0.144] | N/A | N/A |
| Map points mean (/frame) | 15809 (n=1) [15809, 15809] | 4302.9 (n=1) [4302.9, 4302.9] | 5059.7 (n=1) [5059.7, 5059.7] | 72.78% | 68.00% |
| Map points / mission time (points/s proxy) | 1.6404e+05 (n=1) [1.6404e+05, 1.6404e+05] | 44340 (n=1) [44340, 44340] | 51803 (n=1) [51803, 51803] | 72.97% | 68.42% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.0062 (n=1) [5.0062, 5.0062] | 1.3531 (n=1) [1.3531, 1.3531] | 1.5809 (n=1) [1.5809, 1.5809] | 72.97% | 68.42% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.8845 (n=1) [4.8845, 4.8845] | 1.3293 (n=1) [1.3293, 1.3293] | 1.5597 (n=1) [1.5597, 1.5597] | 72.79% | 68.07% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.0062 (n=1) [5.0062, 5.0062] | 1.3531 (n=1) [1.3531, 1.3531] | 1.5809 (n=1) [1.5809, 1.5809] | 72.97% | 68.42% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.003 (n=1) [10.003, 10.003] | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 0.02% | 0.02% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 99.998 (n=1) [99.998, 99.998] | 99.998 (n=1) [99.998, 99.998] | 0.00% | 0.00% |
| Received command frequency (Hz; holds included) | 94.794 (n=1) [94.794, 94.794] | 93.14 (n=1) [93.14, 93.14] | 94.526 (n=1) [94.526, 94.526] | 1.74% | 0.28% |
| Odometry receipt p99 gap (ms) | 10.83 (n=1) [10.83, 10.83] | 10.777 (n=1) [10.777, 10.777] | 11.132 (n=1) [11.132, 11.132] | 0.49% | -2.79% |
| Odometry receipt max gap (ms) | 15.553 (n=1) [15.553, 15.553] | 11.649 (n=1) [11.649, 11.649] | 12.35 (n=1) [12.35, 12.35] | 25.11% | 20.60% |
| Actual FSM main callback frequency (profiled only) | 99.966 (n=1) [99.966, 99.966] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | -0.03% | -0.03% |
| Actual FSM command callback frequency (profiled only) | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | 99.999 (n=1) [99.999, 99.999] | -0.00% | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 5.316 (n=1) [5.316, 5.316] | N/A | N/A |
| Guard active duration (s) | 0.8172 (n=1) [0.8172, 0.8172] | 1.2387 (n=1) [1.2387, 1.2387] | 2.2083 (n=1) [2.2083, 2.2083] | -51.58% | -170.22% |

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
