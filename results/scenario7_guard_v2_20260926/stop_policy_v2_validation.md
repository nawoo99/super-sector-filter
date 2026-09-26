# Stop-viability policy revision 2: implementation and offline validation

Date: 2026-09-26. Changes were applied only after the coordinating agent completed and preserved the v1 ROI probes. This note covers the stop-certificate repair and one diagnostics serialization fix, not the separate occupancy-map repair or a flight-safety result.

## Fixed contract

Previously, `certifiedStopExistsFrom` accepted `CLEARANCE_MARGIN` even when `validatePositionTrajectory` returned at the first soft-margin query. A later occupied/unknown/out-of-map segment could therefore remain unexamined. Revision 1 also permitted `candidateStopsViable` to skip a failed `getState` evaluation.

Revision 2:

- Adds an explicit `DeferSoftMarginUntilHardChecksComplete` validation policy, used only by the sampled stop-viability caller. Ordinary candidate/live validation retains the default `RejectImmediately` margin policy.
- Retains the first soft-margin diagnostic, visits all remaining prepared queries, and preserves all existing hard rejection paths.
- Sets `hard_checks_complete` only after all expected queries and final deadline/map-version checks complete. A stop can accept `CLEARANCE_MARGIN` only with this proof bit. Early-return margin results cannot authorize a stop.
- Rejects empty trajectories, invalid horizon/sample period, failed state evaluation and nonfinite sampled states in `candidateStopsViable`.
- Uses stop-viability receipt revision 2; the FSM explicitly selects revision 2 when evaluating demand-replan evidence. Frozen generic policy defaults and revision-1 test fixtures remain unchanged.

**Unknown-space semantics are deliberately unchanged.** Sampled stop viability still explicitly passes `unknown_as_occupied=false`. Candidate/live validation and the immutable map's neighborhood observation heuristic are not changed by this patch. Existing physical-body and narrowly scoped initial-footprint rules remain the underlying query semantics. “Complete hard checks” means all hard checks under that explicit policy completed; it is not a strict-known-free or continuous swept-body proof.

The existing startup marker, once per demand-enabled FSM, now ends with:

```text
[GUARDED_DEMAND_REPLAN] ... stop_policy=sampled_unknown_allowed_soft_margin_after_complete_hard_checks stop_policy_revision=2
```

Separately, the ROI `published_position_command` JSON serializer now casts the unsigned-byte trajectory flag to `unsigned int`, preventing a raw control byte from corrupting JSON. No old trace file was altered or reinterpreted as valid.

## Changed files

Runtime package `/root/super_ws/src/SUPER/super_planner`:

- Modified `include/super_core/super_planner.h`, `src/super_core/super_planner.cpp`, `include/ros_interface/ros2/fsm_ros2.hpp`.
- Added `include/fsm/stop_margin_certificate.hpp`.
- Added `test/stop_margin_certificate_test.cpp`, `test/stop_margin_demand_policy_test.cpp`, and `test/stop_margin_validator_integration_test.{cpp,py}`.

All eight files were copied to their corresponding `super_patches/native_seedmap_campaign/super_planner_{include,src,test}` mirrors and byte-compared successfully after testing. No production source changed after the “ready for ROS build” notification.

## Offline results

| Test layer | Normal | ASan + UBSan | What it proves |
|---|---|---|---|
| `stop_margin_certificate_test.cpp` | PASS | PASS | Deferral/proof helper, incomplete traversal rejection, early margin followed by hard failure, unchanged ordinary immediate-margin behavior. |
| `stop_margin_demand_policy_test.cpp` | PASS | PASS | Frozen revision-1 assertions still pass; revision-1 receipt cannot authorize revision-2 skip, matching revision 2 can, unexpected revision rejects. |
| Extracted production validator + sampled-state traversal | PASS, 13 cases | PASS, 13 cases | Exact production return/control flow handles deferred margin followed by later occupied, unknown, out-of-map, version change or timeout; state-evaluation failures reject. |

The additive demand test also executes the unmodified legacy fixture: 41 decision cases, 21 nonfinite cases, and the fixture's 101 guard/command ticks, 15 demand ticks, five solves, ten skips. These are synthetic test counts, not measured flight frequencies or CPU savings.

The production extraction test compiles the actual bodies of `validatePositionTrajectory` and `candidateStopsViable` without replacing their traversal logic. Its map predicates, linear trajectory, DDA query fixture and stop predicate are controlled fixtures. Thus it is stronger than a reimplemented stream-policy test but **not** a real-ROG-map/ROS integration or sensor/flight validation. Source-contract assertions separately confirm the actual stop caller consumes the proof, the FSM binds the revision, and the diagnostic flag uses numeric serialization.

Final machine-readable results:

- `stop_margin_tests/production_normal_final/result.json`
- `stop_margin_tests/production_sanitized_final/result.json`

Extracted validator SHA256: `d8043e18190e3f18cadb932438e02ac98a5d2322350d39eac8c17da2d0557c8e`.

| Production source | SHA256 |
|---|---|
| `super_planner.h` | `3c0927c0b19142c177f15d11eb2cf29c705e4b3bebe3db5e8709ff6b6730eb9b` |
| `super_planner.cpp` | `2a7127726488cc0c965edeb0e38fec9b2a4faf2770f45d6e71dc3684e4215d6b` |
| `fsm_ros2.hpp` | `89c1ddad9dcd30d4e742487ffd78086edb090109e7da3f2a0a475624564628f1` |
| `stop_margin_certificate.hpp` | `af40b773a66f859b2edbc0f4220afe675c282fd5c427f787bcdb397ff14f5462` |

Final integration fixture SHA256: C++ `ef4f58a4e3606b5e5388c36da2af7e375ebd4581c14ad62056943e487023a882`; Python driver `e647c4d71534492b287402cdaf087c346d188539ea4503c3c6c015fae0057fd0`.

The initial `production_normal` extraction attempt failed to compile because the older reusable extractor did not ignore braces inside C++ character literals used by diagnostic JSON. Only the new driver's lexer was corrected; the partial failed extraction remains preserved. Subsequent eight-case runs passed; the final fixture adds five actual sampled-state traversal cases, and both final 13-case runs pass. The fixture emits one harmless unused transaction warning because its map-lock object has no runtime behavior.

## Remaining validation

The coordinating agent owns the full ROS build and prospective v2 flights. This offline result does not establish zero contacts, completion rate, retained CPU savings, or known-free stopping safety. Full traversal can cost more than the old early-margin return; actual timing and completion need fresh measurement under the unchanged campaign gates.

## Post-smoke review qualification

The final second-pass review is `final_stop_review.md`. The timeout fixture
checks TIMEOUT and no completion proof, but does not assert the first margin
query was visited before expiration; the table above must not be interpreted
as a proven margin-then-timeout ordering. The production initial-clearance-prefix
final deferral branch also lacks executable fixture coverage. Ordinary candidate
margin policy is unchanged, with an additional final fail-closed deadline check.
The completed smoke and retained flight failures are documented in
`docs/scenario7_guard_v2_results_20260926.md`; this candidate is not promoted.
