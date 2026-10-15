# SUPER trajectory guard audit — 2026-08-13

## Scope

This audit covers the dirty ROS2 working tree at
`/root/super_ws/src/SUPER` (`master`, HEAD `2ad3419`) and answers whether the
existing trajectory guard observes or enforces safety for exploratory (Exp),
Backup, and trajectory-stitching segments. It does not claim equivalence with
upstream SUPER or prove collision freedom against simulator geometry.

## Coverage result

`CmdTraj::buildCandidate(exp, backup)` constructs one positional trajectory by
concatenating the Exp prefix up to `backup_start_tt` and the generated Backup
trajectory. A carried-over Backup interval from the previous command is already
part of the new Exp trajectory and is retained as metadata. All planner commit
sites call `commitTrajectoryCandidate()`, which validates the combined
positional trajectory from the current trajectory time to its end.

Consequently, candidate validation covers:

- the executable remainder of Exp;
- an appended Backup trajectory;
- a carried-over Backup interval;
- the polynomial concatenation boundary between Exp and appended Backup;
- line segments between successive validation samples.

The prior logs did not identify which segment contained the first unsafe point.
The new shadow/enforce log adds one of `EXP`, `APPENDED_BACKUP`, `CARRY_BACKUP`,
`EXP_TO_BACKUP_STITCH`, or `CARRY_BACKUP_STITCH`.

## Enforcement behavior already present

With `fsm/trajectory_guard/enable: true`, the ROS2 implementation:

1. validates a candidate against the inflated ROG map before commit;
2. rejects an unsafe candidate;
3. certificates the committed trajectory against a map version;
4. suppresses normal command publication if the certificate or map version is
   invalid;
5. periodically revalidates when the map changes;
6. generates and publishes a bounded emergency-braking polynomial when
   certification is lost.

This is substantially broader than the Exp-only clearance penalty.

## Important limitations

1. **Map safety is not physical-ground-truth safety.** Validation uses
   `isOccupiedInflate()` and `isLineFree(..., use_inf_map=true,
   use_unk_as_occ=false)`. Missing, delayed, or filtered obstacle points are not
   detected, and UNKNOWN is treated as traversable.
2. **No signed clearance is computed.** The result is a binary inflated-voxel
   classification. It cannot distinguish a millimetre boundary touch from a
   deep physical penetration or calibrate `body_radius` versus
   `planning_radius`.
3. **Emergency braking is not guaranteed safe.** If the generated braking path
   fails validation, the implementation logs `TRAJ_GUARD_BRAKE_PATH_UNSAFE` but
   still executes the shortest bounded stop. At high speed this may be the only
   available action, but it is not a formal invariant.
4. **The robust runtime certificate path is ROS2-specific.** Planner-side
   pre-commit validation is shared, but the audited publication suppression,
   map freshness checks, revalidation, and emergency brake are implemented in
   `fsm_ros2.hpp`.
5. **Candidate validation does not itself reject stale maps by age.** It checks
   commit version/update races. ROS2 FSM freshness logic supplies the map-age
   gate when enforcement is enabled.
6. **The validator cannot attribute a physical contact after execution.** The
   new segment label classifies the validator's predicted first unsafe point;
   the native monitor must still record command generation/flag and static-PCD
   signed clearance to correlate a later contact.
7. **A candidate that is already unsafe at `checked_from_tt` has no safe
   prefix.** Enforcement rejects it, but safe continuation depends on the
   previously committed certificate or on the emergency brake.

## Shadow mode added by this audit

`fsm/trajectory_guard/shadow: true` with `enable: false` now runs the same
candidate validator but never rejects, suppresses, brakes, or changes command
publication. The candidate is committed before validation and copied into a
bounded, latest-only worker queue, so the scan cannot delay that commit. It
emits structured markers:

- `TRAJ_GUARD_SHADOW_SAFE`
- `TRAJ_GUARD_SHADOW_UNSAFE`

The unsafe marker includes planner phase, Exp/Backup/stitch segment, map
version, checked time range, first unsafe trajectory time/position, sample
count, validation runtime (`validation_ms`), and
`action=async_after_commit`. The runtime must be checked because shadow work
can still consume CPU and hold the map read transaction even though it does not
change the observed commit.

The campaign summary separates geometric failures (`OCCUPIED`, `OUT_OF_MAP`)
from map races (`MAP_UPDATING`, `VERSION_CHANGED`) and other indeterminate
states. Exp/Backup/stitch counts are computed only for geometric failures.

The ready-to-run profile is:

`super_planner/config/static_seedmaps_shadow_v10.yaml`

Shadow and enforcement can both be present in YAML, but enforcement wins. The
default remains both disabled, so existing configs and flight behavior are
unchanged.

## Next evidence gate

Run a small shadow campaign before enabling enforcement. For each native
contact, compare:

- whether shadow predicted an unsafe candidate before contact;
- predicted segment versus command `trajectory_flag`;
- ROG-map unsafe position versus static-PCD signed clearance;
- prediction-to-contact lead time;
- false positives that would have caused rejection or braking.

Only after this correlation should the guard be enforced at v=10. If physical
contacts are not predicted, the next fix belongs in mapping/clearance-aware A*
or a physical-distance validator, not in guard thresholds.

## First shadow smoke result

Seed2, v=10, full, one loop completed in 27.52 s with no live-cloud or static-PCD
contact. Shadow committed every candidate and reported 310 safe and 77 unsafe
validations. Of the 77 unsafe results, 54 were `VERSION_CHANGED`, 13 were
`MAP_UPDATING`, and 10 were `OCCUPIED`; the geometric results comprised one Exp
and nine appended-Backup predictions. Mean/max validation time was
23.58/32.25 ms over 387 candidates and FSM CPU was 104.2%. This is too costly
and race-prone for a large campaign without an A/B overhead check or a stable
map snapshot/read transaction. The smoke establishes observability, not safety
or causal correlation.

## Snapshot, A/B, and contact-correlation follow-up

A shared ROG-map read transaction now covers each complete validation pass;
map commits take the matching exclusive transaction. Repeating seed2 removed
all `MAP_UPDATING`/`VERSION_CHANGED` results (67 to 0). A 0.25 s synchronous
rate limit reduced checks from 332 to 93, but missed two of three independently
observed seed4 contacts. Dense validation caught the observed contact, so the
rate limit is suitable only for low-cost characterization, not enforcement.

Shadow validation was subsequently moved to a bounded latest-only worker. The
planner commit returns before the scan starts, while the worker validates a
copy of the committed composite trajectory. A dense async seed4 smoke checked
365 candidates with no map races, but used 128.4% aggregate FSM-process CPU.
This removes commit-path latency but does not remove validation work or the
map-writer delay caused by the read transaction.

Wall-clock contact correlation is implemented in
`scripts/native_campaign/correlate_shadow_contacts.py`. In a rate-limited
seed4 run, one of three contacts matched an appended-Backup warning 0.353 s
earlier, with 6.7 ms prediction-time error. In a separate dense run the only
contact had a preceding appended-Backup warning. These are diagnostic examples,
not recall estimates.

The fail-closed promotion gate is
`scripts/native_campaign/evaluate_guard_readiness.py`. Current evidence returns
`keep_shadow_only`: map-race and small rate-limited A/B overhead checks pass,
but dense evidence has only one contact and no ten-pair dense A/B. Enforcement
and the 50-run comparison must remain disabled until those requirements pass.

## Dense map-commit revalidation result

The earlier shadow path validated only when a new trajectory was committed.
It therefore missed hazards that appeared in later ROG-map commits while the
same trajectory was still executing. Shadow mode now enqueues the committed
trajectory once per new map version (`phase=MAP_COMMIT`) using the same bounded
latest-only worker. This changed the contact-heavy seed7 smoke from 6/7 prior
warnings to 5/5 after adding a 0.2 m guard-only clearance margin.

The dominant validation overhead was also isolated. `ROGMap::getMapConfig()`
returned the full configuration by value, copying large neighbor tables on
every scan. Returning a const reference reduced median validation time from
about 33.26 ms to 0.0615 ms before the clearance-neighbor check. With the 0.2 m
guard margin and map-commit revalidation, mean validation time in the final
dense campaign was 0.447 ms.

Final shadow evidence (`seed4..8`, two rotated-order pairs each) was:

- control completion 10/10, shadow completion 10/10;
- paired FSM CPU delta median +3.53 percentage points;
- paired mission-time delta median +0.73 s;
- shadow contact prediction 17/17 in the paired campaign and 20/20 after two
  same-configuration contact-heavy extensions;
- map snapshot races 0;
- safe validations 2,571 / 5,584 = 46.0% across the gate inputs (the 10-pair
  campaign itself had 2,148 / 4,671).

Artifacts:

- `results/native_shadow_map_recheck_margin02_ab_n10.csv`
- `results/native_shadow_map_recheck_margin02_ab_n10_summary.json`
- `results/trajectory_guard_readiness_map_recheck_margin02_n20_20260813.json`

## Enforcement smoke result: do not promote

The first version of the readiness gate passed recall, map-race, overhead, and
completion checks, so enforcement smoke was attempted. It was not promoted to
the planned 50-run campaign. All four seed6 enforcement variants produced zero
monitor contacts but failed the mission at 0/5 waypoints:

| Profile | Path before stop | Min center-to-cloud distance | Direct failure |
|---|---:|---:|---|
| inflated map 0.3 m + guard 0.2 m | 6.429 m | 0.731 m | repeated candidate rejection after stop |
| globally inflated map 0.5 m | 18.997 m | 0.260 m | `MAP_STALE`, unsafe/non-dynamic brake |
| frontend extra-clearance 0.2 m | 16.083 m | 0.594 m | `MAP_STALE`, then rejection at stop |
| hard radius 0.4 m + extra 0.1 m | 2.892 m | 0.556 m | `MAP_STALE`, then rejection at stop |

The smoke exposed three structural defects that threshold tuning cannot solve:

1. map commits and planning intentionally share a mutually-exclusive callback
   group; expensive planning can make the runtime certificate stale;
2. the emergency brake can report `dynamics_ok=false` or an unsafe brake path
   and still execute the shortest stop;
3. after stopping near the guard boundary, `PlanFromRest` can repeatedly create
   a trajectory whose first Exp samples or appended Backup re-enter the guard
   envelope, with no certified escape behavior.

The readiness gate now also requires at least 50% of dense shadow validations
to be safe. The observed 46.0% fails this operational anti-stall floor, so the
current machine-readable decision is again `keep_shadow_only`. The enforcement
profile is retained only as `static_seedmaps_guard_v10.yaml` with an explicit
experimental warning. The next implementation must use a mapping snapshot or
otherwise decouple map freshness from planning, make braking dynamically and
geometrically fail-safe, and add a certified escape/recovery planner. Do not run
the 50-run enforcement campaign before a smoke completes all five waypoints.
