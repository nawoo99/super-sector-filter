/**
 * Experimental Full-cloud composition for deterministic benchmark delivery.
 *
 * The renderer hands the complete, unfiltered PointCloud2 SharedPtr directly
 * to ROG-Map's existing latest-only admission queue. This removes only the
 * large DDS serialization/transport boundary; PCL conversion, ray casting,
 * inflation, map commits, planning, and trajectory guarding are unchanged.
 */

#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"
#include "perfect_drone_sim/headless_parameter_policy.hpp"
#include "perfect_drone_sim/static_pc_cached_executor_policy.hpp"
#include <super_utils/thread_cpu_profile.hpp>

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <ros_interface/ros2/fsm_ros2.hpp>

#define BACKWARD_HAS_DW 1
#include "utils/header/backward.hpp"

#include <rclcpp/rclcpp.hpp>

#include <chrono>
#include <atomic>
#include <memory>
#include <string>
#include <thread>

namespace backward {
backward::SignalHandling sh;
}

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  pcl::console::setVerbosityLevel(pcl::console::L_ALWAYS);
  const auto side_executor_threads =
      perfect_drone::common_execution_policy::parseSideExecutorThreads(
          std::getenv("SUPER_SIDE_EXECUTOR_THREADS"));
  const char* static_pc_executor_setting =
      std::getenv("SUPER_STATIC_PC_DEDICATED_EXECUTOR");
  const bool dedicated_static_pc_executor = static_pc_executor_setting &&
      std::strcmp(static_pc_executor_setting, "1") == 0;
  const bool cached_static_pc_executor =
      perfect_drone::static_pc_cached_executor_policy::parseEnabled(
          std::getenv("SUPER_STATIC_PC_CACHED_EXECUTOR"),
          dedicated_static_pc_executor,
          perfect_drone::common_execution_policy::parseStaticPcPollMs(
              std::getenv("SUPER_STATIC_PC_POLL_MS")),
          std::getenv("SUPER_STATIC_PC_TWO_PHASE"),
          std::getenv("SUPER_STATIC_PC_DURABLE"));
  const bool headless_parameter_services =
      perfect_drone::headless_parameter_policy::enabled(
          std::getenv("SUPER_HEADLESS_PARAMETER_SERVICES"));

  rclcpp::NodeOptions intra_process_options;
  intra_process_options.use_intra_process_comms(true);
  perfect_drone::headless_parameter_policy::apply(
      intra_process_options, headless_parameter_services);
  auto configuration_node = std::make_shared<rclcpp::Node>(
      "perfect_drone_full_config", intra_process_options);
  RCLCPP_INFO(configuration_node->get_logger(),
              "[COMMON_EXECUTOR_SETTINGS] side_threads=%zu default_threads=10",
              side_executor_threads);
  RCLCPP_INFO(configuration_node->get_logger(),
              "[STATIC_PC_EXECUTOR_SETTINGS] dedicated=%d single_thread=1 "
              "timer_geometry_qos_unchanged=1",
              dedicated_static_pc_executor);
  configuration_node->declare_parameter("drone_config",
                                        std::string{"lidar_sim.yaml"});
  configuration_node->declare_parameter("super_config",
                                        std::string{"click.yaml"});
  const auto drone_config =
      configuration_node->get_parameter("drone_config").as_string();
  const auto super_config =
      configuration_node->get_parameter("super_config").as_string();

  auto fsm_node = std::make_shared<rclcpp::Node>(
      "fsm_node", intra_process_options);
  auto fsm_ptr = std::make_shared<fsm::FsmRos2>();
  const std::string super_config_path =
      ament_index_cpp::get_package_share_directory("super_planner") +
      "/config/" + super_config;
  fsm_ptr->init(fsm_node, super_config_path);

  rclcpp::NodeOptions simulator_options;
  simulator_options.use_intra_process_comms(true);
  perfect_drone::headless_parameter_policy::apply(
      simulator_options, headless_parameter_services);
  simulator_options.parameter_overrides(
      {rclcpp::Parameter("config_name", drone_config)});
  auto simulator = std::make_shared<perfect_drone::PerfectDrone>(
      [fsm_ptr](const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
        fsm_ptr->injectMapCloud(cloud_msg);
      },
      false, simulator_options);
  perfect_drone::headless_parameter_policy::reportEffectiveOptions(
      configuration_node->get_logger(), "full", headless_parameter_services,
      {configuration_node.get(), fsm_node.get(), simulator.get()});

  RCLCPP_INFO(configuration_node->get_logger(),
              "Full raw DDS disabled: renderer -> ROG-Map uses direct "
              "latest-only SharedPtr handoff");

  // Marsim's renderer must remain on the main thread. All FSM callbacks,
  // odometry, commands, and the ROG map worker are serviced independently.
  rclcpp::executors::MultiThreadedExecutor side_executor(
      rclcpp::ExecutorOptions(), side_executor_threads);
  side_executor.add_callback_group(simulator->cmdSubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->odomTimerCbkGroup(),
                                   simulator->get_node_base_interface());
  std::unique_ptr<rclcpp::Executor> static_pc_executor;
  if (dedicated_static_pc_executor) {
    static_pc_executor = perfect_drone::static_pc_cached_executor_policy::make(
        cached_static_pc_executor);
    static_pc_executor->add_callback_group(simulator->globalPcPubCbkGroup(),
                                           simulator->get_node_base_interface());
  } else {
    side_executor.add_callback_group(simulator->globalPcPubCbkGroup(),
                                     simulator->get_node_base_interface());
  }
  perfect_drone::static_pc_cached_executor_policy::reportActualKind(
      configuration_node->get_logger(), static_pc_executor.get(), "full");
  side_executor.add_node(fsm_node);
  side_executor.add_node(configuration_node);
  std::thread side_thread([&side_executor]() { side_executor.spin(); });
  std::thread static_pc_thread;
  std::atomic_bool static_pc_executor_failed{false};
  if (static_pc_executor) {
    static_pc_thread = std::thread([&]() {
      super_utils::thread_cpu_profile::reportThreadRole(
          "sim_static_cloud_executor");
      try {
        static_pc_executor->spin();
      } catch (const std::exception& error) {
        // A signal may invalidate the ROS context between timer dispatch and
        // count_subscribers. Treat only that shutdown race as normal teardown.
        if (rclcpp::ok()) {
          static_pc_executor_failed.store(true, std::memory_order_release);
          RCLCPP_ERROR(configuration_node->get_logger(),
                       "static-PC executor failed: %s", error.what());
          rclcpp::shutdown();
        }
      }
    });
  }

  rclcpp::executors::SingleThreadedExecutor render_executor;
  render_executor.add_callback_group(simulator->localPcCbkGroup(),
                                     simulator->get_node_base_interface());
  super_utils::thread_cpu_profile::reportThreadRole("sim_render_executor");
  render_executor.spin();

  side_executor.cancel();
  if (static_pc_executor) static_pc_executor->cancel();
  side_thread.join();
  if (static_pc_thread.joinable()) static_pc_thread.join();
  simulator->reportSensorCadence();
  fsm_ptr.reset();
  fsm_node.reset();
  simulator.reset();
  configuration_node.reset();
  rclcpp::shutdown();
  return static_pc_executor_failed.load(std::memory_order_acquire) ? 1 : 0;
}
