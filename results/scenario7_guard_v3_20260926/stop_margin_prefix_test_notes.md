# Supplementary stop-prefix coverage (additive)

Status: **normal and ASan/UBSan runs both passed all eight cases**, after explicit CPU-slot approval. Compilation was sequential, one compiler job at a time. Both compiler exit codes and test exit codes are zero; runtime stderr is empty. Both builds retain one fixture-induced unused-variable warning for the no-op map-read transaction. There were no failed test attempts or retries. The earlier preparation-only output remains preserved and is not itself a passing-test claim.

New owned source files only:

- `super_planner/test/stop_margin_prefix_supplement_test.cpp`
- `super_planner/test/stop_margin_prefix_supplement_test.py`

Their new repository mirrors are under `super_patches/native_seedmap_campaign/super_planner_test/`. Existing production, frozen tests, and prior results are not edited.

The driver reuses the existing integration driver's literal/comment-aware extractor, inventories that dependency, and compiles the exact unmodified `validatePositionTrajectory` body and its production result types/name function. Map predicates, a configurable linear trajectory, midpoint DDA, and CPU-scope placeholders are explicitly fixtures. This is control-flow coverage, not ROS, real-map, continuous-time, voxel-volume, or physical safety evidence.

Eight executed cases all call with `allow_initial_clearance_escape=true`:

1. A 0.10 s trajectory remains in the initial margin cluster through its terminal point. Ordinary policy returns final `CLEARANCE_MARGIN` with proof false.
2. The same prefix under deferred policy returns margin with proof true, `used_clearance_escape=false`, and all five prepared fixture queries visited.
3. Initial prefix followed by an occupied hard rejection.
4. Initial prefix followed by configured-unknown rejection (`unknown_as_occupied=true` is a fixture setting; the actual stop caller's false setting is not redefined).
5. Initial prefix followed by out-of-map rejection.
6. Final-prefix deferral followed by a changed third/final map-health snapshot rejects with `VERSION_CHANGED` and proof false.
7. Ordinary-policy control returns on the later margin band, confirming that fixture band really reaches a soft-margin result rather than an initial escape continuation.
8. Deferred policy visits that same margin and its clear raw-body query, then a recorded later map query sleeps beyond a real three-second deadline. The test requires both margin/body flags and the later timeout-trigger flag before accepting `VALIDATION_TIMEOUT` with proof false.

The timeout does not override `std::chrono` or any standard-library definition. Arbitrarily heavy scheduling delays can expire the budget before the trigger; explicit visited-order assertions then fail instead of falsely claiming margin-before-timeout coverage. The budget is conservative for this tiny fixture but is not a deterministic timing guarantee under arbitrary load, nor a performance bound for production.

Preparation command (no compiler/executable):

```bash
python3 /root/super_ws/src/SUPER/super_planner/test/stop_margin_prefix_supplement_test.py --prepare-only --output /root/super-sector-filter/results/scenario7_guard_v3_20260926/stop_prefix_prepare
```

Executed results:

- [Normal result](stop_prefix_normal/result.json): 8/8, exit 0.
- [ASan/UBSan result](stop_prefix_sanitized/result.json): 8/8, exit 0, no sanitizer diagnostics.

## Exact branch evidence

The two short-prefix cases each assert exactly five inflated-map queries (start, two fixture midpoint DDA points, two endpoints), a terminal visit, margin/body-query visits, `first_collision_tt=0`, and `used_clearance_escape=false`. Ordinary policy returns margin before the final health read (`health_reads=2`, proof false); deferred policy continues through the final health read (`health_reads=3`, proof true). This directly executes the production final escape-prefix deferral branch, rather than only testing the policy helper.

Each later-hard-hazard case records an earlier margin/body visit and a later hazard visit, returns its corresponding hard status, and retains proof false. The final-version case records terminal/margin visits and changes only health read three, so it proves post-traversal version rejection following final-prefix deferral.

The timeout case records `margin_visited=1`, `margin_body_checked=1`, and `timeout_trigger_visited=1`, then returns `VALIDATION_TIMEOUT` with proof false. The ordinary-policy control returns `CLEARANCE_MARGIN` in that same later band (0.18–0.30), confirming it is not merely an initial-prefix continuation. The map fixture sets `terminal_visited` at x=0.10: this means the actual terminal only for the short-prefix cases, not for the 1.0 s later-band controls; no full-trajectory completion claim is made for timeout.

The executed tests therefore close the specific executable-coverage qualifications recorded in the v2 review. They do not change production behavior or expand the unknown-space, voxel-volume, physical safety, or real-time claims.

## Source and evidence identity

All eight source dependencies in each result were rehashed after both runs and still match the recorded hashes. Both new files byte-match their repository mirrors. No frozen fixture or production file was modified.

| Item | SHA-256 |
| --- | --- |
| New C++ fixture (runtime and mirror) | `939034099d80d5a06830e6b06bada8732130ddc41c41849355222a6f431b5912` |
| New Python driver (runtime and mirror) | `5c83c59633950252c015db5f667d2af91cdf2674c8520a059a87f4642308134e` |
| Extracted production validator (without appended file newline) | `d8043e18190e3f18cadb932438e02ac98a5d2322350d39eac8c17da2d0557c8e` |
| Normal `result.json` | `a4d71fd4657127dfa85dcf8ebb3c7bb9225d32c9cb36d13028f5029e77cd806c` |
| ASan/UBSan `result.json` | `e3fa49381525fbe3f89e4836b850b692c3da3e5b74836671aa8f98efc5b4d933` |
