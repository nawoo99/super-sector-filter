# Candidate 4: per-line immutable snapshot query preflight

Status: standalone helper/corpus verified; runtime binding implemented in
`rog_map/src/rog_map/rog_map.cpp`, awaiting workspace build and closed-loop tests.
The binding is opt-in with `SUPER_SNAPSHOT_LINE_QUERY=1` (default off), only in
the immutable-map bool max-distance + neighbor overload. All other overloads
and the default/mutable legacy loop are unchanged. Startup reports
`[ROG_MAP_SNAPSHOT_LINE_QUERY] enabled=... immutable=... active=...`.

## Motivation

The candidate-2 thread CPU profile attributed about 0.566 CPU cores in both
Full and Adaptive to backup trajectory generation outside its optimizer. The
backup seed-line check calls the bool `isLineFree(start, end, max_dis, neighbors)`
overload. With 0.05 m raw resolution and 0.2 m robot radius, the radius-four
integer sphere contains 257 neighbors. The old immutable-map path atomically
loads/refcounts a published snapshot separately for every queried neighbor.

The proposed helper preserves the existing ray traversal, maximum-distance
comparison, neighbor order, and caller-defined occupancy predicates while
allowing one snapshot to be pinned for the operation. An otherwise-free line
must pass a final publication-identity/version check; a publication change
rejects the line conservatively. This is only a check at return, not a guarantee
against changes after return. No snapshot persists into a later operation.

## Files

- Runtime helper: `rog_map/include/rog_map/snapshot_line_query.hpp`
- Standalone corpus: `rog_map/test/snapshot_line_query_corpus.cpp`
- Existing production RayCaster is compiled unchanged into the test. The macro
  `SUPER_UTILS_HEADER_TYPE_UTILS_HPP` only skips its unused common utility header
  to avoid linking ROS/PCL into the standalone test.

## Verified semantics

- 16,832 quiescent line comparisons, including 43,197,133 ordered occupancy
  predicates, match the independent baseline loop in bool result and query trace.
- Four resolutions, four occupancy densities, negative/noncanonical ring-map
  origin, forward/reverse/axis/diagonal/random/same-cell rays.
- Empty, singleton, production 257-neighbor sphere and arbitrary ordered lists.
- Positive, zero and negative maximum distance; exact/adjacent distance limits.
- Physical virtual bounds and integer virtual bounds plus safety margin remain
  distinct. Outside-map occupancy is false before virtual-height checks.
- Float-position lookup uses division; neighbor-index conversion uses
  multiplication by the inverse resolution. The corpus explicitly found and
  preserved 198 floating-point boundary distinctions.
- Word/page-edge occupied bits and negative ring wrapping are exercised.
- Ten deterministic publication-change rejections, including a real concurrent
  writer thread; an otherwise-free pinned query rejects at its final check.
- The existing zero-length/same-cell behavior is retained (the caller still
  ignores `RayCaster::setInput`'s return value).

Both the optimized corpus and ASan+UBSan passed after tightening the
word/page-edge fixture to disable virtual obstacles. The final sanitizer rerun
completed after the runtime binding was implemented and before the root
agent's C4 flight validation.

## Synthetic CPU benchmark (not a flight result)

300 six-meter rays, 0.05 m resolution, 257 neighbors, no occupied voxels:

| Metric | Per-point published snapshot | Per-line pinned snapshot |
|---|---:|---:|
| Ordered occupancy predicates | 9,252,000 | 9,252,000 |
| Atomic snapshot loads | 9,252,000 | 600 |
| Thread CPU seconds, final run | 0.330984859 | 0.067010836 |

Synthetic speedup: 4.94x. An earlier run was 4.24x. This includes the fixture's
ordered-trace hashing and uses `CLOCK_THREAD_CPUTIME_ID`; it does not establish
end-to-end planner savings, real-world safety, or equivalence under concurrent
map publication. The latter intentionally becomes more conservative.

## Integration constraints

- Opt-in, default legacy behavior; identical common optimization in Full and
  Adaptive. Immutable snapshots only; mutable path unchanged.
- Initially ONLY the bool max-distance + neighbor overload. Do not alter the
  free-local-goal or inflated/unknown overloads.
- Bind actual private snapshot predicates exactly. In the float callback retain
  `snapshotPosToGlobalIndex` division; in neighbor conversion retain
  `posToGlobalIndex` reciprocal multiplication.
- Final true requires that the pinned snapshot publication is still current.
- The runtime binding uses actual `snapshotInside`, `snapshotHash`,
  `snapshotBit`, `snapshotPosToGlobalIndex`, and `posToGlobalIndex` methods.
  It conservatively rejects a null publication or changed final publication.
  There is no per-query instrumentation or logging. The corpus remains a
  generic traversal + synthetic snapshot fixture, not a ROS flight; direct
  runtime integration awaits the root agent's workspace build/flight tests.
- Nonfinite coordinates/integer overflow are outside this optimization's scope;
  tests use finite representable coordinates and do not add new semantics.

See `commands.sh` and `observed_output.txt` for commands/results.
