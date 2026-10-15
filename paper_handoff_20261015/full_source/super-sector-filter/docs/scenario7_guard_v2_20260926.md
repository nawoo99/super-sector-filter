# Scenario7 guard contract v2 — prospective experimental repair

Candidate: `c27_guard_contract_v2`. This is a new cohort after the failed
`c26_scenario7_repair_v1`, not a rewrite or replacement of its failed trials.
The user authorized another safety repair. The original install, v1 overlay,
map/mission assets and prior outcomes must remain unchanged.

## Bounded changes

1. Preserve same-voxel LiDAR hit multiplicity in the no-raycasting map update.
   Skip only duplicate free-ray work, not hit observations. With the actual
   p_min=.12, p_hit=.9 and p_occ=.85, a previously free cell remains below the
   occupied threshold after one coalesced hit; two true hits cross it. The
   existing claim that one hit always suffices is false for a free prior.
2. In no-raycasting/occupied-accumulation mode, observed-free marker updates
   must not erase an already occupied cell. The 0.15 m observed-ray cell centre
   can lie off the physical ray when inserted into the 0.05 m raw grid. The
   real-library regression erases an occupied raw and inflated obstacle with
   100 such off-axis misses. Full raycasting mode retains its normal clearing
   semantics. No static map/solid ground truth is supplied to planner decisions.
   Occupancy accumulation is evaluated here for the existing static scenarios;
   removing dynamic obstacles or noisy false hits in this mode is not validated.
3. A stop-viability check may waive the soft inflation margin only after
   checking the entire stop for hard failures. An early CLEARANCE_MARGIN must
   not conceal later OCCUPIED, UNOBSERVED, invalid geometry or map/deadline
   errors. A completion proof bit and a new stop-policy revision distinguish
   the stronger traversal contract from v1. Failed/nonfinite state evaluation
   is fail-closed. Ordinary candidate clearance rules remain unchanged.

One observation-only correction also serializes the command's uint8 trajectory
flag as a JSON integer, not a raw control character. The v1 probe exposed this
format error; its original invalid records and trace-loss audits are retained.
This does not change the published command or make an incomplete trace complete.

These changes do not assert strict observation completeness: candidate/live
unknown-space policy and the existing neighbouring-cell coverage heuristic are
still separate known limitations. Do not silently describe unknown as known
free. Raw-cloud CIRI remains shadow-only and default-off. No increased A*
budget, reduced collision radius, relaxed timing/resource gate, map changes,
or success-only trial selection is permitted.

## Evidence and preservation

Previous failed cohort:
`results/scenario7_repair_smoke_20260926_v1` (ON7/OFF6, retained G1 and Urban
Adaptive contacts). Bounded ROI probes of the unchanged v1 binary are diagnostic
only, not CPU/safety primary evidence or profile references. Trace drops, caps,
missing footers and early script failures are retained, never interpreted as
absence of an obstacle. Urban ROI is centred at the entry wall (22,9.5), not
the building centre; G1 uses cylinder68 (-28.591183,-4.598807).

Pre-edit source archive:
`results/scenario7_guard_v2_20260926/preservation/production_source_v1.tgz`,
SHA256 `63e1e4a41fbd6b214b15eebf73cc94c3e28545c7ba5326c8fe9f6ddac38418ee`.
The new install is `/root/super_ws/scenario7_guard_v2_20260926/install`.
Build serially with `MAKEFLAGS='-j1 -l1'` as well as the sequential colcon
executor; CMAKE_BUILD_PARALLEL_LEVEL alone did not constrain colcon previously.

## Validation before promotion

- Run the real occupancy-library regression against old and new implementations.
- Test deferred-margin traversal with later hard failures and revision-bound
  stop receipts; run applicable prior regressions and sanitizers.
- Verify runtime/mirror equality and freeze exact changed source, binary,
  observer, static transport and mission identities in a new admission.
- Start with selected G1/Urban/G4 three-mode n=1 checks, keeping profiled ON and
  unprofiled OFF evidence separate. OFF requires valid same-revision ON evidence.
- Report completion and contact separately, including every failed/ineligible
  attempt. Never retry a failed trial as its replacement or pool old/new data.
- A small smoke pass is not population-level safety, a seven-map confirmation,
  or proof that all unknown-space and collision representations are sound.

Results and remaining defects will be documented separately after validation;
this file is the prospective protocol, not a claim of completed safe flights.
