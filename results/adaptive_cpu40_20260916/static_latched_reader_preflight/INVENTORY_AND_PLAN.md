# C18 static-map reader migration: inventory and proposal

2026-09-16. User authorized an opt-in static-map publisher/reader interface migration and removal of the static 1 ms poll, using the C15 baseline. Root owns the publisher/model and benchmark runner. This agent owns only viewer configs, an explicit viewer launch surface, and RViz validation. Existing profiles and default behavior must remain unchanged.

## Local inventory

Searched the active SUPER checkout and mirror/scripts for global_pc references. No active planner, frontend, mission, or campaign-monitor subscription to /global_pc was found. The native monitors subscribe to acquired/local clouds and load the static PCD directly for independent collision checking; their geometry checks must not be switched to the visualization topic.

| Consumer or surface | Current behavior | Proposed action |
| --- | --- | --- |
| perfect_drone_sim/rviz2/watch_sector.rviz | GlobalCloud requests Best Effort / Volatile / Keep Last 3 | Preserve; add watch_sector_durable.rviz |
| perfect_drone_sim/rviz2/top_down.rviz | Same GlobalCloud QoS | Preserve; add top_down_durable.rviz |
| perfect_drone_sim/rviz2/fpv.rviz | Same GlobalCloud QoS | Preserve; add fpv_durable.rviz |
| perfect_drone_sim/rviz2/benchmark.rviz | Same GlobalCloud QoS | Preserve; add benchmark_durable.rviz |
| perfect_drone_sim/rviz/*.rviz | ROS1 configs with /global_pc | Out of scope; preserve |
| scripts/watch_native.sh | Selects the legacy watch_sector.rviz and separately starts simulator/filter | Preserve existing script; new explicit reader-only launcher avoids silently changing legacy workflow |
| mission_planner/launch/benchmark_seedmap.launch.py | No RViz process; selectable composition modes | Preserve; new viewer launch runs independently after any simulator launch |
| mission_planner/launch/click_demo.launch.py | Starts legacy top_down and fpv viewers | Preserve |
| mission_planner/launch/benchmark_dense.launch.py and banchmark_high_speed.launch.py | Start legacy fpv viewer | Preserve |
| scripts/super_watch.rviz, scripts/watch.sh, scripts/ui_run.sh | No /global_pc subscription in their viewer profile | No migration needed |
| perfect_drone_sim/test/static_pc_late_subscriber_test.py | Test-only explicit legacy or durable reader; existing transition fixtures | Separate agent owns C18 one-shot + exact-SHA extension |
| results/.../executor_preflight/global_pc_prewarm_probe.py and old result prototypes | Historical diagnostics, not production readers | Preserve as historical evidence; do not silently reroute |

## Minimal proposed interface

Add four durable copies, changing only the /global_pc Topic QoS fields to Reliable / Transient Local / Keep Last 1. All other topic QoS, rendering options, frame IDs, displays, and cameras remain byte-preserved in the copy. The existing four legacy files remain byte-identical.

Add perfect_drone_sim/launch/static_map_view.launch.py, a reader-only launch with durable:=false default and view:=watch_sector (allowed choices: watch_sector, top_down, fpv, benchmark). durable:=true selects the matching *_durable.rviz. It does not start a simulator, set publisher environment, send a goal, or mutate planner settings. The durable viewer requires the separately opted-in reliable/transient-local publisher. This makes late start and viewer reconnect explicit and testable without adding RViz to CPU comparison runs.

Mirror new files under super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim/{rviz2,launch,test}. The old flat watch_sector.rviz mirror is historical and remains unchanged. The package already installs launch and rviz2 directories, so no CMake edit is required for these configs/launch files.

## Validation before any flight

1. Offline YAML/structural check: exactly one /global_pc Topic mapping per profile; durable copy differs only in depth/reliability/durability; old profiles retain original SHA; other display/topic fields unchanged. Parse launch and test default/explicit profile selection and invalid inputs without launching ROS.
2. Actual RViz validation, not merely a Python subscriber: load the real durable config in the installed RViz display implementation; verify the GlobalCloud display has Reliable / Transient Local / Keep Last 1 configured and graph discovery reports actual requested reliability/durability. History/depth may be unspecified by the installed DDS graph and must not be falsely claimed from unknown graph fields.
3. Start the viewer only after the simulator has published its sole static map, then require a successful GlobalCloud PointCloud2 display status and full expected point count. Close it, wait for subscriber removal, restart it, and require the same result. No new application publication is allowed. Preserve per-attempt logs and screenshots when rendering is available.
4. The other agent's Python fixture independently verifies the exact point payload SHA, layout, frame, point count and reconnect phases against a successful legacy sample. RViz display success alone is not a byte-equality proof; the two pieces of evidence are complementary.
5. Keep both ordinary and composed Full/Adaptive paths in the publisher fixture; no mission/goals/flight. Root coordinates build and ROS process ownership. No simulator or RViz process has been launched by this proposal.

Installed RViz C++ SDK headers expose VisualizationFrame, VisualizationManager, display/property status, and the real PointCloud2 plugin. A small out-of-repository-built harness is a feasible way to inspect actual display state while loading an unchanged durable config. A static YAML check alone will not be reported as RViz validation.
