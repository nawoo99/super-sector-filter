# Forest Full bounded multi-distance recovery, fresh cohort

- Date: 2026-09-30
- Map: `forest_cluster_f01`
- Mission: `forest_wide_zigzag_v2.txt`
- Mode: Full
- Primary runs: 95401--95410, one flight attempt per run, no behavioral replacement
- Supplemental run: 95411

## Outcome

| Scope | Completion | Static-PCD contact | Strict timing-valid | Time mean +/- sample SD |
|---|---:|---:|---:|---:|
| Primary runs 95401--95410 | 10/10 | 0/10 | 9/10 | 59.421 +/- 4.560 s |
| Supplemental run 95411 | 1/1 | 0/1 | 1/1 | 61.77 s |
| All retained flights | 11/11 | 0/11 | 10/11 | 59.635 +/- 4.384 s |

Primary mission-time range was 53.04--65.89 s and its minimum exact static-PCD
body clearance was 0.165 m. The observed 180 s Forest Full hold did not recur.
Primary end-to-end compute averaged 0.827954 cores and 50.903403 core-s/run;
planner ingress was 10.303542 MiB/s and 613.403381 MiB/run, and map computation
was 36.322434 ms/frame. These compute values characterize this Full-only
diagnostic cohort and are not a new three-mode comparison.

Run 95408 remains in the record. It completed in 60.02 s without contact, but
one odometry receipt interval was 58.572 ms, exceeding the existing 50 ms
engineering guard. Its p99 interval was 10.567 ms and the other nine primary
runs had maxima at or below 13.343 ms. The row is therefore a valid observed
mission outcome but not strict timing-quality-valid. Run 95411 is a declared
supplemental observation, not a silent replacement for run 95408.

Every flight loaded `local_escape_max_distance_m=1.2` and
`local_escape_distance_steps=2` exactly once. Post-hoc evaluation with the
final runtime audit also passed the async-generation and 0.1 m near-hit
contracts in all 11 logs. Run 95405 exercised natural recovery: eight 0.6 m
directions were rejected, direction 9/16 was certified and committed, and the
mission completed in 65.89 s with no contact. No ordinary run committed the
second 1.2 m distance, so its branch proof is kept separately.

## Interpretation

The earlier single-distance cohort (`forest_full_soft_egress_n10_20260930`)
was 9/10 complete with no contacts; retained run 95109 exhausted all sixteen
0.6 m directions in later recovery episodes and stopped at the 180.01 s
horizon. The follow-up adds a bounded second distance rather than weakening
occupied-space, unknown-space, map-boundary, map-version, validation-deadline,
terminal-free-tail, or stop-viability checks. Default behavior remains the old
single 0.6 m step unless a profile explicitly opts into a larger maximum.

The fresh 10/10 result is evidence that the revised Full configuration met the
finite tested objective. It is not a paired replay, a proof that every future
dense pocket is escapable, or a population/real-world 100% guarantee. Because
the current Full, Sector and Adaptive near-hit profiles all opt into the same
bounded distance schedule, publication tables spanning all modes/maps require
a fresh common campaign before replacing frozen results.
