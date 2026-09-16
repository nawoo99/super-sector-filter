// Controlled executor capacity test, NOT a replay of the untraced C20 flight.
// Two overlapping blocking callbacks simulate occupied workers. Timer rate,
// workload, and callback groups are identical in both arms; only workers vary.
#include <rclcpp/rclcpp.hpp>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <thread>
#include <vector>

using namespace std::chrono_literals;
double run(std::size_t workers) {
    auto node = std::make_shared<rclcpp::Node>("worker_reserve_test");
    auto group1 = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto group2 = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto odom_group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    std::atomic<int> started{0}, finished{0};
    rclcpp::TimerBase::SharedPtr heavy1, heavy2;
    auto blocking = [&] {
        ++started;
        const auto deadline = std::chrono::steady_clock::now() + 500ms;
        while (started.load() < 2 && std::chrono::steady_clock::now() < deadline)
            std::this_thread::sleep_for(1ms);
        std::this_thread::sleep_for(100ms);
        ++finished;
    };
    heavy1 = node->create_wall_timer(50ms, [&] { heavy1->cancel(); blocking(); }, group1);
    heavy2 = node->create_wall_timer(50ms, [&] { heavy2->cancel(); blocking(); }, group2);
    std::vector<double> gaps;
    auto previous = std::chrono::steady_clock::time_point{};
    auto odom = node->create_wall_timer(10ms, [&] {
        const auto now = std::chrono::steady_clock::now();
        if (previous.time_since_epoch().count())
            gaps.push_back(std::chrono::duration<double, std::milli>(now - previous).count());
        previous = now;
    }, odom_group);
    rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), workers);
    executor.add_node(node);
    std::thread worker([&] { executor.spin(); });
    std::this_thread::sleep_for(600ms);
    executor.cancel();
    worker.join();
    if (started != 2 || finished != 2 || gaps.empty())
        throw std::runtime_error("test workload not exercised");
    const double maximum = *std::max_element(gaps.begin(), gaps.end());
    std::printf("workers=%zu blocking_callbacks=%d odom_intervals=%zu max_gap_ms=%.6f\n",
                workers, finished.load(), gaps.size(), maximum);
    return maximum;
}
int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    const double two = run(2), three = run(3);
    rclcpp::shutdown();
    if (two < 80. || three >= 50.) return 1;
    std::puts("PASS: reserve worker services odometry during two controlled blocking callbacks; not hard real-time proof");
}
