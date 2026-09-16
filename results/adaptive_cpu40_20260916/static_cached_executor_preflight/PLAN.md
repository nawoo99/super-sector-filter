# C17 static-PC executor-class ablation: prospective plan

2026-09-16. Root explicitly authorized this **executor-only scope**, independently of the pending static-PC/RViz QoS decision. C16 was saved as local commit `288d33c`; this document and initial code copies are outside runtime. No implementation application, compiler, ROS process, or flight is authorized by this plan alone; await independent review/root approval.

## Scope

Use the C15 option set, with C16 frontend dedicated executor OFF. For both Full and Adaptive, replace only the existing dedicated static-PC ordinary STE with installed Humble 16.0.11 `StaticSingleThreadedExecutor` when `SUPER_STATIC_PC_CACHED_EXECUTOR=1`.

Unset, empty, or `0` remains off; exactly `1` enables; other nonempty values fail startup. Opt-in requires existing dedicated static executor, legacy 1 ms polling, two-phase OFF, and durable static-PC OFF. Existing renderer/side-MTE(2)/mission executors, thread counts, manual callback group ownership, callback body, bootstrap/subscriber-count behavior, QoS, and payloads are unchanged. No whole-simulator `add_node`, group migration, new timer, sensor/control downsampling, or frontend change.

Factory returns `unique_ptr<rclcpp::Executor>`. The marker computes actual type using `dynamic_cast`, not the requested flag:

```text
[STATIC_PC_EXECUTOR_KIND] cached_entities=1 executor=static_single callbacks_qos_cadence_unchanged=1 mode=full
```

Default dedicated ordinary STE reports `cached_entities=0 executor=single`; absent dedicated executor reports `cached_entities=0 executor=shared`. Existing `sim_static_cloud_executor` actual TID marker remains on the same dedicated thread. Runtime static-PC model/header is not edited.

## Local support and expected effect

Read `../frontend_cpu_preflight/POST_C16_EXECUTOR_OPTIONS_READONLY.md` and installed `/opt/ros/humble/include/rclcpp/rclcpp/executors/static_single_threaded_executor.hpp`. This installed class overrides `add_callback_group` and supports manual split-node groups; that is tested, not inferred from other ROS releases. Cached collector ownership must not execute the simulator's other groups.

C15's static-thread-minus-callback estimate was about .0311 Full / .0300 Adaptive cores. Removing it entirely would only project roughly 33.84% relative saving, and real waiting/timer dispatch costs remain. C16 reached 32.89% but showed no convincing benefit; this new experiment does not stack an assumed C16 saving. This is a small ablation, not a 40% promise.

## Required lightweight real-ROS preflight (both ordinary/cached)

1. Strict flag/combination tests: normal default and valid cached configuration; reject missing dedicated ownership, non-1 ms polling, two-phase=1, durable=1, and nonempty invalid values. When cached off, do not alter existing feature validation.
2. Actual factory dynamic types and marker values, including base-pointer virtual `add_callback_group` dispatch.
3. One real node with two manually assigned MutuallyExclusive groups and an unassigned default group. Static fixture timer uses 1 ms; control group 10 ms. Pump/spin only the static executor and prove other/default callbacks stay unexecuted. Separately run the control executor and prove correct routing. Assert manually added group counts and duplicate group rejection.
4. Include an intra-process subscription/waitable in each group, with publishers configured for intra-process communication. Require the actual intra-process subscription count and exact message delivery to the assigned executor only. This exercises cached waitable collection even though the production static-PC group itself currently contains only the existing timer.
5. Run actual split executors concurrently under an outer timeout; check distinct actual thread IDs and expected callbacks, then cancel/join without cross-execution.
6. Lifecycle: create/destroy without spin; repeated immediate start/stop with a spin-entry/finished handshake; context invalid before start; context shutdown while spinning; callback exception propagation/cleanup. A helper handshake is necessary because cancelling before `spin()` begins can be lost in either class; do not pretend that class substitution fixes arbitrary legacy thread lifecycle issues.
7. Remove/re-register groups only while stopped, preserving node/group lifetime through join. No dynamic entity mutation during the candidate benchmark.

Use no GPU, simulator, mission, or FSM in this helper. Existing simulation entrypoint thread wrappers and startup/shutdown order stay unchanged, apart from the executor's polymorphic type. Helper coverage does not constitute a proof of every inherited side/static exception path.

## Flight acceptance after preflight/root build

Run a fresh matched Full/Adaptive seed1 pair, n=1 each, with C15 settings and frontend dedicated flag OFF. Freeze source/binaries. Require completion/contact-zero, speed/resource, source10 Hz, main/command/odom100 Hz, exact recovery, goal identity, and existing mission-time guards. Add evidence that both modes used actual cached static executor and the legacy 1 ms static callback still executes at the expected ~1000 Hz with no clock errors. Do not accept savings caused by missing callbacks or static delivery changes.

The original static-PC payload/QoS/body remains source-identical; this does not assert that known late-reader legacy DDS issues are repaired. Compare whole-cgroup mean/cumulative CPU and actual static-thread CPU. Do not subtract diagnostics or stack overlapping residuals. Any eligible threshold result still requires matched unprofiled confirmation; preserve failures and do not automatically retry.
