# Native seed1--10 v6 map design

## Purpose and fixed conditions

V6 turns seed1--10 into a controlled obstacle-size sweep. It removes the old
gap/density axis so that obstacle size is the intended condition difference.
The mission scale inherited from v5 stays fixed:

- field: 64 x 64 m (4096 m2, coordinates +/-32 m)
- obstacles: 410 vertical cylinders per map
- mission loop corners: (+/-24 m, +/-24 m)
- minimum physical obstacle surface gap: 1.00 m on every map
- replicates: two deterministic random layouts per radius tier

The nominal obstacle-count density is therefore the same on all maps,
410 / 4096 = 0.1001 cylinders/m2. Larger cylinders still occupy more physical
area by design; that increasing obstruction is the independent variable.

## Exact seed conditions

| seeds | radius (m) | diameter (m) | nominal minimum center distance (m) | surface gap (m) | count |
|------:|-----------:|-------------:|------------------------------------:|----------------:|------:|
| 1--2 | 0.150 | 0.30 | 1.30 | 1.00 | 410 |
| 3--4 | 0.275 | 0.55 | 1.55 | 1.00 | 410 |
| 5--6 | 0.400 | 0.80 | 1.80 | 1.00 | 410 |
| 7--8 | 0.525 | 1.05 | 2.05 | 1.00 | 410 |
| 9--10 | 0.650 | 1.30 | 2.30 | 1.00 | 410 |

Adjacent tiers differ by 0.125 m in radius and 0.25 m in diameter. The diameter
step is 62.5% of the modeled 0.40 m drone diameter, so the treatment remains
substantial while retaining five levels and two layout replicates per level.
The symmetric sequence is centered on radius 0.40 m.

For obstacle centers `ci`, `cj` and radii `ri`, `rj`, the constraint is:

```text
distance(ci, cj) - ri - rj >= 1.00 m
```

Because every obstacle within one seed has the same radius `r`, the nominal
minimum center distance is `1.00 + 2r`. The generator actually places centers
at least `1.002 + 2r` apart: its extra 0.002 m serialization guard prevents
rounding coordinates to 1 mm from reducing the saved surface gap below 1.00 m.
The 1.00 m value is an **obstacle-to-obstacle surface gap**. It is not the
planner safety threshold, drone-to-obstacle clearance, or collision threshold.

The generator also keeps the takeoff origin at least 3.0 m from every obstacle
surface and each loop corner at least 2.5 m from every obstacle surface. This
prevents the changed cylinder radii from silently shrinking the protected
mission zones.

## Reproduction and generated assets

From the repository root:

```bash
python3 scripts/native_campaign/gen_seeds1_10_v2.py
```

The tracked geometry sources are:

```text
scripts/native_campaign/seed1_static.csv
...
scripts/native_campaign/seed10_static.csv
```

One run deterministically updates all three representations:

- tracked obstacle manifests: `scripts/native_campaign/seedN_static.csv`
- Gazebo SDF and sidecar manifest:
  `/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds/default_seedN.{sdf,obstacles.csv}`
- native MARSIM point clouds:
  `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seedN.pcd`

Before replacement, existing v5 assets are copied once to:

```text
/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds/backup_v5_before_uniform_gap_size_sweep
/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/backup_v5_before_uniform_gap_size_sweep
```

The backup routine does not overwrite an existing backup of the same filename.

## Generated-asset and endpoint validation

The 2026-08-03 generated assets passed these persisted-file checks:

- 410 CSV obstacles and 410 matching SDF cylinders in every seed;
- tracked CSV and external Gazebo sidecar byte-identical for every seed;
- minimum saved surface gap 1.001728--1.009272 m;
- minimum saved obstacle-surface distance 3.001362 m from takeoff and
  2.518039 m from a loop corner;
- PCD header point count equal to the actual data-row count.

| seeds | PCD points per map |
|------:|-------------------:|
| 1--2 | 241,490 |
| 3--4 | 444,850 |
| 5--6 | 635,500 |
| 7--8 | 838,860 |
| 9--10 | 1,042,220 |

The ten current PCDs contain 6,405,840 points in total (about 143 MiB as ASCII
files). The final upper-tier one-run smoke is recorded in
`results/native_seed1_10_v6_final_endpoint_smoke.csv`:

| map / mode | completed | collisions | minimum UAV-center-to-surface distance (m) | kept points (%) |
|------------|----------:|-----------:|-------------------------------------------:|----------------:|
| seed9 full | yes | 0 | 0.224 | 100.000 |
| seed9 adaptive | yes | 1 | 0.169 | 29.158 |
| seed10 full | yes | 0 | 0.237 | 100.000 |
| seed10 adaptive | yes | 2 | 0.006 | 30.993 |

This confirms that radius 0.650 m is below the observed full-baseline failure
boundary while remaining discriminating. It does **not** establish collision
rates: there is only one run per cell. In particular, adaptive's observed
contacts must be reported rather than treating completion as collision-free.

An earlier radius-0.20--0.80 m candidate is preserved separately in
`results/native_seed1_10_v6_r080_candidate_stress.csv`. At radius 0.80 m the
full baseline itself recorded 2 and 4 contacts on seed9 and seed10, so that
candidate was rejected as the main controlled sweep and retained only as a
geometric/planner stress diagnostic.

## Result-version boundary

`docs/paper_story.md` and `results/native_campaign_v5_seed1-10.csv` describe the
v5 maps and the v5 campaign. Those measurements remain valid historical v5
evidence, but they are not v6 results: v6 changes the map treatment from the old
size/gap conditions to the five fixed-gap radius tiers above.

Do not relabel, merge, or directly aggregate v5 rows as v6. Endpoint smoke runs
only validate basic operation. Headline completion, collision, clearance,
point-count, timing, and CPU comparisons for v6 must come from a fresh full
campaign across seed1--10 and all compared filter modes.
