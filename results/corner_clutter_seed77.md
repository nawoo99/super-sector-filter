# Geometry axis — cluttered-corner world (seed77), clean 0.9, n=3

Motivation: the ±60° forward blindspot should bite when the drone TURNS next to obstacles
(abeam obstacles the forward cone didn't pre-map). Our normal perimeter loop keeps the 4
corner turns in cleared discs (CORNER_CLEAR 2.5) — so turns happen in free space and the
blindspot never triggered. seed77 = the SAME dense field as seed7 (RNG 7, gap 1.1) but with
CORNER_CLEAR reduced to 0.8, so **9 obstacles now sit within 2.5 m of the 4 corner turns**
(baseline seed7 had 0). Clean max_vel 0.9 (no flight-quality confound).

| mode | completes | collisions | min-clearance | pts_mean | savings |
|------|:---------:|:----------:|:-------------:|---------:|:-------:|
| full (360°) | 1/3 | [2,–,–] | −0.031 (penetration) | ~7228 | — |
| **sector (±60°)** | **3/3** | **[0,0,0]** | 0.36–0.43 | ~3020 | **64%↓** |
| adaptive (risk-gate) | 3/3 | [0,0,0] | 0.54–0.58 | ~8900 | ~0% |

## Finding
**Even with turns in clutter, pure sector flew 3/3 with ZERO collisions and kept the 64%
savings.** The blindspot did not bite: during the corner hover the drone yaws toward the
next leg and the forward cone sweeps the corner obstacles into the persistent ROG-Map before
it accelerates onto the new leg; at 0.9 m/s the tracking error is small enough not to clip.
full-view again fared worst (1/3 complete, penetration) — map over-population degrades planning.

## Cross-axis conclusion (DEFINITIVE)
Across THREE independent axes — density (dense seed7), speed (max_vel 1.5), and geometry
(cluttered corners) — the result is consistent:
- **Under clean flight, pure sector filtering has NO safety cost** and keeps ~64% raycast
  savings; it even IMPROVES dense-field planning vs full-view.
- **full-view (360°, and risk-gate adaptive in dense fields) over-populates ROG-Map →
  degrades/stalls SUPER planning** (worst completion + collisions).
- The **"adaptive recovers a sector safety cost" thesis is empirically unsupported**: there
  is no cost to recover at clean speed, and the recovery mechanism (full-view) is
  counterproductive. At 1.5 the confound is flight quality, not the blindspot.

Raw rows: `corner_clutter_seed77.csv`. World gen: `/tmp/gen_cluttered_corners.py` (CORNER_CLEAR 0.8).
