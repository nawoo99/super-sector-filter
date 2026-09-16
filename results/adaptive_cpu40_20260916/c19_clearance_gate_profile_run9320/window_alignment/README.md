# CPU report-window alignment

No partial interval interpolation; input artifacts were not modified.

New cumulative evidence uses actual read brackets in both columns; nominal/conservative alternatives apply only to legacy telemetry.

| Mode | Window s | Profiled exclusive cores | Composed bounds (legacy nominal fallback) | Composed bounds (legacy conservative fallback) | Conservative stage-subtracted accounting residual |
|---|---:|---:|---:|---:|---:|
| full | 30.059290 | 0.430620 | 0.468408–0.501010 | 0.468408–0.501010 | 0.037788–0.070390 |
| adaptive | 30.059522 | 0.241374 | 0.303398–0.324024 | 0.303398–0.324024 | 0.062024–0.082650 |

Residual ranges are **accounting ranges, not exact physical uninstrumented-work bounds**; see limitations below.

## Dominant measured stages

| Mode | Stage | Exclusive CPU-s | Exclusive cores |
|---|---|---:|---:|
| full | map_prob_update | 6.975864 | 0.232070 |
| full | map_snapshot_commit_health | 1.374467 | 0.045725 |
| full | sim_render_callback | 1.265835 | 0.042111 |
| full | planner_exp_optimize | 1.078640 | 0.035884 |
| full | planner_backup_optimize | 0.628612 | 0.020912 |
| full | sim_odom_callback | 0.327168 | 0.010884 |
| full | planner_path_search | 0.299715 | 0.009971 |
| full | planner_generate_backup | 0.278675 | 0.009271 |
| adaptive | map_prob_update | 2.734770 | 0.090978 |
| adaptive | planner_exp_optimize | 1.042370 | 0.034677 |
| adaptive | sim_render_callback | 0.721908 | 0.024016 |
| adaptive | map_snapshot_commit_health | 0.598539 | 0.019912 |
| adaptive | planner_backup_optimize | 0.451953 | 0.015035 |
| adaptive | planner_path_search | 0.412571 | 0.013725 |
| adaptive | planner_generate_backup | 0.276247 | 0.009190 |
| adaptive | fsm_command_callback | 0.275265 | 0.009157 |

## Interpretation limits

- All means below divide by the same profiler report-window duration, not by the shorter enclosed-sample duration.
- New telemetry cumulative counters use actual before/after read brackets in BOTH variants; no midpoint is invented. For legacy C18 only, nominal bounds assume reads at sample-start while the conservative fallback allows reads before the next sampling pass.
- Deltas are never linearly interpolated or prorated. Enclosed intervals supply the lower amount; all possibly intersecting intervals supply the upper amount only if the counter-read chain covers the window.
- Bounds concern counter-reported CPU. /proc user/system counters remain tick-quantized. New telemetry checks PID create_time and actual read brackets; legacy C18 lacks those fields and therefore only PID/name/scope continuity can be checked. Cgroup path replacement without a counter reset remains unproven.
- Stage counters are completion-attributed and independently loaded, not exact clipped-window integrals. Unknown active-scope boundary CPU and report skew prevent calling the subtracted interval a strict physical uninstrumented-CPU bound.
- Exclusive stage CPU only is summed. Inclusive parent stages overlap children and must not be added; work performed by spawned worker threads is not implicitly attributed to their caller.
- Composed-process residual includes uninstrumented useful callbacks, executor/DDS work, profiling overhead and boundary attribution error. It is not all avoidable waste.
- Experiment cgroup includes launcher/mission/other experiment processes; process sum and cgroup are alternative measurements, never added. Observer CPU is outside this scope.
- Raw cumulative cgroup CSV remains useful for its own full span, but cannot be rigorously aligned without a persisted absolute monotonic origin.
- This is a profiled single-run offline diagnostic, not new flight evidence or an unprofiled40% acceptance result.
