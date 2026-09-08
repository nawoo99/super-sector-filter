# Wide-bypass static blind-corner supplemental result

Date: 2026-09-08 (Asia/Seoul)

## Outcome

The separately preregistered supplemental campaign completed all 150 scheduled
rows in 174.3 minutes. Full, fixed 45-degree Sector and Adaptive each completed
50/50 missions with zero authoritative source-PCD contact. All 150 rows were
unique, first-attempt and run/resource/speed/performance/cgroup-valid. There
was no retry, resource abort, infrastructure failure or OOM.

The frozen decision is `SUPPLEMENT_COMPLETE_NO_SAFETY_SEPARATION`. The
measurement-validity and protected Full/Adaptive gates passed, but the physical
delivery and both safety-separation routes failed. This is useful supplemental
evidence that the frozen planner remains reliable on five new blind-corner
maps and that Adaptive retains substantial Full-relative compute and ingress
savings. It does **not** show an Adaptive collision-rate advantage over Sector:
Sector also completed all 50 rows without contact, so no McNemar test was
performed.

## Experimental role and integrity

This campaign is not pooled with the existing Map1--10 development/repeated-run
cohort or either previous static-occlusion pilot. The deployed planner, v=7
dynamics, Full policy, 45-degree Sector crop, Adaptive policy and C++ frontend
were frozen. The one-per-cell smoke is also separate from the reported n=10.

The five maps use source layouts 1, 3, 5, 7 and 9, one from each background
radius stratum. Cylinders whose surfaces were within 2.0 m of the common
loop24 polyline were removed so an unrelated inherited bottleneck could not
dominate the test. Every map then received the same solid L-shaped blind
corner and hazard cylinder, while the surrounding point-load stratum remained
different:

- free channel half-width 2.50 m, wall thickness 0.30 m, wall height 3.20 m;
- hazard centre `(18.4,24.0) m`, radius 0.95 m, height 3.20 m;
- validated nearest hazard edge 55.008 degrees from velocity at the reference
  reveal, 10.008 degrees outside the fixed 45-degree Sector crop;
- validated reference northern-bypass body clearance +0.575 m;
- PCD sizes 319,001; 480,107; 619,367; 756,647; and 880,067 points.

Two earlier smoke-only map versions remain preserved as negative design
evidence. `occ_b` retained an unrelated stochastic seed-7 bottleneck, and
`occ_bc` left only +0.21--0.24 m analytic bypass clearance. Neither started an
n=10 campaign, and neither is pooled here. The final `occ_bw` family and its
execution rule were frozen before its first flight.

## Per-map safety and liveness

Every cell contains ten runs. Clearance is vehicle-body surface clearance from
the authoritative static source PCD; hazard clearance is independently
computed against the inserted analytic cylinder. `Effective/TG` is the total
Adaptive effective-Full transitions and trajectory-guard-specific openings.

| Map (tier) | Mode | Complete | Contact runs/events | Mean time | Global clearance median / min | Hazard clearance median / min | Adaptive Effective/TG |
|---|---|---:|---:|---:|---:|---:|---:|
| occ_bw_r1 (1) | Full | 10/10 | 0/0 | 54.423 s | +0.443 / +0.394 m | +0.445 / +0.391 m | -- |
|  | Sector | 10/10 | 0/0 | 55.171 s | +0.369 / +0.263 m | +0.474 / +0.262 m | -- |
|  | Adaptive | 10/10 | 0/0 | 54.234 s | +0.394 / +0.184 m | +0.502 / +0.183 m | 218 / 7 |
| occ_bw_r2 (2) | Full | 10/10 | 0/0 | 54.446 s | +0.449 / +0.352 m | +0.458 / +0.368 m | -- |
|  | Sector | 10/10 | 0/0 | 55.288 s | +0.383 / +0.303 m | +0.428 / +0.310 m | -- |
|  | Adaptive | 10/10 | 0/0 | 54.611 s | +0.428 / +0.350 m | +0.477 / +0.417 m | 221 / 9 |
| occ_bw_r3 (3) | Full | 10/10 | 0/0 | 54.543 s | +0.441 / +0.352 m | +0.468 / +0.356 m | -- |
|  | Sector | 10/10 | 0/0 | 54.325 s | +0.327 / +0.256 m | +0.451 / +0.280 m | -- |
|  | Adaptive | 10/10 | 0/0 | 54.656 s | +0.368 / +0.337 m | +0.424 / +0.337 m | 229 / 4 |
| occ_bw_r4 (4) | Full | 10/10 | 0/0 | 55.374 s | +0.432 / +0.376 m | +0.487 / +0.375 m | -- |
|  | Sector | 10/10 | 0/0 | 53.351 s | +0.398 / +0.283 m | +0.495 / +0.354 m | -- |
|  | Adaptive | 10/10 | 0/0 | 55.393 s | +0.393 / +0.307 m | +0.528 / +0.362 m | 227 / 6 |
| occ_bw_r5 (5) | Full | 10/10 | 0/0 | 55.189 s | +0.436 / +0.288 m | +0.442 / +0.288 m | -- |
|  | Sector | 10/10 | 0/0 | 54.577 s | +0.416 / +0.227 m | +0.482 / +0.368 m | -- |
|  | Adaptive | 10/10 | 0/0 | 54.474 s | +0.400 / +0.357 m | +0.479 / +0.362 m | 224 / 4 |
| **Pooled** | **Full** | **50/50** | **0/0** | **54.795 s** | **+0.441 / +0.288 m** | **+0.458 / +0.288 m** | **--** |
|  | **Sector** | **50/50** | **0/0** | **54.542 s** | **+0.391 / +0.227 m** | **+0.461 / +0.262 m** | **--** |
|  | **Adaptive** | **50/50** | **0/0** | **54.674 s** | **+0.400 / +0.184 m** | **+0.477 / +0.183 m** | **1,119 / 30** |

Full and Adaptive therefore meet the requested observed 100% completion and
zero-contact condition on this finite supplemental cohort. This is not a
population-level 100% guarantee: the five maps are environments and the ten
repetitions within a map are clustered execution samples.

One Adaptive row, `occ_bw_r1` run 10, had +0.184 m global and +0.183 m hazard
clearance. It remained contact-free, but it is the only row below the +0.20 m
descriptive clearance threshold. Full and Sector had zero such rows. The
campaign was not tuned or restarted after observing it.

## Adaptive delivery and safety-separation gates

| Map | Filtered probes | Pooled first-distance median | Sector centre outside crop | Adaptive TG-active runs | Paired median Adaptive-Sector hazard clearance |
|---|---:|---:|---:|---:|---:|
| occ_bw_r1 | 20/20 | 4.441 m | 10/10 | 7/10 | +0.083 m |
| occ_bw_r2 | 20/20 | 4.377 m | 10/10 | 9/10 | +0.090 m |
| occ_bw_r3 | 20/20 | 4.438 m | 10/10 | 4/10 | -0.008 m |
| occ_bw_r4 | 20/20 | 4.382 m | 10/10 | 6/10 | +0.052 m |
| occ_bw_r5 | 20/20 | 4.377 m | 10/10 | 4/10 | +0.028 m |

The geometry/probe portions of delivery worked: all 100 filtered probes were
valid, every map's median first-observation distance was inside the frozen
`[2.5,5.5] m` interval, and Sector first saw the hazard centre outside the
45-degree crop in 50/50 rows. The full physical-delivery gate also required
trajectory-guard activity in at least 8/10 Adaptive rows on every map. Only
tier 2 reached that threshold, so the gate failed.

Adaptive nevertheless entered effective Full mode in every run: 1,119 total
transitions, or 22.38 per run. These transitions were dominated by 1,136
replan-guard opening requests; the legacy stall trigger opened zero times and
the trajectory guard opened 30 times. Counts overlap while a guard is already
open, so the request totals need not equal the effective transition total.

All modes were safe, yielding zero desired Sector-bad/Adaptive-safe and zero
reverse binary discordances. The clearance route improved in 4/5 maps, but
the median of the five paired map advantages was only +0.0515 m, below the
frozen +0.10 m requirement. Both separation routes therefore failed, and the
all-zero binary table does not support a useful McNemar test.

Within Adaptive, the 30 TG-active rows had median hazard clearance +0.562 m,
versus +0.416 m in the 20 TG-inactive rows. This is a descriptive association,
not a causal estimate: guard activation was determined by the evolving path
and risk state rather than randomized.

## Why Sector also remained safe

The inserted cylinder was initially outside Sector's angular crop, but the
solid L walls that formed the blind corner were themselves visible. Sector
could route around those walls before its current trajectory intersected the
hidden cylinder. The final map version also deliberately provided +0.575 m
analytic body clearance on the northern bypass so that Full would be robust;
that same feasible route was available to all three modes. By the approximately
4.4 m median raw reveal, many executions were already following a wall-induced
bypass.

This explains the combined observations: Sector safely handled all rows,
Adaptive's trajectory guard produced no occupied verdict in its 20 inactive
rows, and the much more frequent replan guard still opened Full view elsewhere
on the loop. The test is therefore a valid blind-corner reliability/efficiency
supplement, but it did not force the policy-dependent trajectory conflict
needed to separate collision outcomes.

## Computation and communication

The common `simulator+frontend+planner+mission` cgroup is the valid
Full-versus-filtered CPU boundary. Algorithm-only Full-versus-filtered CPU is
not compared because Full includes the simulator in that narrower scope while
Sector/Adaptive are planner-only.

| Map | Map compute ms/frame F / S / A | Adaptive reduction vs Full | Planner ingress MiB/s F / S / A | Adaptive reduction vs Full | E2E mean cores F / S / A | Adaptive reduction vs Full |
|---|---:|---:|---:|---:|---:|---:|
| occ_bw_r1 | 36.702 / 9.570 / 17.640 | 51.94% | 4.469 / 0.885 / 0.778 | 82.60% | 1.614 / 1.330 / 1.374 | 14.84% |
| occ_bw_r2 | 44.265 / 11.409 / 20.061 | 54.68% | 5.392 / 1.072 / 0.943 | 82.52% | 1.712 / 1.343 / 1.382 | 19.26% |
| occ_bw_r3 | 49.983 / 12.456 / 21.583 | 56.82% | 5.863 / 1.066 / 0.902 | 84.62% | 1.767 / 1.360 / 1.399 | 20.80% |
| occ_bw_r4 | 56.613 / 13.922 / 23.304 | 58.84% | 6.468 / 1.154 / 0.964 | 85.09% | 1.850 / 1.388 / 1.411 | 23.73% |
| occ_bw_r5 | 56.384 / 13.754 / 23.387 | 58.52% | 6.735 / 1.185 / 1.002 | 85.13% | 1.834 / 1.388 / 1.407 | 23.29% |
| **Pooled** | **48.789 / 12.222 / 21.195** | **56.56%** | **5.785 / 1.073 / 0.918** | **84.14%** | **1.755 / 1.362 / 1.395** | **20.54%** |

| Pooled metric, 50 rows/mode | Full | Sector | Adaptive | Sector vs Full | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|---:|
| Mission time (s) | 54.795 | 54.542 | 54.674 | 0.46% lower | 0.22% lower | 0.24% higher |
| Map compute (ms/frame) | 48.789 | 12.222 | 21.195 | 74.95% lower | 56.56% lower | 73.41% higher |
| End-to-end mean cores | 1.755 | 1.362 | 1.395 | 22.40% lower | 20.54% lower | 2.40% higher |
| End-to-end core-seconds | 99.595 | 76.614 | 78.774 | 23.07% lower | 20.91% lower | 2.82% higher |
| End-to-end p95 cores | 2.020 | 1.549 | 1.617 | 23.30% lower | 19.98% lower | 4.34% higher |
| End-to-end peak PSS (MiB) | 3460.1 | 3434.7 | 3467.4 | 0.74% lower | 0.21% higher | 0.95% higher |
| Planner ingress (MiB/s) | 5.785 | 1.073 | 0.918 | 81.46% lower | 84.14% lower | 14.45% lower |

Adaptive preserved mission-time parity while cutting Full-relative map work,
common CPU and logical planner ingress. It used more map compute and common CPU
than fixed Sector, as expected for risk evaluation and Full-view recovery.
Peak PSS was essentially unchanged and 0.21% higher than Full, so no memory
saving is claimed.

The minimum available host memory was 4,950.52 MiB and memory PSI some/full
avg10 stayed 0/0. The host already showed about 2,048 MiB swap used, but
algorithm, common end-to-end and FSM process scopes each recorded zero swap.
No campaign retry, abort or OOM occurred. Thus the persistent host swap value
did not confound these rows.

## Interpretation and next step

No planner change is justified by this supplemental campaign: Full and
Adaptive achieved the requested finite-cohort completion/contact outcome, and
the map was intentionally an out-of-sample check rather than another tuning
set. The result supports the existing efficiency claim and broadens static-map
reliability evidence.

For a future safety-superiority claim, changing the planner again is not the
first step. A separately versioned mechanism map must make the hidden object,
not merely the visible wall, determine the critical path. It should preserve a
Full/Adaptive escape while preventing fixed Sector from selecting the same
wide bypass before reveal. That design must first pass a small preregistered
delivery pilot. The current 150 rows must remain untouched and must not be
relabelled as such a confirmatory safety experiment.

## Evidence

- Preregistration and smoke outcome:
  `docs/static_blind_corner_wide_supplement_preregistration_20260908.md`
- Raw reported rows:
  `results/static_blind_corner_wide_three_mode_n10_raw_20260908.csv`
- Strict validation:
  `results/static_blind_corner_wide_three_mode_n10_validation.json`
- Summary and reductions:
  `results/static_blind_corner_wide_three_mode_n10_{summary,reductions}.csv`
- Per-map and paired tables:
  `results/static_blind_corner_wide_three_mode_n10_{map_table,pair_table}.csv`
- Frozen decision:
  `results/static_blind_corner_wide_three_mode_n10_gate.json`
- Reproducible geometry:
  `scripts/native_campaign/gen_static_blind_corner_supplement.py`,
  `validate_static_blind_corner_supplement.py` and
  `static_blind_corner_supplement_manifest.json`

The analysis-only field-alias defect discovered after the run was fixed and
covered by a regression assertion. It had left resource cells blank in the
specialized map table; it did not affect raw collection, strict validation or
the generic resource summary. The preregistered analyzer hash is retained in
the preregistration, and the post-fix analyzer hash is recorded below.

SHA-256 checksums for raw, summary, reductions, strict validation, map table,
pair table and gate decision, in that order:

```text
5b1cb75adf26141171358fe18543cc2e6723db43002e8495af417dfa3fde171f
3f77a9e55c4f7d743498b0affad9aa34624a8f8de1605ebe337b8a28e094c0f8
1d5950647f6275e1ed6f9e9d3303231fde8b18aea3218e76959e203df00367e1
3e6594a84802556006dddcfd4fa11ece0789733ae04b6f4dc8abbc8e2896dc01
0e1c45c9940d5edab5a9db59c82d16dc69912f17778c84b205ac55c57dbbb00f
cf595a88c14fa43d0e22ee04ca1e65fdd215b4c4c7b15bd39c422807d0ed8e40
766501d2825d452aedc618671f7d82aa1a8f7c314596218157b59ce10712997d
```

Post-fix analyzer SHA-256:

```text
7024e02240f2f409af56abec6a01f8424a99ff0afb2f3b53594eca0792a2eab4
```
