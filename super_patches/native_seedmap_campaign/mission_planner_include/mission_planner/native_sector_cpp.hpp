#pragma once

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <mission_planner/sensor_acquisition.hpp>

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace native_sector {

using GuardCloudObserver = std::function<void(
    const sensor_msgs::msg::PointCloud2::SharedPtr &)>;

// Optional enqueue-only map handoff for the experimental fully composed
// source/frontend/planner executable. The sink must not modify the message or
// perform map updates synchronously on the frontend worker.
using FilteredCloudSink = std::function<void(
    const sensor_msgs::msg::PointCloud2::SharedPtr &)>;

struct DirectInputHandle {
  std::shared_ptr<rclcpp::Node> node;
  std::function<void(const sensor_msgs::msg::PointCloud2::SharedPtr &)>
      submit_cloud;
  std::function<SensorAcquisition()> acquisition_request;
  std::function<void(const sensor_msgs::msg::PointCloud2::SharedPtr &,
                     const SensorAcquisition &)> submit_acquired_cloud;
};

// Construct the native filter without owning rclcpp::init/shutdown. This is
// used by the standalone executable and by the experimental in-process FSM
// composition, which share the exact same option parser and implementation.
std::shared_ptr<rclcpp::Node> createNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options = rclcpp::NodeOptions(),
    GuardCloudObserver guard_cloud_observer = {});

// Construct the filter as an actual sensor front-end: no raw-cloud ROS
// subscription is created, and the simulator submits its freshly rendered
// SharedPtr through submit_cloud. Only the filtered output and optional
// compact risk verdict leave the process through DDS by default. Supplying a
// sink bypasses the cloud publisher, but leaves metadata checks, accounting,
// and the exact Full-refresh request/commit protocol unchanged.
DirectInputHandle createDirectInputNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options = rclcpp::NodeOptions());

// Separate overload preserves the existing two-argument component symbol for
// previously built legacy/replay binaries.
DirectInputHandle createDirectInputNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options,
    FilteredCloudSink filtered_cloud_sink);

} // namespace native_sector
