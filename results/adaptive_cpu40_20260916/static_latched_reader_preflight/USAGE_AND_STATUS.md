# C18 reader migration: explicit usage and validation status

All legacy RViz files, old viewer scripts, mission launch files, and default profiles remain unchanged. The new durable profiles differ only in the /global_pc Topic QoS: Reliable, Transient Local, Keep Last 1. The publisher opt-in is separate and common to Full/Adaptive.

## Matching publisher and viewer

The new publisher contract requires these explicit simulator-process settings:

~~~bash
export SUPER_STATIC_PC_DURABLE=1
export SUPER_STATIC_PC_LATCHED_ONCE=1
export SUPER_STATIC_PC_POLL_MS=1
export SUPER_STATIC_PC_TWO_PHASE=0
export SUPER_STATIC_PC_CACHED_EXECUTOR=0
~~~

POLL_MS=1 is the required requested base setting; with LATCHED_ONCE=1 the effective static polling rate is zero because no static timer is created. The source LiDAR, odometry, and control cadence are not changed by this reader interface. The root's runtime marker records the effective values.

After launching the simulator separately with the above settings, use:

~~~bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
ros2 launch perfect_drone_sim static_map_view.launch.py durable:=true view:=watch_sector
~~~

Allowed views: watch_sector, top_down, fpv, benchmark. The launcher only starts RViz; it does not set publisher environment, start simulator/planner/mission, or send goals. It can be started after the map publication and restarted while the same publisher remains alive. The default durable:=false selects the untouched legacy viewer and is intended for the untouched legacy publisher mode.

For direct source-config use:

~~~bash
rviz2 -d /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/rviz2/watch_sector_durable.rviz
~~~

Old volatile readers are not promised retained historical samples from the one-shot publisher. Selecting the durable viewer against a legacy best-effort/volatile publisher is also unsupported because the requested QoS is stronger than the offer. This is an explicit interface migration, not an invisible compatibility claim. No CPU benchmark includes RViz.

## Offline validation completed

Five offline config/launch tests passed on their first attempt; the all-view test has subcases for all four profiles. It checks exact byte differences, full parsed-YAML equality outside static-map QoS, unchanged world frame, old defaults, strict argument validation, reader-only actions, and missing-install failure. See offline_config_attempt1.log. It starts no ROS node or viewer.

The actual RViz SDK probe also configured and compiled successfully on its first attempt, outside the repository:

~~~text
/tmp/super-rviz-static-test.1LtVI4/static_map_rviz_probe
~~~

The authoritative test sources are now runtime-first under perfect_drone_sim/test/static_map_rviz_probe.cpp and static_map_rviz_reconnect_test.py, with exact native_seedmap_campaign mirrors. proposal/ retains synchronized copies and the standalone out-of-repository build configuration. The probe loads the real RViz configuration and real PointCloud2 plugin, observes the existing plugin message signal rather than adding a replacement cloud subscriber, checks full legacy payload SHA/layout/frame/count, requires the Points display status and actual requested graph QoS, and saves an actual rendered screenshot. Configured Keep Last/depth are verified from actual RViz properties; unknown graph history/depth are explicitly marked unknown rather than claimed verified.

Before the first runtime attempt, independent review identified a possible observer-after-subscribe race during RViz initialization. The test now subclasses only VisualizationFrame's documented virtual config-loading hook: it deep-copies the parsed config, temporarily defers GlobalCloud Enabled/Value in memory, installs the observer, then enables the actual display. This prevents consuming the sole retained sample before the test witness exists. It does not alter the on-disk config, topic/QoS, plugin, geometry, or renderer settings. The result explicitly records test_only_subscription_deferred=true. The original successfully compiled source is retained as probe_before_deferred_start.cpp; the new test-only source requires a coordinated lightweight rebuild after the transport matrix, before the first RViz attempt.

The wrapper result schema is static-latched-rviz-v1 with valid, reader_restarts, probes, publisher_no_republish, latched_summary, and publication_counters. A successful chain requires a late viewer and a restarted viewer to display the same single retained point payload/stamp, and final publisher evidence of one application publication, zero static timers, and zero static poll callbacks. Each process is bounded and cleaned up; attempts are never overwritten or automatically retried.

Final actual status: `actual_rviz_render_capture_attempt1` PASS, both late and
reconnected actual PointCloud2 lifecycles show241490 points from exactly one
message, exact original SHA/stamp and requested QoS; clean viewer/simulator
exit0. Screenshots from the actual Ogre RenderWindow show the static map.
The prior `actual_rviz_attempt1` passed delivery/status but QWidget::grab omitted
the embedded3D surface; its blank screenshots are retained and not accepted as
rendering proof. Test-only capture now uses RenderWindow::captureScreenShot,
and the acceptance validator requires that method. No production configuration
or binary changed for the test-tool correction. Six final transport arms and
these actual reader artifacts are bound in `../static_latched_preflight/acceptance.json`.
