# Static-occlusion balanced pilot preregistration

Date frozen: 2026-09-08 (Asia/Seoul), before the first flight row

## Purpose and relation to Map1--10

The existing Map1--10 campaign is retained unchanged as development and
run-to-run reliability evidence.  Those maps implement five background
cylinder-radius levels with two random seeds per level, but all ten belong to
one uniform random-forest/square-loop scenario family.  They do not constitute
a controlled static-occlusion test and will not be pooled with the experiment
below.

This pilot asks whether a physically rendered static blind corner actually
delivers the mechanism needed to distinguish the complete Adaptive policy from
the fixed Sector ablation.  It is an exploratory design gate, not confirmatory
evidence.  If and only if the frozen gate below passes, the confirmatory study
will use eight new independent layouts at each of the same five radius levels
and both visibility conditions: `8 layouts x 5 radii x 2 visibility = 80`
environments, one paired Full/Sector/Adaptive execution per environment, or
240 flight rows.  Pilot layouts and outcomes will be excluded from that
confirmatory cohort.  This makes the story continuous rather than treating the
old five radius conditions and new maps as unrelated additions.

## Treatment and geometry

The pilot has five radius strata.  Its source layouts are the pre-existing odd
seeds 1, 3, 5, 7 and 9, corresponding to background cylinder radii 0.150,
0.275, 0.400, 0.525 and 0.650 m.  Within each stratum, the nominal and occluded
maps have the same retained background cylinders and the same common hazard:

- a local rectangle `x=[11,26], y=[11,27] m` is cleared identically in both;
- a 0.65 m-radius, 3.0 m-tall hazard is placed at `(19.50, 24.00) m` on the
  outgoing top leg after the `(24,24)` turn;
- the occluded member alone contains a 3.0 m-tall wall with horizontal bounds
  `x=[14.00,20.30], y=[21.35,21.65] m`;
- MARSIM renders the common static PCD through its OpenGL depth buffer, so the
  wall physically hides farther PCD samples rather than deleting them in a
  late software hook.

The analytic validator requires the hazard-centre ray to be hidden from
diagonal approach stations `x=y=12,14,16,18,20 m` and revealed by
`x=y=21 m`.  It also requires at least 0.50 m body clearance from the wall on
the nominal diagonal approach and on a fixed northern local bypass.  The
current frozen values are +0.542462 m and +0.650000 m.  These checks prove that
the intervention is not constructed as an unavoidable geometric contact;
they do not prove planner success.

Map names are:

| Radius stratum | Background radius | Nominal | Occluded | Source layout |
|---:|---:|---|---|---:|
| 1 | 0.150 m | `occ_p_r1_nom` | `occ_p_r1_occ` | seed1 |
| 2 | 0.275 m | `occ_p_r2_nom` | `occ_p_r2_occ` | seed3 |
| 3 | 0.400 m | `occ_p_r3_nom` | `occ_p_r3_occ` | seed5 |
| 4 | 0.525 m | `occ_p_r4_nom` | `occ_p_r4_occ` | seed7 |
| 5 | 0.650 m | `occ_p_r5_nom` | `occ_p_r5_occ` | seed9 |

`scripts/native_campaign/gen_static_occlusion_pilot.py` generates the runtime
PCDs/configs deterministically.  The compact map hashes and counts are frozen
in `scripts/native_campaign/static_occlusion_pilot_manifest.json`.
`validate_static_occlusion_pilot.py` must pass before flight.

## Compared systems and interpretation boundary

All rows use the already frozen v7, 45-degree, C++ frontend stack from the
resource-gated campaigns.  Full receives the unchanged raw cloud.  Fixed
Sector crops around vehicle body yaw and has no recovery opening.  Adaptive
uses velocity-aligned cropping plus the raw-cloud trajectory/current-body risk
side channel and bounded Full refreshes.

Consequently, this is a policy-level comparison.  A result must not be stated
as the isolated causal effect of “turning Adaptive fallback on” because
observation-axis selection also differs.  The common half-angle, planner,
sensor, route, dynamics and resource contract remain fixed.

The C++ frontend now contains a measurement-only static probe centred on the
common hazard.  It records the first raw LiDAR observation position, distance,
speed, body/velocity relative bearing and whether the hazard centre would lie
inside the current crop.  It does not publish a message, open the filter,
change a trajectory, or alter a planning decision.

## Frozen pilot execution

There are ten maps, three modes and one run per cell: 30 rows.  Global mode
rotation gives ten occurrences of each order position.  The authoritative
safety oracle remains the source static PCD inflated by the declared 0.20 m
vehicle sphere.  Timeout is 180 s; retries, infrastructure aborts, resource
quality, speed validity and common end-to-end CPU are recorded as before.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps occ_p_r1_nom occ_p_r1_occ occ_p_r2_nom occ_p_r2_occ \
         occ_p_r3_nom occ_p_r3_occ occ_p_r4_nom occ_p_r4_occ \
         occ_p_r5_nom occ_p_r5_occ \
  --modes full sector adaptive --runs 1 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-adaptive-super-config static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml \
  --seedmap-static-pcd --loop-timeout 180 \
  --filter-profile strict-burst --filter-backend cpp-frontend \
  --full-intra-process --filter-half-angle-deg 45 \
  --filtered-reliable-map-link \
  --adaptive-max-publish-hz 5 --adaptive-risk-max-eval-hz 5 \
  --adaptive-risk-body-clearance-m 0.20 \
  --adaptive-risk-body-horizon-s 0.15 \
  --adaptive-risk-body-max-odom-age-s 0.20 \
  --cgroup-cpu-accounting --optimizer-phase-memory-trace \
  --artifacts-dir results/static_occlusion_balanced_pilot_three_mode_n1_artifacts_20260908 \
  --out results/static_occlusion_balanced_pilot_three_mode_n1_raw_20260908.csv
```

## Frozen validity and stop rules

The pilot is valid only if all 30 requested keys are unique, every row is
first-attempt, run/resource/speed/performance/cgroup-valid, and there is no
retry, OOM or resource abort.  Both filtered rows in every map must report a
valid static probe observation.  An invalid or infrastructure-confounded row
is not silently replaced and is excluded from mechanism conclusions.

A Full or Adaptive failure means either incomplete mission or any authoritative
static-PCD contact.  On the first such failure, preserve the row, stop the
pilot, determine whether the cause is geometry, deployment, infrastructure,
measurement or planner behavior, and do not expand to 80 confirmatory maps.
Sector failure is an observed ablation outcome and is non-stopping.

## Frozen mechanism and expansion gates

All of the following must hold before confirmatory-map generation:

1. Full and Adaptive are complete and contact-free in all ten map conditions.
2. Within every radius stratum, the occluded map's mean first raw-hazard
   observation progress `(drone_x + drone_y)/2` across Sector and Adaptive is
   at least 2.0 m later than the paired nominal map.  This is the physical
   occlusion-delivery gate.
3. There is no reverse binary discordance in which Adaptive fails or contacts
   while Sector is complete and contact-free.
4. The five occluded maps show either:
   - at least two desired binary discordances (Sector incomplete/contact,
     Adaptive complete/contact-free), including at least one Sector contact;
     or
   - Adaptive has greater authoritative minimum clearance in at least four of
     five paired occluded maps with median improvement at least 0.10 m, while
     a trajectory-guard opening is observed in every such improved row.

If gate 4 fails, report that the construction delivered occlusion but lacked
discriminatory stress and stop.  It may inform a separately versioned design,
but its outcomes must not be tuned and then presented as confirmation.  If all
gates pass, freeze the independent 80-map generator and statistical analysis
before running the 240 confirmatory rows.

## Frozen identifiers

- SUPER base commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- sector-filter base commit: `dbcef397408ad5bb8e8ca623d6275d1061121f48`
- campaign runner SHA-256: `e631a86531cab16acea805f55992b035ae22c2a9985fa695085f389e58c82334`
- loop monitor SHA-256: `a84d62214cd4c8e1cfdf863108b331315979a1d59e6eb745012f1f34d5a10c45`
- generator SHA-256: `3a5119f7a5067825be2e5358829863cd9f438b06765e1743a201740282380b3a`
- validator SHA-256: `c7bd136ce8174d7d3a7c2a393010bb37ba2cb404b68e887313d8f5cbfe4a3d72`
- map manifest SHA-256: `e5c51ac51aeabc997702f2a40483911b8f26c3ce820819d86cc64d2e87378812`
- mirrored C++ frontend source SHA-256: `5feb942ce98030499214139555a54b0c822521d1f95fe015e856664181a1cdaa`
- installed native filter executable SHA-256: `95d676044708813b119ffc1d751e5b12c425e70fc091626f0d3e0b7eda861935`
- installed frontend component library SHA-256: `3b19ab30488b2b4de0de8f52d32bd064d5d7d3acddf7c273aa9039b3aaf97c40`
- Full config SHA-256: `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`
- Sector config SHA-256: `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`
- Adaptive config SHA-256: `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`

## Registered outcome (2026-09-08, after all pilot rows)

The pilot completed 30/30 unique, first-attempt, quality-valid rows in about
41 minutes. Full, Sector and Adaptive each completed 10/10 with zero
authoritative source-PCD contacts; the static probe was valid in all 20
filtered rows. There were no retries, resource aborts, OOMs or infrastructure
failures.

The physical-delivery gate passed in all five strata: paired occlusion delayed
mean first raw-hazard observation progress by 6.146, 9.665, 8.971, 6.327 and
4.416 m. The discrimination gate failed. Desired Sector-bad/Adaptive-safe
binary discordances were 0, and Adaptive clearance was greater in only 3/5
occluded strata with median difference +0.011 m rather than the required 4/5
and +0.10 m. Trajectory-guard openings were present in every occluded Adaptive
row.

Per the frozen stop rule, the decision is
`STOP_AFTER_PILOT_NO_CONFIRMATORY_EXPANSION`; the independent 80-map/240-row
confirmatory campaign was not generated or run. Full tables, computation,
mechanism analysis and evidence hashes are in
`docs/static_occlusion_balanced_pilot_result_20260908.md` and the compact gate
record is
`results/static_occlusion_balanced_pilot_three_mode_n1_gate.json`.
