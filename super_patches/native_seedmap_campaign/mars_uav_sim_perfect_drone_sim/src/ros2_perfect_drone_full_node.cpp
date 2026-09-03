/**
 * Experimental Full-cloud composition for deterministic benchmark delivery.
 *
 * The renderer hands the complete, unfiltered PointCloud2 SharedPtr directly
 * to ROG-Map's existing latest-only admission queue. This removes only the
 * large DDS serialization/transport boundary; PCL conversion, ray casting,
 * inflation, map commits, planning, and trajectory guarding are unchanged.
 */

#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <ros_interface/ros2/fsm_ros2.hpp>

#define BACKWARD_HAS_DW 1
#include "utils/header/backward.hpp"

#include <rclcpp/rclcpp.hpp>

#include <chrono>
#include <memory>
#include <string>
#include <thread>

namespace backward {
backward::SignalHandling sh;
}

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  pcl::console::setVerbosityLevel(pcl::console::L_ALWAYS);

  rclcpp::NodeOptions intra_process_options;
  intra_process_options.use_intra_process_comms(true);
  auto configuration_node = std::make_shared<rclcpp::Node>(
      "perfect_drone_full_config", intra_process_options);
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
  simulator_options.parameter_overrides(
      {rclcpp::Parameter("config_name", drone_config)});
  auto simulator = std::make_shared<perfect_drone::PerfectDrone>(
      [fsm_ptr](const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
        fsm_ptr->injectMapCloud(cloud_msg);
      },
      false, simulator_options);

  RCLCPP_INFO(configuration_node->get_logger(),
              "Full raw DDS disabled: renderer -> ROG-Map uses direct "
              "latest-only SharedPtr handoff");

  // Marsim's renderer must remain on the main thread. All FSM callbacks,
  // odometry, commands, and the ROG map worker are serviced independently.
  rclcpp::executors::MultiThreadedExecutor side_executor(
      rclcpp::ExecutorOptions(), 10);
  side_executor.add_callback_group(simulator->cmdSubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->odomTimerCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->globalPcPubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_node(fsm_node);
  side_executor.add_node(configuration_node);
  std::thread side_thread([&side_executor]() { side_executor.spin(); });

  rclcpp::executors::SingleThreadedExecutor render_executor;
  render_executor.add_callback_group(simulator->localPcCbkGroup(),
                                     simulator->get_node_base_interface());
  render_executor.spin();

  side_executor.cancel();
  side_thread.join();
  simulator->reportSensorCadence();
  fsm_ptr.reset();
  fsm_node.reset();
  simulator.reset();
  configuration_node.reset();
  rclcpp::shutdown();
  return 0;
}
