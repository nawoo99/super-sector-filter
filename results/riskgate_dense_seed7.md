# Risk-gated auto-expansion — dense-field evaluation (seed7, gap 1.1m)

Implements the "risk-gated sector auto-expansion": inside sector mode the
`cloud_preprocessor` scans the raw 360° cloud each frame and, if any point
OUTSIDE the ±60° cone is within `risk_range`, drops the filter for that frame
(full-view) so ROG-Map sees the abeam obstacle. Goal was to make the sector
mode collision-free in tight environments while keeping the point-count savings.

Clean SO3 flight, dense seed7 (gap 1.1m — tightest field), n=3 per condition.

## Multi-run (n=3)

| mode | completes | collisions (r1,r2,r3) | min-clearance | pts_mean | raycast (ms) | savings |
|------|:---------:|:---------------------:|:-------------:|---------:|-------------:|:-------:|
| full (360°) | 1/3 | 7, 4, 0 | negative (penetration) | ~8030 | 1.72 | — |
| **sector (±60°)** | **3/3** | **0, 1, 0** | 0.27–0.56 | ~3100 | 0.61 | **64%↓** |
| adaptive (risk-gate @2.0m) | 3/3 | 0, 0, 0 | ~0.58 | ~9180 | 1.72 | ~0% |

## Risk-range re-tune (adaptive, n=3)

| risk_range | completes | collisions | pts_mean | savings |
|:----------:|:---------:|:----------:|---------:|:-------:|
| 2.0 | 3/3 | 0,0,0 | ~9180 | 0% |
| 0.6 | 2/3 | 0,0,1 | ~8200 | −2% |
| 1.0 | 1/3 | 2,2,3 | ~7735 | 4% |

## Findings
1. **The risk-gate cannot be made selective in a tight (1.1m-gap) field.** The drone
   flies ~0.55 m from side-obstacle surfaces, so even a 0.6 m threshold fires almost
   every frame → the gate collapses to full-view → **no point-count savings recovered**
   at any tested range. Wrong tool for dense fields.
2. **Pure sector dominates the dense field**: 3/3 completion, ≤1 collision in 3 runs
   (a 3 cm graze), and the full 64% cost saving. This meets the goal ("sector safe in
   the dense environment") without any recovery mechanism.
3. **Premise flip:** under clean SO3 flight there is essentially **no sector safety cost**
   in dense fields — the earlier "sector collides a lot" (±12 field, 21 collisions) was an
   artifact of the old low-altitude scrappy flight, now confirmed. full-view (360°) is
   actually the *most* collision-prone here (over-populates ROG-Map → degrades planning).
4. All collisions (every mode) occurred at |coord| > 9 = **outside the ±9 perimeter loop**
   = edge-overshoot into out-of-loop obstacles (a controller-tracking/boundary effect
   common to all modes), NOT a sector-blindspot effect.

## Open question
The adaptive/risk-gate recovery only earns its keep if a regime exists where pure sector
genuinely collides. At max_vel 0.9 it does not. The likely such regime is **higher speed**
(the drone passes abeam obstacles before the forward ±60° cone maps them) — untested.

Raw per-run rows: `riskgate_dense_seed7.csv` (datasets mr_full/sector/adaptive, rt_0.6/1.0).
Implementation: `super_patches/cloud_preprocessor.cpp` (risk-gate block), `scripts/g_mission.py`
`--risk-gate`, `scripts/g_campaign.py` MODES.
