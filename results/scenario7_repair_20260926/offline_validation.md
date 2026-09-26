# Repair validation before flight

- Old campaign: `../scenario7_n10_20260925_213533_3120932` (unchanged).
- Separate build/install: `/root/super_ws/scenario7_repair_20260926`.
- rog_map, super_planner and perfect_drone_sim: Release builds succeeded.
- Initial perfect_drone_sim build failed under colcon's explicit 20-way parallel
  compilation; retry using `MAKEFLAGS='-j1 -l1'` succeeded in 3 min 37 s. No old
  install overwritten. This was a build infrastructure failure, not a flight.
- Python suite `python3 -m pytest -q test/test*scenario7*.py`: 230 passed,
  1 skipped (optional real-cloud benchmark).
- Optional real-cloud test rerun with `SCENARIO7_INDEX_CLOUD_TESTS=1`: 3 passed,
  including actual Urban/normal PCD query equivalence (no skip).
- SimplifySFC real-geometry progress test: normal and ASan/UBSan/leak checks pass;
  before/after witness and limits documented in `g4_memory_diagnosis.md`.
- Trajectory handoff guard: normal and sanitizer tests pass; valid polynomial
  prefixes and scaled/stale/discontinuous cases covered.
- Initial footprint egress receipt: helper and real CmdTraj metadata tests pass
  normally and with ASan/UBSan/leak checks. CmdTraj tests cover immutable copied
  and shared receipts, actual commit generation assignment, new-generation
  invalidation, replacement and empty reset.
- Actual controller dry-run: `dryrun_smoke_v1`, ON9/OFF9 for G1/G4/Urban n=1;
  30 commands (24 static checks + 6 three-mode batches), 1738 frozen paths.
  Exact ament resolution selects all three repair packages. Report-only mode
  works without requiring the installed overlay and uses the stored rounds.

Actual flights are separate evidence at
`../scenario7_repair_smoke_20260926_v1`; this offline report does not assert their
outcomes or certify the unresolved G1 r01 smooth-contact mechanism.
