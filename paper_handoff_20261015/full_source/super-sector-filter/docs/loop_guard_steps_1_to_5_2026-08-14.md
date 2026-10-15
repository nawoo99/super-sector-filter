# Loop trajectory guard: steps 1–5 experiment (2026-08-14)

## Scope and checkpoints

- Pre-change archive: `/root/checkpoints/loop_safe_guard_pre_steps_20260814.tar.gz`
- SHA-256: `6c3465d84b58455b76c30a3ab8ffd0f485d4aa180a4c9e81b98a92ff2d3323ce`
- The working profile remains experimental and static-seed-map-specific.

## Step 1 — map scheduling and coherent reads

Implemented separate planner/map callback groups, coherent shared transactions around map-reading frontend phases, a writer-preference gate, explicit executor capacity, and cloud-driven map commits.

- `results/step1d_seed6_smoke.csv`: contact 0, minimum live-cloud distance 0.722 m, `MAP_STALE=0` in that run.
- Later full-loop runs still showed intermittent cloud/executor starvation. Expanding executor capacity reduced stale events from 37 to 3 in the final two pre-smokes, but did not eliminate them.

Conclusion: the original same-callback scheduling defect is fixed, but this is not a true immutable/double-buffered map and freshness is not robust enough for enforcement.

## Step 2 — safety geometry and Backup/stitch coverage

Attempts:

1. Uniform 0.5 m hard geometry: fail-closed A* timeout or CIRI infeasibility.
2. Uniform 0.4 m hard geometry: CIRI repeatedly failed at raw distances around 0.369–0.388 m despite inflated-map path feasibility.
3. Final layered design: A* and composite certificate use 0.3 m; CIRI generates body-feasible candidates at physical radius 0.2 m; preferred corridor margin is 0.3 m.

Every complete candidate is validated after Exp/Backup composition. This covers Exp, appended Backup, carry Backup, and stitches. Unsafe Backup/stitch samples were observed and rejected as `CLEARANCE_MARGIN`.

Conclusion: forcing the same numerical radius into voxel A* and raw-point CIRI destroys liveness because their representations disagree. The operational hard gate is the final composite certificate.

## Step 3 — certified braking only

Implemented duration search up to 3 s and publish only when both acceleration/jerk and trajectory-map validation pass. The old unsafe `executing shortest bounded stop` path was removed. If no certified brake exists, the FSM enters fail-closed state without publishing a brake polynomial.

- `results/step3_seed6_smoke.csv`: executed brake duration 0.571 s, max acceleration 19.172 m/s², max jerk 62.074 m/s³, `path_status=SAFE`, contact 0.

Conclusion: the implementation goal is achieved, but “no command” after brake rejection is not a complete physical fallback.

## Step 4 — certified guard-margin escape

The validator now distinguishes a conservative margin violation from physical-body collision. It permits only an initial margin-unsafe prefix that exits within 1.0 s, remains physically safe at 0.2 m, and never re-enters the guard.

- No seed6 run produced `escape=true`.
- Rejected trajectories entered the margin later, so the initial-escape rule correctly did not accept them.
- `results/step4c_seed6_smoke.csv`: 4/5 waypoints, 204.740 m path, contact 0, minimum live-cloud distance 0.392 m.

Conclusion: implemented but not positively exercised; do not claim empirical validation.

## Step 5 — smoke gate and 50-run decision

Required gate: seed6 5/5 waypoints, contact 0, and no stale-map enforcement failure.

- `results/step5_pre_seed6.csv`: 2/5, contact 0, 37 `MAP_STALE` statuses.
- `results/step5_pre2_seed6.csv`: 1/5, contact 0, 3 `MAP_STALE` statuses.

The one-run prerequisite failed, so the 5-run smoke and 50-run campaign were not started.

## Final assessment

The changes show contact-free execution and final composite rejection of unsafe Exp/Backup/stitch candidates. They do **not** show a useful loop planner: completion remains nondeterministic and freshness can still trigger stops. Keep enforcement experimental. The next architectural task should be a true immutable/double-buffered map snapshot (atomic pointer swap), followed by a recovery policy that always has a physically executable certified action.
