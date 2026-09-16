# C15 residual check before a dedicated frontend executor

Read-only telemetry analysis, 2026-09-16. No runtime/build/flight changes.

As in `READ_ONLY_REVIEW.md`, `/proc` CPU is integrated over sample intervals wholly enclosed in each process's profiler report window. Stage rates cover a slightly different interval; residual differences are approximate. Pool identities below remain inferred, not actual TID markers.

| Candidate/mode | Sample / profiler seconds | Composed process cores | Inferred pooled cores | Pool exclusive scope cores | Approximate pool residual |
|---|---|---:|---:|---:|---:|
| C12 Full | 29.185 / 30.040 | 0.550970 | 0.165497 | 0.120261 | 0.045235 |
| C12 Adaptive | 29.192 / 30.030 | 0.391201 | 0.202452 | 0.123839 | 0.078613 |
| C14 Full | 29.158 / 30.059 | 0.522670 | 0.148845 | 0.097139 | 0.051706 |
| C14 Adaptive | 34.213 / 35.069 | 0.376761 | 0.187358 | 0.108184 | 0.079174 |
| C15 Full | 29.150 / 30.002 | 0.538594 | 0.140309 | 0.093898 | 0.046411 |
| C15 Adaptive | 34.191 / 35.002 | 0.346877 | 0.162324 | 0.095835 | 0.066489 |

Approximate Adaptive-minus-Full pool residual: C12 **0.033377**, C14 **0.027468**, C15 **0.020078 cores**. C15 pool TIDs are Full `2986733,2986735`; Adaptive `2987636,2987638`. Actual role markers separately identify render/static threads, not these pooled workers. C15 Adaptive's extra cloud worker accumulated no positive measured `/proc` tick in the selected window; do not interpret that as exactly zero CPU.

C15's smaller residual is consistent with removing parameter entity overhead, but different n=1 flights, timing, map/planner work, and profiling windows prevent causal allocation of the entire reduction to that change. Whole-flight cgroup costs are not the same as these process/window numbers.

## Decision

A dedicated frontend STE is still a reasonable **small bounded experiment**, primarily to isolate executor overhead and its timing effect. There is no evidence for a large hidden cloud-processing workload. An optimistic removable budget is on the order of 0.02 cores; the added executor/thread costs some of that and can make the net result negative.

At C15's whole-flight Full 0.5798865 / Adaptive 0.3930003 cores, the measured reduction is 32.228%. Reaching 40% requires Adaptive <=0.3479319, another **0.0450684 cores**. Even subtracting the entire approximate 0.020078-core residual only yields about **35.69%**. Do not promise that this candidate alone reaches 40%, or add C12's old residual to the C15 saving.

Keep the feature default off. Compare total cgroup CPU rather than only the reduced shared-pool sum, require unchanged protocol/timing gates, and retain the zero-benefit/regression result if that is what is measured. An implementation and real-component test may be staged outside runtime for review; it must not be applied or built until root approval.
