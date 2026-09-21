# G5 observer-ready preflight (2026-09-21)

Gap-free map `gapfree_d1_m05`, profiled three-mode `n=1`, run `31005`.
This is diagnostic ON evidence, not an unprofiled population estimate.

| Mode | Complete | Analytic contact episodes | Min cylinder clearance (m) | Mission time (s) | Mean experiment CPU (cores) | CPU time (core-s) |
|---|---:|---:|---:|---:|---:|---:|
| Full | yes | 0 | 0.275603 | 50.81 | 0.666776 | 35.125251 |
| Fixed Sector | yes | 1 | -0.200000 | 48.81 | 0.415751 | 21.014069 |
| Adaptive | yes | 0 | 0.277300 | 48.97 | 0.433094 | 22.106507 |

All three observer READY records and odometry CSV files begin at position
`(0,0,1.5)` with zero velocity. All source, recovery, timing, resource, speed,
goal-identity and static-delivery checks passed without retry.

The Fixed Sector contact is one 22-sample episode against zero-based cylinder
index 320 (center `(-0.375437,2.080295)`, radius `0.5m`), observed from
6.3351s through 6.5550s. Full and Adaptive have no analytic cylinder contact.

Adaptive measured mean-CPU and cumulative-CPU reductions versus Full were
35.05% and 37.06%. Because this is profiled `n=1`, the runner correctly marks
the comparison as requiring unprofiled confirmation. It must not be presented
as a final CPU or population-safety result.

The earlier diagnostic folder `gapfree_g5_observer_ready_20260921_103943`
contains an Adaptive origin-to-finish/contact-zero observation but stopped
before the other modes because the first deferred-mission version separated
producer logs from the stack identity audit. It is retained and not pooled.
