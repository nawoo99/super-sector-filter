# Proposed actual-query shadow comparison (not implemented)

Only implement after root approval and after the current build/flight ends.
This is a correctness diagnostic, not a CPU candidate measurement.

1. Keep `ROGMap::boxSearch`'s existing immutable snapshot capture exactly where
   it is. Call it S1. Keep the existing `boundBoxByLocalMap` invocation, including
   its independent internal snapshot load S2. Keep map-empty handling, virtual
   clipping, grid-index floor division, and strict raw index bounds unchanged.
2. Optimize only immutable `gt == OCCUPIED` queries. Other types and mutable-map
   operation retain the existing implementation.
3. After the existing bounds have been computed once, run both algorithms over
   those exact same index bounds and S1's `probability.occupied_pages`. The old
   loop must be an internal loop taking S1/bounds, not a recursive call through
   public `boxSearch`, because that would capture another occupancy snapshot.
4. Gate dual execution with cached opt-in `SUPER_BOX_SCAN_COMPARE=1`. Compare
   every occupied query, including raw-body guard queries and CIRI corridor
   queries, not a sampled subset. Compare output length, index order, and each
   resulting x/y/z double bit representation. Do not sort or use a tolerance.
5. Successful comparisons may use the fast vector. On mismatch, emit an
   unambiguous failure diagnostic containing S1 version, input/clipped bounds,
   query counts and first differing point; use the baseline vector as the safe
   output. Count any mismatch as candidate rejection. This avoids continuing
   with an unverified fast result or abruptly terminating a moving planner.
6. Record compared-query and mismatch totals, and mark the entire diagnostic
   flight `comparison_overhead=true` / `cpu_candidate=false`. Preserve all
   existing guard and monitor telemetry. Logging should be bounded except for
   failures; query comparison itself must be exhaustive.
7. Require zero mismatches in direct flights for both Full and Adaptive with
   the actual CIRI queries and existing guard checks exercised. Separately run
   a matched CPU flight with comparison disabled and the same fast path enabled
   in both modes. Do not cite diagnostic-flight CPU as fast-path performance.

This design intentionally preserves the current S1/S2 load semantics rather
than changing them. In immutable fixed-map mode geometry is expected to remain
fixed, but the comparison need not assume that: both algorithms receive the
same once-computed bounds and the same S1 occupancy, even if publication occurs
between S1 and S2. It validates the traversal change only; it does not establish
or alter operation-wide map transaction semantics.
