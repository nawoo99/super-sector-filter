# Forest Full bounded soft-margin egress, fresh n=10

- Date: 2026-09-30
- Map: `forest_cluster_f01`
- Mission: `forest_wide_zigzag_v2.txt`
- Mode: Full
Runs: 95101--95110, one attempt per run, no replacement

## Result

| Metric | Result |
|---|---:|
| Completion | 9/10 (90%) |
| Runs with static-PCD contact | 0/10 (0%) |
| Safe completion | 9/10 (90%) |
| Successful-run time, mean +/- sample SD | 59.268 +/- 6.109 s |
| Successful-run time, median | 58.150 s |
| Successful-run time, range | 52.69--73.95 s |

Run 95109 is retained as an observed failure: it ended at the 180.01 s
observer horizon with waypoint 1/5, no contact, and static-PCD clearance
0.282 m. It is not replaced by a retry.

## Interpretation

Allowing a certified local/vertical recovery candidate to leave a bounded
soft-clearance prefix fixed the previously identified validator defect while
preserving hard occupied, unknown-space, map-boundary, map-version, deadline,
terminal-clearance, and stop-viability checks. However, this n=10 cohort did
not establish the required Full completion target.

The retained failure committed one 0.6 m local escape and made 2.053 m of
progress, but a later dense pocket rejected every 0.6 m horizontal direction;
a subsequent 0.6 m vertical recovery also did not restore a path. This is the
evidence for evaluating a bounded multi-distance local escape in a separate,
fresh cohort. The present cohort must remain reported as 9/10 and must not be
pooled with that follow-up as if it were one pre-specified sample.
