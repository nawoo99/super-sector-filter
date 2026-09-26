# G4 Adaptive ON v2b: confirmed remaining contact

Primary run:
`/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/gapfree_d1_m04/r01_run70003`.
All primary artifact names below use prefix
`artifacts/gapfree_d1_m04_run70003_adaptive.attempt1`.
This is the **ON** run, not an OFF confirmation. Analysis is read-only; no
additional flight, source change or promotion is authorized by this report.

## Analytic contact and executed motion

The run completed the mission in approximately 51.22s but did not complete
safely. The solid audit is valid and complete: 5,121 samples, one contact
episode with 37 contacting samples, minimum clearance **-.2m**. Native static
PCD observation independently reports one contact, minimum **-.184875m**. The
difference is expected between surface-point distance and closed-solid distance;
the analytic centre enters the solid interior, where this audit reports -.2m
(not signed penetration depth).

Obstacle is `cylinder_0040` (zero-based row 40, CSV physical line 42), centre
`[-18.556532,-.319020]`, radius .5m, z range [0,3]. Body radius is .2m.

- First contact: sample **2637**, elapsed **26.375620127s**, header ns
  `1790429107339570736`, position
  `[-19.2332139945,-.2068944494,1.5963011229]`, clearance **-.0140913612m**.
- Previous sample 2636: `[-19.2594729970,-.1989408175,1.6169462289]`,
  clearance **+.0131234503m**.
- First centre-inside sample: 2644, elapsed 26.445130348s,
  `[-19.0390063117,-.3066364186,1.4786757862]`, clearance -.2m.
- First clear sample after episode: **2674**, elapsed **26.745177269s**,
  header ns `1790429107709389673`, clearance **+.0114992159m**.
- Entry-to-first-clear interval: **.369818937s**.

The entry increment is .034336801m over .010026475s, matching approximately
3.42m/s motion rather than a discontinuous position jump. Native contact
context records speed 3.45362m/s and command velocity
`[2.6595,-.8735,-2.0227]`, matching received odometry.
The largest increment during the contact/exit interval is .077373769m at
sample 2655 over .009788166s; repeated poses and subsequent larger increments
mean these sampled records do not prove perfect continuous-time tracking. They
do establish gradual first entry, not a G1-style large handoff jump.

Native `.json` `contact_events[0].position_command` explicitly records
**trajectory_id=114, trajectory_flag=1**, with position
`[-19.2332,-.2069,1.5963]`. In the frozen ROS2 publisher, normal sampled commands
use flag 2 for backup and flag 1 otherwise. Together with the immediately prior
generation-114 commit, this identifies the first contact on the normal/EXP
trajectory, not an executed backup segment. There is no captured full polynomial
trajectory in this artifact (`committed_trajectory=[]`).

## Guard and recovery chronology

Times below are wall-clock epoch seconds from individually timestamped log
records; subtraction uses the first analytic contact header time
`1790429107.339570736`.

| Event | Epoch seconds | Relation to contact |
|---|---:|---:|
| Candidate gen112 rejected EXP CLEARANCE_MARGIN, map288, collision position `[-19.086,-.189,1.473]` | 1790429106.935330749 | -.404240s |
| Gen112 retry committed, map289 | 1790429107.000438846 | -.339132s |
| Gen113 committed, map290 | 1790429107.134873598 | -.204697s |
| **Gen114 committed**, map291, checked range [.027,.876] | **1790429107.272750933** | **-.066820s** |
| First analytic contact / native command gen114 flag1 | 1790429107.339570736 | 0 |
| Gen115 committed, map293 | 1790429107.469363260 | +.129793s |
| Gen116 committed, map295 | 1790429107.666774022 | +.327203s |
| First clear sample | 1790429107.709389673 | +.369819s |
| Next Full recovery cycle3 begins | 1790429111.909723877 | +4.570153s |

Nearby ordered certificate lines report SAFE for gen114 (`poly_publish`, map291;
`main_pre`, maps292 and293), followed by SAFE certificates for gen115 and116.
These certificate print lines lack individual epoch timestamps, so an exact
millisecond time for the last SAFE certificate cannot be recovered. Generation
115's timestamped commit is while the nearest odometry sample (2650, only
.000242s later) is already centre-inside, with clearance -.2m. Thus the retained
evidence supports continuing acceptance during actual solid contact, without
inventing a precise timestamp for an untimestamped certificate.

Entry generation114 and all later commits shown above log `escape=false` and
`footprint_egress=false`. There are **zero** `footprint_egress=true` commit lines
in this entire run. No recorded footprint receipt use explains the contact.
The last nearby handoff rejection was at epoch1790429105.634831675, about1.705s
before first entry; no handoff rejection immediately precedes entry.

No Full-refresh/brake episode is recorded during this .370s contact. The prior
Full recovery was cycle2 at epoch1790429089.300143510, with ACK at
1790429089.436675668 (about17.903s before entry). Frames292–296 around the contact
explicitly report `full=0`, `cycle=2`, `half_angle_deg=45`. The next Full event
is cycle3 more than4.57s after entry, after contact has ended and at a different
position. This is not an observed immediate recovery response to the contact.

## Bounded coverage/bearing hypothesis

The contact event retains **commanded yaw**, not an independent sensor/body
orientation sample: `yaw=4.23185rad`, or **242.467145deg**. Using the command's
recorded position, the cylinder centre bearing is **-9.408104deg**. Wrapped
relative to commanded yaw, the centre is **+108.124751deg**, outside a nominal
±45deg sector. Conversely, commanded velocity heading is **-18.182518deg**, so
the obstacle is only **+8.774413deg** from motion direction.

Filter stats record `event_recovery_body_heading=true`, `half_angle_deg=45`,
and all near-field radius/speed-gain/max-radius values zero. The active frames
are sector frames, not Full. These facts motivate checking whether the path
coverage contract accounts for lateral/rear motion relative to sensor heading.

**Actual sensor/body yaw at entry: unavailable. Preceding approximately1s of yaw:
unavailable.** The retained odometry CSV contains no quaternion; native
`heading_trace=[]` because trajectory-risk auditing was disabled, and this
primary cohort has no ROI trace. Do not replace body/camera yaw with velocity
heading or silently treat commanded yaw as a directly measured camera pose.
The bearing mismatch is a source-labelled hypothesis, not proof that the
actual sensor excluded this cylinder.

Source-path follow-up: perfect-drone `cmdCallback` immediately calls
`updateFlatness`, which assigns position/velocity and algebraically constructs
the attitude quaternion from acceleration plus gravity and commanded yaw.
There is no modeled attitude/yaw tracking lag. However, its body x-axis is the
projection of `[cos(yaw),sin(yaw),0]` onto the plane normal to
`acceleration+[0,0,9.8]`; therefore body Euler yaw need not equal commanded yaw.
Using the rounded contact command and its acceleration
`[5.1614,-15.4195,9.498]` yields a **source-derived body-yaw proxy of
-132.071937deg**, putting the cylinder centre at **+122.663832deg** relative to
that proxy. This is not a newly recovered measured odometry quaternion.

The frontend reads body yaw from received odometry orientation. Its explicitly
body-aligned Adaptive selector ignores velocity heading. At scan acquisition,
the renderer captures the frontend request, retains the current simulator
roll/pitch, and steers horizontal azimuth in that tilted sensor plane before
rendering. Command receipt, odometry receipt and acquisition are separate
events; the actual synchronized quaternion/request/render pose is not present
in this run. Thus neither a physical yaw lag nor an exactly measured camera
bearing can be inferred. Source locations and the equivalent Urban finding
are recorded in `urban_on_v2b_contact_diagnosis.md` beside this report.

## Causal boundary

There is no primary ROI snapshot, no captured raw occupancy neighbourhood, and
no captured command polynomial (`occupancy_messages_received=0`,
`occupancy_local_5m=[]`, `raw_cloud_local_1m=[]`). Those empty observer fields do
not mean the direct C++ mapper received no points. The source contract still
labels stop policy `sampled_unknown_allowed_soft_margin_after_complete_hard_checks`,
revision2, but the cell classification at entry is not recorded.

The supported proximal conclusion is: a normal committed trajectory entered
cylinder40 while guard checks/commits continued to accept it, without recorded
footprint escape or a contact-triggered Full refresh. Whether the relevant map
cells were unobserved, wrongly classified, missed by a query, or incompletely
covered by the active sensor is unresolved. This n=1 failure does not establish
that v2 caused a regression, nor prove a quantization or unknown-space root cause.
The smoke remains non-promotable on safety grounds; no blind policy toggle is
justified by this report alone.

## Primary evidence hashes

- `.solid_audit.json`:
  `6d1a5a0d6762119885cb2b2fa3ea8154a11bc2a04ef0623244f1c6f31c6cef35`.
- Native `.json`:
  `89b72b747bceb68867c9c170da368d5debb6ecfeb815412dd6fc87404579d377`.
- `.odometry.csv`:
  `c4e6297e5bcbdc2fe506fb5b1d222d06738ba04b74ad35030d3fc074d5197b5e`.
- `.stack.log`:
  `12d99e71befff665332408ce1d762bac294be8cff5d2412e0d41636f9d4e8bda`.
- Geometry CSV:
  `077af6f3b3e9ed36574c248bea56a6f8458a6b09db625a731ce3b90fd3d6e44b`.
