# seed1-10 is_dense fix: root cause and re-validation

`sensor_msgs_py.point_cloud2.create_cloud()` hardcodes `is_dense=False` on
every message it builds. ROG-map's `cloudCallback` drops any frame with
`is_dense=False` outright (`pcl::fromROSMsg` copies the flag as-is; no
NaN rescan). `native_sector.py`'s filtered-cloud publish path used
`create_cloud()` for sector/adaptive/velocity/trigger, so most of their
frames never reached the occupancy map, even though the points themselves
were dense (no NaNs; already filtered with `skip_nans=True`). `full` mode
republishes the untouched upstream message and was unaffected. Direct
measurement on a live run showed the occupancy map's nearest known-occupied
cell 1.7-4.7 m away from the live sensor's actual nearest obstacle at the
moment of contact, despite hundreds of raw points on that obstacle in the
current frame. Fix: set `out_msg.is_dense = True` before publish in
`native_sector.py`.

Two other real (but non-dominant) issues were found and fixed along the way
and are kept:

- `fsm_ros2.hpp`: `replan_cbk_group_` was created but never wired to
  `replan_timer_` (which used `exec_cbk_group_` instead), so replanning
  shared/starved the same callback group as the ROG-map update timer.
  Fixed to use `replan_cbk_group_`.
- `native_sector.py` gained a replan-failure-triggered full-open safety
  valve (subscribes to a new `/planning/replan_status` topic published by
  `fsm.cpp::callReplanOnce`) and an always-keep near-field radius. Neither
  moved the aggregate numbers on their own; the is_dense fix did.

## Files

- `native_seed1_10_isdense_fix_n5.csv`: full re-validation campaign, n=5 x
  (full/sector/adaptive) x seed1..10 = 150 runs, same config as the original
  ablation (`static_seedmaps.yaml`, max_vel=3.0, max_acc=15.0, loop24
  mission). Headline: full 26/50 (52.0%) contact-flagged / mean min
  clearance 0.203 m; sector 17/50 (34.0%) / 0.250 m; adaptive 16/50 (32.0%)
  / 0.257 m. kept_pct: sector 48.6%, adaptive 49.0%. Mission time and fsm
  CPU are within ~1% across modes.
- `native_seed1_10_paper_speed_sweep_n5.csv`: same seed1..10/loop24 ablation
  but on `static_seedmaps_paper_v{1,4,7,10,14,18}.yaml` (max_acc=20 m/s^2,
  matching the SUPER paper's fixed acceleration; max_vel swept over the
  paper's 1-18 m/s set instead of a fixed 3.0). n=5 x 3 modes x 6 speeds x
  10 seeds = 900 runs. Aggregate (all speeds pooled): full 60.3% contact /
  0.157 m; sector 57.3% / 0.169 m; adaptive 55.0% / 0.172 m. Contact rate
  rises sharply with speed for all three modes (2-5% at v=1 to ~70-82% at
  v=10-18), consistent with kinodynamic (angular-rate/thrust) infeasibility
  during loop24's four 90-degree corners, not a perception gap.
- `native_seed1_10_straight_direction_probe.csv`: `full` mode only, 10
  seeds x 4 single-leg straight missions from the shared (0,0) spawn point
  toward each loop24 corner (NE/W/S/E), `static_seedmaps.yaml`
  (max_vel=3.0). Built to test whether loop24's four 90-degree turns are
  the reason contact rates are far from the SUPER paper's reported 0%.
  Contact rate: NE 2/10, W 2/10, S 2/10, E 4/10 -- 10/40 (25%) pooled,
  i.e. distance-normalized contact rate is still ~3x lower than loop24's.
  Turning is not the explanation either.
- `native_seed9_10_full_loop24_contact_segment_position.csv`: every
  `full`-mode contact_event from the n=5 campaign above, on seed9/seed10
  (hardest maps), projected onto its nearest loop24 segment
  (`segment_fraction_t`: 0 = just-turned corner, 1 = next corner). 51/56
  (91%) land in the segment middle (0.15-0.85); 0/56 land right after a
  turn (<0.15). Contacts are not clustered at the corners.

## Interpretation

loop24's higher contact rate versus a short straight probe is best
explained by coverage: loop24 traces the field's ~223 m perimeter near the
+-24 m edges over 4 legs, while each straight probe is a single ~32 m ray
from the field center. The obstacle field's difficulty is not spatially
uniform, and loop24 simply samples far more of it. Since full/sector/
adaptive are always run on identical seeds/missions/config, this shared
per-mission difficulty does not bias the three-way comparison -- it only
means the absolute contact rate should not be read against the SUPER
paper's 0% headline, which used straight 100 m single-goal missions on 60
different (non-public) maps.

Neither GitHub (`hku-mars/SUPER`, `git ls-files`) nor the paper's Zenodo
release (10.5281/zenodo.14528604) contain the paper's actual 60 evaluation
maps; only a handful of unrelated demo `.pcd` files are tracked.
