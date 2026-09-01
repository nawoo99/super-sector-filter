/**
 * Experimental sensor-front-end composition for filtered SUPER campaigns.
 *
 * The renderer hands its freshly allocated PointCloud2 SharedPtr directly to
 * the native filter. The process deliberately creates no /cloud_registered
 * publisher. Only /cloud_sector plus the optional compact trajectory-risk
 * verdict cross a DDS boundary.
 */

#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"

#include <mission_planner/native_sector_cpp.hpp>
#include <rclcpp/rclcpp.hpp>

#include <chrono>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace {

std::vector<std::string> splitFilterArguments(const std::string &encoded) {
  std::vector<std::string> result;
  std::stringstream stream(encoded);
  std::string item;
  while (std::getline(stream, item, ';')) {
    if (!item.empty())
      result.push_back(item);
  }
  return result;
}

} // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);

  rclcpp::NodeOptions intra_process_options;
  intra_process_options.use_intra_process_comms(true);
  auto configuration_node = std::make_shared<rclcpp::Node>(
      "perfect_drone_frontend_config", intra_process_options);
  const std::string default_config{"lidar_sim.yaml"};
  const std::string default_filter_arguments;
  configuration_node->declare_parameter("config_name", default_config);
  configuration_node->declare_parameter("filter_arguments",
                                        default_filter_arguments);
  const std::string config_name =
      configuration_node->get_parameter("config_name").as_string();
  const auto filter_arguments = splitFilterArguments(
      configuration_node->get_parameter("filter_arguments").as_string());
  if (filter_arguments.empty()) {
    RCLCPP_FATAL(configuration_node->get_logger(),
                 "perfect_drone_frontend requires filter_arguments");
    rclcpp::shutdown();
    return 2;
  }

  native_sector::DirectInputHandle filter;
  try {
    filter = native_sector::createDirectInputNode(
        filter_arguments, intra_process_options);
  } catch (const std::exception &error) {
    RCLCPP_FATAL(configuration_node->get_logger(),
                 "native sensor front-end init failed: %s", error.what());
    rclcpp::shutdown();
    return 2;
  }

  rclcpp::NodeOptions simulator_options;
  simulator_options.use_intra_process_comms(true);
  simulator_options.parameter_overrides(
      {rclcpp::Parameter("config_name", config_name)});
  auto simulator = std::make_shared<perfect_drone::PerfectDrone>(
      filter.submit_cloud, false, simulator_options);

  RCLCPP_INFO(configuration_node->get_logger(),
              "raw DDS disabled: renderer -> native front-end uses direct "
              "SharedPtr handoff");

  // Preserve the renderer's GLFW thread-affinity requirement. All non-render
  // simulator groups and the filter's subscriptions use a side executor;
  // raw filtering and risk work remain on their own bounded worker threads.
  rclcpp::executors::MultiThreadedExecutor side_executor(
      rclcpp::ExecutorOptions(), 5);
  side_executor.add_callback_group(simulator->cmdSubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->odomTimerCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_callback_group(simulator->globalPcPubCbkGroup(),
                                   simulator->get_node_base_interface());
  side_executor.add_node(filter.node);
  side_executor.add_node(configuration_node);
  std::thread side_thread([&side_executor]() { side_executor.spin(); });

  rclcpp::executors::SingleThreadedExecutor render_executor;
  render_executor.add_callback_group(simulator->localPcCbkGroup(),
                                     simulator->get_node_base_interface());
  render_executor.spin();

  side_executor.cancel();
  side_thread.join();
  simulator->reportSensorCadence();
  filter.node.reset();
  simulator.reset();
  configuration_node.reset();
  rclcpp::shutdown();
  return 0;
}
