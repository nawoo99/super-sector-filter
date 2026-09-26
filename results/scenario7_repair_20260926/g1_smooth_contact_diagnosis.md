# G1 Adaptive r01/run40100: smooth-contact geometry audit

Date: 2026-09-26. Scope: retrospective, read-only/offline examination of the original campaign. No source changes, threshold changes, ROS execution, or new flights were performed for this audit. **The cause of the whole contact episode remains unresolved pending scoped sensor/map/guard trace evidence.**

## Confirmed outcome

The native full-static-PCD oracle also detected this contact. The result is not solely an analytic-cylinder versus sampled-PCD discrepancy:

- Native `success=true`, `static_pcd_collisions=1`, `safety_collisions=1`, `safety_contact_source=static_pcd`.
- Native summary rounds minimum PCD distance to 0.184 m and clearance to -0.016 m. Its more precise `static_pcd_min_context` records **0.183795 m** distance and **-0.016205 m** clearance at elapsed 13.723110 s.
- First native static-PCD event: elapsed 13.703600 s, distance 0.192650 m.
- Independent closed-cylinder audit: **one episode, eight contacting samples (1369–1376), minimum clearance -0.01761240358360744 m**, using body radius 0.2 m. First analytic contact is elapsed 13.692034006 s; first non-contact sample 1377 is elapsed 13.772535086 s.
- Contacting primitive: cylinder index 211 / ID `cylinder_0211`, center `(16.203836, 23.377856)`, radius 0.5 m, height interval [0, 3] m. These poses are near z=1.5 m, so the side surface, not a cylinder cap, determines clearance.

## Inputs and immutable identities

Campaign root:

`/root/super-sector-filter/results/scenario7_n10_20260925_213533_3120932`

Triplet directory, relative to that root:

`test10/gapfree_d1_m01/r01_run40100`

Artifact stem, relative to the triplet directory:

`artifacts/gapfree_d1_m01_run40100_adaptive.attempt1`

| Input | SHA256 |
|---|---|
| `plan.json` | `e0d10e7d4bd66974c18c6e9c534531f057b829364b869f7d595d5615df5f3568` |
| Artifact stem + `.json` | `b2cbfc52ae477e123c68ed561dc17f660104f9e8ddb912e321501b278c55b715` |
| Artifact stem + `.solid_audit.json` | `21743d02527e039abc5771ae6b034534a71ce3f84f26c1ec47807406b57a5ff3` |
| Artifact stem + `.odometry.csv` | `22b7857e2525a7009e4d4b8b91b3879d662c2bde319618f8a12c77458f2c290b` |
| Artifact stem + `.stack.log` | `cde20ea29048c1f02c48111c5ec2ab82d9c8928e4561c9d7d9599241c5ed97a7` |

Geometry paths:

- `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/gapfree_d1_m01.pcd`: **800730 points**, SHA256 `98ad0e49a126ecbb7f1b6ee8532db06aa76720f4d3cfd7c513441fa9ab576d9e`.
- `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/gapfree_d1_m01_cylinders.csv`: SHA256 `64083e847d41306494aee57f9e6db9c53607ca0368ca819b9f65c59393ebed0a`.

Both geometry hashes match the recorded solid audit. The odometry hash above also matches that audit.

## Historical implementation checked

- `/root/super_ws/src/SUPER/rog_map/src/rog_map/sliding_map.cpp`, SHA256 `72d93569357ee77ab234f4ed1e254de50a3ac8d6b2774a7775c554a6718c5eb9`, matches the triplet plan. Lines 177–204 define `ORIGIN_AT_CORNER` conversion as `floor(position * resolution_inv)` and reconstruction as `(index + 0.5) * resolution`.
- The **historical flight's own stack log, line 124**, states `Init, resetMapSize: ORIGIN_AT_CORNER`. This is not inferred solely from a later build.
- `/root/super_ws/src/SUPER/super_planner/config/static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml`, SHA256 `d853803fb53088506e25c273564dec7b0b759e264c61cec64b0387d16ae84786`, matches the plan. `robot_r` is 0.2 m (line 168), raw-map resolution is 0.05 m (line 343). The separate 0.1 m inflation resolution / three-step inflation is not used in the reconstruction below.
- The original planner implementation is preserved in repository commit **`42c8119e7aecf371ee2608d1631f11f91ef004fa`**, path `super_patches/native_seedmap_campaign/super_planner_src/super_core/super_planner.cpp`. Its SHA256 is `de0485594fdfc538c30823ba9f0b6b4fd6d381adc0a206d79857868d18e856a7`, exactly matching the triplet plan. Read this committed version, not a later repair working-tree version. Lines 559–577 search occupied voxel centers and compare their Euclidean distance with `robot_r + 1e-9`. The search box extends to `robot_r + 0.5 * resolution`, but that does **not** enlarge the collision-distance threshold. The routine also contains initial-footprint masking logic; this reconstruction does not apply such a mask.
- `/root/super-sector-filter/scripts/native_campaign/native_loop_monitor.py`, SHA256 `f11777e680e4d4279c8d34ca7dfd86c55e98c9a7f6cd835e801a1f8a877f0813`, matches the solid audit's base-monitor hash. Its static-PCD test uses nearest original PCD point distance `< 0.2` (lines 896–936), not occupied voxel-center distance. The original planner comment describing these tests as matching should not be read as numerical equivalence after quantization.

## Full-PCD reconstruction at all eight contact poses

Computation: load all PCD XYZ values as float32, matching the point-cloud representation; promote those values to float64 for coordinate-to-index arithmetic; compute `floor(point * 20)`; reconstruct center as `(index + 0.5) * 0.05`. For each exact recorded odometry pose, compute the minimum Euclidean distance over **all** original PCD points and **all** reconstructed voxel centers. Duplicate centers do not change a minimum. No local crop, sensor aperture, visibility, map age, occupancy probability, or footprint mask is applied.

Distances below are meters; elapsed time is seconds. Distances are rounded to nine decimal places for display.

| Sample | Elapsed | Analytic solid clearance | Nearest original PCD point | Nearest full-PCD-derived voxel center | Center within 0.2 m? |
|---:|---:|---:|---:|---:|:---:|
| 1369 | 13.692034 | -0.000404330 | 0.201004342 | 0.191998237 | Yes |
| 1370 | 13.701994 | -0.008268391 | 0.192652750 | 0.183019824 | Yes |
| 1371 | 13.711639 | -0.013841643 | 0.187813307 | 0.177724025 | Yes |
| 1372 | 13.722338 | -0.016980396 | 0.183794361 | 0.180040039 | Yes |
| 1373 | 13.732317 | -0.017612404 | 0.184287495 | 0.189804041 | Yes |
| 1374 | 13.742283 | -0.015566964 | 0.184820164 | 0.193844017 | Yes |
| 1375 | 13.751746 | -0.011017132 | 0.190959772 | 0.197202525 | Yes |
| 1376 | 13.762838 | -0.004013968 | 0.196080814 | **0.207151538** | **No** |

Two distinct representation effects are visible:

1. At sample 1369, the analytic side surface contacts the body by about 0.404 mm, but no discrete PCD point is within the body (nearest 0.201004342 m). This is a sampled-surface versus closed-solid discrepancy. It does not erase the native PCD contact episode at subsequent samples.
2. At sample 1376, an original PCD point is inside the body, but every reconstructed voxel center is outside it. This is a concrete point-to-center quantization false negative, even with the complete static point set supplied to the reconstruction.

Sample 1376 details:

- Body center: `(15.578557987211868, 23.68350933860378, 1.495017459116918)`.
- Nearest original PCD point: `(15.753352165222168, 23.594797134399414, 1.5)`; distance 0.196080814 m.
- Nearest center among all quantized PCD points: `(15.775, 23.625, 1.525)`; distance 0.207151538 m.
- These two minima need not originate from the same PCD point. Each is independently minimized over the complete point set.

At the deepest analytic contact (sample 1373), the nearest reconstructed center is 0.189804041 m away, still inside the body. Seven of the eight analytic-contact poses have at least one reconstructed center inside the body. **Quantization alone therefore does not explain a missed whole episode under the assumption that all relevant full-PCD points were present as occupied cells and the predicate was evaluated at those poses.**

Minimal reproduction of the numerical operation, after loading the listed PCD and contact CSV rows:

```python
points = np.loadtxt(pcd_path, skiprows=11, usecols=(0, 1, 2), dtype=np.float32)
points64 = points.astype(np.float64)
centers = (np.floor(points64 * 20.0) + 0.5) * 0.05
for row in contact_rows:
    pose = np.array([float(row[k]) for k in ('x_m', 'y_m', 'z_m')])
    raw_distance = np.linalg.norm(points64 - pose, axis=1).min()
    center_distance = np.linalg.norm(centers - pose, axis=1).min()
    print(row['sample'], raw_distance, center_distance)
```

The native observer rounds/casts positions differently from the independent CSV replay; its 0.183795 m minimum and the replay's 0.183794361 m agree at the relevant scale. Neither this sub-micrometer discrepancy nor the 1e-9 tangency tolerance explains the reported millimeter-scale representation differences.

## Limits and unresolved causal question

- This is a **geometric counterfactual with full static PCD availability**, not a reconstruction of the actual committed sensor map. It neither asserts that every static point was observed nor that any particular missing point caused the contact.
- The native contact event has empty `raw_cloud_local_1m`, `occupancy_local_5m`, `frontend_path`, and `committed_trajectory` arrays; native `occupancy_messages=0`. These are missing observer evidence, **not proof that the planner's internal map was empty or that the sensor returned no points**.
- Logs show sensor frames and map/trajectory commits near the event, but those scalar records do not establish membership of the specific neighboring voxels in the committed map used by a particular guard query.
- The counterfactual does not reproduce sensor occlusion/aperture, float32 rendering/transforms before map insertion, occupancy probability thresholds, map snapshot version/age, trajectory-versus-executed-pose timing, guard sample selection, or initial-footprint masking.
- Analytic and native contact metrics are received-odometry-sample observations, not a continuous swept-body proof.
- Full voxel-center distance is a point test, not a voxel-AABB/body intersection test. A 0.05 m cube permits point-to-center displacement up to `sqrt(3) * 0.025 ≈ 0.04330127 m`; this geometric bound is explanatory only, **not a proposed threshold adjustment**.

Next evidence needed: a scoped trace tying the relevant sensor returns and voxel occupancy to the exact committed map snapshot and physical-body/trajectory guard decisions around samples 1369–1376. Until then, distinguish the confirmed contact and confirmed representation false negatives from unproven missing-data, stale-map, masking, or guard-timing causes. No blanket fix or tuning recommendation follows from this audit.
