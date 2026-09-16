# C18 final acceptance

`acceptance.json` binds six final canonical transport results and actual RViz
late/reconnect evidence, all raw logs/screenshots, source/config/installed binary
hashes. `acceptance_validation.log` records detailed PASS. It is an opt-in new
publisher AND reader contract; old volatile readers are not claimed compatible.

All six transport arms: exact241490 points/7727680 bytes, fixed full payload SHA,
same original stamp within a publisher lifetime, publications1/timers0/polls0,
>=2 steady summaries spanning>=5s,10Hz, stationary odometry/commands0, cleanexit0.
Actual RViz: exact same data/stamp after late connect and viewer restart, real
PointCloud2 Points/transform/QoS checks and visible Ogre render-target captures.
Simulator restarts are NOT persistent-history continuity claims.

Optimized and ASan/UBSan policy39 checks pass,83 focused Python tests pass,
23 transport-fixture regression tests and5 reader-config tests pass. Raw logs
preserve earlier27-check versions and intermediate tests. Original Full payload
failure, padding diagnostics, QWidget screenshot limitation and runner setup
failure remain separate and are not suppressed or counted as flights.

Actual seed1 run9319 is in `../c18_latched_static_profile_run9319/`; each mode
one flight. Both complete/contact0 and all acceptance checks pass. Mean CPU
reduction31.4506%, cumulative29.5387%, A/Ftime1.032487. **40% unmet**, no extra
unprofiled flight. Static executor stays included in total accounting despite
zero sampled CPU. See main CPU40 document for exact means/times and limitations.
