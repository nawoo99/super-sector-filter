# ROG occupancy: bounded real-library offline proof (2026-09-26)

These are deterministic implementation regressions, not a claim that either
mechanism caused a specific recorded flight contact. No ROS node or flight was
started for this probe. Production files were not edited during this proof.

## Inputs and executable

- Test: `/root/super_ws/src/SUPER/rog_map/test/occupancy_hit_multiplicity_test.cpp`.
- Test SHA256: `1556389dd9c2fc28804211360e52ff74f3be40a396ad883d9c04145492fedfb1`.
- Preserved pre-fix binary: `offline_rog_proof/multiplicity_test_v1` beside this
  note (the same directory also preserves the exact test source).
- Binary SHA256: `297fa6b6614373890810f1809c380f1f4ae450479b8868f429294c7e24be97ea`.
- Actual linked frozen repair-v1 library:
  `/root/super_ws/scenario7_repair_20260926/install/rog_map/lib/librog_map.a`,
  SHA256 `4f5faf78d73a693f231778560627596f5024fac5d02bc2a9bfd2b525e7497ed2`.
- Actual config:
  `/root/super_ws/scenario7_repair_20260926/install/super_planner/share/super_planner/config/static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml`,
  SHA256 `d853803fb53088506e25c273564dec7b0b759e264c61cec64b0387d16ae84786`.
- Runtime `prob_map.cpp` before repair:
  SHA256 `44f771f08222ff52e0cb0ad89c3ae6a026bd632e3b708daa9182046d4c6da09f`.

The subclass uses real `raycastProcess`, `probabilisticMapFromCache`,
`hitPointUpdate`, `missPointUpdate`, raw occupancy queries and `InfMap` queries.
Production probabilities/resolutions are retained; only test map dimensions and
vertical bounds are bounded for allocation. It does not reimplement probability
updates or inflation. No synthetic ground truth is fed to a running planner.

Compile from `/root/super_ws/src/SUPER` using C++17, `-O2`,
`-DORIGIN_AT_CORNER -DUSE_ROS2`, the existing
`scenario7_repair_20260926/build/rog_map/CMakeFiles/rog_map.dir/flags.make`
include flags, the test source, the above static archive, and
`-lyaml-cpp -lfmt -lpcl_common -lpcl_io`.
Run `multiplicity_test CONFIG --probe` to print the pre-fix data; default mode
asserts the repaired contracts and exits **1** against this pre-fix library.

## Proof 1: same-voxel dedup drops real hit evidence

Configured `p_min=.12`, `p_hit=.9`, `p_occ=.85`, `p_max=.98` give
`l_min=-1.9924300909`, `l_hit≈2.19722438`, `l_occ=1.73460125923`.
Seed the target voxel to prior-free using the real miss update, then supply
multiple identical retained sensor points in a single no-raycast scan.

| Input hits | Actual retained hits | Actual final log odds | Actual raw / inflated | Reference retaining every hit | Reference raw / inflated |
|---:|---:|---:|---|---:|---|
| 2 | 1 | 0.204794287682 | false / false | 2.40201854706 | true / true |
| 100 | 1 | 0.204794287682 | false / false | 3.89182138443 | true / true |

`prob_map.cpp:873` skips `insertUpdateCandidate` for duplicate hit voxels.
Its comment that one hit exceeds the occupied threshold assumes a favorable
prior; it is false after accumulated free-space evidence. The reference invokes
the same actual `hitPointUpdate` with the original retained hit multiplicity.
Original upstream no-raycast logic in repository HEAD enqueued every hit.

Minimal intended repair: retain the duplicate's hit contribution via
`insertUpdateCandidate` before continuing; still perform the expensive
observed-space ray march only once per hit voxel. Do not raise thresholds,
reduce safety margins or introduce new counter saturation without separate proof.

## Proof 2: coarse observed-free rays erase off-axis occupied evidence

Sensor is `(0,0,1)`. The target raw voxel centre is `(.825,.075,.975)`, with
voxel bounds `x[.8,.85), y[.05,.1), z[.95,1.0)` at 0.05 m resolution.
Supply 100 distinct endpoint voxels:
`(1.525 + .05*i, .001, 1.001)`, `i=0..99`.
Every exact sensor ray has `y<.001` and `z>=1.0`, so **none intersects the target
raw voxel**. The 0.15 m observed-space DDA emits `(.825,.075,.975)` anyway.
The test first removes unrelated prior-test occupancy, then initializes this
target using two actual hits after a free prior.

| Actual processing mode | Target | Cached misses | Before log odds | After log odds | Raw / inflated |
|---|---|---:|---:|---:|---|
| no-raycast coarse observed-space march | off-axis voxel | 100 | 2.40201854706 | -1.598508358 | false / false |
| full probabilistic raycasting | same off-axis voxel | 0 | 2.40201854706 | 2.40201854706 | true / true |
| full probabilistic raycasting | on-axis voxel `(.825,.025,1.025)` | 100 | 2.40201854706 | -1.598508358 | false / false |

The test also checks that a non-occupied unknown cell still receives free-space
evidence: before `0.204794287682`, 100 coarse misses, after `-1.9924300909`,
raw/inflated false. The repair must not suppress this observed-space marking.

Thus this is not merely extra free coverage: the approximation removes a real
occupied cell and its inflation. Real raw-resolution raycasting does not have
the off-axis error and must retain its intentional on-axis clearing behavior.

Root-approved narrow repair design (not yet applied when this note was made):
in `probabilisticMapFromCache`'s miss-only branch, retain an already OCCUPIED cell
when `!cfg_.raycasting_en`; continue writing observed-free markers for
non-occupied cells. Preserve `raycasting=true` clearing and explicit startup
reset behavior. Emit diagnostic evidence of a preserved miss with before==after
and a reason identifying occupancy-only evidence preservation.

## Scope and remaining caveats

- The original no-raycast branch was occupancy-only accumulation; the observed
  free markers and same-voxel coalescing were already recorded by the Aug-22
  strict-burst changes (`docs/viability_guard_ciri_avoidance_2026-08-15.md`,
  section 8.17), not introduced by the current repair.
- `updateProbMap` has a startup-only `static bool first` near-body clearing loop
  of radius `raycast_range_min=.5m`. It calls `missPointUpdate(...,999)` on the
  first processed update only, not each frame. The narrow repair above leaves it
  unchanged. It is not a direct explanation for urban wall entry around 23s.
- Every scan also discards hit endpoints nearer than .5m. Once the sensor is
  inside or very close to an unobserved wall, fresh near-surface hits cannot
  repair that occupancy through this branch. This filter remains unchanged.
- Current trajectory checks compare radius-.2 spheres to occupied voxel
  **centres**, not closed voxel volumes or full box/cylinder interiors. That
  representation is not identical to the independent solid-contact audit.
- `boxSearch` excludes min/max boundary index layers in both optimized and
  baseline versions; its half-cell-padded physical-body search needs an exact
  tangency regression. Comparing optimized versus baseline alone cannot catch
  a common-boundary omission.
- Snapshot float indexing uses floor(position/resolution), while writer
  indexing uses floor(position*(1/resolution)); exact floating-point grid
  boundaries warrant consistency tests. No broad origin/hash mismatch was
  established by this bounded review.
- The 0.005s polynomial sampling plus straight-chord DDA is not a swept-solid
  mathematical certificate. No independent curve-between-samples counterexample
  has been established here. Do not blame it for the recorded contact without
  its actual occupied snapshot and trajectory.

The ROI flight probes remain necessary to connect a demonstrated implementation
defect to a particular G1/urban contact. These offline results alone do not make
the campaign production-ready.

## Applied repair and verification

After root explicitly released the unchanged-v1 probe freeze, the two narrow
repairs described above were applied to `prob_map.cpp` and mirrored. Final
production SHA256:
`3ee0f4e6b2136ea0423313c8231acf70f056a33b3c8747b01bf11091d3d29805`.
The preserved-miss trace uses canonical `gridTypeName` labels, operation
`observed_miss_preserved`, and reason `no_raycast_occupied_evidence`.

Verification:

- Original frozen archive: default regression exits **1**, demonstrating the
  pre-fix failures; `--probe` prints the measurements above.
- Isolated rebuilt actual `ProbMap.cpp` plus unchanged support archive: default
  regression exits **0**.
- Final v2 installed actual archive: default regression exits **0**. Archive
  `/root/super_ws/scenario7_guard_v2_20260926/install/rog_map/lib/librog_map.a`,
  SHA256 `3fc3f5561d70668874b446c6a51e067311c38e17c9eb39e9fe4c5581d73b5860`.
- ASan+UBSan instrumenting final changed `ProbMap.cpp` and regression source:
  exits **0**, `ASAN_OPTIONS=detect_leaks=1`,
  `UBSAN_OPTIONS=halt_on_error=1`, no sanitizer findings. Unchanged support
  objects are from the uninstrumented frozen archive; this is not a claim that
  every linked library was sanitizer-instrumented.

After repair, two actual hits produce `2.40201854706` and 100 hits produce
`3.89182138443`, exactly matching the retained-multiplicity reference, with raw
and inflated occupancy true. The 100 no-raycast off-axis misses preserve
`2.40201854706`, raw/inflated true. Unknown-cell observed-free marking remains
`0.204794287682 → -1.9924300909`. Genuine full-ray off-axis retains occupancy;
genuine full-ray on-axis still clears it to `-1.598508358`.

Preserved executables beside this note:

- `offline_rog_proof/multiplicity_test_v2_archive`, SHA256
  `5044f3c3ed88b69367af37964d279d31f73fb30e57ecdee052ded6e946eb1388`.
- `offline_rog_proof/multiplicity_test_v2_san`, SHA256
  `385be27108036ad70b7ab313b89f0edb0747654d0b4e19af5194a0bd1224c61a`.

Runtime/mirror equality was checked for production and test sources. No old
installed binaries were replaced. No flight was started by this subtask.
