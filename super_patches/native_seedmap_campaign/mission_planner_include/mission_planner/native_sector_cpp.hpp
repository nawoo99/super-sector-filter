#pragma once

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace native_sector {

using GuardCloudObserver = std::function<void(
    const sensor_msgs::msg::PointCloud2::SharedPtr &)>;

// Construct the native filter without owning rclcpp::init/shutdown. This is
// used by the standalone executable and by the experimental in-process FSM
// composition, which share the exact same option parser and implementation.
std::shared_ptr<rclcpp::Node> createNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options = rclcpp::NodeOptions(),
    GuardCloudObserver guard_cloud_observer = {});

} // namespace native_sector
