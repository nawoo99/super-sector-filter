# Urban Adaptive repair smoke: collision followed by trapped recovery

Read-only diagnosis, 2026-09-26. No frozen cohort code, parameters, binary, or result was edited. This note is outside the active cohort. **The repaired candidate is not ready for production or a replacement 210-flight campaign.**

## Outcome and primary evidence

Attempt: `/root/super-sector-filter/results/scenario7_repair_smoke_20260926_v1/preflight/urban_blocks_u01/r01_run60005`, Adaptive ON. It timed out at 180 s, reached 2/5 waypoints, and recorded one solid contact episode. The completed solid audit has 18000 received samples, 15673 contact samples, minimum distance-to-solid minus body radius -0.2 m, `completion=true`, `audit_valid=true`. Negative -0.2 here means the center is inside a solid; it is not a measured penetration depth.

Stable sidecars are under the attempt's `artifacts/urban_blocks_u01_run60005_adaptive.attempt1.*`. Original scratch was `/tmp/scenario7_n10_42a4e0p2`. References below use the copied `stack.log` and `odometry.csv`; line numbers agree with the scratch at analysis.

The obstacle is `building_12`: center (19,7), size 6 by 8 m, z in [0,6]. Its closed-solid bounds are x in [16,22], y in [3,11], z in [0,6]; body radius is 0.2 m.

## Entry and recovery chronology

| Evidence | Confirmed observation |
|---|---|
| Odom sample 2327, elapsed 23.2748587 s | (22.2036556,9.9161950,1.6555658), clearance +0.0036556 m. |
| Odom sample 2328, elapsed 23.2844708 s; header epoch 1790416722.469237184 | First sphere contact at (22.1585032,9.8637323,1.6479543), clearance -0.0414968 m; velocity (-4.4258,-5.1119,-0.7307) m/s. |
| Odom sample 2332, elapsed 23.3239794 s | Center crosses inside the x=22 wall: (21.9809319,9.6630229,1.6219297), clearance -0.2 m. |
| Stack 2220 / epoch 1790416722.511262934 | Guard commits generation 96, map 256, **after contact has begun**. |
| Stack 2230 / epoch 1790416722.689722428 | Candidate backup rejected near far-side point (16.037,4.200,1.787), not the entry face at x=22. |
| Stack 2231 / epoch 1790416722.762882293 | Guard commits generation 97, map 258; later live checks still print SAFE. |
| Stack 2240–2249 / epoch 1790416722.889481952 onward | Recovery Full cycle 4 is armed, about 0.420 s after first contact. Live failure references (16.399,4.482,1.889). Brake candidates are UNOBSERVED; no brake command is initially published. |
| Stack 2263 / epoch 1790416723.319561811 | Stationary hold is certified at approximately (20.126,7.849,1.860), already inside building_12. |
| Stack 2271 / epoch 1790416723.441675247 onward | A* starts returning TIME_OUT at its existing 0.1 s budget. Subsequent vertical/local recovery moves remain inside the same building. |
| Stack 3592–3608 / epoch 1790416745.0497 onward | Last local escape is attempt 4/4. Four directions are rejected at west/south wall points; a 0.6 m interior move in direction (-0.376,0.927,0) is accepted as generation 110. Every such commit has `footprint_egress=false`. |
| Odom sample 4684, elapsed 46.8449161 s | Last sample with speed above 0.01 m/s. Final stationary pose is (16.4897547,4.0878216,2.4604105), still inside building_12. |
| Stack 3711 / epoch 1790416746.369563762 | BASE_NO_PATH_EXHAUSTED logs action=certified_hold. A* nevertheless continues to run and time out. |
| Stack 3786–3808 / epoch 1790416747.0716 onward | Full cycle 8 / ACK map 501, certified stationary hold, then repeated async recovery calls with revision 41 and generation 110 unchanged. Goal remains (-24,-13,1.5), about 43.9583 m away. |

The initial wall crossing is a sequence of roughly 0.07 m pose increments at roughly 10 ms intervals, not the earlier G1-style 0.9 m one-step teleport. Do not overstate this as proof of perfectly continuous command timing: within the broader 22–24 s window there are isolated up-to-0.140446 m increments and apparent finite-difference speed 14.42 m/s, including one after the body is already inside. Those need command/pose timestamp alignment to classify. The first contact itself is directly visible as a gradual crossing in samples 2326–2332.

Five TRAJ_HANDOFF_REJECT events occur earlier (epochs 1790416703.6808, 6709.3032, 6718.2303, 6718.2818, 6719.3981). The last is 3.071 s before first contact. Later accepted generations resume after each rejection. No handoff rejection is proximal to the first contact or final stall, and no initial-footprint exemption is active. This rules out blaming a contemporaneous handoff/receipt rejection for the stationary tail; it does **not** isolate counterfactual trajectory changes caused by the repaired controller earlier in the flight.

## Route existence versus the trapped start

The previous Urban Adaptive ON, `scenario7_n10_20260925_213533_3120932/preflight/urban_blocks_u01/r01_run40005`, completed 5/5 in 57.14 s with zero analytic contact episodes. On the corresponding right-to-left leg it crossed x=22 at elapsed 30.4739408 s, y=12.1954153, z=1.2334528, with +0.9954153 m clearance, outside the building's north wall. The smoke crossed x=22 near y=9.66, inside its footprint. A route through the map exists; this is not evidence that the mission or street geometry is inherently infeasible.

Once the center is inside this closed solid, however, **there is no fully collision-free trajectory starting at that state**. The physical solid alone establishes this; no A* budget increase can repair that safety violation. The ROG-map occupancy snapshot was not saved, so we cannot prove exact A* free-space connectivity or identify which sampled wall cell blocked every search. The observed interior hold, wall-direction rejections, unchanged generation, and repeated timeouts are consistent with a surface-map trapped component. Do not present that inference as an exact replay of A*'s map.

## Actual unknown-space policy and missing evidence

Loaded config (stack line 6): `/root/super_ws/scenario7_repair_20260926/install/super_planner/share/super_planner/config/static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml`.

- Logs load `fsm/trajectory_guard/unknown_as_occupied=1` (lines 50 and 266), but `super_planner/frontend_in_known_free=0` (line 259).
- `SuperPlanner::PathSearch` selects UNKNOWN_AS_FREE when that frontend flag is false (`super_planner.cpp:4227`).
- Commit validation calls `validatePositionTrajectory(..., allow_clearance_escape, false, ...)` (`super_planner.cpp:1741`): its effective `unknown_as_occupied` argument is false.
- Live committed-trajectory refresh likewise passes `true, false, ...` (`super_planner.cpp:936`), so it also allows unknown cells despite the configured true value.
- Brake validation separately passes `cfg_.trajectory_guard_unknown_as_occupied` (`fsm_ros2.hpp:2710`), explaining a genuine policy distinction; its first moving brake candidates were rejected UNOBSERVED.
- The startup demand-policy log explicitly declares `stop_policy=sampled_unknown_allowed_clearance_margin_allowed` (stack line 343).

These are confirmed call-site semantics, not a claim that the entry face was specifically UNKNOWN in this flight. There is no ROI cloud/map-query trace for building_12, so missing sector observation, ray/update effects, stale or incorrect free classification, and sampled occupied-wall coverage cannot yet be distinguished. Raw CIRI shadow was disabled and no static-solid oracle fed the planner. The guard's SAFE/commit evidence contradicts the independent solid contact observation; that contradiction is the primary unresolved safety defect.

## Timing comparison

Observer timing improved in this attempt under the unchanged gates:

| Metric | Original Urban ON | Repair Urban ON |
|---|---:|---:|
| Received odometry | 97.49598 Hz | 100.00115 Hz |
| Header interval p99 | 20.00678 ms | 10.40510 ms |
| Header maximum | 20.14739 ms | 10.69103 ms |
| Receipt interval p99 | 16.00513 ms | 11.01283 ms |
| Receipt maximum | 25.21728 ms | 12.07812 ms |
| FSM main callback | 99.92698 Hz | 97.52483 Hz |

All seven sensor/odometry timing checks and the command callback check pass in the repair summary. The FSM-main callback check fails, so overall small_pool_timing remains false; callback coverage is valid. The old summary instead failed odometry cadence and header p99. These are distinct trials with different paths and 57 versus 180 s durations, not a controlled benchmark proving timing causality. The repaired observer did not mask the new collision or timeout.

## Bounded recommendations, not implemented

1. Treat this attempt as a retained collision plus mission failure; do not raise A* timeout or loosen occupancy/contact/timing thresholds to make it appear complete. Its ON failure must keep corresponding OFF runs ineligible.
2. Close the confirmed policy split with an explicit, versioned unknown-space admission contract shared by candidate commit, live refresh, and certified stopping distance. Before implementing, add an offline test in which a config-true candidate's swept body enters UNKNOWN and require a fail-closed result. If a limited unknown-space exception is intentionally retained, make it explicit and bound it to a currently observed stopping envelope, not the entire trajectory. A global boolean flip without replay may break liveness and is not established as the full fix.
3. Capture a bounded diagnostic ROI around building_12 for a separate future cohort: actual acquired points, raw/inflated cell states and their update provenance, candidate/live guard queries, pose and command times. Replay the first-entry interval (epoch 1790416721.9–1790416722.9) to determine why the x=22 face was not rejected before crossing. Keep that observer independent of planner decisions; do not add static geometry as hidden planner feedback.
4. The repeated-search CPU tail has a concrete bounded repair opportunity: `PathSearch` runs `pointToPointPathSearch` at line 4240 **before** testing the exhausted counter, while the exhaustion branch at line 4380 only sets `guard_topology_no_path_failures_=-1`. Add an explicit exhausted-stopped-episode result before dispatching another identical full search, retaining certified hold and failure status. Reset only for a genuine new goal/state/topology/observation change, not periodic retransmission of the same goal or a map-version tick alone. Test repeated identical exhausted requests consume no further search budget and genuine changed input permits a bounded retry. This fixes wasteful retry behavior, not the preceding solid collision or mission completion.

## SHA-256 evidence bindings

All relative repair artifacts below are under the attempt identified above.

- `adaptive_summary.json`: `13d4c51baa1e5f64519fc5052416ff0c4c4323d2192d36e5224ce241aa1772f0`
- `artifacts/urban_blocks_u01_run60005_adaptive.attempt1.odometry.csv`: `889677d463bd4d58241a19d152e452850380a3ccf39ec98ff668f2af6da49550`
- `artifacts/urban_blocks_u01_run60005_adaptive.attempt1.solid_audit.json`: `c73f943d9a9431d733e04d96d68b96d21efb121c15bc76373be26385bb828894`
- `artifacts/urban_blocks_u01_run60005_adaptive.attempt1.stack.log`: `37be4748ca64dbb97537d9a34b147c589689fb294d445d3c409940092b5e5d66`
- Original `adaptive_summary.json`: `6ad610cbce52a8427c6bbd9fcf26e44793d97cf796ab79da6a14ececff0640a1`
- Original `artifacts/urban_blocks_u01_run40005_adaptive.attempt1.odometry.csv`: `b1583f364340422688bc59f41bef031b73c63d16697ebf667a8b1e01aeec44e8`
- Runtime `pcd/seed_maps/urban_blocks_u01_geometry.json`: `f40398b0b3a555c96c0acc1f323fc1547cf355a281ce0ec0a225b678c246c8ed`
- Runtime `super_planner/src/super_core/super_planner.cpp`: `73badbd2f56417b411da4d38deefbe4b38eb6a5bab928c86939f7a142eb287b2`
- Actual overlay event-recovery YAML above: `d853803fb53088506e25c273564dec7b0b759e264c61cec64b0387d16ae84786`
