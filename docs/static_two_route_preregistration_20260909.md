# Static two-route blind-hazard preregistration

Date: 2026-09-09 (Asia/Seoul)

Status: **frozen before generation, replay, or flight**

## Research question

Can the deployed 45-degree Fixed Sector lose completion or contact safety in a
realistic static branching corridor, while Full remains safe and Adaptive's
existing raw-future-trajectory trigger opens Full early enough to recover,
without changing planner, optimiser, filter angle, or Adaptive policy?

This is a new exploratory topology family (`sbd2`), not a continuation or
pooled analysis of the result-selected `sbd1_c1--c3` cylinder placements.

## Frozen mechanism

The vehicle approaches a junction while facing north.  West of the junction a
horizontal divider creates two routes to the same goal:

- a short lower route, which is closed by one static full-height cylinder;
- a longer upper route, which remains inflation-feasible and reconnects beyond
  the divider.

At the junction the cylinder must be present in the actual 360-degree raycast
but remain outside the Fixed Sector.  On the clear control, SUPER must naturally
commit the shorter lower route through the hypothetical cylinder.  Once the
hazard is installed, Full can select the upper route before the branching
decision.  Fixed Sector can only observe the closure after rotating toward or
entering the lower route.  Adaptive is successful only if its already deployed
raw-trajectory verdict causes a Full opening before that late observation.

Candidate `sbd2_t1` uses a single predeclared geometry.  If it fails, the full
first-attempt data are retained and the next candidate may change only one
declared causal factor selected from the failure audit: decision-to-hazard
distance, divider endpoint, approach/goal geometry, or corridor width.  A
candidate is never rerun to replace an outcome; reruns are allowed only for a
documented infrastructure or measurement defect.

## Ordered gates

1. **Structure gate:** clear/hazard maps differ only by a positive cylinder
   point set; the inflated lower route is closed; an inflated upper route
   exists; the hazard is line-of-sight visible at the decision pose but has
   zero samples inside the 45-degree body-yaw Sector; and forward background
   support remains nonempty.
2. **Actual frontend replay:** at the frozen decision state, raw hazard and raw
   trajectory-conflict frames are nonzero, Fixed Sector keeps zero hazard and
   conflict points, and Adaptive produces at least two consecutive fresh exact
   `OCCUPIED` verdicts with the deployed `risk_min_points=200` setting.
3. **Clear closed loop:** Fixed Sector completes without contact and commits at
   least one 1.0-second future trajectory whose body intersects the hypothetical
   cylinder.  Otherwise the topology does not test the proposed mechanism.
4. **Hazard smoke:** one first attempt each in Full, Fixed Sector and Adaptive.
   Full and Adaptive must complete without static-PCD contact.  Adaptive must
   have at least two hazard-matched exact verdicts and at least one effective
   Full opening before contact.  Fixed Sector must show degradation, defined
   before flight as either static-PCD contact or non-completion within the
   common 90-second budget.
5. **Repetition:** only a topology passing all prior gates advances to balanced
   repeated trials.  Initial confirmation is 10 trials per mode.  Held-out
   confirmation uses independently generated translations/reflections with no
   parameter adjustment after seeing their outcomes.

## Success and stop decisions

The exploratory mechanism succeeds only when all three hazard-mode conditions
occur on the same frozen topology: Full safe completion, Fixed Sector
degradation, and Adaptive safe completion with causally matched activation.
Transient committed conflict alone is diagnostic and does not count as Sector
degradation.

Stop a candidate immediately when a prerequisite gate fails.  Do not use a
generic `OCCUPIED` count as hazard evidence; the verdict witness must
body-intersect the declared cylinder.  Do not report McNemar or a population
claim from exploratory candidates.  If no frozen-policy topology can create
the separation after causal redesigns are exhausted, the supported conclusion
is that the present static simulation does not demonstrate a safety-rate
advantage; planner changes then require a separate preregistration.

## Frozen iteration log

### `sbd2_t1` — stopped at Full feasibility gate

The structure and actual frontend replay gates passed.  The clear Fixed Sector
control completed and committed a hypothetical hazard-intersecting trajectory.
The first hazard Full attempt was contact-free but did not complete in 90 s.
It stopped east/south of the cylinder with 0.318 m cylinder body clearance.
The planner log contained 800 A-star `TIME_OUT` returns after the local target
fell in the disconnected lower branch; the divider extended to x=2, far beyond
the 7 m local planning horizon.  Sector and Adaptive hazard trials were stopped
without producing rows, as required by the ordered gate.

### `sbd2_t2` — frozen before generation

Change exactly one causal factor: move the divider's west endpoint from x=2 to
x=12 m.  Keep the approach, goal, corridor widths, cylinder `(15,20.5,r=2.1)`,
speed, filter and Adaptive policy unchanged.  This places the upper/lower
reconnection immediately west of the cylinder and tests whether Full can reach
the same local target through the upper homotopy.  Run the same structure and
frontend gates, then one hazard Full feasibility attempt.  Filtered modes are
allowed only if Full completes contact-free.

`t2` subsequently passed both non-flight gates but its first hazard Full row
also stopped without contact at `(17.58,20.05)` and timed out.  Shortening the
west end did not help because Full had already crossed east of the divider by
the time the hazard update invalidated its committed lower-route trajectory.

### `sbd2_t3` — frozen before generation

Change exactly one additional causal factor relative to `t2`: move only the
divider's east endpoint from x=21.5 to x=18.5 m.  Keep the t2 west endpoint,
all other walls, goal, cylinder, speed and policies fixed.  The wider east
junction leaves a cross-over after the measured reveal/update point.  Repeat
the structure and frontend gates and one Full feasibility attempt before any
filtered flight.

`t3` passed the structure/replay and mandatory Full gates; Full completed in
10.84 s with zero contact and 0.302 m static-PCD clearance. The contingent
Fixed-Sector and Adaptive rows also both completed without contact, in 15.33 s
and 14.63 s. Fixed Sector first observed the cylinder centre only 6.24 degrees
from its realised body heading, so the closed-loop state did not preserve the
assumed angular exclusion. Adaptive had one generic exact verdict but zero
hazard-matched exact verdicts; its four openings therefore do not pass the
frozen causal gate. Decision: stop `sbd2` without repetition or McNemar and
start a separately named heading-mismatch topology rather than moving the same
cylinder again.
