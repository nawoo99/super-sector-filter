# Scenario7 near-hit / nonblocking-generation follow-up

Status: v3 G1 Full smoke failed deterministically; v4 is documented separately.
Prospective scope: `docs/scenario7_guard_v3_20260926.md`.

## Unchanged-v2 first-entry diagnostic

The new additive probe selected building10's east face(-4,3.5), with the
preserved v2 install. An initial preparation invocation failed before flight
because the new wrapper omitted a legacy `sha` alias; it is retained at
`results/scenario7_guard_v3_20260926/urban_v2_probe_prepare`. The wrapper was
corrected, four offline tests passed, and the separate `..._prepare_b` admitted
the fresh probe without a flight.

Run72001 at `results/scenario7_guard_v3_20260926/urban_v2_entry_probe` timed out
after180s without observed native contact (minimum native clearance~.019m).
This is **not a valid primary/ON reference**, nor a reproduction of the earlier
contact. Tracing changes timing. The trace reaches its256MiB cap and lacks a
final footer; it retains307,541 data records,126 sensor/map input frames and all
required event kinds, but is not lossless. Truncated arrays or absent records
cannot prove absence of wall observations.

An additional diagnostic admission failure is retained: the child detected a
changed whole-source-tree policy hash because a new, unused
`async_from_rest_planning.hpp` was being prepared concurrently. Every file in
the explicit bound v2 input inventory and child asset list rehashed unchanged,
and no new binary ran; nonetheless the source-tree contract failed and is not
waived. Future flight freezes must include new headers, not only existing files.
The raw flight, trace and failure status remain unchanged; no replacement
flight is substituted for this diagnostic.

Positive records contain near-wall map input points below the actual0.5m
mapping cutoff, which the no-raycasting branch deterministically rejects.
There is an earlier hypothetical SAFE candidate close to the wall, but also a
later OCCUPIED rejection and an outside-wall hold in this noncontact run. These
records support the near-range evidence gap; they do not prove an executed
contact on a specific SAFE candidate.

## Tests and implementation

New supplementary exact-validator fixtures passed8/8 normal and8/8 ASan/UBSan.
They cover the previously missing final initial-clearance-prefix branch,
subsequent hard failures, final version change and verified margin-before-timeout
ordering. Existing frozen tests and production validator logic are unchanged.
See `results/scenario7_guard_v3_20260926/stop_margin_prefix_test_notes.md`.

The fresh v3 ROG library built serially in 1m14s. Its normal real-library
regression passed: legacy/explicit 0.5m preserves the constructed hole, while
the new occupancy-only 0.1m cutoff detects the wall at the contact fixture.
Duplicate near hits still contribute occupancy, but contribute no free-space
miss candidates. Startup clearing at 0.35m, the 0.5m free-ray minimum, real
raycasting's rejection of a 0.25m hit and the 0.2m body radius remain unchanged.
Omitted/0/0.1/0.5 YAML settings were accepted; negative/above-ray-min/NaN/Inf
settings were rejected. This is a constructed regression, not a flight replay.

All four near-range normal invocations and four ASan/UBSan/leak-check
invocations passed. Instrumentation covers the changed prob_map.cpp, inline
Config and the test, not every support-library object. Exact commands and
hashes are in `results/scenario7_guard_v3_20260926/offline_wall_hole/commands.md`.

The fresh v3 campaign controller/child/launcher passed 113 offline tests and
shell/help checks. The asynchronous helper passed normal and ASan/UBSan, ten
read-only source contracts passed after the PVA gate, and the existing actual
handoff-policy test passed. These are not ROS executor integration proofs.

Independent production review then found two gaps in that source snapshot:
ROGMap's RobotState velocity is pose-only/unmaintained, so a zero-speed check
against it is not evidence of rest; and an old ordinary command prepared
before quarantine could pass a state-only check after quarantine was released
again (an ABA publication race). The first complete build was deliberately
interrupted before any new flight to use the actual fresh odometry-twist API
and add final generation/start/certificate binding. Its log is retained at
`build_all_attempt1_review_interrupted.log` (exit143, operator interruption,
not a compiler-error diagnosis). Both fixes were independently re-reviewed;
the corrected helper passed normal and ASan/UBSan again, and all 12 updated
source-contract tests passed. Final fsm_ros2.hpp source/mirror SHA256 is
`eda99ea586ef6c464322b3c6f52da4d10771677d28b2e428ae018a32dd57cb37`.
The second serial build uses this refrozen source.

The new conservative PVA gate applies to ordinary generation only. Existing
certified emergency release also uses solve-start trajectory timestamps and
has not acquired a complete held-PVA/time-rebase proof in this bounded repair.
An Adaptive recovery via that path must not be presented as validation of a
whole-planner stopped-handoff fix.

## Build and preflight

The second serial Release build completed all three packages in 8m6s, using
the separate v3 install prefix. All three existing planner CTest targets
passed. The inherited signedness/unused/CMake-policy warnings remain; no
compilation error occurred. No original/v1/v2 installed artifact was replaced.

Independent read-only checks found all 20 requested runtime/mirror pairs and
the repository launcher identical; all three installed near-hit profiles also
matched. The 787 protected map/mission/profile inventory entries remain
unchanged. CIRI shadow stays absent from these profiles and defaults false.

The first real v3 dry-run stopped before flight: the new shell launcher
exported SUPER_ASYNC_GENERATE_TRAJ, which the inherited controller rejects as
an unexpected parent override. This is a launcher/admission error, not a
planner outcome. The child already sets the required opt-in explicitly; the
launcher is being corrected and the actual admission will be retried in a
different dry-run output root. The earlier 113 mocked/offline checks did not
cover this actual shell-to-controller admission. No v3 flight has occurred yet.

## Final G1 Full result and stop decision

The actual v3 Full smoke is preserved under
`results/scenario7_guard_contract_smoke_20260926_v3_g1/`. It timed out at
180.01 s with 0/5 waypoints, zero path length, no movement and **zero observed
PositionCommand messages**. The worker computed 1,362 results, accepted none,
and every finalization rejection was `POSITION_DISCONTINUITY`. Sector and
Adaptive were not run after this shared startup defect was established.

The minimum observed position error was 0.043510 m. Source and grid arithmetic
show that snapping `(0,0,1.5)` to a 0.05 m voxel centre alone imposes a minimum
0.043301 m displacement, independent of solve delay. The stale solve-start
clock separately produced nonzero velocity and acceleration errors. Main and
command callbacks remained approximately 100 Hz, so the result is a continuity
contract failure, not the earlier synchronous-main starvation failure.

Full evidence and the required two-part repair are in
`results/scenario7_guard_v3_20260926/g1_full_handoff_cause_audit.md`. No failed
run was replaced or reclassified. The separate opt-in v4 implementation and its
single G1 Full functional smoke are recorded in
`docs/scenario7_stopped_departure_v4_20260927.md`.
