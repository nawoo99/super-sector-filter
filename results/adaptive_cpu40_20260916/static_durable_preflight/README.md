# Static geometry transport: bounded next proposal (NOT APPLIED)

2026-09-16. Source-only design; no compilation, ROS execution, flight, or runtime
change was performed. This is a common Full/Adaptive simulator infrastructure
candidate, not an Adaptive algorithm advantage. Source10Hz, angular acquisition,
odom100Hz, planner/control and safety gates remain untouched.

## Important compatibility limit

Recommended canonical `/global_pc` QoS is **Reliable + TransientLocal + KeepLast1**.
It models a static map retained by its living publisher. Current RViz global-PC
display requests BestEffort/Volatile/KeepLast3 (`rviz2/watch_sector.rviz:117–122`);
the existing test and monitor subscription helper use sensor-data QoS,
BestEffort/Volatile/KeepLast5. Offered reliable/durable QoS can match these weaker
requests, but **matching does not upgrade those readers to reliable delivery or
requested historical replay**. A publisher-only change cannot honestly promise
late delivery to arbitrary unchanged volatile readers.

The CPU campaign's static-PCD collision oracle is loaded from its PCD file; do
not silently replace any rendered live-cloud observation with `/global_pc` or
change collision meanings. `native_loop_monitor.py:290` uses its configurable
cloud topic, not a hardcoded global-PC subscription. Inventory actual readers
from the launch/config before changing their QoS.

Local API evidence (no web needed):

- `rmw/types.h:369–417` documents reliability, bounded history and transient-local.
- `rclcpp/publisher.hpp:185–204` **rejects non-volatile durability with Humble
  intra-process enabled**. Set PublisherOptions intra-process Disable for only
  `/global_pc`; source/direct cloud/odom paths keep their existing settings.
- `rclcpp/qos_event.hpp:58–72` has no publisher matched callback in this Humble.
- `PublisherBase::get_subscription_count()` exposes matched count;
  Node `get_subscriptions_info_by_topic()` supplies endpoint GIDs and QoS;
  graph count alone is not DDS-ready evidence. Count alone misses1→1 replacement.
- `PublisherBase::wait_for_all_acked(0)` is an optional diagnostic only: it is
  not proof an old best-effort reader got the message or application processed it.
  Never wait synchronously in source/odom/control callbacks.

## Practical staged implementation

### A. Prove transport before removing timers

Add a strict default-off `SUPER_STATIC_PC_DURABLE=1` mode. Keep legacy1ms timer,
count-edge sends and5.0–5.1s bootstrap unchanged for this first no-flight probe;
change only global-PC offered QoS and explicitly disable its intra-process path.
Use its existing isolated static executor. Do not combine this flag with the
rejected static100/two-phase flags. Explicit startup marker names effective
reliability, durability, history depth, intra-process and publication policy.

Run the unchanged best-effort-reader full-geometry suite FIRST, preserving any
failure. In separate diagnostic arms, test reliable/transient-local readers.
That separates transport reliability/history effects from a purported timer
optimization. If old volatile late readers still fail, that is a real unresolved
compatibility limit, not grounds for declaring the durable mechanism ineffective.

### B. Cache geometry and use the intended durable contract

Only after A's evidence and separate approval, cache the entire converted
PointCloud2 once (`MarsimRender::getGlobalMap()` currently deep-copies immutable
`cloud_color_mesh`; repeated PCL conversion is unnecessary for fixed maps).
Preserve bytes, field layout, world frame, resolution and all points. Explicitly
reject unsupported changing-global-map profiles; never truncate to fit a cap.
The initial candidate supports a≤64MiB payload, KeepLast1 plus one application
cache. Report actual bytes and RSS; middleware can keep extra serialized copies,
so do not describe this as a universal exact process-memory bound.

Publish/cache once after map initialization. Correct durable/reliable readers
obtain the retained map, including late/reconnected consumers, without1kHz
application polling. Prefer opting the static-map-only RViz display and any
actual static-map-only monitor to reliable/transient-local when that interface
change is authorized; all other topic QoS remains unchanged.

For unchanged legacy volatile readers, retain an explicit compatibility path:
100ms steady-clock polling of matched count + bounded endpoint GID set; publish
one fresh cached sample on newly observed reader identity once any matching
reader exists. A reader replacement at the same count must be detected by GID.
No send is required merely because another reader leaves; the remaining reader
already owns the same immutable map. This changes redundant publication timing,
not geometry. It is **best-effort compatibility**, not a guarantee: aggregate
matched count cannot prove the particular new reader is ready. The prototype
policy here makes that limitation explicit and adds no arbitrary retry burst.

If legacy full-SHA late/reconnect tests still fail, stop promotion. Options are
to keep legacy mode, or explicitly migrate those readers to the durable contract
and separately state that legacy late delivery remains unsupported. Do not
silently make retries unbounded, alter host/network settings, weaken SHA checks,
or claim40% based on startup-ready-only diagnostics. Current root acceptance
requires the existing best-effort-reader suite to pass before broad adoption.

## Ownership, clocks and bounds

- Cached cloud, endpoint set and publication decision have one owner: existing
  dedicated static callback group/executor, never the planning worker.
- Endpoint state bounded to64 GIDs. Overflow or invalid/unknown metadata logs
  unsupported/failure; no unbounded allocation/retry. Maximum decision rate10Hz;
  stable endpoint sets cause no application sends after initialization.
- Wall/steady clock controls polling and fixture deadlines. ROS-time pause,
  rollback or large jump cannot recreate a startup loop or trigger retry storms.
  The static cloud stamp means publication/map creation, not LiDAR acquisition;
  geometry SHA excludes stamp but includes all data/layout. No new scans are
  forged. If retaining cached creation stamp, world→world visualization needs no
  historical moving-frame transform; test any other supported frame explicitly.
- No blocking ACK waits. Reliable `publish()` may incur middleware latency;
  isolate it from source/control, record callback/receipt tails, and retain
  source9.5–10.5Hz and odom/control timing gates in later composed tests.
- Cancelling/joining the static executor precedes destroying publisher/cache.
  Signal direct child once, reap it and require exit0. For ROS launch, signal
  launch parent only first to avoid the previous double-SIGINT fixture mistake.

## Required no-flight matrix and acceptance

Use unused domain190, actual installed simulator and seed1 PCD, no mission,
FSM or command publisher in the first transport-only suite. Use direct binary
execution, not ros2-run child wrappers. A small synthetic cloud is an optional
diagnostic only; it cannot replace the≈7.7MiB actual241490-point payload test.

| Variant | Reader QoS | Sequence | Required evidence |
|---|---|---|---|
| Legacy control | Existing best-effort/volatile | Reader before startup; separate post-bootstrap late arm | Preserve known failure or full SHA; establish exact payload baseline |
| A reliable/durable publisher, legacy schedule | Existing best-effort/volatile | Initial, late0→1, second reader1→2, disconnect/reconnect | Every added reader receives complete identical SHA within5s; clean exit |
| A diagnostic durable readers | Reliable/transient-local | Same matrix, plus join after last app publication | Retained full SHA; record whether new app send occurred |
| B cached/coarse candidate, only if authorized | Existing best-effort/volatile AND durable readers in separate arms | Same matrix plus simultaneous1→1 reader replacement | All required readers pass; bounded publication count, no busy loop |
| B composed no-goal smoke after build | Both Full and Adaptive composition | Existing observers ready then late reconnect | Source10Hz/odom100Hz preserved; no commands/goals injected |

Per phase persist: reader endpoint/QoS, creation and receipt steady times,
message bytes/points/field layout/endian/rowstep/frame, SHA256 of complete data,
publisher endpoint/QoS, matched-count/endpoint-set transition and app publish
counter. Baseline SHA must come from a successful legacy actual-map observation,
not self-comparison alone. Existing callbacks immediately validate every message
and retain partial evidence if a later phase fails. Count-decrease alone need
not force a new map under the new durable contract; full geometry retained by
the surviving reader is the invariant.

Each attempt uses a fresh artifact directory, one predefined sequence and a
hard90s overall/5s per-reader deadline. No auto-retry on failure. Enforce direct
child exit0, no surviving PID, all ROS contexts destroyed, no overwriting of
failed evidence. Only after this matrix and explicit approval may a matched
CPU flight be scheduled. Reliable transport by itself is not a simulation
safety claim or an empirical40% savings result.
