#include <rclcpp/rclcpp.hpp>

#include <nav_msgs/msg/odometry.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/msg/point_field.hpp>
#include <std_msgs/msg/bool.hpp>

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
#include <utility>
#include <vector>

namespace {

constexpr double kPi = 3.14159265358979323846;

struct Options {
  std::string mode{"sector"};
  double half_angle_deg{60.0};
  std::string input_topic{"/cloud_registered"};
  std::string output_topic{"/cloud_sector"};
  double max_publish_hz{0.0};
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
    } else if (arg == "--max-publish-hz") {
      options.max_publish_hz = parseDouble(arg, requireValue(i, arg));
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
      options.stall_t < 0.0 || options.resume_v < 0.0 ||
      options.resume_t < 0.0 || options.open_burst_s < 0.0 ||
      options.open_cooldown_s < 0.0 || options.near_field_radius_m < 0.0 ||
      options.near_field_speed_gain_s < 0.0 ||
      near_max < options.near_field_radius_m || guard_burst < 0.0 ||
      guard_cooldown < 0.0) {
    throw std::runtime_error("invalid negative/range-limited filter setting");
  }
  if (options.resume_v <= options.stall_v) {
    throw std::runtime_error("resume-v must be greater than stall-v");
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
    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
        options_.output_topic, sensor_qos);
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

    RCLCPP_INFO(get_logger(),
                "%s mode, half-angle %.1f deg, input %s, publish cap %.2f Hz",
                options_.mode.c_str(), options_.half_angle_deg,
                options_.input_topic.c_str(), options_.max_publish_hz);
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
           replan_guard_open_;
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

  bool shouldPublishCloud(double now) {
    if (options_.max_publish_hz <= 0.0)
      return true;
    const double period = 1.0 / options_.max_publish_hz;
    if (!next_publish_time_s_) {
      next_publish_time_s_ = now + period;
      return true;
    }
    if (now < *next_publish_time_s_) {
      ++rate_limited_frames_;
      return false;
    }
    const double elapsed = now - *next_publish_time_s_;
    const double periods = std::floor(elapsed / period) + 1.0;
    *next_publish_time_s_ += periods * period;
    return true;
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
        updateRecoveryBurst(now) | updateReplanGuardBurst(now);
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
    if (!shouldPublishCloud(now))
      return;
    ++published_frames_;

    const bool passthrough = options_.mode == "full" || !drone_ ||
                             (statefulMode() && effective_recovery_open_) ||
                             replan_guard_open_;
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
    output.data.reserve(static_cast<size_t>(input_points) * msg->point_step);

    uint64_t kept_this_frame = 0;
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
        if (!in_sector && !near)
          continue;
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
        ++kept_this_frame;
      }
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
    number("publish_duty_pct",
           rounded(100.0 * published_frames_ / frame_denominator, 1e3));
    integer("input_points", input_points_);
    integer("kept_points", kept_points_);
    number("kept_pct", rounded(100.0 * kept_points_ / point_denominator, 1e3));
    boolean("armed", armed_);
    number("armed_duty_pct",
           rounded(100.0 * armed_frames_ / frame_denominator, 1e3));
    boolean("open", options_.mode == "full" || effective_recovery_open_ ||
                        replan_guard_open_);
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
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
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
