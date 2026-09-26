# Urban east-face sensor/map/guard audit — pre-probe findings

Scope: read-only review of v2 production code and the completed ON run70005.
The new standalone test is additive only. No production range, policy, source
or prior result was changed. A deterministic fixture does not establish a
specific flight's cause without corresponding sensor/map/query evidence.

## Strongest concrete discriminator: near-range rejection after rendering

The completed Urban ON Adaptive stack loads mapper `ray_range=[0.5,100]`, raw
resolution.05m, inflation resolution.1m/step3, point_filt_num1, intensity
threshold-10, raycasting=false, fixed-map immutable snapshots. Simulator config
`urban_blocks_u01.yaml` has sensing_blind.1m. The no-raycast mapper branch at
`rog_map/src/rog_map/prob_map.cpp:881` rejects every endpoint whose squared
distance to the mapper's cloud pose is below.25 **before inserting a hit**.
Full-mode metadata does not override this predicate.

Recorded held pose immediately before the first entry:
S=(-3.7268038947764675,3.5052099309384137,2.467517505190736).
Building10's east wall is x=-4. The nearest surface is only.2731961052m away;
the mapper's rejected patch on this plane extends about.4187647169m laterally
from its projection. Sensor returns from.1–.5m can therefore exist yet be
excluded from this map even during Full. Previously mapped wall cells or
retained points outside that patch could still protect the trajectory; their
actual existence must be checked, not assumed absent.

The mapper pose is the latest robot-state pose captured by
`rog_map/include/rog_map_ros/rog_map_ros2.hpp:211` when the cloud is enqueued,
not the immutable renderer acquisition pose. The cloud's points remain in
world coordinates. Pose age does not transform those points, but changes
near-range rejection and observed-free ray origin. Use `map_input_cloud`'s
sensor_position for the actual cutoff, not an interpolated render pose.

Startup clearing is a separate mechanism. `updateProbMap` at prob_map.cpp432
uses process-static `first` and calls `missPointUpdate(...,999)` around the
first map pose within `raycast_range_min`. It is **not per-frame clearing**.
For these missions it occurs near(0,0,1.5), far from building10. Changing the
minimum range would also change this startup-clear radius, so a test must
isolate startup and should not silently equate a range counterfactual with an
approved production fix.

## What the current guard actually queries

`SuperPlanner::validatePositionTrajectory` prepares trajectory endpoints and
inflated-grid DDA cells. It evaluates raw occupied voxel-centre/body distance
at mandatory current/start/end poses, and at other samples when an inflated
cell is occupied. With inflation false at an intermediate sample, it returns
the local `safe` verdict without calling the raw-body predicate. The actual
body predicate uses radius.2m and real boxSearch with half-cell padding. This
is not a closed-solid box-volume predicate; once inside a hollow surface map,
an interior pose far from mapped shell cells may appear clear.

Current additional guard clearance is0, so no extra clearance-offset queries
exist. Configured inflation radius.3m exceeds body radius.2m, but can only
inflate retained occupied evidence; it cannot restore a deleted/missing patch.
The direct point queries and immutable snapshot must be compared at the same
raw and inflated global indices to distinguish observation loss from a writer,
publication or query bug.

Immutable `isUnknown` searches a ±3-cell raw neighborhood and returns false if
*any* cell is known, including occupied cells. `isUnknownInflate` always returns
false in this mode, and `isKnownFreeInflate` means only `!occupied`. These are
not precise observed-free volume proofs. An unknown-policy flip alone would
not establish a complete coverage contract.

No general ring-hash/origin mismatch was found in this review. Writer uses
floor(position * inverse_resolution), snapshot uses floor(position / resolution),
and both use the same signed ring mapping with ORIGIN_AT_CORNER. Exact float
boundary equivalence deserves a regression, not a causal assertion. Physical
boxSearch excludes min/max index layers in both fast and baseline paths; the
half-cell padded search should be tested at exact tangency. Fast-vs-baseline
equivalence alone cannot reveal a common boundary omission.

## Existing trace: positive evidence remains useful despite truncation

Renderer and mapper-input records retain the first4096 ROI points, count all
ROI points, and expose `roi_truncated`. A retained wall point proves that point
was rendered/handed to the mapper even if the remainder is truncated. With
the active filters, each retained finite in-map point at mapper-distance<.5
proves a near-range rejection by the unchanged code. A missing point in a
truncated record proves nothing about its presence elsewhere in that cloud.
Lost records, absent footer or writer sequence gaps similarly prohibit a
negative completeness claim.

`map_raycast_summary` counts all ROI inputs and all near-range rejections, but
does not identify individual rejected coordinates. `map_probability_update`
records actual hit/miss outcomes. `map_snapshot_raw_delta` records dirty raw
cells; absence from a delta does not mean a previously committed cell is absent.
There is no corresponding per-cell inflation delta. `map_input_cloud` currently
lacks source stamp/scan sequence, so exact cross-stage joining cannot rely on
timestamp proximity alone when records/frames are missing. Synchronized tracing
should bind source stamp, accepted/processed scan sequence, mapper pose, map
version, raw/inflated indices, and actual query-snapshot version.

## New actual-library fixture and expected discriminating outcomes

Source: `rog_map/test/near_range_wall_hole_test.cpp`, mirrored to
`super_patches/native_seedmap_campaign/rog_map_test/near_range_wall_hole_test.cpp`.
Run separate fresh processes with campaign YAML and `--min-range 0.5` or0.1;
ProbMap permits only one initialization per process. Allocation is bounded,
probabilities/resolutions/inflation remain production values, startup clearing
is exercised at(0,0,1.5) before any wall evidence. ROGMap::init is deliberately
not called because it opens shared diagnostic log files.

Fixture cloud contains float32 points(-4,3+.05*j,1.5+.05*k), j,k=0..30, repeated
for14 held-pose frames. This is a deliberately constructed dense wall, **not
the unrecorded flight clouds**. It queries the real mutable probability/InfMap,
real immutable snapshot, real physical-body boxSearch and exhaustive retained
wall-cell centres at S, first-contact Q, and centre-inside sample644:

- Q=(-3.818210616665875,3.483847125503175,2.4686617574571397).
- Inside=(-4.013501266431111,3.484294077239634,2.4389091380733467).

A lightweight structural calculation predicts222/961 endpoints rejected per
frame at.5; nearest retained raw centres at Q/Inside are approximately.402546m
and.371973m, with both inflation queries false. These preliminary numbers are
not actual-library evidence. The standalone test will assert whether the real
archive reproduces the hole and whether the.1 counterfactual restores both
raw-body and inflated occupied answers. It explicitly does **not** claim to
invoke the full planner trajectory validator. Actual-library baseline execution
is now complete after the unchanged-v2 probe ended; see
`near_range_wall_hole_proof.md` for results and frozen input hashes.

For the exact failure, compare the latest Full scan, first sector commit and
first-contact query near building10, not the previous unrelated Urban ROI.
Only then select a bounded correction at the demonstrated loss stage.
