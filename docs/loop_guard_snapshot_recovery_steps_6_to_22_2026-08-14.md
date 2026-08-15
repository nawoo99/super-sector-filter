# Loop guard continuation: snapshot and recovery steps 6–22 (2026-08-14)

## Status

The guarded planner is still **experimental and not flight-ready**. The immutable
snapshot removed the long map read/write lock, and the adaptive corridor retry
occasionally completed the loop, but the required gate was not met:

- seed6 five-run smoke (`step17`): 2/5 completed, 1/5 had contact.
- The 50-run campaign was therefore not started.
- The final preserved profile uses `max_map_age_s=0.75`; the unsafe 1.25 s
  setting is not retained.

## Step 6 — immutable planner map snapshot

Implemented a fixed-map-only immutable snapshot in ROG-Map. It is enabled only
when map sliding, raycasting, and unknown inflation are disabled. Raw and
inflated occupancy are published through an atomic shared snapshot; changed
32 KiB bit pages are copied on write instead of copying the full ~34 MiB map.
Legacy configurations retain the shared-lock path.

Map health now separates:

- accepted scan time,
- processed scan receive/finish time,
- actual occupancy-map version.

No-op scans refresh processed-scan health without falsely incrementing the map
version. Planner validation ignores `update_in_progress` only when the immutable
snapshot is active and still checks map version before/after validation.

`step6_immutable_snapshot_seed6.csv` is **not a guard result**: it was
accidentally launched in mode `full`, so guard enforcement was off. Preserve it
only as an invalid experiment record.

## Steps 7–11 — corridor representation experiments

Inflated obstacle points in CIRI removed some raw/inflated representation
mismatch, but produced poor liveness. The best completed variants were:

| Step | Configuration | Waypoints | Contact | Minimum live-cloud distance |
|---|---|---:|---:|---:|
| 8d | inflated CIRI + aligned seed LOS | 1/5 | 0 | 0.417 m |
| 10 | inflated CIRI, map age 1.25 s | 1/5 | 0 | 0.391 m |
| 11 | raw CIRI, immutable snapshot, age 1.25 s | 2/5 | 0 | 0.383 m |

The global inflated-CIRI approach was rejected. Raw obstacle points with a
physical 0.2 m CIRI radius remain the normal candidate generator, while the
0.3 m inflated map remains the independent final certificate.

## Steps 12–16 — recovery experiments

- A general 0.2 s delayed-entry clearance escape (`step12`) did not activate
  and was reverted.
- Inflated seed-line visibility with raw CIRI (`step13`) regressed to 0/5.
- The point-seed divide-by-zero in `distancePointToSegment()` was fixed. This
  prevents `a == b` from producing NaN, but `step14` confirmed it was not the
  loop-liveness solution (0/5).
- An adaptive retry was added: after an EXP `CLEARANCE_MARGIN` rejection, the
  next planning attempt uses inflated obstacle points with a 0.005 m numerical
  CIRI radius. Normal candidates still use raw CIRI.
- `step16` completed 5/5 with contact 0 in 82.73 s and minimum distance 0.341 m.
  `escape=true` occurred zero times, so the configured entry grace did not cause
  that success.

## Step 17 — required five-run smoke

Results: `results/step17_adaptive_guard_seed6_n5.csv`

| Run | Waypoints | Completed | Contacts | Minimum distance |
|---:|---:|---:|---:|---:|
| 1 | 2/5 | no | 0 | 0.387 m |
| 2 | 5/5 | yes | **1** | **0.008 m** |
| 3 | 0/5 | no | 0 | 0.377 m |
| 4 | 0/5 | no | 0 | 0.418 m |
| 5 | 5/5 | yes | 0 | 0.360 m |

The contact was not an escape event (`escape=true` count was zero). At elapsed
3.04 s the vehicle center was 0.1928 m from the live cloud. The guard detected
`MAP_STALE` at map age 1.255 s and began a certified brake about 80 ms before
the contact, too late to avoid it. Thus 1.25 s is demonstrably unsafe at this
campaign speed and sensor realization.

## Steps 18–22 — safety restoration and rejected follow-ups

- `step18`, age restored to 0.75 s: 3/5, contact 0, minimum 0.393 m. Frequent
  stale brakes prevented completion.
- `step19`, planner subscribed directly to `/cloud_registered`: 0/5, contact 0.
- `step20`, the unused Python full-mode passthrough was also disabled: 0/5,
  contact 0. This reduced duplicate CPU substantially but did not fix recovery.
- `step21`, optimizer constraint samples doubled (EXP 30, Backup 24): 0/5,
  contact 0. Rejections shifted toward Backup/stitch. The sample counts were
  restored to 15/12.
- `step22`, fallback from unsafe composite trajectory to guard-checked EXP-only:
  0/5, contact 0. At the observed stop, EXP itself was unsafe, so the fallback
  was removed.

## Preserved configuration

`static_seedmaps_guard_v10.yaml` now preserves:

- immutable snapshot support;
- processed-scan freshness and `max_map_age_s: 0.75`;
- raw CIRI (`corridor_min_margin: 0.2`, preferred 0.3);
- optional adaptive inflated-corridor retry enabled;
- entry grace disabled (`0.0`);
- raw simulator cloud subscription (`/cloud_registered`);
- original optimizer integration resolutions (EXP 15, Backup 12).

The campaign skips the no-op Python filter for `full_guard_v10`, because the
planner now subscribes to the raw full cloud directly.

## Engineering conclusion and next gate

The remaining problem is not solved by more clearance tuning. With the current
renderer and campaign load, direct-map performance logs contain roughly
151–155 processed rows per 85 s run (~1.8 Hz), despite `sensing_rate: 10` in the
simulator YAML. At 10 m/s, a 1.25 s freshness allowance consumes essentially
the entire 15 m sensing horizon after braking distance; the observed contact is
consistent with that budget. A 0.75 s allowance is safer but repeatedly stops
the vehicle because the realized scan cadence does not meet it.

Before another 50-run planner comparison, choose and validate one of these:

1. make the simulated sensor actually sustain its declared 10 Hz under load;
2. reduce the common speed to a measured safe operating envelope; or
3. increase sensing horizon and prove the new perception-to-stop budget.

Any option must be applied identically to full/sector/adaptive. The next gate
remains seed6 5/5 runs, zero contacts, before any 50-run claim.
