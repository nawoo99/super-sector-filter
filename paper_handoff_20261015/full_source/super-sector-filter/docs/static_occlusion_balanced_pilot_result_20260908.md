# Balanced static-occlusion pilot result

Date: 2026-09-08 (Asia/Seoul)

## Outcome

The preregistered exploratory pilot completed all 30 scheduled rows in about
41 minutes. Full, Sector and Adaptive each completed 10/10 missions with zero
authoritative source-PCD contacts. Every row was first-attempt and passed the
run, resource, speed, performance and cgroup quality checks.

The static wall did deliver physical occlusion: in all five radius strata the
mean first raw-hazard observation progress across Sector and Adaptive was
4.416--9.665 m later in the occluded member than in its paired nominal member.
The experiment nevertheless failed the frozen discrimination gate. There were
no Sector-bad/Adaptive-safe binary discordances, and Adaptive had greater
minimum clearance in only 3/5 occluded strata with a median advantage of
+0.011 m, below the required 4/5 and +0.10 m.

The registered decision is therefore
`STOP_AFTER_PILOT_NO_CONFIRMATORY_EXPANSION`. The proposed independent
80-environment, 240-flight confirmatory campaign was not generated or run.
This is the required outcome of the preregistered stop rule, not an
infrastructure interruption.

## Experimental role and protocol integrity

The old Map1--10 results remain the development and repeated-run reliability
cohort. This pilot is a separate controlled mechanism experiment: five
background-radius strata, with a matched nominal/occluded pair in each
stratum. Both members contain the same common hazard at `(19.50, 24.00) m`;
only the occluded member contains the wall. Pilot outcomes are not pooled with
Map1--10.

The compared systems are complete deployed policies. Full receives the raw
cloud; Sector uses the fixed body-yaw crop; Adaptive uses velocity-yaw crop,
raw-cloud risk checks and bounded Full refresh. The result is therefore a
policy-level comparison, not the isolated causal effect of fallback alone.

- Requested/observed/unique rows: 30/30/30.
- First-attempt and quality-valid rows: 30/30.
- Retry, resource abort, infrastructure failure and OOM: 0.
- Valid measurement-only raw-hazard probes: 20/20 filtered rows.
- Full/Adaptive safe rows: 20/20.
- The deterministic geometry validator passed all wall-clearance and
  line-of-sight checks before flight.

## Per-map mission and safety result

Each cell is `completion / contacts; time; minimum clearance`. Clearance is
the authoritative distance outside the declared 0.20 m vehicle sphere.

| Stratum | Visibility | Full | Sector | Adaptive | Adaptive effective/TG opens |
|---:|---|---|---|---|---:|
| 1 | Nominal | 1/1 / 0; 58.60 s; +0.244 m | 1/1 / 0; 60.91 s; +0.295 m | 1/1 / 0; 58.11 s; +0.249 m | 23 / 3 |
| 1 | Occluded | 1/1 / 0; 59.62 s; +0.293 m | 1/1 / 0; 60.49 s; +0.263 m | 1/1 / 0; 58.31 s; +0.260 m | 24 / 2 |
| 2 | Nominal | 1/1 / 0; 56.07 s; +0.242 m | 1/1 / 0; 58.38 s; +0.388 m | 1/1 / 0; 55.86 s; +0.330 m | 21 / 1 |
| 2 | Occluded | 1/1 / 0; 59.18 s; +0.290 m | 1/1 / 0; 56.59 s; +0.270 m | 1/1 / 0; 57.07 s; +0.222 m | 23 / 1 |
| 3 | Nominal | 1/1 / 0; 60.03 s; +0.189 m | 1/1 / 0; 63.67 s; +0.250 m | 1/1 / 0; 57.90 s; +0.285 m | 22 / 2 |
| 3 | Occluded | 1/1 / 0; 62.19 s; +0.213 m | 1/1 / 0; 63.71 s; +0.284 m | 1/1 / 0; 63.79 s; +0.295 m | 25 / 3 |
| 4 | Nominal | 1/1 / 0; 76.64 s; +0.251 m | 1/1 / 0; 70.35 s; +0.284 m | 1/1 / 0; 69.41 s; +0.273 m | 23 / 4 |
| 4 | Occluded | 1/1 / 0; 68.15 s; +0.267 m | 1/1 / 0; 71.13 s; +0.199 m | 1/1 / 0; 69.29 s; +0.222 m | 19 / 5 |
| 5 | Nominal | 1/1 / 0; 82.24 s; +0.277 m | 1/1 / 0; 80.57 s; +0.265 m | 1/1 / 0; 75.09 s; +0.217 m | 22 / 7 |
| 5 | Occluded | 1/1 / 0; 95.02 s; +0.239 m | 1/1 / 0; 96.67 s; +0.278 m | 1/1 / 0; 82.45 s; +0.295 m | 21 / 7 |

Pooled Full/Sector/Adaptive mean mission times were
67.774/68.247/64.728 s and minimum clearances across all ten rows were
+0.189/+0.199/+0.217 m. These n=1 cells are mechanism-screening observations,
not mode success-rate estimates.

## Frozen mechanism-gate result

Probe progress is `(drone_x + drone_y) / 2` at the first raw point within the
fixed hazard probe. The clearance difference is Adaptive minus Sector on the
occluded map.

| Radius stratum | Nominal progress | Occluded progress | Occlusion delay | Sector clearance | Adaptive clearance | Difference | Adaptive effective/TG opens |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11.469 m | 17.615 m | +6.146 m | +0.263 m | +0.260 m | -0.003 m | 24 / 2 |
| 2 | 11.137 m | 20.802 m | +9.665 m | +0.270 m | +0.222 m | -0.048 m | 23 / 1 |
| 3 | 11.389 m | 20.359 m | +8.971 m | +0.284 m | +0.295 m | +0.011 m | 25 / 3 |
| 4 | 11.002 m | 17.329 m | +6.327 m | +0.199 m | +0.222 m | +0.023 m | 19 / 5 |
| 5 | 11.634 m | 16.051 m | +4.416 m | +0.278 m | +0.295 m | +0.017 m | 21 / 7 |

The validity, protected-mode safety, physical-delivery and no-reverse-
discordance gates passed. Both alternative discrimination routes failed:

- Desired binary discordances: 0; required at least 2, including a Sector
  contact.
- Adaptive-clearance wins: 3/5; required at least 4/5.
- Median Adaptive clearance advantage: +0.011 m; required at least +0.100 m.
- A trajectory-guard opening did occur in every occluded Adaptive row, so the
  negative result was not caused by Adaptive remaining permanently closed.

No McNemar or safety-superiority test is claimed because there was no binary
outcome variation and the confirmatory cohort was not opened.

## Why the treatment did not discriminate the modes

The wall delayed raw observation in aggregate, but it did not impose one
policy-independent pre-event path and reveal point. On the occluded maps, the
hazard centre was outside Sector's crop at first observation in all five
strata. Sector nevertheless completed safely. In strata 4 and 5, Sector first
saw the hazard at progress 13.815 and 12.042 m, while Adaptive first saw it at
20.843 and 20.059 m. Those reversals show that the policies took different
routes around the finite wall and could expose the hazard from a wall edge.

The supported interpretation is:

1. The wall itself is visible static geometry, so both policies can replan or
   deflect before the hidden cylinder is revealed.
2. The construction leaves a broad northern bypass and does not channel all
   policies through a fixed blind-corner release point.
3. The fixed Sector frontend still preserves a speed-dependent near field,
   measured up to about 2.90 m in this campaign. A hazard excluded from the
   angular crop can therefore re-enter observation at short distance or after
   body yaw changes.
4. Adaptive was active--223 effective Full openings and 35 trajectory-guard
   openings over ten rows--but those interventions did not produce a
   meaningful global-clearance or binary-outcome advantage in this geometry.

Items 1--3 explain plausible safe paths and are consistent with the probe and
trajectory outcomes; the current logs do not isolate a unique causal event
for every run. The design error was using a finite visible wall plus open
bypass as if it guaranteed a common reveal geometry.

The probe has no publisher or control output, but it synchronously scans raw
input until the first observation. It therefore cannot be described as having
literally zero timing perturbation. Its cost is included only in the filtered
rows and makes their compute comparison against Full conservative, but a small
path-timing effect cannot be excluded in this n=1 exploratory pilot. A future
confirmatory implementation should collect visibility at the simulator/source
boundary or fold the check into an existing point pass.

A future experiment, if pursued, must be separately versioned. A longer L- or
U-shaped occluding corridor should first standardize the pre-event trajectory
and fixed reveal point while retaining an independently validated collision-
free escape. It must pass a new small pilot before any large confirmatory
campaign. The frozen pilot must not be retuned and relabelled as confirmation.

## Computation and communication

The common end-to-end cgroup is the valid CPU boundary across all modes.
Algorithm-only Full-versus-filtered CPU remains incomparable because Full has
a different process scope.

| Metric, pooled 10 rows/mode | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 67.774 | 68.247 | 64.728 | 4.494% lower | 5.156% lower |
| Planner ingress (MiB/s) | 8.803 | 2.595 | 2.166 | 75.396% lower | 16.528% lower |
| Map compute (ms/frame) | 41.271 | 11.096 | 22.514 | 45.450% lower | 102.892% higher |
| End-to-end mean cores | 1.623 | 1.316 | 1.393 | 14.199% lower | 5.834% higher |
| End-to-end core-seconds | 112.928 | 91.643 | 92.724 | 17.891% lower | 1.179% higher |
| End-to-end p95 cores | 1.916 | 1.538 | 1.627 | 15.093% lower | 5.784% higher |
| End-to-end peak PSS (MiB) | 3487.9 | 3453.0 | 3491.0 | 0.090% higher | 1.102% higher |

The pilot is consistent with the established computation result: Adaptive
uses substantially less ingress, map work and common end-to-end CPU than Full,
while costing more computation than the fixed Sector ablation. Peak PSS did
not improve, so no memory-saving claim is supported.

Minimum host available memory was 5,649.27 MiB and maximum memory PSI
some/full avg10 was 0/0. Algorithm, end-to-end and FSM process swap were zero,
and no retry, abort or OOM occurred. The host's approximately 2,048 MiB
swap-used counter was persistent external/historical state, not campaign
process swapping.

## Evidence

- Preregistration: `docs/static_occlusion_balanced_pilot_preregistration_20260908.md`
- Raw rows: `results/static_occlusion_balanced_pilot_three_mode_n1_raw_20260908.csv`
- Strict validation: `results/static_occlusion_balanced_pilot_three_mode_n1_validation.json`
- Summary/reductions: `results/static_occlusion_balanced_pilot_three_mode_n1_{summary,reductions}.csv`
- Per-map and pair tables: `results/static_occlusion_balanced_pilot_three_mode_n1_{map_table,pair_table}.csv`
- Frozen-gate decision: `results/static_occlusion_balanced_pilot_three_mode_n1_gate.json`
- Reproducible geometry: `scripts/native_campaign/gen_static_occlusion_pilot.py`,
  `validate_static_occlusion_pilot.py` and
  `static_occlusion_pilot_manifest.json`

SHA-256 checksums for raw, summary, reductions, strict validation, map table,
pair table and gate decision, in that order:

```text
d253630ec9abd70363f3e3aea0e0eb1c3eae9e928c77fffc4fc3c02beff82f06
0bb4153696bfa7958c3141c6a7672f2806a849dcbe3a4d23e70ecffadec3eb33
48c25277f9ce9c5dc5d5462ac186452e6a269a22ff8097a0ad60bde490df6a31
78f06b4b414414af8e7649b4e7a9ca5236d3306052380d8417216e11eac7b463
c2ed54149ceba3fb1702084503294e67815095b4680575cddd586c3447d2d430
0b4e11f914ee6f04887eca60a09018cbc0e11b21c62c5fd46fa533c324f85af5
53a1a81c607fc49680f59486887e4e7f6217ee7f166dc4ef586c72987e61a43a
```
