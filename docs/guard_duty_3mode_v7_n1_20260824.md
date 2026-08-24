# Guard active/hold attribution and map-level v7 three-mode gate

Date: 2026-08-24

## Result first

The unchanged 5 Hz, 2.5 s hold, 6,000-extra-point Adaptive behavior was
instrumented to separate direct trajectory-guard `active` frames from
post-recovery `hold-only` frames.  The order-crossed v=7, `loop24.txt`, static
PCD, 240 s seed1-10 x n=1 gate produced 30/30 valid rows with one attempt,
zero retry, zero FSM swap, and zero OOM delta.

All three modes completed 10/10.  Full had zero live/static contact.  Fixed
Sector had one live-cloud contact on seed10.  Adaptive also had one live-cloud
contact, on seed7, despite completing the mission.  Static-PCD contact was zero
for all 30 rows, but the Adaptive seed7 static body clearance was only +0.036 m.
The Adaptive result therefore does **not** meet the contact-zero target.

## Per-map completion, contact, time, and clearance

`F/S/A` means Full / fixed Sector / Adaptive.  Contact is the live-cloud event
count; every static-PCD contact count was zero.  Clearance subtracts the 0.20 m
body radius from the nearest static-PCD distance.

| map | complete F/S/A | live contact F/S/A | time F/S/A (s) | static clearance F/S/A (m) |
|---:|:---:|:---:|:---:|:---:|
| 1 | O / O / O | 0 / 0 / 0 | 57.49 / 68.01 / 64.16 | +0.242 / +0.237 / +0.260 |
| 2 | O / O / O | 0 / 0 / 0 | 56.98 / 59.69 / 57.67 | +0.325 / +0.266 / +0.331 |
| 3 | O / O / O | 0 / 0 / 0 | 63.87 / 58.97 / 78.69 | +0.307 / +0.293 / +0.295 |
| 4 | O / O / O | 0 / 0 / 0 | 75.05 / 82.02 / 86.74 | +0.327 / +0.278 / +0.297 |
| 5 | O / O / O | 0 / 0 / 0 | 96.30 / 73.10 / 90.46 | +0.203 / +0.212 / +0.207 |
| 6 | O / O / O | 0 / 0 / 0 | 88.33 / 79.79 / 105.46 | +0.244 / +0.252 / +0.243 |
| 7 | O / O / O | 0 / 0 / **1** | 91.06 / 76.83 / 152.61 | +0.244 / +0.293 / **+0.036** |
| 8 | O / O / O | 0 / 0 / 0 | 68.82 / 95.22 / 100.18 | +0.278 / +0.200 / +0.265 |
| 9 | O / O / O | 0 / 0 / 0 | 101.01 / 122.73 / 131.66 | +0.275 / +0.231 / +0.223 |
| 10 | O / O / O | 0 / **1** / 0 | 99.52 / 109.85 / 107.87 | +0.229 / **+0.069** / +0.255 |

## Per-map mapping cost and Adaptive activation

Adaptive activation is shown as actual effective-full-open edges / direct
guard episodes.  The first value also includes the existing stall and bounded
replan triggers, so it is not expected to equal the direct episode count.
CPU is process CPU on this machine and can exceed 100% for multi-threaded work.

| map | points/update F/S/A | map total/update F/S/A (ms) | FSM CPU F/S/A (%) | Adaptive open edges / guard episodes | active / hold duty (%) |
|---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 15,530 / 7,123 / 12,125 | 35.26 / 12.58 / 23.08 | 125.2 / 92.2 / 100.8 | 21 / 4 | 10.8 / 10.4 |
| 2 | 15,407 / 6,588 / 12,660 | 35.32 / 12.95 / 26.05 | 119.2 / 103.1 / 100.2 | 17 / 8 | 9.1 / 31.4 |
| 3 | 23,213 / 10,295 / 18,156 | 43.16 / 15.29 / 33.45 | 111.5 / 98.2 / 74.2 | 12 / 25 | 30.2 / 41.4 |
| 4 | 22,465 / 11,873 / 19,494 | 40.03 / 14.41 / 34.47 | 102.0 / 75.7 / 74.5 | 4 / 36 | 42.1 / 44.1 |
| 5 | 27,726 / 12,909 / 21,367 | 43.06 / 16.57 / 35.45 | 77.5 / 85.7 / 65.7 | 11 / 40 | 30.8 / 40.5 |
| 6 | 29,941 / 15,350 / 23,102 | 41.99 / 15.63 / 32.73 | 73.7 / 84.3 / 63.1 | 12 / 41 | 34.8 / 39.7 |
| 7 | 35,798 / 18,616 / 26,024 | 43.82 / 16.61 / 32.34 | 79.0 / 92.1 / 41.6 | 6 / 54 | 51.0 / 29.7 |
| 8 | 33,181 / 18,347 / 25,388 | 46.74 / 16.27 / 33.18 | 106.3 / 67.5 / 58.3 | 7 / 43 | 36.4 / 37.8 |
| 9 | 42,259 / 21,996 / 33,310 | 42.36 / 14.96 / 31.74 | 77.0 / 52.8 / 50.7 | 5 / 52 | 47.4 / 44.6 |
| 10 | 41,600 / 21,085 / 33,191 | 41.22 / 15.65 / 32.18 | 79.9 / 56.0 / 60.6 | 7 / 37 | 44.2 / 42.0 |

The update-count-weighted aggregate is:

| mode | completion | contact runs | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 0 | 79.843 | +0.203 | 27,995 | 40.990 | 91.40 |
| fixed Sector | 10/10 | 1 | 82.621 | +0.069 | 14,075 | 15.013 | 76.91 |
| Adaptive | 10/10 | 1 | 97.550 | +0.036 | 22,554 | 31.376 | 64.10 |

Against Full, Adaptive reduced points/update 19.43%, map total/update 23.45%,
map update time 15.37%, and time-weighted FSM CPU 29.87%.  Mean mission time was
22.18% longer.  Adaptive averaged 33.68% direct-active duty and 36.17%
hold-only duty, for 69.85% direct-guard open duty.  It recorded 340 direct
guard episodes and 339 corresponding full-refresh frames across the ten maps;
the final episode can leave one refresh pending at shutdown.

## Why the Adaptive seed7 contact occurred

The event was not a completion failure or a high-speed pass-through.  It
occurred 4.8221 s into the mission at `[6.8925, 7.8803, 1.2118]`, while an
emergency brake was finishing at 0.2229 m/s.  The nearest live-cloud point was
0.19861 m away, 1.39 mm inside the 0.20 m body threshold.  The common static
PCD measured 0.236 m at its worst sample, so this is a live-only contact but
with only +0.036 m static body clearance; it must not be dismissed as safe.

The stack log shows the causal ordering:

1. At epoch 1787565836.311, the guard detected `MAP_STALE` at map age 0.558 s
   and activated the direct recovery signal.
2. A 0.529 s brake ending near `[6.886, 7.880, 1.208]` was certified `SAFE`
   against that stale map and published.
3. The Adaptive filter received the true edge and scheduled the intended
   uncapped full scan, but this can only update the next map; it cannot change
   the brake already being executed.
4. At epoch 1787565836.752, the live-cloud detector recorded the contact at the
   brake endpoint.

Therefore the remaining hole is earlier than the 2.5 s post-guard hold.  A
post-event rate increase cannot protect the first stale-map brake.  The next
candidate should be a bounded pre-stale full refresh triggered before the
guard's 0.50-0.55 s stale limit, with an ACK/version gate so it cannot flood the
map worker.  Its target is to make lateral obstacle evidence current before a
brake must be certified, while retaining the existing true-edge refresh and
hold until repeated testing proves otherwise.

## Rejected active-only 6 Hz candidate

Before the final three-mode gate, active and hold-only duty were measured on
seed6-10 with the established 5 Hz profile.  All five completed without
contact; mean direct-active/hold-only duty was 59.42%/32.86%.  This showed that
actual guard recurrence, not hold alone, dominated the late-map open state.

A second seed6-10 smoke raised the cap to 6 Hz only while the direct guard was
active.  It also completed 5/5 without contact, but mean time increased
133.02 -> 163.89 s (+23.20%) and map total/update increased 26.26 -> 29.45 ms
(+12.14%).  Only seed8 improved in time.  The candidate is rejected; the
runtime default remains disabled (`0`, meaning use the established 5 Hz cap).

Primary raw results are
`results/guard_duty_attribution_adaptive_seed6_10_n1_raw_20260824.csv`,
`results/guard_active6_adaptive_seed6_10_n1_raw_20260824.csv`, and
`results/guard_duty_final_order_crossed_3mode_v7_n1_raw_20260824.csv`.
This is an n=1 diagnostic gate, not a population estimate; no McNemar test was
performed.  Raw-cloud CIRI remains default false and non-authoritative.
