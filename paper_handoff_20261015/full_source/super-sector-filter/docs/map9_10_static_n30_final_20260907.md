# Map9--10 static three-mode n=30 final report

Date: 2026-09-07 (Asia/Seoul)

## Outcome

The preregistered Map9--10 repeated-run campaign completed all 180 scheduled
rows in about 287 minutes. Full and Adaptive each completed 60/60 missions
with zero authoritative static-PCD contacts. The protected-mode stop, repair
and full-restart rule was therefore never triggered. No planner or profile
parameter was changed during the cohort.

Sector completed 59/60 missions with zero contact. Map10 run 30 reached only
3/5 waypoints before the 180.01 s mission timeout. It remained safely clear of
the source PCD and was a liveness failure, not a collision or infrastructure
failure. Sector failure was explicitly non-stopping in the preregistration.

## Protocol integrity

- Scheduled/observed/unique rows: 180/180/180.
- Every row used exactly one attempt. There were zero retries, resource
  aborts, infrastructure failures and OOM kills.
- All 180 rows were run-, resource-, speed- and performance-valid. The strict
  campaign summarizer passed with no missing, duplicate, unexpected, quality
  or CPU-scope rows.
- Mode-order rotation was exactly balanced: for each map, every mode occupied
  positions 1, 2 and 3 ten times each.
- The authoritative safety endpoint was the unfiltered source PCD with a
  0.20 m vehicle sphere. The legacy live-cloud `collisions` field was not used.
- The pre-run config and runner hashes still match the preregistration.

The motion-source audit found all 180 attempt logs and parsed 9,503 brake
motion records. None of 1,359 stationary-pose/nonzero-twist conflicts selected
`odom_twist`, and no accepted odometry twist crossed a discontinuous
trajectory generation. Its aggregate status is `FAIL` only because that audit
also treats the one Sector mission timeout as a quality failure; both motion
policy violation counters and the Full/Adaptive contact-violation counter are
zero.

## Per-map mission and safety results

Time is the all-row mean plus sample standard deviation. Clearance is mean /
minimum distance outside the 0.20 m body sphere.

| Map | Mode | Complete | Static-PCD contact runs | Time (s) | Clearance mean/min (m) | First-attempt protocol-valid |
|---|---|---:|---:|---:|---:|---:|
| Map9 | Full | 30/30 (100%) | 0/30 | 81.49 +/- 8.92 | +0.239 / +0.177 | 30/30 |
| Map9 | Sector | 30/30 (100%) | 0/30 | 77.89 +/- 5.86 | +0.242 / +0.187 | 30/30 |
| Map9 | Adaptive | 30/30 (100%) | 0/30 | 76.79 +/- 4.32 | +0.237 / +0.179 | 30/30 |
| Map10 | Full | 30/30 (100%) | 0/30 | 82.03 +/- 8.93 | +0.230 / +0.180 | 30/30 |
| Map10 | Sector | 29/30 (96.67%) | 0/30 | 82.73 +/- 19.82 | +0.247 / +0.153 | 30/30 |
| Map10 | Adaptive | 30/30 (100%) | 0/30 | 81.22 +/- 6.02 | +0.239 / +0.177 | 30/30 |
| Map9--10 | Full | 60/60 (100%) | 0/60 | 81.76 +/- 8.85 | +0.235 / +0.177 | 60/60 |
| Map9--10 | Sector | 59/60 (98.33%) | 0/60 | 80.31 +/- 14.70 | +0.245 / +0.153 | 60/60 |
| Map9--10 | Adaptive | 60/60 (100%) | 0/60 | 79.01 +/- 5.66 | +0.238 / +0.177 | 60/60 |

The Map10 Sector all-row mean includes the 180.01 s timeout. Its mean among
the 29 successful rows is 79.37 s. A completed mission may still come closer
than 0.20 m clearance without contact under the declared 0.20 m sphere; those
counts were 6/7/7 for Full/Sector/Adaptive across both maps.

At the run level, 60/60 completion gives a two-sided exact 95% success-rate
interval of approximately 94.04--100%. Zero contacts in 60 runs gives a
two-sided exact 95% contact-rate interval of approximately 0--5.96%. These
conditional repeated-run intervals are not a population-level guarantee and
the 60 executions cover only two selected maps. Since Sector also had zero
contacts, this cohort provides no collision-rate superiority result for
Adaptive. The single completion discordance is descriptive and is not enough
for a mode-superiority claim.

## Adaptive activation

`effective Full open` counts every transition in which the frontend's
effective output becomes Full. `trajectory-guard open` is the trajectory-risk
subset of those transitions.

| Map | Runs | Effective Full opens total/mean | Trajectory-guard opens total/mean | Guard-open duty mean | Guard-active duty mean |
|---|---:|---:|---:|---:|---:|
| Map9 | 30 | 659 / 21.97 | 219 / 7.30 | 48.49% | 21.49% |
| Map10 | 30 | 647 / 21.57 | 243 / 8.10 | 53.22% | 23.02% |
| Map9--10 | 60 | 1,306 / 21.77 | 462 / 7.70 | 50.86% | 22.26% |

The Adaptive frontend published at a measured mean 5.46 Hz from a 10.00 Hz
sensor stream. The repeated openings are therefore real policy activity, not
an always-Sector run mislabeled as Adaptive.

## Computation and communication

The common end-to-end cgroup is the valid CPU comparison across all three
modes. One core equals 100% of one logical CPU, so 1.623 cores means 162.3%
on the usual per-process percentage scale and is not an impossible value.
Algorithm-only CPU is shown for transparency but Full includes a different
process scope from filtered modes, so Full-versus-filtered reductions are not
claimed from that row.

| Metric, pooled 60 runs/mode | Full | Sector | Adaptive | Sector vs Full | Adaptive vs Full |
|---|---:|---:|---:|---:|---:|
| Mission time, all rows (s) | 81.762 | 80.309 | 79.009 | 1.777% lower | 3.366% lower |
| Planner ingress (MiB/s) | 13.374 | 4.351 | 3.443 | 67.466% lower | 74.256% lower |
| Map compute (ms/frame) | 43.060 | 11.893 | 27.361 | 72.380% lower | 36.458% lower |
| Algorithm mean cores, non-common scope | 1.563 | 1.024 | 1.066 | not comparable | not comparable |
| End-to-end mean cores | 1.623 | 1.296 | 1.395 | 20.164% lower | 14.029% lower |
| End-to-end core-seconds | 135.921 | 105.678 | 112.895 | 22.251% lower | 16.941% lower |
| End-to-end p95 cores, 1 s bins | 1.924 | 1.557 | 1.672 | 19.099% lower | 13.093% lower |
| End-to-end peak PSS (MiB) | 3545.1 | 3575.2 | 3618.4 | 0.847% higher | 2.066% higher |

Adaptive versus Full reductions are consistent on both maps:

| Map | Ingress | Map compute/frame | End-to-end mean cores | End-to-end core-seconds | Mission time |
|---|---:|---:|---:|---:|---:|
| Map9 | 73.982% | 35.831% | 12.482% | 17.406% | 5.765% |
| Map10 | 74.540% | 37.066% | 15.554% | 16.486% | 0.984% |

Adaptive is intentionally more expensive than fixed Sector: pooled map work
is 130.06% higher and end-to-end mean cores are 7.68% higher than Sector.
Peak PSS is also slightly higher than Full, so no memory-reduction claim is
supported. The defensible computation claim is lower bandwidth, map work and
common end-to-end CPU than Full while retaining Full's observed completion and
contact outcomes on this cohort.

## Map10 Sector run-30 forensic analysis

The failed row was first-attempt and run/resource/speed/performance-valid. It
had no collision, +0.226 m minimum static clearance, zero resource abort,
zero OOM, zero measured campaign-process swap and zero memory PSI. It ended at
`(-23.975, -23.975, 1.525)`, 0.123 m from that waypoint, and the next
`(24.025, -23.975, 1.525)` goal had only just been issued near the timeout.

| Liveness indicator | Failed run 30 | Other 29 runs median | Other 29 range |
|---|---:|---:|---:|
| Mission time (s) | 180.010 | 77.350 | 68.230--97.120 |
| Recovery-active total (s) | 132.692 | 14.909 | 3.586--30.953 |
| Longest recovery episode (s) | 115.321 | 4.222 | 0.562--14.884 |
| Topology reroute arms | 69 | 9 | 3--16 |
| Topology reroute searches | 195 | 12 | 3--42 |
| Certified local-escape commits | 4 | 0 | 0--1 |
| Trajectory commit rate (Hz) | 0.600 | 2.077 | 1.695--2.523 |

The attempt log contains 199 `GeneratePolytopeFromLine` failures, 93
clearance-margin trajectory rejections, 14 expansion/backup optimizer failure
messages, ten infeasible-CIRI warnings, 69 reroute-arm events and four
certified local escapes. These agree with the counters and show a prolonged
safe stop/reroute loop caused by the fixed 45-degree Sector observation losing
a usable corridor/topology branch. This is the supported proximate cause; the
data do not prove that any one optimizer call is the unique root cause.

No Sector tuning was performed. Changing the fixed ablation after observing
this result would invalidate the frozen cohort, and the user's restart rule
covered Full or Adaptive failures, neither of which occurred. A future
Sector-liveness change, if desired, should be a separately versioned
engineering experiment rather than a replacement of this observation.

## Resource result

The minimum host available memory was 5,481.99 MiB and maximum memory PSI
some/full avg10 was 0/0. The host swap-used counter stayed near 2,043 MiB, but
all campaign process groups, the FSM and both algorithm scopes measured zero
swap and there were no OOM, abort or retry events. The nonzero host counter is
therefore persistent external/historical swap, not evidence that this campaign
was thrashing.

## Evidence

- Preregistration: `docs/map9_10_static_n30_preregistration_20260907.md`.
- Raw rows: `results/map9_10_static_three_mode_n30_raw_20260907.csv`.
- Summary: `results/map9_10_static_three_mode_n30_summary.csv`.
- Reductions: `results/map9_10_static_three_mode_n30_reductions.csv`.
- Strict validation: `results/map9_10_static_three_mode_n30_validation.json`.
- Motion audit: `results/map9_10_static_three_mode_n30_motion_audit_20260907.json`.

SHA-256 checksums, in the same order as the five result files above, are:

```text
d4423896eaf7e169ee4cd54b72d0ff779aebb4f1528c619f64ac4b2a3299f6d5
5bd18b96a03a832fe77a0fa9dcddea642f57facec347a4183a2e9d2348109f4e
1c854cfaf46b57001ecbeba28f13ce9438b75e34824cc3e641bd1b53428c7d08
7a4b1808c091d3c7bda7e4fff6a3bf0939c054021bba8ecfef73a2929b18ee2a
df672239dc145f17eb5b50b364ec79c8c92810e6322d39dea924bdbcdf7d54e9
```

The 314 MiB per-attempt artifact directory remains local and is not committed.
It retains the detailed logs and performance traces needed for the Sector
timeout forensic analysis.
