/**
 * Opt-in acquired-source/frontend/planner composition.
 *
 * The source generates only its requested angular window. The frontend checks
 * immutable mode/cycle metadata, publishes any exact Full-refresh request, then
 * hands that same PointCloud2 allocation to ROG-Map's latest-only admission
 * queue. Heavy map updates remain on ROG-Map's existing worker. No cloud DDS
 * publisher is created, and planner/recovery policy is unchanged.
 */

#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"
#include <super_utils/thread_cpu_profile.hpp>

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <mission_planner/native_sector_cpp.hpp>
#include <ros_interface/ros2/fsm_ros2.hpp>

#define BACKWARD_HAS_DW 1
#include "utils/header/backward.hpp"

#include <rclcpp/rclcpp.hpp>

#include <memory>
#include <atomic>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace backward {
backward::SignalHandling sh;
}

namespace {

std::vector<std::string> splitFilterArguments(const std::string &encoded) {
  std::vector<std::string> result;
  std::stringstream stream(encoded);
  std::string item;
  while (std::getline(stream, item, ';')) {
    if (!item.empty()) result.push_back(item);
  }
  return result;
}

}  // namespace

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

  rclcpp::NodeOptions intra_process_options;
  intra_process_options.use_intra_process_comms(true);
  auto configuration_node = std::make_shared<rclcpp::Node>(
      "perfect_drone_adaptive_config", intra_process_options);
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
  configuration_node->declare_parameter("filter_arguments", std::string{});
  const auto drone_config =
      configuration_node->get_parameter("drone_config").as_string();
  const auto super_config =
      configuration_node->get_parameter("super_config").as_string();
  const auto filter_arguments = splitFilterArguments(
      configuration_node->get_parameter("filter_arguments").as_string());
  if (filter_arguments.empty()) {
    RCLCPP_FATAL(configuration_node->get_logger(),
                 "perfect_drone_adaptive requires filter_arguments");
    rclcpp::shutdown();
    return 2;
  }

  auto fsm_node = std::make_shared<rclcpp::Node>(
      "fsm_node", intra_process_options);
  auto fsm_ptr = std::make_shared<fsm::FsmRos2>();
  const std::string super_config_path =
      ament_index_cpp::get_package_share_directory("super_planner") +
      "/config/" + super_config;
  fsm_ptr->init(fsm_node, super_config_path);

  native_sector::DirectInputHandle filter;
  try {
    filter = native_sector::createDirectInputNode(
        filter_arguments, intra_process_options,
        [fsm_ptr](const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
          // injectMapCloud is admission/enqueue only, never a synchronous map
          // update. Exact Full request/ACK topics retain their existing QoS.
          fsm_ptr->injectMapCloud(cloud_msg);
        });
    if (!filter.acquisition_request().enabled) {
      throw std::runtime_error(
          "fully composed source path requires --sensor-acquisition");
    }
  } catch (const std::exception &error) {
    RCLCPP_FATAL(configuration_node->get_logger(),
                 "composed source/front-end init failed: %s", error.what());
    filter = {};
    fsm_ptr.reset();
    fsm_node.reset();
    rclcpp::shutdown();
    return 2;
  }

  rclcpp::NodeOptions simulator_options;
  simulator_options.use_intra_process_comms(true);
  simulator_options.parameter_overrides(
      {rclcpp::Parameter("config_name", drone_config)});
  perfect_drone::AcquisitionProvider acquisition_provider =
      [get = filter.acquisition_request]() {
        const auto r = get();
        return perfect_drone::AcquisitionWindow{
            r.enabled, r.full, r.cycle, r.center_yaw_rad, r.half_angle_deg};
      };
  perfect_drone::AcquiredCloudObserver acquired_observer =
      [submit = filter.submit_acquired_cloud](
          const sensor_msgs::msg::PointCloud2::SharedPtr &cloud,
          const perfect_drone::AcquisitionWindow &r) {
        submit(cloud, {r.enabled, r.full, r.cycle, r.center_yaw_rad,
                       r.half_angle_deg});
      };
  auto simulator = std::make_shared<perfect_drone::PerfectDrone>(
      filter.submit_cloud, false, simulator_options,
      std::move(acquisition_provider), std::move(acquired_observer));

  RCLCPP_INFO(configuration_node->get_logger(),
              "raw and filtered DDS disabled: acquired source -> frontend -> "
              "ROG-Map use SharedPtr handoff; exact Full ACK gate unchanged");

  // Match the Full composition's executor budget. GLFW stays on the main
  // thread, while commands, FSM and frontend callbacks run independently.
  // Frontend and ROG-Map each retain their own bounded latest-only worker.
  rclcpp::executors::MultiThreadedExecutor side_executor(
      rclcpp::ExecutorOptions(), side_executor_threads);
  side_executor.add_callback_group(simulator->cmdSubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->odomTimerCbkGroup(),
                                   simulator->get_node_base_interface());
  std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> static_pc_executor;
  if (dedicated_static_pc_executor) {
    static_pc_executor =
        std::make_unique<rclcpp::executors::SingleThreadedExecutor>();
    static_pc_executor->add_callback_group(simulator->globalPcPubCbkGroup(),
                                           simulator->get_node_base_interface());
  } else {
    side_executor.add_callback_group(simulator->globalPcPubCbkGroup(),
                                     simulator->get_node_base_interface());
  }
  side_executor.add_node(fsm_node);
  side_executor.add_node(filter.node);
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
  // Release the simulator's frontend closures before stopping the frontend
  // worker; its direct sink keeps the map alive until that worker has joined.
  simulator.reset();
  filter = {};
  fsm_ptr.reset();
  fsm_node.reset();
  configuration_node.reset();
  rclcpp::shutdown();
  return static_pc_executor_failed.load(std::memory_order_acquire) ? 1 : 0;
}
