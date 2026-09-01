/**
 * Experimental in-process composition of SUPER and the native sector filter.
 * Filtered PointCloud2 messages stay inside rclcpp's intra-process manager;
 * Adaptive also hands the already-received raw SharedPtr directly to the FSM,
 * so the simulator raw cloud is the only DDS cloud input.
 */

#include <mission_planner/native_sector_cpp.hpp>
#include <ros_interface/ros2/fsm_ros2.hpp>

#define BACKWARD_HAS_DW 1
#include "utils/header/backward.hpp"

#include <rclcpp/rclcpp.hpp>

#include <chrono>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
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
    if (!item.empty())
      result.push_back(item);
  }
  return result;
}

} // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  pcl::console::setVerbosityLevel(pcl::console::L_ALWAYS);

  rclcpp::NodeOptions intra_process_options;
  intra_process_options.use_intra_process_comms(true);
  auto node = std::make_shared<rclcpp::Node>(
      "fsm_node", intra_process_options);

  while (rclcpp::ok()) {
    bool use_sim_time;
    if (node->get_parameter("use_sim_time", use_sim_time)) {
      if (!use_sim_time) {
        std::cout << " -- [Bench] Use sim time is false, begin replay."
                  << std::endl;
        break;
      }
      node->set_parameter(rclcpp::Parameter("use_sim_time", false));
    } else {
      node->set_parameter(rclcpp::Parameter("use_sim_time", false));
    }
    std::this_thread::sleep_for(std::chrono::seconds(1));
  }

#define CONFIG_FILE_DIR(name)                                                 \
  (std::string(std::string(ROOT_DIR) + "config/" + (name)))
  std::string cfg_path = "click.yaml";
  node->declare_parameter("config_name", cfg_path);
  node->get_parameter("config_name", cfg_path);

  std::string encoded_filter_arguments;
  node->declare_parameter("filter_arguments", encoded_filter_arguments);
  node->get_parameter("filter_arguments", encoded_filter_arguments);
  const auto filter_arguments = splitFilterArguments(encoded_filter_arguments);
  if (filter_arguments.empty()) {
    RCLCPP_FATAL(node->get_logger(),
                 "fsm_node_with_sector requires filter_arguments");
    rclcpp::shutdown();
    return 2;
  }

  auto fsm_ptr = std::make_shared<fsm::FsmRos2>();
  const bool inject_raw_guard_cloud = filter_arguments.front() == "adaptive";
  if (inject_raw_guard_cloud)
    fsm_ptr->enableInProcessGuardCloudInjection();
  fsm_ptr->init(node, CONFIG_FILE_DIR(cfg_path));

  std::shared_ptr<rclcpp::Node> filter_node;
  try {
    native_sector::GuardCloudObserver guard_observer;
    if (inject_raw_guard_cloud) {
      guard_observer = [fsm_ptr](
          const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
        fsm_ptr->injectGuardCloud(cloud_msg);
      };
    }
    filter_node = native_sector::createNode(
        filter_arguments, intra_process_options, std::move(guard_observer));
  } catch (const std::exception &error) {
    RCLCPP_FATAL(node->get_logger(), "native sector init failed: %s",
                 error.what());
    rclcpp::shutdown();
    return 2;
  }
  RCLCPP_INFO(node->get_logger(),
              "\033[32m -- [Fsm-Test] Begin with intra-process native "
              "sector filter.\033[0m");

  rclcpp::executors::MultiThreadedExecutor executor(
      rclcpp::ExecutorOptions(), 8);
  executor.add_node(filter_node);
  executor.add_node(node);
  executor.spin();

  executor.remove_node(node);
  executor.remove_node(filter_node);
  fsm_ptr.reset();
  filter_node.reset();
  node.reset();
  rclcpp::shutdown();
  return 0;
}
