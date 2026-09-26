# Urban ON v2b: first-entry and heading audit

Primary run:
`/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005`.
Artifacts below use prefix `artifacts/urban_blocks_u01_run70005_<mode>.attempt1`.
This report covers **ON only**, not OFF confirmation. Analysis reads retained
artifacts and existing source; no flight or frozen-input edit was performed.

## Confirmed outcome and first entry

Adaptive and Sector each timed out at approximately 180s with 0/5 waypoints
reached and one continuous analytic solid-contact episode. Their audits are
valid and observer-complete, but mission success is false. Both remain in
contact at the final sample. Observer completion is not mission completion or
safety. Full was not executed in this ON triplet; the controller retained the
Sector timing/source-contract gate failure rather than inventing a third result.

Both first contacts are with `building_10`, primitive index9: centre(-7,7),
size6x8m, solid bounds **x[-10,-4], y[3,11], z[0,6]**. Body radius is .2m.
The relevant entry surface is the east face x=-4, not a different building near
the old diagnostic ROI(22,9.5).

| Observed field | Adaptive | Sector |
|---|---:|---:|
| Received samples | 18,000 | 18,000 |
| Contact samples | 17,367 | 17,361 |
| First contact sample | 634 | 640 |
| First contact elapsed seconds | 6.339383602 | 6.404018879 |
| First contact header ns | 1790429283301078771 | 1790429495514220511 |
| First clearance, m | -.018210617 | -.033237284 |
| First centre-inside sample | 644 | 647 |
| Minimum clearance, m | -.2 | -.2 |
| First-contact command generation / flag | 8 / 1 | 9 / 1 |

Adaptive first-contact position is
`[-3.8182106167,3.4838471255,2.4686617575]`, velocity
`[-1.3386996504,-.3147039937,-.1500887787]`. Previous sample633 is
`[-3.7936404126,3.4906337941,2.4712000080]`, clearance+.006359587m.
The first-entry increment is **.025616333m over .009977867s**. Sector first
contact is `[-3.8332372844,3.3429179599,2.1217592612]`, previous clearance
+.004730455m and increment **.038140661m over .009949110s**.
These are incremental entries, not a large position teleport. Repeated poses
and catch-up increments elsewhere mean the sample stream does not prove exact
continuous-time tracking or exact velocity agreement at every interval.

Native static-PCD contact contexts independently identify the same wall and
record matching commands. Both first-contact commands have flag1 (normal/EXP,
not backup); native trajectory IDs are8 and9 respectively. Neither entire stack
log contains `footprint_egress=true`. Minimum -.2m is distance-to-solid minus
body radius for a centre inside a closed solid, not signed penetration depth.

Final native positions are approximately Adaptive(-9.396,10.221,1.843) and
Sector(-9.316,10.547,2.550), both inside building10. Received contact persists
from the first-entry sample through the final sample; no sampled exit occurs.

## Adaptive guard and Full chronology

The immediately preceding Full episode is important: the failure cannot be
explained solely by asserting that the wall was never inside any recent Full
scan. Times below are epoch seconds; no individual timestamp is invented for
the untimestamped `TRAJ_GUARD_CERT` print lines.

| Recorded event | Epoch seconds |
|---|---:|
| Full cycle1 requested | 1790429281.670832236 |
| Full map84 ACK | 1790429281.798062543 |
| Certified stationary hold at(-3.727,3.505,2.468), outside wall | 1790429282.001019818 |
| Gen6 EXP candidate rejected, collision(-3.938,3.500,2.448), map86 | 1790429282.040226917 |
| Last cycle1 Full frame97 acquisition timestamp | 1790429283.051219183 |
| Recovery gen7/map97 committed, footprint_egress=false | 1790429283.098927674 |
| Recovery released to sector | 1790429283.100723498 |
| Gen8/map98 committed, range[.039,.752], footprint_egress=false | 1790429283.248049586 |
| **First analytic wall contact** | **1790429283.301078771** |
| First subsequent gen9 handoff rejection | 1790429283.402898125 |
| Next Full cycle2 request | 1790429284.014395299 |

Entry is **53.029185ms after gen8 commit**, **200.355273ms after sector release**,
and **249.859588ms after last Full acquisition**. Full frames84–97 were emitted
before sector frames98 onward. Gen8 `poly_publish` is reported SAFE on map98;
later `main_pre`/`replan_post` certificates remain SAFE on maps99–105 while
received odometry is in contact. The subsequent handoff rejections retain gen8;
they occur after entry and do not explain the initial penetration as a rejected
handoff jump. No footprint-egress exception is recorded.

In Sector, gen9/map96 commits at1790429495.423958582, **90.261929ms before first
contact**; its `poly_publish` and later maps97–100 checks report SAFE. Generation
10 later commits while contact continues. Its nearby acquisition frames are
cycle0/full0. Sector has no event Full handshake, as expected for this mode.

## Commanded heading, source-derived body heading, and actual evidence limit

Closest-solid bearing at these east-face entries is180deg (due west), using
the nearest point on the closed box at the same y,z. A building-centre bearing
would answer a different geometric question. Angles below use recorded rounded
native contact command values; relative angles are wrapped to[-180,180].

| First-entry heading quantity, degrees | Adaptive | Sector |
|---|---:|---:|
| Commanded yaw | 89.147649 | 99.326244 |
| Command velocity heading | -166.771170 | -176.107869 |
| Wall relative to command yaw | +90.852351 | +80.673756 |
| Wall relative to velocity heading | -13.228830 | -3.892131 |
| Source-derived body-yaw proxy | 79.403205 | 83.434177 |
| Wall relative to body-yaw proxy | +100.596795 | +96.565823 |

Adaptive contact acceleration is[-11.6656,2.9599,-2.5294]m/s²; Sector is
[-14.9446,4.5764,2.2471]m/s². The proxy reproduces simulator flatness algebra
from those commands, not a measured quaternion. Both filter stats have45deg
half-angle and zero near-field radius/speed-gain/max-radius. Adaptive records
`event_recovery_body_heading=true`; Sector's mode itself selects body heading.
Velocity heading is therefore not the selected sector axis.

The actual command-to-render source path is:

1. `mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp:1281`
   calls `updateFlatness` directly from each received PositionCommand.
2. The same file:1518 assigns position/velocity immediately and constructs
   `zB=normalize(acc+[0,0,9.8])`, `yB=normalize(zB cross xC)`,
   `xB=yB cross zB`, where `xC=[cos(yaw),sin(yaw),0]`. There is **no modeled
   attitude tracking lag**, but resulting body Euler yaw can differ from
   commanded yaw under tilt.
3. The same file:1443 publishes that quaternion in odometry.
   `mission_planner/Apps/native_sector_cpp.cpp:1180` extracts body yaw from
   received odometry quaternion; :688 captures acquisition mode and centre.
   `mission_planner/include/mission_planner/sector_heading_policy.hpp:17`
   selects body yaw for these policies, not velocity heading.
4. `ros2_perfect_drone_model.hpp:744` captures an immutable acquisition request
   before rendering, reads current simulator pose, and steers azimuth within
   the retained tilted body plane. Therefore scan orientation is not simply a
   world-z quaternion of commanded yaw.
5. `mars_uav_sim/marsim_render/src/marsim_render.cpp:314` transforms the render
   camera's forward/up axes using the supplied scan quaternion.

Command callback, odometry callback and acquisition are distinct events.
Transport/sampling age is possible even though the simulator has no physical
yaw-lag model. **Actual synchronized body quaternion, frontend requested heading
and render quaternion at entry, and the preceding1s of yaw, are unavailable.**
Odometry CSV retains positions/velocities but no quaternion; `heading_trace=[]`.
The preceding1s Adaptive odometry shows a stationary hold for most of that
interval and movement resuming shortly before contact. It does not supply the
missing yaw history. Do not relabel motion direction or this algebraic proxy as
measured camera orientation.

## Proven versus unresolved

Proven: normal committed commands incrementally enter building10, with SAFE
certificates around/after entry and no recorded footprint-egress use. Commanded
heading and source-derived attitude are strongly lateral to motion/nearest wall.
Adaptive recently completed Full acquisition/ACK and then released to sector.

Unresolved: whether the relevant wall surface was actually rendered, filtered,
inserted, retained, or queried at the decisive guard snapshot; whether the path
was unobserved/unknown, misclassified, or missed by a predicate. This primary run
has no ROI trace, no full captured command polynomial, and no corresponding map
snapshot. Empty native raw/occupancy subscriber fields do not mean direct C++
map handoff received no points. The recorded policy still allows sampled unknown
space; that fact does not establish the entry cell's classification.

The bounded next diagnostic is synchronized command/quaternion/acquisition,
raw-wall points, map updates and guard queries around **building10's east face**,
including the last Full frame and first sector commits. Source-derived lateral
bearing is a useful hypothesis, not proof that coverage alone caused the contact.
These ON failures preclude a safety-promotion claim; no blind threshold/budget
increase or unknown-policy toggle is justified by this report.

## Evidence SHA256

| Artifact suffix | Adaptive | Sector |
|---|---|---|
| `.solid_audit.json` | `5ff777c8db9c430dc590319e77e4adcb265738c23f5220796031d2c6f0bc51e3` | `f0a1e198f975e881aeae0a20b0e77f837e434c4e791eeccbae30a70911fd4c45` |
| `.json` | `fd977bf35e9a6f99f68bc18d5e2c426ca2bf4422d37730b33c9c4965408a9c58` | `4e3a1d76193d6b857ac6165d662b38813740dd87ada5937a21310204379bd4cd` |
| `.odometry.csv` | `f23bee0d58b13307ed64c64cee4c84977b330c649d6b8bc7620c315756ce1563` | `286e34dbb71bfccae6b9f124f319c89c008a4c18d3b33f4758eff5d56ff3cc2b` |
| `.stack.log` | `649a3fd1c28e27b915a7ee6a5ca0bef4940d0f991ba45b19ca6c8302834af4f3` | `0dff4f576309524e6908a3050d4c4e83628a3e2fbb83a17cb1c1f5d6229d5827` |

Geometry `urban_blocks_u01_geometry.json`:
`f40398b0b3a555c96c0acc1f323fc1547cf355a281ce0ec0a225b678c246c8ed`.
