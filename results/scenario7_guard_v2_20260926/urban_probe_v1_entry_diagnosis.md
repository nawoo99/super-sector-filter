# Urban unchanged-v1 diagnostic: new first-leg entry, ROI mismatch

Run `urban_probe_v1/flight`, Adaptive 62002, times out at 180s. The independent
solid audit is valid and complete: 18,000 samples, 17,526 contact samples, one
unbroken episode, minimum clearance -.2m, observer completion=true but mission
success=false. The contact is a different building/leg from the earlier repair
smoke, not a reproduction at the selected old ROI.

First contact is sample 475, elapsed 4.758229494s, header ns
`1790426968465580297`, position
`[-3.8290335312,3.5950205025,2.1865836215]`, velocity
`[-4.8789197672,4.9127414860,.9655232346]`, clearance -.0290335312m.
The solid is `building_10` (index 9), centre `[-7,7]`, size 6x8m, bounds
`x[-10,-4], y[3,11], z[0,6]`, body radius .2m.

Entry is a normal-scale incremental movement, not a one-sample teleport:

| Sample | x | y | z | Solid clearance |
|---:|---:|---:|---:|---:|
| 473 | -3.731438 | 3.496892 | 2.166906 | +.068562 |
| 474 | -3.779564 | 3.545245 | 2.176699 | +.020436 |
| 475 | -3.829034 | 3.595021 | 2.186584 | -.029034 |

Samples 475–480 retain the exact same contacting position. At epoch
`1790426968.905729010` (about .440s after entry), the stack records
`TRAJ_GUARD_STATIONARY_HOLD` / `TRAJ_GUARD_BRAKE`, `path_status=SAFE`, and stop
`[-3.829,3.595,2.187]`: the certified hold is already in body contact. Generation
7 then commits `PlanFromRest/with_backup` at `1790426969.011638566`, with
`footprint_egress=false`; later recovery movement enters farther into the solid.
The final pose reported by the run is approximately
`[-9.2519433,10.3412748,2.6344622]`, inside the same box.

## What the diagnostic cannot establish

The configured ROI was centred at `[22,9.5]`, selected from the previous smoke's
`building_12` entry. It does not include the new entry near `[-4,3.6]`.
The 10,979,138-byte C++ trace contains **no** map probability-update records,
raw snapshot deltas, physical-body queries or individual guard queries; the
retained `map_input_cloud` ROI point counts total zero. This means the diagnostic
did not observe this location, not that the mapper received no obstacle points
near the vehicle. The exact local occupancy/unknown classification and any
particular missed-return or occupied-erasure cause remain unproven here.

The trace also has 16,949 malformed command JSON records caused by the raw
uint8 `trajectory_flag` byte, 13 sequence gaps / reported contention drops, and
no final footer. Positive stack/odometry/audit evidence above remains usable,
but this trace is not a complete state reconstruction or negative-evidence proof.

## Evidence hashes

All paths below are under `urban_probe_v1/` beside this note's parent directory.

- `cpp_trace/contact_trace_3899291.jsonl`:
  `968338be22c0cd4b3d7c33d03799b41b1b8e961094a395a6cce5f277c3e89193`.
- `flight/artifacts/urban_blocks_u01_run62002_adaptive.attempt1.solid_audit.json`:
  `6ef43312450a6d9c86a3ae270c1d07e80dd58a99ea1616be99736fd9dcb04e24`.
- Matching `.odometry.csv`:
  `876b4bc676136ca7e6b14efbf62506c7bd89e87bda21b78a0161a0d0763ab67e`.
- Matching `.stack.log`:
  `acf8c854825bbfa7912fb7d263d0a0fae646f07f80e8694a7aa37a0c2a03faa1`.

No production-readiness claim follows from this diagnostic. The separate ROG
offline regressions justify two bounded mapper fixes but do not prove that
those fixes alone prevent this particular first-leg entry.
