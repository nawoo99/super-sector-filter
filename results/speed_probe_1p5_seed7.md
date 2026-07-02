# Speed probe @ max_vel 1.5 — does pure sector's safety cost appear at speed?

Motivation: at max_vel 0.9 pure sector is safe (0–1 collisions) + 64% savings, so the
"adaptive recovers a safety cost" thesis has no cost to recover. Hypothesis: at higher
speed the drone passes abeam obstacles before the forward ±60° cone maps them → sector
collides → adaptive earns its keep. Bumped SUPER max_vel 0.9→1.5 (acc 3.5→5, jerk 25→35).

## Initial probe (same-bringup back-to-back, n=3) — MISLEADING (n=1 flown)
Only the 1st run after each bringup flew; runs 2–3 failed to re-init. The one flown run:
sector 5 collisions, adaptive 1 — looked like a clean "adaptive rescues sector at speed"
result, but it was a single flight per mode.

## Robust confirmation (FRESH BRINGUP PER RUN, n=3)
| mode @1.5 | completes | collisions | min-clearance |
|-----------|:---------:|:----------:|:-------------:|
| sector    | 2/3 | [1, 4, 2] | ~0, near/at penetration |
| adaptive  | **0/3** | [1, 1, 4] | penetration in one run |

## Findings
1. **The initial "5 vs 1" was n=1 noise.** With n=3 the collision counts OVERLAP
   (sector mean ~2.3, adaptive ~2.0). Adaptive does NOT robustly reduce sector's
   collisions at speed.
2. **Flight quality collapses for both modes at 1.5** with the current SO3 controller
   (tuned for 0.9): scrappy tracking, penetrations, incomplete loops. So 1.5 is NOT a
   fair test of the sensing blindspot — collisions are dominated by controller overshoot.
3. **Adaptive completes WORSE (0/3 vs 2/3)**: risk-gate ≈ full-view in the dense field →
   ROG-Map over-population → SUPER stalls (all 3 adaptive runs timed out at 2 corners).
   Consistent with the `full` mode result (over-population degrades planning).

## Overall conclusion (consistent across all experiments)
- **Under CLEAN flight, pure sector dominates**: safe + 64% cost cut + best completion.
- **full-view (full mode, or risk-gate adaptive in dense fields) OVER-POPULATES ROG-Map
  → degrades/stalls SUPER planning.** Sector's sparse map is actually *better* for the
  planner in dense fields.
- The original "adaptive recovers sector's safety cost" thesis is **empirically not
  supported**: at 0.9 there is no safety cost; at 1.5 flight quality (not the blindspot)
  drives collisions and adaptive doesn't help (and hurts completion).
- A fair speed test would require re-tuning the controller for clean 1.5 flight first
  (raise vmax_h, re-tune SO3 gains) — untested. Config reverted to the validated 0.9.

Raw rows: `speed_probe_1p5_seed7.csv`.
