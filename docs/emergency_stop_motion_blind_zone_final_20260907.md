# EMER_STOP, motion-source, and blind-zone campaign closure

Date: 2026-09-07 (Asia/Seoul)

## Outcome

The correctly deployed guard build completed the prospective Map1--10,
Full/Sector/Adaptive, n=10 campaign with 300/300 unique, protocol-valid,
first-attempt completions.  Full and Adaptive had zero source-static-PCD
contacts.  Sector had one authoritative source contact on Map9 run 3 while
still completing the loop.  Thus the result meets the engineering target for
Full and Adaptive and contains one paired Sector-contact/Adaptive-no-contact
observation; it does not show a Sector completion-rate loss.

The separately frozen v6 side-entry blind-zone experiment delivered a valid
late obstacle in all 27 confirmatory rows, but all three modes completed 9/9
without source or synthetic-cylinder contact.  It therefore validates common
treatment delivery and the compute/communication measurements, but it does
not establish a side-entry collision-rate advantage for Adaptive.

## Corrected defects

1. Guard-enabled `EMER_STOP` can no longer publish an ordinary trajectory
   command while the certified emergency brake is inactive.  Guard-disabled
   legacy behavior remains explicit in a pure publication policy.
2. ROG now keeps a separately timestamped odometry twist.  Brake initialization
   accepts direct twist only when a same-generation finite pose delta agrees
   under the scale-aware limit
   `min(configured, max(0.25, 0.10 * max(|twist|, |pose|)))`.
3. A pose speed at or below 0.05 m/s conflicting with a twist above 0.05 m/s
   rejects the twist and falls back to the pose difference.  The independent
   0.25 s / 0.03 m stationary certificate is still required.
4. The v5/v6 side-entry trigger uses three consecutive qualifying callbacks,
   resetting on every gate failure.  Required and observed counts are written
   into the event and independently validated.
5. Campaign teardown now runs `fastdds shm clean`, which removes only zombie
   Fast DDS IPC segments after participant exit.

An earlier build was accidentally installed below
`/root/super_ws/src/SUPER/install` while the campaign sourced
`/root/super_ws/install`.  Its 300-row result is retained only as deployment
audit evidence.  All results below use the binary rebuilt from
`/root/super_ws` and sourced from `/root/super_ws/install`.

## Correct-deployment 300-run result

Each cell is `completions / source-contact runs / mean time`.  Adaptive opens
are effective Full-open transitions over ten runs.

| Map | Full | Sector | Adaptive | Adaptive opens |
|---|---:|---:|---:|---:|
| Map1 | 10/10 / 0 / 61.10 s | 10/10 / 0 / 60.16 s | 10/10 / 0 / 59.48 s | 203 |
| Map2 | 10/10 / 0 / 54.40 s | 10/10 / 0 / 53.80 s | 10/10 / 0 / 53.94 s | 218 |
| Map3 | 10/10 / 0 / 55.80 s | 10/10 / 0 / 54.37 s | 10/10 / 0 / 54.78 s | 226 |
| Map4 | 10/10 / 0 / 60.55 s | 10/10 / 0 / 60.90 s | 10/10 / 0 / 58.52 s | 180 |
| Map5 | 10/10 / 0 / 57.99 s | 10/10 / 0 / 56.88 s | 10/10 / 0 / 57.92 s | 226 |
| Map6 | 10/10 / 0 / 62.89 s | 10/10 / 0 / 61.42 s | 10/10 / 0 / 61.04 s | 208 |
| Map7 | 10/10 / 0 / 65.62 s | 10/10 / 0 / 62.52 s | 10/10 / 0 / 63.49 s | 212 |
| Map8 | 10/10 / 0 / 61.27 s | 10/10 / 0 / 62.01 s | 10/10 / 0 / 60.21 s | 217 |
| Map9 | 10/10 / 0 / 72.04 s | 10/10 / 1 / 73.05 s | 10/10 / 0 / 72.67 s | 198 |
| Map10 | 10/10 / 0 / 70.99 s | 10/10 / 0 / 68.12 s | 10/10 / 0 / 69.72 s | 180 |

The Map9 run 3 Sector contact began at 34.1248 s near
`(-22.107, -12.743, 1.132)` at 6.985 m/s.  Minimum centre-to-source-point
distance reached 0.0059 m, or -0.1941 m clearance for the 0.20 m vehicle
sphere.  The row was resource-valid, first-attempt, completed in 64.29 s and
had no Adaptive opening because it was the fixed Sector treatment.  Its paired
Adaptive row completed without contact in 69.08 s, had +0.274 m minimum source
clearance, and made 16 effective Full opens including six trajectory-guard
opens.  Full also completed without contact.

| Metric, all 100 runs/mode | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| Mean mission time (s) | 62.264 | 61.324 | 61.179 | 1.743% lower | 0.236% lower |
| Planner ingress (MiB/s) | 9.577 | 2.749 | 2.189 | 77.139% lower | 20.352% lower |
| Map compute (ms/frame) | 32.574 | 9.317 | 19.780 | 39.276% lower | 112.300% higher |
| Algorithm mean cores | 1.462 | 1.029 | 1.036 | 29.136% lower | 0.681% higher |
| End-to-end mean cores | 1.508 | 1.273 | 1.316 | 12.751% lower | 3.364% higher |
| End-to-end core-seconds | 96.712 | 80.102 | 82.739 | 14.448% lower | 3.292% higher |
| Peak end-to-end PSS (MiB) | 3502.784 | 3442.680 | 3494.050 | 0.249% lower | 1.492% higher |

Adaptive made 2,068 effective Full-open transitions and 397 trajectory-guard
opens over 100 runs.  The objective computation claim is therefore relative
to Full: Adaptive reduces ingress, map work and common end-to-end CPU.  It is
not cheaper than fixed Sector in map work or total CPU.

The deployed-log audit parsed 7,372 brake-motion records from 300 distinct
attempt logs.  Of 1,160 cases in which pose speed was at most 0.05 m/s while
twist exceeded 0.05 m/s, zero selected `odom_twist`; zero accepted odometry
twists had a discontinuous trajectory generation.  Command-publication and
motion-source coverage contains 12 named GTest cases; the package-level
`colcon test-result` reports 14 passing test entries in total.

## Blind-zone experiment chronology and result

V4 post-deployment design collection completed all 27 missions but produced
only 26 valid events.  Map10 Full run 1 never met the mode-dependent
yaw/velocity mismatch gate.  One unrelated Map10 run 3 Sector source contact
occurred near `(5.75, 5.75)` before the synthetic obstacle appeared.  The
incomplete v4 cohort was not used for location selection.

V5 retained `(22.5, 23.0)`, made yaw/velocity mismatch diagnostic, and required
three consecutive body-outside samples.  Its Map7 n=1 gate passed 3/3 and its
design cohort passed 27/27 events and completions with zero contacts.  The
predeclared selector evaluated 0.05 m lattice candidates, preserved at least
+0.10 m proxy clearance for every Full and Adaptive trajectory, and selected
the v6 centre `(22.50, 22.95)` from 13 feasible candidates.

The frozen v6 confirmatory result is:

| Map | Mode | complete | source contacts | side-entry contacts | mean/min side clearance (m) | mean time (s) | ingress (MiB/s) | algorithm/E2E cores | effective/TG opens |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Map7 | Full | 3/3 | 0 | 0 | 0.546/0.495 | 74.00 | 11.456 | 1.577/1.626 | 0/0 |
| Map7 | Sector | 3/3 | 0 | 0 | 0.622/0.451 | 76.02 | 3.661 | 1.037/1.294 | 0/0 |
| Map7 | Adaptive | 3/3 | 0 | 0 | 0.551/0.402 | 70.10 | 3.142 | 1.080/1.391 | 62/19 |
| Map9 | Full | 3/3 | 0 | 0 | 0.460/0.451 | 92.55 | 12.996 | 1.514/1.563 | 0/0 |
| Map9 | Sector | 3/3 | 0 | 0 | 0.406/0.269 | 78.72 | 4.540 | 1.046/1.302 | 0/0 |
| Map9 | Adaptive | 3/3 | 0 | 0 | 0.425/0.349 | 77.01 | 3.692 | 1.078/1.395 | 56/22 |
| Map10 | Full | 3/3 | 0 | 0 | 0.453/0.412 | 74.05 | 13.054 | 1.620/1.670 | 0/0 |
| Map10 | Sector | 3/3 | 0 | 0 | 0.350/0.214 | 76.55 | 4.227 | 1.042/1.300 | 0/0 |
| Map10 | Adaptive | 3/3 | 0 | 0 | 0.405/0.327 | 79.90 | 3.653 | 1.049/1.361 | 72/21 |

Across nine runs/mode, Adaptive versus Full reduced ingress 72.041%, map
compute 39.030%, algorithm mean cores 31.909% and end-to-end mean cores
14.666%.  Against Sector it reduced ingress 15.626% but increased map compute
123.793%, algorithm cores 2.667% and end-to-end cores 6.426%.  Adaptive made
190 effective and 62 trajectory-guard opens.  Mean side-entry clearance was
0.486/0.460/0.461 m for Full/Sector/Adaptive: Adaptive was only +0.001 m above
Sector in aggregate.  With zero completion or contact discordances, no
success-rate advantage or McNemar result is claimed.

## Resource audit

The final 300-run campaign had zero resource abort, retry, OOM kill, campaign
process swap or memory PSI.  Minimum host available memory was 4032 MiB; the
runtime floor was 2048 MiB.  Host swap nevertheless reached 2047.97 MiB while
every end-to-end process group reported 0 MiB swap, so the swapped pages were
outside the measured campaign processes.

Before the blind-zone design run, preflight correctly timed out before
launching a row at 8004.8 MiB available.  Inspection found 7,675 unowned
`/dev/shm/fastrtps_*` files consuming about 2 GiB from repeated terminated
campaigns.  No process held them.  Removing those zombie IPC files restored
about 9.5 GiB available memory and the unchanged 8 GiB preflight passed.  The
runner now invokes the vendor `fastdds shm clean` command after process
termination so only zombie ports/segments are reclaimed.  Saturated host swap
does not immediately empty when memory is freed; PSI and per-process swap are
the relevant evidence that no active campaign was thrashing.

## Evidence and limitations

Primary compact evidence:

- `results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_raw_20260905.csv`
- `results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_{summary,reductions}.csv`
- `results/allmaps_stationary_conflict_deployed_resource_guard_three_mode_n10_motion_audit_20260907.json`
- `results/side_entry_v6_center_selection_20260907.json`
- `results/side_entry_v6_confirmatory_maps7_9_10_three_mode_n3_{raw,summary,reductions}.csv`
- `results/side_entry_v6_confirmatory_maps7_9_10_three_mode_n3_validation_20260907.json`

The large per-run artifact directories remain local.  Zero failures in 100
Full or Adaptive runs gives an exact two-sided 95% success-rate lower bound of
about 96.38%, not a population-level 100% guarantee.  These are simulation
results on the tuned Map1--10 family.  No new-map generalization, PX4/Gazebo
dynamics, sensor delay/dropout/noise, real LiDAR replay, or real-flight safety
claim is made.

## Post-closure v7 exploratory stress

A later preregistered Map9 trajectory-intersection smoke increased the
side-entry cylinder radius to 0.50 m at the reproducibly selected centre
`(22.50, 23.05)`.  Full/Sector/Adaptive each completed one first-attempt valid
run with zero source or synthetic contact; minimum synthetic clearance was
+0.305/+0.237/+0.199 m.  Because Sector did not degrade and Adaptive passed
closest, the frozen expansion gate failed and the remaining candidates were
not run.  Details and the explicit stop rule are in
`docs/blind_zone_v7_stress_preregistration_20260907.md`.
