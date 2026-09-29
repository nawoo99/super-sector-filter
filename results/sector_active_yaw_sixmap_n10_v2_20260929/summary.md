# Fixed Sector + Active Yaw Recovery: six-map screening

## Outcome

The predeclared 60-flight campaign stopped on the first blocking failure. Runs
94001--94020 completed without contact. Run 94021 completed the mission but made
one static-PCD contact in `forest_cluster_f01`; therefore only 21/60 planned
flights were executed and this directory is an early-stopped safety screen, not
a completed n=10-per-map performance campaign.

| Map | Observed | Mission complete | Contact runs | Time (s, mean ± SD) | Active-yaw arms | Exhaustions |
|---|---:|---:|---:|---:|---:|---:|
| Map 1 (`gapfree_d1_m01`) | 3 | 3/3 | 0/3 | 70.71 ± 7.67 | 29 | 0 |
| Map 2 (`gapfree_d1_m02`) | 3 | 3/3 | 0/3 | 78.77 ± 4.40 | 34 | 3 |
| Map 3 (`gapfree_d1_m03`) | 3 | 3/3 | 0/3 | 80.42 ± 18.34 | 37 | 8 |
| Map 4 (`gapfree_d1_m04`) | 4 | 4/4 | 0/4 | 68.78 ± 3.79 | 35 | 0 |
| Map 5 (`gapfree_d1_m05r2`) | 4 | 4/4 | 0/4 | 67.11 ± 7.06 | 32 | 2 |
| Forest (`forest_cluster_f01`) | 4 | 4/4 | **1/4** | 82.97 ± 11.82 | 40 | 1 |

The aggregate 21-run means (unequal n because of early stopping) were 0.429
end-to-end CPU cores, 32.770 core-s/run, 2.756 MiB/s planner ingress, and 9.749
ms/frame map-update time. These are diagnostic only and must not be presented
as final six-map means.

## Failure reconstruction (run 94021)

- Contact source: static PCD, one episode at mission elapsed 48.048 s.
- Vehicle position: `(-17.1203, -20.9027, 1.6539)`; speed 0.4503 m/s.
- Minimum static-PCD distance: 0.179 m. With the 0.200 m body radius, the
  measured clearance was -0.021 m.
- Nearest obstacle: forest cylinder `trunk_024`, center
  `(-16.4524, -20.7181)`, radius 0.5 m.
- At brake activation the vehicle yaw was 133.3 degrees while the trunk was at
  approximately 14.8 degrees world bearing, or -118.5 degrees body-relative.
  It was outside the fixed ±45 degree sensor sector.
- The guard initially certified the stop path as `SAFE` from its limited map.
  It then detected a clearance conflict and entered emergency braking at about
  0.684 m/s, but the selected stop point `(-17.103, -20.889, 1.648)` already
  overlapped the unseen trunk footprint.
- Active yaw starts changing the commanded yaw only after the brake trajectory
  is finished. Thus this was a blind-sector braking contact before rotation,
  not a collision caused by the yaw maneuver.

## Interpretation

Active-yaw recovery improves the ability of Fixed Sector to regain a route, but
it cannot guarantee a safe stop when an obstacle beside or behind the vehicle
is absent from the limited-FOV map. This result should remain a separately named
ablation (`Fixed Sector + Active Yaw Recovery`) and must not replace the frozen
original Fixed Sector baseline. Full and Adaptive references were not rerun or
modified by this screen.

For context, the frozen n=10 forest results were: Full 10/10 complete, 0 contact
runs, 62.109 s mean; original Fixed Sector 8/10 complete, 2 contact runs,
88.185 s mean; Adaptive 10/10 complete, 0 contact runs, 60.732 s mean. The new
variant's partial 4/4 completion with 1/4 contact cannot be treated as a final
rate because the campaign stopped at the first failure.
