# G4 sector memory-runaway diagnosis and bounded repair

Date: 2026-09-26. Offline analysis/tests only; no new flights. Original campaign results and installed binaries were not changed by this repair.

## Evidence and confidence

The affected attempt is `scenario7_n10_20260925_213533_3120932/test10/gapfree_d1_m04/r08_run40173`, sector mode. Its composed executable is named `perfect_drone_adaptive_node`; this name does not mean the failed attempt used adaptive sensor mode.

- `diagnostic_contamination.json` records PID 3310925 at 4726.1171875 MiB RSS, above the unchanged 4608 MiB guard. The entire triplet's performance metrics are invalid; existing outcomes remain retained.
- `memory_runaway_diagnostic/gdb_backtrace.txt:35` captures the active planning thread in `sdlp::linprog -> findInterior -> SimplifySFC -> ExpTrajOpt::optimize -> SuperPlanner::generateExpTraj -> PlanFromRest -> FSM`. Other captured threads mostly wait.
- Failed-sector scratch diagnostics were copied unchanged from `/tmp/scenario7_n10_ycwifuch` to this repair's `evidence/g4_sector_memory/` to avoid losing them with scratch cleanup. The original campaign folder had no completed sector raw row.
- Sector RSS stays about 3375 MiB through elapsed 35.062 s, then climbs to 3475.7, 3627.2, 3794.8, 3944.3, 4112.4, 4299.0, 4407.6, 4574.6 and 4740.1 MiB at 37.119 through 45.416 s. PSS grows similarly; process swap remains zero. RSS then stays flat while GDB pauses execution, which is not evidence of recovery.
- Nine other G4 sector runs peak between 3387.6 and 3427.7 MiB, without accumulating across process restarts. The anomalous within-attempt growth is therefore not explained by normal map-loading baseline or a steadily increasing cross-run leak.
- Immediately before growth, the third mission goal is accepted; backup optimization/replans fail or overrun, the preceding trajectory ends, FSM enters GENERATE_TRAJ, and a PlanFromRest attempt fails. The last completed planning-state message is `[Fsm 36.350] Current state: GENERATE_TRAJ`. Sensor frames continue while planning stops returning. These preceding failures explain entry into recovery, not the exact corridor geometry that caused the loop.

The source defect is definite and reproduces deterministically. Its match to the active captured stack and runaway allocation pattern is strong causal evidence for this attempt. The diagnostic did not capture corridor matrices or local loop indices, so this is not an exact replay of the recorded corridor and does not establish why that particular corridor became disconnected.

## Defect and bounded fix

In `super_planner/include/data_structure/base/polytope.h`, the old SimplifySFC non-overlap branch appended `last_overlapped`, assigned it to `check_cand`, and decremented `i`. If that bridge also cannot reach candidate `i`, the same bridge/index repeats forever, allocating another polytope each time.

Concrete real-geometry witness: three boxes have X intervals `[0,2]`, `[1,3]`, `[4,6]` and Y/Z intervals `[-1,1]`. Box 0 overlaps 1, but neither 0 nor 1 overlaps 2. At candidate index 2 the old anchor changes 0 -> 1 once; all subsequent iterations keep anchor 1 and candidate 2 while appending box 1 indefinitely. A touch-only pair also has no strictly positive interior and follows the same path.

The fix validates the initial bridge and tracks anchor/bridge indices. A failed overlap can append/retry only if the anchor advances; otherwise it returns false before another append. An index is therefore tested at most twice, and the result vector stays bounded by the selected input size. Every rejected path leaves the caller's corridor and its metadata unchanged. Existing optimizer callers already turn false into an optimization failure. Successful selection and the existing <=2-corridor pass-through policy are unchanged.

## Offline validation

Test: `super_planner/test/simplify_sfc_progress_test.cpp`, mirrored under `super_patches/native_seedmap_campaign/super_planner_test/`.

- Normal test: PASS. Covers disconnected and touching initial/later bridges, late disconnection, input/metadata preservation, 1000 repeated failures, and four successful selection/trimming cases.
- ASan + UBSan + leak detection against the real polytope, geometry and SDLP source implementations: PASS, no reports.
- Preserved pre-fix header: the same disconnected witness, limited to 256 MiB address space and five seconds, throws `std::bad_alloc`; observed 0.778228 s and 170936 KiB peak child RSS.
- Fixed header: the same witness returns false with unchanged input; observed 0.004574 s and 6528 KiB peak child RSS. These are illustrative one-shot diagnostic measurements, not campaign performance results.
- All four valid cases produce identical before/after selections: bridge=3, shortcut=3, trimmed=3, common=1, with metadata unchanged.

Executables are in `validation/simplify_sfc_progress{,_before,_sanitized}_test`. They are standalone and do not start ROS or simulation. Compile normal/sanitized with C++17, `-DCLASS_COLOR_MSG_UTILS -ffunction-sections -fdata-sections`, planner/ROG-map/Eigen includes, and the test plus `src/utils/{polytope,geometry_utils,sdlp}.cpp`; link `-Wl,--gc-sections -ldl`. The color define skips unrelated ROS logging includes only. Sanitized adds `-fsanitize=address,undefined -fno-omit-frame-pointer`; run with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`. The before executable defines `SIMPLIFY_SFC_TEST_HEADER` as the preserved absolute header path and links the preexisting installed `libsuper.a`.

## Preservation and hashes

- Pre-edit header, including preexisting user changes: `preservation/polytope.h.before`, SHA-256 `e0c58352f05b843d2fc126315ab40e6338c1c021e8cf3a27534ed6fd9d4b832f`.
- Fixed runtime and mirror header: `1a5be294fbc9f37eb4fe6c6849c949edbf3ce16645e7fa99b022e3d25732122e`.
- Runtime and mirror test: `2a23561276575e0c451fa7a7d5b25ad9584894b1f9473b406a4ca5266fa423d2`.
- Preserved sector memory CSV: `bdc0c1c22c0929deaf4990c5c57740743455f91c3dee29a75f02f0314fd63515`.
- Preserved sector cgroup CSV: `7c7783d687c946405984575b359e1a52faec1dbeffd12d6ee19364a8718f4401`.
- Preserved sector stack log: `fb2a59f241b49edf40c3c8c3022edc23d74a5bf926b45c626f9ed4199514ae3a`.

No cap increase, collision-policy loosening, automatic retry, installed-binary replacement, or rewrite of previous campaign outcomes was performed.
