# Candidate 5 preflight: exact, bounded neighborhood memoization

Status: standalone optimized and ASan+UBSan corpora passed; runtime opt-in binding
implemented inside the C4 line-query branch. Root reported the three-package
workspace build passed; closed-loop tests remain. Enable with
`SUPER_SNAPSHOT_NEIGHBOR_CACHE=1` together
with `SUPER_SNAPSHOT_LINE_QUERY=1`; both default off. Startup marker reports
`[ROG_MAP_SNAPSHOT_NEIGHBOR_CACHE] enabled=... immutable=... line_query=... active=...`.

The candidate-4 per-line pin removes per-voxel atomic snapshot loads but still
repeats the same 257-neighbor sphere for each center voxel in many overlapping
backup rays. Candidate 5 memoizes the exact bool result of that sphere query.
This is not map downsampling, neighbor thinning, inflation approximation, or
unsafe replanning throttling.

## Bounded state

- 4096 direct-mapped entries, keyed by all three signed center coordinates plus
  a context epoch. Hash collisions recompute and replace; never approximate.
- Up to 512 full ordered integer neighbor offsets are retained for identity
  comparisons. Longer or empty neighbor lists bypass caching.
- Default helper measured 88,136 bytes per thread; compile-time test requires
  size below 96 KiB. Ten worker threads would total about 861 KiB of cache state.
- No strong snapshot/map/page ownership, global maps or growing containers.
- An unsigned epoch wrap clears all entry tags; a narrow epoch tests this path.

## Context identity, verified once per line

- Snapshot shared ownership/control-block identity, using weak_ptr owner_before
  comparisons: safe against reused raw addresses, without keeping old maps alive.
- Snapshot object pointer too, to distinguish different aliases of one owner.
- Snapshot version, map-instance identity, integer virtual ground/ceiling and
  safe-margin inputs read by the occupancy predicate.
- Full ordered neighbor-list CONTENT, not its address, size alone, or a hash.

The context is reused only while these identities match. The line operation
still pins a strong snapshot locally and retains C4's final current-publication
check before accepting a free line. Map publication during a cached ray cannot
bypass that check. Float/empty-neighbor occupancy does not use this cache.

## Implemented integration

Inside the C4 bool max-distance+neighbors immutable branch, a cached opt-in flag
selects one thread_local cache for nonempty neighbor lists. beginLine receives
the pinned snapshot and exact integer predicate identity. Its inner neighbor
scan is a pure callback used by cache.anyOccupied(center, callback). Point
conversions, raycaster, distance comparisons, float predicate, outside-map
semantics, and final snapshot pointer/version check are unchanged. Both Full
and Adaptive receive the same opt-in policy. All other overloads are unchanged.

The additional generic traversal is in the new helper file; C4's existing
snapshot_line_query.hpp remains unchanged. Thread-local use requires no
cross-thread locks/atomics, and this call path must remain non-reentrant.

## Optimized corpus evidence

The corpus passed exact bool hits/misses, hash collision replacement, all
context identity fields, mutated same-address neighbor lists, same-address
snapshot/control-block ABA, shared-owner aliases, weak snapshot lifetime,
epoch wrap, bounded-list bypass, actual RayCaster comparison against the C4
helper, and cached-hit publication-change rejection. The final corpus lives at
`rog_map/test/snapshot_neighborhood_cache_corpus.cpp`. Independent read-only
review found a generic bool-epoch issue (now statically excluded) and suggested
additional true-hit, full-list mutation, and bypass-return cases, all passing.

7,456 ray comparisons passed. Across the corpus, occupancy predicate evaluations
fell from 45,534,573 to 8,044,082 (including cached-side publication-test extras).

Synthetic 1,000 repeated six-meter rays with the production 257-neighbor sphere:

| Metric | C4 pinned per-line query | C5 exact neighborhood cache |
|---|---:|---:|
| Occupancy predicate evaluations | 30,840,000 | 544,326 |
| Thread CPU seconds | 0.037258978 | 0.003200773 |

The remaining repeated evaluations include direct-mapped hash collisions, which
correctly recompute. Synthetic speedup is 11.64x. This simplified snapshot fixture
and repeated-ray workload do not establish real-flight savings or the user's
40% end-to-end goal; flight results must be measured separately.
