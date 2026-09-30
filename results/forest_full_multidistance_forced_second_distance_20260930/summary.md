# Forced second-distance branch proof

- Date: 2026-09-30
- Run: 95501
- Map: `gapfree_d1_m01`
- Mode: Full

`SUPER_TEST_FORCE_LOCAL_ESCAPE_SECOND_DISTANCE_ONCE=1` is a default-off,
one-shot regression hook. It armed one local recovery and skipped the complete
0.6 m tier (16 trials) so the next distance had to pass through the real
trajectory guard and stop-viability commit path.

Observed sequence:

1. `TEST_FAULT_LOCAL_ESCAPE_ARM action=skip_first_distance_then_certify`
2. `distance_step=1/2 skipped_trials=16 distance=0.600m`
3. `TRAJ_GUARD_LOCAL_ESCAPE action=commit distance_step=2/2 direction=1/16 distance=1.200m`

The flight then completed in 48.72 s with zero contacts, 0.288 m minimum
static-PCD body clearance, valid 7 m/s speed enforcement, valid resources,
valid performance logs, and all small-pool timing checks passing. The hook is
not enabled by any experiment profile and does not change ordinary planning.
