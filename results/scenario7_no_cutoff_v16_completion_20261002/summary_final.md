# c41 fresh seven-map n10 final result (2026-10-02)

The predeclared cohort is complete: 7 maps × 3 modes × 10 physical runs =
210 unique flights. The first 93 flights and their original v7 stop verdict
remain in `scenario7_no_cutoff_v15_n10_20261002`; the other 117 flights are
in this v16 continuation. The corrected v8 event audit passes all 210 flights.
Every map/mode cell contains exactly 10 runs, with no replacement or retry.
The original Forest Adaptive overlap was a log-audit false rejection; it was
not a flight failure.

| Map | Full complete/contact runs | Active-Yaw Sector complete/contact runs | Adaptive complete/contact runs |
|---|---:|---:|---:|
| Normal 1 (`gapfree_d1_m01`) | 10/10 · 0/10 | 9/10 · 1/10 | 10/10 · 0/10 |
| Normal 2 (`gapfree_d1_m02`) | 10/10 · 0/10 | 10/10 · 0/10 | 10/10 · 0/10 |
| Normal 3 (`gapfree_d1_m03`) | 10/10 · 0/10 | 10/10 · 0/10 | 10/10 · 0/10 |
| Normal 4 (`gapfree_d1_m04`) | 10/10 · 0/10 | 9/10 · 1/10 | 10/10 · 0/10 |
| Normal 5 (`gapfree_d1_m05r2`) | 10/10 · 0/10 | 9/10 · 1/10 | 10/10 · 0/10 |
| Urban (`urban_blocks_u01`) | 10/10 · 0/10 | 10/10 · 0/10 | 10/10 · 0/10 |
| Forest (`forest_cluster_f01`) | 9/10 · 0/10 | 10/10 · 1/10 | 10/10 · 0/10 |
| **Total** | **69/70 · 0/70** | **67/70 · 4/70** | **70/70 · 0/70** |

Completion and contact are separate observations. Forest Sector repeat7
contacted a cylinder but still reached the final waypoint; therefore the
Sector safe-completion count is 66/70, not 67/70.

| Per-run mean over all seven maps, including non-completions | Full | Sector | Adaptive | Adaptive vs Full |
|---|---:|---:|---:|---:|
| Observed mission/termination time (s) | 51.13 | 77.56 | 56.27 | +10.1% |
| End-to-end mean CPU (cores) | 0.726 | 0.432 | 0.512 | −29.5% |
| End-to-end CPU time (core-s/run) | 40.14 | 35.05 | 31.09 | −22.5% |
| Planner input rate (MiB/s) | 11.238 | 2.831 | 3.954 | −64.8% |
| Total planner input (MiB/run) | 581.82 | 224.02 | 228.65 | −60.7% |
| Map update (ms/frame) | 29.47 | 9.26 | 12.09 | −59.0% |

The time column is the observed duration to completion **or terminal stop**;
it is not a completion-only travel-time comparison. CPU and payload averages
also include the non-completing runs. The exact map/mode means are in
`combined_summary_by_map.csv` and `combined_summary_by_map.md`.
`final_flight_manifest.csv` records all 210 planned flight identities,
outcomes, metrics, archive origins, and source-log hashes.

The one Full failure is Forest repeat3, run97036: contact 0, only waypoint
1/5 reached, then the measurement-only 60 s/2 cm persistent-no-progress
observer stopped it at 104.02 s near (8.675, 18.973, 2.686) m. Its log shows
repeated `NO_PATH`, CIRI polytope-generation failures, and trajectory-guard
rejections. This establishes a stopped planning state, not a mission-duration
timeout; it does **not** yet establish the sole root cause or justify deleting
the run. Sector contact/non-completion cases were Normal 1 repeat4 run97040,
Normal 5 repeat7 run97074, and Normal 4 repeat9 run97093. Forest Sector
repeat7 run97076 had contact but completed.

Thus this independent fresh cohort supports Adaptive 70/70 contact-free
completion and relative workload reduction, but **does not support Full 100%
completion**. These are finite-simulation observations, not population-level
guarantees. The next scientific step is a separate, predeclared diagnosis of
the Forest Full stall; the frozen c41 result must not be retroactively tuned
or replaced.
