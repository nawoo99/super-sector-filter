# C15 headless parameter-service preflight

2026-09-16. Implements a common, explicit opt-in for the composed Full and Adaptive executables only. No flight or full simulator build was run by this subtask.

## Change

`SUPER_HEADLESS_PARAMETER_SERVICES=1` sets only these `rclcpp::NodeOptions` fields to false before constructing nodes:

- `start_parameter_services`
- `start_parameter_event_publisher`

Unset, empty, or `0` leaves all supplied options unchanged. Unsupported nonempty strings throw an explicit invalid-argument error. This preserves the default configuration and avoids a mistyped opt-in silently producing a different benchmark configuration.

Full applies the option to its configuration, FSM, and simulator nodes (3). Adaptive applies it to those nodes plus the frontend through its existing inherited NodeOptions (4). Local startup overrides, declaration, get/set, intra-process setting, clock/QoS, subscriptions, publishers other than parameter events, executor groups, and timer periods are untouched. The existing simulator startup `config_name` override is installed after applying the helper.

One `[HEADLESS_PARAMETER_SETTINGS]` startup line inspects `get_node_options()` on every actual constructed node and reports the enabled flag, mode, node count, service-enabled-node count, and parameter-event-publisher-enabled-node count. These are effective **options**, not a runtime DDS discovery assertion. The independent helper test checks actual graph endpoints.

### Deliberate limitation

In opt-in mode the affected nodes no longer provide remote parameter list/get/set RPCs or publish parameter-change events. External `ros2 param` tools and parameter-event observers therefore lose that functionality. Local parameter access continues to work. This is a headless-benchmark configuration, not a claim of completely unchanged external ROS behavior; it stays default off. Do not enable it in profiles requiring remote parameter mutation or parameter-event consumers without a separate review.

## Lightweight ROS test

Runtime source: `mars_uav_sim/perfect_drone_sim/test/headless_parameter_policy_test.cpp`.

Build entry: this directory's `CMakeLists.txt`, a standalone rclcpp helper, not the simulator package build.

Commands:

```bash
source /opt/ros/humble/setup.bash
cmake -S /root/super-sector-filter/results/adaptive_cpu40_20260916/headless_parameter_preflight \
  -B /tmp/super-headless-parameter-test.hc1q0H \
  -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build /tmp/super-headless-parameter-test.hc1q0H --parallel 1
ROS_DOMAIN_ID=198 ROS_LOCALHOST_ONLY=1 timeout 20s \
  /tmp/super-headless-parameter-test.hc1q0H/headless_parameter_policy_test
```

Results: **PASS, 37 checks, exit 0**. First execution passed; no execution retries. `build.log` records the initial compilation, and `build_node_discovery.log` records a pre-execution improvement adding explicit discovery of the headless node before asserting endpoint absence. `ros_helper_run1.log` contains the sole ROS execution.

Verified:

- Exact parser behavior, including rejected nonempty typos.
- Default leaves service/event flags enabled; opt-in disables both; applying the disabled helper does not reset caller-supplied options.
- Local string/integer startup overrides, declare/get/set on both control and headless nodes.
- Intra-process choice, selected clock/event QoS fields, and rosout preserved.
- Both nodes discovered; default control exposes all six parameter services and one parameter-event publisher; headless exposes neither.
- Real remote get RPC succeeds for the control and returns the local-set/overridden values.
- Headless remote parameter services remain unavailable.

No simulator, GPU renderer, mission node, FSM, or planner was instantiated by the test. Runtime/mirror files are identical. The helper and both composed entrypoints are ready for root review and the separately coordinated simulator build; CPU savings are not yet measured.
