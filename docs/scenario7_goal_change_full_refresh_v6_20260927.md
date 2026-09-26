# Scenario7 goal-change Full-refresh v6 exploratory validation

Status: the default-off implementation fixes the retained Urban turn failure
in two independent Adaptive observations. It is not yet promoted as the final
configuration or population-level evidence.

## Bounded change

Candidate c31 is enabled only with
`SUPER_GOAL_CHANGE_FULL_REFRESH_V6=1` and requires event recovery plus
stopped-departure v4. While `FOLLOW_TRAJ` is active, a genuinely new goal
identity is latched inside the existing pending-goal transaction. Exact goal
retransmissions are ignored. The main callback then enters the existing
certified emergency-stop path before normal FSM processing. Adaptive acquisition
opens Full, waits for the exact committed map-refresh ACK, replans and certifies
from rest, and only then releases the trajectory and returns to Sector.

The goal callback performs no planning, publication or blocking work. Full and
Fixed Sector launch with v6 explicitly disabled. All new behavior remains
default-off. Maps, missions, collision radii, speed limits, CIRI settings and
the v5 stationary-hold policy were not changed.

The separate Release overlay is
`/root/super_ws/scenario7_guard_v6_20260927/install`. Runtime and repository
mirror files have identical SHA256 values. Planner CTest passed 4/4; v6 source
contracts passed 4/4, v5 contracts 3/3, v4 contracts 5/5 and inherited async
contracts 12/12. One attempted `python -m unittest /absolute/path` verification
used an invalid unittest module syntax; the same files were immediately run
directly and passed. This invocation mistake did not start a flight or expose a
product failure.

## Urban Adaptive observations

Both runs were resource-valid, used no retry or replacement, respected the
7 m/s speed bound and recorded zero analytic/static-PCD contact.

| Metric | run 81500 | run 81501 |
|---|---:|---:|
| Completion | 5/5 | 5/5 |
| Mission time | 51.35 s | 67.87 s |
| Safety contacts | 0 | 0 |
| Minimum body clearance | 0.279 m | 0.315 m |
| Goal-change v6 requests | 4 | 4 |
| All Full open / close cycles | 7 / 7 | 17 / 17 |
| Committed Full ACKs | 7 | 17 |
| Full-open time duty | 12.233% | 25.219% |
| Mean end-to-end CPU | 0.4843 cores | 0.4997 cores |
| End-to-end CPU | 25.6039 core-s | 34.8500 core-s |
| Map input | 3.6648 MiB/s | 4.6647 MiB/s |
| Map update | 13.0609 ms/frame | 15.5171 ms/frame |

Each run received five distinct goal identities: the initial goal and four
waypoint changes. Exactly the four changes generated v6 requests. Each request
was followed by a committed Full-refresh ACK and a newer certified trajectory
generation. Periodic mission retransmissions did not generate v6 requests.
Run 81501 had thirteen additional pre-existing trajectory-guard recovery cycles;
all closed successfully and none timed out. This explains its higher Full duty
and longer completion time and is not counted as thirteen extra goal changes.

## Fresh three-mode control

Run 81501 executed Full, Fixed Sector and Adaptive once each under the same
wrapper and retained every outcome.

| Metric | Full | Fixed Sector | Adaptive |
|---|---:|---:|---:|
| Completion | 5/5 | 1/5 | 5/5 |
| Mission time | 54.74 s | 180.01 s | 67.87 s |
| Safety contacts | 0 | 0 | 0 |
| Minimum body clearance | 0.460 m | 0.278 m | 0.315 m |
| Mean end-to-end CPU | 0.7279 cores | 0.2495 cores | 0.4997 cores |
| End-to-end CPU | 41.5247 core-s | 45.4053 core-s | 34.8500 core-s |
| Map input | 10.5752 MiB/s | 0.4379 MiB/s | 4.6647 MiB/s |
| Map update | 31.5168 ms/frame | 8.5286 ms/frame | 15.5171 ms/frame |

Source audit found one `enabled=false` marker and zero v6 requests in each
control. Adaptive had one `enabled=true` marker and four goal-change requests.
Thus the Full/Sector outcomes did not silently receive the new transaction.

Relative to Full, Adaptive reduced mean end-to-end CPU by 31.35%, map-input
bandwidth by 55.89%, and mean map-update time by 50.77%. Its mission took 24.0%
longer, so cumulative end-to-end CPU fell only 16.07%, below the 30% cumulative
objective. This profiled exploratory n=1 comparison therefore passes the mean
CPU engineering threshold but not the combined time/cumulative-CPU target.
Sector's low mean CPU is not an efficiency success because it failed to finish.

## Decision and next gate

The missing pre-turn Full observation that caused the v5 Urban contact is fixed
in these two observations: Adaptive completed 10/10 waypoint visits with no
contact, while the fresh Fixed Sector control failed completion. This is causal
closed-loop evidence for the transaction, not a 100% population guarantee.

Keep v6 default-off. Before any final confirmation campaign, run bounded G1 and
G4 Adaptive regressions to ensure the mandatory goal-change stops do not regress
the previously passing cylinder scenarios. If those pass, run a predeclared
Urban repetition cohort and report both safety/completion and the increased
Full-transition/time cost. Do not tune away or replace the retained v5 failure,
the Sector timeout, or either v6 observation.

Compact evidence is stored in
`results/scenario7_goal_change_full_refresh_v6_urban_20260927/functional_summary.json`.
