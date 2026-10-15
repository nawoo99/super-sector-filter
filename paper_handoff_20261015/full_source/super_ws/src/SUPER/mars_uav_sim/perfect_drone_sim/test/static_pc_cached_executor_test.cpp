#include <perfect_drone_sim/static_pc_cached_executor_policy.hpp>
#include <super_utils/thread_cpu_profile.hpp>
#include <std_msgs/msg/u_int64.hpp>

#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>
#include <unistd.h>
#include <sys/syscall.h>

namespace policy = perfect_drone::static_pc_cached_executor_policy;
using namespace std::chrono_literals;

namespace {
void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}
long tid() { return ::syscall(SYS_gettid); }
template<class Function> void rejected(Function&& function) {
  bool threw = false;
  try { function(); } catch (const std::exception&) { threw = true; }
  require(threw, "expected rejection");
}

// Test-only owner: the sleeping spin-entry handshake prevents a lost
// cancel-before-spin in either class. Production thread wrappers are unchanged.
class SpinThread {
 public:
  SpinThread(rclcpp::Executor& executor, const char* role) : executor_(executor) {
    thread_ = std::thread([this, role] {
      actual_tid_ = tid();
      try {
        super_utils::thread_cpu_profile::reportThreadRole(role);
        executor_.spin();
      } catch (...) {
        if (rclcpp::ok()) {
          failed_ = true;
          try { rclcpp::shutdown(); } catch (...) {}
        }
      }
      finished_ = true;
    });
  }
  ~SpinThread() { stop(); }
  void stop() {
    if (!thread_.joinable()) return;
    while (!executor_.is_spinning() && !finished_)
      std::this_thread::sleep_for(1ms);
    try { executor_.cancel(); }
    catch (...) { if (rclcpp::ok()) failed_ = true; }
    thread_.join();
  }
  long actualTid() const { return actual_tid_; }
  bool failed() const { return failed_; }
 private:
  rclcpp::Executor& executor_;
  std::thread thread_;
  std::atomic_bool finished_{false}, failed_{false};
  std::atomic<long> actual_tid_{0};
};

void parserTest() {
  for (const auto* setting : {static_cast<const char*>(nullptr), "", "0"})
    require(!policy::parseEnabled(setting, false, 100, "1", "1"), "off altered legacy behavior");
  require(policy::parseEnabled("1", true, 1, "0", "0"), "valid opt-in rejected");
  require(policy::parseEnabled("1", true, 1, nullptr, nullptr), "unset other flags rejected");
  for (const auto* value : {"true", "01", " 1", "1 ", "2"})
    rejected([&] { policy::parseEnabled(value, true, 1, "0", "0"); });
  rejected([] { policy::parseEnabled("1", false, 1, "0", "0"); });
  rejected([] { policy::parseEnabled("1", true, 100, "0", "0"); });
  rejected([] { policy::parseEnabled("1", true, 1, "1", "0"); });
  rejected([] { policy::parseEnabled("1", true, 1, "0", "1"); });
  rejected([] { policy::parseEnabled("1", true, 1, "bad", "0"); });
  rejected([] { policy::parseEnabled("1", true, 1, "0", "bad"); });
}

void pump(rclcpp::Executor& executor, std::chrono::milliseconds duration) {
  const auto until = std::chrono::steady_clock::now() + duration;
  do { executor.spin_some(); std::this_thread::sleep_for(1ms); }
  while (std::chrono::steady_clock::now() < until);
}

void routingTest(bool cached) {
  rclcpp::NodeOptions options;
  options.use_intra_process_comms(true).start_parameter_services(false)
      .start_parameter_event_publisher(false);
  auto node = std::make_shared<rclcpp::Node>("static_cached_group_fixture", options);
  // Match simulator's default auto-add setting. No executor gets add_node().
  auto static_group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  auto odom_group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  auto cmd_group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  auto render_group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  std::atomic<unsigned> static_calls{0}, odom_calls{0}, cmd_calls{0}, render_calls{0}, default_calls{0};
  std::atomic<unsigned> static_messages{0}, side_messages{0};
  std::atomic<long> static_last_tid{0}, render_last_tid{0};
  std::mutex side_tid_mutex;
  std::set<long> side_tids;
  const auto record_side = [&] {
    std::lock_guard<std::mutex> lock(side_tid_mutex);
    side_tids.insert(tid());
  };
  auto static_timer = node->create_wall_timer(1ms, [&] {
    ++static_calls; static_last_tid = tid();
  }, static_group);
  auto odom_timer = node->create_wall_timer(10ms, [&] { ++odom_calls; record_side(); }, odom_group);
  auto cmd_timer = node->create_wall_timer(10ms, [&] { ++cmd_calls; record_side(); }, cmd_group);
  auto render_timer = node->create_wall_timer(100ms, [&] {
    ++render_calls; render_last_tid = tid();
  }, render_group);
  auto unassigned_timer = node->create_wall_timer(1ms, [&] { ++default_calls; });
  rclcpp::SubscriptionOptions static_sub_options, side_sub_options;
  static_sub_options.callback_group = static_group;
  side_sub_options.callback_group = cmd_group;
  auto static_sub = node->create_subscription<std_msgs::msg::UInt64>(
      "/cached_fixture/static", rclcpp::QoS(10),
      [&](std_msgs::msg::UInt64::ConstSharedPtr message) {
        if (message->data == 1701) ++static_messages;
      }, static_sub_options);
  auto side_sub = node->create_subscription<std_msgs::msg::UInt64>(
      "/cached_fixture/side", rclcpp::QoS(10),
      [&](std_msgs::msg::UInt64::ConstSharedPtr message) {
        if (message->data == 1702) ++side_messages;
      }, side_sub_options);
  auto static_pub = node->create_publisher<std_msgs::msg::UInt64>("/cached_fixture/static", rclcpp::QoS(10));
  auto side_pub = node->create_publisher<std_msgs::msg::UInt64>("/cached_fixture/side", rclcpp::QoS(10));
  require(static_pub->get_intra_process_subscription_count() == 1 &&
              side_pub->get_intra_process_subscription_count() == 1,
          "actual intra-process subscriptions not established");
  auto static_executor = policy::make(cached);
  require((dynamic_cast<rclcpp::executors::StaticSingleThreadedExecutor*>(static_executor.get()) != nullptr) == cached,
          "factory concrete type mismatch");
  rclcpp::executors::MultiThreadedExecutor side_executor(rclcpp::ExecutorOptions(), 2);
  rclcpp::executors::SingleThreadedExecutor render_executor;
  static_executor->add_callback_group(static_group, node->get_node_base_interface());
  side_executor.add_callback_group(odom_group, node->get_node_base_interface());
  side_executor.add_callback_group(cmd_group, node->get_node_base_interface());
  render_executor.add_callback_group(render_group, node->get_node_base_interface());
  require(static_executor->get_manually_added_callback_groups().size() == 1,
          "static executor acquired additional groups");
  require(side_executor.get_manually_added_callback_groups().size() == 2,
          "side executor manual split mismatch");
  rejected([&] { render_executor.add_callback_group(static_group, node->get_node_base_interface()); });
  policy::reportActualKind(node->get_logger(), static_executor.get(), "fixture");
  auto static_message = std::make_unique<std_msgs::msg::UInt64>();
  static_message->data = 1701; static_pub->publish(std::move(static_message));
  auto side_message = std::make_unique<std_msgs::msg::UInt64>();
  side_message->data = 1702; side_pub->publish(std::move(side_message));
  pump(*static_executor, 120ms);
  require(static_calls > 50 && static_messages == 1, "static timer or IPC waitable did not run");
  require(odom_calls == 0 && cmd_calls == 0 && render_calls == 0 && default_calls == 0 && side_messages == 0,
          "static collector stole another simulator group");
  const auto static_before_side = static_calls.load();
  pump(side_executor, 120ms);
  require(odom_calls > 0 && cmd_calls > 0 && side_messages == 1, "side timer or IPC did not run");
  require(static_calls == static_before_side && render_calls == 0 && default_calls == 0,
          "side executor stole another group");
  pump(render_executor, 120ms);
  require(render_calls > 0 && default_calls == 0, "render/default group routing incorrect");
  {
    std::lock_guard<std::mutex> lock(side_tid_mutex);
    side_tids.clear();
  }
  const auto static_before = static_calls.load();
  SpinThread static_thread(*static_executor, "sim_static_cloud_executor");
  SpinThread side_thread(side_executor, "c17_side_fixture_entry");
  SpinThread render_thread(render_executor, "c17_render_fixture");
  std::this_thread::sleep_for(500ms);
  static_thread.stop(); side_thread.stop(); render_thread.stop();
  require(!static_thread.failed() && !side_thread.failed() && !render_thread.failed(), "split executor failed");
  require(default_calls == 0, "unassigned default group ran during concurrent split");
  require(static_last_tid == static_thread.actualTid() && render_last_tid == render_thread.actualTid(),
          "callback identity crossed static/render domains");
  {
    std::lock_guard<std::mutex> lock(side_tid_mutex);
    require(!side_tids.empty() && !side_tids.count(static_thread.actualTid()) &&
                !side_tids.count(render_thread.actualTid()), "side callback crossed executor domain");
  }
  const auto static_delta = static_calls.load() - static_before;
  require(static_delta >= 350 && static_delta <= 700, "1 ms timer grossly stalled/doubled in fixture");
  std::cout << "PASS manual3domain cached=" << cached << " static_delta_500ms=" << static_delta
            << " static_tid=" << static_thread.actualTid() << " render_tid=" << render_thread.actualTid()
            << " ipc_static=" << static_messages << " ipc_side=" << side_messages << '\n';
}

void lifecycleTest(bool cached, const std::string& test_case) {
  if (test_case == "immediate") {
    for (unsigned i = 0; i < 24; ++i) {
      auto node = std::make_shared<rclcpp::Node>("cached_lifecycle_" + std::to_string(i));
      auto group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
      auto timer = node->create_wall_timer(1ms, [] {}, group);
      auto executor = policy::make(cached);
      executor->add_callback_group(group, node->get_node_base_interface());
      if (i == 0) continue;
      SpinThread worker(*executor, "sim_static_cloud_executor");
      worker.stop();
      require(!worker.failed(), "immediate start/stop failed");
    }
  } else {
    auto node = std::make_shared<rclcpp::Node>("cached_lifecycle");
    auto group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    std::atomic<unsigned> callbacks{0};
    auto timer = node->create_wall_timer(5ms, [&] {
      ++callbacks;
      if (test_case == "throw") throw std::runtime_error("intentional callback exception");
    }, group);
    auto executor = policy::make(cached);
    executor->add_callback_group(group, node->get_node_base_interface());
    if (test_case == "invalid") rclcpp::shutdown();
    SpinThread worker(*executor, "sim_static_cloud_executor");
    if (test_case == "shutdown") rclcpp::shutdown();
    if (test_case == "live-shutdown") {
      const auto until = std::chrono::steady_clock::now() + 2s;
      while (rclcpp::ok() && std::chrono::steady_clock::now() < until &&
             (!executor->is_spinning() || callbacks.load() == 0))
        std::this_thread::sleep_for(1ms);
      require(executor->is_spinning() && callbacks.load() > 0,
              "live shutdown never observed spinning callback");
      std::cout << "LIVE_SHUTDOWN spinning_before_shutdown=1 callbacks_before_shutdown="
                << callbacks.load() << '\n';
      rclcpp::shutdown();
    }
    if (test_case == "throw") {
      const auto until = std::chrono::steady_clock::now() + 2s;
      while (rclcpp::ok() && std::chrono::steady_clock::now() < until)
        std::this_thread::sleep_for(1ms);
    }
    worker.stop();
    require(worker.failed() == (test_case == "throw"), "wrong lifecycle failure state");
    if (test_case == "throw") require(!rclcpp::ok(), "failure did not shut down context");
  }
  std::cout << "PASS lifecycle cached=" << cached << " case=" << test_case << '\n';
}
}  // namespace

int main(int argc, char** argv) {
  const bool cached = argc > 1 && std::string(argv[1]) == "cached";
  const std::string test_case = argc > 2 ? argv[2] : "routing";
  rclcpp::init(argc, argv);
  try {
    parserTest();
    if (test_case == "routing") routingTest(cached);
    else lifecycleTest(cached, test_case);
    rclcpp::shutdown();
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL cached=" << cached << " case=" << test_case << " error=" << error.what() << '\n';
    rclcpp::shutdown();
    return 1;
  }
}
