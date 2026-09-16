# C18 six-arm command plan (not executed yet)

Only execute after the root agent confirms the combined simulator build has
finished and grants the isolated, serial ROS preflight window.

Common environment: source `/opt/ros/humble/setup.bash` and
`/root/super_ws/install/setup.bash`; set `ROS_DOMAIN_ID=190`,
`DISPLAY=unix:0`, `XAUTHORITY=/root/.Xauthority`. The fixture itself selects the
direct installed binary, exact opt-in flags and composed profiles. No launch,
mission, goals or commanded movement are started.

Command pattern (replace the three placeholders with one row below):

```bash
/usr/bin/python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py \
  --out-dir /root/super-sector-filter/results/adaptive_cpu40_20260916/static_latched_once_preflight/ARM \
  --poll-ms 1 --durable --latched-once --reader-qos durable \
  --composition COMPOSITION --sequence SEQUENCE \
  --expected-sha256 b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f
```

| Arm directory | COMPOSITION | SEQUENCE |
| --- | --- | --- |
| ros_standalone_reader_first_attempt1 | standalone | reader-first |
| ros_standalone_late_attempt1 | standalone | late |
| ros_full_reader_first_attempt1 | full | reader-first |
| ros_full_late_attempt1 | full | late |
| ros_adaptive_reader_first_attempt1 | adaptive | reader-first |
| ros_adaptive_late_attempt1 | adaptive | late |

Keep each console log beside its arm directory, named `ARM.console.log`. Preserve
all attempts and failures. Each arm's `result.json` and `simulator.log` must stay
together. Never retry automatically or reuse an existing output directory. If a
fixture bug blocks protocol execution, report it and preserve that attempt
before any separately authorized corrected attempt.

The actual RViz display/reader test is separate and must not run concurrently in
this domain: the transport fixture intentionally requires exactly its own reader
count during disconnect/reconnect. Root coordinates both windows.
