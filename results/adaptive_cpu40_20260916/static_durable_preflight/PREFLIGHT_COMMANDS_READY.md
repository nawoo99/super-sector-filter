# Completed matrix command history — no rerun authorized

Root completed the combined simulator build and then explicitly authorized six
serial no-flight arms. All are now finished and reaped. Candidate publisher with
existing best-effort readers failed both arms; separate reliable/transient-local
reader diagnostics passed both arms. See `ROS_FINDINGS.md`/`matrix_summary.json`.
The commands below are retained for provenance, not an instruction to rerun.
No automatic retry occurred. Each fixture retained its90s useful-work bound plus
14s bounded cleanup; useful observation time across six arms was≈69.3s.

Legacy observed payload baseline:
`b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`.
Source is `static_two_phase_preflight/ros_reader_first_legacy/result.json`, with
four validated full241490-point clouds and reader-first geometry valid. That
old whole sequence remains failed (second reader); it is not a passed baseline
delivery suite. New candidate geometry must exactly equal this observed payload.

Environment observed at preparation: `DISPLAY=unix:0`,
`XAUTHORITY=/root/.Xauthority`. Do not change host/network settings.

```sh
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
export ROS_DOMAIN_ID=190
export DISPLAY=unix:0
export XAUTHORITY=/root/.Xauthority

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --reader-qos legacy --sequence reader-first --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_control_reader_first_attempt1

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --reader-qos legacy --sequence late --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_control_late_attempt1

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos legacy --sequence reader-first --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_durable_legacy_reader_first_attempt1

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos legacy --sequence late --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_durable_legacy_late_attempt1

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos durable --sequence reader-first --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_durable_reader_first_attempt1

/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py --poll-ms 1 --durable --reader-qos durable --sequence late --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_durable_preflight/ros_durable_late_attempt1
```

Fixture pins durable/two-phase/static-poll environment independently per case;
do not infer it from an inherited shell setting. Candidate metadata acceptance
requires own publisher `get_actual_qos()` history/depth and graph reliability /
durability. Graph historyUNKNOWN or depth0 is explicitly reported unverified,
not mistaken for a contradictory known configuration. Tests never publish a
position command or goal, and the direct standalone simulator child avoids
ros2-run/launch signal forwarding.
