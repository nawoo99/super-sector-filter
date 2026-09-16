# C14 paired-flight explicit-goal identity audit

Run 9315, seed1, one Full flight and one Adaptive flight. Runtime remained frozen
through both flights. This audit only read logs; it did not launch ROS, compile,
alter policy, or run CPU-heavy tests during the experiment.

Sources: `results/adaptive_cpu40_20260916/c14_goal_identity_profile/` final
`status.json`, `full_summary.json`, `adaptive_summary.json`, and archived
`artifacts/seed1_run9315_{full,adaptive}.attempt1.stack.log`.
Reproduce the lightweight protocol counts with `audit_c14_log.py LOG...` in this
directory. The actual diagnostic scans used the identical `/tmp/native_campaign`
log paths before the runner archived them.

## Observed protocol coverage

| Log observation | Full | Adaptive |
|---|---:|---:|
| Producer publications | 41 | 43 |
| Fresh positive command identities | 5 | 5 |
| Explicit retransmissions | 36 | 38 |
| Receiver coalesced retransmissions | 34 | 33 |
| Accepted-goal log entries | 6 | 9 |
| Distinct accepted mapped targets | 5 | 5 |
| Ordinary ReplanOnce commit log entries | 119 | 128 |
| ReplanOnce success log entries | 119 | 128 |
| All trajectory commit log entries | 120 | 130 |
| Coalesces with nearby exact gen/map SAFE log | 34/34 | 33/33 |

Both modes exercised the optimization positively. All 67 coalescing markers link
to a preceding producer publication with the exact same positive stamp and
`supported=1,new_intent=0,new_identity=0`. Each counter is contiguous starting at
1, and queued/accepted revisions remain positive and monotonic. No protocol error
was found. Fresh waypoint identities continue through normal admission, and all
five mapped targets appear in the accepted-goal logs in both modes.

Coalesced counts by waypoint 0..4 were Full `5,8,7,9,5` and Adaptive `5,9,8,6,5`.
Noncoalesced repeats remain possible by design whenever the strict healthy/token
proof is unavailable. The producer publication count is not an accepted-goal
count: the existing latest-wins startup queue can overwrite an unconsumed request.
Each log has one more producer publication than coalesced plus accepted entries;
this count alone must not be called a lost fresh mission intent.

## Certificate log ordering limitation

Every coalescing marker has an exact-generation, exact-map `status=SAFE`
certificate record within 30 merged-log lines. Only 12 Full and 6 Adaptive
certificate records appear *before* the corresponding marker in that merged
file; others appear shortly after. Certificate logging uses `fmt::print` whereas
coalescing uses the ROS logger, so merged stream line order is not a strict
cross-stream execution-order proof.

Example Full: coalesced #2 at generation13/map40 is line605, with its exact SAFE
record at line607. Coalesced #8 at generation33/map101 has an earlier exact SAFE
record. Neither missing-preceding-line cases nor nearby future lines are used to
claim a new runtime safety guarantee. Runtime source and focused tests establish
that the marker is reached only after its locked explicit SAFE/current-map/gen
check; the logs provide supporting coverage, not an independent race proof.

The last periodic demand reports are not final complete-flight counters:
Full checks530/skips393/renewals307; Adaptive checks586/skips435/renewals350.
They confirm both modes exercised demand skipping. Last periodic core-call
counts were Full137 and Adaptive150, also not complete-flight totals.

## Outcome, not a 40% success claim

| Final runner metric | Full | Adaptive |
|---|---:|---:|
| Completion | Yes | Yes |
| Recorded contacts/collisions | 0 | 0 |
| Mission time (s) | 37.54 | 39.65 |
| Mean experiment CPU (cores) | 0.579354 | 0.423070 |
| Cumulative experiment CPU (core-s) | 22.889422 | 17.650004 |

Runner result: mean reduction **26.9756%**, cumulative reduction **22.8901%**;
Adaptive/Full mission-time ratio **1.05621**. Safety/quality, paired and per-mode
time gates, positive common-demand coverage, positive common-goal coverage and
the current static-delivery preservation gate all passed. The 40% mean target
did **not** pass. This remains exploratory n=1, with profiling/diagnostic overhead
present and unprofiled confirmation still required before adoption claims.

The receiver-specific zero-Full-optimization problem is absent in this pair.
These results do not establish population-level reliability, bit-identical old
planner behavior, or safety in untested maps.
