# Source-side Sector acquisition v2 (2026-09-16)

## Why this is separate from event-only v1

User clarified that ordinary Adaptive must receive a Sector-only source scan,
not a Full cloud subsequently cropped in the frontend. v1 changed the recovery
policy but still rendered/constructed a360deg source cloud. Its seed1 CPU result
is NOT evidence for source-side acquisition. Both v1 cohorts, all old normal/
stress data, and legacy profiles are preserved.

Pre-edit v2 backup, including renderer/frontend/simulator source and installed
binaries, is local (not Git):
`results/sensor_acquisition_v2_backup_20260916_fsDc9a/runtime_before.tar.gz`.
SHA256 `b4812fa6ba35b748ed507070077dccc5811e68345afcce761d5d1f860226038c`.
Prior mirror/code revision: `38e6750` (with prototype `4cc4a0b` retained).

## Implemented source path

1. `NativeSectorCpp::acquisitionRequest()` provides a read-only snapshot of
   requested Full/Sector, recovery cycle, selected heading and half-angle.
   `--sensor-acquisition` is default off and requires typed direct input, no
   near-field exception and no raw-risk/witness stream. Adaptive additionally
   requires the existing event-only recovery protocol.
2. PerfectDrone captures this snapshot AND scan-start timestamp before rendering.
   MarsimRender changes the angular projection/viewport/scissor, depth readback
   dimensions and ray conversion loop before any PointCloud is constructed.
   With seed1's0.4deg sampling and445 vertical pixels, Full has900 columns and
   Sector225. GENERAL_360 retains its128 sampled rows and10Hz clock.
3. Sector therefore converts28,800 candidate rays instead of115,200 and reads
   200,250 depth+color pixels instead of801,000. Only the acquired region is
   converted into PCL/PointCloud2. Global simulation geometry still exists;
   it is not a sensor observation available to the planner.
4. The frontend receives that already-limited cloud plus its immutable source
   snapshot. It does NOT traverse/crop/repack the points. Exact typed mode/cycle
   matching rejects a Sector scan whose render straddled a Full request, an old
   Full scan after Sector release, or a scan from a previous recovery episode.
5. Existing v1 Full→fresh committed map ACK→new safe trajectory→Sector release
   remains. No new planner/optimizer/guard policy tuning is included in v2.
   No path retains the existing brake/terminal hold. There is no timer-only exit.

Fixed Sector uses the same restricted source, without automatic Full recovery.
Adaptive follows the previous velocity-heading selection, converted to an
azimuth steering offset in the current sensor/body plane. Full uses the original
body attitude. The45deg half-angle is sensor-local azimuth (total90deg), NOT
the old world-horizontal geometric crop under arbitrary roll/pitch. The existing
vehicle roll/pitch is retained. The new acquisition model therefore changes
observation geometry, not just implementation cost. It has no near-field360deg
exception. This policy is a simulated steerable angular acquisition model;
physical LiDAR support or steering latency has NOT been validated.

## Renderer readback correction and matched controls

The first two standalone renderer tests produced an empty cloud because the
test binary resolved the PCD relative to marsim_render instead of PerfectDrone's
asset root. This was a test-fixture path error, not evidence of a readback bug.
Both failed logs are preserved, including
`results/sensor_acquisition_renderer_corrected_20260916/renderer.log`.
The test now uses the same asset root as the simulator and explicitly rejects
an empty ground-truth map before checking scans.

Independently, depth reading after `glfwSwapBuffers` is unsuitable for an exact
new-acquisition contract: the back buffer is not the just-drawn scan. Source acquisition now
reads the just-rendered `GL_BACK` buffer BEFORE swapping, and stamps scan start.
The initial failed fixture log is retained in
`results/sensor_acquisition_renderer_test_20260916/renderer.log`.

The separate Full control enables `SUPER_SENSOR_FULL_ACQUISITION=1` only in its
launch process. It stays360deg but uses the same fresh readback/timestamp policy
as the source-Sector/Adaptive experiment. Legacy invocations do not set this
opt-in and retain their original behavior. No old YAML is modified.

## Measurement and scope constraints

- GPU backing framebuffer allocation remains at maximum size; scene vertices
  are still stored/submitted. Do not claim75% GPU time or memory savings from
  the75% ray/readback reduction. Geometry vertices are not received LiDAR points.
- Sector PointCloud2 keeps the32-byte raw point layout; v1 cropped output had
  removed padding to20bytes. Compare observed source/transport bytes explicitly.
- Frontend `kept_pct` near100% is expected: angular reduction already happened
  at the source. A slight loss can be a rejected in-flight mode/cycle boundary
  frame, not a second angular crop. Use renderer ray/readback and source payload
  counters to measure source reduction, not that old downstream filter ratio.
- This is MARSIM perfect tracking, not a physical stopping guarantee or PX4
  dynamics validation. No physical sensor bandwidth/power claims.
- All failures and infrastructure-invalid attempts are retained. The seed1
  smoke has no automatic retry, map search or tuning to select favorable results.
- Old Normal300 SHA256 remains
  `b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`.

## Verification and reproduction

Pure typed-acquisition test covers all mode/cycle boundary crossings, including
missing metadata. Existing event-latch and ROS protocol tests remain applicable.
The GPU renderer test exercises16 alternating Full/Sector scans with changing
yaw and nonzero pitch/roll, asserting source width, candidate ray counts,
sensor-angle bounds and correspondence to actual map geometry.

Separate closed-loop runner:

```bash
cd /root/super-sector-filter
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 -u scripts/native_campaign/sensor_acquisition_seed1_smoke.py \
  --output results/sensor_acquisition_seed1_n1_20260916 --run 9201
```

Use a new output directory/run ID for another trial. It runs Full/Sector/Adaptive
sequentially, with the same seed1/v7/loop24/static-PCD contact monitor, baseline
and independent1Hz CPU observer as v1. Source frame logs verify widths/rays/
bytes and link each recovery ACK to a frame actually GENERATED in Full mode.
No results are pooled with v1 or the old Normal300 dataset.

## Completed verification and seed1 results (2026-09-16 02:30 KST)

Implementation/verification snapshot: `6a2e476`, local only. All4 packages built
sequentially (7min54s); readback/matched-control rebuild passed (1min45s); final
standalone fixture-root rebuild passed (9s). No parallel flight/build.

`results/sensor_acquisition_renderer_verified_20260916/renderer.log` confirms
all16 real GPU scans passed after loading241,490 truth points. Sector width225,
28,800 candidate rays and maximum sensor azimuth45deg; Full width900 and115,200
rays. Maximum nearest-truth distance across the exercised points was0.302016m,
within the renderer-test0.8m bound (rendered splats need not coincide exactly
with discrete PCD samples). No out-of-window point was observed in Sector.
Typed mode/cycle unit assertions, existing event-latch assertions, legacy ROS
transport10checks and24 prior Python tests passed. The failed empty-map fixture
logs were not deleted or counted as successful tests.

Controller2622042 completed run9201 Full/Sector/Adaptive each1; all first-attempt,
quality/resource/speed-valid, retry0. No experiment is left running. Results:
`results/sensor_acquisition_seed1_n1_20260916/` (not pooled with any prior cohort).
The generic raw.csv `filter_profile` retains the runner's nominal parent label
`strict-burst`; the actual override is source-acquisition/event-only, recorded
in plan.json, source logs and summary audit fields. Do not classify these rows
as the legacy policy from that inherited label alone.

| Seed1 mode | Completion | Static-PCD contacts | Mission s | CPU core-s | Experiment share of20 logical CPUs | Map Total mean ms | Map updates/s | Planner input MiB/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Source Full | 1/1 | 0 | 60.39 | 101.020821 | 8.1788% | 37.4504 | 10.2004 | 5.2080 |
| Source fixed Sector | 1/1 | 0 | 65.22 | 87.916298 | 6.5824% | 11.1501 | 10.2576 | 1.5383 |
| Source event Adaptive | 1/1 | 0 | 66.37 | 89.551627 | 6.5901% | 13.1694 | 10.2305 | 1.6560 |

CPU core-s includes native cgroup simulator/frontend/mapping/planner/mission/
launch CPU time, not background or external observers. CPU% divides mean used
logical CPUs by20. Whole-PC CPU including background was20.7139/19.9098/21.0047%
separately, so it did NOT decrease for A in this observation. Do not substitute
host CPU or infer experimental cost by simply subtracting a background sample.
Map Total is wall time, not CPU time. Planner payload is logical input data,
not physical NIC traffic: Full has an in-process sensor/map connection.

This n1 A vs F comparison observed11.3533% less cumulative CPU,19.4255% less mean
occupied CPU,64.8350% less map-update wall time. Mission time increased5.98s
(9.9023%). Map input points/s were170,655.72/50,406.59/54,264.26 (F/S/A), with
32-byte points in all3 modes; no20-byte packing confound. Filter worker means
S0.1919/A0.2025ms; risk worker work0, risk topic empty/verdicts0.

### Acquisition and recovery evidence

| Mode | Logged source frames | Sector frames | Full frames | Candidate rays converted (whole logged lifecycle) |
|---|---:|---:|---:|---:|
| Full | 616 | 0 | 616 | 70,963,200 |
| Sector | 695 | 695 | 0 | 20,016,000 |
| Adaptive | 707 | 630 | 77 | 27,014,400 |

These source totals include startup/termination and different mission durations,
so they are not equal-duration causal measurements. A spent10.8911% of logged
source frames in Full and89.1089% in Sector. Each Sector scan uses75% fewer
depth/color readback pixels and candidate rays than Full. All source-size and
flight-protocol audit checks passed. Source generated bytes were329,788,768 /
107,037,728 /117,642,208 across these logged lifecycles, not a NIC measurement.

Adaptive Full openings9, Sector returns9, committed refresh ACKs9, new-path
certificates9; all nine ACK timestamps map to source frames marked GENERATED
Full (`full=1`, width900), not queued Sector clouds. Frontend requested2 episodes;
the common planner safety guard directly requested the others. One obsolete
in-flight mode/cycle frame was rejected, removing15,181 points. Hence its old
`kept_pct` is99.586%, while fixed Sector's is100%; neither indicates a post-cloud
angular crop. Latest frontend checkpoint saw704 frames versus707 final source
log records, a3-frame shutdown/checkpoint boundary difference, not three proven
delivery failures. Source Full77 versus frontend accepted Full76 includes the
one obsolete boundary scan.140 above-threshold routine optimizer failure
notifications remained ignored after a successful plan, as specified in v1.

| Recovery | Full scan stamp ns | ACK map | Certified map | New trajectory generation |
|---|---:|---:|---:|---|
| 1 | 1789493370974577550 | 15 | 27 | 1 -> 2 |
| 2 | 1789493373574452691 | 41 | 49 | 4 -> 5 |
| 3 | 1789493379374562335 | 98 | 107 | 7 -> 8 |
| 4 | 1789493398774387950 | 292 | 297 | 45 -> 46 |
| 5 | 1789493400974488142 | 314 | 319 | 48 -> 49 |
| 6 | 1789493423574391276 | 540 | 545 | 87 -> 88 |
| 7 | 1789493429174315125 | 596 | 601 | 92 -> 93 |
| 8 | 1789493430274422537 | 607 | 616 | 93 -> 94 |
| 9 | 1789493432474312107 | 629 | 634 | 94 -> 95 |

Map-based guard recoveries were2/5/9 and measured recovery-active durations
1.8934/2.8384/7.6250s for F/S/A. A's extra5.7316s of recovery-active time is close
to its extra5.98s mission duration, consistent with recovery overhead being a
major contributor; this is not a controlled attribution. Removing near-field
retention and changing acquisition coordinates may affect recovery frequency;
their separate contributions were not isolated. Do not restore outside-Sector
data or tune the planner silently just to improve this result.

Static-PCD minimum body clearances0.308/0.255/0.261m, body radius0.20m. All three
completed; this does not establish safety superiority over Sector or population
100% completion. No deliberately impossible-path closed-loop trial was included;
all9 A recoveries found a new path. The no-path hold protocol was checked in
unit/synthetic transport tests, not validated as a physical dynamics guarantee.

Next validation, if requested, should freeze this source-policy version and
separately test impossible-path hold plus multi-map repeatability. These are
new experiments, not grounds to relabel old normal/stress results.
