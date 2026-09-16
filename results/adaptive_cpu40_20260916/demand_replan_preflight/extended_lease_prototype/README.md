# Extended lease review artifact (not applied)

`extended_lease_runtime_proposal.patch` changes only the policy header, its
FsmRos2 hookup, and a new standalone test. The complete proposed files are in
this folder for review. They are not loaded by the experiment.

`git apply --check` passes against the current runtime. This is a context check,
not a build or safety test. No extension test was compiled/executed during C10
or C11 flights. Do not apply until root authorizes after the active flight.

## Control and instrumentation

- Main feature remains `SUPER_GUARDED_DEMAND_REPLAN=1`.
- Additional exact `SUPER_GUARDED_DEMAND_EXTENDED_LEASE=1` selects 500 ms.
- Unset/malformed/non-1 extension values preserve 250 ms; extension by itself
  never enables the main policy. All other evidence, timers and horizons remain
  unchanged. No CPU profiler enum, stage binding or accounting is modified.
- Default startup marker and existing `[DEMAND_REPLAN]` line keep their current
  text/value contract. Extended mode reports `max_dispatch_interval=0.5`.
- New `[DEMAND_REPLAN_REASONS]` reports cumulative **final** outcomes after any
  renewal, only at the existing approximately 5 s reporting point. Nineteen
  unchanged contiguous Reason values span DISABLED=0 through SKIP=18. The array
  uses size SKIP+1, and each name comes from the existing reasonName function.
- A replan-callback-owned plain integer increment is the only per-check histogram
  work. String formatting/allocation happens only on reporting. Its CPU remains
  inside the existing FsmReplanCallback profile; it is not subtracted or hidden.
- `counted == checks` and `final_counts.SKIP == skips` should hold on each paired
  report. These counts do not cover timer entries returned before the demand
  checker, and the final <5 s flight tail may be absent from logs.

## Proposed tests

The new test includes the unchanged default regression under a renamed entry
point, so the original 41 gates/21 nonfinite cases still run. It then repeats all
40 non-deadline rejection cases with the extended policy and adds explicit
parser/bounds/deadline/backup/receipt/cadence/histogram tests.

After the flight freeze is lifted, the prototype can be tested without touching
runtime:

```sh
cd /root/super-sector-filter/results/adaptive_cpu40_20260916/demand_replan_preflight/extended_lease_prototype
g++ -std=c++17 -O2 -Wall -Wextra -pedantic extended_dispatch_lease_test.cpp -o /tmp/extended_dispatch_lease_test
/tmp/extended_dispatch_lease_test
g++ -std=c++17 -O1 -g0 -Wall -Wextra -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer extended_dispatch_lease_test.cpp -o /tmp/extended_dispatch_lease_test_sanitize
/tmp/extended_dispatch_lease_test_sanitize
```

After authorized runtime application, the same new test includes the actual
existing runtime `demand_replan_policy_test.cpp`; compile with the package source
include path. This test is standalone, not added to CMake in the proposal.

The proposed histogram diagnoses deadline versus horizon limits; it does not
prove logical safety or explain every lost lease. Real callback/guard cadence,
actual dispatch gaps, own-commit attribution, map renewal coherence and Full ACK
ordering still need the matched flight audit described in the parent design note.
