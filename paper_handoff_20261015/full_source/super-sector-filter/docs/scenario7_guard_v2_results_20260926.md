# Scenario7 guard-contract v2 — repair and validation record

Candidate `c27_guard_contract_v2`; prospective scope is in
`docs/scenario7_guard_v2_20260926.md`. The previous repair-v1 and original
installations, maps, missions, and failed observations are preserved. This
candidate is **not production-ready**: the completed smoke retains G4 Adaptive
contact and Urban Adaptive/Sector contact with timeout.

## Reproduced defects and fixes

1. In no-raycasting mode, duplicate LiDAR hits were removed from probability
   evidence as well as redundant free-ray work. At the actual free prior, one
   retained hit does not make a cell occupied; two hits do. Preserve every hit
   contribution while still deduplicating the expensive ray march.
2. Approximate 0.15 m observed-free ray markers were inserted into 0.05 m raw
   cells and could erase occupied cells that the true sensor ray did not cross.
   No-raycasting occupancy accumulation now preserves occupied cells from these
   markers. Genuine probabilistic raycasting still clears real on-axis misses;
   nonoccupied coverage markers and startup-only clearing are unchanged.
3. Sampled stop viability accepted an early `CLEARANCE_MARGIN` result without
   inspecting the rest of the stop. The new stop-only traversal defers this soft
   margin and can waive it only after all prepared hard checks and final
   map/deadline checks complete. Invalid sampled states reject. Receipts and the
   FSM consumer both use policy revision 2. Ordinary candidate margin rules and
   explicit unknown-space policy are unchanged.

The optional command trace also serializes its uint8 flag as a JSON integer.
This repairs new trace formatting only, not the old invalid/incomplete records.

## Preserved pre-fix diagnostic flights

Both successful input-preservation audits verified all frozen v1 inputs
unchanged after each flight. These profiled ROI probes are **diagnostic only**,
not primary safety/CPU trials or reusable preflight references.

| Probe | Waypoint completion | Native sampled-PCD contacts | Time | Interpretation |
|---|---:|---:|---:|---|
| G1 v1b | Yes | 0 | 48.28 s | Prior contact not reproduced; real occupied-cell erasure and a hypothetical unsafe SAFE endpoint were recorded. |
| Urban v1 | No | 1 | 180.01 s | First contact at 4.758 s against building_10; subsequently stops/moves inside it. |

G1's independent solid audit has 0 episodes over 4,827 samples. Urban has one
episode with 17,526 contact samples out of 18,000; waypoint completion and
contact observation completeness are different quantities. Urban's chosen ROI
covered the previous building_12 entry, not the newly observed building_10
entry, so this trace cannot establish the local map state at the new contact.

The first G1 probe invocation failed in argument construction before launching
a flight; its evidence remains in `g1_probe_v1`. The corrected fresh run is
`g1_probe_v1b`. The v1 traces contain contention loss, malformed command JSON,
and missing final footers. Positive valid records support bounded findings;
absent records must never be used as evidence of absent obstacles.

Detailed evidence under `results/scenario7_guard_v2_20260926/`:

- `rog_occupancy_offline_proof.md`
- `g1_probe_v1b_mapping_diagnosis.md`
- `urban_probe_v1_entry_diagnosis.md`
- `stop_policy_v2_validation.md`

## Offline validation

The installed v2 ROG archive passes real-library hit-multiplicity and occupancy
preservation regressions, including unchanged unknown-marker and genuine-ray
clearing behavior. The changed map code also passes ASan/UBSan/leak checking;
unchanged support-library code was not instrumented by that isolated test.

Stop helper, additive revision-bound demand policy, and the extracted exact
production validator/state traversal pass normal and ASan/UBSan tests. The
extraction fixture covers 13 cases; map, trajectory, DDA and stop predicates are
controlled fixtures, not a real-sensor or swept-volume safety proof. New runner
and frozen control/runtime regressions pass 79 tests. The three existing
command-publication, path-publication and brake-motion CTest targets pass.

The second-pass review found no new blocking scoped regression, but identified
test limits: the extracted fixture does not execute the initial-clearance-prefix
final deferral branch; the timeout case does not assert that timeout occurred
after the first margin query. The ordinary candidate policy remains immediate
margin rejection, with one additional final fail-closed deadline check; it is
not literally byte-identical behavior. Concrete follow-up tests are recorded
in `results/scenario7_guard_v2_20260926/final_stop_review.md`. These limits are
not waived by the existing passing tests.

The separate three-package Release build completed in 12 min 28 s with explicit
`MAKEFLAGS='-j1 -l1'` and sequential colcon execution. Its dependency caches select
the v2 ROG and planner prefixes. All five changed production input hashes match
their pre-build values, and 18 admitted runtime/mirror C++/test files match.
Warnings are retained in `build_serial.log`; the build exit code is zero.

## V2 smoke execution

Dry admission passed with independent ON9/OFF9 and no ROS launch. The first
actual controller at `results/scenario7_guard_contract_smoke_20260926_v2` was
started without the previous smoke's continuation flag. It was deliberately
interrupted during static checks, before any flight, to correct this scheduling
omission. Three static checks had passed; the fourth was interrupted. The
original plan/status/logs remain intact. This is not a failed flight retry.

The fresh cohort is `results/scenario7_guard_contract_smoke_20260926_v2b`:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_guard_v2.sh \
  --rounds 1 --maps gapfree_d1_m01 gapfree_d1_m04 urban_blocks_u01 \
  --continue-after-failure \
  --output /root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b
```

Continuation retains failed/invalid steps and permits the next scheduled map;
it does not relax a gate, retry/replace a flight, or admit OFF without a valid
same-version ON reference. All results are fresh and separate from repair-v1.

### Profiled ON smoke: safety failure remains

All 24 static transport/RViz/admission checks passed. The ON phase completed
eight actual flights, not the nine planned flights. Contact below means an
independently audited analytic-solid episode; the native sampled-PCD observer
also reports the same episode counts for these flights.

| Map | Mode | Waypoint completion | Contact episodes | Time, s | Measurement/admission |
|---|---|---|---:|---:|---|
| G1 | Full | yes | 0 | 49.15 | all checks pass |
| G1 | Sector | yes | 0 | 48.89 | all checks pass |
| G1 | Adaptive | yes | 0 | 61.69 | all checks pass |
| G4 | Full | yes | 0 | 54.22 | all checks pass |
| G4 | Sector | yes | 0 | 52.53 | all checks pass |
| G4 | Adaptive | yes | **1** | 51.22 | measurement checks pass; safety fails |
| Urban | Adaptive | **no** | **1** | 180.01 | measurement checks pass; safety/completion fail |
| Urban | Sector | **no** | **1** | 180.00 | small-pool timing gate also fails |
| Urban | Full | not run | N/A | N/A | child stops after Sector timing failure |

The Urban missing Full flight is not counted as a failed flight or contact-free
flight. ON and subsequent OFF observations must remain separate. The safety
failures alone prevent promotion, regardless of any CPU reduction.

G4 Adaptive enters cylinder40 on normal EXP generation114, not backup, with a
smooth first-entry step. One episode lasts about .370s (37 sampled contacts),
including entry of the centre into the solid. Guard checks and later commits
remain SAFE; no footprint-egress exception is exercised. Full recovery does
not open during the contact, and the next Full event is 4.57s after first entry.
At entry the obstacle is 108.1 degrees from **commanded yaw** but 8.8 degrees
from the commanded velocity heading. This supports investigation of lateral
motion versus sensor coverage; it does not establish the unrecorded actual
render pose, preceding scan visibility, or voxel classification.

G1 Adaptive's 12.54s excess over Full decomposes into 8.157s more recovery-active
time and 4.383s outside those windows. It has 13 recovery cycles versus Full's
two; all Adaptive cycles receive their Full ACK before first async dispatch.
Actual Adaptive main/command rates are 99.457/100.002Hz; sampled stop validation
averages .238ms CPU/call and .141s inclusive CPU in its 55.099s profiling window.
These observations do not support attributing the longer mission to the new
complete traversal's CPU cost. Recovery-active time includes deceleration, not
only stationary waiting. Single-sample v1/v2 differences are not a regression
probability or a causal performance estimate.

See `results/scenario7_guard_v2_20260926/g4_adaptive_on_v2b_contact_diagnosis.md`
and `g1_v2_on_timing_audit.md` for evidence, timelines and limitations.

### Urban entry: recent Full acquisition did not prevent contact

Both Urban first entries are incremental normal/EXP commands into building10's
east face, x=-4, y[3,11], z[0,6]. Adaptive enters at6.339s on generation8;
Sector at6.404s on generation9. Neither uses a footprint-egress receipt. Both
then remain in sampled contact until timeout, with0/5 waypoints reached.

Adaptive had completed Full acquisition/map ACK and released to Sector only
200.355ms before entry. Its last Full acquisition was249.860ms before entry,
and generation8 committed53.029ms before entry. SAFE certificates continue
around/after penetration. Therefore **recent Full acquisition plus a current
SAFE result is demonstrably insufficient in this implementation**; a claim
that the wall was never recently visible, or that delayed Full switching alone
caused this failure, is unsupported.

Command and source-derived attitude point laterally to motion, but synchronized
actual quaternion, acquisition/render pose, wall points and guard map snapshot
were not recorded. The simulator applies flatness-derived attitude immediately;
it has no modeled physical yaw lag, although callbacks and acquisition have
distinct sample ages. The actual raw-point → voxel → query failure remains
unresolved. See `urban_on_v2b_contact_diagnosis.md` for exact chronology.

Sector's separate timing failure is downstream of contact. After the final
FOLLOW_TRAJ→GENERATE_TRAJ transition, synchronous PlanFromRest/A* repeatedly
times out at about100ms/call. The175.636s profiling window contains1,610 path
searches and157.09 exclusive CPU-s; main callback rate averages19.7568Hz and
falls to about9.96Hz in late windows. Command callbacks remain100.0023Hz in their
separate group. This is not a map-update or observer cadence bottleneck, and
does not by itself explain the earlier wall entry. See `urban_sector_v2_timing.md`.

### Unprofiled OFF confirmation and final count

| Map | Mode | Waypoint completion | Contact episodes | Time, s | Mean experiment CPU, cores | CPU, core-s |
|---|---|---|---:|---:|---:|---:|
| G1 | Full | yes | 0 | 50.24 | .758606 | 41.139838 |
| G1 | Sector | yes | 0 | 56.59 | .449940 | 27.148713 |
| G1 | Adaptive | yes | 0 | 46.32 | .416767 | 21.231938 |
| G4 | all three modes | not run: blocked by ON safety | N/A | N/A | N/A | N/A |
| Urban | all three modes | not run: invalid/incomplete ON reference | N/A | N/A | N/A | N/A |

G1 OFF Adaptive measured45.06% lower mean experiment CPU and48.39% lower total
CPU than Full. This is **one exploratory unprofiled run per mode**, includes
the experiment cgroup/simulator but excludes the external observer, and does
not establish repeatability, seven-map performance or safety. It must not be
pooled with the slower ON Adaptive run or promoted because it meets a CPU
target. All G1 OFF source/admission checks pass; Adaptive has3 observed
Sector→Full source-frame transitions.

Final state is `COMPLETE_WITH_RETAINED_FAILURES`, elapsed1785.946s (~29m46s).
Planned ON9/OFF9; actual ON8/OFF3 = **11 flights**. Seven scheduled flights did
not start: Urban ON Full and G4/Urban OFF triplets. Two preceding unchanged-v1
ROI flights are separate diagnostics, not members of this cohort. The aborted
first v2 controller did not start a flight. There was no flight retry or
replacement. Neither G2/G3/G5 nor Forest was retested.

## Next bounded repair, before another large campaign

1. Capture synchronized body/acquisition/render orientation, raw wall points,
   occupied/observed voxel updates and guard queries at building10's east face
   and G4 cylinder40. Include the last Full frame and first Sector commits.
   Verify tracing completeness; absent trace data is not free-space evidence.
2. Use that evidence to repair the sensor→map→trajectory acceptance contract.
   Require adequate observation for the executable path and stopping region;
   do not assume a generic Full ACK proves this geometry. Preserve stop/hold
   when coverage or a safe path cannot be established. A blanket unknown-policy
   toggle or angle widening without a liveness/safety audit is not a proven fix.
3. Separately remove synchronous repeated path search from the Sector
   GENERATE_TRAJ main callback, retaining generation/goal/map identity and safe
   hold semantics. Do not increase the A* budget to hide the failure.
4. Add the missing escape-prefix and margin-before-timeout regressions, then
   rerun a new versioned smoke before a seven-map confirmation. Do not change
   the maps or select successful repetitions to remove these failures.

## Remaining model limits

The explicit unknown=false sampled-stop/candidate policy, neighborhood-based
observation heuristic, centre-based occupied-voxel contact representation and
between-sample motion remain separate limitations. The voxel-volume review
contains conservative-volume counterexamples, not evidence that this was the
cause of a recorded contact. It also requires consistent initial-footprint
semantics before changing that contract; see `voxel_volume_followup.md`.

No map changes, A* budget increase, safety-radius reduction, timing/resource
gate relaxation, automatic retry, old/new result pooling, or CIRI activation
was used for this repair.
