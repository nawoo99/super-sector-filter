# C17 cached static-PC executor preflight

2026-09-16. Runtime-first implementation and mirror were explicitly authorized after root and independent source review. This is an executor-class ablation only, not a safety-algorithm or sensor-quality change. The root owns the simulator build and matched flight; this directory contains lightweight real-ROS helper evidence, not a flight result.

## Applied scope

Both composed Full and Adaptive entrypoints use the same opt-in factory. Exactly SUPER_STATIC_PC_CACHED_EXECUTOR=1 selects the installed Humble 16.0.11 StaticSingleThreadedExecutor for the existing dedicated static-PC callback group. Unset, empty, and 0 are off; other nonempty strings fail startup. Opt-in also requires dedicated ownership, legacy 1 ms polling, two-phase OFF, and durable static-PC OFF. The actual executor type is reported via dynamic_cast in STATIC_PC_EXECUTOR_KIND.

The factory preserves base-pointer virtual manual callback-group registration. No simulator model/header, callback body, timer period, bootstrap logic, subscriber-count test, payload, QoS, shared-MTE(2), render executor, or mission code was changed. C17 flight uses the C15 setting base with the C16 frontend-dedicated option OFF. Cached entity collection is a small overhead experiment, not a promise of reaching 40% mean CPU reduction.

Runtime files, with corresponding native_seedmap_campaign mirrors:

- include/perfect_drone_sim/static_pc_cached_executor_policy.hpp
- src/ros2_perfect_drone_full_node.cpp
- src/ros2_perfect_drone_adaptive_node.cpp
- test/static_pc_cached_executor_test.cpp

## Build and first-attempt results

Standalone CMake configuration and compilation both exited 0 on their first attempt. The helper builds against actual installed rclcpp/std_msgs and the runtime header, without PCL, GPU, simulator, mission, or FSM. The binary is outside the repository: /tmp/super-static-cached-test.aMxxaA/static_pc_cached_executor_test. Configuration/build output is preserved in configure_attempt1.log and build_attempt1.log.

Each case was launched separately with ROS_DOMAIN_ID=199, ROS_LOCALHOST_ONLY=1, SUPER_CPU_PROFILE=1 and an outer 20 s timeout. There was no automatic retry. The original ten result logs remain unchanged.

| Case | Ordinary STE | Cached Static STE | Evidence |
| --- | --- | --- | --- |
| routing | PASS, exit 0 | PASS, exit 0 | Actual factory type; strict settings; manual 3-domain ownership; intra-process waitables; duplicate registration rejection; unassigned default group stays unexecuted |
| immediate | PASS, exit 0 | PASS, exit 0 | Never-started destruction and repeated immediate start/stop/join with spin-entry-or-finished handshake |
| invalid | PASS, exit 0 | PASS, exit 0 | Context invalid before worker starts; bounded cleanup |
| shutdown | PASS, exit 0 | PASS, exit 0 | Immediate external shutdown after starting worker; this case alone does not guarantee spin was already entered |
| throw | PASS, exit 0 | PASS, exit 0 | Intentional callback exception detected, context shut down, worker joined |
| live-shutdown (added) | PASS, exit 0 | PASS, exit 0 | Explicitly observed is_spinning and one executed callback before external/main-thread context shutdown; joined with no worker failure |

Both routing arms observed 501 static callbacks during the approximately 500 ms concurrent-executor interval. Static and render callbacks matched their distinct actual worker TIDs; side callbacks stayed out of those domains. Static and side intra-process subscriptions each received their exact expected message. The fixture's 350..700 callback count acceptance is only a gross stall/double-execution check; it does not replace the root's stricter flight timing gate.

The added live-shutdown case was requested after the first ten cases to remove an ambiguity in the original immediate-shutdown case. After the root's simulator build completed, only the test source was updated runtime-first and mirrored; production files were unchanged. build_live_shutdown_attempt1.log records the successful first lightweight rebuild. ordinary_live-shutdown_run1.log and cached_live-shutdown_run1.log preserve both successful first executions, each reporting spinning_before_shutdown=1 and callbacks_before_shutdown=1. The wait for live state is bounded at 2 s in addition to the outer 20 s process timeout.

## Lifecycle limitations and plan adjustment

The production callback groups remain fixed from startup through shutdown. The prospective plan mentioned stopped remove/re-register testing, but this was deliberately not executed or claimed: independent inspection of this installed Humble collector indicated that removal may retain the group's associated-with-executor atomic. Fresh node/group/executor ownership is used for each lifecycle iteration. There is no dynamic group migration in this implementation.

The helper's startup handshake prevents its own cancel-before-spin race. Production legacy side/static thread wrappers and their exception semantics were not rewritten by C17. These tests establish the bounded cases above, not all legacy exception paths or late-reader DDS behavior. Source-level preservation of payload/QoS/body is not a claim that other static-PC delivery defects are repaired.

## Source freeze

After the two added cases, runtime/mirror test comparison succeeded and no helper, compiler, or ROS test process remained. Root was notified to proceed with run9318. Final SHA-256:

~~~text
ba954844a13c9035cb6a0edbda9121d16b760ed95407b140f754a0d045533b93  static_pc_cached_executor_policy.hpp
0e600a1adc4708e5d9919fe7772e12edbbb6480425cb80b19df3d23f07016cb8  static_pc_cached_executor_test.cpp
6c563991cddc11bfe5e81663f48bffdb348da3dd9046c261fcf4b95e91aa3fb2  ros2_perfect_drone_full_node.cpp
a96b787c6634eb4529d6c8fe752fe255af3f8a2f9fb56627fc4bb8f808f473b9  ros2_perfect_drone_adaptive_node.cpp
~~~

The production fingerprints did not change during the post-build test-only addition. The earlier test fingerprint for the original ten cases was b52d30f63f4b6bec132979464bc08890bb0b22ce98fd34153daddf2b7eb98b0f.
