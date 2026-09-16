// Test-only real RViz display witness. Build outside the repository.
// Usage: probe CONFIG EXPECTED_POINTS EXPECTED_SHA256 SCREENSHOT RESULT_JSON
// Starts no publisher, simulator, planner, mission, or command source.
#include <QApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPixmap>
#include <QRegularExpression>
#include <QTimer>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <rviz_common/display.hpp>
#include <rviz_common/display_group.hpp>
#include <rviz_common/render_panel.hpp>
#include <rviz_rendering/render_window.hpp>
#include <rviz_common/properties/property.hpp>
#include <rviz_common/properties/status_property.hpp>
#include <rviz_common/ros_integration/ros_node_abstraction.hpp>
#include <rviz_common/ros_topic_display.hpp>
#include <rviz_common/visualization_frame.hpp>
#include <rviz_common/visualization_manager.hpp>
#include <chrono>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace {
using Property = rviz_common::properties::Property;
using Status = rviz_common::properties::StatusProperty;
void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}
rviz_common::Display* findGlobal(rviz_common::DisplayGroup* group) {
  for (int i = 0; i < group->numDisplays(); ++i) {
    auto* display = group->getDisplayAt(i);
    if (display->getName() == "GlobalCloud" &&
        display->getClassId() == "rviz_default_plugins/PointCloud2") return display;
    if (auto* child = dynamic_cast<rviz_common::DisplayGroup*>(display))
      if (auto* found = findGlobal(child)) return found;
  }
  return nullptr;
}
void collectStatus(Property* property, QJsonArray& out, bool& points_ok,
                   uint64_t expected_points, bool& error) {
  if (auto* status = dynamic_cast<Status*>(property)) {
    const QString text = status->getValue().toString();
    out.append(QJsonObject{{"name", status->getName()}, {"value", text},
                           {"level", static_cast<int>(status->getLevel())}});
    if (status->getLevel() == Status::Error) error = true;
    if (status->getName() == "Points" && status->getLevel() == Status::Ok) {
      const auto match = QRegularExpression(
          R"(Showing \[(\d+)\] points from \[(\d+)\] messages)").match(text);
      points_ok = match.hasMatch() && match.captured(1).toULongLong() == expected_points &&
                  match.captured(2).toULongLong() >= 1;
    }
  }
  for (int i = 0; i < property->numChildren(); ++i)
    collectStatus(property->childAt(i), out, points_ok, expected_points, error);
}
QString hash(const QByteArray& data) {
  return QCryptographicHash::hash(data, QCryptographicHash::Sha256).toHex();
}
unsigned deferGlobal(rviz_common::Config displays) {
  unsigned count = 0;
  for (int i = 0; i < displays.listLength(); ++i) {
    auto display = displays.listChildAt(i);
    if (display.mapGetChild("Name").getValue().toString() == "GlobalCloud" &&
        display.mapGetChild("Class").getValue().toString() ==
            "rviz_default_plugins/PointCloud2" &&
        display.mapGetChild("Topic").mapGetChild("Value").getValue().toString() == "/global_pc") {
      require(display.mapGetChild("Enabled").getValue().toBool() &&
                  display.mapGetChild("Value").getValue().toBool(),
              "actual profile must enable GlobalCloud");
      display.mapSetValue("Enabled", false);
      display.mapSetValue("Value", false);
      ++count;
    }
    count += deferGlobal(display.mapGetChild("Displays"));
  }
  return count;
}
// Only test subscription startup is deferred. The real PointCloud2 plugin,
// topic, QoS, decay/frame/rendering settings, and on-disk config are unchanged.
class DeferredGlobalFrame final : public rviz_common::VisualizationFrame {
 public:
  using VisualizationFrame::VisualizationFrame;
  void load(const rviz_common::Config& config) override {
    rviz_common::Config deferred;
    deferred.copy(config);
    deferred_displays += deferGlobal(deferred.mapGetChild("Visualization Manager")
                                        .mapGetChild("Displays"));
    VisualizationFrame::load(deferred);
  }
  unsigned deferred_displays{0};
};
}  // namespace

int main(int argc, char** argv) {
  if (argc != 6) {
    std::cerr << "Usage: probe CONFIG EXPECTED_POINTS EXPECTED_SHA256 SCREENSHOT RESULT_JSON\n";
    return 2;
  }
  const QString config = argv[1], screenshot = argv[4], result_path = argv[5];
  const uint64_t expected_points = std::stoull(argv[2]);
  const QString expected_sha = argv[3];
  if (QFile::exists(screenshot) || QFile::exists(result_path)) {
    std::cerr << "Refusing to overwrite RViz evidence\n";
    return 2;
  }
  QJsonObject result{{"valid", false}, {"config", config},
                     {"expected_points", static_cast<double>(expected_points)},
                     {"expected_sha256", expected_sha}, {"extra_map_subscription", false},
                     {"actual_rviz_display", true}};
  int exit_code = 1;
  try {
    QFile input(config);
    require(input.open(QIODevice::ReadOnly), "cannot read actual RViz config");
    result["config_sha256"] = hash(input.readAll());
    rclcpp::init(argc, argv);
    int qt_argc = 1;
    QApplication app(qt_argc, argv);
    auto abstraction = std::make_shared<rviz_common::ros_integration::RosNodeAbstraction>(
        "static_map_rviz_probe");
    auto node = abstraction->get_raw_node();
    {
      DeferredGlobalFrame frame(abstraction);
      frame.setApp(&app);
      frame.setSplashPath("");
      frame.initialize(abstraction, config);
      frame.resize(1280, 900);
      frame.show();
      auto* global = findGlobal(frame.getManager()->getRootDisplayGroup());
      require(global && !global->isEnabled() && frame.deferred_displays == 1,
              "real GlobalCloud subscription was not uniquely deferred before observation");
      result["test_only_subscription_deferred"] = true;
      auto* topic_display = dynamic_cast<rviz_common::_RosTopicDisplay*>(global);
      require(topic_display, "GlobalCloud is not a real ROS topic display");
      auto* topic = global->subProp("Topic");
      require(topic->getValue().toString() == "/global_pc", "wrong static map topic");
      require(topic->subProp("Reliability Policy")->getValue().toString() == "Reliable",
              "RViz reliability not Reliable");
      require(topic->subProp("Durability Policy")->getValue().toString() == "Transient Local",
              "RViz durability not Transient Local");
      require(topic->subProp("History Policy")->getValue().toString() == "Keep Last" &&
                  topic->subProp("Depth")->getValue().toInt() == 1,
              "RViz history/depth not Keep Last 1");
      require(global->subProp("Decay Time")->getValue().toDouble() == 0,
              "RViz static cloud decay changed");
      result["configured_reader_qos"] = QJsonObject{
          {"reliability", "reliable"}, {"durability", "transient_local"},
          {"history", "keep_last"}, {"depth", 1}};
      unsigned received = 0;
      std::string callback_error;
      // Observe the real plugin's own message signal, not a second subscription.
      QObject::connect(topic_display, &rviz_common::_RosTopicDisplay::typeErasedMessageTaken,
                       &frame, [&](std::shared_ptr<const void> erased) {
        try {
          auto message = std::static_pointer_cast<const sensor_msgs::msg::PointCloud2>(erased);
          const uint64_t points = uint64_t(message->width) * message->height;
          require(points == expected_points && message->header.frame_id == "world",
                  "RViz received wrong static point count/frame");
          require(message->point_step > 0 &&
                      message->data.size() == points * message->point_step &&
                      message->data.size() == uint64_t(message->row_step) * message->height,
                  "RViz received malformed geometry");
          require(message->data.size() <= std::numeric_limits<int>::max(), "payload exceeds Qt bound");
          const auto sha = hash(QByteArray(reinterpret_cast<const char*>(message->data.data()),
                                          static_cast<int>(message->data.size())));
          require(sha == expected_sha, "RViz payload differs from legacy point SHA");
          QJsonArray fields;
          for (const auto& field : message->fields)
            fields.append(QJsonObject{{"name", QString::fromStdString(field.name)},
                {"offset", static_cast<int>(field.offset)}, {"datatype", field.datatype},
                {"count", static_cast<int>(field.count)}});
          result["geometry"] = QJsonObject{{"sha256", sha}, {"frame", "world"},
              {"points", static_cast<double>(points)},
              {"stamp_ns", QString::number(int64_t(message->header.stamp.sec) * 1000000000LL +
                                            message->header.stamp.nanosec)},
              {"width", static_cast<int>(message->width)}, {"height", static_cast<int>(message->height)},
              {"point_step", static_cast<int>(message->point_step)},
              {"row_step", static_cast<int>(message->row_step)}, {"fields", fields},
              {"bytes", static_cast<double>(message->data.size())},
              {"is_dense", message->is_dense}, {"is_bigendian", message->is_bigendian}};
          result["rviz_received_messages"] = static_cast<int>(++received);
        } catch (const std::exception& error) {
          callback_error = error.what();
        }
      });
      // The only test /global_pc subscription starts after the observer exists.
      global->setEnabled(true);
      require(global->isEnabled(), "GlobalCloud did not enable after observer installation");
      const auto started = std::chrono::steady_clock::now();
      auto valid_since = started;
      bool was_valid = false;
      QTimer poll;
      QObject::connect(&poll, &QTimer::timeout, &frame, [&] {
        try {
          require(callback_error.empty(), callback_error.c_str());
          require(rclcpp::ok(), "ROS context shutdown while checking RViz");
          QJsonArray statuses;
          bool points_ok = false, status_error = false;
          collectStatus(global, statuses, points_ok, expected_points, status_error);
          result["display_statuses"] = statuses;
          bool graph_qos_ok = false;
          unsigned own_endpoints = 0;
          for (const auto& endpoint : node->get_subscriptions_info_by_topic("/global_pc")) {
            if (endpoint.node_name() != node->get_name()) continue;
            ++own_endpoints;
            const auto qos = endpoint.qos_profile().get_rmw_qos_profile();
            graph_qos_ok = qos.reliability == RMW_QOS_POLICY_RELIABILITY_RELIABLE &&
                           qos.durability == RMW_QOS_POLICY_DURABILITY_TRANSIENT_LOCAL;
            const bool history_known = qos.history != RMW_QOS_POLICY_HISTORY_UNKNOWN &&
                                       qos.history != RMW_QOS_POLICY_HISTORY_SYSTEM_DEFAULT;
            const bool depth_known = qos.depth > 0;
            if (history_known) require(qos.history == RMW_QOS_POLICY_HISTORY_KEEP_LAST,
                                       "RViz graph known history mismatch");
            if (depth_known) require(qos.depth == 1, "RViz graph known depth mismatch");
            result["requested_qos_graph"] = QJsonObject{
                {"reliability", static_cast<int>(qos.reliability)},
                {"durability", static_cast<int>(qos.durability)},
                {"history", static_cast<int>(qos.history)}, {"depth", static_cast<double>(qos.depth)},
                {"history_known", history_known}, {"depth_known", depth_known}};
          }
          require(received <= 1, "RViz received more than one retained static sample");
          const bool ready = received == 1 && points_ok && !status_error &&
                             own_endpoints == 1 && graph_qos_ok;
          const auto now = std::chrono::steady_clock::now();
          if (ready && !was_valid) { was_valid = true; valid_since = now; }
          if (!ready) was_valid = false;
          if (ready && now - valid_since >= std::chrono::seconds(1)) {
            // QWidget::grab omits the embedded Ogre QWindow and produces an
            // empty central pane. Capture the real render target instead.
            frame.getManager()->getRenderPanel()->getRenderWindow()->captureScreenShot(
                screenshot.toStdString());
            require(QFile::exists(screenshot), "could not save RViz render target");
            result["screenshot_method"] = "rviz_render_window_capture";
            result["screenshot"] = screenshot;
            result["valid"] = true;
            result["own_global_pc_endpoints"] = static_cast<int>(own_endpoints);
            exit_code = 0;
            app.quit();
          } else if (now - started > std::chrono::seconds(20)) {
            throw std::runtime_error("timeout awaiting real RViz geometry/status/QoS");
          }
        } catch (const std::exception& error) {
          result["error"] = error.what();
          app.quit();
        }
      });
      poll.start(100);
      app.exec();
      poll.stop();
      frame.getManager()->stopUpdate();
    }
    rclcpp::shutdown();
  } catch (const std::exception& error) {
    result["error"] = error.what();
    if (rclcpp::ok()) rclcpp::shutdown();
  }
  QFile output(result_path);
  if (!output.open(QIODevice::WriteOnly | QIODevice::NewOnly)) {
    std::cerr << "Could not write new result file\n";
    return 2;
  }
  output.write(QJsonDocument(result).toJson(QJsonDocument::Indented));
  std::cout << "RVIZ_STATIC_MAP valid=" << (exit_code == 0)
            << " result=" << result_path.toStdString() << '\n';
  return exit_code;
}
