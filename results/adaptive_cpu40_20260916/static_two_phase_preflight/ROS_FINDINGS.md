# Two-phase static-PC preflight, 2026-09-16

Rebuilt simulator package PASS5min57s. Four distinct ROS no-flight tests on
domain188, no retries. Same seed1 full241490-point/7727680-byte payload and
best-effort/volatile QoS; no host network/SHM changes. All children exited0.

| Test | Initial complete geometry | Later transition | Whole test |
|---|---|---|---|
| Legacy1ms reader-first | SHA/layout valid | Second persistent reader timed out | FAIL |
| Two-phase reader-first | Identical SHA/layout valid | Second persistent reader timed out | FAIL |
| Legacy1ms late reader | No receipt | First persistent late reader timed out | FAIL |
| Two-phase late reader | No receipt | First persistent late reader timed out | FAIL |

Every received payload SHA256:
`b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`.
Two-phase reader-first handoff at5.102043152s, actualfast_timer_canceled=1.
Later failed phases stop each suite, so subsequent disconnect/reconnect steps
were NOT exercised; don't report them as passed. Actual bootstrap send counts
remain scheduler-dependent. This is not the rejected single-shot bootstrap.

Decision declared BEFORE C13 flight: permit a **startup-ready CPU diagnostic**,
not general adoption. Both legacy and candidate late-delivery failures remain
unresolved. The runner now explicitly disqualifies this prototype from final
40% target acceptance and from blessing an unprofiled small-pool confirmation,
even if its raw CPU reduction reaches40%. Initial truth readiness and all flight
source/recovery/timing checks are still mandatory. Default option stays off.

Raw per-test result.json/simulator.log/console logs are preserved in this folder.
