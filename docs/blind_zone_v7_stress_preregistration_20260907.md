# Blind-zone v7 trajectory-intersection stress preregistration

Date frozen: 2026-09-07 (Asia/Seoul), before any v7 flight

## Purpose and status

V6 verified common late-obstacle delivery but did not require any mode to
avoid the cylinder: the minimum observed Sector clearance remained +0.214 m.
V7 is a new exploratory stress family intended to test the missing mechanism:
whether a body-fixed 45-degree Sector loses a path-intersecting obstacle while
Adaptive's independent 360-degree risk channel opens Full perception in time.

The completed v6 Map7/9/10 three-mode n=3 cohort is explicitly reused as
design data.  No v7 smoke row is confirmatory evidence.  No v7 centre, radius,
or candidate may be changed after observing a v7 outcome.

## Frozen selector

`select_side_entry_v7_smoke.py` requires all 27 unique, valid v6 rows and uses
only the nine Map9 rows.  It evaluates 0.05 m world-frame centre points in
`[21.5, 24.0] x [21.5, 24.0]` and radii 0.35/0.40/0.45/0.50 m.  A candidate is
eligible only when:

1. the centre is within 2.0 m of the first corner `(24, 24)`;
2. exact horizontal surface separation from every source-map cylinder is at
   least 0.30 m;
3. at every recorded v6 Map9 spawn state, trigger distance is 0.8--3.5 m and
   the complete cylinder is outside the body-fixed sector by at least the
   enforced 47-degree inner edge;
4. insertion clearance at those states is at least 0.10 m after subtracting
   the 0.20 m vehicle sphere;
5. the candidate intersects at least one recorded nominal Sector trajectory
   proxy.

The lexicographic objective is: maximize the number of negative Sector
proxies, minimize median Sector proxy clearance, maximize minimum insertion
clearance, minimize radius, then minimize x and y.  Full and Adaptive nominal
path intersections are deliberately allowed because their ability to detect
and avoid the new obstacle is the mechanism being tested.

The selector found 404 eligible candidates and chose scenario 1:

- centre `(22.50, 23.05)`, radius 0.50 m;
- exact source gap 0.927742 m;
- minimum design-state insertion clearance 0.118258 m;
- Sector design proxies -0.063182/0.227068/0.176813 m.

For a possible follow-up it also froze six candidates greedily in selector
order with at least 0.20 m centre separation:

| Scenario | centre x/y (m) | radius (m) | min insertion clearance (m) | exact source gap (m) |
|---:|---:|---:|---:|---:|
| 1 | 22.50 / 23.05 | 0.50 | 0.118258 | 0.927742 |
| 2 | 22.35 / 23.20 | 0.50 | 0.113042 | 0.866485 |
| 3 | 22.35 / 22.90 | 0.50 | 0.328375 | 0.729258 |
| 4 | 22.20 / 23.35 | 0.50 | 0.161700 | 0.826211 |
| 5 | 22.15 / 23.55 | 0.50 | 0.147898 | 0.915577 |
| 6 | 22.15 / 23.75 | 0.50 | 0.133418 | 1.055223 |

Frozen pre-flight identifiers are:

- selector SHA-256:
  `d253374cd1f071d9e34367325bed92b56ea8d98d486d43f47c0c3b3b80d974c1`;
- selection record SHA-256:
  `199309875e76af3344081c74e15d652cfb0e684600b69db074e97a4f5b8b6c7c`;
- scenario-1 config SHA-256:
  `05bed8edfb450241257819ac9bfb35972dfed67abb4b73e63b85e5b795c912d9`;
- simulator header SHA-256:
  `2aec7b1c381d999056b62a2a6cca89398678ed28364f73b8f6707cd3cf8123e8`.

## Time-boxed smoke and stopping rule

The first and only exploratory smoke is Map9, Full/Sector/Adaptive, n=1,
rotated order, with the same v7 planner/front-end profiles as the final
campaign.  The default resource-quality thresholds remain active; preflight
timeout is shortened to 60 s, loop timeout is 150 s, and the whole smoke is
stopped if wall time exceeds 12 minutes.

Expansion is permitted only if all three rows are unique, first-attempt,
resource/speed/performance valid, produce independently validated v7 events
with at least +0.10 m insertion clearance, and Full plus Adaptive both finish
with zero source and synthetic contact.  Sector must show a synthetic contact
or a synthetic-obstacle-caused failure.  A source-map contact does not satisfy
the gate.  If Sector also passes without synthetic contact, or Full/Adaptive
fail, v7 stops without moving or enlarging the obstacle.

If the gate passes within the time budget, the already frozen six candidates
may be materialized as six Map9 scenario configurations.  The exploratory
smoke is excluded.  A separate confirmatory campaign then runs each scenario
once under all three modes (18 rows), paired by scenario and order-balanced.
Contact/completion discordance is the primary endpoint; minimum clearance,
Adaptive detection/open latency, CPU and ingress are secondary.  Exact
two-sided McNemar is reported only on the 18-row frozen cohort.  Six
Sector-contact/Adaptive-no-contact scenario pairs with zero reverse pairs
would give p=0.03125; this is a reporting rule, not a stopping target.

## Exploratory smoke outcome and frozen stop decision

The Map9 smoke completed in about 4.5 minutes.  All three rows were unique,
first-attempt, resource/speed/performance valid, and their independently
validated v7 events had conservative insertion clearances of
+0.226702/+0.260111/+0.198770 m for Full/Sector/Adaptive.  Runtime memory PSI
and end-to-end process swap were zero.

| Mode | complete | source contact | v7 contact | min v7 clearance | time | effective/TG opens |
|---|---:|---:|---:|---:|---:|---:|
| Full | 1/1 | 0 | 0 | +0.305 m | 68.84 s | 0/0 |
| Sector | 1/1 | 0 | 0 | +0.237 m | 80.44 s | 0/0 |
| Adaptive | 1/1 | 0 | 0 | +0.199 m | 75.47 s | 13/4 |

The smoke therefore failed the preregistered discrimination gate: Sector did
not contact or fail, and Adaptive passed closer than Sector.  Adaptive's raw
risk worker emitted zero OCCUPIED verdicts; its first trajectory-guard Full
opening preceded obstacle insertion by 10.69 s, so it is not evidence of an
obstacle-triggered safety response.  At the actual Sector insertion, the
cylinder centre was 80.83 degrees from velocity direction and the replanned
path bypassed it.  The v6 closest-point proxy did not robustly predict the new
planner branch.

Per the frozen rule, scenarios 2--6 and the 18-row confirmatory campaign were
not run.  The centre/radius were not tuned again.  No safety-rate advantage or
McNemar result is claimed.  Evidence is:

- `results/side_entry_v7_map9_smoke_selection_20260907.json`;
- `results/side_entry_v7_map9_three_mode_n1_smoke_raw_20260907.csv`;
- `results/side_entry_v7_map9_three_mode_n1_smoke_{summary,reductions}.csv`;
- `results/side_entry_v7_map9_three_mode_n1_smoke_validation_20260907.json`.
