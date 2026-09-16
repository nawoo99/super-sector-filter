# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed1 — c23_normal_comparison_comparison5 — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 1 | 1 |
| Successes | 1 | 1 | 1 |
| Valid runs | 1 | 1 | 1 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 5 runs per mode; INCOMPLETE — planned rows still missing. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 39.27 (n=1) [39.27, 39.27] | 39.64 (n=1) [39.64, 39.64] | 38.76 (n=1) [38.76, 38.76] | -0.94% | 1.30% |
| Path length (m) | 228.7 (n=1) [228.7, 228.7] | 223 (n=1) [223, 223] | 222.95 (n=1) [222.95, 222.95] | 2.49% | 2.52% |
| Minimum static-PC clearance (m) | 0.308 (n=1) [0.308, 0.308] | 0.153 (n=1) [0.153, 0.153] | 0.308 (n=1) [0.308, 0.308] | 50.32% | 0.00% |
| Experiment CPU (cores) | 0.72194 (n=1) [0.72194, 0.72194] | 0.4211 (n=1) [0.4211, 0.4211] | 0.43288 (n=1) [0.43288, 0.43288] | 41.67% | 40.04% |
| Experiment CPU (whole-host %) | 3.6097 (n=1) [3.6097, 3.6097] | 2.1055 (n=1) [2.1055, 2.1055] | 2.1644 (n=1) [2.1644, 2.1644] | 41.67% | 40.04% |
| Experiment measurement-window CPU (core-s) | 29.89 (n=1) [29.89, 29.89] | 17.402 (n=1) [17.402, 17.402] | 17.433 (n=1) [17.433, 17.433] | 41.78% | 41.67% |
| Accounting window (s) | 41.402 (n=1) [41.402, 41.402] | 41.325 (n=1) [41.325, 41.325] | 40.272 (n=1) [40.272, 40.272] | 0.18% | 2.73% |
| Experiment CPU 1 s p95 (cores) | 0.90623 (n=1) [0.90623, 0.90623] | 0.51107 (n=1) [0.51107, 0.51107] | 0.55906 (n=1) [0.55906, 0.55906] | 43.60% | 38.31% |
| Experiment CPU 1 s maximum (cores) | 0.94864 (n=1) [0.94864, 0.94864] | 0.66213 (n=1) [0.66213, 0.66213] | 0.59589 (n=1) [0.59589, 0.59589] | 30.20% | 37.19% |
| Composed runtime CPU (cores; includes simulator) | 0.6788 (n=1) [0.6788, 0.6788] | 0.37803 (n=1) [0.37803, 0.37803] | 0.38947 (n=1) [0.38947, 0.38947] | 44.31% | 42.62% |
| Composed runtime measurement-window CPU (core-s) | 28.103 (n=1) [28.103, 28.103] | 15.622 (n=1) [15.622, 15.622] | 15.685 (n=1) [15.685, 15.685] | 44.41% | 44.19% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.2241 (n=1) [3.2241, 3.2241] | 3.0295 (n=1) [3.0295, 3.0295] | 3.0564 (n=1) [3.0564, 3.0564] | 6.04% | 5.20% |
| Whole-host CPU (%) | 15.51 (n=1) [15.51, 15.51] | 14.07 (n=1) [14.07, 14.07] | 13.68 (n=1) [13.68, 13.68] | 9.28% | 11.79% |
| Baseline whole-host CPU (%) | 10.946 (n=1) [10.946, 10.946] | 10.719 (n=1) [10.719, 10.719] | 10.786 (n=1) [10.786, 10.786] | 2.07% | 1.46% |
| Experiment sampled peak RSS (MiB) | 3387.7 (n=1) [3387.7, 3387.7] | 3379 (n=1) [3379, 3379] | 3383.6 (n=1) [3383.6, 3383.6] | 0.26% | 0.12% |
| Experiment sampled peak PSS (MiB) | 3347.6 (n=1) [3347.6, 3347.6] | 3339.1 (n=1) [3339.1, 3339.1] | 3343.6 (n=1) [3343.6, 3343.6] | 0.25% | 0.12% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5352.9 (n=1) [5352.9, 5352.9] | 5350.8 (n=1) [5350.8, 5350.8] | 5363.9 (n=1) [5363.9, 5363.9] | 0.04% | -0.20% |
| GPU device utilization (%) | 52.659 (n=1) [52.659, 52.659] | 51.707 (n=1) [51.707, 51.707] | 49.05 (n=1) [49.05, 49.05] | 1.81% | 6.85% |
| GPU device utilization p95 (%) | 56 (n=1) [56, 56] | 55 (n=1) [55, 55] | 52 (n=1) [52, 52] | 1.79% | 7.14% |
| GPU device memory-controller utilization (%) | 19.195 (n=1) [19.195, 19.195] | 19.268 (n=1) [19.268, 19.268] | 19.65 (n=1) [19.65, 19.65] | -0.38% | -2.37% |
| GPU device memory (MiB) | 1265.1 (n=1) [1265.1, 1265.1] | 1264.6 (n=1) [1264.6, 1264.6] | 1261.5 (n=1) [1261.5, 1261.5] | 0.04% | 0.29% |
| GPU device power (W; not flight attribution) | 18.821 (n=1) [18.821, 18.821] | 18.949 (n=1) [18.949, 18.949] | 18.985 (n=1) [18.985, 18.985] | -0.68% | -0.87% |
| Observed source frame records | 411 (n=1) [411, 411] | 410 (n=1) [410, 410] | 401 (n=1) [401, 401] | 0.24% | 2.43% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 246.88 (n=1) [246.88, 246.88] | 75.00% | 72.57% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.1973e+05 (n=1) [2.1973e+05, 2.1973e+05] | 75.00% | 72.57% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 31601 (n=1) [31601, 31601] | 75.00% | 72.57% |
| Observed source generated points (/frame) | 15975 (n=1) [15975, 15975] | 4124.9 (n=1) [4124.9, 4124.9] | 4863 (n=1) [4863, 4863] | 74.18% | 69.56% |
| Observed source cloud payload (bytes/frame) | 5.112e+05 (n=1) [5.112e+05, 5.112e+05] | 1.32e+05 (n=1) [1.32e+05, 1.32e+05] | 1.5562e+05 (n=1) [1.5562e+05, 1.5562e+05] | 74.18% | 69.56% |
| Map total elapsed mean (ms/frame) | 33.132 (n=1) [33.132, 33.132] | 9.8805 (n=1) [9.8805, 9.8805] | 10.022 (n=1) [10.022, 10.022] | 70.18% | 69.75% |
| Map total elapsed p95 (ms/frame) | 43.6 (n=1) [43.6, 43.6] | 15.639 (n=1) [15.639, 15.639] | 17.227 (n=1) [17.227, 17.227] | 64.13% | 60.49% |
| Map total elapsed max (ms/frame) | 65.301 (n=1) [65.301, 65.301] | 31.339 (n=1) [31.339, 31.339] | 41.5 (n=1) [41.5, 41.5] | 52.01% | 36.45% |
| Map raycast elapsed mean (ms/frame) | 21.211 (n=1) [21.211, 21.211] | 6.2209 (n=1) [6.2209, 6.2209] | 6.3394 (n=1) [6.3394, 6.3394] | 70.67% | 70.11% |
| Map update elapsed mean (ms/frame) | 11.919 (n=1) [11.919, 11.919] | 3.6579 (n=1) [3.6579, 3.6579] | 3.6815 (n=1) [3.6815, 3.6815] | 69.31% | 69.11% |
| Map inflation elapsed mean (ms/frame; nested) | 1.5694 (n=1) [1.5694, 1.5694] | 0.76465 (n=1) [0.76465, 0.76465] | 0.78202 (n=1) [0.78202, 0.78202] | 51.28% | 50.17% |
| Map processed frames / mission time (Hz proxy) | 10.441 (n=1) [10.441, 10.441] | 10.343 (n=1) [10.343, 10.343] | 10.32 (n=1) [10.32, 10.32] | 0.93% | 1.16% |
| Trajectory commits (Hz) | 5.5456 (n=1) [5.5456, 5.5456] | 5.5572 (n=1) [5.5572, 5.5572] | 5.3747 (n=1) [5.3747, 5.3747] | -0.21% | 3.08% |
| Goal retransmissions coalesced | 35 (n=1) [35, 35] | 29 (n=1) [29, 29] | 30 (n=1) [30, 30] | 17.14% | 14.29% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.013059 (n=1) [0.013059, 0.013059] | 0.013405 (n=1) [0.013405, 0.013405] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.098 (n=1) [0.098, 0.098] | 0.163 (n=1) [0.163, 0.163] | N/A | N/A |
| Map points mean (/frame) | 15991 (n=1) [15991, 15991] | 4124.9 (n=1) [4124.9, 4124.9] | 4827 (n=1) [4827, 4827] | 74.20% | 69.81% |
| Map points / mission time (points/s proxy) | 1.6695e+05 (n=1) [1.6695e+05, 1.6695e+05] | 42664 (n=1) [42664, 42664] | 49814 (n=1) [49814, 49814] | 74.45% | 70.16% |
| Map payload / mission time (MiB/s proxy, logical edge) | 5.095 (n=1) [5.095, 5.095] | 1.302 (n=1) [1.302, 1.302] | 1.5202 (n=1) [1.5202, 1.5202] | 74.45% | 70.16% |
| Sensor report payload (MiB/s, logical edge; own span) | 4.937 (n=1) [4.937, 4.937] | 1.2777 (n=1) [1.2777, 1.2777] | 1.4907 (n=1) [1.4907, 1.4907] | 74.12% | 69.81% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 5.095 (n=1) [5.095, 5.095] | 1.302 (n=1) [1.302, 1.302] | 1.5202 (n=1) [1.5202, 1.5202] | 74.45% | 70.16% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10 (n=1) [10, 10] | 10.001 (n=1) [10.001, 10.001] | 10 (n=1) [10, 10] | -0.00% | -0.00% |
| Received odometry frequency (Hz) | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 100 (n=1) [100, 100] | 0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 91.876 (n=1) [91.876, 91.876] | 91.936 (n=1) [91.936, 91.936] | 91.826 (n=1) [91.826, 91.826] | -0.06% | 0.05% |
| Odometry receipt p99 gap (ms) | 10.702 (n=1) [10.702, 10.702] | 10.715 (n=1) [10.715, 10.715] | 10.822 (n=1) [10.822, 10.822] | -0.12% | -1.11% |
| Odometry receipt max gap (ms) | 14.685 (n=1) [14.685, 14.685] | 19.404 (n=1) [19.404, 19.404] | 11.441 (n=1) [11.441, 11.441] | -32.13% | 22.09% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 2 (n=1) [2, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 3.038 (n=1) [3.038, 3.038] | N/A | N/A |
| Guard active duration (s) | 0.041321 (n=1) [0.041321, 0.041321] | 1.4759 (n=1) [1.4759, 1.4759] | 1.3518 (n=1) [1.3518, 1.3518] | -3471.76% | -3171.50% |

## seed3 — c23_normal_comparison_comparison5 — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 2 | 2 | 2 |
| Successes | 2 | 2 | 2 |
| Valid runs | 2 | 2 | 2 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 5 runs per mode; INCOMPLETE — planned rows still missing. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 36.695 ± 0.02121 [36.68, 36.71] | 38.2 ± 0.02828 [38.18, 38.22] | 38.86 ± 1.57 [37.75, 39.97] | -4.10% | -5.90% |
| Path length (m) | 222.55 ± 0.1556 [222.44, 222.66] | 223.79 ± 0.2835 [223.59, 223.99] | 224.33 ± 0.4731 [224, 224.67] | -0.56% | -0.80% |
| Minimum static-PC clearance (m) | 0.329 ± 0.01414 [0.319, 0.339] | 0.307 ± 0.01273 [0.298, 0.316] | 0.34 ± 0.01838 [0.327, 0.353] | 6.69% | -3.34% |
| Experiment CPU (cores) | 0.648 ± 0.02572 [0.62981, 0.66619] | 0.42243 ± 0.000308 [0.42221, 0.42265] | 0.41851 ± 0.001914 [0.41716, 0.41986] | 34.81% | 35.41% |
| Experiment CPU (whole-host %) | 3.24 ± 0.1286 [3.149, 3.3309] | 2.1121 ± 0.00154 [2.1111, 2.1132] | 2.0925 ± 0.009568 [2.0858, 2.0993] | 34.81% | 35.41% |
| Experiment measurement-window CPU (core-s) | 24.811 ± 0.9686 [24.126, 25.495] | 16.613 ± 0.008555 [16.607, 16.619] | 17.1 ± 0.8175 [16.522, 17.678] | 33.04% | 31.08% |
| Accounting window (s) | 38.289 ± 0.02514 [38.271, 38.306] | 39.326 ± 0.008421 [39.32, 39.332] | 40.864 ± 2.14 [39.351, 42.378] | -2.71% | -6.73% |
| Experiment CPU 1 s p95 (cores) | 0.86215 ± 0.07894 [0.80633, 0.91797] | 0.56289 ± 0.03984 [0.53472, 0.59106] | 0.55096 ± 0.04142 [0.52166, 0.58025] | 34.71% | 36.10% |
| Experiment CPU 1 s maximum (cores) | 0.90879 ± 0.06252 [0.86459, 0.953] | 0.58353 ± 0.01315 [0.57423, 0.59282] | 0.70744 ± 0.02869 [0.68715, 0.72773] | 35.79% | 22.16% |
| Composed runtime CPU (cores; includes simulator) | 0.6062 ± 0.0268 [0.58725, 0.62515] | 0.37702 ± 0.002147 [0.3755, 0.37854] | 0.37535 ± 0.001544 [0.37426, 0.37644] | 37.81% | 38.08% |
| Composed runtime measurement-window CPU (core-s) | 23.21 ± 1.011 [22.495, 23.925] | 14.827 ± 0.08124 [14.769, 14.884] | 15.34 ± 0.8664 [14.727, 15.953] | 36.12% | 33.91% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.3103 ± 0.09196 [3.2453, 3.3753] | 3.3518 ± 0.01797 [3.3391, 3.3645] | 3.4137 ± 0.1106 [3.3355, 3.4919] | -1.26% | -3.12% |
| Whole-host CPU (%) | 10.239 ± 0.5602 [9.8428, 10.635] | 9.5763 ± 0.0236 [9.5596, 9.593] | 9.5115 ± 0.3296 [9.2785, 9.7446] | 6.47% | 7.10% |
| Baseline whole-host CPU (%) | 7.1477 ± 0.04694 [7.1145, 7.1809] | 8.1868 ± 0.2699 [7.996, 8.3776] | 7.7479 ± 0.3446 [7.5042, 7.9916] | -14.54% | -8.40% |
| Experiment sampled peak RSS (MiB) | 3447.4 ± 19.74 [3433.5, 3461.4] | 3426 ± 2.027 [3424.6, 3427.5] | 3432.1 ± 3.712 [3429.4, 3434.7] | 0.62% | 0.45% |
| Experiment sampled peak PSS (MiB) | 3407.5 ± 19.82 [3393.5, 3421.5] | 3385.9 ± 2.09 [3384.4, 3387.4] | 3391.8 ± 4.056 [3388.9, 3394.6] | 0.63% | 0.46% |
| Experiment sampled peak process swap (MiB) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5494 ± 5.185 [5490.3, 5497.7] | 5542.9 ± 2.088 [5541.4, 5544.4] | 5563.5 ± 35.23 [5538.6, 5588.4] | -0.89% | -1.26% |
| GPU device utilization (%) | 50.868 ± 2.084 [49.395, 52.342] | 50.5 ± 0.6346 [50.051, 50.949] | 54.244 ± 1.07 [53.487, 55] | 0.72% | -6.64% |
| GPU device utilization p95 (%) | 56 ± 1.414 [55, 57] | 56 ± 0 [56, 56] | 57.5 ± 0.7071 [57, 58] | 0.00% | -2.68% |
| GPU device memory-controller utilization (%) | 19.026 ± 0.03722 [19, 19.053] | 19 ± 0.03626 [18.974, 19.026] | 19.012 ± 0.01684 [19, 19.024] | 0.14% | 0.08% |
| GPU device memory (MiB) | 1265.7 ± 0.2349 [1265.5, 1265.8] | 1265.4 ± 0.119 [1265.3, 1265.5] | 1265.7 ± 0.1418 [1265.6, 1265.8] | 0.02% | -0.00% |
| GPU device power (W; not flight attribution) | 18.711 ± 0.006196 [18.706, 18.715] | 18.771 ± 0.03759 [18.745, 18.798] | 18.75 ± 0.04007 [18.722, 18.778] | -0.32% | -0.21% |
| Observed source frame records | 381.5 ± 0.7071 [381, 382] | 392 ± 0 [392, 392] | 406 ± 21.21 [391, 421] | -2.75% | -6.42% |
| Observed source readback width (pixels/frame) | 900 ± 0 [900, 900] | 225 ± 0 [225, 225] | 242.7 ± 22.59 [226.73, 258.67] | 75.00% | 73.03% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 ± 0 [8.01e+05, 8.01e+05] | 2.0025e+05 ± 0 [2.0025e+05, 2.0025e+05] | 2.16e+05 ± 2.01e+04 [2.0179e+05, 2.3022e+05] | 75.00% | 73.03% |
| Observed source conversion rays (/frame) | 1.152e+05 ± 0 [1.152e+05, 1.152e+05] | 28800 ± 0 [28800, 28800] | 31065 ± 2891 [29021, 33110] | 75.00% | 73.03% |
| Observed source generated points (/frame) | 22714 ± 87.52 [22652, 22775] | 6427 ± 301.5 [6213.8, 6640.2] | 6664.4 ± 748.6 [6135.1, 7193.7] | 71.70% | 70.66% |
| Observed source cloud payload (bytes/frame) | 7.2683e+05 ± 2801 [7.2485e+05, 7.2881e+05] | 2.0566e+05 ± 9649 [1.9884e+05, 2.1249e+05] | 2.1326e+05 ± 2.395e+04 [1.9632e+05, 2.302e+05] | 71.70% | 70.66% |
| Map total elapsed mean (ms/frame) | 31.021 ± 1.661 [29.847, 32.196] | 11.123 ± 0.3377 [10.884, 11.361] | 11.345 ± 0.5541 [10.954, 11.737] | 64.15% | 63.43% |
| Map total elapsed p95 (ms/frame) | 39.95 ± 1.121 [39.158, 40.743] | 16.593 ± 0.02397 [16.576, 16.61] | 18.688 ± 3.574 [16.161, 21.215] | 58.47% | 53.22% |
| Map total elapsed max (ms/frame) | 81.417 ± 23.65 [64.692, 98.142] | 22.787 ± 3.336 [20.428, 25.146] | 45.236 ± 9.598 [38.449, 52.022] | 72.01% | 44.44% |
| Map raycast elapsed mean (ms/frame) | 19.216 ± 1.234 [18.344, 20.089] | 7.4661 ± 0.2301 [7.3034, 7.6287] | 7.4725 ± 0.407 [7.1847, 7.7604] | 61.15% | 61.11% |
| Map update elapsed mean (ms/frame) | 11.803 ± 0.4274 [11.501, 12.105] | 3.6549 ± 0.1077 [3.5788, 3.731] | 3.8714 ± 0.1469 [3.7675, 3.9753] | 69.03% | 67.20% |
| Map inflation elapsed mean (ms/frame; nested) | 1.8404 ± 0.04594 [1.8079, 1.8729] | 0.85406 ± 0.01793 [0.84139, 0.86674] | 0.85169 ± 0.01811 [0.83888, 0.8645] | 53.59% | 53.72% |
| Map processed frames / mission time (Hz proxy) | 10.369 ± 0.02526 [10.351, 10.387] | 10.262 ± 0.007598 [10.256, 10.267] | 10.445 ± 0.1239 [10.358, 10.533] | 1.04% | -0.73% |
| Trajectory commits (Hz) | 5.4474 ± 0.149 [5.3421, 5.5528] | 5.462 ± 0.1665 [5.3443, 5.5797] | 5.2932 ± 0.2432 [5.1212, 5.4652] | -0.27% | 2.83% |
| Goal retransmissions coalesced | 29 ± 5.657 [25, 33] | 32.5 ± 2.121 [31, 34] | 32.5 ± 2.121 [31, 34] | -12.07% | -12.07% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.017165 ± 9.207e-06 [0.017159, 0.017172] | 0.014677 ± 0.0008246 [0.014094, 0.01526] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.087 ± 0.001414 [0.086, 0.088] | 0.1315 ± 0.01344 [0.122, 0.141] | N/A | N/A |
| Map points mean (/frame) | 22727 ± 87.06 [22665, 22789] | 6427 ± 301.5 [6213.8, 6640.2] | 6664.4 ± 748.6 [6135.1, 7193.7] | 71.72% | 70.68% |
| Map points / mission time (points/s proxy) | 2.3566e+05 ± 1477 [2.3462e+05, 2.3671e+05] | 65951 ± 3045 [63798, 68105] | 69658 ± 8645 [63545, 75771] | 72.01% | 70.44% |
| Map payload / mission time (MiB/s proxy, logical edge) | 7.1919 ± 0.04507 [7.16, 7.2238] | 2.0127 ± 0.09294 [1.947, 2.0784] | 2.1258 ± 0.2638 [1.9392, 2.3123] | 72.01% | 70.44% |
| Sensor report payload (MiB/s, logical edge; own span) | 7.0249 ± 0.04833 [6.9907, 7.0591] | 1.9907 ± 0.06976 [1.9414, 2.04] | 2.0701 ± 0.2234 [1.9121, 2.2281] | 71.66% | 70.53% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 7.1919 ± 0.04507 [7.16, 7.2238] | 2.0127 ± 0.09294 [1.947, 2.0784] | 2.1258 ± 0.2638 [1.9392, 2.3123] | 72.01% | 70.44% |
| DDS cloud payload (MiB/s, logical messages) | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 ± 0.0005657 [10, 10.001] | 10.001 ± 0.0003465 [10.001, 10.001] | 10.001 ± 0.0004285 [10.001, 10.001] | -0.00% | -0.00% |
| Received odometry frequency (Hz) | 100 ± 0.004533 [99.999, 100.01] | 100.01 ± 0.007191 [100, 100.01] | 100.01 ± 0.0008168 [100.01, 100.01] | -0.00% | -0.00% |
| Received command frequency (Hz; holds included) | 93.583 ± 2.109 [92.092, 95.074] | 95.112 ± 1.288 [94.201, 96.022] | 95.305 ± 0.6598 [94.839, 95.772] | -1.63% | -1.84% |
| Odometry receipt p99 gap (ms) | 10.631 ± 0.01533 [10.62, 10.642] | 10.921 ± 0.1249 [10.832, 11.009] | 10.982 ± 0.282 [10.782, 11.181] | -2.72% | -3.30% |
| Odometry receipt max gap (ms) | 11.529 ± 0.09045 [11.465, 11.593] | 13.304 ± 2.884 [11.265, 15.344] | 12.524 ± 0.4381 [12.214, 12.833] | -15.40% | -8.63% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Certified recovery cycles opened | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Certified recovery cycles completed | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 1.5 ± 0.7071 [1, 2] | N/A | N/A |
| Recovery cycles outstanding | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | 0 ± 0 [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 ± 0 [0, 0] | 2.666 ± 3.403 [0.26, 5.072] | N/A | N/A |
| Guard active duration (s) | 0 ± 0 [0, 0] | 0.96437 ± 1.364 [0, 1.9287] | 1.1594 ± 1.501 [0.097772, 2.221] | N/A | N/A |

## seed5 — c23_normal_comparison_comparison5 — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 2 | 2 |
| Successes | 1 | 2 | 1 |
| Valid runs | 1 | 2 | 1 |
| Runs with contact | 0 | 1 | 0 |
| Unknown contact outcome | 0 | 0 | 1 |

Declared plan: 5 runs per mode; INCOMPLETE — planned rows still missing. Recording all rows is not a safety or performance acceptance decision.

WARNING: not all runs completed. Completion-time/CPU comparisons are outcome-confounded; failures remain in the tables.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 42.31 (n=1) [42.31, 42.31] | 43.5 ± 0.7637 [42.96, 44.04] | 41.96 (n=1) [41.96, 41.96] | -2.81% | 0.83% |
| Path length (m) | 226.96 (n=1) [226.96, 226.96] | 228.92 ± 0.9306 [228.26, 229.57] | 224.99 (n=1) [224.99, 224.99] | -0.86% | 0.87% |
| Minimum static-PC clearance (m) | 0.293 (n=1) [0.293, 0.293] | 0.06 ± 0.3323 [-0.175, 0.295] | 0.276 (n=1) [0.276, 0.276] | 79.52% | 5.80% |
| Experiment CPU (cores) | 0.70325 (n=1) [0.70325, 0.70325] | 0.42886 ± 0.007669 [0.42343, 0.43428] | 0.45044 (n=1) [0.45044, 0.45044] | 39.02% | 35.95% |
| Experiment CPU (whole-host %) | 3.5163 (n=1) [3.5163, 3.5163] | 2.1443 ± 0.03835 [2.1172, 2.1714] | 2.2522 (n=1) [2.2522, 2.2522] | 39.02% | 35.95% |
| Experiment measurement-window CPU (core-s) | 31.313 (n=1) [31.313, 31.313] | 19.326 ± 0.6644 [18.856, 19.796] | 19.593 (n=1) [19.593, 19.593] | 38.28% | 37.43% |
| Accounting window (s) | 44.527 (n=1) [44.527, 44.527] | 45.057 ± 0.7435 [44.531, 45.583] | 43.499 (n=1) [43.499, 43.499] | -1.19% | 2.31% |
| Experiment CPU 1 s p95 (cores) | 0.83304 (n=1) [0.83304, 0.83304] | 0.54051 ± 0.02098 [0.52567, 0.55534] | 0.54556 (n=1) [0.54556, 0.54556] | 35.12% | 34.51% |
| Experiment CPU 1 s maximum (cores) | 1.0927 (n=1) [1.0927, 1.0927] | 0.70892 ± 0.129 [0.61769, 0.80015] | 0.63289 (n=1) [0.63289, 0.63289] | 35.12% | 42.08% |
| Composed runtime CPU (cores; includes simulator) | 0.66511 (n=1) [0.66511, 0.66511] | 0.38862 ± 0.002452 [0.38689, 0.39035] | 0.40661 (n=1) [0.40661, 0.40661] | 41.57% | 38.86% |
| Composed runtime measurement-window CPU (core-s) | 29.615 (n=1) [29.615, 29.615] | 17.511 ± 0.3994 [17.229, 17.793] | 17.687 (n=1) [17.687, 17.687] | 40.87% | 40.28% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.3907 (n=1) [3.3907, 3.3907] | 3.4856 ± 0.07017 [3.436, 3.5352] | 3.4796 (n=1) [3.4796, 3.4796] | -2.80% | -2.62% |
| Whole-host CPU (%) | 10.561 (n=1) [10.561, 10.561] | 9.3521 ± 0.0793 [9.2961, 9.4082] | 9.6783 (n=1) [9.6783, 9.6783] | 11.45% | 8.36% |
| Baseline whole-host CPU (%) | 7.2933 (n=1) [7.2933, 7.2933] | 6.866 ± 0.4406 [6.5544, 7.1776] | 7.3168 (n=1) [7.3168, 7.3168] | 5.86% | -0.32% |
| Experiment sampled peak RSS (MiB) | 3479.3 (n=1) [3479.3, 3479.3] | 3473.7 ± 0.09391 [3473.7, 3473.8] | 3482.9 (n=1) [3482.9, 3482.9] | 0.16% | -0.10% |
| Experiment sampled peak PSS (MiB) | 3439.1 (n=1) [3439.1, 3439.1] | 3433.8 ± 0.04696 [3433.7, 3433.8] | 3442.7 (n=1) [3442.7, 3442.7] | 0.16% | -0.10% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5461.8 (n=1) [5461.8, 5461.8] | 5465.9 ± 21.37 [5450.8, 5481] | 3439.7 ± 2874 [1407.3, 5472.1] | -0.08% | 37.02% |
| GPU device utilization (%) | 51.205 (n=1) [51.205, 51.205] | 47.157 ± 1.475 [46.114, 48.2] | 52.955 (n=1) [52.955, 52.955] | 7.91% | -3.42% |
| GPU device utilization p95 (%) | 58 (n=1) [58, 58] | 52.5 ± 2.121 [51, 54] | 58 (n=1) [58, 58] | 9.48% | 0.00% |
| GPU device memory-controller utilization (%) | 19.023 (n=1) [19.023, 19.023] | 19.023 ± 0.03214 [19, 19.045] | 19.005 ± 0.05652 [18.966, 19.045] | 0.00% | 0.09% |
| GPU device memory (MiB) | 1270.5 (n=1) [1270.5, 1270.5] | 1270.6 ± 0.1007 [1270.5, 1270.7] | 1270.5 (n=1) [1270.5, 1270.5] | -0.01% | 0.00% |
| GPU device power (W; not flight attribution) | 18.735 (n=1) [18.735, 18.735] | 18.706 ± 0.003967 [18.704, 18.709] | 18.743 (n=1) [18.743, 18.743] | 0.16% | -0.04% |
| Observed source frame records | 442 (n=1) [442, 442] | 447.5 ± 6.364 [443, 452] | 432 (n=1) [432, 432] | -1.24% | 2.26% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 ± 0 [225, 225] | 273.44 (n=1) [273.44, 273.44] | 75.00% | 69.62% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 ± 0 [2.0025e+05, 2.0025e+05] | 2.4336e+05 (n=1) [2.4336e+05, 2.4336e+05] | 75.00% | 69.62% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 ± 0 [28800, 28800] | 35000 (n=1) [35000, 35000] | 75.00% | 69.62% |
| Observed source generated points (/frame) | 28927 (n=1) [28927, 28927] | 7928.4 ± 153.3 [7820, 8036.8] | 9617 (n=1) [9617, 9617] | 72.59% | 66.75% |
| Observed source cloud payload (bytes/frame) | 9.2565e+05 (n=1) [9.2565e+05, 9.2565e+05] | 2.5371e+05 ± 4905 [2.5024e+05, 2.5718e+05] | 3.0775e+05 (n=1) [3.0775e+05, 3.0775e+05] | 72.59% | 66.75% |
| Map total elapsed mean (ms/frame) | 34.261 (n=1) [34.261, 34.261] | 11.489 ± 0.3604 [11.234, 11.743] | 12.887 (n=1) [12.887, 12.887] | 66.47% | 62.38% |
| Map total elapsed p95 (ms/frame) | 43.834 (n=1) [43.834, 43.834] | 16.797 ± 0.657 [16.333, 17.262] | 25.349 (n=1) [25.349, 25.349] | 61.68% | 42.17% |
| Map total elapsed max (ms/frame) | 94.74 (n=1) [94.74, 94.74] | 38.779 ± 18.48 [25.712, 51.847] | 58.244 (n=1) [58.244, 58.244] | 59.07% | 38.52% |
| Map raycast elapsed mean (ms/frame) | 21.528 (n=1) [21.528, 21.528] | 7.6219 ± 0.2102 [7.4732, 7.7706] | 8.3938 (n=1) [8.3938, 8.3938] | 64.60% | 61.01% |
| Map update elapsed mean (ms/frame) | 12.731 (n=1) [12.731, 12.731] | 3.8653 ± 0.1502 [3.7591, 3.9715] | 4.4921 (n=1) [4.4921, 4.4921] | 69.64% | 64.71% |
| Map inflation elapsed mean (ms/frame; nested) | 2.0149 (n=1) [2.0149, 2.0149] | 0.91185 ± 0.02061 [0.89728, 0.92643] | 1.0102 (n=1) [1.0102, 1.0102] | 54.74% | 49.86% |
| Map processed frames / mission time (Hz proxy) | 10.447 (n=1) [10.447, 10.447] | 10.288 ± 0.03431 [10.263, 10.312] | 10.296 (n=1) [10.296, 10.296] | 1.52% | 1.45% |
| Trajectory commits (Hz) | 5.1103 (n=1) [5.1103, 5.1103] | 5.0305 ± 0.3285 [4.7982, 5.2628] | 5.0579 (n=1) [5.0579, 5.0579] | 1.56% | 1.02% |
| Goal retransmissions coalesced | 33 (n=1) [33, 33] | 29.5 ± 6.364 [25, 34] | 34 (n=1) [34, 34] | 10.61% | -3.03% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.015088 ± 0.0002642 [0.014901, 0.015274] | 0.01539 (n=1) [0.01539, 0.01539] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.059 ± 0.004243 [0.056, 0.062] | 0.139 (n=1) [0.139, 0.139] | N/A | N/A |
| Map points mean (/frame) | 28927 (n=1) [28927, 28927] | 7928.4 ± 153.3 [7820, 8036.8] | 9617 (n=1) [9617, 9617] | 72.59% | 66.75% |
| Map points / mission time (points/s proxy) | 3.0219e+05 (n=1) [3.0219e+05, 3.0219e+05] | 81568 ± 1849 [80260, 82875] | 99013 (n=1) [99013, 99013] | 73.01% | 67.23% |
| Map payload / mission time (MiB/s proxy, logical edge) | 9.2221 (n=1) [9.2221, 9.2221] | 2.4892 ± 0.05642 [2.4493, 2.5291] | 3.0216 (n=1) [3.0216, 3.0216] | 73.01% | 67.23% |
| Sensor report payload (MiB/s, logical edge; own span) | 9.0238 (n=1) [9.0238, 9.0238] | 2.4605 ± 0.08988 [2.3969, 2.524] | 3.0319 (n=1) [3.0319, 3.0319] | 72.73% | 66.40% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 9.2221 (n=1) [9.2221, 9.2221] | 2.4892 ± 0.05642 [2.4493, 2.5291] | 3.0216 (n=1) [3.0216, 3.0216] | 73.01% | 67.23% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | 10.001 ± 0.0001379 [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 0.00% | -0.00% |
| Received odometry frequency (Hz) | 100.01 (n=1) [100.01, 100.01] | 100 ± 0.000535 [100, 100.01] | 100.01 (n=1) [100.01, 100.01] | 0.01% | -0.00% |
| Received command frequency (Hz; holds included) | 93.077 (n=1) [93.077, 93.077] | 93.036 ± 2.465 [91.292, 94.779] | 91.001 (n=1) [91.001, 91.001] | 0.04% | 2.23% |
| Odometry receipt p99 gap (ms) | 10.699 (n=1) [10.699, 10.699] | 10.686 ± 0.06041 [10.643, 10.729] | 10.798 (n=1) [10.798, 10.798] | 0.12% | -0.93% |
| Odometry receipt max gap (ms) | 14.593 (n=1) [14.593, 14.593] | 13.676 ± 2.533 [11.886, 15.467] | 11.132 (n=1) [11.132, 11.132] | 6.28% | 23.72% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 6 (n=1) [6, 6] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 ± 0 [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 ± 0 [0, 0] | 7.329 (n=1) [7.329, 7.329] | N/A | N/A |
| Guard active duration (s) | 3.5909 (n=1) [3.5909, 3.5909] | 3.4878 ± 1.888 [2.153, 4.8226] | 3.2654 (n=1) [3.2654, 3.2654] | 2.87% | 9.06% |

## seed7 — c23_normal_comparison_comparison5 — unprofiled_primary

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | 1 | 1 |
| Successes | 1 | 1 | 1 |
| Valid runs | 1 | 1 | 1 |
| Runs with contact | 0 | 0 | 0 |
| Unknown contact outcome | 0 | 0 | 0 |

Declared plan: 5 runs per mode; INCOMPLETE — planned rows still missing. Recording all rows is not a safety or performance acceptance decision.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 42.2 (n=1) [42.2, 42.2] | 45.35 (n=1) [45.35, 45.35] | 47.77 (n=1) [47.77, 47.77] | -7.46% | -13.20% |
| Path length (m) | 228.85 (n=1) [228.85, 228.85] | 230.11 (n=1) [230.11, 230.11] | 232.69 (n=1) [232.69, 232.69] | -0.55% | -1.68% |
| Minimum static-PC clearance (m) | 0.275 (n=1) [0.275, 0.275] | 0.307 (n=1) [0.307, 0.307] | 0.158 (n=1) [0.158, 0.158] | -11.64% | 42.55% |
| Experiment CPU (cores) | 0.73392 (n=1) [0.73392, 0.73392] | 0.43229 (n=1) [0.43229, 0.43229] | 0.47137 (n=1) [0.47137, 0.47137] | 41.10% | 35.77% |
| Experiment CPU (whole-host %) | 3.6696 (n=1) [3.6696, 3.6696] | 2.1614 (n=1) [2.1614, 2.1614] | 2.3568 (n=1) [2.3568, 2.3568] | 41.10% | 35.77% |
| Experiment measurement-window CPU (core-s) | 32.695 (n=1) [32.695, 32.695] | 20.558 (n=1) [20.558, 20.558] | 23.383 (n=1) [23.383, 23.383] | 37.12% | 28.48% |
| Accounting window (s) | 44.549 (n=1) [44.549, 44.549] | 47.557 (n=1) [47.557, 47.557] | 49.606 (n=1) [49.606, 49.606] | -6.75% | -11.35% |
| Experiment CPU 1 s p95 (cores) | 0.93262 (n=1) [0.93262, 0.93262] | 0.5749 (n=1) [0.5749, 0.5749] | 0.66928 (n=1) [0.66928, 0.66928] | 38.36% | 28.24% |
| Experiment CPU 1 s maximum (cores) | 1.1135 (n=1) [1.1135, 1.1135] | 0.61858 (n=1) [0.61858, 0.61858] | 0.77449 (n=1) [0.77449, 0.77449] | 44.45% | 30.45% |
| Composed runtime CPU (cores; includes simulator) | 0.69034 (n=1) [0.69034, 0.69034] | 0.38913 (n=1) [0.38913, 0.38913] | 0.42582 (n=1) [0.42582, 0.42582] | 43.63% | 38.32% |
| Composed runtime measurement-window CPU (core-s) | 30.754 (n=1) [30.754, 30.754] | 18.506 (n=1) [18.506, 18.506] | 21.123 (n=1) [21.123, 21.123] | 39.83% | 31.32% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.4117 (n=1) [3.4117, 3.4117] | 3.3428 (n=1) [3.3428, 3.3428] | 3.3204 (n=1) [3.3204, 3.3204] | 2.02% | 2.68% |
| Whole-host CPU (%) | 10.397 (n=1) [10.397, 10.397] | 9.1064 (n=1) [9.1064, 9.1064] | 9.2571 (n=1) [9.2571, 9.2571] | 12.41% | 10.96% |
| Baseline whole-host CPU (%) | 7.5493 (n=1) [7.5493, 7.5493] | 7.7625 (n=1) [7.7625, 7.7625] | 6.909 (n=1) [6.909, 6.909] | -2.82% | 8.48% |
| Experiment sampled peak RSS (MiB) | 3490.8 (n=1) [3490.8, 3490.8] | 3463.1 (n=1) [3463.1, 3463.1] | 3483.8 (n=1) [3483.8, 3483.8] | 0.79% | 0.20% |
| Experiment sampled peak PSS (MiB) | 3450.9 (n=1) [3450.9, 3450.9] | 3423.3 (n=1) [3423.3, 3423.3] | 3443.9 (n=1) [3443.9, 3443.9] | 0.80% | 0.20% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5444.7 (n=1) [5444.7, 5444.7] | 5487.9 (n=1) [5487.9, 5487.9] | 5485.4 (n=1) [5485.4, 5485.4] | -0.79% | -0.75% |
| GPU device utilization (%) | 47.659 (n=1) [47.659, 47.659] | 48.064 (n=1) [48.064, 48.064] | 55.4 (n=1) [55.4, 55.4] | -0.85% | -16.24% |
| GPU device utilization p95 (%) | 54 (n=1) [54, 54] | 53 (n=1) [53, 53] | 58 (n=1) [58, 58] | 1.85% | -7.41% |
| GPU device memory-controller utilization (%) | 19.114 (n=1) [19.114, 19.114] | 19.064 (n=1) [19.064, 19.064] | 19.02 (n=1) [19.02, 19.02] | 0.26% | 0.49% |
| GPU device memory (MiB) | 1276 (n=1) [1276, 1276] | 1276.4 (n=1) [1276.4, 1276.4] | 1275.2 (n=1) [1275.2, 1275.2] | -0.03% | 0.06% |
| GPU device power (W; not flight attribution) | 18.716 (n=1) [18.716, 18.716] | 18.823 (n=1) [18.823, 18.823] | 18.823 (n=1) [18.823, 18.823] | -0.57% | -0.57% |
| Observed source frame records | 440 (n=1) [440, 440] | 471 (n=1) [471, 471] | 489 (n=1) [489, 489] | -7.05% | -11.14% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | 225 (n=1) [225, 225] | 296.78 (n=1) [296.78, 296.78] | 75.00% | 67.02% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | 2.0025e+05 (n=1) [2.0025e+05, 2.0025e+05] | 2.6413e+05 (n=1) [2.6413e+05, 2.6413e+05] | 75.00% | 67.02% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | 28800 (n=1) [28800, 28800] | 37988 (n=1) [37988, 37988] | 75.00% | 67.02% |
| Observed source generated points (/frame) | 36943 (n=1) [36943, 36943] | 9945 (n=1) [9945, 9945] | 14331 (n=1) [14331, 14331] | 73.08% | 61.21% |
| Observed source cloud payload (bytes/frame) | 1.1822e+06 (n=1) [1.1822e+06, 1.1822e+06] | 3.1824e+05 (n=1) [3.1824e+05, 3.1824e+05] | 4.586e+05 (n=1) [4.586e+05, 4.586e+05] | 73.08% | 61.21% |
| Map total elapsed mean (ms/frame) | 33.753 (n=1) [33.753, 33.753] | 10.643 (n=1) [10.643, 10.643] | 12.356 (n=1) [12.356, 12.356] | 68.47% | 63.39% |
| Map total elapsed p95 (ms/frame) | 42.964 (n=1) [42.964, 42.964] | 16.899 (n=1) [16.899, 16.899] | 21.404 (n=1) [21.404, 21.404] | 60.67% | 50.18% |
| Map total elapsed max (ms/frame) | 105.49 (n=1) [105.49, 105.49] | 23.26 (n=1) [23.26, 23.26] | 37.277 (n=1) [37.277, 37.277] | 77.95% | 64.66% |
| Map raycast elapsed mean (ms/frame) | 21.816 (n=1) [21.816, 21.816] | 7.1655 (n=1) [7.1655, 7.1655] | 8.3925 (n=1) [8.3925, 8.3925] | 67.16% | 61.53% |
| Map update elapsed mean (ms/frame) | 11.934 (n=1) [11.934, 11.934] | 3.4761 (n=1) [3.4761, 3.4761] | 3.962 (n=1) [3.962, 3.962] | 70.87% | 66.80% |
| Map inflation elapsed mean (ms/frame; nested) | 2.2318 (n=1) [2.2318, 2.2318] | 0.91406 (n=1) [0.91406, 0.91406] | 0.95434 (n=1) [0.95434, 0.95434] | 59.04% | 57.24% |
| Map processed frames / mission time (Hz proxy) | 10.403 (n=1) [10.403, 10.403] | 10.386 (n=1) [10.386, 10.386] | 10.237 (n=1) [10.237, 10.237] | 0.16% | 1.60% |
| Trajectory commits (Hz) | 5.3055 (n=1) [5.3055, 5.3055] | 5.2733 (n=1) [5.2733, 5.2733] | 5.1893 (n=1) [5.1893, 5.1893] | 0.61% | 2.19% |
| Goal retransmissions coalesced | 29 (n=1) [29, 29] | 32 (n=1) [32, 32] | 29 (n=1) [29, 29] | -10.34% | 0.00% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | 0.015104 (n=1) [0.015104, 0.015104] | 0.018573 (n=1) [0.018573, 0.018573] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | 0.072 (n=1) [0.072, 0.072] | 2.102 (n=1) [2.102, 2.102] | N/A | N/A |
| Map points mean (/frame) | 36985 (n=1) [36985, 36985] | 9945 (n=1) [9945, 9945] | 14331 (n=1) [14331, 14331] | 73.11% | 61.25% |
| Map points / mission time (points/s proxy) | 3.8475e+05 (n=1) [3.8475e+05, 3.8475e+05] | 1.0329e+05 (n=1) [1.0329e+05, 1.0329e+05] | 1.467e+05 (n=1) [1.467e+05, 1.467e+05] | 73.15% | 61.87% |
| Map payload / mission time (MiB/s proxy, logical edge) | 11.742 (n=1) [11.742, 11.742] | 3.1521 (n=1) [3.1521, 3.1521] | 4.477 (n=1) [4.477, 4.477] | 73.15% | 61.87% |
| Sensor report payload (MiB/s, logical edge; own span) | 11.33 (n=1) [11.33, 11.33] | 3.0563 (n=1) [3.0563, 3.0563] | 4.4955 (n=1) [4.4955, 4.4955] | 73.02% | 60.32% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 11.742 (n=1) [11.742, 11.742] | 3.1521 (n=1) [3.1521, 3.1521] | 4.477 (n=1) [4.477, 4.477] | 73.15% | 61.87% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.005 (n=1) [10.005, 10.005] | 10.001 (n=1) [10.001, 10.001] | 10.001 (n=1) [10.001, 10.001] | 0.04% | 0.04% |
| Received odometry frequency (Hz) | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 100.01 (n=1) [100.01, 100.01] | 0.00% | 0.01% |
| Received command frequency (Hz; holds included) | 92.683 (n=1) [92.683, 92.683] | 95.103 (n=1) [95.103, 95.103] | 93.852 (n=1) [93.852, 93.852] | -2.61% | -1.26% |
| Odometry receipt p99 gap (ms) | 10.615 (n=1) [10.615, 10.615] | 10.721 (n=1) [10.721, 10.721] | 10.85 (n=1) [10.85, 10.85] | -1.00% | -2.22% |
| Odometry receipt max gap (ms) | 11.121 (n=1) [11.121, 11.121] | 12.1 (n=1) [12.1, 12.1] | 11.598 (n=1) [11.598, 11.598] | -8.81% | -4.29% |
| Actual FSM main callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Actual FSM command callback frequency (profiled only) | N/A | N/A | N/A | N/A | N/A |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 3 (n=1) [3, 3] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | 0 (n=1) [0, 0] | 10.833 (n=1) [10.833, 10.833] | N/A | N/A |
| Guard active duration (s) | 1.3881 (n=1) [1.3881, 1.3881] | 5.386 (n=1) [5.386, 5.386] | 5.237 (n=1) [5.237, 5.237] | -288.02% | -277.29% |

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

## Data warnings

- 16112/adaptive: performance trace unavailable or window invalid
