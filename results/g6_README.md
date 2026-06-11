# G6 raw data

`g6_perf_log.csv` — ROG-Map `rm_performance_log.csv` from one run, drone held at
a fixed pose. Sector filter was ON for the first segment, then `cloud_preprocessor`
was relaunched with `sector_enable:=false` for the second segment (ROG-Map / fsm
never restarted, so the same file appends across both).

Segmentation: ON = data rows up to file line 503; OFF = the rest.
Analyze: `python3 ../scripts/g6_analyze.py 503 40 g6_perf_log.csv`

Columns: Total, Raycast, Update_cache, Inflation, PointCloudNumber, CacheNumber, InflationNumber (times in seconds).
