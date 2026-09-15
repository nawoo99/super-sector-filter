# Candidate 3 preflight: synthetic occupied-box traversal

Status: standalone helper and tests only. No existing ROGMap runtime source,
header, profiling-stage list, or production configuration was changed for this
preflight. Integration and flight validation remain pending root approval.

Results below were captured from successful tool executions and persisted here
on 2026-09-15 19:13:51 UTC (2026-09-16 in Asia/Seoul). They were not obtained from
an integrated planner or a matched Full/Adaptive flight.

## Validation

- Ordered-output differential corpus: 19,191 queries passed.
- AddressSanitizer plus UndefinedBehaviorSanitizer: the same 19,191 queries
  passed, exit code 0, no sanitizer diagnostics.
- Corpus includes all-empty, all-occupied, sparse and dense bitmaps; negative
  and noncanonical origins; fractional physical boxes; invalid and clipped
  bounds; virtual-height clipping; 64-bit word and 4096-word page boundaries;
  and repeated ring wraps in direct iterator tests.
- The oracle reproduces the previous per-voxel signed-modulo hash independently
  of the new traversal. It compares occupied point counts, exact order, and each
  coordinate's double representation.

Important limitation: baseline and fast query wrappers share a transcribed
physical-box clipping/rounding routine. This corpus does not exercise real
ROGMap objects, concurrent publication, `boundBoxByLocalMap`'s second snapshot
load, CIRI, or ROS. It establishes ordered traversal equivalence after the same
bounds have been calculated. See `flight_comparison_plan.md` for the proposed
same-snapshot check on actual runtime queries.

## Synthetic whole-query CPU benchmark

These are synthetic microbenchmark results, not planner CPU or experiment CPU
reductions. Timing uses CLOCK_THREAD_CPUTIME_ID and includes clipping, floor
division, scanning, point conversion, fresh output-vector allocation/growth, and
destruction. Console output is outside the timed interval. Both paths use the
same immutable paged bitmap and query boxes.

Geometry: 0.05 m raw cells, 0.8 m corridor padding, an additional 1 m extent along
one seed axis, 64 boxes, 8 repetitions per timing round, 5 alternating-order
rounds, reported median per implementation. Bitmap dimensions are 401x401x121;
the production profile's larger world-map dimensions are not reproduced.

| Synthetic occupancy | Baseline us/query | Fast us/query | Speedup |
| --- | ---: | ---: | ---: |
| 0% | 431.378 | 9.647 | 44.715x |
| 0.098% | 441.097 | 12.482 | 35.338x |
| 0.781% | 427.036 | 21.993 | 19.417x |
| 6.250% | 554.798 | 57.581 | 9.635x |
| 50% | 1254.097 | 133.459 | 9.397x |
| 100% | 622.494 | 270.250 | 2.303x |

## Reproduction and artifacts

`commands.sh` records the successful compile/run commands. The initial optimized
compile emitted a harmless multiline-comment warning; the source comment was
then corrected. Sanitizer compilation of the corrected source was clean.
`benchmark.stdout.log` and `sanitizer.stdout.log` preserve observed stdout;
`metadata.json` records the source hashes, toolchain, status, and limitations.

New source files are under `/root/super_ws/src/SUPER`:

- `rog_map/include/rog_map/occupied_box_scan.hpp`
- `rog_map/test/occupied_box_scan_corpus.cpp`
