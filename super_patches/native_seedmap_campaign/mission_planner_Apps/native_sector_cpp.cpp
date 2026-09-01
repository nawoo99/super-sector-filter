#include <rclcpp/rclcpp.hpp>
#include <rclcpp/serialization.hpp>

#include <mission_planner/native_sector_cpp.hpp>

#include <nav_msgs/msg/odometry.hpp>
#include <mars_quadrotor_msgs/msg/polynomial_trajectory.hpp>
#include <mars_quadrotor_msgs/msg/trajectory_risk_verdict.hpp>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/msg/point_field.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/u_int64.hpp>
#include <std_msgs/msg/u_int64_multi_array.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <fstream>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

constexpr double kPi = 3.14159265358979323846;

struct Options {
  std::string mode{"sector"};
  double half_angle_deg{60.0};
  std::string input_topic{"/cloud_registered"};
  std::string output_topic{"/cloud_sector"};
  bool reliable_output{false};
  double max_publish_hz{0.0};
  std::string map_commit_topic{"/rog_map/commit_version"};
  double map_commit_refresh_age_s{0.12};
  double map_commit_refresh_min_interval_s{0.10};
  double map_commit_pre_stale_full_age_s{0.0};
  double map_commit_pre_stale_ack_retry_age_s{0.0};
  std::string map_process_ack_topic{"/rog_map/cloud_process_ack"};
  std::string full_refresh_request_topic{"/sector/full_refresh_request"};
  bool full_refresh_generation_ack_en{false};
  uint64_t full_open_extra_max_points{6000};
  bool track_trap{false};
  bool sector_until_trap{false};
  double trap_intensity{12012.0};
  std::string event_json;
  std::string stats_json;
  double stall_v{0.6};
  double stall_t{1.2};
  double resume_v{1.5};
  double resume_t{2.0};
  double slowdown_full_refresh_v{0.0};
  double slowdown_full_refresh_rearm_v{0.0};
  int replan_fail_streak_open{5};
  int replan_ok_streak_close{15};
  bool replan_guard_en{true};
  bool bounded_replan_guard{false};
  std::optional<double> replan_open_burst_s;
  std::optional<double> replan_open_cooldown_s;
  double near_field_radius_m{1.5};
  double near_field_speed_gain_s{0.0};
  std::optional<double> near_field_max_radius_m;
  std::string guard_witness_topic;
  double guard_witness_radius_m{0.0};
  double open_burst_s{0.0};
  double open_cooldown_s{0.0};
  std::string trajectory_guard_topic{
      "/planning/trajectory_guard_recovery_active"};
  double trajectory_guard_hold_s{2.5};
  double trajectory_guard_active_max_publish_hz{0.0};
  double trajectory_guard_ack_retry_age_s{0.0};
  bool test_drop_first_trajectory_guard_full_cloud{false};
  bool direct_input{false};
  std::string risk_verdict_topic;
  std::string risk_trajectory_topic{"/planning_cmd/poly_traj"};
  double risk_accum_window_s{1.5};
  double risk_clearance_m{0.20};
  double risk_horizon_s{1.0};
  double risk_sample_dt_s{0.01};
  int risk_min_points{200};
  double risk_voxel_m{0.0};
  double risk_max_cloud_age_s{0.75};
  double risk_max_eval_hz{0.0};
  double risk_egress_tolerance_m{0.005};
  double risk_egress_min_progress_m{0.02};
};

double parseDouble(const std::string &name, const char *value) {
  try {
    size_t used = 0;
    const double parsed = std::stod(value, &used);
    if (used != std::strlen(value) || !std::isfinite(parsed)) {
      throw std::invalid_argument("trailing or non-finite value");
    }
    return parsed;
  } catch (const std::exception &) {
    throw std::runtime_error(name + " expects a finite number, got '" + value +
                             "'");
  }
}

int parseInt(const std::string &name, const char *value) {
  try {
    size_t used = 0;
    const long parsed = std::stol(value, &used);
    if (used != std::strlen(value) || parsed < 0 ||
        parsed > std::numeric_limits<int>::max()) {
      throw std::invalid_argument("out of range");
    }
    return static_cast<int>(parsed);
  } catch (const std::exception &) {
    throw std::runtime_error(name + " expects a non-negative integer, got '" +
                             value + "'");
  }
}

Options parseArgs(int argc, char **argv) {
  Options options;
  int positional = 0;
  auto requireValue = [&](int &index, const std::string &name) -> const char * {
    if (++index >= argc) {
      throw std::runtime_error(name + " requires a value");
    }
    return argv[index];
  };

  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (!arg.empty() && arg.front() != '-') {
      if (positional == 0) {
        options.mode = arg;
      } else if (positional == 1) {
        options.half_angle_deg = parseDouble("half_angle_deg", argv[i]);
      } else {
        throw std::runtime_error("unexpected positional argument '" + arg +
                                 "'");
      }
      ++positional;
    } else if (arg == "--input-topic") {
      options.input_topic = requireValue(i, arg);
    } else if (arg == "--output-topic") {
      options.output_topic = requireValue(i, arg);
    } else if (arg == "--reliable-output") {
      options.reliable_output = true;
    } else if (arg == "--max-publish-hz") {
      options.max_publish_hz = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--map-commit-topic") {
      options.map_commit_topic = requireValue(i, arg);
    } else if (arg == "--map-commit-refresh-age-s") {
      options.map_commit_refresh_age_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--map-commit-refresh-min-interval-s") {
      options.map_commit_refresh_min_interval_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--map-commit-pre-stale-full-age-s") {
      options.map_commit_pre_stale_full_age_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--map-commit-pre-stale-ack-retry-age-s") {
      options.map_commit_pre_stale_ack_retry_age_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--map-process-ack-topic") {
      options.map_process_ack_topic = requireValue(i, arg);
    } else if (arg == "--full-refresh-request-topic") {
      options.full_refresh_request_topic = requireValue(i, arg);
    } else if (arg == "--full-refresh-generation-ack") {
      options.full_refresh_generation_ack_en = true;
    } else if (arg == "--full-open-extra-max-points") {
      options.full_open_extra_max_points = static_cast<uint64_t>(
          parseInt(arg, requireValue(i, arg)));
    } else if (arg == "--track-trap") {
      options.track_trap = true;
    } else if (arg == "--sector-until-trap") {
      options.sector_until_trap = true;
    } else if (arg == "--trap-intensity") {
      options.trap_intensity = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--event-json") {
      options.event_json = requireValue(i, arg);
    } else if (arg == "--stats-json") {
      options.stats_json = requireValue(i, arg);
    } else if (arg == "--stall-v") {
      options.stall_v = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--stall-t") {
      options.stall_t = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--resume-v") {
      options.resume_v = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--resume-t") {
      options.resume_t = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--slowdown-full-refresh-v") {
      options.slowdown_full_refresh_v =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--slowdown-full-refresh-rearm-v") {
      options.slowdown_full_refresh_rearm_v =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--replan-fail-streak-open") {
      options.replan_fail_streak_open = parseInt(arg, requireValue(i, arg));
    } else if (arg == "--replan-ok-streak-close") {
      options.replan_ok_streak_close = parseInt(arg, requireValue(i, arg));
    } else if (arg == "--no-replan-guard") {
      options.replan_guard_en = false;
    } else if (arg == "--bounded-replan-guard") {
      options.bounded_replan_guard = true;
    } else if (arg == "--replan-open-burst-s") {
      options.replan_open_burst_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--replan-open-cooldown-s") {
      options.replan_open_cooldown_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--near-field-radius-m") {
      options.near_field_radius_m = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--near-field-speed-gain-s") {
      options.near_field_speed_gain_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--near-field-max-radius-m") {
      options.near_field_max_radius_m = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--guard-witness-topic") {
      options.guard_witness_topic = requireValue(i, arg);
    } else if (arg == "--guard-witness-radius-m") {
      options.guard_witness_radius_m =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--open-burst-s") {
      options.open_burst_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--open-cooldown-s") {
      options.open_cooldown_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--trajectory-guard-topic") {
      options.trajectory_guard_topic = requireValue(i, arg);
    } else if (arg == "--trajectory-guard-hold-s") {
      options.trajectory_guard_hold_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--trajectory-guard-active-max-publish-hz") {
      options.trajectory_guard_active_max_publish_hz =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--trajectory-guard-ack-retry-age-s") {
      options.trajectory_guard_ack_retry_age_s =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg ==
               "--test-drop-first-trajectory-guard-full-cloud") {
      options.test_drop_first_trajectory_guard_full_cloud = true;
    } else if (arg == "--direct-input") {
      options.direct_input = true;
    } else if (arg == "--risk-verdict-topic") {
      options.risk_verdict_topic = requireValue(i, arg);
    } else if (arg == "--risk-trajectory-topic") {
      options.risk_trajectory_topic = requireValue(i, arg);
    } else if (arg == "--risk-accum-window-s") {
      options.risk_accum_window_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-clearance-m") {
      options.risk_clearance_m = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-horizon-s") {
      options.risk_horizon_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-sample-dt-s") {
      options.risk_sample_dt_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-min-points") {
      options.risk_min_points = parseInt(arg, requireValue(i, arg));
    } else if (arg == "--risk-voxel-m") {
      options.risk_voxel_m = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-max-cloud-age-s") {
      options.risk_max_cloud_age_s = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-max-eval-hz") {
      options.risk_max_eval_hz = parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-egress-tolerance-m") {
      options.risk_egress_tolerance_m =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--risk-egress-min-progress-m") {
      options.risk_egress_min_progress_m =
          parseDouble(arg, requireValue(i, arg));
    } else if (arg == "--help" || arg == "-h") {
      throw std::runtime_error(
          "usage: native_sector_cpp [full|sector|velocity|adaptive] "
          "[half_angle_deg] "
          "[native_sector.py-compatible options]");
    } else {
      throw std::runtime_error("unknown argument '" + arg + "'");
    }
  }

  const std::array<std::string, 6> modes{
      "full", "sector", "velocity", "adaptive", "trigger", "legacy-trigger"};
  if (std::find(modes.begin(), modes.end(), options.mode) == modes.end()) {
    throw std::runtime_error("unsupported mode '" + options.mode + "'");
  }
  if (options.track_trap || options.sector_until_trap ||
      !options.event_json.empty()) {
    throw std::runtime_error("C++ backend does not yet implement seed12-15 "
                             "trap-event instrumentation; "
                             "use the Python backend for those maps");
  }
  const double near_max =
      options.near_field_max_radius_m.value_or(options.near_field_radius_m);
  const double guard_burst =
      options.replan_open_burst_s.value_or(options.open_burst_s);
  const double guard_cooldown =
      options.replan_open_cooldown_s.value_or(options.open_cooldown_s);
  if (options.half_angle_deg < 0.0 || options.half_angle_deg > 180.0 ||
      options.max_publish_hz < 0.0 || options.stall_v < 0.0 ||
      options.map_commit_refresh_age_s < 0.0 ||
      options.map_commit_refresh_min_interval_s < 0.0 ||
      options.map_commit_pre_stale_full_age_s < 0.0 ||
      options.map_commit_pre_stale_ack_retry_age_s < 0.0 ||
      options.stall_t < 0.0 || options.resume_v < 0.0 ||
      options.resume_t < 0.0 || options.slowdown_full_refresh_v < 0.0 ||
      options.slowdown_full_refresh_rearm_v < 0.0 ||
      options.open_burst_s < 0.0 ||
      options.open_cooldown_s < 0.0 ||
      options.trajectory_guard_hold_s < 0.0 ||
      options.trajectory_guard_active_max_publish_hz < 0.0 ||
      options.trajectory_guard_ack_retry_age_s < 0.0 ||
      options.near_field_radius_m < 0.0 ||
      options.near_field_speed_gain_s < 0.0 ||
      options.guard_witness_radius_m < 0.0 ||
      options.risk_accum_window_s < 0.0 ||
      options.risk_clearance_m <= 0.0 || options.risk_horizon_s < 0.0 ||
      options.risk_sample_dt_s <= 0.0 || options.risk_min_points <= 0 ||
      options.risk_voxel_m < 0.0 || options.risk_max_cloud_age_s <= 0.0 ||
      options.risk_max_eval_hz < 0.0 ||
      options.risk_egress_tolerance_m < 0.0 ||
      options.risk_egress_min_progress_m < 0.0 ||
      near_max < options.near_field_radius_m || guard_burst < 0.0 ||
      guard_cooldown < 0.0) {
    throw std::runtime_error("invalid negative/range-limited filter setting");
  }
  if (options.resume_v <= options.stall_v) {
    throw std::runtime_error("resume-v must be greater than stall-v");
  }
  if (options.guard_witness_topic.empty() !=
      (options.guard_witness_radius_m <= 0.0)) {
    throw std::runtime_error(
        "guard witness requires both a non-empty topic and a positive radius");
  }
  if (!options.risk_verdict_topic.empty() &&
      options.risk_trajectory_topic.empty()) {
    throw std::runtime_error(
        "risk verdict requires both verdict and trajectory topics");
  }
  if (options.slowdown_full_refresh_v > 0.0 &&
      options.slowdown_full_refresh_rearm_v <=
          options.slowdown_full_refresh_v) {
    throw std::runtime_error(
        "slowdown-full-refresh-rearm-v must be greater than "
        "slowdown-full-refresh-v");
  }
  if (options.test_drop_first_trajectory_guard_full_cloud &&
      (options.mode != "adaptive" ||
       !options.full_refresh_generation_ack_en)) {
    throw std::runtime_error(
        "test trajectory-guard cloud drop requires adaptive mode and "
        "full-refresh generation ACK");
  }
  if (options.bounded_replan_guard && guard_burst <= 0.0) {
    throw std::runtime_error(
        "bounded-replan-guard requires a positive replan burst");
  }
  return options;
}

template <typename T> T loadScalar(const uint8_t *source, bool swap_bytes) {
  T value;
  std::memcpy(&value, source, sizeof(T));
  if (swap_bytes) {
    auto *bytes = reinterpret_cast<uint8_t *>(&value);
    std::reverse(bytes, bytes + sizeof(T));
  }
  return value;
}

bool hostIsBigEndian() {
  const uint16_t marker = 0x0102;
  return *reinterpret_cast<const uint8_t *>(&marker) == 0x01;
}

std::string jsonString(const std::string &value) {
  std::ostringstream out;
  out << '"';
  for (const char ch : value) {
    switch (ch) {
    case '\\':
      out << "\\\\";
      break;
    case '"':
      out << "\\\"";
      break;
    case '\n':
      out << "\\n";
      break;
    case '\r':
      out << "\\r";
      break;
    case '\t':
      out << "\\t";
      break;
    default:
      out << ch;
      break;
    }
  }
  out << '"';
  return out.str();
}

std::string jsonNumber(double value) {
  std::ostringstream out;
  out << std::setprecision(12) << value;
  return out.str();
}

std::string jsonOptional(const std::optional<double> &value) {
  return value ? jsonNumber(*value) : "null";
}

std::string jsonArray(const std::vector<double> &values) {
  std::ostringstream out;
  out << '[';
  for (size_t i = 0; i < values.size(); ++i) {
    if (i != 0)
      out << ',';
    out << jsonNumber(values[i]);
  }
  out << ']';
  return out.str();
}

double rounded(double value, double scale = 1e6) {
  return std::round(value * scale) / scale;
}

} // namespace

class NativeSectorCpp final : public rclcpp::Node {
public:
  explicit NativeSectorCpp(
      Options options,
      const rclcpp::NodeOptions &node_options = rclcpp::NodeOptions(),
      native_sector::GuardCloudObserver guard_cloud_observer = {})
      : Node("native_sector_cpp", node_options), options_(std::move(options)),
        half_angle_rad_(options_.half_angle_deg * kPi / 180.0),
        half_angle_cos_(std::cos(half_angle_rad_)),
        near_field_max_radius_m_(options_.near_field_max_radius_m.value_or(
            options_.near_field_radius_m)),
        replan_guard_burst_s_(
            options_.replan_open_burst_s.value_or(options_.open_burst_s)),
        replan_guard_cooldown_s_(
            options_.replan_open_cooldown_s.value_or(options_.open_cooldown_s)),
        guard_cloud_observer_(std::move(guard_cloud_observer)),
        armed_(options_.mode == "legacy-trigger") {
    const auto sensor_qos =
        rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();
    if (!options_.direct_input) {
      cloud_sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
          options_.input_topic, sensor_qos,
          std::bind(&NativeSectorCpp::cloudCallback, this,
                    std::placeholders::_1));
    }
    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
        "/lidar_slam/odom", sensor_qos,
        std::bind(&NativeSectorCpp::odomCallback, this, std::placeholders::_1));
    if (options_.mode != "full" && options_.replan_guard_en) {
      replan_sub_ = create_subscription<std_msgs::msg::Bool>(
          "/planning/replan_status", sensor_qos,
          std::bind(&NativeSectorCpp::replanCallback, this,
                    std::placeholders::_1));
    }
    if (options_.mode == "adaptive") {
      const auto guard_qos =
          rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
      rclcpp::SubscriptionOptions guard_options;
      guard_options.use_intra_process_comm =
          rclcpp::IntraProcessSetting::Disable;
      trajectory_guard_sub_ = create_subscription<std_msgs::msg::Bool>(
          options_.trajectory_guard_topic, guard_qos,
          std::bind(&NativeSectorCpp::trajectoryGuardCallback, this,
                    std::placeholders::_1),
          guard_options);
    }
    if (options_.mode == "adaptive" && options_.max_publish_hz > 0.0 &&
        (options_.map_commit_refresh_age_s > 0.0 ||
         options_.map_commit_pre_stale_full_age_s > 0.0)) {
      map_commit_sub_ = create_subscription<std_msgs::msg::UInt64>(
          options_.map_commit_topic, sensor_qos,
          std::bind(&NativeSectorCpp::mapCommitCallback, this,
                    std::placeholders::_1));
    }
    if (options_.mode == "adaptive" &&
        options_.full_refresh_generation_ack_en) {
      const auto generation_qos = rclcpp::QoS(rclcpp::KeepLast(16))
                                      .reliable()
                                      .durability_volatile();
      map_process_ack_sub_ =
          create_subscription<std_msgs::msg::UInt64MultiArray>(
              options_.map_process_ack_topic, generation_qos,
              std::bind(&NativeSectorCpp::mapProcessAckCallback, this,
                        std::placeholders::_1));
      const auto request_qos = rclcpp::QoS(rclcpp::KeepLast(16))
                                   .reliable()
                                   .transient_local();
      rclcpp::PublisherOptions request_options;
      request_options.use_intra_process_comm =
          rclcpp::IntraProcessSetting::Disable;
      full_refresh_request_pub_ =
          create_publisher<std_msgs::msg::UInt64MultiArray>(
              options_.full_refresh_request_topic, request_qos,
              request_options);
    }
    const auto output_qos = options_.reliable_output
        ? rclcpp::QoS(rclcpp::KeepLast(1)).reliable().durability_volatile()
        : sensor_qos;
    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
        options_.output_topic, output_qos);
    if (!options_.risk_verdict_topic.empty()) {
      trajectory_sub_ = create_subscription<
          mars_quadrotor_msgs::msg::PolynomialTrajectory>(
          options_.risk_trajectory_topic, sensor_qos,
          std::bind(&NativeSectorCpp::trajectoryCallback, this,
                    std::placeholders::_1));
      const auto verdict_qos = rclcpp::QoS(rclcpp::KeepLast(4))
                                   .reliable()
                                   .durability_volatile();
      risk_verdict_pub_ = create_publisher<
          mars_quadrotor_msgs::msg::TrajectoryRiskVerdict>(
          options_.risk_verdict_topic, verdict_qos);
    }
    if (!options_.guard_witness_topic.empty()) {
      // The witness is latest-only evidence, just like the simulator's raw
      // sensor stream. Keep this hop best-effort depth-1 even when the map
      // output is reliable, so an unavailable guard subscriber cannot block
      // filtering or map delivery.
      guard_witness_pub_ =
          create_publisher<sensor_msgs::msg::PointCloud2>(
              options_.guard_witness_topic, sensor_qos);
    }
    full_open_pub_ =
        create_publisher<std_msgs::msg::Bool>("/sector/full_open", 1);
    armed_pub_ =
        create_publisher<std_msgs::msg::Bool>("/sector/trigger_armed", 1);
    state_timer_ = create_wall_timer(std::chrono::seconds(1), [this]() {
      std::lock_guard<std::mutex> lock(state_mutex_);
      publishState();
      writeStats();
    });
    report_timer_ = create_wall_timer(
        std::chrono::seconds(5), std::bind(&NativeSectorCpp::report, this));

    if (full_refresh_request_pub_) {
      // A transient-local zero record advertises that this Adaptive filter
      // participates in generation-gated recovery before the first cloud.
      std_msgs::msg::UInt64MultiArray enabled;
      enabled.data = {0, 0, 0};
      full_refresh_request_pub_->publish(enabled);
    }

    RCLCPP_INFO(get_logger(),
                "%s mode, half-angle %.1f deg, input %s, publish cap %.2f Hz, "
                "commit refresh %.3f s, full-open extra budget %lu, "
                "guard witness %s radius %.2f m, direct input %s, "
                "risk verdict %s",
                options_.mode.c_str(), options_.half_angle_deg,
                options_.input_topic.c_str(), options_.max_publish_hz,
                options_.map_commit_refresh_age_s,
                static_cast<unsigned long>(
                    options_.full_open_extra_max_points),
                options_.guard_witness_topic.empty()
                    ? "disabled"
                    : options_.guard_witness_topic.c_str(),
                options_.guard_witness_radius_m,
                options_.direct_input ? "enabled" : "disabled",
                options_.risk_verdict_topic.empty()
                    ? "disabled"
                    : options_.risk_verdict_topic.c_str());
    publishState();
    writeStats();
    cloud_worker_ = std::thread(&NativeSectorCpp::cloudWorkerLoop, this);
    if (risk_verdict_pub_)
      risk_worker_ = std::thread(&NativeSectorCpp::riskWorkerLoop, this);
  }

  ~NativeSectorCpp() override {
    {
      std::lock_guard<std::mutex> lock(cloud_queue_mutex_);
      cloud_worker_stop_ = true;
      pending_cloud_.reset();
    }
    cloud_queue_cv_.notify_one();
    if (cloud_worker_.joinable())
      cloud_worker_.join();
    {
      std::lock_guard<std::mutex> lock(risk_worker_mutex_);
      risk_worker_stop_ = true;
      pending_risk_job_.reset();
    }
    risk_worker_cv_.notify_one();
    if (risk_worker_.joinable())
      risk_worker_.join();
    std::lock_guard<std::mutex> lock(state_mutex_);
    writeStats();
  }

  // Direct raw-sensor handoff used by the simulator/front-end composition.
  // The exact same latest-only queue and accounting path is used as the DDS
  // subscription callback, but the raw PointCloud2 is never serialized.
  void submitCloud(
      const sensor_msgs::msg::PointCloud2::SharedPtr &cloud_msg) {
    cloudCallback(cloud_msg);
  }

private:
  bool statefulMode() const {
    return options_.mode == "adaptive" || options_.mode == "trigger" ||
           options_.mode == "legacy-trigger";
  }

  bool effectiveFullOpen() const {
    return options_.mode == "full" ||
           (statefulMode() && effective_recovery_open_) ||
           replan_guard_open_ || trajectory_guard_open_;
  }

  void observeEffectiveFullOpen(double now) {
    const bool current = effectiveFullOpen();
    if (!effective_full_open_initialized_) {
      effective_full_open_ = current;
      effective_full_open_initialized_ = true;
      return;
    }
    if (current == effective_full_open_)
      return;
    effective_full_open_ = current;
    if (current) {
      ++effective_full_open_transitions_;
      if (!first_effective_full_open_time_s_)
        first_effective_full_open_time_s_ = rounded(now);
    } else {
      ++effective_full_close_transitions_;
    }
  }

  double nowSeconds() { return get_clock()->now().seconds(); }

  enum class PublishDecision {
    DROP,
    REGULAR,
    COMMIT_REFRESH,
    PRE_STALE_FULL_REFRESH
  };

  void recordFullRefreshSourceVersion(bool pre_stale,
                                      double trigger_age_s = 0.0,
                                      bool exact_ack_retry = false) {
    if (!last_map_commit_rx_s_)
      return;
    last_full_refresh_source_version_ = last_map_commit_version_;
    if (!pre_stale)
      return;
    ++pre_stale_full_refresh_frames_;
    if (exact_ack_retry)
      ++pre_stale_full_refresh_ack_retry_frames_;
    pre_stale_full_refresh_source_version_ = last_map_commit_version_;
    pre_stale_full_refresh_pending_version_advance_ = true;
    pre_stale_full_refresh_trigger_age_sum_s_ += trigger_age_s;
    pre_stale_full_refresh_trigger_age_max_s_ =
        std::max(pre_stale_full_refresh_trigger_age_max_s_, trigger_age_s);
  }

  PublishDecision publicationDecision(double now) {
    trajectory_guard_unbounded_refresh_frame_ = false;
    slowdown_unbounded_refresh_frame_ = false;
    // The first cloud after a guard brake is safety evidence, so do not make
    // it wait behind the Adaptive publication cap. Only one latest cloud is
    // exempted per guard true-edge.
    if (trajectory_guard_refresh_pending_) {
      trajectory_guard_refresh_pending_ = false;
      trajectory_guard_unbounded_refresh_frame_ = true;
      ++trajectory_guard_refresh_frames_;
      recordFullRefreshSourceVersion(false);
      return PublishDecision::REGULAR;
    }
    // A successful short-horizon replan can decelerate into a blind-side
    // obstacle without first producing a replan failure or guard edge. On a
    // hysteretic high-to-low-speed transition, let exactly one latest scan
    // bypass the Adaptive publication cap and sector crop. Re-arming requires
    // a distinct high-speed phase, so stop jitter cannot flood the map worker.
    if (slowdown_full_refresh_pending_) {
      slowdown_full_refresh_pending_ = false;
      slowdown_unbounded_refresh_frame_ = true;
      ++slowdown_full_refresh_frames_;
      return PublishDecision::REGULAR;
    }
    if (trajectory_guard_active_ &&
        options_.full_refresh_generation_ack_en &&
        options_.trajectory_guard_ack_retry_age_s > 0.0 &&
        trajectory_guard_pending_exact_ack_stamp_ns_ &&
        trajectory_guard_pending_exact_ack_send_s_ &&
        now - *trajectory_guard_pending_exact_ack_send_s_ >=
            options_.trajectory_guard_ack_retry_age_s) {
      // A reliable depth-1 DDS hop guarantees transport delivery, not that a
      // slow subscriber will take this exact cloud before a newer sample
      // replaces it. While the planner is already fail-closed, resend one
      // latest complete generation at a bounded stop-and-wait cadence until
      // an exact process ACK arrives. Normal flight and pre-stale publication
      // remain unchanged.
      trajectory_guard_unbounded_refresh_frame_ = true;
      ++trajectory_guard_refresh_frames_;
      ++trajectory_guard_full_refresh_ack_retry_frames_;
      recordFullRefreshSourceVersion(false);
      return PublishDecision::REGULAR;
    }
    double publish_hz = options_.max_publish_hz;
    if (options_.mode == "adaptive" && trajectory_guard_active_ &&
        options_.trajectory_guard_active_max_publish_hz > publish_hz) {
      publish_hz = options_.trajectory_guard_active_max_publish_hz;
    }

    // A guard true-edge is too late to change the brake that was already
    // certified against a stale map. Before that stale threshold, allow one
    // complete scan per acknowledged map version. The version gate prevents a
    // stalled map worker from being flooded with repeated full scans.
    const double commit_age_s = last_map_commit_rx_s_
        ? std::max(0.0, now - *last_map_commit_rx_s_)
        : 0.0;
    const bool pre_stale_age_due = options_.mode == "adaptive" &&
        options_.map_commit_pre_stale_full_age_s > 0.0 &&
        last_map_commit_rx_s_ &&
        commit_age_s >= options_.map_commit_pre_stale_full_age_s;
    const bool version_already_refreshed =
        last_full_refresh_source_version_ &&
        *last_full_refresh_source_version_ == last_map_commit_version_;
    const bool exact_ack_retry_enabled =
        options_.full_refresh_generation_ack_en &&
        options_.map_commit_pre_stale_ack_retry_age_s > 0.0;
    double pending_exact_ack_age_s = 0.0;
    const bool exact_ack_pending = !pre_stale_pending_exact_ack_.empty();
    if (exact_ack_pending) {
      pending_exact_ack_age_s = std::max(
          0.0, now - pre_stale_pending_exact_ack_.begin()->second.send_s);
    }
    const bool retry_already_used =
        pre_stale_full_refresh_ack_retry_source_version_ &&
        *pre_stale_full_refresh_ack_retry_source_version_ ==
            last_map_commit_version_;
    const bool exact_ack_retry_due = pre_stale_age_due &&
        version_already_refreshed && exact_ack_retry_enabled &&
        exact_ack_pending && !retry_already_used &&
        pending_exact_ack_age_s >=
            options_.map_commit_pre_stale_ack_retry_age_s;
    if (exact_ack_retry_due) {
      // The reliable request token can arrive while its best-effort cloud is
      // lost. Send the next LiDAR generation once for this source map
      // version. This is content-driven and bounded: the retry has a new
      // stamp, supersedes the old pending generation, and cannot repeat until
      // the map version advances.
      pre_stale_full_refresh_ack_retry_source_version_ =
          last_map_commit_version_;
      recordFullRefreshSourceVersion(true, commit_age_s, true);
      if (publish_hz > 0.0)
        next_publish_time_s_ = now + 1.0 / publish_hz;
      return PublishDecision::PRE_STALE_FULL_REFRESH;
    }
    if (pre_stale_age_due && version_already_refreshed &&
        exact_ack_retry_enabled && exact_ack_pending && retry_already_used &&
        pending_exact_ack_age_s >=
            options_.map_commit_pre_stale_ack_retry_age_s) {
      ++pre_stale_full_refresh_ack_retry_suppressed_frames_;
    }
    if (pre_stale_age_due && !version_already_refreshed) {
      recordFullRefreshSourceVersion(true, commit_age_s);
      if (publish_hz > 0.0)
        next_publish_time_s_ = now + 1.0 / publish_hz;
      return PublishDecision::PRE_STALE_FULL_REFRESH;
    }
    if (pre_stale_age_due && version_already_refreshed)
      ++pre_stale_full_refresh_same_version_suppressed_frames_;

    if (publish_hz <= 0.0)
      return PublishDecision::REGULAR;
    const double period = 1.0 / publish_hz;
    if (!next_publish_time_s_) {
      next_publish_time_s_ = now + period;
      return PublishDecision::REGULAR;
    }
    if (now >= *next_publish_time_s_) {
      const double elapsed = now - *next_publish_time_s_;
      const double periods = std::floor(elapsed / period) + 1.0;
      *next_publish_time_s_ += periods * period;
      return PublishDecision::REGULAR;
    }

    // The cap controls expensive Adaptive publications, not safety evidence.
    // When the actual ROG-Map commit acknowledgement ages, allow one bounded
    // sector-only heartbeat.  A minimum interval and depth-1 QoS retain
    // latest-only behavior even if a commit is temporarily delayed.
    const bool commit_refresh_due = options_.mode == "adaptive" &&
        last_map_commit_rx_s_ &&
        now - *last_map_commit_rx_s_ >=
            options_.map_commit_refresh_age_s &&
        (!last_commit_refresh_publish_s_ ||
         now - *last_commit_refresh_publish_s_ >=
             options_.map_commit_refresh_min_interval_s);
    if (commit_refresh_due) {
      last_commit_refresh_publish_s_ = now;
      return PublishDecision::COMMIT_REFRESH;
    }
    ++rate_limited_frames_;
    return PublishDecision::DROP;
  }

  void mapCommitCallback(const std_msgs::msg::UInt64::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    const double now = nowSeconds();
    if (pre_stale_full_refresh_pending_version_advance_ &&
        pre_stale_full_refresh_source_version_ &&
        msg->data > *pre_stale_full_refresh_source_version_) {
      ++pre_stale_full_refresh_version_advance_count_;
      pre_stale_full_refresh_pending_version_advance_ = false;
    }
    last_map_commit_rx_s_ = now;
    last_map_commit_version_ = msg->data;
    ++map_commit_status_count_;
    recordCadence(map_commit_first_ns_, map_commit_last_ns_);
  }

  struct PendingFullRefresh {
    double send_s{0.0};
  };

  static uint64_t cloudStampNs(const sensor_msgs::msg::PointCloud2 &msg) {
    const int64_t stamp_ns =
        static_cast<int64_t>(msg.header.stamp.sec) * 1000000000LL +
        static_cast<int64_t>(msg.header.stamp.nanosec);
    return static_cast<uint64_t>(stamp_ns);
  }

  void publishFullRefreshRequest(
      const sensor_msgs::msg::PointCloud2 &msg, uint64_t kind, double now) {
    if (!full_refresh_request_pub_)
      return;
    const uint64_t stamp_ns = cloudStampNs(msg);
    const uint64_t request_seq = ++full_refresh_request_seq_;
    std_msgs::msg::UInt64MultiArray request;
    // [filter request sequence, exact PointCloud2 source stamp, kind]
    // kind 1 = pre-stale; kind 2 = trajectory-guard true edge;
    // kind 3 = hysteretic high-to-low-speed transition.
    request.data = {request_seq, stamp_ns, kind};
    full_refresh_request_pub_->publish(request);
    ++full_refresh_request_count_;
    if (kind == 1) {
      if (!pre_stale_pending_exact_ack_.empty()) {
        pre_stale_full_refresh_superseded_count_ +=
            pre_stale_pending_exact_ack_.size();
        pre_stale_pending_exact_ack_.clear();
      }
      const auto [it, inserted] = pre_stale_pending_exact_ack_.emplace(
          stamp_ns, PendingFullRefresh{now});
      if (!inserted) {
        ++full_refresh_duplicate_stamp_count_;
        it->second.send_s = now;
      }
      pre_stale_full_refresh_pending_ack_max_ = std::max<uint64_t>(
          pre_stale_full_refresh_pending_ack_max_,
          pre_stale_pending_exact_ack_.size());
    } else if (kind == 2) {
      if (trajectory_guard_pending_exact_ack_stamp_ns_) {
        ++trajectory_guard_full_refresh_superseded_count_;
      }
      trajectory_guard_pending_exact_ack_stamp_ns_ = stamp_ns;
      trajectory_guard_pending_exact_ack_send_s_ = now;
      trajectory_guard_full_refresh_pending_ack_max_ = 1;
    } else if (kind == 3) {
      if (slowdown_pending_exact_ack_stamp_ns_)
        ++slowdown_full_refresh_superseded_count_;
      slowdown_pending_exact_ack_stamp_ns_ = stamp_ns;
      slowdown_pending_exact_ack_send_s_ = now;
    }
  }

  void mapProcessAckCallback(
      const std_msgs::msg::UInt64MultiArray::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    ++map_process_ack_status_count_;
    if (msg->data.size() < 4) {
      ++map_process_ack_malformed_count_;
      return;
    }
    const uint64_t stamp_ns = msg->data[1];
    last_map_process_ack_scan_seq_ = msg->data[0];
    last_map_process_ack_stamp_ns_ = stamp_ns;
    last_map_process_ack_version_ = msg->data[2];
    if (trajectory_guard_pending_exact_ack_stamp_ns_ &&
        *trajectory_guard_pending_exact_ack_stamp_ns_ == stamp_ns) {
      ++trajectory_guard_full_refresh_ack_count_;
      if (msg->data[3] != 0)
        ++trajectory_guard_full_refresh_ack_committed_count_;
      if (trajectory_guard_pending_exact_ack_send_s_) {
        const double latency = std::max(
            0.0, nowSeconds() -
                     *trajectory_guard_pending_exact_ack_send_s_);
        trajectory_guard_full_refresh_ack_latency_sum_s_ += latency;
        trajectory_guard_full_refresh_ack_latency_max_s_ = std::max(
            trajectory_guard_full_refresh_ack_latency_max_s_, latency);
      }
      trajectory_guard_pending_exact_ack_stamp_ns_.reset();
      trajectory_guard_pending_exact_ack_send_s_.reset();
    }
    if (slowdown_pending_exact_ack_stamp_ns_ &&
        *slowdown_pending_exact_ack_stamp_ns_ == stamp_ns) {
      ++slowdown_full_refresh_ack_count_;
      if (msg->data[3] != 0)
        ++slowdown_full_refresh_ack_committed_count_;
      if (slowdown_pending_exact_ack_send_s_) {
        const double latency = std::max(
            0.0, nowSeconds() - *slowdown_pending_exact_ack_send_s_);
        slowdown_full_refresh_ack_latency_sum_s_ += latency;
        slowdown_full_refresh_ack_latency_max_s_ = std::max(
            slowdown_full_refresh_ack_latency_max_s_, latency);
      }
      slowdown_pending_exact_ack_stamp_ns_.reset();
      slowdown_pending_exact_ack_send_s_.reset();
    }
    const auto pending = pre_stale_pending_exact_ack_.find(stamp_ns);
    if (pending == pre_stale_pending_exact_ack_.end())
      return;
    ++pre_stale_full_refresh_ack_count_;
    if (msg->data[3] != 0)
      ++pre_stale_full_refresh_ack_committed_count_;
    const double latency = std::max(0.0, nowSeconds() - pending->second.send_s);
    pre_stale_full_refresh_ack_latency_sum_s_ += latency;
    pre_stale_full_refresh_ack_latency_max_s_ =
        std::max(pre_stale_full_refresh_ack_latency_max_s_, latency);
    pre_stale_pending_exact_ack_.erase(pending);
  }

  void recordTransition(const std::string &transition, double now) {
    const double timestamp = rounded(now);
    if (!first_transition_time_s_)
      first_transition_time_s_ = timestamp;
    if (transition == "arm") {
      ++arm_transitions_;
      arm_transition_times_s_.push_back(timestamp);
      if (!first_arm_time_s_)
        first_arm_time_s_ = timestamp;
    } else if (transition == "open") {
      ++open_transitions_;
      open_transition_times_s_.push_back(timestamp);
      if (!first_open_time_s_)
        first_open_time_s_ = timestamp;
    } else {
      ++close_transitions_;
      close_transition_times_s_.push_back(timestamp);
      if (!first_close_time_s_)
        first_close_time_s_ = timestamp;
    }
  }

  void startRecoveryBurst(double now) {
    if (options_.open_burst_s <= 0.0) {
      effective_recovery_open_ = recovery_active_;
      open_burst_until_s_.reset();
      next_open_burst_s_.reset();
      return;
    }
    effective_recovery_open_ = true;
    open_burst_until_s_ = now + options_.open_burst_s;
    next_open_burst_s_ = *open_burst_until_s_ + options_.open_cooldown_s;
  }

  bool updateRecoveryBurst(double now) {
    const bool previous = effective_recovery_open_;
    if (!recovery_active_) {
      effective_recovery_open_ = false;
    } else if (options_.open_burst_s <= 0.0) {
      effective_recovery_open_ = true;
    } else if (next_open_burst_s_ && now >= *next_open_burst_s_) {
      startRecoveryBurst(now);
    } else {
      effective_recovery_open_ =
          open_burst_until_s_ && now < *open_burst_until_s_;
    }
    return previous != effective_recovery_open_;
  }

  void stopRecoveryOpen() {
    recovery_active_ = false;
    effective_recovery_open_ = false;
    open_burst_until_s_.reset();
    next_open_burst_s_.reset();
  }

  void startReplanGuardBurst(double now) {
    const bool was_open = replan_guard_open_;
    replan_guard_open_ = true;
    if (options_.bounded_replan_guard) {
      replan_guard_burst_until_s_ = now + replan_guard_burst_s_;
      replan_guard_next_burst_s_ =
          *replan_guard_burst_until_s_ + replan_guard_cooldown_s_;
    } else {
      replan_guard_burst_until_s_.reset();
      replan_guard_next_burst_s_.reset();
    }
    if (!was_open) {
      ++replan_guard_open_transitions_;
      if (!first_replan_guard_open_time_s_) {
        first_replan_guard_open_time_s_ = rounded(now);
      }
    }
  }

  bool updateReplanGuardBurst(double now) {
    const bool was_open = replan_guard_open_;
    if (!replan_guard_active_) {
      replan_guard_open_ = false;
    } else if (!options_.bounded_replan_guard) {
      replan_guard_open_ = true;
    } else {
      replan_guard_open_ =
          replan_guard_burst_until_s_ && now < *replan_guard_burst_until_s_;
      if (!replan_guard_open_) {
        replan_guard_active_ = false;
        replan_guard_burst_until_s_.reset();
      }
    }
    if (was_open && !replan_guard_open_)
      ++replan_guard_close_transitions_;
    return was_open != replan_guard_open_;
  }

  void stopReplanGuard() {
    replan_guard_active_ = false;
    if (replan_guard_open_)
      ++replan_guard_close_transitions_;
    replan_guard_open_ = false;
    replan_guard_burst_until_s_.reset();
    replan_guard_next_burst_s_.reset();
  }

  void odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    const auto &p = msg->pose.pose.position;
    const auto &q = msg->pose.pose.orientation;
    drone_ = std::array<double, 3>{p.x, p.y, p.z};
    yaw_ = std::atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z));
    const auto &v = msg->twist.twist.linear;
    const double speed = std::hypot(v.x, v.y);
    latest_speed_mps_ = speed;
    if (options_.mode == "adaptive" &&
        options_.slowdown_full_refresh_v > 0.0) {
      if (speed >= options_.slowdown_full_refresh_rearm_v) {
        slowdown_full_refresh_armed_ = true;
      } else if (slowdown_full_refresh_armed_ &&
                 speed <= options_.slowdown_full_refresh_v) {
        slowdown_full_refresh_armed_ = false;
        slowdown_full_refresh_pending_ = true;
        ++slowdown_full_refresh_triggers_;
      }
    }
    const double velocity_update_v =
        (options_.mode == "velocity" || options_.mode == "adaptive")
            ? options_.resume_v
            : 0.2;
    if (speed > velocity_update_v)
      velocity_yaw_ = std::atan2(v.y, v.x);

    if (!statefulMode())
      return;
    const double now = nowSeconds();
    if (!armed_) {
      if (speed > options_.resume_v) {
        if (!fast_since_s_) {
          fast_since_s_ = now;
        } else if (now - *fast_since_s_ > options_.resume_t) {
          armed_ = true;
          fast_since_s_.reset();
          recordTransition("arm", now);
          publishState();
          writeStats();
        }
      } else {
        fast_since_s_.reset();
      }
      return;
    }

    if (!recovery_active_) {
      min_armed_closed_speed_mps_ =
          min_armed_closed_speed_mps_
              ? std::min(*min_armed_closed_speed_mps_, speed)
              : speed;
      if (speed < options_.stall_v) {
        if (!slow_since_s_) {
          slow_since_s_ = now;
          ++stall_candidate_count_;
          if (!first_stall_candidate_time_s_) {
            first_stall_candidate_time_s_ = rounded(now);
            writeStats();
          }
        }
        const double duration = now - *slow_since_s_;
        max_stall_candidate_duration_s_ =
            std::max(max_stall_candidate_duration_s_, duration);
        if (duration > options_.stall_t) {
          if (!first_open_delay_s_) {
            first_open_stall_start_time_s_ = rounded(*slow_since_s_);
            first_open_delay_s_ = rounded(duration);
          }
          recovery_active_ = true;
          slow_since_s_.reset();
          fast_since_s_.reset();
          startRecoveryBurst(now);
          recordTransition("open", now);
          publishState();
          writeStats();
        }
      } else {
        if (slow_since_s_) {
          max_stall_candidate_duration_s_ =
              std::max(max_stall_candidate_duration_s_, now - *slow_since_s_);
        }
        slow_since_s_.reset();
      }
    } else if (speed > options_.resume_v) {
      if (!fast_since_s_) {
        fast_since_s_ = now;
      } else if (now - *fast_since_s_ > options_.resume_t) {
        stopRecoveryOpen();
        slow_since_s_.reset();
        fast_since_s_.reset();
        recordTransition("close", now);
        publishState();
        writeStats();
      }
    } else {
      fast_since_s_.reset();
    }
  }

  void replanCallback(const std_msgs::msg::Bool::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    const double now = nowSeconds();
    ++replan_status_count_;
    if (msg->data) {
      ++replan_ok_streak_;
      replan_fail_streak_ = 0;
    } else {
      ++replan_fail_streak_;
      replan_ok_streak_ = 0;
      ++replan_fail_count_;
      max_replan_fail_streak_ =
          std::max(max_replan_fail_streak_, replan_fail_streak_);
    }

    if (!replan_guard_active_) {
      const bool cooldown_ready =
          !replan_guard_next_burst_s_ || now >= *replan_guard_next_burst_s_;
      if (cooldown_ready &&
          replan_fail_streak_ >= options_.replan_fail_streak_open) {
        replan_guard_active_ = true;
        startReplanGuardBurst(now);
        if (options_.bounded_replan_guard)
          replan_fail_streak_ = 0;
        publishState();
        writeStats();
      }
    } else if (!options_.bounded_replan_guard &&
               replan_ok_streak_ >= options_.replan_ok_streak_close) {
      stopReplanGuard();
      publishState();
      writeStats();
    }
  }

  void setTrajectoryGuardOpen(bool open, double now) {
    if (open == trajectory_guard_open_)
      return;
    trajectory_guard_open_ = open;
    if (open) {
      ++trajectory_guard_open_transitions_;
      if (!first_trajectory_guard_open_time_s_)
        first_trajectory_guard_open_time_s_ = rounded(now);
    } else {
      ++trajectory_guard_close_transitions_;
      trajectory_guard_hold_until_s_.reset();
    }
  }

  void trajectoryGuardCallback(const std_msgs::msg::Bool::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    const double now = nowSeconds();
    ++trajectory_guard_status_count_;
    trajectory_guard_active_ = msg->data;
    if (msg->data) {
      ++trajectory_guard_active_count_;
      // A held-open interval can contain many distinct guard episodes. Each
      // true edge needs one complete, uncapped scan; tying this refresh to an
      // open transition silently collapsed dozens of episodes into one.
      trajectory_guard_refresh_pending_ = true;
      trajectory_guard_hold_until_s_.reset();
      setTrajectoryGuardOpen(true, now);
    } else {
      if (trajectory_guard_pending_exact_ack_stamp_ns_) {
        ++trajectory_guard_full_refresh_abandoned_count_;
        trajectory_guard_pending_exact_ack_stamp_ns_.reset();
        trajectory_guard_pending_exact_ack_send_s_.reset();
      }
      if (trajectory_guard_open_ &&
          options_.trajectory_guard_hold_s > 0.0) {
        trajectory_guard_hold_until_s_ =
            now + options_.trajectory_guard_hold_s;
      } else {
        setTrajectoryGuardOpen(false, now);
      }
    }
    publishState();
    writeStats();
  }

  bool updateTrajectoryGuardHold(double now) {
    const bool previous = trajectory_guard_open_;
    if (trajectory_guard_active_) {
      setTrajectoryGuardOpen(true, now);
    } else if (trajectory_guard_hold_until_s_ &&
               now >= *trajectory_guard_hold_until_s_) {
      setTrajectoryGuardOpen(false, now);
    }
    return previous != trajectory_guard_open_;
  }

  struct CloudFields {
    const sensor_msgs::msg::PointField *x{nullptr};
    const sensor_msgs::msg::PointField *y{nullptr};
    const sensor_msgs::msg::PointField *z{nullptr};
  };

  static CloudFields findCloudFields(const sensor_msgs::msg::PointCloud2 &msg) {
    CloudFields result;
    for (const auto &field : msg.fields) {
      if (field.name == "x")
        result.x = &field;
      else if (field.name == "y")
        result.y = &field;
      else if (field.name == "z")
        result.z = &field;
    }
    return result;
  }

  static bool readField(const uint8_t *point,
                        const sensor_msgs::msg::PointField &field,
                        bool swap_bytes, double &value) {
    if (field.datatype == sensor_msgs::msg::PointField::FLOAT32) {
      value = static_cast<double>(
          loadScalar<float>(point + field.offset, swap_bytes));
      return true;
    }
    if (field.datatype == sensor_msgs::msg::PointField::FLOAT64) {
      value = loadScalar<double>(point + field.offset, swap_bytes);
      return true;
    }
    return false;
  }

  using RiskClock = std::chrono::steady_clock;

  static int64_t cadenceTimestampNs(const RiskClock::time_point time) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               time.time_since_epoch())
        .count();
  }

  static void recordCadence(
      std::atomic<int64_t> &first_ns, std::atomic<int64_t> &last_ns,
      const RiskClock::time_point time = RiskClock::now()) {
    const int64_t timestamp_ns = cadenceTimestampNs(time);
    int64_t unset = 0;
    first_ns.compare_exchange_strong(unset, timestamp_ns,
                                     std::memory_order_relaxed);
    last_ns.store(timestamp_ns, std::memory_order_relaxed);
  }

  static double cadenceSpanSeconds(
      const std::atomic<int64_t> &first_ns,
      const std::atomic<int64_t> &last_ns) {
    const int64_t first = first_ns.load(std::memory_order_relaxed);
    const int64_t last = last_ns.load(std::memory_order_relaxed);
    return first > 0 && last >= first ? 1e-9 * (last - first) : 0.0;
  }

  static double cadenceRateHz(
      const uint64_t count, const std::atomic<int64_t> &first_ns,
      const std::atomic<int64_t> &last_ns) {
    const double span_s = cadenceSpanSeconds(first_ns, last_ns);
    return count > 1 && span_s > 0.0
        ? static_cast<double>(count - 1) / span_s
        : 0.0;
  }

  struct PolynomialSnapshot {
    uint64_t generation{0};
    double start_wt{0.0};
    uint32_t order{0};
    std::vector<double> durations;
    std::vector<double> coef_x;
    std::vector<double> coef_y;
    std::vector<double> coef_z;

    bool empty() const { return generation == 0 || durations.empty(); }

    double totalDuration() const {
      double total = 0.0;
      for (const double duration : durations)
        total += duration;
      return total;
    }

    bool position(double trajectory_time,
                  std::array<double, 3> &out) const {
      if (empty())
        return false;
      double local_time = std::clamp(trajectory_time, 0.0, totalDuration());
      size_t piece = 0;
      while (piece + 1 < durations.size() &&
             local_time > durations[piece]) {
        local_time -= durations[piece];
        ++piece;
      }
      local_time = std::clamp(local_time, 0.0, durations[piece]);
      const size_t columns = static_cast<size_t>(order) + 1;
      const size_t base = piece * columns;
      if (base + columns > coef_x.size() ||
          base + columns > coef_y.size() ||
          base + columns > coef_z.size()) {
        return false;
      }
      out = {0.0, 0.0, 0.0};
      double power = 1.0;
      for (int column = static_cast<int>(order); column >= 0; --column) {
        const size_t index = base + static_cast<size_t>(column);
        out[0] += power * coef_x[index];
        out[1] += power * coef_y[index];
        out[2] += power * coef_z[index];
        power *= local_time;
      }
      return std::isfinite(out[0]) && std::isfinite(out[1]) &&
             std::isfinite(out[2]);
    }
  };

  struct RiskCloudBatch {
    sensor_msgs::msg::PointCloud2::SharedPtr cloud;
    RiskClock::time_point receive_time{};
    uint64_t sequence{0};
  };

  struct RiskJob {
    uint64_t cloud_sequence{0};
    uint64_t source_cloud_stamp_ns{0};
    RiskClock::time_point cutoff_time{};
  };

  static int64_t riskVoxelKey(const double x, const double y,
                              const double z, const double voxel) {
    auto quantize = [voxel](const double value) -> int64_t {
      return static_cast<int64_t>(std::floor(value / voxel));
    };
    constexpr int64_t bits = 21;
    constexpr int64_t mask = (int64_t(1) << bits) - 1;
    constexpr int64_t offset = int64_t(1) << (bits - 1);
    const int64_t ix = (quantize(x) + offset) & mask;
    const int64_t iy = (quantize(y) + offset) & mask;
    const int64_t iz = (quantize(z) + offset) & mask;
    return (ix << (2 * bits)) | (iy << bits) | iz;
  }

  void trajectoryCallback(
      const mars_quadrotor_msgs::msg::PolynomialTrajectory::SharedPtr msg) {
    using TrajectoryMsg = mars_quadrotor_msgs::msg::PolynomialTrajectory;
    if ((msg->type & TrajectoryMsg::POSITION_TRAJ) == 0 ||
        msg->trajectory_generation == 0 || msg->piece_num_pos == 0) {
      return;
    }
    const size_t columns = static_cast<size_t>(msg->order_pos) + 1;
    const size_t coefficient_count =
        static_cast<size_t>(msg->piece_num_pos) * columns;
    if (msg->time_pos.size() != msg->piece_num_pos ||
        msg->coef_pos_x.size() != coefficient_count ||
        msg->coef_pos_y.size() != coefficient_count ||
        msg->coef_pos_z.size() != coefficient_count ||
        !std::isfinite(msg->start_wt_pos)) {
      ++risk_invalid_trajectory_messages_;
      RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 5000,
          "risk trajectory malformed: gen=%lu pieces=%u order=%u",
          static_cast<unsigned long>(msg->trajectory_generation),
          msg->piece_num_pos, msg->order_pos);
      return;
    }
    for (const double duration : msg->time_pos) {
      if (!std::isfinite(duration) || duration <= 0.0) {
        ++risk_invalid_trajectory_messages_;
        return;
      }
    }
    PolynomialSnapshot snapshot;
    snapshot.generation = msg->trajectory_generation;
    snapshot.start_wt = msg->start_wt_pos;
    snapshot.order = msg->order_pos;
    snapshot.durations = msg->time_pos;
    snapshot.coef_x = msg->coef_pos_x;
    snapshot.coef_y = msg->coef_pos_y;
    snapshot.coef_z = msg->coef_pos_z;
    bool new_generation = false;
    {
      std::lock_guard<std::mutex> lock(risk_trajectory_mutex_);
      if (snapshot.generation < latest_risk_trajectory_.generation)
        return;
      new_generation =
          snapshot.generation > latest_risk_trajectory_.generation;
      latest_risk_trajectory_ = std::move(snapshot);
    }
    ++risk_trajectory_messages_;
    if (new_generation) {
      ++risk_trajectory_unique_generations_;
      risk_trajectory_last_generation_.store(
          msg->trajectory_generation, std::memory_order_relaxed);
      recordCadence(risk_trajectory_first_ns_, risk_trajectory_last_ns_);
    }
  }

  void enqueueRiskCloud(
      const sensor_msgs::msg::PointCloud2::SharedPtr &msg,
      const RiskClock::time_point receive_time, const uint64_t sequence) {
    if (!risk_verdict_pub_)
      return;
    bool evaluation_due = true;
    {
      std::lock_guard<std::mutex> lock(risk_worker_mutex_);
      risk_cloud_window_.push_back(RiskCloudBatch{msg, receive_time, sequence});
      const double retain_s = std::max(options_.risk_accum_window_s,
                                       options_.risk_max_cloud_age_s) + 0.25;
      while (!risk_cloud_window_.empty() &&
             std::chrono::duration<double>(
                 receive_time - risk_cloud_window_.front().receive_time)
                     .count() > retain_s) {
        risk_cloud_window_.pop_front();
      }
      if (options_.risk_max_eval_hz > 0.0) {
        const auto period = std::chrono::duration<double>(
            1.0 / options_.risk_max_eval_hz);
        if (!risk_next_eval_time_) {
          risk_next_eval_time_ = receive_time +
              std::chrono::duration_cast<RiskClock::duration>(period);
        } else if (receive_time >= *risk_next_eval_time_) {
          do {
            *risk_next_eval_time_ +=
                std::chrono::duration_cast<RiskClock::duration>(period);
          } while (receive_time >= *risk_next_eval_time_);
        } else {
          evaluation_due = false;
        }
      }
      if (evaluation_due) {
        if (pending_risk_job_)
          ++risk_worker_overwrites_;
        pending_risk_job_ =
            RiskJob{sequence, cloudStampNs(*msg), receive_time};
      } else {
        ++risk_rate_limited_jobs_;
      }
    }
    if (evaluation_due) {
      risk_worker_cv_.notify_one();
    }
  }

  mars_quadrotor_msgs::msg::TrajectoryRiskVerdict calculateRiskVerdict(
      const RiskJob &job) {
    using Verdict = mars_quadrotor_msgs::msg::TrajectoryRiskVerdict;
    const auto compute_start = RiskClock::now();
    Verdict result;
    result.header.stamp = get_clock()->now();
    result.header.frame_id = "world";
    result.request_id = ++risk_request_sequence_;
    result.cloud_sequence = job.cloud_sequence;
    result.source_cloud_stamp_ns = job.source_cloud_stamp_ns;
    result.status = Verdict::EMPTY_TRAJECTORY;
    result.witness_tt = -1.0;
    result.minimum_distance_m = std::numeric_limits<double>::infinity();
    result.body_distance_m = std::numeric_limits<double>::infinity();
    result.end_distance_m = std::numeric_limits<double>::infinity();

    PolynomialSnapshot trajectory;
    {
      std::lock_guard<std::mutex> lock(risk_trajectory_mutex_);
      trajectory = latest_risk_trajectory_;
    }
    result.trajectory_generation = trajectory.generation;
    result.trajectory_start_wt = trajectory.start_wt;
    if (trajectory.empty()) {
      result.compute_ms = std::chrono::duration<double, std::milli>(
                              RiskClock::now() - compute_start)
                              .count();
      return result;
    }

    const double total_duration = trajectory.totalDuration();
    const double from_tt =
        std::clamp(nowSeconds() - trajectory.start_wt, 0.0, total_duration);
    const double to_tt =
        std::min(total_duration, from_tt + options_.risk_horizon_s);
    result.checked_from_tt = from_tt;
    result.checked_to_tt = to_tt;

    std::array<double, 3> crop_min;
    if (!trajectory.position(from_tt, crop_min)) {
      result.status = Verdict::OCCUPIED;
      result.compute_ms = std::chrono::duration<double, std::milli>(
                              RiskClock::now() - compute_start)
                              .count();
      return result;
    }
    std::array<double, 3> crop_max = crop_min;
    for (double tt = from_tt;;
         tt = std::min(to_tt, tt + options_.risk_sample_dt_s)) {
      std::array<double, 3> position;
      if (!trajectory.position(tt, position)) {
        result.status = Verdict::OCCUPIED;
        result.witness_tt = tt;
        break;
      }
      for (size_t axis = 0; axis < 3; ++axis) {
        crop_min[axis] = std::min(crop_min[axis], position[axis]);
        crop_max[axis] = std::max(crop_max[axis], position[axis]);
      }
      if (tt >= to_tt)
        break;
    }
    for (size_t axis = 0; axis < 3; ++axis) {
      crop_min[axis] -= options_.risk_clearance_m;
      crop_max[axis] += options_.risk_clearance_m;
    }

    std::deque<RiskCloudBatch> window;
    {
      std::lock_guard<std::mutex> lock(risk_worker_mutex_);
      window = risk_cloud_window_;
    }
    auto cloud = std::make_shared<pcl::PointCloud<pcl::PointXYZ>>();
    std::unordered_set<int64_t> seen_voxels;
    const bool downsample = options_.risk_voxel_m > 0.0;
    const double voxel = downsample ? std::max(0.005, options_.risk_voxel_m)
                                    : 1.0;
    RiskClock::time_point latest_receive{};
    for (const auto &batch : window) {
      const double age_at_cutoff = std::chrono::duration<double>(
                                       job.cutoff_time - batch.receive_time)
                                       .count();
      if (age_at_cutoff < 0.0 ||
          age_at_cutoff > options_.risk_accum_window_s || !batch.cloud) {
        continue;
      }
      latest_receive = std::max(latest_receive, batch.receive_time);
      const auto &msg = *batch.cloud;
      result.source_point_count +=
          static_cast<uint64_t>(msg.width) * msg.height;
      const CloudFields fields = findCloudFields(msg);
      if (!fields.x || !fields.y || !fields.z || msg.point_step == 0)
        continue;
      const bool swap_bytes = msg.is_bigendian != hostIsBigEndian();
      for (uint32_t row = 0; row < msg.height; ++row) {
        const size_t row_base = static_cast<size_t>(row) * msg.row_step;
        for (uint32_t column = 0; column < msg.width; ++column) {
          const size_t offset =
              row_base + static_cast<size_t>(column) * msg.point_step;
          if (offset + msg.point_step > msg.data.size())
            continue;
          const uint8_t *point = msg.data.data() + offset;
          double x, y, z;
          if (!readField(point, *fields.x, swap_bytes, x) ||
              !readField(point, *fields.y, swap_bytes, y) ||
              !readField(point, *fields.z, swap_bytes, z) ||
              !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
              x < crop_min[0] || x > crop_max[0] || y < crop_min[1] ||
              y > crop_max[1] || z < crop_min[2] || z > crop_max[2]) {
            continue;
          }
          if (downsample &&
              !seen_voxels.insert(riskVoxelKey(x, y, z, voxel)).second) {
            continue;
          }
          cloud->push_back(pcl::PointXYZ(static_cast<float>(x),
                                         static_cast<float>(y),
                                         static_cast<float>(z)));
        }
      }
    }
    result.cropped_point_count = cloud->size();
    result.source_cloud_age_s = latest_receive.time_since_epoch().count() == 0
        ? std::numeric_limits<double>::infinity()
        : std::chrono::duration<double>(RiskClock::now() - latest_receive)
              .count();
    if (!std::isfinite(result.source_cloud_age_s) ||
        result.source_cloud_age_s < 0.0 ||
        result.source_cloud_age_s > options_.risk_max_cloud_age_s) {
      result.status = Verdict::STALE;
    } else if (result.source_point_count <
               static_cast<uint64_t>(options_.risk_min_points)) {
      result.status = Verdict::INSUFFICIENT_DATA;
    } else if (cloud->empty()) {
      result.status = Verdict::NO_HIT;
    } else {
      cloud->width = static_cast<uint32_t>(cloud->size());
      cloud->height = 1;
      cloud->is_dense = true;
      pcl::KdTreeFLANN<pcl::PointXYZ> tree;
      tree.setInputCloud(cloud);
      std::vector<int> indices(1);
      std::vector<float> squared_distances(1);
      bool first_sample = true;
      bool body_starts_inside = false;
      bool exited_clearance = false;
      double previous_distance = std::numeric_limits<double>::infinity();
      result.status = Verdict::NO_HIT;
      for (double tt = from_tt;;
           tt = std::min(to_tt, tt + options_.risk_sample_dt_s)) {
        std::array<double, 3> position;
        if (!trajectory.position(tt, position)) {
          result.status = Verdict::OCCUPIED;
          result.witness_tt = tt;
          break;
        }
        pcl::PointXYZ query(static_cast<float>(position[0]),
                            static_cast<float>(position[1]),
                            static_cast<float>(position[2]));
        if (tree.nearestKSearch(query, 1, indices, squared_distances) > 0) {
          const double distance =
              std::sqrt(std::max(0.0F, squared_distances.front()));
          result.minimum_distance_m =
              std::min(result.minimum_distance_m, distance);
          result.end_distance_m = distance;
          if (first_sample) {
            result.body_distance_m = distance;
            body_starts_inside = distance <= options_.risk_clearance_m;
            if (body_starts_inside) {
              result.witness_tt = tt;
              result.witness_position.x = position[0];
              result.witness_position.y = position[1];
              result.witness_position.z = position[2];
            }
          } else if (body_starts_inside && !exited_clearance &&
                     distance + options_.risk_egress_tolerance_m <
                         previous_distance) {
            result.status = Verdict::OCCUPIED;
          } else if (body_starts_inside && exited_clearance &&
                     distance <= options_.risk_clearance_m) {
            result.status = Verdict::OCCUPIED;
          } else if (!body_starts_inside &&
                     distance <= options_.risk_clearance_m) {
            result.status = Verdict::OCCUPIED;
          }
          if (result.status == Verdict::OCCUPIED) {
            result.witness_tt = tt;
            result.witness_position.x = position[0];
            result.witness_position.y = position[1];
            result.witness_position.z = position[2];
            break;
          }
          if (body_starts_inside && !exited_clearance &&
              distance > options_.risk_clearance_m +
                             options_.risk_egress_tolerance_m) {
            exited_clearance = true;
          }
          previous_distance = distance;
        }
        first_sample = false;
        if (tt >= to_tt)
          break;
      }
      if (result.status != Verdict::OCCUPIED && body_starts_inside) {
        const bool made_progress =
            std::isfinite(result.body_distance_m) &&
            std::isfinite(result.end_distance_m) &&
            result.end_distance_m - result.body_distance_m >=
                options_.risk_egress_min_progress_m;
        result.status = made_progress && exited_clearance ? Verdict::EGRESS
                                                          : Verdict::OCCUPIED;
      }
    }
    result.compute_ms = std::chrono::duration<double, std::milli>(
                            RiskClock::now() - compute_start)
                            .count();
    return result;
  }

  void riskWorkerLoop() {
    while (true) {
      RiskJob job;
      {
        std::unique_lock<std::mutex> lock(risk_worker_mutex_);
        risk_worker_cv_.wait(lock, [this]() {
          return risk_worker_stop_ || pending_risk_job_.has_value();
        });
        if (risk_worker_stop_)
          return;
        job = *pending_risk_job_;
        pending_risk_job_.reset();
      }
      auto verdict = calculateRiskVerdict(job);
      ++risk_verdict_messages_;
      recordCadence(risk_verdict_first_ns_, risk_verdict_last_ns_);
      rclcpp::SerializedMessage serialized_verdict;
      risk_verdict_serializer_.serialize_message(
          &verdict, &serialized_verdict);
      risk_verdict_payload_bytes_.fetch_add(
          serialized_verdict.size(), std::memory_order_relaxed);
      if (verdict.status ==
          mars_quadrotor_msgs::msg::TrajectoryRiskVerdict::OCCUPIED) {
        ++risk_occupied_verdicts_;
        RCLCPP_WARN(
            get_logger(),
            "[FRONTEND_RISK_VERDICT] request=%lu gen=%lu cloud=%lu "
            "status=OCCUPIED age=%.3fs min=%.4fm compute=%.3fms",
            static_cast<unsigned long>(verdict.request_id),
            static_cast<unsigned long>(verdict.trajectory_generation),
            static_cast<unsigned long>(verdict.cloud_sequence),
            verdict.source_cloud_age_s, verdict.minimum_distance_m,
            verdict.compute_ms);
      }
      const uint64_t compute_us = static_cast<uint64_t>(
          std::max(0.0, verdict.compute_ms) * 1000.0);
      risk_compute_us_sum_.fetch_add(compute_us, std::memory_order_relaxed);
      uint64_t previous_max =
          risk_compute_us_max_.load(std::memory_order_relaxed);
      while (previous_max < compute_us &&
             !risk_compute_us_max_.compare_exchange_weak(
                 previous_max, compute_us, std::memory_order_relaxed)) {
      }
      risk_verdict_pub_->publish(verdict);
    }
  }

  static size_t fieldByteSize(uint8_t datatype) {
    switch (datatype) {
    case sensor_msgs::msg::PointField::INT8:
    case sensor_msgs::msg::PointField::UINT8:
      return 1;
    case sensor_msgs::msg::PointField::INT16:
    case sensor_msgs::msg::PointField::UINT16:
      return 2;
    case sensor_msgs::msg::PointField::INT32:
    case sensor_msgs::msg::PointField::UINT32:
    case sensor_msgs::msg::PointField::FLOAT32:
      return 4;
    case sensor_msgs::msg::PointField::FLOAT64:
      return 8;
    default:
      return 0;
    }
  }

  static uint32_t packedPointStep(const sensor_msgs::msg::PointCloud2 &msg) {
    size_t point_step = 0;
    for (const auto &field : msg.fields) {
      point_step =
          std::max(point_step, static_cast<size_t>(field.offset) +
                                   fieldByteSize(field.datatype) * field.count);
    }
    if (point_step == 0 || point_step > std::numeric_limits<uint32_t>::max()) {
      return msg.point_step;
    }
    return static_cast<uint32_t>(point_step);
  }

  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
    const auto receive_time = RiskClock::now();
    const uint64_t cloud_sequence = ++cloud_input_callbacks_;
    recordCadence(cloud_input_first_ns_, cloud_input_last_ns_, receive_time);
    cloud_input_payload_bytes_.fetch_add(msg->data.size(),
                                         std::memory_order_relaxed);
    enqueueRiskCloud(msg, receive_time, cloud_sequence);
    if (guard_cloud_observer_) {
      guard_cloud_observer_(msg);
      ++in_process_guard_handoffs_;
    }
    {
      std::lock_guard<std::mutex> lock(cloud_queue_mutex_);
      if (pending_cloud_)
        ++cloud_worker_overwrites_;
      pending_cloud_ = msg;
    }
    cloud_queue_cv_.notify_one();
  }

  void cloudWorkerLoop() {
    while (true) {
      sensor_msgs::msg::PointCloud2::SharedPtr msg;
      {
        std::unique_lock<std::mutex> lock(cloud_queue_mutex_);
        cloud_queue_cv_.wait(lock, [this]() {
          return cloud_worker_stop_ || static_cast<bool>(pending_cloud_);
        });
        if (cloud_worker_stop_)
          return;
        msg = std::move(pending_cloud_);
        pending_cloud_.reset();
      }
      const auto filter_start = RiskClock::now();
      {
        std::lock_guard<std::mutex> state_lock(state_mutex_);
        processCloud(msg);
      }
      const uint64_t compute_us = static_cast<uint64_t>(
          std::chrono::duration<double, std::micro>(
              RiskClock::now() - filter_start)
              .count());
      filter_compute_us_sum_.fetch_add(compute_us,
                                       std::memory_order_relaxed);
      uint64_t previous_max =
          filter_compute_us_max_.load(std::memory_order_relaxed);
      while (previous_max < compute_us &&
             !filter_compute_us_max_.compare_exchange_weak(
                 previous_max, compute_us, std::memory_order_relaxed)) {
      }
    }
  }

  static sensor_msgs::msg::PointCloud2 packedCloudLike(
      const sensor_msgs::msg::PointCloud2 &msg) {
    sensor_msgs::msg::PointCloud2 output;
    output.header = msg.header;
    output.height = 1;
    output.fields = msg.fields;
    output.is_bigendian = msg.is_bigendian;
    // Match sensor_msgs_py.create_cloud(), which the prototype used: retain
    // declared field offsets but remove trailing transport padding.
    output.point_step = packedPointStep(msg);
    output.is_dense = true;
    return output;
  }

  static void appendPackedPoint(sensor_msgs::msg::PointCloud2 &output,
                                const sensor_msgs::msg::PointCloud2 &input,
                                const uint8_t *point) {
    const size_t output_offset = output.data.size();
    output.data.resize(output_offset + output.point_step, 0);
    uint8_t *destination = output.data.data() + output_offset;
    for (const auto &field : input.fields) {
      const size_t byte_count = fieldByteSize(field.datatype) * field.count;
      if (byte_count == 0 || field.offset + byte_count > input.point_step ||
          field.offset + byte_count > output.point_step) {
        continue;
      }
      std::memcpy(destination + field.offset, point + field.offset,
                  byte_count);
    }
  }

  void publishGuardWitness(
      const sensor_msgs::msg::PointCloud2::SharedPtr &msg) {
    if (!guard_witness_pub_)
      return;
    ++guard_witness_source_frames_;
    if (!drone_) {
      ++guard_witness_missing_odom_frames_;
      return;
    }
    const CloudFields fields = findCloudFields(*msg);
    if (!fields.x || !fields.y || !fields.z || msg->point_step == 0) {
      ++guard_witness_invalid_cloud_frames_;
      RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 5000,
          "guard witness source lacks float x/y/z fields; skipping it");
      return;
    }

    const bool swap_bytes = msg->is_bigendian != hostIsBigEndian();
    const double radius_sq = options_.guard_witness_radius_m *
                             options_.guard_witness_radius_m;
    const uint64_t input_points =
        static_cast<uint64_t>(msg->width) * msg->height;
    sensor_msgs::msg::PointCloud2 witness = packedCloudLike(*msg);
    witness.data.reserve(
        static_cast<size_t>(input_points / 2) * witness.point_step);
    uint64_t witness_points = 0;
    for (uint32_t row = 0; row < msg->height; ++row) {
      const size_t row_base = static_cast<size_t>(row) * msg->row_step;
      for (uint32_t column = 0; column < msg->width; ++column) {
        const size_t offset =
            row_base + static_cast<size_t>(column) * msg->point_step;
        if (offset + msg->point_step > msg->data.size())
          continue;
        const uint8_t *point = msg->data.data() + offset;
        double x, y, z;
        if (!readField(point, *fields.x, swap_bytes, x) ||
            !readField(point, *fields.y, swap_bytes, y) ||
            !readField(point, *fields.z, swap_bytes, z) || !std::isfinite(x) ||
            !std::isfinite(y) || !std::isfinite(z)) {
          continue;
        }
        const double dx = x - (*drone_)[0];
        const double dy = y - (*drone_)[1];
        const double dz = z - (*drone_)[2];
        if (dx * dx + dy * dy + dz * dz > radius_sq)
          continue;
        appendPackedPoint(witness, *msg, point);
        ++witness_points;
      }
    }
    witness.width = static_cast<uint32_t>(witness_points);
    witness.row_step = witness.width * witness.point_step;
    guard_witness_points_ += witness_points;
    guard_witness_payload_bytes_ += witness.data.size();
    ++guard_witness_published_frames_;
    guard_witness_pub_->publish(witness);
  }

  void publishFilteredCloud(const sensor_msgs::msg::PointCloud2 &msg) {
    cloud_pub_->publish(msg);
    ++cloud_publish_events_;
    recordCadence(cloud_publish_first_ns_, cloud_publish_last_ns_);
  }

  void processCloud(const sensor_msgs::msg::PointCloud2::SharedPtr &msg) {
    const double now = nowSeconds();
    const bool state_changed =
        updateRecoveryBurst(now) | updateReplanGuardBurst(now) |
        updateTrajectoryGuardHold(now);
    if (state_changed)
      publishState();
    ++frames_;
    const uint64_t input_points =
        static_cast<uint64_t>(msg->width) * msg->height;
    processed_input_payload_bytes_ += msg->data.size();
    input_points_ += input_points;
    total_points_ += input_points;
    // This bounded 360-degree stream is independent of the angular/map
    // publication decision below. In particular, Adaptive rate limiting or a
    // fixed Sector crop must never make the guard witness disappear.
    publishGuardWitness(msg);
    if (statefulMode() && armed_)
      ++armed_frames_;
    const bool effective_open = effectiveFullOpen();
    if (effective_open) {
      ++open_frames_;
      open_input_points_ += input_points;
    }
    if (replan_guard_open_)
      ++replan_guard_open_frames_;
    if (trajectory_guard_open_)
      ++trajectory_guard_open_frames_;
    if (trajectory_guard_active_) {
      ++trajectory_guard_active_frames_;
    } else if (trajectory_guard_open_) {
      ++trajectory_guard_hold_only_frames_;
    }
    if (last_map_commit_rx_s_) {
      const double commit_age_s = std::max(0.0, now - *last_map_commit_rx_s_);
      map_commit_age_sum_s_ += commit_age_s;
      ++map_commit_age_samples_;
      map_commit_age_max_s_ = std::max(map_commit_age_max_s_, commit_age_s);
    }
    const PublishDecision publish_decision = publicationDecision(now);
    if (publish_decision == PublishDecision::DROP)
      return;
    const bool commit_refresh =
        publish_decision == PublishDecision::COMMIT_REFRESH;
    const bool pre_stale_full_refresh =
        publish_decision == PublishDecision::PRE_STALE_FULL_REFRESH;
    if (commit_refresh)
      ++commit_refresh_frames_;
    ++published_frames_;
    if (trajectory_guard_active_) {
      ++trajectory_guard_active_published_frames_;
    } else if (trajectory_guard_open_) {
      ++trajectory_guard_hold_only_published_frames_;
    }

    const bool bounded_full_open =
        options_.mode == "adaptive" && effective_open && !commit_refresh &&
        !trajectory_guard_unbounded_refresh_frame_ &&
        !slowdown_unbounded_refresh_frame_ &&
        options_.full_open_extra_max_points > 0;
    const bool passthrough = options_.mode == "full" || !drone_ ||
        pre_stale_full_refresh ||
        slowdown_unbounded_refresh_frame_ ||
        (effective_open && !commit_refresh && !bounded_full_open);
    if (pre_stale_full_refresh) {
      publishFullRefreshRequest(*msg, 1, now);
    } else if (trajectory_guard_unbounded_refresh_frame_) {
      publishFullRefreshRequest(*msg, 2, now);
      if (options_.test_drop_first_trajectory_guard_full_cloud &&
          test_dropped_trajectory_guard_full_clouds_ == 0) {
        ++test_dropped_trajectory_guard_full_clouds_;
        RCLCPP_WARN(
            get_logger(),
            "[TEST_FAULT_DROP_TRAJECTORY_GUARD_FULL_CLOUD] stamp_ns=%lu "
            "action=request_without_cloud",
            static_cast<unsigned long>(cloudStampNs(*msg)));
        return;
      }
    } else if (slowdown_unbounded_refresh_frame_) {
      publishFullRefreshRequest(*msg, 3, now);
    }
    if (passthrough) {
      kept_points_ += input_points;
      published_payload_bytes_ += msg->data.size();
      publishFilteredCloud(*msg);
      return;
    }

    const CloudFields fields = findCloudFields(*msg);
    if (!fields.x || !fields.y || !fields.z || msg->point_step == 0) {
      RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 5000,
          "cloud lacks float x/y/z fields; passing it through");
      kept_points_ += input_points;
      published_payload_bytes_ += msg->data.size();
      publishFilteredCloud(*msg);
      return;
    }
    const bool swap_bytes = msg->is_bigendian != hostIsBigEndian();
    const double center =
        ((options_.mode == "adaptive" || options_.mode == "velocity") &&
         velocity_yaw_)
            ? *velocity_yaw_
            : yaw_;
    const double heading_x = std::cos(center);
    const double heading_y = std::sin(center);
    const double near_radius =
        std::min(near_field_max_radius_m_,
                 options_.near_field_radius_m +
                     options_.near_field_speed_gain_s * latest_speed_mps_);
    max_effective_near_field_radius_m_ =
        std::max(max_effective_near_field_radius_m_, near_radius);
    const double near_radius_sq = near_radius * near_radius;

    sensor_msgs::msg::PointCloud2 output = packedCloudLike(*msg);
    // Match sensor_msgs_py.create_cloud(), which the prototype used: retain
    // the declared field offsets but remove any trailing transport padding.
    // MARSIM's input records are 32 bytes while x/y/z/intensity end at byte
    // 20.  Keeping the raw 32-byte stride made the nominally equivalent C++
    // path observably different at the ROG-Map subscription boundary.
    output.data.reserve(static_cast<size_t>(input_points) * output.point_step);

    uint64_t kept_this_frame = 0;
    std::vector<size_t> full_open_extra_offsets;
    if (bounded_full_open)
      full_open_extra_offsets.reserve(static_cast<size_t>(input_points / 2));
    for (uint32_t row = 0; row < msg->height; ++row) {
      const size_t row_base = static_cast<size_t>(row) * msg->row_step;
      for (uint32_t column = 0; column < msg->width; ++column) {
        const size_t offset =
            row_base + static_cast<size_t>(column) * msg->point_step;
        if (offset + msg->point_step > msg->data.size())
          continue;
        const uint8_t *point = msg->data.data() + offset;
        double x, y, z;
        if (!readField(point, *fields.x, swap_bytes, x) ||
            !readField(point, *fields.y, swap_bytes, y) ||
            !readField(point, *fields.z, swap_bytes, z) || !std::isfinite(x) ||
            !std::isfinite(y) || !std::isfinite(z)) {
          continue;
        }
        const double dx = x - (*drone_)[0];
        const double dy = y - (*drone_)[1];
        const double dz = z - (*drone_)[2];
        const double horizontal_sq = dx * dx + dy * dy;
        const bool in_sector = horizontal_sq == 0.0 ||
                               dx * heading_x + dy * heading_y >=
                                   std::sqrt(horizontal_sq) * half_angle_cos_;
        const bool near = options_.near_field_radius_m > 0.0 &&
                          dx * dx + dy * dy + dz * dz <= near_radius_sq;
        if (!in_sector && !near) {
          if (bounded_full_open)
            full_open_extra_offsets.push_back(offset);
          continue;
        }
        appendPackedPoint(output, *msg, point);
        ++kept_this_frame;
      }
    }
    if (bounded_full_open && !full_open_extra_offsets.empty()) {
      full_open_extra_candidates_ += full_open_extra_offsets.size();
      const size_t extra_to_keep = std::min(
          full_open_extra_offsets.size(),
          static_cast<size_t>(options_.full_open_extra_max_points));
      for (size_t i = 0; i < extra_to_keep; ++i) {
        const size_t selected = std::min(
            full_open_extra_offsets.size() - 1,
            static_cast<size_t>((static_cast<long double>(i) + 0.5L) *
                                full_open_extra_offsets.size() /
                                extra_to_keep));
        appendPackedPoint(
            output, *msg,
            msg->data.data() + full_open_extra_offsets[selected]);
      }
      kept_this_frame += extra_to_keep;
      full_open_extra_kept_ += extra_to_keep;
    }
    output.width = static_cast<uint32_t>(kept_this_frame);
    output.row_step = output.width * output.point_step;
    kept_points_ += kept_this_frame;
    published_payload_bytes_ += output.data.size();
    publishFilteredCloud(output);
  }

  void publishState() {
    observeEffectiveFullOpen(nowSeconds());
    std_msgs::msg::Bool full_open;
    full_open.data = effectiveFullOpen();
    full_open_pub_->publish(full_open);
    std_msgs::msg::Bool armed;
    armed.data = statefulMode() && armed_;
    armed_pub_->publish(armed);
  }

  void addJson(std::ostringstream &out, bool &first, const std::string &key,
               const std::string &value) const {
    if (!first)
      out << ",\n";
    first = false;
    out << "  " << jsonString(key) << ": " << value;
  }

  std::string statsJson() const {
    const double frame_denominator =
        static_cast<double>(std::max<uint64_t>(1, frames_));
    const double point_denominator =
        static_cast<double>(std::max<uint64_t>(1, input_points_));
    const double open_duty = options_.mode == "full"
                                 ? 100.0
                                 : 100.0 * open_frames_ / frame_denominator;
    const double open_point_duty =
        options_.mode == "full"
            ? 100.0
            : 100.0 * open_input_points_ / point_denominator;
    std::optional<double> first_open_duration;
    if (first_open_time_s_ && first_close_time_s_) {
      first_open_duration = rounded(*first_close_time_s_ - *first_open_time_s_);
    }
    std::ostringstream out;
    out << "{\n";
    bool first = true;
    auto string = [&](const std::string &key, const std::string &value) {
      addJson(out, first, key, jsonString(value));
    };
    auto number = [&](const std::string &key, double value) {
      addJson(out, first, key, jsonNumber(value));
    };
    auto integer = [&](const std::string &key, uint64_t value) {
      addJson(out, first, key, std::to_string(value));
    };
    auto boolean = [&](const std::string &key, bool value) {
      addJson(out, first, key, value ? "true" : "false");
    };
    auto optional = [&](const std::string &key,
                        const std::optional<double> &value) {
      addJson(out, first, key, jsonOptional(value));
    };
    auto array = [&](const std::string &key, const std::vector<double> &value) {
      addJson(out, first, key, jsonArray(value));
    };

    string("mode", options_.mode);
    string("implementation", "cpp");
    boolean("reliable_output", options_.reliable_output);
    number("half_angle_deg", rounded(options_.half_angle_deg, 1e3));
    number("stall_v", options_.stall_v);
    number("stall_t", options_.stall_t);
    number("resume_v", options_.resume_v);
    number("resume_t", options_.resume_t);
    number("slowdown_full_refresh_v", options_.slowdown_full_refresh_v);
    number("slowdown_full_refresh_rearm_v",
           options_.slowdown_full_refresh_rearm_v);
    boolean("slowdown_full_refresh_armed", slowdown_full_refresh_armed_);
    boolean("slowdown_full_refresh_pending", slowdown_full_refresh_pending_);
    integer("slowdown_full_refresh_triggers", slowdown_full_refresh_triggers_);
    integer("slowdown_full_refresh_frames", slowdown_full_refresh_frames_);
    boolean("slowdown_full_refresh_pending_ack",
            slowdown_pending_exact_ack_stamp_ns_.has_value());
    integer("slowdown_full_refresh_ack_count",
            slowdown_full_refresh_ack_count_);
    integer("slowdown_full_refresh_ack_committed_count",
            slowdown_full_refresh_ack_committed_count_);
    integer("slowdown_full_refresh_superseded_count",
            slowdown_full_refresh_superseded_count_);
    number("slowdown_full_refresh_ack_latency_mean_s",
           slowdown_full_refresh_ack_count_ > 0
               ? rounded(slowdown_full_refresh_ack_latency_sum_s_ /
                         slowdown_full_refresh_ack_count_)
               : 0.0);
    number("slowdown_full_refresh_ack_latency_max_s",
           rounded(slowdown_full_refresh_ack_latency_max_s_));
    number("velocity_yaw_update_v",
           (options_.mode == "velocity" || options_.mode == "adaptive")
               ? options_.resume_v
               : 0.2);
    integer("frames", frames_);
    const uint64_t cloud_input_count =
        cloud_input_callbacks_.load(std::memory_order_relaxed);
    integer("cloud_input_callbacks", cloud_input_count);
    number("cloud_input_span_s",
           cadenceSpanSeconds(cloud_input_first_ns_, cloud_input_last_ns_));
    number("cloud_input_hz",
           cadenceRateHz(cloud_input_count, cloud_input_first_ns_,
                         cloud_input_last_ns_));
    integer("cloud_worker_overwrites", cloud_worker_overwrites_.load());
    integer("cloud_input_payload_bytes",
            cloud_input_payload_bytes_.load(std::memory_order_relaxed));
    number("cloud_compute_ms_mean",
           frames_ == 0
               ? 0.0
               : filter_compute_us_sum_.load(std::memory_order_relaxed) /
                     (1000.0 * frames_));
    number("cloud_compute_ms_max",
           filter_compute_us_max_.load(std::memory_order_relaxed) / 1000.0);
    integer("in_process_guard_handoffs",
            in_process_guard_handoffs_.load(std::memory_order_relaxed));
    boolean("direct_input", options_.direct_input);
    string("risk_verdict_topic", options_.risk_verdict_topic);
    string("risk_trajectory_topic", options_.risk_trajectory_topic);
    number("risk_accum_window_s", options_.risk_accum_window_s);
    number("risk_clearance_m", options_.risk_clearance_m);
    number("risk_horizon_s", options_.risk_horizon_s);
    number("risk_sample_dt_s", options_.risk_sample_dt_s);
    integer("risk_min_points",
            static_cast<uint64_t>(options_.risk_min_points));
    number("risk_voxel_m", options_.risk_voxel_m);
    number("risk_max_cloud_age_s", options_.risk_max_cloud_age_s);
    number("risk_max_eval_hz", options_.risk_max_eval_hz);
    integer("risk_worker_overwrites",
            risk_worker_overwrites_.load(std::memory_order_relaxed));
    integer("risk_rate_limited_jobs",
            risk_rate_limited_jobs_.load(std::memory_order_relaxed));
    integer("risk_trajectory_messages",
            risk_trajectory_messages_.load(std::memory_order_relaxed));
    const uint64_t risk_trajectory_generation_count =
        risk_trajectory_unique_generations_.load(std::memory_order_relaxed);
    integer("risk_trajectory_unique_generations",
            risk_trajectory_generation_count);
    integer("risk_trajectory_last_generation",
            risk_trajectory_last_generation_.load(
                std::memory_order_relaxed));
    number("risk_trajectory_generation_span_s",
           cadenceSpanSeconds(risk_trajectory_first_ns_,
                              risk_trajectory_last_ns_));
    number("risk_trajectory_generation_hz",
           cadenceRateHz(risk_trajectory_generation_count,
                         risk_trajectory_first_ns_,
                         risk_trajectory_last_ns_));
    integer("risk_invalid_trajectory_messages",
            risk_invalid_trajectory_messages_.load(
                std::memory_order_relaxed));
    const uint64_t risk_verdict_count =
        risk_verdict_messages_.load(std::memory_order_relaxed);
    integer("risk_verdict_messages", risk_verdict_count);
    number("risk_verdict_span_s",
           cadenceSpanSeconds(risk_verdict_first_ns_,
                              risk_verdict_last_ns_));
    number("risk_verdict_hz",
           cadenceRateHz(risk_verdict_count, risk_verdict_first_ns_,
                         risk_verdict_last_ns_));
    integer("risk_verdict_payload_bytes",
            risk_verdict_payload_bytes_.load(std::memory_order_relaxed));
    integer("risk_occupied_verdicts",
            risk_occupied_verdicts_.load(std::memory_order_relaxed));
    number("risk_compute_ms_mean",
           risk_verdict_count == 0
               ? 0.0
               : risk_compute_us_sum_.load(std::memory_order_relaxed) /
                     (1000.0 * risk_verdict_count));
    number("risk_compute_ms_max",
           risk_compute_us_max_.load(std::memory_order_relaxed) / 1000.0);
    integer("processed_input_payload_bytes", processed_input_payload_bytes_);
    integer("published_frames", published_frames_);
    const uint64_t cloud_publish_count =
        cloud_publish_events_.load(std::memory_order_relaxed);
    integer("cloud_publish_events", cloud_publish_count);
    number("cloud_publish_span_s",
           cadenceSpanSeconds(cloud_publish_first_ns_,
                              cloud_publish_last_ns_));
    number("cloud_publish_hz",
           cadenceRateHz(cloud_publish_count, cloud_publish_first_ns_,
                         cloud_publish_last_ns_));
    integer("published_payload_bytes", published_payload_bytes_);
    integer("rate_limited_frames", rate_limited_frames_);
    string("guard_witness_topic", options_.guard_witness_topic);
    number("guard_witness_radius_m", options_.guard_witness_radius_m);
    integer("guard_witness_source_frames", guard_witness_source_frames_);
    integer("guard_witness_missing_odom_frames",
            guard_witness_missing_odom_frames_);
    integer("guard_witness_invalid_cloud_frames",
            guard_witness_invalid_cloud_frames_);
    integer("guard_witness_published_frames",
            guard_witness_published_frames_);
    integer("guard_witness_points", guard_witness_points_);
    integer("guard_witness_payload_bytes", guard_witness_payload_bytes_);
    number("max_publish_hz", options_.max_publish_hz);
    string("map_commit_topic", options_.map_commit_topic);
    number("map_commit_refresh_age_s",
           options_.map_commit_refresh_age_s);
    number("map_commit_refresh_min_interval_s",
           options_.map_commit_refresh_min_interval_s);
    number("map_commit_pre_stale_full_age_s",
           options_.map_commit_pre_stale_full_age_s);
    number("map_commit_pre_stale_ack_retry_age_s",
           options_.map_commit_pre_stale_ack_retry_age_s);
    boolean("full_refresh_generation_ack_en",
            options_.full_refresh_generation_ack_en);
    string("map_process_ack_topic", options_.map_process_ack_topic);
    string("full_refresh_request_topic",
           options_.full_refresh_request_topic);
    integer("map_commit_status_count", map_commit_status_count_);
    integer("map_commit_version", last_map_commit_version_);
    number("map_commit_span_s",
           cadenceSpanSeconds(map_commit_first_ns_, map_commit_last_ns_));
    number("map_commit_hz",
           cadenceRateHz(map_commit_status_count_, map_commit_first_ns_,
                         map_commit_last_ns_));
    integer("commit_refresh_frames", commit_refresh_frames_);
    integer("pre_stale_full_refresh_frames",
            pre_stale_full_refresh_frames_);
    integer("pre_stale_full_refresh_ack_count",
            pre_stale_full_refresh_ack_count_);
    boolean("pre_stale_full_refresh_pending_ack",
            !pre_stale_pending_exact_ack_.empty());
    integer("pre_stale_full_refresh_pending_ack_count",
            pre_stale_pending_exact_ack_.size());
    integer("pre_stale_full_refresh_pending_ack_max",
            pre_stale_full_refresh_pending_ack_max_);
    integer("pre_stale_full_refresh_ack_committed_count",
            pre_stale_full_refresh_ack_committed_count_);
    integer("pre_stale_full_refresh_superseded_count",
            pre_stale_full_refresh_superseded_count_);
    integer("pre_stale_full_refresh_ack_retry_frames",
            pre_stale_full_refresh_ack_retry_frames_);
    integer("pre_stale_full_refresh_ack_retry_suppressed_frames",
            pre_stale_full_refresh_ack_retry_suppressed_frames_);
    integer("pre_stale_full_refresh_version_advance_count",
            pre_stale_full_refresh_version_advance_count_);
    boolean("pre_stale_full_refresh_pending_version_advance",
            pre_stale_full_refresh_pending_version_advance_);
    integer("full_refresh_request_count", full_refresh_request_count_);
    integer("full_refresh_request_sequence", full_refresh_request_seq_);
    integer("full_refresh_duplicate_stamp_count",
            full_refresh_duplicate_stamp_count_);
    integer("map_process_ack_status_count", map_process_ack_status_count_);
    integer("map_process_ack_malformed_count",
            map_process_ack_malformed_count_);
    integer("last_map_process_ack_scan_seq",
            last_map_process_ack_scan_seq_);
    integer("last_map_process_ack_stamp_ns",
            last_map_process_ack_stamp_ns_);
    integer("last_map_process_ack_version",
            last_map_process_ack_version_);
    integer("pre_stale_full_refresh_same_version_suppressed_frames",
            pre_stale_full_refresh_same_version_suppressed_frames_);
    number("pre_stale_full_refresh_trigger_age_mean_s",
           pre_stale_full_refresh_frames_ > 0
               ? rounded(pre_stale_full_refresh_trigger_age_sum_s_ /
                         pre_stale_full_refresh_frames_)
               : 0.0);
    number("pre_stale_full_refresh_trigger_age_max_s",
           rounded(pre_stale_full_refresh_trigger_age_max_s_));
    number("pre_stale_full_refresh_ack_latency_mean_s",
           pre_stale_full_refresh_ack_count_ > 0
               ? rounded(pre_stale_full_refresh_ack_latency_sum_s_ /
                         pre_stale_full_refresh_ack_count_)
               : 0.0);
    number("pre_stale_full_refresh_ack_latency_max_s",
           rounded(pre_stale_full_refresh_ack_latency_max_s_));
    number("map_commit_age_mean_s",
           map_commit_age_samples_ > 0
               ? rounded(map_commit_age_sum_s_ / map_commit_age_samples_)
               : 0.0);
    number("map_commit_age_max_s", rounded(map_commit_age_max_s_));
    integer("full_open_extra_max_points",
            options_.full_open_extra_max_points);
    integer("full_open_extra_candidates", full_open_extra_candidates_);
    integer("full_open_extra_kept", full_open_extra_kept_);
    number("publish_duty_pct",
           rounded(100.0 * published_frames_ / frame_denominator, 1e3));
    integer("input_points", input_points_);
    integer("kept_points", kept_points_);
    number("kept_pct", rounded(100.0 * kept_points_ / point_denominator, 1e3));
    boolean("armed", armed_);
    number("armed_duty_pct",
           rounded(100.0 * armed_frames_ / frame_denominator, 1e3));
    boolean("open", effectiveFullOpen());
    boolean("recovery_active", recovery_active_);
    number("open_burst_s", options_.open_burst_s);
    number("open_cooldown_s", options_.open_cooldown_s);
    number("near_field_radius_m", options_.near_field_radius_m);
    number("near_field_speed_gain_s", options_.near_field_speed_gain_s);
    number("near_field_max_radius_m", near_field_max_radius_m_);
    number("max_effective_near_field_radius_m",
           rounded(max_effective_near_field_radius_m_));
    number("open_duty_pct", rounded(open_duty, 1e3));
    number("open_point_duty_pct", rounded(open_point_duty, 1e3));
    integer("arm_transitions", arm_transitions_);
    integer("open_transitions", open_transitions_);
    integer("close_transitions", close_transitions_);
    array("arm_transition_times_s", arm_transition_times_s_);
    array("open_transition_times_s", open_transition_times_s_);
    array("close_transition_times_s", close_transition_times_s_);
    optional("first_transition_time_s", first_transition_time_s_);
    optional("first_stall_candidate_time_s", first_stall_candidate_time_s_);
    optional("first_open_stall_start_time_s", first_open_stall_start_time_s_);
    optional("first_open_delay_s", first_open_delay_s_);
    optional("first_arm_time_s", first_arm_time_s_);
    optional("first_open_time_s", first_open_time_s_);
    optional("first_close_time_s", first_close_time_s_);
    optional("first_open_duration_s", first_open_duration);
    integer("stall_candidate_count", stall_candidate_count_);
    number("max_stall_candidate_duration_s",
           rounded(max_stall_candidate_duration_s_));
    optional("min_armed_closed_speed_mps",
             min_armed_closed_speed_mps_
                 ? std::optional<double>(rounded(*min_armed_closed_speed_mps_))
                 : std::nullopt);
    boolean("replan_guard_en", options_.replan_guard_en);
    boolean("replan_guard_bounded", options_.bounded_replan_guard);
    boolean("replan_guard_active", replan_guard_active_);
    number("replan_guard_burst_s",
           options_.bounded_replan_guard ? replan_guard_burst_s_ : 0.0);
    number("replan_guard_cooldown_s",
           options_.bounded_replan_guard ? replan_guard_cooldown_s_ : 0.0);
    integer("replan_fail_streak_open", options_.replan_fail_streak_open);
    integer("replan_ok_streak_close", options_.replan_ok_streak_close);
    boolean("replan_guard_open", replan_guard_open_);
    integer("replan_guard_open_transitions", replan_guard_open_transitions_);
    integer("replan_guard_close_transitions", replan_guard_close_transitions_);
    integer("effective_full_open_transitions",
            effective_full_open_transitions_);
    integer("effective_full_close_transitions",
            effective_full_close_transitions_);
    number("replan_guard_open_duty_pct",
           rounded(100.0 * replan_guard_open_frames_ / frame_denominator, 1e3));
    integer("replan_status_count", replan_status_count_);
    integer("replan_fail_count", replan_fail_count_);
    integer("max_replan_fail_streak", max_replan_fail_streak_);
    optional("first_replan_guard_open_time_s", first_replan_guard_open_time_s_);
    optional("first_effective_full_open_time_s",
             first_effective_full_open_time_s_);
    string("trajectory_guard_topic", options_.trajectory_guard_topic);
    number("trajectory_guard_hold_s", options_.trajectory_guard_hold_s);
    number("trajectory_guard_active_max_publish_hz",
           options_.trajectory_guard_active_max_publish_hz);
    number("trajectory_guard_ack_retry_age_s",
           options_.trajectory_guard_ack_retry_age_s);
    boolean("test_drop_first_trajectory_guard_full_cloud",
            options_.test_drop_first_trajectory_guard_full_cloud);
    integer("test_dropped_trajectory_guard_full_clouds",
            test_dropped_trajectory_guard_full_clouds_);
    boolean("trajectory_guard_active", trajectory_guard_active_);
    boolean("trajectory_guard_open", trajectory_guard_open_);
    integer("trajectory_guard_status_count", trajectory_guard_status_count_);
    integer("trajectory_guard_active_count", trajectory_guard_active_count_);
    integer("trajectory_guard_open_transitions",
            trajectory_guard_open_transitions_);
    integer("trajectory_guard_close_transitions",
            trajectory_guard_close_transitions_);
    integer("trajectory_guard_refresh_frames",
            trajectory_guard_refresh_frames_);
    boolean("trajectory_guard_full_refresh_pending_ack",
            trajectory_guard_pending_exact_ack_stamp_ns_.has_value());
    integer("trajectory_guard_full_refresh_pending_ack_max",
            trajectory_guard_full_refresh_pending_ack_max_);
    integer("trajectory_guard_full_refresh_ack_count",
            trajectory_guard_full_refresh_ack_count_);
    integer("trajectory_guard_full_refresh_ack_committed_count",
            trajectory_guard_full_refresh_ack_committed_count_);
    integer("trajectory_guard_full_refresh_superseded_count",
            trajectory_guard_full_refresh_superseded_count_);
    integer("trajectory_guard_full_refresh_ack_retry_frames",
            trajectory_guard_full_refresh_ack_retry_frames_);
    integer("trajectory_guard_full_refresh_abandoned_count",
            trajectory_guard_full_refresh_abandoned_count_);
    number("trajectory_guard_full_refresh_ack_latency_mean_s",
           trajectory_guard_full_refresh_ack_count_ > 0
               ? rounded(trajectory_guard_full_refresh_ack_latency_sum_s_ /
                         trajectory_guard_full_refresh_ack_count_)
               : 0.0);
    number("trajectory_guard_full_refresh_ack_latency_max_s",
           rounded(trajectory_guard_full_refresh_ack_latency_max_s_));
    number("trajectory_guard_open_duty_pct",
           rounded(100.0 * trajectory_guard_open_frames_ /
                   frame_denominator, 1e3));
    integer("trajectory_guard_active_frames",
            trajectory_guard_active_frames_);
    integer("trajectory_guard_hold_only_frames",
            trajectory_guard_hold_only_frames_);
    integer("trajectory_guard_active_published_frames",
            trajectory_guard_active_published_frames_);
    integer("trajectory_guard_hold_only_published_frames",
            trajectory_guard_hold_only_published_frames_);
    number("trajectory_guard_active_duty_pct",
           rounded(100.0 * trajectory_guard_active_frames_ /
                   frame_denominator, 1e3));
    number("trajectory_guard_hold_only_duty_pct",
           rounded(100.0 * trajectory_guard_hold_only_frames_ /
                   frame_denominator, 1e3));
    optional("first_trajectory_guard_open_time_s",
             first_trajectory_guard_open_time_s_);
    out << "\n}\n";
    return out.str();
  }

  void writeStats() const {
    if (options_.stats_json.empty())
      return;
    const std::string temporary = options_.stats_json + ".tmp";
    {
      std::ofstream stream(temporary, std::ios::trunc);
      if (!stream)
        return;
      stream << statsJson();
      if (!stream)
        return;
    }
    std::rename(temporary.c_str(), options_.stats_json.c_str());
  }

  void report() {
    std::lock_guard<std::mutex> lock(state_mutex_);
    if (frames_ == 0)
      return;
    const double kept_pct =
        100.0 * kept_points_ /
        static_cast<double>(std::max<uint64_t>(1, input_points_));
    RCLCPP_INFO(
        get_logger(),
        "frames=%lu published=%lu kept %.1f%% (%lu/%lu pts/input-frame)",
        static_cast<unsigned long>(frames_),
        static_cast<unsigned long>(published_frames_), kept_pct,
        static_cast<unsigned long>(kept_points_ /
                                   std::max<uint64_t>(1, frames_)),
        static_cast<unsigned long>(total_points_ /
                                   std::max<uint64_t>(1, frames_)));
    writeStats();
  }

  Options options_;
  double half_angle_rad_;
  double half_angle_cos_;
  double near_field_max_radius_m_;
  double replan_guard_burst_s_;
  double replan_guard_cooldown_s_;

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_sub_;
  rclcpp::Subscription<mars_quadrotor_msgs::msg::PolynomialTrajectory>::SharedPtr
      trajectory_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr replan_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr trajectory_guard_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt64>::SharedPtr map_commit_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt64MultiArray>::SharedPtr
      map_process_ack_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
  rclcpp::Publisher<mars_quadrotor_msgs::msg::TrajectoryRiskVerdict>::SharedPtr
      risk_verdict_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr
      guard_witness_pub_;
  rclcpp::Publisher<std_msgs::msg::UInt64MultiArray>::SharedPtr
      full_refresh_request_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr full_open_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr armed_pub_;
  rclcpp::TimerBase::SharedPtr state_timer_;
  rclcpp::TimerBase::SharedPtr report_timer_;

  // The input is best-effort depth-1 by design. Keep its DDS callback cheap
  // and move point filtering plus reliable publication to a latest-only
  // worker, so slow output/map work is removed from the cloud subscription
  // callback and pending raw input remains bounded. All filter state stays
  // serialized under state_mutex_, preserving the former single-threaded
  // transition order.
  mutable std::mutex state_mutex_;
  std::mutex cloud_queue_mutex_;
  std::condition_variable cloud_queue_cv_;
  sensor_msgs::msg::PointCloud2::SharedPtr pending_cloud_;
  std::thread cloud_worker_;
  bool cloud_worker_stop_{false};
  std::atomic<uint64_t> cloud_input_callbacks_{0};
  std::atomic<int64_t> cloud_input_first_ns_{0};
  std::atomic<int64_t> cloud_input_last_ns_{0};
  std::atomic<uint64_t> cloud_worker_overwrites_{0};
  std::atomic<uint64_t> cloud_input_payload_bytes_{0};
  std::atomic<uint64_t> filter_compute_us_sum_{0};
  std::atomic<uint64_t> filter_compute_us_max_{0};
  std::atomic<uint64_t> in_process_guard_handoffs_{0};
  native_sector::GuardCloudObserver guard_cloud_observer_;

  std::mutex risk_trajectory_mutex_;
  PolynomialSnapshot latest_risk_trajectory_;
  std::mutex risk_worker_mutex_;
  std::condition_variable risk_worker_cv_;
  std::deque<RiskCloudBatch> risk_cloud_window_;
  std::optional<RiskJob> pending_risk_job_;
  std::optional<RiskClock::time_point> risk_next_eval_time_;
  std::thread risk_worker_;
  bool risk_worker_stop_{false};
  std::atomic<uint64_t> risk_worker_overwrites_{0};
  std::atomic<uint64_t> risk_rate_limited_jobs_{0};
  std::atomic<uint64_t> risk_trajectory_messages_{0};
  std::atomic<uint64_t> risk_trajectory_unique_generations_{0};
  std::atomic<uint64_t> risk_trajectory_last_generation_{0};
  std::atomic<int64_t> risk_trajectory_first_ns_{0};
  std::atomic<int64_t> risk_trajectory_last_ns_{0};
  std::atomic<uint64_t> risk_invalid_trajectory_messages_{0};
  std::atomic<uint64_t> risk_request_sequence_{0};
  std::atomic<uint64_t> risk_verdict_messages_{0};
  std::atomic<int64_t> risk_verdict_first_ns_{0};
  std::atomic<int64_t> risk_verdict_last_ns_{0};
  std::atomic<uint64_t> risk_verdict_payload_bytes_{0};
  std::atomic<uint64_t> risk_occupied_verdicts_{0};
  rclcpp::Serialization<
      mars_quadrotor_msgs::msg::TrajectoryRiskVerdict>
      risk_verdict_serializer_;
  std::atomic<uint64_t> risk_compute_us_sum_{0};
  std::atomic<uint64_t> risk_compute_us_max_{0};

  std::optional<std::array<double, 3>> drone_;
  double yaw_{0.0};
  std::optional<double> velocity_yaw_;
  double latest_speed_mps_{0.0};
  uint64_t kept_points_{0};
  uint64_t total_points_{0};
  uint64_t frames_{0};
  uint64_t published_frames_{0};
  std::atomic<uint64_t> cloud_publish_events_{0};
  std::atomic<int64_t> cloud_publish_first_ns_{0};
  std::atomic<int64_t> cloud_publish_last_ns_{0};
  uint64_t rate_limited_frames_{0};
  uint64_t input_points_{0};
  uint64_t processed_input_payload_bytes_{0};
  uint64_t published_payload_bytes_{0};
  uint64_t guard_witness_source_frames_{0};
  uint64_t guard_witness_missing_odom_frames_{0};
  uint64_t guard_witness_invalid_cloud_frames_{0};
  uint64_t guard_witness_published_frames_{0};
  uint64_t guard_witness_points_{0};
  uint64_t guard_witness_payload_bytes_{0};
  std::optional<double> next_publish_time_s_;
  std::optional<double> last_map_commit_rx_s_;
  std::optional<double> last_commit_refresh_publish_s_;
  std::optional<uint64_t> last_full_refresh_source_version_;
  std::optional<uint64_t> pre_stale_full_refresh_source_version_;
  std::optional<uint64_t>
      pre_stale_full_refresh_ack_retry_source_version_;
  std::unordered_map<uint64_t, PendingFullRefresh>
      pre_stale_pending_exact_ack_;
  uint64_t map_commit_status_count_{0};
  uint64_t last_map_commit_version_{0};
  std::atomic<int64_t> map_commit_first_ns_{0};
  std::atomic<int64_t> map_commit_last_ns_{0};
  uint64_t commit_refresh_frames_{0};
  uint64_t pre_stale_full_refresh_frames_{0};
  uint64_t pre_stale_full_refresh_ack_count_{0};
  uint64_t pre_stale_full_refresh_ack_committed_count_{0};
  uint64_t pre_stale_full_refresh_superseded_count_{0};
  uint64_t pre_stale_full_refresh_ack_retry_frames_{0};
  uint64_t pre_stale_full_refresh_ack_retry_suppressed_frames_{0};
  uint64_t pre_stale_full_refresh_version_advance_count_{0};
  bool pre_stale_full_refresh_pending_version_advance_{false};
  uint64_t pre_stale_full_refresh_pending_ack_max_{0};
  uint64_t full_refresh_request_count_{0};
  uint64_t full_refresh_request_seq_{0};
  uint64_t full_refresh_duplicate_stamp_count_{0};
  uint64_t map_process_ack_status_count_{0};
  uint64_t map_process_ack_malformed_count_{0};
  uint64_t last_map_process_ack_scan_seq_{0};
  uint64_t last_map_process_ack_stamp_ns_{0};
  uint64_t last_map_process_ack_version_{0};
  uint64_t pre_stale_full_refresh_same_version_suppressed_frames_{0};
  double pre_stale_full_refresh_trigger_age_sum_s_{0.0};
  double pre_stale_full_refresh_trigger_age_max_s_{0.0};
  double pre_stale_full_refresh_ack_latency_sum_s_{0.0};
  double pre_stale_full_refresh_ack_latency_max_s_{0.0};
  uint64_t map_commit_age_samples_{0};
  double map_commit_age_sum_s_{0.0};
  double map_commit_age_max_s_{0.0};
  uint64_t full_open_extra_candidates_{0};
  uint64_t full_open_extra_kept_{0};

  bool recovery_active_{false};
  bool effective_recovery_open_{false};
  std::optional<double> open_burst_until_s_;
  std::optional<double> next_open_burst_s_;
  bool armed_{false};
  std::optional<double> slow_since_s_;
  std::optional<double> fast_since_s_;
  uint64_t armed_frames_{0};
  uint64_t open_frames_{0};
  uint64_t open_input_points_{0};
  uint64_t arm_transitions_{0};
  uint64_t open_transitions_{0};
  uint64_t close_transitions_{0};
  std::vector<double> arm_transition_times_s_;
  std::vector<double> open_transition_times_s_;
  std::vector<double> close_transition_times_s_;
  std::optional<double> first_transition_time_s_;
  std::optional<double> first_stall_candidate_time_s_;
  std::optional<double> first_open_stall_start_time_s_;
  std::optional<double> first_open_delay_s_;
  std::optional<double> first_arm_time_s_;
  std::optional<double> first_open_time_s_;
  std::optional<double> first_close_time_s_;
  uint64_t stall_candidate_count_{0};
  double max_stall_candidate_duration_s_{0.0};
  std::optional<double> min_armed_closed_speed_mps_;
  double max_effective_near_field_radius_m_{options_.near_field_radius_m};

  bool slowdown_full_refresh_armed_{false};
  bool slowdown_full_refresh_pending_{false};
  bool slowdown_unbounded_refresh_frame_{false};
  uint64_t slowdown_full_refresh_triggers_{0};
  uint64_t slowdown_full_refresh_frames_{0};
  std::optional<uint64_t> slowdown_pending_exact_ack_stamp_ns_;
  std::optional<double> slowdown_pending_exact_ack_send_s_;
  uint64_t slowdown_full_refresh_ack_count_{0};
  uint64_t slowdown_full_refresh_ack_committed_count_{0};
  uint64_t slowdown_full_refresh_superseded_count_{0};
  double slowdown_full_refresh_ack_latency_sum_s_{0.0};
  double slowdown_full_refresh_ack_latency_max_s_{0.0};

  bool replan_guard_active_{false};
  bool replan_guard_open_{false};
  std::optional<double> replan_guard_burst_until_s_;
  std::optional<double> replan_guard_next_burst_s_;
  int replan_fail_streak_{0};
  int replan_ok_streak_{0};
  uint64_t replan_guard_open_frames_{0};
  uint64_t replan_guard_open_transitions_{0};
  uint64_t replan_guard_close_transitions_{0};
  bool effective_full_open_{false};
  bool effective_full_open_initialized_{false};
  uint64_t effective_full_open_transitions_{0};
  uint64_t effective_full_close_transitions_{0};
  uint64_t replan_status_count_{0};
  uint64_t replan_fail_count_{0};
  int max_replan_fail_streak_{0};
  std::optional<double> first_replan_guard_open_time_s_;
  std::optional<double> first_effective_full_open_time_s_;
  bool trajectory_guard_active_{false};
  bool trajectory_guard_open_{false};
  bool trajectory_guard_refresh_pending_{false};
  bool trajectory_guard_unbounded_refresh_frame_{false};
  std::optional<double> trajectory_guard_hold_until_s_;
  uint64_t trajectory_guard_status_count_{0};
  uint64_t trajectory_guard_active_count_{0};
  uint64_t trajectory_guard_open_frames_{0};
  uint64_t trajectory_guard_active_frames_{0};
  uint64_t trajectory_guard_hold_only_frames_{0};
  uint64_t trajectory_guard_active_published_frames_{0};
  uint64_t trajectory_guard_hold_only_published_frames_{0};
  uint64_t trajectory_guard_open_transitions_{0};
  uint64_t trajectory_guard_close_transitions_{0};
  uint64_t trajectory_guard_refresh_frames_{0};
  std::optional<uint64_t> trajectory_guard_pending_exact_ack_stamp_ns_;
  std::optional<double> trajectory_guard_pending_exact_ack_send_s_;
  uint64_t trajectory_guard_full_refresh_pending_ack_max_{0};
  uint64_t trajectory_guard_full_refresh_ack_count_{0};
  uint64_t trajectory_guard_full_refresh_ack_committed_count_{0};
  uint64_t trajectory_guard_full_refresh_superseded_count_{0};
  uint64_t trajectory_guard_full_refresh_ack_retry_frames_{0};
  uint64_t trajectory_guard_full_refresh_abandoned_count_{0};
  double trajectory_guard_full_refresh_ack_latency_sum_s_{0.0};
  double trajectory_guard_full_refresh_ack_latency_max_s_{0.0};
  uint64_t test_dropped_trajectory_guard_full_clouds_{0};
  std::optional<double> first_trajectory_guard_open_time_s_;
};

namespace native_sector {

std::shared_ptr<rclcpp::Node> createNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options,
    GuardCloudObserver guard_cloud_observer) {
  std::vector<std::string> storage;
  storage.reserve(arguments.size() + 1);
  storage.emplace_back("native_sector_cpp");
  storage.insert(storage.end(), arguments.begin(), arguments.end());
  std::vector<char *> argv;
  argv.reserve(storage.size());
  for (auto &argument : storage)
    argv.push_back(argument.data());
  Options options = parseArgs(static_cast<int>(argv.size()), argv.data());
  return std::make_shared<NativeSectorCpp>(
      std::move(options), node_options, std::move(guard_cloud_observer));
}

DirectInputHandle createDirectInputNode(
    const std::vector<std::string> &arguments,
    const rclcpp::NodeOptions &node_options) {
  std::vector<std::string> direct_arguments = arguments;
  direct_arguments.emplace_back("--direct-input");
  std::vector<std::string> storage;
  storage.reserve(direct_arguments.size() + 1);
  storage.emplace_back("native_sector_cpp");
  storage.insert(storage.end(), direct_arguments.begin(),
                 direct_arguments.end());
  std::vector<char *> argv;
  argv.reserve(storage.size());
  for (auto &argument : storage)
    argv.push_back(argument.data());
  Options options = parseArgs(static_cast<int>(argv.size()), argv.data());
  auto concrete = std::make_shared<NativeSectorCpp>(
      std::move(options), node_options);
  DirectInputHandle handle;
  handle.node = concrete;
  handle.submit_cloud = [concrete](
                            const sensor_msgs::msg::PointCloud2::SharedPtr
                                &cloud_msg) {
    concrete->submitCloud(cloud_msg);
  };
  return handle;
}

} // namespace native_sector

#ifndef NATIVE_SECTOR_CPP_NO_MAIN
int main(int argc, char **argv) {
  try {
    Options options = parseArgs(argc, argv);
    int ros_argc = 1;
    rclcpp::init(ros_argc, argv);
    auto node = std::make_shared<NativeSectorCpp>(std::move(options));
    rclcpp::spin(node);
    node.reset();
    rclcpp::shutdown();
    return 0;
  } catch (const std::exception &error) {
    std::fprintf(stderr, "native_sector_cpp: %s\n", error.what());
    return 2;
  }
}
#endif
