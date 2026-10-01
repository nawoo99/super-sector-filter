# c39 seven-map result: documented interrupted-campaign completion

The first session retained 173 unique flights, then stopped after a recovery
log audit rejected two distinct certified paths in one Full interval. A revised
strict audit of those unchanged logs passed 173/173. The second session ran
the 37 unflown slots once each. The combined evidence is 210 unique planned
flights, with no replacement attempts. This was not one uninterrupted run.

| Map | Mode | Complete | Contact runs | Time s | CPU cores | CPU core-s | Input MiB/s | Input MiB/run | Map ms/frame | Adaptive Full opens |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gapfree_d1_m01 | full | 10/10 | 0/10 | 56.50 | 0.678 | 40.79 | 11.218 | 646.42 | 25.87 | — |
| gapfree_d1_m01 | sector | 10/10 | 0/10 | 95.48 | 0.425 | 41.90 | 3.039 | 294.46 | 7.87 | — |
| gapfree_d1_m01 | adaptive | 10/10 | 0/10 | 57.93 | 0.513 | 31.72 | 4.041 | 237.40 | 11.27 | 10.20 |
| gapfree_d1_m02 | full | 10/10 | 0/10 | 47.77 | 0.714 | 36.84 | 10.910 | 521.41 | 27.05 | — |
| gapfree_d1_m02 | sector | 10/10 | 0/10 | 67.78 | 0.443 | 31.69 | 2.718 | 185.55 | 8.62 | — |
| gapfree_d1_m02 | adaptive | 10/10 | 0/10 | 49.87 | 0.520 | 28.05 | 3.539 | 176.82 | 11.21 | 5.90 |
| gapfree_d1_m03 | full | 10/10 | 0/10 | 51.50 | 0.693 | 38.44 | 11.252 | 583.59 | 26.16 | — |
| gapfree_d1_m03 | sector | 10/10 | 0/10 | 87.76 | 0.447 | 40.44 | 2.952 | 264.94 | 8.19 | — |
| gapfree_d1_m03 | adaptive | 10/10 | 0/10 | 58.30 | 0.522 | 32.54 | 4.153 | 248.48 | 10.72 | 9.10 |
| gapfree_d1_m04 | full | 10/10 | 0/10 | 50.21 | 0.696 | 37.62 | 10.732 | 538.99 | 26.45 | — |
| gapfree_d1_m04 | sector | 9/10 | 1/10 | 82.38 | 0.432 | 36.06 | 3.082 | 275.10 | 8.16 | — |
| gapfree_d1_m04 | adaptive | 10/10 | 0/10 | 53.75 | 0.516 | 29.65 | 4.008 | 217.83 | 11.33 | 7.90 |
| gapfree_d1_m05r2 | full | 10/10 | 0/10 | 45.71 | 0.686 | 33.91 | 11.414 | 521.76 | 25.48 | — |
| gapfree_d1_m05r2 | sector | 10/10 | 0/10 | 66.32 | 0.441 | 30.89 | 2.948 | 195.34 | 8.29 | — |
| gapfree_d1_m05r2 | adaptive | 10/10 | 0/10 | 50.90 | 0.507 | 27.74 | 3.871 | 198.01 | 10.41 | 7.20 |
| urban_blocks_u01 | full | 10/10 | 0/10 | 49.34 | 0.698 | 37.90 | 11.684 | 576.08 | 28.40 | — |
| urban_blocks_u01 | sector | 10/10 | 0/10 | 72.76 | 0.443 | 34.30 | 2.721 | 197.88 | 9.07 | — |
| urban_blocks_u01 | adaptive | 10/10 | 0/10 | 53.23 | 0.515 | 29.90 | 3.439 | 183.88 | 11.60 | 7.00 |
| forest_cluster_f01 | full | 10/10 | 0/10 | 56.99 | 0.736 | 45.52 | 10.729 | 613.01 | 29.42 | — |
| forest_cluster_f01 | sector | 9/10 | 0/10 | 96.59 | 0.430 | 42.74 | 2.787 | 295.63 | 8.05 | — |
| forest_cluster_f01 | adaptive | 10/10 | 0/10 | 67.52 | 0.519 | 37.71 | 4.527 | 323.38 | 11.36 | 10.40 |

## Separate aggregate groups

| Group | Mode | Complete | Contact runs | Time s | CPU cores | CPU core-s | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal Map1–5 | full | 50/50 | 0/50 | 50.34 | 0.694 | 37.52 | 11.105 | 562.43 | 26.20 |
| Normal Map1–5 | sector | 49/50 | 1/50 | 79.94 | 0.438 | 36.19 | 2.948 | 243.08 | 8.23 |
| Normal Map1–5 | adaptive | 50/50 | 0/50 | 54.15 | 0.516 | 29.94 | 3.922 | 215.71 | 10.99 |
| Urban | full | 10/10 | 0/10 | 49.34 | 0.698 | 37.90 | 11.684 | 576.08 | 28.40 |
| Urban | sector | 10/10 | 0/10 | 72.76 | 0.443 | 34.30 | 2.721 | 197.88 | 9.07 |
| Urban | adaptive | 10/10 | 0/10 | 53.23 | 0.515 | 29.90 | 3.439 | 183.88 | 11.60 |
| Forest | full | 10/10 | 0/10 | 56.99 | 0.736 | 45.52 | 10.729 | 613.01 | 29.42 |
| Forest | sector | 9/10 | 0/10 | 96.59 | 0.430 | 42.74 | 2.787 | 295.63 | 8.05 |
| Forest | adaptive | 10/10 | 0/10 | 67.52 | 0.519 | 37.71 | 4.527 | 323.38 | 11.36 |

## Change relative to Full

| Group | Mode | Mean CPU | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |
|---|---|---:|---:|---:|---:|---:|
| Normal Map1–5 | sector | +36.9% | +3.5% | +73.5% | +56.8% | +68.6% |
| Normal Map1–5 | adaptive | +25.6% | +20.2% | +64.7% | +61.6% | +58.1% |
| Urban | sector | +36.5% | +9.5% | +76.7% | +65.7% | +68.1% |
| Urban | adaptive | +26.2% | +21.1% | +70.6% | +68.1% | +59.1% |
| Forest | sector | +41.5% | +6.1% | +74.0% | +51.8% | +72.6% |
| Forest | adaptive | +29.4% | +17.2% | +57.8% | +47.2% | +61.4% |

Positive percentages indicate a reduction; negative percentages
indicate an increase. CPU cores is mean use, while CPU core-s/run
includes differences in mission duration.
