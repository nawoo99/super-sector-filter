# G1 repair-v1 ROI probe: bounded mapping diagnosis

Run: `g1_probe_v1b/flight`, Adaptive run 62001. This note is read-only analysis;
it does not change production source or initiate a flight.

## Outcome and limits

The recorded run completed 5/5 goals in 48.28s. Its independent solid audit is
valid and complete: 4,827 received samples, zero contacts/episodes, minimum
clearance +0.187277039m. The earlier G1 contact **was not reproduced**. The
instrumented run is diagnostic-only, not a CPU/timing comparison result.

Nevertheless the actual ROG trace positively records occupancy erasure and a
hypothetical trajectory SAFE/solid-contact disagreement. Those observations
must not be presented as an executed collision or as a complete replay of the
earlier failed trial.

## Occupied evidence removed by misses

File: `g1_probe_v1b/cpp_trace/contact_trace_3896845.jsonl`.
Among strictly valid JSON records:

- 235 `map_probability_update` miss transitions are OCCUPIED→UNKNOWN.
- 4 are OCCUPIED→KNOWN_FREE.
- 108 of these 239 recorded demotions have centres within 0.12m radial distance
  of cylinder 68's surface and z in [0,3]. This is a spatial screening count,
  not a claim that every such voxel was originally a return from that cylinder.
- 175 hit transitions go KNOWN_FREE→UNKNOWN, showing that a single hit does
  not invariably restore occupied classification after a free prior. The
  independent offline test establishes actual duplicate hit-count loss; this
  live count alone does not prove each update contained duplicate input hits.

Example demotion: sequence 51675, epoch ns `1790426800552781428`, at
`[-29.175,-4.275,1.725]`, count 8 misses, log odds
`1.9023722410202026 → 1.5823301076889038`, OCCUPIED→UNKNOWN.
An example nearer the cylinder surface is line 91476, sequence 91716, epoch ns
`1790426800993537039`, position `[-29.175,-4.425,1.875]`, 4 misses,
`1.7423511743545532 → 1.5823301076889038`.

These are positive events from the actual no-raycast mapper, not an inference
from missing scan data. They substantiate that the erasure mechanism proven
offline also occurs in this ROI run. They do not alone establish its causal
role in the earlier contact.

## Hypothetical SAFE endpoint intersects the closed cylinder

Cylinder 68 (zero-based CSV row; physical CSV line 70) has centre
`[-28.591183,-4.598807]`, radius .5m, height [0,3]; body radius is .2m.

Trace line 184267, sequence 187317, epoch ns `1790426801994750756`:

- `trajectory_generation=135`, `map_version=322`, query 135,
  `tt=0.59876053033888343`.
- Mandatory hard-body endpoint
  `[-28.61134131472965,-5.221968838039126,2.674450799980871]`.
- `effective_unknown_as_occupied=false`, `inflated_occupied=false`,
  `physical_occupied=false`, verdict `safe`.
- Independent closed-cylinder clearance is **-0.076512202m**.
- Immediately preceding physical-body record (line 184265, sequence 187315)
  reports clear, `occupied_candidates=0`.
- Next validation-result record (sequence 187318) reports `SAFE` for range
  `[0,0.59876053033888343]`, generation 135, map 322.

This is a real predicate/solid-geometry disagreement, but it is a hypothetical
validation endpoint, not the simultaneous vehicle pose. Odometry sample 2961,
header ns `1790426801994726304`, was at
`[-30.19697512371158,-3.9489011962913207,2.5470283718985214]`, solid clearance
**+1.032323843m**.

Multiple candidate/brake checks share generation 135. The committed path log at
epoch `1790426801.980664758` has checked range `[.049,.638]`, not the endpoint
check's `[0,.59876053]`; therefore this note does **not** identify the hypothetical
endpoint as the executed committed path. The next map update produces a
CLEARANCE_MARGIN finding on generation 135, and the stack records emergency
braking at epoch `1790426802.016568487` with path_status=SAFE and stop position
`[-30.082,-5.031,2.761]`. Later replanning succeeds.

The two recorded occupancy demotions within .3m of the hypothetical endpoint
occur at epochs `1790426802742014174` and `1790426802748087340`, **after** this
SAFE check. They cannot by themselves explain the endpoint's earlier missing
occupied candidates. Neither an earlier missed return nor a particular prior
erasure is proven for that endpoint by this incomplete trace.

## Trace completeness caveats

The final file is 140,525,801 bytes. It has 344,201 strictly valid JSON records
and 4,136 malformed `published_position_command` records: the C++ uint8
`trajectory_flag` was streamed as a raw control character (e.g. byte 0x01),
not a JSON integer. This note does not silently repair those records.

The last retained checkpoint (epoch ns `1790426820921404548`) reports
353,658 submissions, 348,178 writes, 5,480 contention drops, zero write errors,
zero queue/file-cap/oversize drops and zero queued records. There is no final
`trace_footer`, so final completion/counter equality cannot be certified.
Twenty-four cloud records also explicitly flag truncated ROI point arrays
(the independent per-record ROI retention cap is 4,096 points).
Including the sequence numbers extractable from malformed command lines, there
are 348,282 unique positive sequences through 353,763: 5,481 sequence gaps.

Consequently this trace supports the positive events above but cannot establish
that an unrecorded hit, query, state transition or command did not occur. It
cannot reconstruct a complete immutable snapshot or prove end-to-end absence of
occupied evidence at every contact-relevant location.

## Evidence hashes

- Trace SHA256:
  `f53bafc2f2757409aadc6d465d55cd8c452dd267ebd9535422a10252b82813fe`.
- `flight/artifacts/gapfree_d1_m01_run62001_adaptive.attempt1.solid_audit.json`:
  `0ca74c6f5cc84f6ded75f303185b02b41b836695e27a2a66b0fbd3a671bd1b86`.
- Matching `.odometry.csv`:
  `e667581acf8087ed063956d455af5ec501433d23db0296a2c13910f27c6757d9`.
- Matching `.stack.log`:
  `d1bb35d3795d377f9170e81d382d27641a9f7b2dfedb7c12ec2307b3e475dc9b`.

The separate `rog_occupancy_offline_proof.md` gives real-library counterexamples
and the bounded repair design. Neither this successful single diagnostic flight
nor those offline proofs establish production readiness.
