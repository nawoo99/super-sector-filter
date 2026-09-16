# C20 bounded certificate refresh

**Final status: STOPPED_FOR_DIAGNOSIS.** Runtime fix implemented; the planned
OFF n5 per mode validation is incomplete. ON3 + OFF8 flights all completed with
zero contact, but OFF run9603 Full exceeded the odometry max-gap limit:
header56.987398ms / receipt57.573880ms versus50ms. Seven planned flights were
not attempted. No failed row was discarded/replaced and no threshold relaxed.
`verification.json` is false. This is not an accepted performance candidate.

Runtime change: preserve newer certificates, retry version replacement once
within a cooperative 4 ms refresh-entry budget, preserve real geometry failures
and fail closed. See `docs/c20_certificate_refresh_20260916.md`.

## Evidence layout

- `preservation/pre_c20_sources.tar.gz`: source state before the change.
- `prior_diagnosis/`: historical extracted-function reproduction, before the fix.
  The `.inc` files preserve the old functions; the historical extractor itself
  refers to live source paths and must not be rerun as if they were still old.
- `unit_final/`, `unit_sanitized_final/`: 1,403 assertions each, including 300
  controlled thread interleavings. Geometry and command storage are fixtures;
  these are not flights or full geometry validation.
- `python_tests.log`: 135 Python regression tests.
- `publication_tests.log`, `demand_tests.log`: unchanged policy regression tests.
- `build.log`: serial Release build, 2 packages, 6 min 47 s.
- Top-level `plan.json`, `status.json`, `controller.log`: **initial preflight
  environment failure before any simulator/flight** (missing ROS Python setup).
  Kept intentionally; not the status of the later flight validation.
- `validation/`: corrected-shell, separately preregistered campaign. Its
  `status.json` is the flight execution status. Execution COMPLETE is not a
  performance acceptance verdict.
- `verification.json`: derived safety/source/timing/hash/paired-time gates,
  ON and OFF kept separate. Only final complete coverage can pass.
- `audit_results.py`: regenerates that derived verification, never edits logs.

The planned primary cohort is seed1, OFF, five runs per mode in rotated order.
One ON triplet is only a profiled preflight. No automatic flight retries or
historical pooling. Unfinished slots are not successes. The original CPU40
objective is not redefined by the separate CPU30 engineering check.
