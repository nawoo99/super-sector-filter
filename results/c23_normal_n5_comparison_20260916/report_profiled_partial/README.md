# Full / Sector / Adaptive 연산량 비교 (Computational comparison)

Values: run mean ± sample SD [minimum, maximum]. N/A is not zero.

## seed9 — c23_normal_comparison_preflight — profiled_supplement

| Outcome | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Recorded attempts | 1 | N/A | 1 |
| Successes | 1 | N/A | 1 |
| Valid runs | 1 | N/A | 1 |
| Runs with contact | 0 | N/A | 0 |
| Unknown contact outcome | 0 | N/A | 0 |

Planned run count unavailable in supplied root manifest; observed counts above do not establish campaign completion.

WARNING: not all runs completed. Completion-time/CPU comparisons are outcome-confounded; failures remain in the tables.

| Metric | Full | Sector | Adaptive | Sector reduction vs Full | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 66.71 (n=1) [66.71, 66.71] | N/A | 51.29 (n=1) [51.29, 51.29] | N/A | 23.11% |
| Path length (m) | 243.25 (n=1) [243.25, 243.25] | N/A | 236.73 (n=1) [236.73, 236.73] | N/A | 2.68% |
| Minimum static-PC clearance (m) | 0.272 (n=1) [0.272, 0.272] | N/A | 0.313 (n=1) [0.313, 0.313] | N/A | -15.07% |
| Experiment CPU (cores) | 0.85096 (n=1) [0.85096, 0.85096] | N/A | 0.57663 (n=1) [0.57663, 0.57663] | N/A | 32.24% |
| Experiment CPU (whole-host %) | 4.2548 (n=1) [4.2548, 4.2548] | N/A | 2.8831 (n=1) [2.8831, 2.8831] | N/A | 32.24% |
| Experiment measurement-window CPU (core-s) | 59.079 (n=1) [59.079, 59.079] | N/A | 31.015 (n=1) [31.015, 31.015] | N/A | 47.50% |
| Accounting window (s) | 69.426 (n=1) [69.426, 69.426] | N/A | 53.787 (n=1) [53.787, 53.787] | N/A | 22.53% |
| Experiment CPU 1 s p95 (cores) | 1.5312 (n=1) [1.5312, 1.5312] | N/A | 0.93072 (n=1) [0.93072, 0.93072] | N/A | 39.22% |
| Experiment CPU 1 s maximum (cores) | 1.6636 (n=1) [1.6636, 1.6636] | N/A | 1.0828 (n=1) [1.0828, 1.0828] | N/A | 34.91% |
| Composed runtime CPU (cores; includes simulator) | 0.80828 (n=1) [0.80828, 0.80828] | N/A | 0.53483 (n=1) [0.53483, 0.53483] | N/A | 33.83% |
| Composed runtime measurement-window CPU (core-s) | 56.116 (n=1) [56.116, 56.116] | N/A | 28.767 (n=1) [28.767, 28.767] | N/A | 48.74% |
| Autonomy-only CPU (cores) | N/A | N/A | N/A | N/A | N/A |
| Observer CPU (one-core %) | 3.5046 (n=1) [3.5046, 3.5046] | N/A | 3.2806 (n=1) [3.2806, 3.2806] | N/A | 6.39% |
| Whole-host CPU (%) | 17.273 (n=1) [17.273, 17.273] | N/A | 14.918 (n=1) [14.918, 14.918] | N/A | 13.64% |
| Baseline whole-host CPU (%) | 11.123 (n=1) [11.123, 11.123] | N/A | 10.712 (n=1) [10.712, 10.712] | N/A | 3.70% |
| Experiment sampled peak RSS (MiB) | 3581.1 (n=1) [3581.1, 3581.1] | N/A | 3520.9 (n=1) [3520.9, 3520.9] | N/A | 1.68% |
| Experiment sampled peak PSS (MiB) | 3541 (n=1) [3541, 3541] | N/A | 3480.9 (n=1) [3480.9, 3480.9] | N/A | 1.70% |
| Experiment sampled peak process swap (MiB) | 0 (n=1) [0, 0] | N/A | 0 (n=1) [0, 0] | N/A | N/A |
| Host minimum available memory (MiB) | 5170.7 (n=1) [5170.7, 5170.7] | N/A | 5138.3 (n=1) [5138.3, 5138.3] | N/A | 0.63% |
| GPU device utilization (%) | 51.882 (n=1) [51.882, 51.882] | N/A | 49.245 (n=1) [49.245, 49.245] | N/A | 5.08% |
| GPU device utilization p95 (%) | 55 (n=1) [55, 55] | N/A | 53 (n=1) [53, 53] | N/A | 3.64% |
| GPU device memory-controller utilization (%) | 19.338 (n=1) [19.338, 19.338] | N/A | 19.321 (n=1) [19.321, 19.321] | N/A | 0.09% |
| GPU device memory (MiB) | 1290 (n=1) [1290, 1290] | N/A | 1291.1 (n=1) [1291.1, 1291.1] | N/A | -0.08% |
| GPU device power (W; not flight attribution) | 18.898 (n=1) [18.898, 18.898] | N/A | 18.826 (n=1) [18.826, 18.826] | N/A | 0.38% |
| Observed source frame records | 684 (n=1) [684, 684] | N/A | 527 (n=1) [527, 527] | N/A | 22.95% |
| Observed source readback width (pixels/frame) | 900 (n=1) [900, 900] | N/A | 291.6 (n=1) [291.6, 291.6] | N/A | 67.60% |
| Observed source depth-readback pixels (/frame) | 8.01e+05 (n=1) [8.01e+05, 8.01e+05] | N/A | 2.5953e+05 (n=1) [2.5953e+05, 2.5953e+05] | N/A | 67.60% |
| Observed source conversion rays (/frame) | 1.152e+05 (n=1) [1.152e+05, 1.152e+05] | N/A | 37325 (n=1) [37325, 37325] | N/A | 67.60% |
| Observed source generated points (/frame) | 44706 (n=1) [44706, 44706] | N/A | 14042 (n=1) [14042, 14042] | N/A | 68.59% |
| Observed source cloud payload (bytes/frame) | 1.4306e+06 (n=1) [1.4306e+06, 1.4306e+06] | N/A | 4.4936e+05 (n=1) [4.4936e+05, 4.4936e+05] | N/A | 68.59% |
| Map total elapsed mean (ms/frame) | 38.74 (n=1) [38.74, 38.74] | N/A | 14.445 (n=1) [14.445, 14.445] | N/A | 62.71% |
| Map total elapsed p95 (ms/frame) | 58.579 (n=1) [58.579, 58.579] | N/A | 33.476 (n=1) [33.476, 33.476] | N/A | 42.85% |
| Map total elapsed max (ms/frame) | 120.58 (n=1) [120.58, 120.58] | N/A | 58.296 (n=1) [58.296, 58.296] | N/A | 51.65% |
| Map raycast elapsed mean (ms/frame) | 27.277 (n=1) [27.277, 27.277] | N/A | 9.5597 (n=1) [9.5597, 9.5597] | N/A | 64.95% |
| Map update elapsed mean (ms/frame) | 11.46 (n=1) [11.46, 11.46] | N/A | 4.8841 (n=1) [4.8841, 4.8841] | N/A | 57.38% |
| Map inflation elapsed mean (ms/frame; nested) | 2.1496 (n=1) [2.1496, 2.1496] | N/A | 1.328 (n=1) [1.328, 1.328] | N/A | 38.22% |
| Map processed frames / mission time (Hz proxy) | 10.253 (n=1) [10.253, 10.253] | N/A | 10.255 (n=1) [10.255, 10.255] | N/A | -0.02% |
| Trajectory commits (Hz) | 3.5776 (n=1) [3.5776, 3.5776] | N/A | 4.8501 (n=1) [4.8501, 4.8501] | N/A | -35.57% |
| Goal retransmissions coalesced | 39 (n=1) [39, 39] | N/A | 38 (n=1) [38, 38] | N/A | 2.56% |
| Demand replan checks (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Demand replans skipped (latest cumulative report) | N/A | N/A | N/A | N/A | N/A |
| Unprofiled planner callback latency (ms) | N/A | N/A | N/A | N/A | N/A |
| Frontend cloud elapsed mean (ms/frame) | N/A | N/A | 0.017275 (n=1) [0.017275, 0.017275] | N/A | N/A |
| Frontend cloud elapsed max (ms/frame) | N/A | N/A | 0.167 (n=1) [0.167, 0.167] | N/A | N/A |
| Map points mean (/frame) | 44706 (n=1) [44706, 44706] | N/A | 14010 (n=1) [14010, 14010] | N/A | 68.66% |
| Map points / mission time (points/s proxy) | 4.5838e+05 (n=1) [4.5838e+05, 4.5838e+05] | N/A | 1.4368e+05 (n=1) [1.4368e+05, 1.4368e+05] | N/A | 68.66% |
| Map payload / mission time (MiB/s proxy, logical edge) | 13.989 (n=1) [13.989, 13.989] | N/A | 4.3847 (n=1) [4.3847, 4.3847] | N/A | 68.66% |
| Sensor report payload (MiB/s, logical edge; own span) | 13.756 (n=1) [13.756, 13.756] | N/A | 4.4106 (n=1) [4.4106, 4.4106] | N/A | 67.94% |
| Planner ingress / mission time (MiB/s proxy, logical edge) | 13.989 (n=1) [13.989, 13.989] | N/A | 4.3847 (n=1) [4.3847, 4.3847] | N/A | 68.66% |
| DDS cloud payload (MiB/s, logical messages) | 0 (n=1) [0, 0] | N/A | 0 (n=1) [0, 0] | N/A | N/A |
| Physical wire bandwidth (MiB/s) | N/A | N/A | N/A | N/A | N/A |
| LiDAR source frequency (Hz) | 10.001 (n=1) [10.001, 10.001] | N/A | 10 (n=1) [10, 10] | N/A | 0.01% |
| Received odometry frequency (Hz) | 99.88 (n=1) [99.88, 99.88] | N/A | 100 (n=1) [100, 100] | N/A | -0.12% |
| Received command frequency (Hz; holds included) | 94.837 (n=1) [94.837, 94.837] | N/A | 92.205 (n=1) [92.205, 92.205] | N/A | 2.78% |
| Odometry receipt p99 gap (ms) | 11.359 (n=1) [11.359, 11.359] | N/A | 10.796 (n=1) [10.796, 10.796] | N/A | 4.96% |
| Odometry receipt max gap (ms) | 17.971 (n=1) [17.971, 17.971] | N/A | 18.012 (n=1) [18.012, 18.012] | N/A | -0.23% |
| Actual FSM main callback frequency (profiled only) | 97.586 (n=1) [97.586, 97.586] | N/A | 99.645 (n=1) [99.645, 99.645] | N/A | -2.11% |
| Actual FSM command callback frequency (profiled only) | 100 (n=1) [100, 100] | N/A | 100 (n=1) [100, 100] | N/A | -0.00% |
| Observed source Sector-to-Full activations | 0 (n=1) [0, 0] | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Observed source Full-to-Sector returns | 0 (n=1) [0, 0] | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery cycles (frontend state) | N/A | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Event recovery completed (frontend state) | N/A | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles opened | 0 (n=1) [0, 0] | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Certified recovery cycles completed | 0 (n=1) [0, 0] | N/A | 6 (n=1) [6, 6] | N/A | N/A |
| Recovery cycles outstanding | 0 (n=1) [0, 0] | N/A | 0 (n=1) [0, 0] | N/A | N/A |
| Trajectory guard Full-open duty (%) | N/A | N/A | 9.677 (n=1) [9.677, 9.677] | N/A | N/A |
| Guard active duration (s) | 20.653 (n=1) [20.653, 20.653] | N/A | 5.2306 (n=1) [5.2306, 5.2306] | N/A | 74.67% |

## Instrumented stage CPU supplement (not primary CPU evidence)

Separate profiled windows, not complete mission windows. Only exclusive core means are shown below; inclusive CPU per call and all counts/windows are in `profiled_stages.csv`. No stage total is added to cgroup CPU.

Source: `/root/super-sector-filter/results/c23_normal_n5_comparison_20260916/profiled_preflight/seed9/thread_cpu_summary.json`

| Stage / process index | Full exclusive cores | Sector exclusive cores | Adaptive exclusive cores |
|---|---:|---:|---:|
| frontend_acquisition / 0 | N/A | N/A | 2.86094e-05 |
| frontend_cloud / 0 | N/A | N/A | 0.0001049 |
| frontend_enqueue / 0 | N/A | N/A | 4.32718e-05 |
| frontend_guard_status / 0 | N/A | N/A | 1.56309e-05 |
| frontend_map_ack / 0 | N/A | N/A | 2.22044e-05 |
| frontend_odom / 0 | N/A | N/A | 0.000611153 |
| frontend_replan_status / 0 | N/A | N/A | 1.58866e-05 |
| frontend_report / 0 | N/A | N/A | 1.2992e-05 |
| frontend_stats / 0 | N/A | N/A | 0.000933024 |
| fsm_command_callback / 0 | 0.00936563 | N/A | 0.0070475 |
| fsm_main_callback / 0 | 0.000505569 | N/A | 0.000580152 |
| fsm_main_core / 0 | 0.000341602 | N/A | 0.000365878 |
| fsm_poly_publish / 0 | 3.28806e-05 | N/A | 4.99447e-05 |
| fsm_replan_callback / 0 | 0.000210375 | N/A | 0.000285334 |
| fsm_replan_core / 0 | 0.000251044 | N/A | 0.000390443 |
| guard_brake / 0 | 3.7475e-05 | N/A | 3.06163e-05 |
| guard_certificate / 0 | 0.0008663 | N/A | 0.0010538 |
| guard_recover / 0 | 0.000181786 | N/A | 2.45413e-05 |
| map_ack_and_log / 0 | 0.000804371 | N/A | 0.00145714 |
| map_cloud_enqueue / 0 | 6.52143e-05 | N/A | 6.45159e-05 |
| map_odom_callback / 0 | 0.00089089 | N/A | 0.00108321 |
| map_prob_update / 0 | 0.366822 | N/A | 0.138746 |
| map_ros_to_pcl / 0 | 0.0085836 | N/A | 0.00240956 |
| map_snapshot_commit_health / 0 | 0.0450572 | N/A | 0.0279528 |
| map_worker / 0 | 9.08002e-05 | N/A | 7.42671e-05 |
| planner_backup_optimize / 0 | 0.0569699 | N/A | 0.0579572 |
| planner_commit / 0 | 0.000384099 | N/A | 0.000517474 |
| planner_corridor_search / 0 | 0.0145395 | N/A | 0.0164269 |
| planner_exp_optimize / 0 | 0.0794177 | N/A | 0.0996081 |
| planner_generate_backup / 0 | 0.0239465 | N/A | 0.026394 |
| planner_generate_exp / 0 | 0.000411618 | N/A | 0.000503134 |
| planner_path_search / 0 | 0.0483171 | N/A | 0.0483421 |
| planner_stop_viability / 0 | 0.000250328 | N/A | 0.000342575 |
| planner_validate_geometry / 0 | 0.00361741 | N/A | 0.00503646 |
| planner_velocity_extrema / 0 | 0.000103803 | N/A | 0.000134343 |
| planner_visualize_path / 0 | 0.000472371 | N/A | 0.000403337 |
| sim_odom_callback / 0 | 0.0111437 | N/A | 0.0132077 |
| sim_render_callback / 0 | 0.0479981 | N/A | 0.02045 |

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
