# Seed1 C19 diagnostic CPU attribution

ON n=1 per mode, exclusive thread CPU only. 1 core = 100% of one logical CPU.

| Mode | Window s | Autonomy measured subtotal (cores) | Simulator callbacks | Diagnostic/visualization | Composed accounting residual range | Other experiment processes |
|---|---:|---:|---:|---:|---:|---:|
| full | 30.059 | 0.387961 | 0.052925 | 0.000577 | 0.036595 to 0.070528 | 0.038923 to 0.041252 |
| sector | 35.049 | 0.206890 | 0.026457 | 0.001442 | 0.062224 to 0.078487 | 0.042512 to 0.045365 |
| adaptive | 30.059 | 0.209239 | 0.029530 | 0.001677 | 0.044657 to 0.063952 | 0.043913 to 0.047240 |

The subtotal is NOT full autonomy CPU. Residual includes executor/DDS, uninstrumented work, profiling cost and completion/report boundary error. It is an accounting range, not a physical bound or avoidable waste. Noncomposed launcher/mission CPU remains included in primary cgroup metrics and is separately bounded in alignment.json. GPU work is not CPU work.

## New ON/OFF smoke runs (not pooled with original OFF n=5)

| Arm | Mode | Complete | Contacts | Mission s | Experiment mean cores | Experiment CPU core-s |
|---|---|---:|---:|---:|---:|---:|
| ON | full | True | 0 | 39.410 | 0.542691 | 22.041888 |
| ON | sector | True | 0 | 38.970 | 0.342253 | 13.896686 |
| ON | adaptive | True | 0 | 37.450 | 0.345792 | 13.321922 |
| OFF | full | True | 0 | 37.670 | 0.530831 | 21.012528 |
| OFF | sector | True | 0 | 36.760 | 0.348768 | 13.456781 |
| OFF | adaptive | True | 0 | 43.750 | 0.368413 | 16.496592 |

One reversed-order ON/OFF pair per mode does not isolate profiler overhead from scheduling/trajectory variability. Old frozen C19 n=5 remains the main performance evidence; these runs verify diagnostic coverage and regressions. No 40% acceptance selection or automatic retries.
