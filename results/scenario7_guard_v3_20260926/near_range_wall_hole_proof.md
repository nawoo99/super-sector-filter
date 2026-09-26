# Near-range wall hole: actual v2 archive proof

No ROS node, renderer or flight is started by this fixture. Production source
and configuration remain unchanged. This is a constructed dense-wall
counterexample using recorded held/contact poses, **not a replay of the
unrecorded run70005 clouds and not proof of that run's unique root cause**.

The exact test source, v2 config header and executable are preserved in
`offline_wall_hole/` beside this note. It links the real v2 ROG static archive
and uses the installed v2 headers first, preventing an ABI mismatch with later
runtime-header edits.

## Fixture and isolation

Wall points are float32(-4,3+.05*j,1.5+.05*k), j,k=0..30:961 points per frame,
repeated14 times at recorded held sensor
S=(-3.7268038947764675,3.5052099309384137,2.467517505190736).
Actual raw resolution.05, inflation resolution.1/step3, probabilities,
point_filt_num1 and occupancy-only update code are retained. Map allocation is
bounded to8x8x4m. Config::resetMapSize is not idempotent for virtual bounds, so
the fixture restores the already-loaded bounds after resizing; actual initialized
ground/ceiling are.25/3.15m, not a twice-shrunk range.

Before wall insertion, the real updateProbMap startup clear runs at mission
origin(0,0,1.5) using a distant dummy point. The wall is more than5m away;
startup clearing cannot remove its evidence. The two baseline counterfactuals
run in fresh processes because ProbMap initialization/startup have static guards.
They change only the fixture's ray_range minimum/squared minimum to.5 or.1.
This baseline also changes the startup-clear radius in the counterfactual,
but both occur away from the wall. A proposed production repair must keep
startup/free-ray semantics separate rather than adopting this broad fixture
parameter change blindly.

Queries:

- Q, first analytic contact:
  (-3.818210616665875,3.483847125503175,2.4686617574571397).
- I, first centre-inside sample:
  (-4.013501266431111,3.484294077239634,2.4389091380733467).

## Observed actual-library results

Both fresh-process executions exit0 and assert the expected discriminating
outcome. These values are from the actual library, not the preliminary Python
structural calculation.

| Actual query/result | Legacy min.5m | Counterfactual min.1m |
|---|---:|---:|
| Per-frame endpoints rejected by minimum range | 222 | 0 |
| Per-frame endpoints retained | 739 | 961 |
| Wall patch point(-4,3.5,2.45) raw/snapshot occupied | false/false | true/true |
| Q nearest occupied wall raw-centre distance, m | .402545837640240 | .157166649370966 |
| Q mutable/snapshot inflated occupied | false/false | true/true |
| Q physical body predicate occupied | false | true |
| I nearest occupied wall raw-centre distance, m | .371972847351751 | .0419784648418575 |
| I mutable/snapshot inflated occupied | false/false | true/true |
| I physical body predicate occupied | false | true |
| Q/I unknown-neighborhood query | true/true | false/false |

The physical predicate uses the actual current boxSearch with.225m search
extent and.2m centre-distance test. It agrees with an independent exhaustive
scan of occupied wall-cell centres. Raw mutable occupied wall cells agree
with real committed snapshot bits; mutable inflation agrees with committed
snapshot inflation. At.1, both Q and I body searches return36 candidates.
At.5, they return zero candidates within the search box.

The fixture does **not invoke the full planner validator**. It demonstrates
that actual map queries consumed by its hard/body and inflation branches can
both be clear despite closed-solid contact when near hits are excluded. With
unknown-as-occupied=false, the validator's intermediate inflation-false branch
also has no occupied evidence on which to reject. That is an observation-loss
counterexample, not an established snapshot-indexing defect. Fourteen repeated
Full-shaped wall frames cannot restore deterministically discarded endpoints.

## Reproduction and hashes

Compile the preserved test with C++17,-O2,-DORIGIN_AT_CORNER,-DUSE_ROS2,
ROOT_DIR pointing to the runtime rog_map directory, installed v2 rog_map
include directory first, then the v2 build flags.make include list, the archive
below and `-lyaml-cpp -lfmt -lpcl_common -lpcl_io`. Compilation was a single
g++ process after the diagnostic flight ended.

Execute the preserved binary with
`CONFIG --min-range 0.5`, then separately `CONFIG --min-range 0.1`.
CONFIG is
`/root/super_ws/scenario7_guard_v2_20260926/install/super_planner/share/super_planner/config/static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml`.

- Executable `offline_wall_hole/near_range_wall_hole_test`:
  `f71ac18a83d839d483a406c60dcebf066a256781f05860c8fcda4f0be746442c`.
- Source `offline_wall_hole/near_range_wall_hole_test_v2.cpp`:
  `d2d04736f611c6f5bd1f56a15f9f512bba1a21d4fd39f71b0408155cb68b924c`.
- Config header `offline_wall_hole/config_v2.hpp`:
  `1e69442c97f2d2309a2209abbe644a61878a1e7c6a81c5102bd07c05d935fcaa`.
- Archive `/root/super_ws/scenario7_guard_v2_20260926/install/rog_map/lib/librog_map.a`:
  `3fc3f5561d70668874b446c6a51e067311c38e17c9eb39e9fe4c5581d73b5860`.

The additive runtime test may subsequently be extended to exercise a separate
occupancy-only hit minimum. This preserved v2 source/binary remains the baseline;
never rebuild it against an ABI-incompatible new config header and old archive.

## Separated near-hit repair: fresh v3 normal regression

The extended additive test uses the fresh v3 archive and its matching installed
headers. New CLI is `CONFIG --occupancy-min-range legacy|0.5|0.1` and
`CONFIG --test-config`. The preserved v2 source/binary above is unchanged.

All four normal invocations pass. The new setting changes only occupancy-only
hit admission; `ray_range[0]` and its squared value stay.5/.25. Both sentinel
fallback and explicit.5 preserve the original hole. Explicit.1 admits the wall
patch and restores Q/I physical/inflated occupancy with the same distances in
the baseline table. Additional real-implementation assertions pass:

- Startup clearing still reaches a point.35m from the origin and reports.5m
  radius; configured physical body radius remains.2m.
- Two duplicate near returns at.25m retain two hits and enqueue **zero misses**.
- A far endpoint produces identical actual sparse hit/miss cache entries with
  the.5 and.1 occupancy minima, preserving observed-free ray geometry.
- Genuine raycasting=true still rejects a.25m endpoint under ray_range[0]=.5,
  despite the.1 occupancy-only override.
- Actual YAML loader accepts omitted(default.5),0,.1,.5 and rejects-1,.6,NaN,Inf.
  Temporary YAML fixtures are removed by the test after each parser case.

At the held pose S, repaired occupancy-only.1 retains `unknown_neighborhood=true`,
unlike the broad v2 ray_range=.1 counterfactual. This is consistent with the
intended separation: admitting near occupied endpoints does **not** manufacture
near-field free-ray evidence. Q/I are nevertheless both raw-body/inflated
occupied. No unchanged-policy or liveness-success claim is inferred from this.

Normal logs: `offline_wall_hole/v3/normal_legacy.log`, `normal_0.5.log`,
`normal_0.1.log`, `normal_config.log`.

- Extended test/mirror source SHA256:
  `8eef464f963e135a13f4016e5b82c64353b75789b3c4512c00e485a7e87ea9be`.
- Normal binary SHA256:
  `d8c60d7624039cf72e414625715eafc93729d006b2b5307f6c18f4251bdf0c43`.
- Fresh v3 archive SHA256:
  `2b87365711ea56702b936c122107c58fbae38462360c02148ee598c3458d809b`.
- Repaired prob_map.cpp SHA256:
  `497c4fa761d08c5db38bd6c8b4bc88da313572039acf4b16ea530afeef6b3b4a`.
- New Config header SHA256:
  `e819a7bd308a23da4e92622a19c7a85d5374471d0920ff8b7499e271ddf57c37`.

ASAN+UBSAN with leak detection now **passes all four invocations**: sentinel
legacy,.5,.1 and config validation. No sanitizer or runtime-error report appears
in the retained logs. The actual changed prob_map.cpp and the test/inline Config
parser are instrumented; supporting objects from the new archive remain
uninstrumented, so this is not a fully sanitized ROG build. Sanitizer binary
SHA256 is `1a33a75aa84f6f2e2bc8af7b789ef8639086982b2117ba111ccba97ece17c26f`.
Complete logs are `offline_wall_hole/v3/sanitized_legacy.log`,
`sanitized_0.5.log`, `sanitized_0.1.log`, `sanitized_config.log`.
Exact build/run recipes, all implementation/config hashes, and preliminary
attempt disclosures are in `offline_wall_hole/commands.md`.
