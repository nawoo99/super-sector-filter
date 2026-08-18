#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"
#include "rclcpp/rclcpp.hpp"
#include <thread>

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<perfect_drone::PerfectDrone>();

    // The node splits cmd/odom/global_pc/local_pc into separate
    // MutuallyExclusive callback groups, but a plain single-threaded spin
    // still serializes all of them onto one thread. The 1000 Hz global_pc
    // timer and 100 Hz odom timer then starve the local_pc (LiDAR
    // render+publish) callback, so the declared sensing_rate is never
    // actually achieved.
    //
    // The render callback can't simply move to a shared thread pool either:
    // its GLFW/GL context (and glfwPollEvents()) are only valid on the
    // thread that created them, i.e. this one. So cmd/odom/global_pc run on
    // their own multi-threaded executor on a side thread, while local_pc
    // (rendering) keeps this thread to itself via a single-threaded
    // executor holding only that one callback group.
    rclcpp::executors::MultiThreadedExecutor side_executor(rclcpp::ExecutorOptions(), 3);
    side_executor.add_callback_group(node->cmdSubCbkGroup(), node->get_node_base_interface());
    side_executor.add_callback_group(node->odomTimerCbkGroup(), node->get_node_base_interface());
    side_executor.add_callback_group(node->globalPcPubCbkGroup(), node->get_node_base_interface());
    std::thread side_thread([&side_executor]() { side_executor.spin(); });

    rclcpp::executors::SingleThreadedExecutor render_executor;
    render_executor.add_callback_group(node->localPcCbkGroup(), node->get_node_base_interface());
    render_executor.spin();

    side_executor.cancel();
    side_thread.join();
    rclcpp::shutdown();
    return 0;
}
