# Forest Sector stationary-window sensitivity diagnostic (2026-10-02)

This is a separate diagnostic, not a replacement for the frozen c40 210-flight
campaign. The original Forest Active-Yaw Sector failures were repeat 5
(`run96456`, 90.80 s, 60 s no-progress terminal at `[7.905, 19.655, 1.344]`)
and repeat 9 (`run96496`, 137.32 s, 60 s no-progress terminal at
`[-19.463, -21.724, 1.885]`). Both had zero contact.

The diagnostic retained the same Forest map, `c40_no_mission_cutoff_v14_n10`
candidate, Active-Yaw Sector mode, source acquisition, planner, and unlimited
total mission time. Only `SCENARIO7_TERMINAL_STALL_WINDOW_S` changed from 60 to
180; the displacement radius remained 0.02 m. Five independent physical
re-executions used each failed run number as an output label. The repeated run
number does **not** make wall-timed simulation trajectories deterministic.

| Original failure label | Trial | Complete | Contact | Mission time (s) | Longest position-stationary interval (s) | Closest approach to original stall pose (m) |
|---|---:|---:|---:|---:|---:|---:|
| Forest 5 | 1 | yes | 0 | 73.43 | 7.88 | 6.14 |
| Forest 5 | 2 | yes | 0 | 73.77 | 8.23 | 5.86 |
| Forest 5 | 3 | yes | 0 | 103.73 | 19.16 | 1.02 |
| Forest 5 | 4 | yes | 0 | 90.81 | 8.20 | 0.98 |
| Forest 5 | 5 | yes | 0 | 133.80 | 25.89 | 0.49 |
| Forest 9 | 1 | yes | 0 | 106.11 | 11.05 | 1.46 |
| Forest 9 | 2 | yes | 0 | 134.68 | 17.68 | 1.40 |
| Forest 9 | 3 | yes | 0 | 86.28 | 15.12 | 1.40 |
| Forest 9 | 4 | yes | 0 | 89.02 | 10.80 | 1.38 |
| Forest 9 | 5 | yes | 0 | 83.21 | 7.90 | 1.29 |

All 10 physical runs completed without contact or a terminal stall. Their
`run_valid`, `resource_valid`, and `speed_limit_valid` rows and solid-obstacle
audits are true, each with one attempt and zero retries. The first Forest-5
flight completed and wrote its raw row/audit, but its post-flight CPU summary
process exited nonzero because it was launched from the source-script directory
and resolved a relative performance CSV there. The following nine used the
repository working directory and their full postprocessing completed. That
postprocessing error did not interrupt or alter the first physical flight.

No repeat remained stationary for 60 s and then recovered. In particular,
none reproduced the original trap pose exactly; the closest repeat stayed
0.49 m away. Thus this experiment does **not** prove that increasing the
original observer window would have rescued either original failure. It shows
that the two original failures were not reliably reproduced by relaunching
their run labels, and that Forest Sector can complete along other trajectories.
The original c40 Sector result remains 8/10 for Forest under its declared
60 s/2 cm no-progress rule. A same-state counterfactual replay would be needed
to determine whether either original stopped state could recover after 60 s.
