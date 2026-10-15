// Standalone ROS test of the opt-in frontend->map sink; no renderer or FSM.
// Link against native_sector_cpp_component after building mission_planner.
// Run in an isolated ROS_DOMAIN_ID. Temporary JSON evidence is retained.

#include <mission_planner/native_sector_cpp.hpp>

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
  executor.add_node(filter.node);
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
  executor.remove_node(filter.node);
  executor.remove_node(observer);
  filter = {};  // Join the worker before destroying captured sink state.
  std::cout << "PASS direct sink: pointer identity, unchanged payload/stamp, "
               "no crop, stale mode/cycle/untyped rejection, no ROS publisher\n";
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
  rclcpp::init(argc, argv);
  int result = 0;
  try {
    char directory_template[] = "/tmp/native_direct_sink_test_XXXXXX";
    const char *created = ::mkdtemp(directory_template);
    require(created != nullptr, "failed to create test evidence directory");
    const std::string directory(created);
    std::cout << "Evidence directory: " << directory << '\n';
    runDirectTest(directory);
    runLegacyApiTest(directory);
  } catch (const std::exception &error) {
    std::cerr << "FAIL native direct sink: " << error.what() << '\n';
    result = 1;
  }
  rclcpp::shutdown();
  return result;
}
