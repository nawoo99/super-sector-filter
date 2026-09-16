#pragma once

#include <rclcpp/rclcpp.hpp>
#include <rclcpp/executors/static_single_threaded_executor.hpp>

#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>

namespace perfect_drone::static_pc_cached_executor_policy {

inline bool exactEnabled(const char* setting, const char* name) {
  if (!setting || *setting == '\0' || std::strcmp(setting, "0") == 0) return false;
  if (std::strcmp(setting, "1") == 0) return true;
  throw std::invalid_argument(std::string(name) + " must be 0 or 1");
}

inline bool parseEnabled(const char* setting, const bool dedicated,
                         const int poll_ms, const char* two_phase,
                         const char* durable) {
  const bool cached = exactEnabled(setting, "SUPER_STATIC_PC_CACHED_EXECUTOR");
  if (!cached) return false;  // Preserve all legacy validation/behavior when off.
  if (!dedicated || poll_ms != 1 ||
      exactEnabled(two_phase, "SUPER_STATIC_PC_TWO_PHASE") ||
      exactEnabled(durable, "SUPER_STATIC_PC_DURABLE")) {
    throw std::invalid_argument(
        "SUPER_STATIC_PC_CACHED_EXECUTOR=1 requires dedicated static executor, "
        "legacy 1 ms polling, two-phase OFF, and durable static-PC OFF");
  }
  return true;
}

// Change only executor class. Callers retain the exact existing manual group,
// node ownership, thread, timers, publication callback, and QoS.
inline std::unique_ptr<rclcpp::Executor> make(
    const bool cached, const rclcpp::ExecutorOptions& options = rclcpp::ExecutorOptions()) {
  if (cached)
    return std::make_unique<rclcpp::executors::StaticSingleThreadedExecutor>(options);
  return std::make_unique<rclcpp::executors::SingleThreadedExecutor>(options);
}

inline void reportActualKind(const rclcpp::Logger& logger,
                             const rclcpp::Executor* executor, const char* mode) {
  const bool cached = dynamic_cast<
      const rclcpp::executors::StaticSingleThreadedExecutor*>(executor) != nullptr;
  const bool ordinary = dynamic_cast<
      const rclcpp::executors::SingleThreadedExecutor*>(executor) != nullptr;
  if (executor && !cached && !ordinary)
    throw std::logic_error("unsupported dedicated static-PC executor type");
  RCLCPP_INFO(logger,
      "[STATIC_PC_EXECUTOR_KIND] cached_entities=%d executor=%s "
      "callbacks_qos_cadence_unchanged=1 mode=%s",
      cached, cached ? "static_single" : (ordinary ? "single" : "shared"), mode);
}

}  // namespace perfect_drone::static_pc_cached_executor_policy
