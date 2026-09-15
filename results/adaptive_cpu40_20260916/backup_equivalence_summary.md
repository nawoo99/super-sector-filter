# Backup diagnostic replay regression (2026-09-16)

## Conclusion and important limitation

Under identical deterministic box geometry, the existing BackupTrajOpt binary
produced identical operational outputs and initialization records with and
without the discarded replay. Both the replay comparison and the no-replay /
no-replay control passed 1,614 scalar comparisons with maximum absolute error
zero (unchanged tolerance 1e-10 relative), including initialized failure ->
success and NaN early-return -> success histories.

This is **optimizer state-isolation evidence, NOT exact production-trajectory
equivalence**. Production SDLP uses a process-global random permutation stream;
removing replay advances that stream differently. Native rectangular fixtures
did exhibit later operational trajectory differences. All failures remain below.
Runtime optimizer/planner sources were not changed by this test work, and the
test-only geometry wrapper is not linked into any production executable.

## Final passing controls

Config: `super_planner/config/static_seedmaps_guard_viability_tight_v7.yaml`,
backup optimizer production bound 2,048 iterations. Four suites: uniform and
nonuniform timing, each with two and three pieces. Every suite exercised five
successful operational solves, two intentional failures, and two subsequent
successful recoveries. Fixtures use straight, accelerating diagonal, and curved
reverse polynomial motion; an incompatible bounded corridor; a NaN corridor;
and successful calls after each failure. Diagnostic replay is never called on
the NaN early-return fixture. The initialized incompatible-corridor failure does
exercise replay using checked nonempty, finite, positive initialization data.

The test-only linker wrapper supplies the analytic center of a finite
axis-aligned six-face box, then invokes production vertex enumeration's
explicit-interior overload. This bypasses SDLP random center selection while
leaving BackupTrajOpt, MINCO, L-BFGS, penalties and trajectory conversion intact.
Only equal-axis cube fixtures are used for the final passing controls.

| Final test | Operational comparison | Geometry wrapper calls | Max abs error | Result |
|---|---|---:|---:|---|
| `backup_equivalence_deterministic_cube_replay.log` | A operational+replay / B operational-only | 72 | 0 | PASS |
| `backup_equivalence_deterministic_cube_no_replay.log` | A operational-only / B operational-only | 48 | 0 | PASS |

Each log includes all four suites and 1,614 scalar checks. Compared fields:
operational bool, out_ts, heuristic duration, trajectory piece counts,
durations, coefficient matrices, and captured pre-replay initial start time,
durations and points. These finite fixtures are not an exhaustive proof for
every trajectory/configuration, physical stopping, or closed-loop safety.

## Failed and exploratory trials (not counted as passes)

| Artifact | Outcome |
|---|---|
| `backup_equivalence_rectangular_replay_failure.log` | Native SDLP; 512-iteration test cap. Later successful trajectory duration differs after NaN fixture. |
| `backup_equivalence_rectangular_no_replay_control.log` | Native SDLP; 512 cap. No numerical mismatch reached; nonuniform three-piece suite lacks enough successful fixtures. |
| `backup_equivalence_unique_512.log` | Native SDLP with cubes; uniform three-piece suite lacks enough successes under 512 cap. |
| `backup_equivalence_unique_2048.log` | Native SDLP, cubes, production 2048; replay comparison passes, max abs error 1.33227e-15. This alone does not isolate random geometry. |
| `backup_equivalence_rectangular_2048.log` | Native SDLP, production 2048; rectangular operational duration mismatch remains. |
| `backup_equivalence_rectangular_no_replay_2048.log` | Native SDLP control; insufficient successful fixtures in nonuniform three-piece suite. |
| `backup_equivalence_unique_no_replay_2048.log` | Native SDLP cube control; two failed solves differ in discarded out_ts by 1.7590515e-6. |
| `backup_equivalence_deterministic_replay.log` | Analytic-center rectangular boxes; comparisons agree but nonuniform three-piece fixtures lack enough successes. |
| `backup_equivalence_deterministic_no_replay.log` | Same rectangular geometry control; comparisons agree but same successful-fixture coverage shortfall. |

Native rectangular successful-solve mismatch:

```
uniform/pieces2/after_nan_corridor durations:
first=0.21336158536280314
second=0.21358483229382494
absolute_error=0.00022324693102179771 seconds per piece
```

The NaN fixture position is not evidence that NaN itself caused this difference.
`sdlp.cpp::rand_permutation` has a static `std::mt19937_64`, consumed by
`processCorridor -> enumerateVs -> findInterior -> linprog`. A nonunique
Chebyshev center can yield a different vertex parameterization of the same
polytope. Replay adds these geometry calls. No-replay-only controls also show
that strict comparison across shared random-stream positions is not generally
a valid test of optimizer member-state equality. The deterministic controls
were added for that reason; numerical tolerance was never relaxed.

## Reproduction and resources

Test sources (runtime tree; new test files only):

- `super_planner/test/backup_replay_equivalence_test.cpp`
- `super_planner/test/backup_replay_geometry_shim.cpp`

Compile commands are in `backup_equivalence_compile.sh`; its deterministic
invocation's expanded compiler command is retained in
`backup_equivalence_deterministic_compile.log`.

```
bash results/adaptive_cpu40_20260916/backup_equivalence_compile.sh deterministic
results/adaptive_cpu40_20260916/backup_equivalence_deterministic_test \
  /root/super_ws/src/SUPER/super_planner/config/static_seedmaps_guard_viability_tight_v7.yaml \
  --unique-center-cubes
results/adaptive_cpu40_20260916/backup_equivalence_deterministic_test \
  /root/super_ws/src/SUPER/super_planner/config/static_seedmaps_guard_viability_tight_v7.yaml \
  --control-no-replay --unique-center-cubes
```

Compilation is sequential at `-O0 -g0 -DNDEBUG`, linked to the already-built
`libsuper.a`; it does not rebuild the optimizer or require ROS/GPU execution.
First successful one-TU compile: 3.393 s wall, 3.095 s user CPU, 0.295 s system
CPU, peak RSS 428,680 KiB. The initial attempt to use `/usr/bin/time` failed
immediately (tool absent); no compiler ran on that attempt. Python subprocess /
resource measurement was used instead. Native cube 2048 test measurement:
1.155 s wall, 1.141 s user CPU, 0.012 s system CPU, peak RSS 9,440 KiB, exit 0.
Other standalone executions also finished within a few seconds; no flights or
production launch processes were started by this test work.
