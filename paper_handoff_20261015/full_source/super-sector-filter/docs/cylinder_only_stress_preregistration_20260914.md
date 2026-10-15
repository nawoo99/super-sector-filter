# Cylinder-only static Stress 1--5 freeze record

Date: 2026-09-14 (Asia/Seoul)

Status at freeze: **geometry gate passed; development replay gate passed; no
final-map flight outcome observed yet**

## Purpose and evidence boundary

This family is a supplemental static-occlusion test requested after the earlier
wall-shaped blind-fork/dropout suite did not match the intended environment.
Every obstacle in this new family is a vertical cylinder, as in Normal Map
1--5. There are no walls, meshes, moving obstacles, artificial point-cloud
dropouts or planner changes.

Normal results and the earlier `shc1`--`shc5` wall/dropout results are immutable
separate evidence. They must not be renamed, pooled with, or reported as the
new cylinder-only Stress results. The development layout
`stress_cyl_dev_r3` is also excluded from final flights and statistics.

## Frozen final family

All maps use the same `loop24.txt` mission, 3.0 m-high cylinders, exactly 410
cylinders and the existing v7 planner profiles. Radius is the controlled
severity variable. Odd seed 5 was used only for development; the five final
backgrounds use previously unused even seeds.

| Report label | Runtime map | Source seed | Radius (diameter), m | Cylinders |
|---|---|---:|---:|---:|
| Stress 1 | `stress_cyl_r1` | 2 | 0.150 (0.300) | 410 |
| Stress 2 | `stress_cyl_r2` | 4 | 0.275 (0.550) | 410 |
| Stress 3 | `stress_cyl_r3` | 6 | 0.400 (0.800) | 410 |
| Stress 4 | `stress_cyl_r4` | 8 | 0.525 (1.050) | 410 |
| Stress 5 | `stress_cyl_r5` | 10 | 0.650 (1.300) | 410 |

The first north-east loop corner contains three connected chains of individual
cylinders. Adjacent chain cylinders have 0.20 m surface separation, which is
smaller than the 0.40 m vehicle diameter and therefore does not form a
traversable slit. A transverse cylinder chain conflicts with the direct
post-turn trajectory. A northern topology-changing bypass was reserved before
flight. Non-structural background cylinders have at least 1.0 m pairwise
surface separation and were kept at least 2.0 m from the nominal mission
polyline before structural cylinders were added.

The generator, exact cylinder tables, simulator configs and PCD hashes are
frozen in `scripts/native_campaign/cylinder_only_stress_manifest.json`.
Regenerating a PCD from the frozen generator/table is allowed only as a byte
identity check. Geometry, seed, cylinder count, radius, route, filter angle or
planner tuning must not be changed after the first final-map flight.

## Pre-flight gates

The fail-closed structure validator passed all eight family checks:

- five final maps and exactly 410 same-radius cylinders per map;
- no non-cylinder primitive, sensor fault or dynamic obstacle;
- direct trajectory body collision exists;
- the predeclared bypass has vehicle-body plus 0.20 m planner-margin clearance;
- the 45 degree Fixed Sector excludes every replay-conflicting closure
  cylinder.

The worst reserved bypass body clearance was 0.30 m in Stress 5, leaving the
frozen 0.20 m planner margin. Exact per-map measurements are stored in
`results/cylinder_only_stress_structure_gate_20260914.json`.

The development-only seed-5 map was then rendered by MARSIM and the identical
raw frames were handed directly to the production C++ Sector and Adaptive
frontends. All 10 measured raw frames contained trajectory-conflicting points;
the Fixed Sector removed all of them. Adaptive produced five fresh,
generation-matched `OCCUPIED` verdicts in one consecutive sequence. The raw
stream hash matched exactly between modes
(`42dbd1959a2e2db8`). The fail-closed replay gate passed all 14 checks. This is
a component mechanism gate, not a closed-loop safety or completion result.

## Frozen Full-feasibility gate

Before any Sector or Adaptive final evaluation, run exactly one first-attempt
Full flight on each frozen Stress map:

- modes: Full only;
- repetitions: one per map, five rows total;
- mission: `loop24.txt`, target speed 7 m/s;
- perception: static PCD through the real 10 Hz MARSIM renderer;
- planner profile: `static_seedmaps_guard_viability_tight_v7.yaml`;
- retries: no outcome-driven retry; an infrastructure-invalid row is retained
  and reported separately rather than silently replaced;
- pass: all five rows complete, have zero static-PCD contacts, valid speed,
  valid resource accounting and no infrastructure failure.

If any map fails this gate, preserve the failure and stop the confirmatory
Sector/Adaptive campaign. Diagnose feasibility without rewriting the observed
map under the same name. Any redesigned geometry must receive new names and a
new freeze record.

Passing five flights only establishes feasibility for the next experiment. It
does not establish a 100% population guarantee or Adaptive safety superiority.
Those claims require the later paired Full/Sector/Adaptive campaign and
uncertainty reporting.

