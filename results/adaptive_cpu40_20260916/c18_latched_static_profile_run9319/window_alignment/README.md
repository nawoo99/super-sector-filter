# C18 CPU report-window alignment

No partial interval interpolation; input artifacts were not modified.

| Mode | Window s | Profiled exclusive cores | Composed nominal counter bounds | Composed conservative read-bracket bounds | Conservative stage-subtracted accounting residual |
|---|---:|---:|---:|---:|---:|
| full | 30.000167 | 0.441002 | 0.477664–0.514997 | 0.458331–0.534664 | 0.017329–0.093662 |
| adaptive | 30.020140 | 0.241248 | 0.307127–0.330445 | 0.298133–0.344769 | 0.056886–0.103521 |

Residual ranges are **accounting ranges, not exact physical uninstrumented-work bounds**; see limitations below.

## Dominant measured stages

| Mode | Stage | Exclusive CPU-s | Exclusive cores |
|---|---|---:|---:|
| full | map_prob_update | 7.061543 | 0.235383 |
| full | sim_render_callback | 1.542053 | 0.051401 |
| full | map_snapshot_commit_health | 1.389204 | 0.046307 |
| full | planner_exp_optimize | 1.045122 | 0.034837 |
| full | planner_backup_optimize | 0.627763 | 0.020925 |
| full | sim_odom_callback | 0.370504 | 0.012350 |
| full | planner_path_search | 0.281312 | 0.009377 |
| full | planner_generate_backup | 0.267222 | 0.008907 |
| adaptive | map_prob_update | 2.978637 | 0.099221 |
| adaptive | planner_exp_optimize | 0.976489 | 0.032528 |
| adaptive | map_snapshot_commit_health | 0.611633 | 0.020374 |
| adaptive | planner_backup_optimize | 0.546436 | 0.018202 |
| adaptive | sim_render_callback | 0.541537 | 0.018039 |
| adaptive | sim_odom_callback | 0.359284 | 0.011968 |
| adaptive | planner_path_search | 0.282804 | 0.009420 |
| adaptive | planner_generate_backup | 0.258351 | 0.008606 |

## Interpretation limits

- All means below divide by the same profiler report-window duration, not by the shorter enclosed-sample duration.
- Nominal bounds assume a counter read at the recorded sample-start timestamp. The conservative variant allows each read anywhere before the next sampling pass.
- Deltas are never linearly interpolated or prorated. Enclosed intervals supply the lower amount; all possibly intersecting intervals supply the upper amount only if the counter-read chain covers the window.
- Bounds concern counter-reported CPU. /proc user/system counters are tick-quantized; collection does not persist per-read timestamps or PID create_time. PID/name/scope continuity is checked, but a formal PID-ABA proof is unavailable.
- Stage counters are completion-attributed and independently loaded, not exact clipped-window integrals. Unknown active-scope boundary CPU and report skew prevent calling the subtracted interval a strict physical uninstrumented-CPU bound.
- Exclusive stage CPU only is summed. Inclusive parent stages overlap children and must not be added; work performed by spawned worker threads is not implicitly attributed to their caller.
- Composed-process residual includes uninstrumented useful callbacks, executor/DDS work, profiling overhead and boundary attribution error. It is not all avoidable waste.
- Experiment cgroup includes launcher/mission/other experiment processes; process sum and cgroup are alternative measurements, never added. Observer CPU is outside this scope.
- Raw cumulative cgroup CSV remains useful for its own full span, but cannot be rigorously aligned without a persisted absolute monotonic origin.
- This is a profiled single-run offline diagnostic, not new flight evidence or an unprofiled40% acceptance result.
