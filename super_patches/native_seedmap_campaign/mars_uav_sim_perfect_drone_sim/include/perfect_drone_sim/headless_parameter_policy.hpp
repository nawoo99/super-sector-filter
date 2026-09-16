#pragma once

#include <rclcpp/rclcpp.hpp>

#include <cstddef>
#include <cstring>
#include <initializer_list>
#include <stdexcept>

namespace perfect_drone::headless_parameter_policy {

// Benchmark opt-in only. Reject nonempty typos rather than running a different
// benchmark configuration from the requested one.
inline bool enabled(const char* setting) {
  if (!setting || *setting == '\0' || std::strcmp(setting, "0") == 0) return false;
  if (std::strcmp(setting, "1") == 0) return true;
  throw std::invalid_argument("SUPER_HEADLESS_PARAMETER_SERVICES must be 0 or 1");
}

// Local startup overrides, declare/get/set, clock options and every other
// NodeOptions field remain unchanged. Remote parameter RPC/introspection and
// parameter-event publication are intentionally unavailable only when opted in.
inline void apply(rclcpp::NodeOptions& options, const bool headless) {
  if (!headless) return;
  options.start_parameter_services(false);
  options.start_parameter_event_publisher(false);
}

// Observe the options of actual constructed nodes, rather than reporting only
// the requested environment value. One marker covers the entire composition.
inline void reportEffectiveOptions(
    const rclcpp::Logger& logger, const char* mode, const bool headless,
    std::initializer_list<const rclcpp::Node*> nodes) {
  std::size_t service_nodes = 0;
  std::size_t event_publisher_nodes = 0;
  for (const auto* node : nodes) {
    const auto& options = node->get_node_options();
    service_nodes += options.start_parameter_services() ? 1U : 0U;
    event_publisher_nodes += options.start_parameter_event_publisher() ? 1U : 0U;
  }
  RCLCPP_INFO(logger,
      "[HEADLESS_PARAMETER_SETTINGS] enabled=%d mode=%s nodes=%zu "
      "parameter_services_nodes=%zu parameter_event_publisher_nodes=%zu "
      "local_parameters_preserved=1 default_off=1",
      headless, mode, nodes.size(), service_nodes, event_publisher_nodes);
}

}  // namespace perfect_drone::headless_parameter_policy
