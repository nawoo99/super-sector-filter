# Scenario7 repair v1 results — not accepted for deployment

The requested analysis and bounded repairs were implemented and tested, but the
candidate **has not solved Adaptive contact safety**. Do not promote it to the
default install, restart a 210-flight confirmation, or describe the experiment as
a successful correction of every failure.

Protocol: [scenario7_repair_20260926.md](scenario7_repair_20260926.md).
Actual cohort: `results/scenario7_repair_smoke_20260926_v1`.
Duration: 1720.57 s (28 min 41 s). End state: COMPLETE_WITH_RETAINED_FAILURES.
24/24 static transport/RViz/acceptance commands passed. Actual flights: ON7 and
OFF6 = 13; requested ON9/OFF9. Urban ON stopped after its Adaptive failure, and
the three Urban OFF flights were explicitly BLOCKED_BY_PREFLIGHT before launch.
Missing flights are not failed flights, successful flights, or zero contacts.

## Actual results

Each cell below is mission time / analytic contact episodes. All numeric times
except Urban's 180 s timeout completed all goals. ON and OFF are separate cohorts.

| Map / phase | Full | Fixed Sector | Adaptive |
|---|---:|---:|---:|
| G1 ON, n=1 | 49.97 s / 0 | 49.55 s / 1 | 61.30 s / 0 |
| G1 OFF, n=1 | 50.34 s / 0 | 48.92 s / 0 | 59.72 s / 1 |
| G4 ON, n=1 | 50.73 s / 0 | 50.22 s / 0 | 47.30 s / 0 |
| G4 OFF, n=1 | 49.05 s / 0 | 54.66 s / 0 | 51.25 s / 0 |
| Urban ON | Not executed | Not executed | 180 s timeout / 1 |
| Urban OFF | Blocked before flight | Blocked before flight | Blocked before flight |

G2/G3/G5/Forest were not rerun. These selected-map smoke tests are not a new
seven-map comparison or population-level safety evidence. Original September25
results and failed attempts remain unchanged.

## What was fixed and what was exercised

- **Unbounded SimplifySFC allocation:** reject a disconnected/non-progressing
  bridge without modifying the input. The old real-box witness exhausts a
  bounded heap; the fixed witness returns immediately. Normal and sanitizer
  tests pass. G4 six new flights finished without runaway, but they do not
  constitute an exact replay of the original recorded corridor.
- **Stopped footprint admission/live-refresh mismatch:** preserve one immutable,
  generation-bound receipt with exact initial hits, fixed origin and deadline.
  Standalone and real CmdTraj normal/sanitizer tests pass. Actual smoke logs did
  not exercise footprint_egress=true: old G1 r06 recovery still needs targeted
  admission-to-refresh replay before claiming a closed-loop fix.
- **Moving trajectory handoff:** reject genuinely discontinuous slowed/cached
  candidates while retaining the old certified command. Actual G1 rejections
  match 1.25x rescaling, not wholesale rejection of ordinary replans. This does
  not prove continuity for all other phases or every command callback.
- **Urban observer self-overload:** replace Python empty-cell iteration with
  exact occupied-cell enumeration. Real-cloud results are unchanged. New Urban
  odometry is 100.001 Hz, header p99 10.405 ms and max10.691 ms; all unchanged
  odometry gates pass. Its FSM main callback is 97.525 Hz and still fails the
  98 Hz gate, independently of the now-correct received odometry.
- **Missing reference handling:** Urban OFF writes structured
  BLOCKED_BY_PREFLIGHT (return2, flights_started=false) instead of starting a
  flight or raising an uncaught missing-summary error. Safety/source/timing
  criteria, resource caps and no-retry policy were not relaxed.

Offline: 230 Python tests passed with the optional real-cloud test initially
skipped; enabling that test separately passed all3 index tests. C++ receipt,
metadata, corridor and handoff normal/sanitizer tests pass. Three-package Release
overlay builds succeeded. See `results/scenario7_repair_20260926/offline_validation.md`.

## Remaining safety defects and next work

1. **G1 OFF collision is smooth backup execution, not the old moving-handoff
   jump.** Generation122/backup command flag2 crosses cylinder68 for104 received
   pose samples (~1.04 s), minimum analytic clearance about -0.1685 m. Live
   certificates remain SAFE during penetration. Full recovery starts about
   245.5 ms after first contact. No footprint exemption was used. A separate
   later ~0.212 m pose step was observed away from this contact and still needs
   classification; do not claim every command transition is now continuous.
2. **Urban collision precedes the A* timeout.** First contact at23.284 s enters
   building_12 (x16..22, y3..11, z0..6). Guard reacts about0.42 s later, then the
   vehicle eventually stops inside the building. Raising the A* time budget is
   not a safety fix. Exhausted recovery also still starts redundant A* calls
   before checking its exhausted budget; that is a separate bounded-retry issue.
3. **Configured/effective unknown policy differs.** The profile says
   unknown_as_occupied=true, but candidate and live-trajectory checks explicitly
   pass false; brakes separately use the configured value. Missing live cloud/
   occupancy traces prevent distinguishing an UNKNOWN entry wall from a stale,
   missing or incorrectly cleared occupancy cell. Do not assume either cause.
4. Next, capture sensor input, map insertion and certificate query states at the
   first G1/Urban intrusion, including the appended backup. Correct the verified
   perception-to-certificate contract and test the stopped recovery receipt
   directly. Do not use ground-truth geometry in planner decisions, change maps
   to hide failures, loosen tolerances, or increase repetitions as a substitute
   for this diagnosis. Raw-cloud CIRI remains shadow-only/default-off.

G1 ON's additional11.33 s vs Full includes9.91 s extra recovery-active time;
most is repeated geometry/path-search failure, not Full-frame acknowledgement
latency. Do not attribute that cost to the unexercised footprint receipt.

Detailed evidence is in `results/scenario7_repair_20260926/`:
`g4_memory_diagnosis.md`, `g1_smooth_contact_diagnosis.md`,
`g1_repair_smoke_timing.md`, `g1_repair_off_contact.md`,
`urban_repair_smoke_failure.md`. Generated per-map CPU/input/map-time/transition
tables and all failed-run artifacts remain in the actual cohort directory.

## Preservation / execution

Runtime code is mirrored to the filter repository; the original install and old
result cohorts are preserved. The separate repair install is
`/root/super_ws/scenario7_repair_20260926/install`. No GitHub push was performed.
The following is a **manual experimental smoke command**, not a recommendation
to rerun until a pass is obtained:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_repair.sh \
  --rounds 1 --maps gapfree_d1_m01 gapfree_d1_m04 urban_blocks_u01 \
  --continue-after-failure
```

Every invocation creates a new folder and retains failures. Revisions must use
new admissions/cohorts; never overwrite this frozen protocol, source snapshot or
results to make an old failure appear fixed.
