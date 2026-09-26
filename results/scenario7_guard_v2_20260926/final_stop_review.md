# Stop-policy v2: final read-only second-pass review

Date: 2026-09-26. Reviewed the current runtime against the preserved v1 archive
`preservation/production_source_v1.tgz`, not against the much older upstream
Git base. No source/test edits, compilation, test execution, or flights were
performed during this review. This is a second pass by the stop-patch author,
not an independent-author or formal safety certification.

## Verdict

No new blocking regression was identified in the scoped v1-to-v2 change.
The early-soft-margin loophole is closed at the production stop-admission
call site: a deferred margin does not authorize a stop unless the complete
prepared query traversal and final map/deadline checks finish. Two test-coverage
qualifications below should accompany the existing offline validation report.

## Production control-flow checks

| Area | Reviewed behavior |
|---|---|
| Ordinary candidate/live margin policy | The header defaults to `RejectImmediately`; only `certifiedStopExistsFrom` explicitly selects deferral. Ordinary first-margin returns remain immediate. |
| Deferred margin | The loop records the margin and continues. Subsequent existing occupied, configured-unknown, out-of-map, and timeout branches still return immediately with `hard_checks_complete=false`. |
| Completion proof | The result starts false. The only assignment to true is after the loop, final escape-tail handling, final map-version check, and final deadline check; exact positive expected-query count is required. |
| Final escape-prefix margin | A failed free-tail/departure condition defers only under the stop policy. Ordinary policy still returns margin without a completion proof. |
| Stop admission | `admissibleStop(safety.safe(), is_margin, hard_checks_complete)` accepts a margin only with the proof. A later hard status is not accepted even if a margin was previously encountered. |
| Sampled-state failures | Empty input, invalid finite/range configuration, failed `getState`, and nonfinite state reject instead of being silently skipped. |
| Receipt version | The producer and runtime demand consumer both obtain revision 2 from the planner getter. Generic frozen policy defaults remain revision 1; mismatches fail closed. |
| Runtime FSM diff | Only numeric byte serialization, startup marker/revision, and demand policy revision selection change. No timer, lock, command publication, brake dispatch, or Full-ACK release condition changes in this v2 diff. |

The helper's query counter is not an independently sufficient physical
certificate: correctness depends on its reviewed call site setting the result
only after the checks. In particular, the existing `safe()` behavior still
includes disabled validation; this patch does not convert guard-disabled mode
into a certified mode.

One narrow semantic qualification: ordinary **margin** behavior is preserved,
but ordinary validation gains an additional final cooperative deadline check.
Work that expires during the final map-health read can now fail closed rather
than return SAFE. Thus “all ordinary behavior is byte-for-byte unchanged” would
be inaccurate; “ordinary immediate-margin semantics are preserved” is correct.

## Evidence and report consistency

Reviewed `stop_policy_v2_validation.md`, the three new C++ test fixtures, the
extraction driver, and both final machine-readable results. Both
`stop_margin_tests/production_{normal,sanitized}_final/result.json` report
exit code 0, 13 cases, empty stderr, and source hashes matching current
production. All eight runtime files byte-match their repository mirrors.
The 13-case count is eight geometry-policy cases plus five sampled-state
assertion groups; it is not 13 physical map scenarios.

The report correctly distinguishes:

- policy-helper tests from exact extracted production control-flow tests;
- real production function bodies from fixture map predicates, linear
  trajectories, DDA, and stop-existence predicate;
- executable traversal tests from source-contract assertions for the actual
  stop caller, receipt consumer, and numeric JSON byte serialization;
- normal/sanitized offline checks from ROS flight or real-map integration.

The report's explicit unknown-space limitation is necessary and accurate.
Production sampled stop viability continues to pass `unknown_as_occupied=false`.
The fixture's unknown=true case proves the optional hard rejection remains
reachable, while its unknown=false case deliberately accepts the same space.
Neither the patch nor the passing fixture establishes strict known-free space,
continuous swept-body safety, conservative voxel-volume coverage, or a
population-level zero-contact guarantee. The initial-footprint exception and
occupied-voxel-centre geometry remain inherited query semantics.

## Coverage qualifications and proposed additive cases

1. The exact production fixture calls `validatePositionTrajectory` with
   `allow_initial_clearance_escape=false`. The real stop caller uses true.
   Therefore the **final escape-prefix deferral branch** currently has helper
   coverage and source review, not a direct executable production-branch test.
   Proposed addition: a configurable 0.10 s trajectory remaining in the initial
   margin cluster through its terminal point. With escape enabled, deferred
   policy must return margin with proof true and `used_clearance_escape=false`;
   ordinary policy must return margin with proof false. Also test a later hard
   hazard following an initial prefix and a final map-version change.
2. The existing timeout fixture sleeps in a later map query, but asserts only
   `VALIDATION_TIMEOUT` and proof false. A scheduling delay could expire its
   2 ms deadline before the first margin and still satisfy those assertions.
   It proves timeout rejection, but is not a deterministic proof of the
   **margin-then-timeout** ordering. Proposed addition: a test-local controlled
   clock that advances only at a recorded later query; require that the first
   margin and later timeout-trigger query were both visited before asserting
   timeout/proof false. Keep the extracted production function text unchanged
   and label the clock as a fixture, not real-time performance evidence.

These are coverage/claim qualifications, not newly demonstrated production
failures. The coordinating agent has requested preparation only while the
current cohort remains frozen; the additions above have not been implemented
or run in this review.

## Remaining limits

Complete hard-query traversal can cost more than an early margin return;
prospective flight timing remains necessary. The related G1 ON timing note
shows approximately 0.238 ms CPU per stop-viability call and no command-rate
gate failure in one sample, but does not establish general timing bounds.
The stop caller currently supplies no finite deadline; the patch preserves
that existing policy rather than claiming bounded worst-case stop-search cost.

Recommended final wording: “Revision 2 prevents an early soft-margin result
from standing in for a fully traversed sampled stop check, under the unchanged
unknown-space and physical-query policy. Offline control-flow checks and
prospective smoke results do not by themselves prove general safety.”
