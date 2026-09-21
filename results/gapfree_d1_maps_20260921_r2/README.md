# Gapfree G5-R2 map revision (2026-09-21)

This folder defines the active five-map suite as the frozen original G1–G4
plus `gapfree_d1_m05r2`. The original `gapfree_d1_m05` assets and results are
not modified or pooled with R2.

G5-R2 retains 410 static cylinders, 1 m diameter, 3 m height, the 64×64 m
field, simulator configuration, mission, planner, and sensor policy. Only
cylinder index 199 is moved:

- old center: `(0.931831, 1.726500)`
- new center: `(4.25, 29.50)`

The change was made after an Adaptive development-preflight contact in
`gapfree_n5_20260921_111647_3386864`; it is therefore outcome-informed map
development, not blind validation. Fresh R2 runs are required and prior G5
runs must not be counted as R2 evidence. Full provenance and exact hashes are
in `manifest.json`; offline geometry checks are in `verification.json`.
