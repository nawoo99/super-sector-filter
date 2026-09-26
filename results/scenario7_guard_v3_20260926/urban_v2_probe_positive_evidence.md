# Urban unchanged-v2 probe: positive evidence and explicit limits

Probe root:
`/root/super-sector-filter/results/scenario7_guard_v3_20260926/urban_v2_entry_probe`.
Run72001, Adaptive only, ROI centre(-4,3.5). This was a diagnostic, not a primary
cohort result. No additional flight was started by this analysis.

## Outcome and validity

This run **did not reproduce contact**. The solid audit covers17,999 received
samples, observer-complete/valid, zero analytic contacts, minimum clearance
+.0180414066m. At sample475 (elapsed4.757164240s), the vehicle reached
(-3.7819585934,3.5332055450,2.2149645487) and then remained held outside the wall.
Mission timed out at180s with0/5 waypoints, so this is not liveness success.
Native minimum PCD clearance is+.019m.

The child exited2 with `Source/config/binary changed during candidate` and
`STOPPED_FOR_DIAGNOSIS`. Parent input-preservation reports all2,519 protected
inputs unchanged (`input_preservation.json`: changed=[],unchanged=true).
The root's source-identity audit attributes the broader source-tree mismatch
to a newly added/edited async helper that was not compiled into the running v2
overlay. This explanation does **not waive the failed gate**: the run remains
diagnostic-only, primary-comparison-ineligible and profile-reference-ineligible.
Its positive retained point/query records may inform a mechanism; it cannot
be used as an accepted campaign comparison or repair validation.

## Positive evidence of near-wall hits discarded by mapping

Trace file `cpp_trace/contact_trace_3947397.jsonl` contains126 renderer records,
126 mapper-input records and126 mapper-raycast summaries before its size cap.
The retained mapper arrays alone contain54,422 points in the near-east-face
band |x+4|<.08,3<=y<=11, each less than.5m from the associated mapper pose,
across74 inputs. These are render-derived points near the building face, not
assumed exact analytic-wall coordinates. Truncation means these counts are
positive lower bounds, not full-cloud totals.

Representative retained mapper-input record:

- Sequence39234, epoch1790430806390866392ns.
- Mapper pose(-3.7819585934,3.5332055450,2.2149645487).
- Retained point(-3.9258637428,3.5655350685,2.5425548553), intensity0.
- Distance to mapper pose **.3592621593m**, below the.5m mapping cutoff and
  above the.1m renderer blind range.
- ROI total46,950, retained4,096, `roi_truncated=true`.

Preceding renderer record sequence39233 is Full cycle1/frame55, source stamp
1790430806372083528, with55,994 rendered points and the same46,950 ROI count.
The input trace lacks source stamp, so this temporal/count adjacency is not a
new exact cross-stage identity guarantee. It does not affect the direct claim
that sequence39234 contains the listed mapper input point.

More directly, mapper-raycast summary sequence172306 at
epoch1790430809909591979ns reports55,965 input points,47,029 ROI inputs,
**34,095 near-range rejections**, no intensity/temporal/out-of-map rejections,
10,990 duplicate hits and1,944 first hit insertions. Those categories sum to
the full ROI count. Its mapper pose is the same held pose above. Thus the
unchanged real mapper demonstrably discards many observed near-wall returns
while Full is active. That is not merely a geometric speculation.

## The guard also rejected occupied evidence in this run

This no-contact run must not be summarized as an executed SAFE contact.

- Gen7 committed on map52 at epoch1790430806.197681127.
- At epoch1790430806216581040ns, trace sequence34115 checks gen7/map53,
  query_index2, trajectory time.038928633s, physical point
  (-3.8560864660,3.6053586322,2.2316331411), and records
  `inflated_occupied=true, physical_occupied=true, verdict=occupied`.
  This is a future query, not the stopped vehicle's actual pose.
- Full cycle1 requests at epoch1790430806.216769927; the subsequent brake
  attempt rejects with UNOBSERVED, and no new brake command is published.
- Full frame54 is acquired at1790430806272075258ns; map54 ACK is recorded at
  epoch1790430806.346203492. The vehicle holds at the previously stated clear
  pose rather than executing the hypothetical occupied query.

Earlier local guard queries also expose unsafe analytic geometry accepted
against incomplete map evidence. For example sequence17176, gen5/map47,
physical point(-3.9990811427,3.7550900337,2.2827980137), reports `safe` with
inflated=false, effective_unknown_as_occupied=false. That hypothetical point
overlaps the analytic building. Several full gen5/map47 validation result
records report SAFE with configured_unknown_as_occupied=true but effective
false. However trace records do not carry a unique validation invocation ID,
and concurrent candidate/brake validations can reuse a generation. Therefore
do not silently join every local query to an arbitrary whole-validation result
or assert that this exact future point was executed. Actual odometry has no
contact in this run.

## Trace completeness and next inference boundary

The file has268,427,175 bytes, close to the256MiB cap with footer reserve,
307,541 total JSON records and no final footer. There are no malformed JSON
lines in this parse. The last retained checkpoint explicitly reports3,257
contention drops; later loss is unknown. Records from concurrent emitters can
arrive out of sequence. The trace audit marks complete_lossless=false.
No missing point, cell update, guard event, or later recovery may be interpreted
as absent from execution.

Positive mapper rejections plus the actual-library constructed-wall fixture
justify separating sensor-valid occupancy hits from the historical.5m free-ray
and startup-clear radius. They do not prove that this mechanism alone caused
run70005's contact, or that preserving near hits alone solves liveness/safety.
Raw/committed snapshot equality and query-version/scan identity still require
the proposed synchronized bounded diagnostics. The observed OCCUPIED rejection
shows why this particular diagnostic did not reproduce entry.

## Hashes

- Trace:
  `7ffd5667f0a4310dd3879b6fb80f7073a2f0a669a8ec684dd978147cbf7a6533`.
- Solid audit:
  `21bb59fdcb6a82d08369ee9e8f67ba40e65c76da19f561dac79769228b868578`.
- Stack log:
  `97785a4631192d1def89ae34330a57915c42475cc07ccd54a5d41de2b340c6c5`.
