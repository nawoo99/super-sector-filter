# C19 diagnosis and bounded next step

Seed1 n1 per mode: Full .5257245179 cores /20.700615 core-s /37.61s;
Adaptive .3580665708 cores /14.483161 core-s /39.00s. Both complete/contact0,
all audits pass. Relative mean saving31.8908%; cumulative30.0351%. Target40%
is unmet. C18→C19 change is only+0.4403 percentage points, not an isolated or
repeatable improvement. No second lucky-run attempt or unprofiled confirmation.

## Why another scalar tweak is not yet justified

The actual acquired-source Adaptive path already forwards the same SharedPtr.
There is no angular scan, packed payload copy or DDS cloud hop in this path;
raw-risk worker, near-field witness and static probe are disabled. The cloud
worker waits on a condition variable rather than polling. Preserve this design.

Actual final frontend stats:396 cloud/direct-output events,0 worker overwrites,
mean cloud body .0246237373737ms (about9.751ms total elapsed), replan-status134,
map-processing ACK395 and guard-status3. This elapsed measurement includes lock
waiting and is NOT a thread-CPU measurement. It does not cover every callback,
stats serialization, acquisition/enqueue, executor or middleware operation.

At fixed Full mean, another .04263186 Adaptive-only cores must be removed to
reach40%; equal savings in both modes would require .10657965cores. Prior C16
entire dedicated frontend executor consumed .014028cores, including useful
callbacks. Hypothetically deleting all of that projects only34.56% saving at
C19's totals. This is a cross-run sensitivity check, NOT a strict current
ceiling or permission to delete required work.

New raw-counter alignment in `window_alignment/` bounds composed CPU over the
same report window. Its stage-subtracted differences include useful callbacks,
ROS/DDS/profiling cost and scope-completion edge effects. They are not all
avoidable waste. Inferred side-pool thread order must not be used as exact
ownership proof. Existing sampled zero cloud-worker ticks do not prove zero CPU.

## Next implementation: diagnostic attribution before policy changes

1. Append default-off CPU-profile scopes around frontend odometry, replan
   status, map ACK, guard state, acquisition/enqueue and cloud processing, with
   nested writeStats measured exclusively. Keep callback rates and bodies intact.
2. Mark actual map/cloud worker TIDs and both executing pool-worker TIDs. Also
   cover common map-odometry/event callbacks, so shared work is not assigned to
   Adaptive merely because it is currently unnamed.
3. Verify one shared profiler registry across executable/component-library
   boundaries, disabled-path behavior and no double-counting of nested scopes.
4. Run one matched diagnostic Full/Adaptive pair; label it attribution evidence,
   not a new optimized candidate selected for a lucky40% result.
5. Optimize only an established substantial cost, preserving Full/Adaptive
   common treatment and rolling safety/fresh-Full/map-ACK/new-path protocol.

Do not lower10Hz LiDAR or100Hz control/guard rates, widen the source's fixed
45-degree half-angle contract, slow Full, change CPU denominator, omit threads
or launcher/mission CPU, or remove diagnostic evidence just to reach a number.
`perf` is not installed and perf_event_paranoid=4; do not promise stack sampling
without a separate environment decision. Current source is preserved as an
optional C19 implementation; production defaults remain unchanged.

Sources: raw.csv, full_summary.json, adaptive_summary.json,
artifacts/seed1_run9320_adaptive.attempt1.filt_stats.json, thread_cpu_summary.json,
window_alignment/, and the C16 recorded actual frontend thread-role evidence.
