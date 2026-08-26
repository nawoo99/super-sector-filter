#include <rclcpp/rclcpp.hpp>

#include <nav_msgs/msg/odometry.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/msg/point_field.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/u_int64.hpp>
#include <std_msgs/msg/u_int64_multi_array.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
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
  int replan_fail_streak_open{5};
  int replan_ok_streak_close{15};
  bool replan_guard_en{true};
  bool bounded_replan_guard{false};
  std::optional<double> replan_open_burst_s;
  std::optional<double> replan_open_cooldown_s;
  double near_field_radius_m{1.5};
  double near_field_speed_gain_s{0.0};
  std::optional<double> near_field_max_radius_m;
  double open_burst_s{0.0};
  double open_cooldown_s{0.0};
  std::string trajectory_guard_topic{
      "/planning/trajectory_guard_recovery_active"};
  double trajectory_guard_hold_s{2.5};
  double trajectory_guard_active_max_publish_hz{0.0};
  double trajectory_guard_ack_retry_age_s{0.0};
  bool test_drop_first_trajectory_guard_full_cloud{false};
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
      options.resume_t < 0.0 || options.open_burst_s < 0.0 ||
      options.open_cooldown_s < 0.0 ||
      options.trajectory_guard_hold_s < 0.0 ||
      options.trajectory_guard_active_max_publish_hz < 0.0 ||
      options.trajectory_guard_ack_retry_age_s < 0.0 ||
      options.near_field_radius_m < 0.0 ||
      options.near_field_speed_gain_s < 0.0 ||
      near_max < options.near_field_radius_m || guard_burst < 0.0 ||
      guard_cooldown < 0.0) {
    throw std::runtime_error("invalid negative/range-limited filter setting");
  }
  if (options.resume_v <= options.stall_v) {
    throw std::runtime_error("resume-v must be greater than stall-v");
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
  explicit NativeSectorCpp(Options options)
      : Node("native_sector_cpp"), options_(std::move(options)),
        half_angle_rad_(options_.half_angle_deg * kPi / 180.0),
        half_angle_cos_(std::cos(half_angle_rad_)),
        near_field_max_radius_m_(options_.near_field_max_radius_m.value_or(
            options_.near_field_radius_m)),
        replan_guard_burst_s_(
            options_.replan_open_burst_s.value_or(options_.open_burst_s)),
        replan_guard_cooldown_s_(
            options_.replan_open_cooldown_s.value_or(options_.open_cooldown_s)),
        armed_(options_.mode == "legacy-trigger") {
    const auto sensor_qos =
        rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();
    cloud_sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
        options_.input_topic, sensor_qos,
        std::bind(&NativeSectorCpp::cloudCallback, this,
                  std::placeholders::_1));
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
      trajectory_guard_sub_ = create_subscription<std_msgs::msg::Bool>(
          options_.trajectory_guard_topic, guard_qos,
          std::bind(&NativeSectorCpp::trajectoryGuardCallback, this,
                    std::placeholders::_1));
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
      full_refresh_request_pub_ =
          create_publisher<std_msgs::msg::UInt64MultiArray>(
              options_.full_refresh_request_topic, request_qos);
    }
    const auto output_qos = options_.reliable_output
        ? rclcpp::QoS(rclcpp::KeepLast(1)).reliable().durability_volatile()
        : sensor_qos;
    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
        options_.output_topic, output_qos);
    full_open_pub_ =
        create_publisher<std_msgs::msg::Bool>("/sector/full_open", 1);
    armed_pub_ =
        create_publisher<std_msgs::msg::Bool>("/sector/trigger_armed", 1);
    state_timer_ = create_wall_timer(std::chrono::seconds(1), [this]() {
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
                "commit refresh %.3f s, full-open extra budget %lu",
                options_.mode.c_str(), options_.half_angle_deg,
                options_.input_topic.c_str(), options_.max_publish_hz,
                options_.map_commit_refresh_age_s,
                static_cast<unsigned long>(
                    options_.full_open_extra_max_points));
    publishState();
    writeStats();
  }

  ~NativeSectorCpp() override { writeStats(); }

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
    // kind 1 = pre-stale; kind 2 = trajectory-guard true edge.
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
    }
  }

  void mapProcessAckCallback(
      const std_msgs::msg::UInt64MultiArray::SharedPtr msg) {
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
    const auto &p = msg->pose.pose.position;
    const auto &q = msg->pose.pose.orientation;
    drone_ = std::array<double, 3>{p.x, p.y, p.z};
    yaw_ = std::atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z));
    const auto &v = msg->twist.twist.linear;
    const double speed = std::hypot(v.x, v.y);
    latest_speed_mps_ = speed;
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
    const double now = nowSeconds();
    const bool state_changed =
        updateRecoveryBurst(now) | updateReplanGuardBurst(now) |
        updateTrajectoryGuardHold(now);
    if (state_changed)
      publishState();
    ++frames_;
    const uint64_t input_points =
        static_cast<uint64_t>(msg->width) * msg->height;
    input_points_ += input_points;
    total_points_ += input_points;
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
        options_.full_open_extra_max_points > 0;
    const bool passthrough = options_.mode == "full" || !drone_ ||
        pre_stale_full_refresh ||
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
    }
    if (passthrough) {
      kept_points_ += input_points;
      cloud_pub_->publish(*msg);
      return;
    }

    const CloudFields fields = findCloudFields(*msg);
    if (!fields.x || !fields.y || !fields.z || msg->point_step == 0) {
      RCLCPP_WARN_THROTTLE(
          get_logger(), *get_clock(), 5000,
          "cloud lacks float x/y/z fields; passing it through");
      kept_points_ += input_points;
      cloud_pub_->publish(*msg);
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

    sensor_msgs::msg::PointCloud2 output;
    output.header = msg->header;
    output.height = 1;
    output.fields = msg->fields;
    output.is_bigendian = msg->is_bigendian;
    // Match sensor_msgs_py.create_cloud(), which the prototype used: retain
    // the declared field offsets but remove any trailing transport padding.
    // MARSIM's input records are 32 bytes while x/y/z/intensity end at byte
    // 20.  Keeping the raw 32-byte stride made the nominally equivalent C++
    // path observably different at the ROG-Map subscription boundary.
    output.point_step = packedPointStep(*msg);
    output.is_dense = true;
    output.data.reserve(static_cast<size_t>(input_points) * output.point_step);

    const auto appendPoint = [&output, &msg](const uint8_t *point) {
      const size_t output_offset = output.data.size();
      output.data.resize(output_offset + output.point_step, 0);
      uint8_t *destination = output.data.data() + output_offset;
      for (const auto &field : msg->fields) {
        const size_t byte_count = fieldByteSize(field.datatype) * field.count;
        if (byte_count == 0 || field.offset + byte_count > msg->point_step ||
            field.offset + byte_count > output.point_step) {
          continue;
        }
        std::memcpy(destination + field.offset, point + field.offset,
                    byte_count);
      }
    };

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
        appendPoint(point);
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
        appendPoint(msg->data.data() + full_open_extra_offsets[selected]);
      }
      kept_this_frame += extra_to_keep;
      full_open_extra_kept_ += extra_to_keep;
    }
    output.width = static_cast<uint32_t>(kept_this_frame);
    output.row_step = output.width * output.point_step;
    kept_points_ += kept_this_frame;
    cloud_pub_->publish(output);
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
    number("velocity_yaw_update_v",
           (options_.mode == "velocity" || options_.mode == "adaptive")
               ? options_.resume_v
               : 0.2);
    integer("frames", frames_);
    integer("published_frames", published_frames_);
    integer("rate_limited_frames", rate_limited_frames_);
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
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr replan_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr trajectory_guard_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt64>::SharedPtr map_commit_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt64MultiArray>::SharedPtr
      map_process_ack_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
  rclcpp::Publisher<std_msgs::msg::UInt64MultiArray>::SharedPtr
      full_refresh_request_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr full_open_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr armed_pub_;
  rclcpp::TimerBase::SharedPtr state_timer_;
  rclcpp::TimerBase::SharedPtr report_timer_;

  std::optional<std::array<double, 3>> drone_;
  double yaw_{0.0};
  std::optional<double> velocity_yaw_;
  double latest_speed_mps_{0.0};
  uint64_t kept_points_{0};
  uint64_t total_points_{0};
  uint64_t frames_{0};
  uint64_t published_frames_{0};
  uint64_t rate_limited_frames_{0};
  uint64_t input_points_{0};
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
