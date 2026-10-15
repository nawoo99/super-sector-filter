// Standalone ROS test of the opt-in frontend->map sink; no renderer or FSM.
// Link against native_sector_cpp_component after building mission_planner.
// Run in an isolated ROS_DOMAIN_ID. Temporary JSON evidence is retained.

#include <mission_planner/native_sector_cpp.hpp>
#include <perfect_drone_sim/frontend_executor_policy.hpp>
#include <perfect_drone_sim/headless_parameter_policy.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/u_int64_multi_array.hpp>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/msg/point_field.hpp>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <memory>
#include <mutex>
#include <regex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
using Cloud = sensor_msgs::msg::PointCloud2;
namespace executor_policy = perfect_drone::frontend_executor_policy;
bool dedicated_mode = true;

// Control ownership is the real two-worker executor, not a fake callback pump.
// This harness measures protocol/lifecycle only, not CPU performance.
class SharedFrontendHarness {
 public:
  explicit SharedFrontendHarness(rclcpp::Node::SharedPtr node)
      : node_(std::move(node)), executor_(rclcpp::ExecutorOptions(), 2) {
    executor_.add_node(node_);
    thread_ = std::thread([this] {
      try { executor_.spin(); }
      catch (...) { failed_ = true; try { rclcpp::shutdown(); } catch (...) {} }
      finished_ = true;
    });
  }
  ~SharedFrontendHarness() {
    while (!executor_.is_spinning() && !finished_)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    try { executor_.cancel(); } catch (...) {}
    if (thread_.joinable()) thread_.join();
  }
  bool failed() const { return failed_; }
 private:
  rclcpp::Node::SharedPtr node_;
  rclcpp::executors::MultiThreadedExecutor executor_;
  std::thread thread_;
  std::atomic_bool finished_{false}, failed_{false};
};

void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}

bool pumpUntil(rclcpp::executors::SingleThreadedExecutor &executor,
               const std::function<bool()> &predicate,
               std::chrono::milliseconds timeout = std::chrono::seconds(4)) {
  const auto deadline = std::chrono::steady_clock::now() + timeout;
  while (rclcpp::ok() && std::chrono::steady_clock::now() < deadline) {
    executor.spin_some();
    if (predicate()) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  executor.spin_some();
  return predicate();
}

bool jsonCounterAtLeast(const std::string &path, const std::string &key,
                        unsigned long long minimum) {
  std::ifstream input(path);
  const std::string contents((std::istreambuf_iterator<char>(input)),
                              std::istreambuf_iterator<char>());
  std::smatch match;
  if (!std::regex_search(contents, match,
                        std::regex("\"" + key + "\"\\s*:\\s*([0-9]+)")))
    return false;
  return std::stoull(match[1].str()) >= minimum;
}

Cloud::SharedPtr fixtureCloud() {
  auto message = std::make_shared<Cloud>();
  message->header.frame_id = "world";
  message->header.stamp.sec = 123;
  message->header.stamp.nanosec = 456789;
  message->width = 3;
  message->height = 1;
  message->point_step = 32;
  message->row_step = message->width * message->point_step;
  message->is_dense = true;
  for (unsigned i = 0; i < 3; ++i) {
    sensor_msgs::msg::PointField field;
    field.name = std::string(1, "xyz"[i]);
    field.offset = i * sizeof(float);
    field.datatype = sensor_msgs::msg::PointField::FLOAT32;
    field.count = 1;
    message->fields.push_back(field);
  }
  message->data.assign(message->row_step, 0x5a);
  // Deliberately include coordinates outside +/-45deg. This is a frontend
  // transport fixture, not a physically valid Sector render: the test proves
  // the trusted source payload is NOT subjected to a second angular crop.
  const float xyz[3][3] = {{1.0f, 0.0f, 0.0f},
                            {-1.0f, 0.0f, 0.0f},
                            {0.0f, 1.0f, 0.0f}};
  for (unsigned i = 0; i < 3; ++i)
    std::memcpy(message->data.data() + i * message->point_step,
                xyz[i], sizeof(xyz[i]));
  return message;
}

std::vector<std::string> argumentsFor(const std::string &output_topic,
                                      const std::string &stats_path) {
  return {"sector", "45", "--sensor-acquisition", "--no-replan-guard",
          "--near-field-radius-m", "0", "--output-topic", output_topic,
          "--stats-json", stats_path};
}

void runDirectTest(const std::string &directory) {
  const std::string topic = "/native_direct_sink_test/acquired_cloud";
  const std::string stats_path = directory + "/direct_stats.json";
  std::mutex received_mutex;
  std::vector<Cloud::SharedPtr> received;
  rclcpp::NodeOptions options;
  options.use_intra_process_comms(true);
  perfect_drone::headless_parameter_policy::apply(options, true);
  auto filter = native_sector::createDirectInputNode(
      argumentsFor(topic, stats_path), options,
      [&](const Cloud::SharedPtr &cloud) {
        std::lock_guard<std::mutex> lock(received_mutex);
        received.push_back(cloud);
      });
  auto observer = std::make_shared<rclcpp::Node>("direct_sink_test_observer");
  std::atomic<unsigned> dds_deliveries{0};
  auto subscription = observer->create_subscription<Cloud>(
      topic, rclcpp::QoS(1).best_effort(),
      [&](Cloud::ConstSharedPtr) { ++dds_deliveries; });
  rclcpp::executors::SingleThreadedExecutor executor;
  std::unique_ptr<executor_policy::DedicatedExecutor> dedicated;
  std::unique_ptr<SharedFrontendHarness> shared;
  if (dedicated_mode) {
    dedicated = std::make_unique<executor_policy::DedicatedExecutor>(filter.node);
    dedicated->start();
  } else {
    shared = std::make_unique<SharedFrontendHarness>(filter.node);
  }
  executor.add_node(observer);
  const auto receivedCount = [&]() {
    std::lock_guard<std::mutex> lock(received_mutex);
    return received.size();
  };

  const auto acquisition = filter.acquisition_request();
  require(acquisition.enabled && !acquisition.full && acquisition.cycle == 0 &&
              acquisition.half_angle_deg == 45.0,
          "fixed Sector acquisition request changed");
  auto cloud = fixtureCloud();
  const auto original_bytes = cloud->data;
  filter.submit_acquired_cloud(cloud, acquisition);
  require(pumpUntil(executor, [&]() { return receivedCount() == 1; }),
          "valid typed acquisition did not reach sink");
  {
    std::lock_guard<std::mutex> lock(received_mutex);
    require(received.front().get() == cloud.get(), "SharedPtr identity lost");
    require(received.front()->data == original_bytes &&
                received.front()->width == 3 &&
                received.front()->point_step == 32,
            "source payload cropped/repacked/modified");
    require(received.front()->header.stamp == cloud->header.stamp,
            "exact acquisition timestamp changed");
  }

  // Wait for explicit processed-drop counters, not merely absence of a sink
  // callback; a latest-only overwrite must not falsely satisfy these tests.
  auto stale_mode = acquisition;
  stale_mode.full = true;
  filter.submit_acquired_cloud(fixtureCloud(), stale_mode);
  require(pumpUntil(executor, [&]() {
    return jsonCounterAtLeast(stats_path, "sensor_acquisition_stale_drops", 1);
  }), "wrong Full/Sector metadata was not explicitly rejected");
  require(receivedCount() == 1, "stale mode leaked into map sink");

  auto stale_cycle = acquisition;
  ++stale_cycle.cycle;
  filter.submit_acquired_cloud(fixtureCloud(), stale_cycle);
  require(pumpUntil(executor, [&]() {
    return jsonCounterAtLeast(stats_path, "sensor_acquisition_stale_drops", 2);
  }), "wrong recovery cycle was not explicitly rejected");
  require(receivedCount() == 1, "stale cycle leaked into map sink");

  filter.submit_cloud(fixtureCloud());  // No immutable acquisition metadata.
  require(pumpUntil(executor, [&]() {
    return jsonCounterAtLeast(stats_path, "sensor_acquisition_stale_drops", 3);
  }), "untyped source cloud was not explicitly rejected");
  require(receivedCount() == 1, "untyped source cloud leaked into map sink");

  auto second = fixtureCloud();
  ++second->header.stamp.nanosec;
  filter.submit_acquired_cloud(second, acquisition);
  require(pumpUntil(executor, [&]() { return receivedCount() == 2; }),
          "sink did not resume after rejecting invalid acquisitions");
  require(pumpUntil(executor, [&]() {
    return jsonCounterAtLeast(stats_path, "direct_output_events", 2);
  }), "direct output accounting missing");
  require(observer->count_publishers(topic) == 0,
          "direct-sink mode created a ROS cloud publisher");
  require(dds_deliveries.load() == 0,
          "direct-sink mode duplicated a cloud through ROS");
  if (dedicated) {
    dedicated->stop();
    require(!dedicated->failed(), "dedicated frontend executor failed");
    dedicated.reset();
  } else {
    require(!shared->failed(), "shared control executor failed");
    shared.reset();
  }
  executor.remove_node(observer);
  filter = {};  // Join the worker before destroying captured sink state.
  std::cout << "PASS direct sink: pointer identity, unchanged payload/stamp, "
               "no crop, stale mode/cycle/untyped rejection, no ROS publisher\n";
}

// Reuses the real direct-input component and the two arrival-order cases in
// scripts/native_campaign/test_event_recovery_transport.py. No fake planner
// certificate is claimed: guard false is a synthetic protocol release only.
void runEventTest(const std::string& directory) {
  auto observer = std::make_shared<rclcpp::Node>("dedicated_event_observer");
  const auto latched = rclcpp::QoS(16).reliable().transient_local();
  const auto reliable = rclcpp::QoS(16).reliable();
  auto guard = observer->create_publisher<std_msgs::msg::Bool>(
      "/planning/trajectory_guard_recovery_active", latched);
  auto ack = observer->create_publisher<std_msgs::msg::UInt64MultiArray>(
      "/rog_map/cloud_process_ack", reliable);
  std::vector<std::uint64_t> request;
  auto request_sub = observer->create_subscription<std_msgs::msg::UInt64MultiArray>(
      "/sector/full_refresh_request", latched,
      [&](std_msgs::msg::UInt64MultiArray::ConstSharedPtr message) {
        if (message->data.size() >= 3 && message->data[0] > 0) request = message->data;
      });
  std::atomic<unsigned> delivered{0};
  rclcpp::NodeOptions options;
  options.use_intra_process_comms(true);
  perfect_drone::headless_parameter_policy::apply(options, true);
  auto filter = native_sector::createDirectInputNode(
      {"adaptive", "45", "--sensor-acquisition", "--event-recovery",
       "--full-refresh-generation-ack", "--near-field-radius-m", "0",
       "--stats-json", directory + "/event_stats.json"}, options,
      [&](const Cloud::SharedPtr&) { ++delivered; });
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(observer);
  std::unique_ptr<executor_policy::DedicatedExecutor> dedicated;
  std::unique_ptr<SharedFrontendHarness> shared;
  if (dedicated_mode) {
    dedicated = std::make_unique<executor_policy::DedicatedExecutor>(filter.node);
    dedicated->start();
  } else {
    shared = std::make_unique<SharedFrontendHarness>(filter.node);
  }
  require(pumpUntil(executor, [&] {
    return guard->get_subscription_count() > 0 && ack->get_subscription_count() > 0 &&
           request_sub->get_publisher_count() > 0;
  }), "event endpoints not discovered");
  require(!filter.acquisition_request().full, "event mode did not start Sector");
  for (unsigned cycle = 1; cycle <= 2; ++cycle) {
    std_msgs::msg::Bool state;
    state.data = true;
    guard->publish(state);
    require(pumpUntil(executor, [&] {
      const auto window = filter.acquisition_request();
      return window.full && window.cycle == cycle;
    }), "guard did not produce a new Full cycle");
    request.clear();
    auto cloud = fixtureCloud();
    cloud->header.stamp = observer->now();
    const auto before = delivered.load();
    filter.submit_acquired_cloud(cloud, filter.acquisition_request());
    require(pumpUntil(executor, [&] { return !request.empty() && delivered > before; }),
            "fresh Full frame did not produce exact request and sink delivery");
    const auto stamp = static_cast<std::uint64_t>(cloud->header.stamp.sec) * 1000000000ULL +
                       cloud->header.stamp.nanosec;
    require(request[1] == stamp, "Full request changed source stamp");
    const auto publish_ack = [&](std::uint64_t source, std::uint64_t version, bool committed) {
      std_msgs::msg::UInt64MultiArray message;
      message.data = {cycle, source, version, committed ? 1ULL : 0ULL};
      ack->publish(message);
    };
    publish_ack(stamp + 1, 42, true);
    publish_ack(stamp, 0, true);
    publish_ack(stamp, 42, false);
    const auto still_full = [&] { return filter.acquisition_request().full; };
    if (cycle == 1) {
      state.data = false;
      guard->publish(state);
      require(pumpUntil(executor, [&] {
        return jsonCounterAtLeast(directory + "/event_stats.json", "trajectory_guard_status_count", 2);
      }), "close callback not observed");
      require(still_full(), "invalid ACK or close-only released Full");
      publish_ack(stamp, 42, true);
    } else {
      publish_ack(stamp, 43, true);
      require(pumpUntil(executor, [&] {
        return jsonCounterAtLeast(directory + "/event_stats.json", "event_recovery_commit_acks", 2);
      }), "matching committed ACK not processed");
      require(still_full(), "ACK-only released Full without planner close");
      state.data = false;
      guard->publish(state);
    }
    require(pumpUntil(executor, [&] { return !filter.acquisition_request().full; }),
            "exact ACK plus release did not converge to Sector");
  }
  if (dedicated) {
    dedicated->stop();
    require(!dedicated->failed(), "dedicated event executor failed");
    dedicated.reset();
  } else {
    require(!shared->failed(), "shared event control executor failed");
    shared.reset();
  }
  executor.remove_node(observer);
  filter = {};
  std::cout << "PASS real component recovery: fresh exact Full request, invalid ACK holds, "
               "close-before-ACK and ACK-before-close; dedicated=" << dedicated_mode << '\n';
}

void runLifecycleTest(const std::string& kind) {
  require(!executor_policy::enabled(nullptr) && !executor_policy::enabled("0") &&
              executor_policy::enabled("1"), "flag parser");
  for (const auto* text : {"true", "01", "1 ", "2"}) {
    bool threw = false;
    try { (void)executor_policy::enabled(text); }
    catch (const std::invalid_argument&) { threw = true; }
    require(threw, "invalid flag accepted");
  }
  bool null_rejected = false;
  try { executor_policy::DedicatedExecutor invalid(nullptr); }
  catch (const std::invalid_argument&) { null_rejected = true; }
  require(null_rejected, "null node accepted");
  auto node = std::make_shared<rclcpp::Node>("frontend_lifecycle_test");
  if (kind == "lifecycle") {
    { executor_policy::DedicatedExecutor never_started(node); }
    rclcpp::executors::SingleThreadedExecutor other;
    other.add_node(node);
    bool duplicate_rejected = false;
    try { executor_policy::DedicatedExecutor duplicate(node); }
    catch (const std::exception&) { duplicate_rejected = true; }
    require(duplicate_rejected, "node admitted to two executors");
    other.remove_node(node);
    for (unsigned attempt = 0; attempt < 32; ++attempt) {
      executor_policy::DedicatedExecutor executor(node);
      executor.start();
      executor.stop();  // Deliberately no sleep: exercises cancel-before-spin race.
      require(!executor.failed(), "immediate stop incorrectly failed");
    }
  } else if (kind == "invalid-context") {
    executor_policy::DedicatedExecutor executor(node);
    rclcpp::shutdown();
    executor.start();
    executor.stop();
    require(!executor.failed(), "invalid startup context treated as application failure");
  } else if (kind == "context-shutdown") {
    executor_policy::DedicatedExecutor executor(node);
    executor.start();
    rclcpp::shutdown();
    executor.stop();
    require(!executor.failed(), "ordinary context shutdown treated as application failure");
  } else if (kind == "callback-throw") {
    auto timer = node->create_wall_timer(std::chrono::milliseconds(5), [] {
      throw std::runtime_error("intentional lifecycle test exception");
    });
    executor_policy::DedicatedExecutor executor(node);
    executor.start();
    const auto until = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (rclcpp::ok() && std::chrono::steady_clock::now() < until)
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
    executor.stop();
    require(executor.failed() && !rclcpp::ok(), "callback exception did not fail and shut down context");
  } else {
    throw std::invalid_argument("unknown lifecycle case");
  }
  std::cout << "PASS lifecycle case=" << kind << '\n';
}

void runLegacyApiTest(const std::string &directory) {
  const std::string topic = "/native_direct_sink_test/legacy_cloud";
  // Explicit two-argument call exercises the preserved component ABI.
  auto filter = native_sector::createDirectInputNode(
      argumentsFor(topic, directory + "/legacy_stats.json"),
      rclcpp::NodeOptions());
  auto observer = std::make_shared<rclcpp::Node>("legacy_sink_test_observer");
  std::atomic<unsigned> deliveries{0};
  auto subscription = observer->create_subscription<Cloud>(
      topic, rclcpp::QoS(1).best_effort(),
      [&](Cloud::ConstSharedPtr cloud) {
        if (cloud->width == 3 && cloud->data == fixtureCloud()->data)
          ++deliveries;
      });
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(filter.node);
  executor.add_node(observer);
  require(pumpUntil(executor, [&]() {
    return observer->count_publishers(topic) == 1 &&
           filter.node->count_subscribers(topic) == 1;
  }), "legacy two-argument API lost its ROS cloud publisher");
  filter.submit_acquired_cloud(fixtureCloud(), filter.acquisition_request());
  require(pumpUntil(executor, [&]() { return deliveries.load() == 1; }),
          "legacy ROS cloud delivery changed");
  executor.remove_node(filter.node);
  executor.remove_node(observer);
  filter = {};
  std::cout << "PASS legacy two-argument API: ROS cloud delivery preserved\n";
}
}  // namespace

int main(int argc, char **argv) {
  const std::string mode = argc > 1 ? argv[1] : "dedicated";
  rclcpp::init(argc, argv);
  int result = 0;
  try {
    if (mode != "dedicated" && mode != "shared") {
      runLifecycleTest(mode);
      rclcpp::shutdown();
      return 0;
    }
    dedicated_mode = mode == "dedicated";
    char directory_template[] = "/tmp/frontend_executor_test_XXXXXX";
    const char *created = ::mkdtemp(directory_template);
    require(created != nullptr, "failed to create test evidence directory");
    const std::string directory(created);
    std::cout << "Evidence directory: " << directory << '\n';
    runDirectTest(directory);
    runEventTest(directory);
  } catch (const std::exception &error) {
    std::cerr << "FAIL native direct sink: " << error.what() << '\n';
    result = 1;
  }
  rclcpp::shutdown();
  return result;
}
