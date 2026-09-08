# Channelized static-occlusion v2 pilot result

Date: 2026-09-08 (Asia/Seoul)

## Outcome

The separately versioned channelized pilot completed all 30 scheduled rows in
about 41 minutes. Full, Sector and Adaptive each completed 10/10 missions with
zero authoritative source-PCD contacts. Every row was unique, first-attempt
and run/resource/speed/performance/cgroup-valid. There was no retry, resource
abort, infrastructure failure or OOM.

The frozen decision is
`STOP_AFTER_CHANNEL_PILOT_NO_CONFIRMATORY_EXPANSION`. The validity,
protected-mode, nominal-control and no-reverse-discordance gates passed. The
channelized-occlusion delivery and both alternative discrimination gates
failed. Consequently the proposed independent 80-environment/240-row
confirmatory cohort was not generated or run.

This negative result must not be reported as an Adaptive safety-rate advantage
or as a McNemar result. It is a valid exploratory mechanism-screening result,
not an infrastructure-interrupted campaign.

## Experimental role and integrity

V1 used odd-seed source layouts and is closed design evidence. V2 used the
independent even-seed layouts 2, 4, 6, 8 and 10, one for each of the five
existing radius strata. V1 and V2 are not pooled. The old Map1--10 cohort also
remains a separate development/repeated-run reliability cohort.

Both members of a V2 pair shared the same cleared local patch, L-shaped
channel, walls and hazard cylinder at `(18.0,24.0) m`. Nominal removed wall
samples only in the 0.20 m-high `z=[1.35,1.55] m` sensor slit; Occluded retained
the solid inner walls. The slit was narrower than the declared 0.40 m vehicle
diameter and therefore was not intended as a body-traversable shortcut.

The deterministic preflight validator passed the frozen 1.45 m sensor-height
line-of-sight, solid-wall reveal, body-clearance and fixed-bypass checks. The
runtime PCDs/configs were reproduced from the frozen generator with the
manifest hashes before flight. The compared Full/Sector/Adaptive systems are
complete deployed policies, not an isolated fallback-only intervention.

## Per-map result

Each mode cell is `completion/contact; time; authoritative global clearance`.
The last column is Adaptive effective-Full/trajectory-guard opening count.

| Tier | Visibility | Full | Sector | Adaptive | Adaptive opens |
|---:|---|---|---|---|---:|
| 1 | Nominal | 1/0; 60.15 s; +0.287 m | 1/0; 58.53 s; +0.292 m | 1/0; 57.44 s; +0.265 m | 24 / 2 |
| 1 | Occluded | 1/0; 61.20 s; +0.258 m | 1/0; 60.75 s; +0.307 m | 1/0; 59.87 s; +0.136 m | 24 / 1 |
| 2 | Nominal | 1/0; 60.49 s; +0.225 m | 1/0; 62.36 s; +0.274 m | 1/0; 56.96 s; +0.261 m | 23 / 2 |
| 2 | Occluded | 1/0; 70.72 s; +0.266 m | 1/0; 61.67 s; +0.226 m | 1/0; 66.02 s; +0.204 m | 23 / 4 |
| 3 | Nominal | 1/0; 65.15 s; +0.283 m | 1/0; 61.82 s; +0.268 m | 1/0; 60.94 s; +0.154 m | 22 / 2 |
| 3 | Occluded | 1/0; 65.47 s; +0.270 m | 1/0; 67.53 s; +0.252 m | 1/0; 66.02 s; +0.273 m | 23 / 4 |
| 4 | Nominal | 1/0; 80.09 s; +0.286 m | 1/0; 73.49 s; +0.288 m | 1/0; 60.45 s; +0.249 m | 17 / 4 |
| 4 | Occluded | 1/0; 64.28 s; +0.284 m | 1/0; 68.07 s; +0.270 m | 1/0; 66.17 s; +0.218 m | 21 / 6 |
| 5 | Nominal | 1/0; 85.35 s; +0.255 m | 1/0; 71.52 s; +0.111 m | 1/0; 73.50 s; +0.246 m | 23 / 6 |
| 5 | Occluded | 1/0; 68.26 s; +0.258 m | 1/0; 68.99 s; +0.278 m | 1/0; 81.43 s; +0.252 m | 21 / 9 |

All 30 analytic hazard-cylinder measurements were valid and recorded zero
hazard contact. Minimum hazard-specific clearance over the ten rows per mode
was +0.276/+0.229/+0.135 m for Full/Sector/Adaptive. Global source-PCD
clearance fell below +0.20 m in 0/1/2 Full/Sector/Adaptive rows. These are
descriptive n=1 mechanism observations, not reliability estimates.

## Frozen delivery-gate result

Probe progress is `(drone_x + drone_y)/2` at the first raw point within the
fixed 0.90 m hazard probe. Delays are Occluded minus Nominal within the same
mode. Alignment is the absolute Sector--Adaptive progress difference on the
Occluded member.

| Tier | Sector delay | Adaptive delay | Occluded alignment | Sector/Adaptive reveal distance | Sector centre in crop |
|---:|---:|---:|---:|---:|---:|
| 1 | +3.029 m | +6.149 m | 0.129 m | 4.216 / 4.198 m | no |
| 2 | +4.231 m | +6.422 m | 0.091 m | 3.978 / 4.293 m | no |
| 3 | +0.014 m | +6.927 m | 0.052 m | 3.908 / 4.288 m | no |
| 4 | -0.006 m | +10.420 m | 0.154 m | 3.721 / 3.418 m | no |
| 5 | +6.294 m | +5.981 m | 0.254 m | 4.532 / 4.459 m | no |

The solid-wall Occluded treatment did standardize late delivery: every reveal
distance was inside the frozen `[3.5,7.0] m` band, Sector/Adaptive progress
agreed within 0.255 m, and the hazard centre was outside the Sector crop in
5/5 tiers. The full delivery gate nevertheless required both policies to have
at least 6.0 m Occluded-minus-Nominal delay in every tier. Sector passed only
tier 5; Adaptive passed tiers 1--4 and missed tier 5 by 0.019 m. The delivery
gate therefore failed exactly as preregistered.

## Frozen discrimination-gate result

| Tier | Sector nominal clearance | Adaptive nominal clearance | Sector occluded clearance | Adaptive occluded clearance | Direct A-S | Difference-in-differences | Adaptive occluded opens |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | +0.297 m | +0.289 m | +0.311 m | +0.135 m | -0.176 m | -0.168 m | 24 / 1 |
| 2 | +0.304 m | +0.300 m | +0.229 m | +0.279 m | +0.050 m | +0.054 m | 23 / 4 |
| 3 | +0.296 m | +0.320 m | +0.475 m | +0.299 m | -0.176 m | -0.200 m | 23 / 4 |
| 4 | +0.293 m | +0.279 m | +0.294 m | +0.308 m | +0.014 m | +0.028 m | 21 / 6 |
| 5 | +0.282 m | +0.299 m | +0.318 m | +0.248 m | -0.070 m | -0.087 m | 21 / 9 |

- Desired Nominal-Sector-safe/Occluded-Sector-bad/Occluded-Adaptive-safe
  discordances: 0; required at least 2, including a hazard contact.
- Reverse binary discordances: 0.
- Adaptive hazard-clearance wins: 2/5; required at least 4/5.
- Median direct Adaptive advantage: -0.070 m; required at least +0.100 m.
- Median paired difference-in-differences: -0.087 m; required at least
  +0.100 m.
- Every Occluded Adaptive row did open on the trajectory guard, 1--9 times.
  The negative result was not an always-closed Adaptive execution.

Both discrimination routes failed. Because binary outcomes had no variation
and the confirmatory cohort was not opened, no McNemar test was performed.

## Why the channel still failed as a controlled treatment

The channel fixed the solid-wall reveal geometry, but the Nominal slit did not
provide policy-independent 3D visibility. The analytic validator checked a
ray at the frozen 1.45 m sensor height. The flown altitude varied by mode and
trajectory. In tiers 3 and 4, Nominal Sector first detected the hazard only at
drone z=1.942 and 1.905 m near the late reveal, whereas Nominal Adaptive first
detected it at z=1.462 and 1.491 m through the intended slit. This altitude
pattern is consistent with the near-zero Sector delay in those tiers. It does
not prove the exact depth-buffer ray for every point, but it directly shows
that the fixed-height validation did not cover the flown 3D state.

Early Nominal observations were also sparse. For example, tier-1/2 Sector
first saw only two probe points, while late solid-wall reveals commonly
contained hundreds. Depth-buffer rasterization, wall-point discretization and
the vertical extent of the cylinder therefore made the narrow slit a brittle
visibility control.

The two policies did not share the same Nominal pre-observation state. In
tier 4 their first-observation progress differed by about 10.27 m, and
Adaptive was already effectively Full-open at the tier-4 and tier-5 Nominal
probe. Thus a geometry validated at one fixed station/height could not enforce
a matched nominal trajectory after the deployed policies began reacting.

Once the solid wall forced a common late reveal, both policies remained safe.
Sector could react to visible walls, later body-yaw changes and its preserved
speed-dependent near field. Adaptive did react--221 effective Full openings
and 40 trajectory-guard openings over ten rows--but those interventions did
not produce greater hazard clearance. In three of five Occluded tiers its
hazard clearance was lower than Sector's.

The root design defect is therefore not simply “the wall was too short.” V2
coupled a narrow fixed-height optical slit to policy-dependent 3D motion. The
solid-wall member standardized the reveal, but the nominal control did not.
Retuning the slit after viewing these outcomes and calling the same cohort
confirmatory would be invalid.

## Computation and communication

The measurement-only raw probe synchronously scans the filtered raw cloud
until first observation. It has no publisher/control output, but literal zero
timing perturbation is not claimed. Its burden is included only in Sector and
Adaptive, making their Full comparison conservative. This n=1 pilot is not
the definitive compute cohort.

| Metric, pooled 10 rows/mode | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| Mission time (s) | 68.116 | 65.473 | 64.880 | 4.751% lower | 0.906% lower |
| Planner ingress (MiB/s) | 10.535 | 3.091 | 2.585 | 75.459% lower | 16.351% lower |
| Map compute (ms/frame) | 44.082 | 12.204 | 24.585 | 44.229% lower | 101.444% higher |
| End-to-end mean cores | 1.660 | 1.344 | 1.414 | 14.807% lower | 5.214% higher |
| End-to-end core-seconds | 116.217 | 90.461 | 94.262 | 18.891% lower | 4.202% higher |
| End-to-end p95 cores | 1.937 | 1.559 | 1.671 | 13.735% lower | 7.217% higher |
| End-to-end peak PSS (MiB) | 3499.1 | 3457.9 | 3506.8 | 0.222% higher | 1.416% higher |

Algorithm-only Full-versus-filtered CPU remains out of scope because Full has
a different process boundary. The common end-to-end cgroup is the valid CPU
comparison. Adaptive preserved the established Full-relative ingress, map and
CPU reductions but did not save peak memory, and it cost more map work and
end-to-end CPU than fixed Sector.

Minimum system available memory was 5416.14 MiB and maximum memory PSI
some/full avg10 was 0/0. Algorithm, end-to-end and FSM swap were zero. The
host's approximately 2046.9 MiB swap-used value and the parent cgroup's
approximately 681.5 MiB peak were persistent broader-host accounting, not
swap attributed to the measured algorithm/end-to-end/FSM process scopes.

## Next defensible step

Do not expand V2. Before another flight cohort, use the recorded trajectories
to validate visibility over a 3D envelope rather than at one height. A V3
design should avoid a narrow horizontal slit: either measure/control visibility
at the simulator source boundary with identical collision geometry, or use a
fully solid blind corner and a separately defined no-hazard control. It must
first prove, on replay or a very small preregistered pilot, that:

1. the compared policies enter the Occluded reveal region on matched paths;
2. the Nominal treatment is visible over the full flown altitude/yaw envelope;
3. Sector excludes the hazard until the intended reveal while Adaptive opens
   before the critical clearance point; and
4. an independently validated collision-free escape remains available.

Only a new version that passes those delivery checks should open a large
confirmatory campaign. The current result supports the compute-efficiency
claim but not the desired static-occlusion safety-superiority claim.

## Evidence

- Preregistration:
  `docs/static_occlusion_channel_pilot_preregistration_20260908.md`
- Raw rows:
  `results/static_occlusion_channel_pilot_three_mode_n1_raw_20260908.csv`
- Strict validation:
  `results/static_occlusion_channel_pilot_three_mode_n1_validation.json`
- Summary and reductions:
  `results/static_occlusion_channel_pilot_three_mode_n1_{summary,reductions}.csv`
- Per-map and pair tables:
  `results/static_occlusion_channel_pilot_three_mode_n1_{map_table,pair_table}.csv`
- Frozen decision:
  `results/static_occlusion_channel_pilot_three_mode_n1_gate.json`
- Reproducible geometry:
  `scripts/native_campaign/gen_static_occlusion_channel_pilot.py`,
  `validate_static_occlusion_channel_pilot.py` and
  `static_occlusion_channel_pilot_manifest.json`

SHA-256 checksums for raw, summary, reductions, strict validation, map table,
pair table and gate decision, in that order:

```text
a3764a9b262d33e43fb80293f84b59bc28499ffd6575061b38bb7a8a5c3a2f4b
16090559e8c30c8c00257fb4e66a7001043579d3768d8a3931193426f76118f6
f701865ee8aa026cb187627f06f95123d78c53219c746f66d9485420e4f764b2
2ef21e4feca56c73d7f86175d743d3a77bc6010cca8e9814d3a9db6b6bdc4078
912c7cdf16a643998908be395027993491bcb274d0b1e7bee0fd07b8a64ac8cb
5b835bf8619e4370b188d01282c556a8996d98da138b2b6b36de3af7139f46ec
bbfe9bd18d3f7ab9dcb642975cdfc9b2d64c178e18a53f940d105292788eb36d
```
