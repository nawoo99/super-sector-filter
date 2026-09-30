# Legacy ablation only

This directory was run with the body-forward-only legacy Fixed Sector:

- `SUPER_SECTOR_ACTIVE_YAW_SCAN=0`
- `SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT=0`
- runtime `ACTIVE_YAW_SCAN` contract records: zero

It must not be used as the canonical Sector result after the project decision
that `Sector` means **Sector (Active-Yaw)**.  The raw files remain immutable and
useful only as a legacy fixed-view ablation and failure-reconstruction cohort.

Canonical replacement campaign:

`results/urban_active_yaw_default_no_mission_timeout_n10_20260930/`
