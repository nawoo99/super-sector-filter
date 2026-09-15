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

Final verification and flight results will be appended after completion.
