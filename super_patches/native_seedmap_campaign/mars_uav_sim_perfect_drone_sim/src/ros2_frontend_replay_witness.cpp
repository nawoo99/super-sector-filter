/**
 * Deterministic MARSIM -> native-front-end replay witness.
 *
 * This executable deliberately does not run SUPER or alter its decisions.  It
 * holds PerfectDrone at one commanded state, renders the real configured PCD,
 * hands each raw PointCloud2 directly to the production native front-end, and
 * records whether a supplied straight committed trajectory intersects the
 * rendered evidence.  Running the same state once in fixed-sector mode and
 * once in adaptive mode separates three prerequisites that closed-loop map
 * tuning had previously conflated:
 *   1. MARSIM actually raycasts the conflicting surface,
 *   2. the fixed sector removes that surface, and
 *   3. the asynchronous raw-cloud risk worker emits fresh OCCUPIED verdicts.
 */

#include "perfect_drone_sim/ros2_perfect_drone_model.hpp"

#include <mars_quadrotor_msgs/msg/polynomial_trajectory.hpp>
#include <mars_quadrotor_msgs/msg/position_command.hpp>
#include <mars_quadrotor_msgs/msg/trajectory_risk_verdict.hpp>
#include <mission_planner/native_sector_cpp.hpp>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <limits>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

using Verdict = mars_quadrotor_msgs::msg::TrajectoryRiskVerdict;
using SteadyClock = std::chrono::steady_clock;

std::vector<std::string> splitArguments(const std::string &encoded) {
  std::vector<std::string> result;
  std::stringstream stream(encoded);
  std::string item;
  while (std::getline(stream, item, ';')) {
    if (!item.empty())
      result.push_back(item);
  }
  return result;
}

std::string argumentValue(const std::vector<std::string> &arguments,
                          const std::string &name) {
  const auto found = std::find(arguments.begin(), arguments.end(), name);
  if (found == arguments.end() || std::next(found) == arguments.end())
    return {};
  return *std::next(found);
}

std::string jsonEscape(const std::string &input) {
  std::ostringstream output;
  for (const char character : input) {
    switch (character) {
    case '\\':
      output << "\\\\";
      break;
    case '"':
      output << "\\\"";
      break;
    case '\n':
      output << "\\n";
      break;
    case '\r':
      output << "\\r";
      break;
    case '\t':
      output << "\\t";
      break;
    default:
      output << character;
      break;
    }
  }
  return output.str();
}

struct CloudObservation {
  std::uint64_t frames{0};
  std::uint64_t points{0};
  std::uint64_t hazard_frames{0};
  std::uint64_t hazard_points{0};
  std::uint64_t conflict_frames{0};
  std::uint64_t conflict_points{0};
  std::uint64_t max_conflict_points_per_frame{0};
};

class ReplayWitness final : public rclcpp::Node {
public:
  explicit ReplayWitness(const rclcpp::NodeOptions &options)
      : Node("frontend_replay_witness", options), start_(SteadyClock::now()) {
    mode_ = declare_parameter<std::string>("mode", "sector");
    result_json_ = declare_parameter<std::string>("result_json", "");
    duration_s_ = declare_parameter<double>("duration_s", 6.0);
    warmup_s_ = declare_parameter<double>("warmup_s", 1.0);
    x_ = declare_parameter<double>("replay_x", 24.0);
    y_ = declare_parameter<double>("replay_y", 20.0);
    z_ = declare_parameter<double>("replay_z", 1.5);
    yaw_deg_ = declare_parameter<double>("replay_yaw_deg", 90.0);
    vx_ = declare_parameter<double>("replay_vx", 0.0);
    vy_ = declare_parameter<double>("replay_vy", 7.0);
    vz_ = declare_parameter<double>("replay_vz", 0.0);
    trajectory_end_x_ = declare_parameter<double>("trajectory_end_x", 16.2);
    trajectory_end_y_ = declare_parameter<double>("trajectory_end_y", 24.4);
    trajectory_end_z_ = declare_parameter<double>("trajectory_end_z", 1.5);
    trajectory_duration_s_ =
        declare_parameter<double>("trajectory_duration_s", 1.5);
    risk_horizon_s_ = declare_parameter<double>("risk_horizon_s", 1.0);
    conflict_clearance_m_ =
        declare_parameter<double>("conflict_clearance_m", 0.20);
    hazard_x_ = declare_parameter<double>("hazard_x", 16.2);
    hazard_y_ = declare_parameter<double>("hazard_y", 24.4);
    hazard_radius_m_ = declare_parameter<double>("hazard_radius_m", 1.2);
    hazard_z_min_ = declare_parameter<double>("hazard_z_min", 0.0);
    hazard_z_max_ = declare_parameter<double>("hazard_z_max", 3.2);
    fresh_age_limit_s_ = declare_parameter<double>("fresh_age_limit_s", 0.75);
    generation_ = static_cast<std::uint64_t>(
        declare_parameter<int64_t>("trajectory_generation", 1));

    if (duration_s_ <= 0.0 || warmup_s_ < 0.0 || warmup_s_ >= duration_s_ ||
        trajectory_duration_s_ <= 0.0 || risk_horizon_s_ <= 0.0 ||
        conflict_clearance_m_ <= 0.0 || hazard_radius_m_ <= 0.0 ||
        hazard_z_min_ > hazard_z_max_ || fresh_age_limit_s_ <= 0.0 ||
        generation_ == 0) {
      throw std::invalid_argument("invalid replay-witness parameter");
    }

    const auto sensor_qos =
        rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();
    const auto verdict_qos =
        rclcpp::QoS(rclcpp::KeepLast(4)).reliable().durability_volatile();
    command_pub_ = create_publisher<mars_quadrotor_msgs::msg::PositionCommand>(
        "/planning/pos_cmd", sensor_qos);
    trajectory_pub_ =
        create_publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>(
            "/witness/planning_cmd/poly_traj", sensor_qos);
    filtered_sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
        "/witness/cloud_filtered", sensor_qos,
        [this](const sensor_msgs::msg::PointCloud2::SharedPtr message) {
          observeCloud(*message, filtered_);
        });
    verdict_sub_ = create_subscription<Verdict>(
        "/witness/trajectory_risk_verdict", verdict_qos,
        [this](const Verdict::SharedPtr message) { observeVerdict(*message); });
    command_timer_ = create_wall_timer(std::chrono::milliseconds(10), [this]() {
      publishCommandAndTrajectory();
    });
  }

  void observeRaw(const sensor_msgs::msg::PointCloud2::SharedPtr &message) {
    if (message)
      observeCloud(*message, raw_);
  }

  bool expired() const {
    return std::chrono::duration<double>(SteadyClock::now() - start_).count() >=
           duration_s_;
  }

  const std::string &mode() const { return mode_; }
  double riskHorizonSeconds() const { return risk_horizon_s_; }

  void writeResult() const {
    if (result_json_.empty())
      return;
    std::lock_guard<std::mutex> lock(mutex_);
    const std::string temporary = result_json_ + ".tmp";
    std::ofstream output(temporary);
    if (!output)
      throw std::runtime_error("cannot write result JSON: " + result_json_);
    const auto writeCloud = [&output](const char *name,
                                      const CloudObservation &value,
                                      const bool trailing) {
      output << "  \"" << name << "\": {\n"
             << "    \"frames\": " << value.frames << ",\n"
             << "    \"points\": " << value.points << ",\n"
             << "    \"hazard_frames\": " << value.hazard_frames << ",\n"
             << "    \"hazard_points\": " << value.hazard_points << ",\n"
             << "    \"conflict_frames\": " << value.conflict_frames << ",\n"
             << "    \"conflict_points\": " << value.conflict_points << ",\n"
             << "    \"max_conflict_points_per_frame\": "
             << value.max_conflict_points_per_frame << "\n"
             << "  }" << (trailing ? "," : "") << "\n";
    };
    const auto jsonNumber = [](const double value) {
      if (!std::isfinite(value))
        return std::string("null");
      std::ostringstream encoded;
      encoded << std::fixed << std::setprecision(9) << value;
      return encoded.str();
    };
    const double evaluated_fraction =
        std::min(1.0, risk_horizon_s_ / trajectory_duration_s_);
    output << std::fixed << std::setprecision(9) << "{\n"
           << "  \"schema\": \"frontend-replay-witness-v1\",\n"
           << "  \"mode\": \"" << jsonEscape(mode_) << "\",\n"
           << "  \"duration_s\": " << duration_s_ << ",\n"
           << "  \"warmup_s\": " << warmup_s_ << ",\n"
           << "  \"replay_position_xyz_m\": [" << x_ << ", " << y_ << ", " << z_
           << "],\n"
           << "  \"replay_yaw_deg\": " << yaw_deg_ << ",\n"
           << "  \"replay_velocity_xyz_mps\": [" << vx_ << ", " << vy_ << ", "
           << vz_ << "],\n"
           << "  \"trajectory_end_xyz_m\": [" << trajectory_end_x_ << ", "
           << trajectory_end_y_ << ", " << trajectory_end_z_ << "],\n"
           << "  \"trajectory_duration_s\": " << trajectory_duration_s_ << ",\n"
           << "  \"risk_horizon_s\": " << risk_horizon_s_ << ",\n"
           << "  \"evaluated_trajectory_end_xyz_m\": ["
           << x_ + evaluated_fraction * (trajectory_end_x_ - x_) << ", "
           << y_ + evaluated_fraction * (trajectory_end_y_ - y_) << ", "
           << z_ + evaluated_fraction * (trajectory_end_z_ - z_) << "],\n"
           << "  \"trajectory_generation\": " << generation_ << ",\n"
           << "  \"conflict_clearance_m\": " << conflict_clearance_m_ << ",\n"
           << "  \"hazard_xy_radius_m\": [" << hazard_x_ << ", " << hazard_y_
           << ", " << hazard_radius_m_ << "],\n";
    writeCloud("raw", raw_, true);
    writeCloud("filtered", filtered_, true);
    output << "  \"verdict_messages\": " << verdict_messages_ << ",\n"
           << "  \"future_verdict_messages\": " << future_verdict_messages_
           << ",\n"
           << "  \"occupied_verdicts\": " << occupied_verdicts_ << ",\n"
           << "  \"fresh_occupied_verdicts\": " << fresh_occupied_verdicts_
           << ",\n"
           << "  \"max_consecutive_fresh_occupied\": "
           << max_consecutive_fresh_occupied_ << ",\n"
           << "  \"last_verdict_status\": " << last_verdict_status_ << ",\n"
           << "  \"last_verdict_generation\": " << last_verdict_generation_
           << ",\n"
           << "  \"last_verdict_source_cloud_age_s\": "
           << jsonNumber(last_verdict_source_cloud_age_s_) << ",\n"
           << "  \"last_verdict_minimum_distance_m\": "
           << jsonNumber(last_verdict_minimum_distance_m_) << "\n"
           << "}\n";
    output.close();
    if (std::rename(temporary.c_str(), result_json_.c_str()) != 0) {
      std::remove(temporary.c_str());
      throw std::runtime_error("cannot replace result JSON: " + result_json_);
    }
  }

private:
  bool afterWarmup() const {
    return std::chrono::duration<double>(SteadyClock::now() - start_).count() >=
           warmup_s_;
  }

  static double pointSegmentDistance(const std::array<double, 3> &point,
                                     const std::array<double, 3> &start,
                                     const std::array<double, 3> &end) {
    std::array<double, 3> direction{};
    std::array<double, 3> offset{};
    double length_squared = 0.0;
    double projection = 0.0;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      direction[axis] = end[axis] - start[axis];
      offset[axis] = point[axis] - start[axis];
      length_squared += direction[axis] * direction[axis];
      projection += offset[axis] * direction[axis];
    }
    const double fraction =
        length_squared > 0.0 ? std::clamp(projection / length_squared, 0.0, 1.0)
                             : 0.0;
    double distance_squared = 0.0;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      const double residual =
          point[axis] - (start[axis] + fraction * direction[axis]);
      distance_squared += residual * residual;
    }
    return std::sqrt(distance_squared);
  }

  void observeCloud(const sensor_msgs::msg::PointCloud2 &message,
                    CloudObservation &observation) {
    if (!afterWarmup())
      return;
    pcl::PointCloud<pcl::PointXYZI> cloud;
    pcl::fromROSMsg(message, cloud);
    std::uint64_t hazard_points = 0;
    std::uint64_t conflict_points = 0;
    const std::array<double, 3> start{x_, y_, z_};
    const double evaluated_fraction =
        std::min(1.0, risk_horizon_s_ / trajectory_duration_s_);
    const std::array<double, 3> end{
        x_ + evaluated_fraction * (trajectory_end_x_ - x_),
        y_ + evaluated_fraction * (trajectory_end_y_ - y_),
        z_ + evaluated_fraction * (trajectory_end_z_ - z_)};
    for (const auto &point : cloud) {
      if (!std::isfinite(point.x) || !std::isfinite(point.y) ||
          !std::isfinite(point.z)) {
        continue;
      }
      const double dx = point.x - hazard_x_;
      const double dy = point.y - hazard_y_;
      if (dx * dx + dy * dy <= hazard_radius_m_ * hazard_radius_m_ &&
          point.z >= hazard_z_min_ && point.z <= hazard_z_max_) {
        ++hazard_points;
      }
      if (pointSegmentDistance({point.x, point.y, point.z}, start, end) <=
          conflict_clearance_m_) {
        ++conflict_points;
      }
    }
    std::lock_guard<std::mutex> lock(mutex_);
    ++observation.frames;
    observation.points += cloud.size();
    observation.hazard_points += hazard_points;
    observation.conflict_points += conflict_points;
    if (hazard_points > 0)
      ++observation.hazard_frames;
    if (conflict_points > 0)
      ++observation.conflict_frames;
    observation.max_conflict_points_per_frame =
        std::max(observation.max_conflict_points_per_frame, conflict_points);
  }

  void observeVerdict(const Verdict &verdict) {
    if (!afterWarmup())
      return;
    std::lock_guard<std::mutex> lock(mutex_);
    ++verdict_messages_;
    const bool future = verdict.scope == Verdict::FUTURE_TRAJECTORY;
    if (future) {
      ++future_verdict_messages_;
      if (verdict.status == Verdict::OCCUPIED)
        ++occupied_verdicts_;
    }
    const bool fresh_occupied =
        future && verdict.status == Verdict::OCCUPIED &&
        verdict.trajectory_generation == generation_ &&
        verdict.source_cloud_stamp_ns != 0 &&
        std::isfinite(verdict.source_cloud_age_s) &&
        verdict.source_cloud_age_s >= 0.0 &&
        verdict.source_cloud_age_s <= fresh_age_limit_s_;
    if (fresh_occupied) {
      ++fresh_occupied_verdicts_;
      ++consecutive_fresh_occupied_;
      max_consecutive_fresh_occupied_ = std::max(
          max_consecutive_fresh_occupied_, consecutive_fresh_occupied_);
    } else if (future) {
      consecutive_fresh_occupied_ = 0;
    }
    if (future) {
      // The frontend may publish two CURRENT_BODY verdicts around each
      // FUTURE_TRAJECTORY result.  Do not let callback scheduling overwrite
      // the generation-bound evidence that this witness is designed to test.
      last_verdict_status_ = verdict.status;
      last_verdict_generation_ = verdict.trajectory_generation;
      last_verdict_source_cloud_age_s_ = verdict.source_cloud_age_s;
      last_verdict_minimum_distance_m_ = verdict.minimum_distance_m;
    }
  }

  void publishCommandAndTrajectory() {
    mars_quadrotor_msgs::msg::PositionCommand command;
    command.header.stamp = get_clock()->now();
    command.header.frame_id = "world";
    command.position.x = x_;
    command.position.y = y_;
    command.position.z = z_;
    command.velocity.x = vx_;
    command.velocity.y = vy_;
    command.velocity.z = vz_;
    command.yaw = yaw_deg_ * M_PI / 180.0;
    command.trajectory_id = static_cast<std::uint32_t>(generation_);
    command.trajectory_flag =
        mars_quadrotor_msgs::msg::PositionCommand::TRAJECTORY_STATUS_READY;
    command_pub_->publish(command);

    mars_quadrotor_msgs::msg::PolynomialTrajectory trajectory;
    trajectory.header = command.header;
    trajectory.trajectory_id = static_cast<std::uint32_t>(generation_);
    trajectory.trajectory_generation = generation_;
    trajectory.type =
        mars_quadrotor_msgs::msg::PolynomialTrajectory::POSITION_TRAJ |
        mars_quadrotor_msgs::msg::PolynomialTrajectory::HEART_BEAT;
    trajectory.piece_num_pos = 1;
    trajectory.order_pos = 1;
    trajectory.start_wt_pos = get_clock()->now().seconds();
    trajectory.time_pos = {trajectory_duration_s_};
    // SUPER serializes each polynomial as [highest degree, ..., constant].
    trajectory.coef_pos_x = {(trajectory_end_x_ - x_) / trajectory_duration_s_,
                             x_};
    trajectory.coef_pos_y = {(trajectory_end_y_ - y_) / trajectory_duration_s_,
                             y_};
    trajectory.coef_pos_z = {(trajectory_end_z_ - z_) / trajectory_duration_s_,
                             z_};
    trajectory_pub_->publish(trajectory);
  }

  mutable std::mutex mutex_;
  const SteadyClock::time_point start_;
  std::string mode_;
  std::string result_json_;
  double duration_s_{6.0};
  double warmup_s_{1.0};
  double x_{24.0};
  double y_{20.0};
  double z_{1.5};
  double yaw_deg_{90.0};
  double vx_{0.0};
  double vy_{7.0};
  double vz_{0.0};
  double trajectory_end_x_{16.2};
  double trajectory_end_y_{24.4};
  double trajectory_end_z_{1.5};
  double trajectory_duration_s_{1.5};
  double risk_horizon_s_{1.0};
  double conflict_clearance_m_{0.20};
  double hazard_x_{16.2};
  double hazard_y_{24.4};
  double hazard_radius_m_{1.2};
  double hazard_z_min_{0.0};
  double hazard_z_max_{3.2};
  double fresh_age_limit_s_{0.75};
  std::uint64_t generation_{1};
  CloudObservation raw_;
  CloudObservation filtered_;
  std::uint64_t verdict_messages_{0};
  std::uint64_t future_verdict_messages_{0};
  std::uint64_t occupied_verdicts_{0};
  std::uint64_t fresh_occupied_verdicts_{0};
  std::uint64_t consecutive_fresh_occupied_{0};
  std::uint64_t max_consecutive_fresh_occupied_{0};
  std::uint64_t last_verdict_generation_{0};
  int last_verdict_status_{-1};
  double last_verdict_source_cloud_age_s_{
      std::numeric_limits<double>::infinity()};
  double last_verdict_minimum_distance_m_{
      std::numeric_limits<double>::infinity()};
  rclcpp::Publisher<mars_quadrotor_msgs::msg::PositionCommand>::SharedPtr
      command_pub_;
  rclcpp::Publisher<mars_quadrotor_msgs::msg::PolynomialTrajectory>::SharedPtr
      trajectory_pub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr filtered_sub_;
  rclcpp::Subscription<Verdict>::SharedPtr verdict_sub_;
  rclcpp::TimerBase::SharedPtr command_timer_;
};

} // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  int return_code = 0;
  try {
    rclcpp::NodeOptions options;
    options.use_intra_process_comms(true);
    auto configuration = std::make_shared<rclcpp::Node>(
        "frontend_replay_witness_config", options);
    configuration->declare_parameter<std::string>("config_name",
                                                  "abt2_cal_t3.yaml");
    configuration->declare_parameter<std::string>("filter_arguments", "");
    const std::string config_name =
        configuration->get_parameter("config_name").as_string();
    const std::string encoded_arguments =
        configuration->get_parameter("filter_arguments").as_string();
    auto filter_arguments = splitArguments(encoded_arguments);
    if (filter_arguments.empty())
      throw std::invalid_argument("filter_arguments must not be empty");

    auto witness = std::make_shared<ReplayWitness>(options);
    if (filter_arguments.front() != witness->mode()) {
      throw std::invalid_argument(
          "mode parameter and filter_arguments mode must match");
    }
    if (argumentValue(filter_arguments, "--output-topic") !=
        "/witness/cloud_filtered") {
      throw std::invalid_argument(
          "filter_arguments must publish /witness/cloud_filtered");
    }
    if (witness->mode() == "adaptive") {
      if (argumentValue(filter_arguments, "--risk-verdict-topic") !=
              "/witness/trajectory_risk_verdict" ||
          argumentValue(filter_arguments, "--risk-trajectory-topic") !=
              "/witness/planning_cmd/poly_traj") {
        throw std::invalid_argument(
            "adaptive witness requires the dedicated risk topics");
      }
      const std::string encoded_horizon =
          argumentValue(filter_arguments, "--risk-horizon-s");
      if (encoded_horizon.empty() ||
          std::abs(std::stod(encoded_horizon) - witness->riskHorizonSeconds()) >
              1e-9) {
        throw std::invalid_argument(
            "witness and frontend risk horizons must match");
      }
    }
    native_sector::DirectInputHandle filter =
        native_sector::createDirectInputNode(filter_arguments, options);
    rclcpp::NodeOptions simulator_options;
    simulator_options.use_intra_process_comms(true);
    simulator_options.parameter_overrides(
        {rclcpp::Parameter("config_name", config_name)});
    auto simulator = std::make_shared<perfect_drone::PerfectDrone>(
        [witness, submit = filter.submit_cloud](
            const sensor_msgs::msg::PointCloud2::SharedPtr &cloud) {
          witness->observeRaw(cloud);
          submit(cloud);
        },
        false, simulator_options);

    rclcpp::executors::MultiThreadedExecutor side_executor(
        rclcpp::ExecutorOptions(), 5);
    side_executor.add_callback_group(simulator->cmdSubCbkGroup(),
                                     simulator->get_node_base_interface());
    side_executor.add_callback_group(simulator->odomTimerCbkGroup(),
                                     simulator->get_node_base_interface());
    // The global-map publisher is irrelevant to this sensor witness and its
    // 1 ms timer has a legacy 5 s burst.  Do not execute that callback group.
    side_executor.add_node(filter.node);
    side_executor.add_node(witness);
    side_executor.add_node(configuration);
    std::thread side_thread([&side_executor]() { side_executor.spin(); });

    std::atomic<bool> watchdog_stop{false};
    std::thread watchdog([&watchdog_stop, witness]() {
      while (!watchdog_stop.load(std::memory_order_relaxed) &&
             !witness->expired()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
      }
      if (!watchdog_stop.load(std::memory_order_relaxed))
        rclcpp::shutdown();
    });

    rclcpp::executors::SingleThreadedExecutor render_executor;
    render_executor.add_callback_group(simulator->localPcCbkGroup(),
                                       simulator->get_node_base_interface());
    render_executor.spin();
    watchdog_stop.store(true, std::memory_order_relaxed);
    watchdog.join();
    side_executor.cancel();
    side_thread.join();
    simulator->reportSensorCadence();
    simulator.reset();
    filter.node.reset();
    filter.submit_cloud = {};
    witness->writeResult();
    witness.reset();
    configuration.reset();
  } catch (const std::exception &error) {
    std::fprintf(stderr, "frontend replay witness failed: %s\n", error.what());
    return_code = 2;
    if (rclcpp::ok())
      rclcpp::shutdown();
  }
  return return_code;
}
