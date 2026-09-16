#include <cstdlib>
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "waypoint_mission/ros2_waypoint_planner.hpp"

#define BACKWARD_HAS_DW 1
#include "utils/backward.hpp"
namespace backward{
    backward::SignalHandling sh;
}

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("waypoint_mission");

    /* Publisher and subscriber */
    bool repeat_identity = false;
    try {
        repeat_identity = mission_planner::goal_retransmit::enabledFromSetting(
                std::getenv("SUPER_GOAL_RETRANSMIT_IDENTITY"));
    } catch (const std::invalid_argument& error) {
        RCLCPP_FATAL(node->get_logger(), "%s", error.what());
        rclcpp::shutdown();
        return 2;
    }
    mission_planner::WaypointPlanner wpl(node, repeat_identity);

    if (repeat_identity) {
        RCLCPP_INFO(node->get_logger(),
                    "[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1 executor=single callbacks_serialized=1 timers_qos_unchanged=1");
        rclcpp::executors::SingleThreadedExecutor executor;
        executor.add_node(node);
        executor.spin();
    } else {
        rclcpp::executors::MultiThreadedExecutor executor;
        executor.add_node(node);
        executor.spin();
    }
    rclcpp::shutdown();
    return 0;
}
