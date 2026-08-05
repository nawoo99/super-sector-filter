# seed11 raw-direct/adaptive n=30 artifacts

Use `native_seed11_raw_adaptive_n30.csv` and its 60 JSON files as the final,
fully instrumented campaign. Both modes publish ROG occupied voxels at 2 Hz and
use the same contact monitor.

- Final rows: 60/60, with 30 runs per mode and alternating first mode.
- Completion: raw 30/30, adaptive 29/30.
- Live-cloud contact runs: raw 8/30, adaptive 14/30.
- Efficiency: adaptive reduced points 66.2%, raycast 60.6%, and mapping 51.3%.
- Statistics: Fisher exact p=0.180; paired McNemar exact p=0.210.
- Contact payloads: 89 events. Each event records pose, velocity, local raw
  cloud, local static PCD, occupied-map state, A* frontend path, committed
  trajectory, and position command. Five startup events occurred before the
  first 2 Hz occupied-map publication and therefore record zero map points.

Files:

- `native_seed11_raw_adaptive_n30.csv`: final per-run metrics.
- `native_seed11_raw_adaptive_n30_summary.csv`: final aggregate table.
- `native_seed11_raw_adaptive_n30_forensics/`: final per-run JSON payloads.
- `native_seed11_raw_adaptive_n30_pre_occupancy_capture.csv` and matching
  directory: preliminary 60-run batch before occupied-map publication was
  enabled. It is retained for timing-sensitivity analysis, not pooled with the
  final safety result.
- `native_seed11_raw_adaptive_n30_smoke*.csv` and matching directories:
  incremental validation of PCD contact, contact capture, monitor CPU
  optimization, occupied-map publisher, and occupied-map counters.

The static PCD check is an auxiliary union of occupied samples inflated by the
0.20 m robot radius. PCD-only and live-only contacts both occurred, so neither
representation is treated as physical ground truth. See `docs/paper_story.md`
and the 2026-08-05 entry in `docs/연구일지.md` for interpretation boundaries.
