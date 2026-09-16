#pragma once

#include <rclcpp/rclcpp.hpp>
#include <super_utils/thread_cpu_profile.hpp>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace perfect_drone::frontend_executor_policy {

inline bool enabled(const char* setting) {
  if (!setting || *setting == '\0' || std::strcmp(setting, "0") == 0) return false;
  if (std::strcmp(setting, "1") == 0) return true;
  throw std::invalid_argument("SUPER_FRONTEND_DEDICATED_EXECUTOR must be 0 or 1");
}

// Owns exactly one already-existing frontend node. Construct/start/stop/destroy
// from the composing thread, never from one of this executor's callbacks.
// The node is retained until its callbacks have stopped and the thread joined.
class DedicatedExecutor final {
 public:
  explicit DedicatedExecutor(rclcpp::Node::SharedPtr node)
      : node_(requireNode(std::move(node))), context_(node_->get_node_base_interface()->get_context()),
        executor_(executorOptions(context_)) {
    executor_.add_node(node_);
  }

  DedicatedExecutor(const DedicatedExecutor&) = delete;
  DedicatedExecutor& operator=(const DedicatedExecutor&) = delete;

  ~DedicatedExecutor() { stop(); }

  void start() {
    if (started_) throw std::logic_error("frontend executor already started");
    started_ = true;
    worker_finished_.store(false, std::memory_order_release);
    try {
      thread_ = std::thread([this] {
        try {
          super_utils::thread_cpu_profile::reportThreadRole("frontend_event_executor");
          executor_.spin();
        } catch (const std::exception& error) {
          failWhileRunning(error.what());
        } catch (...) {
          failWhileRunning("unknown exception");
        }
        worker_finished_.store(true, std::memory_order_release);
        lifecycle_cv_.notify_all();
      });
    } catch (...) {
      started_ = false;
      throw;
    }
  }

  void stop() {
    if (!started_) return;
    // cancel() before spin() starts can otherwise be lost. Wait for the actual
    // executor spinning state or a completed worker, with a sleeping handshake
    // (startup/teardown only, no extra ROS timer or callback).
    {
      std::unique_lock<std::mutex> lock(lifecycle_mutex_);
      while (!executor_.is_spinning() &&
             !worker_finished_.load(std::memory_order_acquire)) {
        lifecycle_cv_.wait_for(lock, std::chrono::milliseconds(1));
      }
    }
    try {
      executor_.cancel();
    } catch (const std::exception& error) {
      failWhileRunning(error.what());
    } catch (...) {
      failWhileRunning("unknown cancellation exception");
    }
    if (thread_.joinable()) thread_.join();
    started_ = false;
  }

  bool failed() const noexcept { return failed_.load(std::memory_order_acquire); }

 private:
  static rclcpp::Node::SharedPtr requireNode(rclcpp::Node::SharedPtr node) {
    if (!node) throw std::invalid_argument("frontend executor requires a node");
    return node;
  }

  static rclcpp::ExecutorOptions executorOptions(const rclcpp::Context::SharedPtr& context) {
    rclcpp::ExecutorOptions options;
    options.context = context;
    return options;
  }

  void failWhileRunning(const char* reason) noexcept {
    if (!rclcpp::ok(context_)) return;  // Existing context-invalid shutdown race.
    failed_.store(true, std::memory_order_release);
    try {
      RCLCPP_ERROR(node_->get_logger(), "frontend executor failed: %s", reason);
    } catch (...) {}  // Logging must not escape an executor-thread exception.
    try {
      rclcpp::shutdown(context_, "frontend executor failure");
    } catch (...) {}  // Failure stays observable to the composing thread.
  }

  rclcpp::Node::SharedPtr node_;
  rclcpp::Context::SharedPtr context_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  std::thread thread_;
  std::atomic_bool failed_{false};
  std::atomic_bool worker_finished_{false};
  std::mutex lifecycle_mutex_;
  std::condition_variable lifecycle_cv_;
  bool started_{false};
};

}  // namespace perfect_drone::frontend_executor_policy
