# Gap-free diameter1m additional maps: G1–G5

Maps created; **zero flight tests**. All410 cylinders/map are static, diameter1m,
height3m, in64×64m field. No pair overlap or mandatory1m surface gap.
Offline body radius0.2m plus at least0.35m surface margin connects all loop24 legs.
Offline witnesses are never planner inputs and do not certify dynamic flight.

See [configuration, statistics and limitations](../../docs/gapfree_d1_maps_20260918.md).

- `manifest.json`: geometry, all nearest gaps/quantiles/histograms/density, offline
  routes, accepted/rejected geometric proposals and all source/mirror/install hashes.
- `summary.csv`: per-map scalar summary.
- `gapfree_d1_mNN_cylinders.csv`: exact analytic cylinders for contact auditing.
- `gapfree_d1_mNN_nearest_gaps.csv`: per-cylinder nearest surface gap.
- `gapfree_d1_mNN_routes.json`: offline continuous segment witnesses only.
- `map_overview.png`, `nearest_gap_cdf.png`: arrangement and gap distribution.

Future comparison:5maps ×3modes ×5runs=75; not executed in this request.
