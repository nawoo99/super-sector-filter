# Guard-v3 read-only preflight input audit

Result: **PASS**, checked 2026-09-26 before the new smoke campaign. This is an input-preservation and mirror audit, not a flight-safety or production-readiness claim. No source, script, test, map, or mission was edited; no build, compilation, or flight was launched by this audit.

## Runtime and mirror equality

All 20 requested runtime/mirror pairs are byte-identical (SHA-256 comparisons). Runtime root is `/root/super_ws/src/SUPER`; mirror root is `/root/super-sector-filter/super_patches/native_seedmap_campaign`, using the existing package/type directory mapping.

| Group | Runtime-relative paths |
| --- | --- |
| ROG, 3 | `rog_map/include/rog_map/rog_map_core/config.hpp`; `rog_map/src/rog_map/prob_map.cpp`; `rog_map/test/near_range_wall_hole_test.cpp` |
| Async FSM, 6 | `super_planner/include/fsm/fsm.h`; `super_planner/src/super_core/fsm.cpp`; `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`; `super_planner/include/fsm/async_from_rest_planning.hpp`; `super_planner/test/async_from_rest_planning_test.cpp`; `super_planner/test/async_from_rest_source_contract_test.py` |
| Stop supplement, 2 | `super_planner/test/stop_margin_prefix_supplement_test.cpp`; `super_planner/test/stop_margin_prefix_supplement_test.py` |
| Scripts, 4 | `mars_uav_sim/perfect_drone_sim/scripts/run_scenario7_v2_entry_probe.py`; `.../run_scenario7_guard_v3.py`; `.../run_scenario7_guard_v3.sh`; `.../scenario7_guard_v3_cpu_compare.py` |
| Script tests, 2 | `mars_uav_sim/perfect_drone_sim/test/test_scenario7_v2_entry_probe.py`; `.../test_run_scenario7_guard_v3.py` |
| Profiles, 3 | `super_planner/config/static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml`; `.../static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearhit_v3.yaml`; `.../static_seedmaps_guard_viability_tight_v7_event_recovery_v1_nearhit_v3.yaml` |

The repository launcher `/root/super-sector-filter/scripts/native_campaign/run_scenario7_guard_v3.sh` is also byte-identical to its runtime and mirror copies: `7a6d78146f813c1d1e87f19643fa46cc989be3bf6f9ad076d9c47fb2f4c222d1`.

All three candidate profiles are installed under `/root/super_ws/scenario7_guard_v3_20260926/install/super_planner/share/super_planner/config/` and match runtime/mirror bytes. Removing the following single added line from each candidate recovers its corresponding legacy base profile byte-for-byte:

```yaml
    occupancy_only_min_range: 0.1 # Sensor blind distance; keep free-ray/startup radius.
```

No CIRI key is present in any of these three candidate profiles. The unchanged `super_planner/include/fsm/config.hpp` retains `trajectory_guard_raw_cloud_ciri_shadow_en{false}` at line 142 and loader default `false` at lines 324–325. Its SHA-256 is `3376248f9d6424475815ac08c6bcf3e382f401270d58a525461c03674db63200`. This confirms the explicit CIRI shadow switch remains default-off; it is not a claim that unrelated existing corridor construction was removed.

## Preserved inputs

Baseline: `/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/frozen_inputs_and_evidence.json`, SHA-256 `bf2fd286f18231f8761507d56ceed9cbf71b4bea689cd6baf7742571f3df98b1` (2,519 recorded paths).

787 protected recorded paths were rehashed with zero changed or missing files. Selection covered seed-map PCDs and geometry, all recorded perfect-drone configuration paths, mission-planner paths, scenario7 mission definition/runtime files and proofs, waypoint-related paths, map manifests, unchanged legacy base profiles, and FSM configuration. In particular, each of the seven maps has its runtime PCD, analytic geometry (CSV or JSON), and sensor configuration checked: `gapfree_d1_m01`, `gapfree_d1_m02`, `gapfree_d1_m03`, `gapfree_d1_m04`, `gapfree_d1_m05r2`, `urban_blocks_u01`, `forest_cluster_f01`. No map or waypoint change was found.

All 851 recorded paths under the runtime source root and native-campaign mirror root were also compared. The only changed recorded runtime paths are the five authorized existing files:

- `rog_map/include/rog_map/rog_map_core/config.hpp`
- `rog_map/src/rog_map/prob_map.cpp`
- `super_planner/include/fsm/fsm.h`
- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`
- `super_planner/src/super_core/fsm.cpp`

Two corresponding mirrors were already present in that older inventory and differ as expected: `rog_map_src/rog_map/prob_map.cpp` and `super_planner_include/ros_interface/ros2/fsm_ros2.hpp`. Other current-turn additions are covered by the explicit 20-pair check above, not falsely presented as old-inventory entries. No unexpected changed recorded source/mirror path was found. This bounded audit did not exhaustively hash every old binary or result artifact in the 2,519-entry inventory.

The preserved old v2 archive `/root/super_ws/scenario7_guard_v2_20260926/install/rog_map/lib/librog_map.a` still has SHA-256 `3fc3f5561d70668874b446c6a51e067311c38e17c9eb39e9fe4c5581d73b5860`, identical to the baseline actual-library regression record.

## Important current source identities

| File | SHA-256 |
| --- | --- |
| ROG config.hpp | `e819a7bd308a23da4e92622a19c7a85d5374471d0920ff8b7499e271ddf57c37` |
| ROG prob_map.cpp | `497c4fa761d08c5db38bd6c8b4bc88da313572039acf4b16ea530afeef6b3b4a` |
| near_range_wall_hole_test.cpp | `8eef464f963e135a13f4016e5b82c64353b75789b3c4512c00e485a7e87ea9be` |
| FSM fsm.h | `1e944a48dc8cacc152d5d0e0542fd2c8bcb4b3efbdfe0975f0b505d49960678d` |
| FSM fsm.cpp | `22352f9d291302ea7c3b3ce1aba330d054a61843d3fdf96e4f68bcc9ccccf6ce` |
| FSM fsm_ros2.hpp | `eda99ea586ef6c464322b3c6f52da4d10771677d28b2e428ae018a32dd57cb37` |
| async_from_rest_planning.hpp | `5666247a266f930f4485db88b2a34f2faf99ece6efbc6edbd7d7934e4adeb03f` |
| run_scenario7_guard_v3.py | `ba241088c6533703939f494606789cd9d7febe6acc7950bdd89532da8ed705b3` |
| scenario7_guard_v3_cpu_compare.py | `4281da9f7c34f84ce05fe438324db7a87457ce3b37bea919ba2799b9afd08fb0` |

Serial overlay-build completion and subsequent campaign admission/runtime gates remain the root controller's responsibility. This report does not substitute for them.
