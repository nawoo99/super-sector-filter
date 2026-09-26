# G1 repair OFF smoke: Adaptive contact audit

Date: 2026-09-26. Scope: **uninstrumented/profile-OFF, n=1 Adaptive**, retrospective read-only analysis. OFF refers to CPU profiling, not disabling the repair or asynchronous recovery. No runtime code, geometry, thresholds, recorded evidence, or flights were changed for this audit.

## Conclusion

The repair candidate **does not meet zero-contact admission**. Adaptive completed in 59.72 s but contacted a cylinder for 104 consecutive received odometry samples. The minimum analytic solid clearance was **-0.168520456 m**. The native static-PCD observer independently recorded one contact episode, so this is not merely a closed-cylinder versus sparse-PCD disagreement.

Entry was smooth execution of an already committed backup trajectory, generation 122, not the earlier r08-style moving-handoff jump. Its live guard certificates remained `SAFE` during contact. Full recovery activated only after this trajectory finished and the next from-rest candidate failed. The vehicle was already stopped at an overlapping pose. The newly added initial-footprint-egress receipt was **not exercised anywhere in this run**.

This is evidence of a remaining runtime-map/physical-safety mismatch. These artifacts do not contain the local sensor/map membership and sampled-trajectory trace needed to identify its precise cause. Do not promote the candidate or treat successful mission completion as a safety pass.

## Evidence and identity

Campaign-relative run directory:

`results/scenario7_repair_smoke_20260926_v1/test10/gapfree_d1_m01/r01_run60100/`

Artifact stem under that directory:

`artifacts/gapfree_d1_m01_run60100_adaptive.attempt1`

| Input | SHA256 |
|---|---|
| Stem + `.json` | `69e065ce23a4059a442c6ff1d2e4047cd7f2043f6192a82789714d6ac22cc57a` |
| Stem + `.solid_audit.json` | `e79153672ed79521cb42e448b6ca4f1bcc69a717eef49dcf771db545a9870b58` |
| Stem + `.odometry.csv` | `7bd2a9fad39f808c3eb36755f1b1693aac697b6f0e82410df3b45d71bb0bfefb` |
| Stem + `.stack.log` | `646abc2144c3835fa6a5c06be448e0eb97daf899892750411aed3e46132ceb94` |

The solid audit validates its native JSON and odometry hashes and reports `audit_valid=true`, no invalid samples, no nonmonotonic timestamps, and `observation=received_odometry_samples_only`. It does not claim a continuous swept-body collision proof.

Map geometry SHA256: `64083e847d41306494aee57f9e6db9c53607ca0368ca819b9f65c59393ebed0a`.
PCD SHA256: `98ad0e49a126ecbb7f1b6ee8532db06aa76720f4d3cfd7c513441fa9ab576d9e`.

## Observed outcome

| Metric | Adaptive OFF |
|---|---:|
| Mission completion | yes |
| Mission time | 59.72 s |
| Received odometry samples | 5,971 |
| Analytic solid contact episodes | 1 |
| Contacting received samples | 104 |
| Minimum solid clearance | -0.168520456 m |
| Native static-PCD contact episodes | 1 |
| Native static-PCD minimum clearance, rounded summary | -0.153 m |
| First solid contact sample | 3942 |
| First solid contact elapsed receipt time | 39.424080372 s |
| First non-contact sample after episode | 4046 |
| Episode span, entry-to-exit receipt time | 1.041081429 s |
| Episode span, entry-to-exit header time | 1.040183059 s |
| Whole-flight maximum header interval | 10.529943 ms |
| Whole-flight maximum receipt interval | 11.122346 ms |
| Speed-limit check | valid |
| Moving-candidate handoff rejections | 17 |
| Cached-EXP reuse rejections | 1 |
| Guard commit log entries | 220 |
| `footprint_egress=true` commits | 0 |

Contacting primitive: **index 68 / `cylinder_0068`**, center `(-28.591183, -4.598807)`, radius 0.5 m, height [0, 3] m. The observer body radius is 0.2 m. Clearance is distance from the body center to the closed solid minus body radius; this is the frozen clearance metric, not a newly introduced signed-distance convention.

## First contact and minimum

| Sample | Header epoch, s | Elapsed receipt time, s | Position, m | Solid clearance, m |
|---:|---:|---:|---|---:|
| 3941, last clear sample | 1790417132.030202510 | 39.414038897 | (-29.126860, -5.084849, 0.953887) | +0.023316274 |
| 3942, first contact | 1790417132.040215779 | 39.424080372 | (-29.100598, -5.077651, 0.951730) | -0.000860886 |
| 3990, stationary inside episode | 1790417132.520384086 | 39.905177355 | (-28.836346, -5.071279, 0.939658) | -0.167708531 |
| 4024, last stationary sample before recovery motion | 1790417132.860390828 | 40.244711161 | (-28.836346, -5.071279, 0.939658) | -0.167708531 |
| 4025, minimum | 1790417132.870397566 | 40.254819870 | (-28.832052, -5.072571, 0.926447) | -0.168520456 |
| 4046, first clear sample | 1790417133.080398838 | 40.465161800 | (-29.215429, -4.967761, 1.004863) | +0.025127919 |

At entry, velocity was `(2.628632, 0.679150, -0.157891)` m/s. The entry step was **0.027315498 m in 10.013269 ms**. Samples 3934–3949 have header intervals 9.729–10.184 ms and receipt intervals 9.157–10.714 ms. Clearance decreases smoothly through zero. There is no contact-window missing-odometry or approximately 0.9 m teleport signature.

The native first-contact event is at epoch 1790417132.052923 / elapsed 39.4364 s, with position `(-29.0744, -5.0714, 0.9506)`, speed 2.66277 m/s, PCD distance 0.18337 m, command `trajectory_id=122`, and `trajectory_flag=2`. The normal command publisher maps `sample.on_backup` to flag 2 (`fsm_ros2.hpp`, `fillPositionCommand`, around line 2035). No emergency brake was activated at contact entry; this is the appended backup of generation 122, not an emergency-brake flag inferred solely from its numeric value.

## Planner and recovery timeline

Epoch seconds below are from timestamped stack log records, except the explicitly marked odometry records. `TRAJ_GUARD_CERT` lines do not themselves include wall timestamps; their map/range and adjacent log ordering are reported without inventing exact callback times.

| Epoch, s | Event and evidence |
|---:|---|
| 1790417126.736328443 | Last handoff rejection before contact: candidate gen96/from95, position error 0.026937153 m, velocity error 0.781894417 m/s, acceleration error 3.189296887 m/s²; candidate time 0.034170 s. Stack line 2442. This is **5.303887 s before contact**. |
| 1790417131.541830109 | `ReplanOnce/with_backup` commits gen122/map414; checked range [0.021, 0.718] s, 142 samples, `escape=false footprint_egress=false`. Stack line 2737. |
| 1790417131.743572706 | Replacement gen123 APPENDED_BACKUP rejected `CLEARANCE_MARGIN`, map416. More replacement candidates are rejected on maps417–419, covering backup, EXP-to-backup stitch, and EXP. Current gen122 is retained. |
| 1790417132.040215779 | First analytic contact, odometry sample3942. Approximately 0.498386 s after gen122 commit. |
| 1790417132.047371466 | Replacement gen123 EXP rejected `CLEARANCE_MARGIN`, map419. |
| Between surrounding 1790417132.059399142 and 1790417132.060049584 records | Current **gen122 still `SAFE`**, map420, `main_pre`, range [0.534, 0.718], 38 samples, speed 2.663 m/s. Stack line 2766, already after contact onset. |
| 1790417132.180347221 | Cached-EXP reuse rejected: gen122, position error **0.260079295 m**, velocity error 3.489059858 m/s, acceleration error 23.834206068 m/s²; action `retain_committed_command`. This is **140.131 ms after contact entry**, so this rejected mismatch did not initiate the episode. Stack line 2778. |
| Immediately following the cached-EXP rejection | Current gen122 again `SAFE`, map421, range [0.634, 0.718], 18 samples, speed 1.198 m/s. Stack line 2779. |
| Around 1790417132.245661087 | Trajectory finishes; command callback switches FOLLOW_TRAJ → GENERATE_TRAJ. Vehicle is stopped at an overlapping pose. |
| 1790417132.285656673 | First from-rest replacement rejected `CLEARANCE_MARGIN`, map422. |
| 1790417132.285702405 | Recovery signal activates, **245.487 ms after first solid contact**. |
| 1790417132.285815318 | Full acquisition opens, cycle8. |
| 1790417132.355980427 | Exact Full frame ACK: request8, stamp1790417132340342110, map423. |
| 1790417132.394203832 through 1790417132.604428471 | Stationary brake attempts rejected `UNOBSERVED` on maps423–425; no moving emergency brake is newly published. |
| 1790417132.714262550 / 1790417132.714383228 | After 0.320 s stationary stability, `publish_certified_hold`; brake reports `SAFE`, map426, zero speed, stop `(-28.836,-5.071,0.940)`. This remains physically overlapping according to the independent solid observer. |
| 1790417132.724186799 | Async from-rest request23, revision23, previous gen122, exact Full request8/ACKmap423. |
| 1790417132.835013161 | From-rest gen123 commits on map427, checked range [0.061,1.068], `escape=false footprint_egress=false`. |
| 1790417132.844150584 / 1790417132.844339610 | Path ready gen123/map427, recovery releases, Full closes to Sector. |
| 1790417132.870397566 | Minimum clearance sample4025, shortly after recovery starts moving; step only 0.013951388 m. |
| 1790417133.080398838 | First clear odometry sample4046; episode ends. |

The existing stationary-hold fallback rechecks a stable, zero-displacement `UNOBSERVED` candidate with `unknown_as_occupied=false`; ordinary candidate admission and live committed-trajectory validation also pass false explicitly. This policy is visible in `fsm_ros2.hpp` around lines 2769–2787 and `super_planner.cpp` around lines 936–941 / 1741–1749. It must not be described as an all-unknown-is-occupied guarantee merely because the YAML configured value is true. The log proves the resulting hold was certified, but without exact guard/map traces it does not establish which missing/occupied-cell predicate was decisive.

## What is and is not explained

- **Confirmed failure class:** a committed backup and its subsequent stationary endpoint overlap physical geometry while current map-based guard results say `SAFE`. Replacement-candidate rejections are not sufficient protection when the retained path is itself a physical false negative.
- **Not a repeated rejected handoff:** the final pre-contact handoff rejection was over 5 s earlier; the cached-EXP rejection occurs after contact entry. These candidates were rejected, not committed.
- **Not caused by the new footprint receipt in this run:** no commit has `footprint_egress=true`; gen122 and recovery gen123 both explicitly log false. This run cannot validate the earlier timeout's footprint-egress repair either.
- **Not merely a sampling/analytic-oracle dispute:** both static-PCD and analytic-solid observers detect the episode, with large negative clearances relative to the 0.05 m raw-map resolution. This does not by itself identify sensor/map membership or prove a particular geometric predicate defect.
- **Remaining evidence gap:** the native event's raw-cloud and occupancy arrays are empty and `occupancy_messages=0`. This means those diagnostics were not captured, not that the planner's internal cloud/map was empty. Scalar frame/map commits cannot show that this cylinder's relevant surface returns were occupied in the exact queried snapshot.
- **No causal ON/OFF conclusion:** the profiled ON G1 Adaptive triplet had zero contacts in 61.30 s; this OFF triplet had one in 59.72 s. One run of each cannot identify profiling as the cause, establish a failure rate, or demonstrate repeatability.

The whole-flight maximum pose step is 0.212321638 m at sample5787 / header1790417150.490313911 (elapsed57.874712 s), with 10.040040 ms header interval and positive clearance0.677391625 m. It is about 18.45 s after contact entry, near gen209 admission, and is **not** the contact-entry step. This audit does not classify that separate discontinuity; do not extend the local smooth-entry finding into a claim that all handoffs or command dispatches in the flight are continuous.

## Decision and bounded next evidence

Keep this attempt in the failure record and do not promote the repair revision. The next diagnostic, if separately authorized by the coordinating agent, should join sensor returns, exact map version/occupied-cell membership, current generation122-style backup samples, and body geometry around a reproduced contact. Include the retained-path guard as well as replacement candidates and the stationary fallback. Preserve all received samples and current contact definitions; do not alter a safety threshold simply to pass this run.
