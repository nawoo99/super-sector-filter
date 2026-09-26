# Scenario7 stopped-hold v5 retained experiment

Status: default-off implementation and two Urban Adaptive no-retry runs are
preserved. The candidate is not promoted.

## Intended bounded repair

The v4 Urban trace could prove that the vehicle was physically stationary but
could not publish a terminal hold when strict validation returned `UNOBSERVED`
and a full-query retry returned `CLEARANCE_MARGIN`. Candidate v5 is enabled only
with `SUPER_STOPPED_HOLD_V5=1`, and requires v4. It revalidates only a stationary,
physically stable candidate using
`DeferSoftMarginUntilHardChecksComplete`. A soft margin is admissible only after
all hard queries complete; occupied, out-of-map, stale-version and deadline
failures remain rejected. Defaults, maps, radii and CIRI settings are unchanged.

The separate Release overlay is
`/root/super_ws/scenario7_guard_v5_20260927/install`. Planner CTest 4/4, v5
source contracts 3/3, inherited v4 contracts 5/5 and async source contracts
12/12 passed. Runtime and repository-mirror files have identical SHA256 values.
Two wrapper defects were found before any flight: profile paths were supplied
as absolute paths although admission requires profile names, then the child
process lacked the generated `V5_SOURCE` binding. Both were corrected. The
empty first output directory is not a flight result.

## Urban Adaptive repeats

| Metric | run 81400 | run 81401 |
|---|---:|---:|
| Completion | 5/5 | 2/5 |
| Mission time | 71.88 s | 180.01 s |
| Safety contacts | 0 | 1 |
| Minimum body clearance | 0.223 m | -0.148 m |
| Full open / close | 20 / 20 | 3 / 2 |
| Committed Full ACKs | 20 | 3 |
| Full-open time duty | 23.310% | 87.036% |
| Mean end-to-end CPU | 0.4912 cores | 1.3167 cores |
| End-to-end CPU | 36.2141 core-s | 240.2617 core-s |
| Map input | 3.2567 MiB/s | 30.5833 MiB/s |
| Map update | 12.6981 ms/frame | 43.8904 ms/frame |

Both attempts were valid, had no infrastructure retry, passed the speed bound,
and loaded the v5 binary. The first completed without contact. The second made
contact at elapsed 21.562 s near `(21.996, 9.721, 1.553)` at 6.976 m/s, then
timed out after reaching only waypoint 2.

Crucially, neither run exercised v5's new
`publish_physically_clear_margin_hold` action. The successful run used 20
ordinary `publish_certified_hold` actions and the failed run used one. Therefore
the first completion is not causal evidence that the new margin rule repaired
the old v4 hold gap.

## Updated failure analysis

The second run exposes an earlier Adaptive failure. Waypoint 1 to waypoint 2 is
a large direction change. The new goal is accepted while acquisition remains a
45-degree forward sector, and the vehicle accelerates toward the new direction
before a Full observation is requested. The guard remains `SAFE` until the
trajectory becomes visible as `CLEARANCE_MARGIN`; Full opens only at the guard
event, with about 0.48 s TTC. The external static-PCD observer records contact.

The subsequent 87% Full-open duty is a consequence, not the initiating cause.
After stopping near the building, PlanFromRest repeatedly reaches its 0.1 s A*
budget (1,141 logged timeouts), so the Full recovery latch correctly remains
open. Increasing this timeout or repeating the stochastic run does not repair
the missing pre-turn observation.

## Decision

v5 remains default-off and is not suitable for a confirmation campaign. The
next bounded candidate should treat a genuinely new goal while following as an
observation-changing event: retain the new goal, publish a certified stop,
open Full, wait for the exact committed refresh ACK, plan and certify from the
stopped state, and only then return to Sector. Exact goal retransmissions must
remain coalesced and must not trigger this cycle. Full and Fixed Sector behavior
must remain unchanged unless the new opt-in is explicitly enabled.

Compact evidence is in
`results/scenario7_stopped_hold_v5_urban_adaptive_20260927/functional_repeat_summary.json`.
