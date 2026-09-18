# Preparation evidence only — no new-map flights

This directory is **not** a simulation result cohort.

- `dry_run01`: initial controller/geometry/hash admission and exact plan check.
  It started zero flights. Subsequent report-validity hardening changes the
  controller hash; this earlier preparation snapshot is retained, not resumed.
- `dry_run02`: final one-command preparation check after that hardening.
  Its `status.json` must say `DRY_RUN_ONLY`, `actual_flights_started: 0`.
- Actual user-launched runs go into their own timestamp/PID folders under
  `results/gapfree_n5_*`, never this preparation folder.

The one-command launcher sources ROS2/current workspace, but `--dry-run` starts
no ROS nodes. Python geometry/contact/controller/report tests use offline or
synthetic fixtures, not observations of Full/Sector/Adaptive flight performance.

Read `docs/gapfree_n5_manual_campaign_20260918.md` before interpreting metrics.
No new-map completion/contact/CPU advantage has been established by this work.

Final offline suite: **67 passed in55.84s** using these runtime test files:

```
test_gen_gapfree_d1_maps.py
test_run_gapfree_n5.py
test_gapfree_campaign_support.py
test_gapfree_loop_monitor.py
test_gapfree_report_validity.py
```

Bash syntax/help and final dry-run passed. Original C25 admission reports1396
files checked, zero changes. No actual campaign was launched by the assistant.
