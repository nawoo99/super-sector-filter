# Channelized static-occlusion v2 pilot preregistration

Date frozen: 2026-09-08 (Asia/Seoul), before the first v2 flight row

## Study role and independence

The first balanced static-occlusion pilot is closed design evidence. Its
finite wall delayed raw hazard observation but left a broad bypass and did not
force a common reveal point; it therefore stopped before confirmation. The
v1 maps, parameters and outcomes will not be pooled with this v2 pilot.

V2 uses the independent even-seed backgrounds 2, 4, 6, 8 and 10, one from
each of the same five cylinder-radius strata. V1 used odd seeds 1, 3, 5, 7 and
9. The route, sensor, speed, planner, 45-degree half-angle, three deployed
policies and resource contract remain unchanged. V2 is still an exploratory
mechanism gate, not confirmatory evidence.

If and only if every frozen gate below passes, a later confirmatory study may
generate eight new independent layouts per radius stratum and both visibility
conditions: `8 layouts x 5 radii x 2 visibility = 80 environments`, with one
paired Full/Sector/Adaptive execution per environment, or 240 rows. Neither
v1 nor v2 layouts may enter that cohort, and its generator and statistical
analysis must be frozen before flight.

## Common channel and controlled visibility treatment

A local rectangle `x=[5.0,27.5], y=[5.0,27.5] m` is cleared identically in
both members of every pair. The common 3.2 m-high L-shaped channel guides the
first diagonal leg into the `(24,24)` turn chamber and then west along the top
loop leg. Its free half-width is 1.80 m and wall thickness is 0.30 m. The
outer diagonal, east and north walls form a connected outer boundary; the
inner diagonal joins the south outgoing wall, removing the finite-edge bypass
that invalidated v1.

Every map contains the same 0.75 m-radius, 3.2 m-high hazard cylinder at
`(18.0,24.0) m`. A fixed northern path has analytically checked body clearance
+0.25 m from the hazard and +0.40 m from the walls, so the construction is not
an unavoidable geometric collision.

Both visibility conditions have the same walls and body free-space topology:

- Nominal removes only wall samples in `z=[1.35,1.55] m` from the two inner
  walls, creating a narrow horizontal sensor slit.
- Occluded retains the solid inner walls.
- The declared slit is 0.20 m high, below the 0.40 m vehicle diameter. It is
  therefore a line-of-sight aperture, not a body-traversable shortcut.

At sensor height 1.45 m, the deterministic validator requires the nominal
hazard-centre ray to remain visible and the occluded ray to remain blocked at
diagonal stations `x=y=11,14,17,20 m`. The solid-wall ray must be revealed at
`(22.4,22.4) m`, 4.681880 m from the hazard. At station 11 the nominal hazard
is 14.764823 m away, inside the fixed 15 m LiDAR horizon. The diagonal
approach has +1.532419 m wall body clearance and +3.292643 m hazard body
clearance.

MARSIM renders these source PCDs through its OpenGL depth buffer. The paired
treatment therefore changes physical sensor visibility rather than deleting
points after rendering. The source-PCD oracle inflated by the declared 0.20 m
vehicle sphere remains authoritative for contact. A separate analytic
cylinder metric records hazard-specific clearance/contact without replacing
that oracle.

| Radius stratum | Radius | Nominal map | Occluded map | Source layout |
|---:|---:|---|---|---:|
| 1 | 0.150 m | `occ_c_r1_nom` | `occ_c_r1_occ` | seed2 |
| 2 | 0.275 m | `occ_c_r2_nom` | `occ_c_r2_occ` | seed4 |
| 3 | 0.400 m | `occ_c_r3_nom` | `occ_c_r3_occ` | seed6 |
| 4 | 0.525 m | `occ_c_r4_nom` | `occ_c_r4_occ` | seed8 |
| 5 | 0.650 m | `occ_c_r5_nom` | `occ_c_r5_occ` | seed10 |

`gen_static_occlusion_channel_pilot.py` generates the runtime PCDs/configs;
their hashes and point counts are frozen in
`static_occlusion_channel_pilot_manifest.json`.
`validate_static_occlusion_channel_pilot.py` must pass before flight.

## Compared policies and measurement limitation

Full receives the unchanged raw cloud. Fixed Sector crops around body yaw and
cannot open. Adaptive uses velocity-yaw cropping, raw-cloud trajectory/current
body risk checks and bounded Full refresh. This is a deployed-policy
comparison, not the isolated effect of one fallback switch.

The existing C++ static probe records the first raw point within 0.90 m of the
hazard, including pose, speed, body/velocity bearing and crop state. It has no
publisher or control output, but it synchronously scans input until first
detection. Literal zero timing perturbation is not claimed. The extra work is
limited to the filtered rows and the pilot is not used as a definitive
computation comparison; future confirmation should move the probe to the
simulator/source boundary or reuse an existing point pass.

## Frozen execution

The pilot contains ten maps, three modes and one run per cell: 30 rows. Mode
order rotates globally. Timeout is 180 s. No planner, filter or map parameter
may change after the first row.

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/native_campaign.py \
  --maps occ_c_r1_nom occ_c_r1_occ occ_c_r2_nom occ_c_r2_occ \
         occ_c_r3_nom occ_c_r3_occ occ_c_r4_nom occ_c_r4_occ \
         occ_c_r5_nom occ_c_r5_occ \
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
  --artifacts-dir results/static_occlusion_channel_pilot_three_mode_n1_artifacts_20260908 \
  --out results/static_occlusion_channel_pilot_three_mode_n1_raw_20260908.csv
```

## Frozen validity and stop rules

The pilot is valid only with 30 exact unique keys, all first-attempt and
run/resource/speed/performance/cgroup-valid, no retry/resource abort/OOM/
infrastructure failure, 20/20 filtered raw probes and 30/30 valid analytic
hazard metrics.

On the first Full or Adaptive incomplete mission or authoritative static-PCD
contact, preserve the row, stop launching new rows, classify the failure and
do not expand. Sector failure/contact is a non-stopping ablation outcome. A
Nominal Sector failure does not stop collection but fails the control gate.
Infrastructure-confounded rows are preserved and excluded rather than silently
replaced as planner outcomes.

## Frozen mechanism and expansion gates

All gates must pass:

1. Full and Adaptive are complete and authoritative-contact-free in all 20
   protected rows.
2. All 15 Nominal rows are complete and contact-free.
3. For each radius stratum and for both Sector and Adaptive separately,
   Occluded minus Nominal first-probe progress `(x+y)/2` is at least 6.0 m.
4. Within every Occluded stratum:
   - Sector and Adaptive first-probe progress differ by at most 2.0 m;
   - both first-probe horizontal distances are in `[3.5,7.0] m`; and
   - the hazard centre is outside Sector's 45-degree crop at first raw
     observation.
5. There is no reverse binary discordance where Adaptive fails/contacts while
   Sector is complete/contact-free.
6. The Occluded maps show either:
   - at least two matched desired discordances where Nominal Sector is safe,
     Occluded Sector fails/contacts and Occluded Adaptive is safe, including
     at least one analytic hazard-contact episode; or
   - Adaptive hazard-specific minimum clearance exceeds Sector in at least
     4/5 Occluded strata, with median direct advantage at least +0.10 m,
     median paired difference-in-differences at least +0.10 m, and at least
     one trajectory-guard opening in every improved Adaptive row.

Failure of gate 3 or 4 means the channel still did not standardize physical
delivery. Failure of gate 6 means delivery worked but did not establish the
required safety separation. Either outcome stops before confirmation. No
McNemar or safety-superiority claim is made from the n=1 pilot itself.

## Frozen identifiers

- SUPER base commit: `2ad3419c127a617c6d7df6925e81a14175a9c096`
- sector-filter base commit: `b7523b505dc5b57423b2112ffb08c514ef273349`
- campaign runner SHA-256: `c11b16e84066eab3422834053480e865f2f2c73403a67514f5c1906287751dc7`
- loop monitor SHA-256: `873638c582313a49ac8e9cba5522be7fcef4f84914508e01ce609c218201d6f2`
- generator SHA-256: `b99057aad07ce19d87ff159c7c9796c6dc8321b98e4b3f08e160ce0a0ce59e23`
- validator SHA-256: `b31de59ad1808218b41b0f54479927d3572a256bbdcc9a3af9273f18032cef58`
- analyzer SHA-256: `4265182869b8693b773939663d02c908e2d1d91ce00670f78b0bfe3c5c82eb6d`
- manifest SHA-256: `d26c8483e95fca1a9c806c1c5c0313d74b74f41f94e0fc81973fd140e8dc4ae7`
- mirrored C++ frontend SHA-256: `5feb942ce98030499214139555a54b0c822521d1f95fe015e856664181a1cdaa`
- installed frontend executable SHA-256: `95d676044708813b119ffc1d751e5b12c425e70fc091626f0d3e0b7eda861935`
- installed frontend component SHA-256: `3b19ab30488b2b4de0de8f52d32bd064d5d7d3acddf7c273aa9039b3aaf97c40`
- Full/Sector/Adaptive config SHA-256:
  `6589b7c4065aa528facecc8f0f624c4f178718933afa537af861f4eb54cee540`,
  `eafae08a239cc4409b7df0b829f7951a0d26a0ea3ec5a97c3f03ad3a2b44eb24`,
  `82c8536181b1c402330d47a23c3b17311537f91105eca71337286d0d514277a7`

## Registered outcome

The pilot subsequently completed all 30 rows in about 41 minutes. All rows
were unique, first-attempt and quality-valid; Full/Sector/Adaptive were each
10/10 complete with zero authoritative contact. Validity, protected-mode,
nominal-control and no-reverse-discordance gates passed.

The frozen delivery gate failed. Sector Occluded-minus-Nominal probe delays
were +3.029/+4.231/+0.014/-0.006/+6.294 m and Adaptive delays were
+6.149/+6.422/+6.927/+10.420/+5.981 m. Hence neither policy met the required
6.0 m delay in every tier, although all solid-wall Occluded reveals were
aligned within 0.255 m, occurred 3.418--4.532 m from the hazard and had the
hazard centre outside Sector's crop.

Both discrimination routes also failed: desired binary discordances were 0,
Adaptive hazard clearance was greater in 2/5 Occluded tiers, median direct
advantage was -0.070 m and median paired difference-in-differences was
-0.087 m. All Occluded Adaptive rows had trajectory-guard openings, so the
negative result was not an inactive fallback.

The registered decision is
`STOP_AFTER_CHANNEL_PILOT_NO_CONFIRMATORY_EXPANSION`; the proposed 80-map,
240-row confirmatory cohort was not generated or run. The fixed-height
Nominal slit did not cover the policy-dependent 3D flight envelope: for
example, tier-3/4 Nominal Sector first detection occurred at z=1.942/1.905 m,
while Adaptive first detection occurred at z=1.462/1.491 m inside the intended
slit band. Full evidence and interpretation are in
`docs/static_occlusion_channel_pilot_result_20260908.md`.
