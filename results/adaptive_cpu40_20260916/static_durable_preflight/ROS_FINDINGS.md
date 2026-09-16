# Plan A actual no-flight transport findings

2026-09-16. Six predeclared arms, one attempt each, serial domain190, actual
installed standalone simulator/seed1. No mission, FSM, goal/command publisher,
flight, host tuning, fixture retry or runtime edits during this matrix.

| Publisher | Reader QoS | Sequence | Full geometry received (first / second / reconnect) | Result |
|---|---|---|---:|---|
| Legacy BestEffort/Volatile/100 | Legacy BestEffort/Volatile | Reader-first | 5 / 0 / not reached | FAIL: second reader timeout |
| Legacy BestEffort/Volatile/100 | Legacy BestEffort/Volatile | Late first reader | 0 / not reached / not reached | FAIL: first late reader timeout |
| Candidate Reliable/TransientLocal/1 | Legacy BestEffort/Volatile | Reader-first | 8 / 0 / not reached | FAIL: second reader timeout |
| Candidate Reliable/TransientLocal/1 | Legacy BestEffort/Volatile | Late first reader | 0 / not reached / not reached | FAIL: first late reader timeout |
| Candidate Reliable/TransientLocal/1 | Reliable/TransientLocal/1 | Reader-first | 8 / 1 / 1 | PASS: all transitions |
| Candidate Reliable/TransientLocal/1 | Reliable/TransientLocal/1 | Late first reader | 3 / 1 / 1 | PASS: all transitions |

The two successful diagnostic sequences include2→1 count decrease and
1→0→1 disconnect/reconnect. Failed sequences preserve their early geometry
evidence and stop at the first failed phase; unexercised later phases are not
called passed. All received clouds matched the exact legacy baseline SHA
`b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`, complete
241490-point payload, field layout, row/point stride and world frame.

All six direct children exited0 after one SIGINT, were reaped, and no simulator
or fixture process remained after the last arm. Final source cadence summaries
were10.000863,10.001546,10.001280,10.003744,10.002446,10.003248Hz respectively;
all satisfy9.5–10.5Hz. These are no-flight cadence summaries, not per-callback
latency or flight-safety proofs.

## Interpretation and decision

Changing the publisher alone did **not** solve unchanged legacy-reader late
delivery. Reliable/transient-local reader diagnostics passed both complete
sequences. This supports the intended durable/reliable static-map contract;
it does not identify every historical best-effort loss mechanism or turn
best-effort subscribers into reliable historical consumers.

**Existing-reader acceptance remains failed. Keep SUPER_STATIC_PC_DURABLE=0;
do not adopt Plan A or implement Plan B on the basis of these diagnostics.**
C15 CPU comparison stays durable0. No acceptance criterion is relaxed, no
successful diagnostic replaces the failed compatibility arms, and no40% CPU
claim follows from this work. Any future migration of actual static-map readers
requires a separately authorized interface change and new verification.

Actual QoS evidence is intentionally split: publisher `get_actual_qos()`
verified history/depth plus reliability/durability. FastDDS graph information
really returned historyUNKNOWN/depth0 in all six arms, so those graph fields
are explicitly unverified while graph reliability/durability are verified.
Requested constants were not misreported as actual settings.

Raw results/logs remain in six `ros_*_attempt1/` directories and matching
console logs. `matrix_summary.json` is an offline aggregation and
`summarize_matrix.py` never starts or retries an experiment. Useful observation
time sums≈69.3s; wall-clock gaps between serial cases are not CPU measurements.
