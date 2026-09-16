# C18 latched-once transport preflight

Status: all six final `*_canonical_attempt1` ROS arms PASS. Original first Full
arm failed; preserved padding diagnostics and repair are in PADDING_DIAGNOSIS.md.
No failed attempt was reclassified. Final-build standalone/Full/Adaptive each
pass reader-first and late, with all retained/additional/reconnected readers.

This is a new, explicitly authorized publisher AND reader QoS migration. It does
not retroactively pass Plan A's failed best-effort reader compatibility checks.
Those original six arms remain in `../static_durable_preflight/` unchanged.

## Fixture contract

Runtime source:
`mars_uav_sim/perfect_drone_sim/test/static_pc_late_subscriber_test.py`.

New `--latched-once --durable --reader-qos durable --poll-ms 1` enables
`SUPER_STATIC_PC_LATCHED_ONCE=1`, with durable1, two-phase0 and cached-executor0.
The parameter1 is retained for compatible opt-in validation; actual static poll
must report0. No static timer, subscriber-count poll or periodic map resend is
allowed. Existing source10Hz, odometry and planner behavior remain unchanged.

`--composition standalone|full|adaptive` selects the real installed binary,
without a mission publisher, goals or command injection. Composed modes use
side-executor2 and dedicated-static executor1, plus the source-acquisition v2
Full or Adaptive45 configuration. The fixture observes finite, stationary
odometry and requires no position command. This is no-flight transport evidence,
not navigation success, callback timing or CPU performance evidence.

Each mode will be run once with `--sequence reader-first` and once with `late`:

1. Initial/first-late reader receives complete241490-point world-frame geometry.
2. Additional simultaneous reader receives the same retained sample.
3. Removing the additional reader causes no new delivery to the first reader.
4. Disconnect all readers, then reconnect: retained sample is received again.
5. All three readers receive exactly one sample, full payload SHA
   `b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`, identical
   layout/bytes and exact original positive publication timestamp.
6. Actual publisher QoS must be Reliable/TransientLocal/KeepLast1, separately
   checked against publisher getter and available graph fields. Unknown graph
   history/depth remain explicitly unverified, not guessed.
7. Exactly one initial publication marker; all cumulative counters remain
   publications1, timers0, poll-callbacks0, with identical points/bytes/stamp.
   At least two existing cadence summary records must span5s, using exact
   nanosecond log timestamps. Hold at least11s after observing the initial
   publication. No new timer is introduced to gather evidence.
8. Source cadence must remain9.5–10.5Hz. Direct child receives one SIGINT and
   exits0; TERM/KILL fallback is bounded and makes the test fail. Domain190,
   hard90s work deadline, no overwriting or automatic reruns.

Result schema includes `composition`, `latched_once`, `publisher_actual_qos`,
`no_flight_observation`, `clouds`, `sensor_cadence_hz`, `exact_child_reaped`, and
`latched_once_audit` with `valid`, `checks`, `publication_count`, `summary_count`,
`initial`, `observation_before_shutdown_s`, `steady_summary_span_s`.

Separate actual RViz evidence is owned by the frontend-review agent. It must use
the migrated config and real PointCloud2 display; this Python fixture does not
claim to validate RViz rendering.

## Offline regression

`test_fixture_audit.py` AST-loads the pure audit function without importing ROS or
starting processes. It exercises valid evidence and rejects missing/duplicate
publications, changed counters/stamps, any polling/timer, short/backward summary
windows, missing readers, duplicate delivery and wrong SHA/layout/frame.
It is only parser/contract regression; actual DDS/renderer proof remains pending.
