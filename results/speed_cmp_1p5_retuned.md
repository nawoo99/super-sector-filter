# Speed test @1.5 with a RE-TUNED controller — adaptive still not justified

The earlier @1.5 test was scrappy partly because the SO3 controller was tuned for 0.9.
Re-tuned for speed: controller vmax_h 1.8→2.2, tilt_max 30→33°, Kp_pos/Kv up; SUPER
max_vel 0.9→1.5, max_acc 3.5→5, jerk 25→40. (Tilt capped 33° = the altitude-hold limit
for this weak-TWR LiDAR-x500: thr_max 0.98·cos(33°)=0.82 ≈ hover; beyond it sinks.)

Tune-check: a single sector run now COMPLETES 4/4 at 1.5 (was failing before) but still
3 collisions with slight penetration → tracking overshoot remains (weak TWR can't
decelerate hard enough for turns at speed).

## sector vs adaptive @1.5 (re-tuned), dense seed7, per-run bringup, n=3
| mode | completes | collisions | mean(flown) |
|------|:---------:|:----------:|:-----------:|
| sector   | 2/3 | [4, 3, 4] | 3.7 |
| adaptive | **1/3** | [7, 7, 2] | **5.3** |

## Finding
**Adaptive collides MORE than sector at speed (5.3 vs 3.7) and completes worse (1/3 vs
2/3)** — the opposite of "adaptive recovers safety." Adding sensing (risk-gate ≈ full-view
in the dense field) over-populates ROG-Map → degrades SUPER planning → more collisions +
stalls, exactly as the `full` mode does. The 1.5 collisions are tracking-overshoot-dominated
(weak TWR); adding information makes it worse, not better.

## Verdict across ALL tested static regimes
density (0.9) · geometry / cluttered corners (0.9) · speed (1.5, re-tuned) — in EVERY one,
pure sector matches or beats adaptive on both safety and completion, and keeps the ~64%
raycast savings. **The "adaptive full-view recovery mitigates a sector safety cost" thesis
is empirically unsupported for STATIC obstacles at any tested speed.** Clean flight much
above 0.9 is not achievable with this weak-TWR vehicle, so a perfectly clean high-speed
test isn't possible here — but the RELATIVE result (adaptive ≥ sector collisions) is clear.

The one regime not yet tested, where the forward-only blindspot is canonically real, is
**DYNAMIC (moving) obstacles** — a side-approaching moving obstacle is never in the ±60°
forward cone and persistence can't cover it. That is the honest remaining test for adaptive.

Config + controller reverted to the validated 0.9 baseline. Raw rows:
`speed_cmp_1p5_retuned_seed7.csv`.
