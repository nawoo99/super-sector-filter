#ifndef _PERFECT_DRONE_SIM_HPP_
#define _PERFECT_DRONE_SIM_HPP_

#include "rclcpp/rclcpp.hpp"
#include "visualization_msgs/msg/marker_array.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mars_quadrotor_msgs/msg/position_command.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "string"
#include "Eigen/Dense"
#include "nav_msgs/msg/path.hpp"
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <marsim_render/marsim_render.hpp>
#include "pcl_conversions/pcl_conversions.h"
#include "perfect_drone_sim/config.hpp"
#include "perfect_drone_sim/common_execution_policy.hpp"
#include "perfect_drone_sim/static_pc_two_phase_policy.hpp"
#include "perfect_drone_sim/static_pc_durable_policy.hpp"
#include "perfect_drone_sim/static_pc_latched_policy.hpp"
// Only the composed Full/Adaptive targets have the shared planner profiler
// dependency. Standalone/front-end targets retain their existing dependencies.
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
#include <super_utils/thread_cpu_profile.hpp>
#include <super_utils/callback_timing_trace.hpp>
#include <rog_map/diagnostic_trace.hpp>
#endif
#include "tf2_ros/transform_broadcaster.h"
#include <chrono>
#include <atomic>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <mutex>
#include <limits>
#include <optional>
#include <stdexcept>


typedef Eigen::Matrix<double, 3, 1> Vec3;
typedef Eigen::Matrix<double, 3, 3> Mat33;

typedef Eigen::Matrix<double, 3, 3> StatePVA;
typedef Eigen::Matrix<double, 3, 4> StatePVAJ;
typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic> DynamicMat;
typedef Eigen::MatrixX4d MatX4;
typedef std::pair<double, Vec3> TimePosPair;

namespace perfect_drone {
    using SensorCloudObserver = std::function<void(
            const sensor_msgs::msg::PointCloud2::SharedPtr &)>;

    struct AcquisitionWindow {
        bool enabled{false};
        bool full{false};
        std::uint64_t cycle{0};
        double center_yaw_rad{0.0};
        double half_angle_deg{45.0};
    };
    using AcquisitionProvider = std::function<AcquisitionWindow()>;
    using AcquiredCloudObserver = std::function<void(
            const sensor_msgs::msg::PointCloud2::SharedPtr &, const AcquisitionWindow &)>;

    struct SideEntryV1Config {
        bool enabled{false};
        int scenario_version{0};
        double speed_min_mps{2.0};
        double yaw_velocity_mismatch_min_deg{50.0};
        bool require_yaw_velocity_mismatch{true};
        double hold_s{0.02};
        int qualifying_samples{0};
        double prediction_s{0.8};
        bool require_velocity_inside{true};
        bool fixed_center_enabled{false};
        double fixed_center_x{22.5};
        double fixed_center_y{23.0};
        double trigger_distance_min_m{0.8};
        double trigger_distance_max_m{3.5};
        double trigger_waypoint_x{24.0};
        double trigger_waypoint_y{24.0};
        double trigger_waypoint_radius_m{2.0};
        double trap_waypoint_radius_m{2.0};
        double sector_half_angle_deg{45.0};
        double angular_margin_deg{2.0};
        double max_nudge_deg{20.0};
        double radius_m{0.25};
        double height_m{3.0};
        double point_spacing_m{0.05};
        double z_spacing_m{0.10};
        double sensing_horizon_m{15.0};
        double intensity{14545.0};

        void load(const std::string &path) {
            yaml_loader::YamlLoader loader(path);
            bool v1_enabled = false;
            bool v2_enabled = false;
            bool v3_enabled = false;
            bool v4_enabled = false;
            bool v5_enabled = false;
            bool v6_enabled = false;
            bool v7_enabled = false;
            loader.LoadParam("side_entry_v1/enabled", v1_enabled, false, false);
            loader.LoadParam("side_entry_v2/enabled", v2_enabled, false, false);
            loader.LoadParam("side_entry_v3/enabled", v3_enabled, false, false);
            loader.LoadParam("side_entry_v4/enabled", v4_enabled, false, false);
            loader.LoadParam("side_entry_v5/enabled", v5_enabled, false, false);
            loader.LoadParam("side_entry_v6/enabled", v6_enabled, false, false);
            loader.LoadParam("side_entry_v7/enabled", v7_enabled, false, false);
            if (static_cast<int>(v1_enabled) + static_cast<int>(v2_enabled) +
                        static_cast<int>(v3_enabled) +
                        static_cast<int>(v4_enabled) +
                        static_cast<int>(v5_enabled) +
                        static_cast<int>(v6_enabled) +
                        static_cast<int>(v7_enabled) > 1) {
                throw std::invalid_argument(
                        "only one side-entry scenario can be enabled");
            }
            enabled = v1_enabled || v2_enabled || v3_enabled || v4_enabled ||
                      v5_enabled || v6_enabled || v7_enabled;
            scenario_version =
                    v7_enabled ? 7 : v6_enabled ? 6 : v5_enabled ? 5 :
                    v4_enabled ? 4 : v3_enabled ? 3 :
                    v2_enabled ? 2 : v1_enabled ? 1 : 0;
            const std::string prefix = "side_entry_v" +
                                       std::to_string(scenario_version);
            loader.LoadParam(prefix + "/speed_min_mps", speed_min_mps, 2.0, false);
            loader.LoadParam(prefix + "/yaw_velocity_mismatch_min_deg",
                             yaw_velocity_mismatch_min_deg, 50.0, false);
            loader.LoadParam(prefix + "/require_yaw_velocity_mismatch",
                             require_yaw_velocity_mismatch, true, false);
            loader.LoadParam(prefix + "/hold_s", hold_s, 0.02, false);
            loader.LoadParam(prefix + "/qualifying_samples",
                             qualifying_samples,
                             scenario_version >= 5 ? 3 : 0, false);
            loader.LoadParam(prefix + "/prediction_s", prediction_s, 0.8, false);
            loader.LoadParam(prefix + "/require_velocity_inside",
                             require_velocity_inside, true, false);
            loader.LoadParam(prefix + "/fixed_center_enabled",
                             fixed_center_enabled, false, false);
            loader.LoadParam(prefix + "/fixed_center_x",
                             fixed_center_x, 22.5, false);
            loader.LoadParam(prefix + "/fixed_center_y",
                             fixed_center_y, 23.0, false);
            loader.LoadParam(prefix + "/trigger_distance_min_m",
                             trigger_distance_min_m, 0.8, false);
            loader.LoadParam(prefix + "/trigger_distance_max_m",
                             trigger_distance_max_m, 3.5, false);
            loader.LoadParam(prefix + "/trigger_waypoint_x",
                             trigger_waypoint_x, 24.0, false);
            loader.LoadParam(prefix + "/trigger_waypoint_y",
                             trigger_waypoint_y, 24.0, false);
            loader.LoadParam(prefix + "/trigger_waypoint_radius_m",
                             trigger_waypoint_radius_m, 2.0, false);
            loader.LoadParam(prefix + "/trap_waypoint_radius_m",
                             trap_waypoint_radius_m, 2.0, false);
            loader.LoadParam(prefix + "/sector_half_angle_deg",
                             sector_half_angle_deg, 45.0, false);
            loader.LoadParam(prefix + "/angular_margin_deg",
                             angular_margin_deg, 2.0, false);
            loader.LoadParam(prefix + "/max_nudge_deg",
                             max_nudge_deg, 20.0, false);
            loader.LoadParam(prefix + "/radius_m", radius_m, 0.25, false);
            loader.LoadParam(prefix + "/height_m", height_m, 3.0, false);
            loader.LoadParam(prefix + "/point_spacing_m",
                             point_spacing_m, 0.05, false);
            loader.LoadParam(prefix + "/z_spacing_m", z_spacing_m, 0.10, false);
            loader.LoadParam(prefix + "/sensing_horizon_m",
                             sensing_horizon_m, 15.0, false);
            loader.LoadParam(prefix + "/intensity", intensity, 14545.0, false);
        }

        void validate() const {
            if (!enabled)
                return;
            if (speed_min_mps <= 0.0 || hold_s < 0.0 ||
                (scenario_version >= 5 && qualifying_samples <= 0) ||
                prediction_s <= 0.0 ||
                trigger_distance_min_m < 0.0 ||
                trigger_distance_max_m < trigger_distance_min_m ||
                trigger_waypoint_radius_m <= 0.0 || trap_waypoint_radius_m <= 0.0 ||
                sector_half_angle_deg <= 0.0 || sector_half_angle_deg >= 180.0 ||
                angular_margin_deg < 0.0 || max_nudge_deg < 0.0 ||
                radius_m <= 0.0 || height_m <= 0.0 || point_spacing_m <= 0.0 ||
                z_spacing_m <= 0.0 || sensing_horizon_m <= radius_m) {
                throw std::invalid_argument("invalid side_entry_v1 configuration");
            }
        }
    };

    struct SensorBurstDropoutConfig {
        bool enabled{false};
        double warmup_s{1.0};
        double period_s{2.0};
        double duration_s{0.5};
        double phase_s{0.0};
        bool phase_overridden_by_environment{false};

        void load(const std::string &path) {
            yaml_loader::YamlLoader loader(path);
            loader.LoadParam("sensor_burst_dropout/enabled", enabled, false,
                             false);
            loader.LoadParam("sensor_burst_dropout/warmup_s", warmup_s, 1.0,
                             false);
            loader.LoadParam("sensor_burst_dropout/period_s", period_s, 2.0,
                             false);
            loader.LoadParam("sensor_burst_dropout/duration_s", duration_s,
                             0.5, false);
            loader.LoadParam("sensor_burst_dropout/phase_s", phase_s, 0.0,
                             false);
            if (const char *override_value =
                        std::getenv("SUPER_SENSOR_BURST_DROPOUT_PHASE_S")) {
                char *end = nullptr;
                const double parsed = std::strtod(override_value, &end);
                if (end == override_value || *end != '\0' ||
                    !std::isfinite(parsed)) {
                    throw std::invalid_argument(
                            "invalid SUPER_SENSOR_BURST_DROPOUT_PHASE_S");
                }
                phase_s = parsed;
                phase_overridden_by_environment = true;
            }
        }

        void validate() const {
            if (!std::isfinite(warmup_s) || warmup_s < 0.0 ||
                !std::isfinite(period_s) || period_s <= 0.0 ||
                !std::isfinite(duration_s) || duration_s <= 0.0 ||
                duration_s >= period_s || !std::isfinite(phase_s) ||
                phase_s < 0.0 || phase_s >= period_s) {
                throw std::invalid_argument(
                        "invalid sensor_burst_dropout configuration");
            }
        }

        bool shouldDrop(const double elapsed_s) const {
            if (!enabled || !std::isfinite(elapsed_s))
                return false;
            const double first_start_s = warmup_s + phase_s;
            if (elapsed_s < first_start_s)
                return false;
            const double cycle_s = std::fmod(elapsed_s - first_start_s,
                                             period_s);
            return cycle_s >= 0.0 && cycle_s < duration_s;
        }
    };

    class PerfectDrone : public rclcpp::Node {
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
        super_utils::callback_timing_trace::State odom_trace_;
#endif
        std::shared_ptr<tf2_ros::TransformBroadcaster> br_map_ego_;

        Config cfg_;
        std::shared_ptr<marsim::MarsimRender> render_ptr_;
        double sys_start_t;
        int static_pc_poll_ms_{1};
        bool static_pc_durable_en_{false};
        bool static_pc_latched_en_{false};
        static_pc_latched::Evidence static_pc_latched_evidence_;
        std::atomic<std::uint64_t> static_pc_latched_poll_callbacks_{0};
        common_execution_policy::StaticPcPolicy static_pc_policy_;
        static_pc_two_phase::Policy static_pc_two_phase_policy_;
        std::chrono::steady_clock::time_point static_pc_policy_start_;
        rclcpp::TimerBase::SharedPtr odom_pub_timer_;
        rclcpp::TimerBase::SharedPtr global_pc_pub_timer_;
        rclcpp::TimerBase::SharedPtr global_pc_slow_pub_timer_;
        rclcpp::TimerBase::SharedPtr local_pc_pub_timer_;
        rclcpp::Subscription<mars_quadrotor_msgs::msg::PositionCommand>::SharedPtr cmd_sub_;
        rclcpp::CallbackGroup::SharedPtr odom_timer_cbk_group, global_pc_pub_cbk_group, local_pc_pub_cbk_group,
                cmd_sub_cbk_group;


        rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
        rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
        rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr robot_pub_;
        rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
        rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr local_pc_pub_;
        rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr global_pc_pub_;
        Vec3 position_, velocity_;
        double yaw_;
        Eigen::Quaterniond q_;
        std::string mesh_resource_;
        SensorCloudObserver local_cloud_observer_;
        AcquisitionProvider acquisition_provider_;
        AcquiredCloudObserver acquired_cloud_observer_;
        bool publish_raw_cloud_{true};
        using SensorCadenceClock = std::chrono::steady_clock;
        std::optional<SensorCadenceClock::time_point> first_sensor_frame_time_;
        std::optional<SensorCadenceClock::time_point> last_sensor_frame_time_;
        std::uint64_t sensor_frame_count_{0};
        std::uint64_t raw_cloud_publish_count_{0};
        std::uint64_t direct_cloud_handoff_count_{0};
        std::uint64_t sensor_payload_bytes_{0};

        SensorBurstDropoutConfig sensor_burst_dropout_cfg_;
        std::optional<SensorCadenceClock::time_point>
                first_delivered_sensor_frame_time_;
        std::optional<SensorCadenceClock::time_point>
                last_delivered_sensor_frame_time_;
        std::uint64_t sensor_delivered_frame_count_{0};
        std::uint64_t sensor_dropped_frame_count_{0};
        std::uint64_t sensor_dropped_payload_bytes_{0};
        std::uint64_t sensor_dropout_burst_count_{0};
        std::uint64_t sensor_dropout_consecutive_frames_{0};
        std::uint64_t sensor_dropout_max_consecutive_frames_{0};
        double sensor_delivered_max_gap_s_{0.0};
        bool sensor_dropout_active_{false};
        std::optional<double> sensor_fixed_render_time_s_;

        SideEntryV1Config side_entry_v1_cfg_;
        mutable std::mutex side_entry_v1_mutex_;
        std::optional<SensorCadenceClock::time_point> side_entry_v1_qualify_since_;
        bool side_entry_v1_spawned_{false};
        Eigen::Vector2d side_entry_v1_center_{Eigen::Vector2d::Zero()};
        pcl::PointCloud<marsim::PointType> side_entry_v1_cloud_;
        std::uint64_t side_entry_v1_injected_frames_{0};
        std::uint64_t side_entry_v1_command_callbacks_{0};
        std::uint64_t side_entry_v1_near_corner_samples_{0};
        std::uint64_t side_entry_v1_speed_gate_samples_{0};
        std::uint64_t side_entry_v1_prediction_gate_samples_{0};
        std::uint64_t side_entry_v1_mismatch_gate_samples_{0};
        std::uint64_t side_entry_v1_nudge_gate_samples_{0};
        std::uint64_t side_entry_v1_geometry_gate_samples_{0};
        std::uint64_t side_entry_v1_qualifying_samples_consecutive_{0};
        std::uint64_t side_entry_v1_qualifying_samples_max_{0};
        double side_entry_v1_corner_speed_max_{0.0};
        double side_entry_v1_prediction_distance_min_{
                std::numeric_limits<double>::infinity()};
        double side_entry_v1_prediction_distance_max_{0.0};
        double side_entry_v1_mismatch_max_deg_{0.0};
        double side_entry_v1_inner_edge_max_deg_{-
                std::numeric_limits<double>::infinity()};
        double side_entry_v1_velocity_outer_edge_min_deg_{
                std::numeric_limits<double>::infinity()};
        double side_entry_v1_trap_waypoint_distance_min_{
                std::numeric_limits<double>::infinity()};
        double side_entry_v1_qualifying_duration_max_s_{0.0};
        std::string side_entry_v1_event_json_;
        rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr side_entry_v1_marker_pub_;

        nav_msgs::msg::Odometry odom_;
        nav_msgs::msg::Path path_;


    public:
        explicit PerfectDrone(
                SensorCloudObserver local_cloud_observer = {},
                const bool publish_raw_cloud = true,
                const rclcpp::NodeOptions &node_options =
                        rclcpp::NodeOptions(),
                AcquisitionProvider acquisition_provider = {},
                AcquiredCloudObserver acquired_cloud_observer = {})
                : Node("perfect_tracking", node_options),
                  local_cloud_observer_(std::move(local_cloud_observer)),
                  acquisition_provider_(std::move(acquisition_provider)),
                  acquired_cloud_observer_(std::move(acquired_cloud_observer)),
                  publish_raw_cloud_(publish_raw_cloud) {
            // Matched Full control for the source-acquisition experiment.
            // Legacy runs do not set this process-local opt-in.
            if (const char *full_source = std::getenv("SUPER_SENSOR_FULL_ACQUISITION")) {
                if (std::string(full_source) != "1" || acquisition_provider_)
                    throw std::runtime_error("invalid/conflicting Full acquisition opt-in");
                acquisition_provider_ = []() {
                    return AcquisitionWindow{true, true, 0, 0.0, 45.0};
                };
                acquired_cloud_observer_ = [this](
                        const sensor_msgs::msg::PointCloud2::SharedPtr &cloud,
                        const AcquisitionWindow &) {
                    if (local_cloud_observer_) local_cloud_observer_(cloud);
                };
            }
            static_pc_poll_ms_ = common_execution_policy::parseStaticPcPollMs(
                    std::getenv("SUPER_STATIC_PC_POLL_MS"));
            static_pc_two_phase_policy_ = static_pc_two_phase::Policy(
                    static_pc_two_phase::parseEnabled(
                            std::getenv("SUPER_STATIC_PC_TWO_PHASE"), static_pc_poll_ms_));
            static_pc_durable_en_ = static_pc_durable::parseEnabled(
                    std::getenv("SUPER_STATIC_PC_DURABLE"), static_pc_poll_ms_,
                    static_pc_two_phase_policy_.enabled());
            static_pc_latched_en_ = static_pc_latched::parseEnabled(
                    std::getenv("SUPER_STATIC_PC_LATCHED_ONCE"), static_pc_durable_en_,
                    static_pc_poll_ms_, static_pc_two_phase_policy_.enabled(),
                    std::getenv("SUPER_STATIC_PC_CACHED_EXECUTOR"));
            // TODO: The current implementation uses a lenient QoS configuration for message transmission.
            const rclcpp::QoS qos(rclcpp::QoS(100)
                                          .best_effort()
                                          .keep_last(100)
                                          .durability_volatile());
            // ROG-Map's cloud subscription and update worker are both
            // explicitly latest-only. Keeping 100 multi-megabyte scans in
            // the raw writer cannot add usable map history; under sustained
            // Full traffic it instead lets stale samples occupy the DDS
            // writer path while the guard waits for a fresh map. Preserve
            // the complete 360-degree point set of every published sample,
            // but retain only the newest sample at the transport boundary.
            const rclcpp::QoS cloud_qos(rclcpp::QoS(1)
                                                .best_effort()
                                                .keep_last(1)
                                                .durability_volatile());
            // Position commands are state set-points, not a replayable event
            // stream.  Keeping a backlog can apply stale exploratory commands
            // after an emergency brake when rendering blocks the single-thread
            // executor, so retain only the newest command.
            const rclcpp::QoS command_qos(rclcpp::QoS(1)
                                                  .best_effort()
                                                  .keep_last(1)
                                                  .durability_volatile());

#define CONFIG_FILE_DIR(name) (std::string(std::string(ROOT_DIR) + "config/"+(name)))
            std::string dft_cfg_path = CONFIG_FILE_DIR("lidar_sim.yaml");
            std::string cfg_path, cfg_name;
            this->declare_parameter<std::string>("config_name", dft_cfg_path);

            if(this->get_parameter("config_name", cfg_name)){
                cfg_path = CONFIG_FILE_DIR(cfg_name);
                RCLCPP_WARN(this->get_logger(), " -- [MissionPlanner] Load config by file name: %s", cfg_path.c_str());
            }

            cfg_ = Config(cfg_path);
            side_entry_v1_cfg_.load(cfg_path);
            side_entry_v1_cfg_.validate();
            if (static_pc_latched_en_ && side_entry_v1_cfg_.enabled)
                throw std::invalid_argument(
                        "latched static geometry is not enabled for side-entry event scenarios");
            sensor_burst_dropout_cfg_.load(cfg_path);
            sensor_burst_dropout_cfg_.validate();
            if (const char *fixed_render_time =
                        std::getenv("SUPER_SENSOR_FIXED_RENDER_TIME_S")) {
                char *end = nullptr;
                const double parsed = std::strtod(fixed_render_time, &end);
                if (end == fixed_render_time || *end != '\0' ||
                    !std::isfinite(parsed)) {
                    throw std::invalid_argument(
                            "invalid SUPER_SENSOR_FIXED_RENDER_TIME_S");
                }
                sensor_fixed_render_time_s_ = parsed;
            }
            if (const char *event_path = std::getenv("SUPER_SIDE_ENTRY_V1_EVENT_JSON")) {
                side_entry_v1_event_json_ = event_path;
            }

            // 创建 TransformBroadcaster

            br_map_ego_ = std::make_shared<tf2_ros::TransformBroadcaster>(this);


            // 初始化 render_ptr_
            render_ptr_ = std::make_shared<marsim::MarsimRender>(cfg_path);

            // 订阅命令
            rclcpp::SubscriptionOptions so;
            cmd_sub_cbk_group = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
            so.callback_group = cmd_sub_cbk_group;
            cmd_sub_ = this->create_subscription<mars_quadrotor_msgs::msg::PositionCommand>(
                    "/planning/pos_cmd", command_qos,
                    std::bind(&PerfectDrone::cmdCallback, this, std::placeholders::_1),
                    so
            );

            // 发布 Odometry 消息
            odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("/lidar_slam/odom", qos);

            // 发布 Pose 消息
            pose_pub_ = this->create_publisher<geometry_msgs::msg::PoseStamped>("/lidar_slam/pose", qos);

            // 发布 Robot Marker
            robot_pub_ = this->create_publisher<visualization_msgs::msg::Marker>("robot", qos);

            // 发布 Path
            path_pub_ = this->create_publisher<nav_msgs::msg::Path>("path", qos);

            // 发布 PointCloud2 消息
            if (publish_raw_cloud_) {
                local_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(
                        "/cloud_registered", cloud_qos);
            }

            if (static_pc_durable_en_) {
                // Humble rejects TransientLocal with intra-process enabled.
                // Disable it for static geometry ONLY; acquired sensor paths,
                // odometry and command QoS remain unchanged. The separate
                // explicitly authorized latched opt-in changes static timers.
                rclcpp::PublisherOptions global_options;
                global_options.use_intra_process_comm = rclcpp::IntraProcessSetting::Disable;
                const auto global_qos = rclcpp::QoS(rclcpp::KeepLast(1))
                        .reliable().transient_local();
                global_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(
                        "/global_pc", global_qos, global_options);
            } else {
                global_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("/global_pc", qos);
            }
            const auto global_actual_qos = global_pc_pub_->get_actual_qos();
            const char* global_actual_reliability =
                    global_actual_qos.reliability() == rclcpp::ReliabilityPolicy::Reliable
                    ? "reliable" : global_actual_qos.reliability() == rclcpp::ReliabilityPolicy::BestEffort
                    ? "best_effort" : "unknown";
            const char* global_actual_durability =
                    global_actual_qos.durability() == rclcpp::DurabilityPolicy::TransientLocal
                    ? "transient_local" : global_actual_qos.durability() == rclcpp::DurabilityPolicy::Volatile
                    ? "volatile" : "unknown";
            const char* global_actual_history =
                    global_actual_qos.history() == rclcpp::HistoryPolicy::KeepLast
                    ? "keep_last" : global_actual_qos.history() == rclcpp::HistoryPolicy::KeepAll
                    ? "keep_all" : "unknown";
            RCLCPP_INFO(this->get_logger(),
                        "[STATIC_PC_DURABLE_SETTINGS] enabled=%d actual_qos=1 reliability=%s durability=%s "
                        "history=%s depth=%zu intra_process=%s publication_schedule=%s other_qos_unchanged=1",
                        static_pc_durable_en_, global_actual_reliability, global_actual_durability,
                        global_actual_history, global_actual_qos.depth(),
                        static_pc_durable_en_ ? "disabled" : "node_default",
                        static_pc_latched_en_ ? "latched_once" :
                            (static_pc_durable_en_ ? "legacy" : "existing"));
            if (side_entry_v1_cfg_.enabled) {
                side_entry_v1_marker_pub_ =
                        this->create_publisher<visualization_msgs::msg::Marker>(
                                "/side_entry_v1/marker", qos);
                RCLCPP_WARN(
                        this->get_logger(),
                        "SIDE_ENTRY_V%d armed: first corner=(%.2f, %.2f), "
                        "half_angle=%.1f deg, prediction=%.2f s, radius=%.2f m",
                        side_entry_v1_cfg_.scenario_version,
                        side_entry_v1_cfg_.trigger_waypoint_x,
                        side_entry_v1_cfg_.trigger_waypoint_y,
                        side_entry_v1_cfg_.sector_half_angle_deg,
                        side_entry_v1_cfg_.prediction_s,
                        side_entry_v1_cfg_.radius_m);
            }
            if (sensor_burst_dropout_cfg_.enabled) {
                RCLCPP_WARN(
                        this->get_logger(),
                        "SENSOR_BURST_DROPOUT armed before every cloud "
                        "transport: warmup=%.3fs period=%.3fs duration=%.3fs "
                        "phase=%.3fs env_override=%d",
                        sensor_burst_dropout_cfg_.warmup_s,
                        sensor_burst_dropout_cfg_.period_s,
                        sensor_burst_dropout_cfg_.duration_s,
                        sensor_burst_dropout_cfg_.phase_s,
                        sensor_burst_dropout_cfg_.phase_overridden_by_environment
                                ? 1 : 0);
            }
            if (sensor_fixed_render_time_s_) {
                RCLCPP_WARN(
                        this->get_logger(),
                        "SENSOR_FIXED_RENDER_TIME enabled for deterministic "
                        "replay only: t=%.6f",
                        *sensor_fixed_render_time_s_);
            }


            position_ = cfg_.init_pos;
            velocity_.setZero();
            yaw_ = cfg_.init_yaw;
            mesh_resource_ = cfg_.mesh_resource;
            q_ = Eigen::AngleAxisd(yaw_, Vec3::UnitZ());
            odom_.header.frame_id = "world";
            path_.poses.clear();
            path_.header.frame_id = "world";
            path_.header.stamp = this->get_clock()->now();


            odom_timer_cbk_group = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
            odom_pub_timer_ = this->create_wall_timer(
                    std::chrono::milliseconds(10),
                    std::bind(&PerfectDrone::publishOdom, this),
                    odom_timer_cbk_group
            );

            global_pc_pub_cbk_group = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
            static_pc_policy_start_ = std::chrono::steady_clock::now();
            RCLCPP_INFO(this->get_logger(),
                        "[STATIC_PC_POLL_SETTINGS] poll_ms=%d bootstrap_once=%d "
                        "complete_geometry=1 qos_unchanged=%d",
                        static_pc_latched_en_ ? 0 : static_pc_poll_ms_,
                        static_pc_latched_en_ || static_pc_poll_ms_ == 100, !static_pc_durable_en_);
            if (!static_pc_latched_en_) {
                global_pc_pub_timer_ = this->create_wall_timer(
                        std::chrono::milliseconds(static_pc_poll_ms_),
                        std::bind(&PerfectDrone::publishGlobalPCFast, this),
                        global_pc_pub_cbk_group);
            }

            if (static_pc_two_phase_policy_.enabled()) {
                // Same mutually-exclusive group owns both timers and the
                // unchanged publication/subscriber-count state. During startup
                // this slow callback returns without graph queries/publication.
                global_pc_slow_pub_timer_ = this->create_wall_timer(
                        std::chrono::milliseconds(100),
                        std::bind(&PerfectDrone::publishGlobalPCSlow, this),
                        global_pc_pub_cbk_group);
                RCLCPP_INFO(this->get_logger(),
                            "[STATIC_PC_TWO_PHASE] enabled=true phase=fast initial_poll_ms=1 "
                            "coarse_poll_ms=100 bootstrap_window_end_ros_s=5.1 "
                            "clock_fallback=permanent_legacy qos_unchanged=1");
            }

            const int publish_dt_ms = static_cast<int>((1.0 / cfg_.sensing_rate) * 1000);
            local_pc_pub_cbk_group = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
            local_pc_pub_timer_ = this->create_wall_timer(
                    std::chrono::milliseconds(publish_dt_ms),
                    std::bind(&PerfectDrone::publishPC, this),
                    local_pc_pub_cbk_group
            );

            sys_start_t = this->get_clock()->now().seconds();
            // Geometry and all state are initialized, and no executor can spin
            // this node until construction returns. DDS retains this one sample
            // for matching late/reconnecting readers while publisher is alive.
            if (static_pc_latched_en_) publishLatchedGlobalPC();
        }

        double getSensingRate() {
            return cfg_.sensing_rate;
        }

        // The renderer's GLFW window/GL context and glfwPollEvents() are
        // only valid on the thread that created them (GLFW requires event
        // functions to run on the creating/main thread). Callers must keep
        // this group on its own single-threaded executor on that thread
        // rather than folding it into a general multi-threaded pool.
        rclcpp::CallbackGroup::SharedPtr localPcCbkGroup() const {
            return local_pc_pub_cbk_group;
        }

        rclcpp::CallbackGroup::SharedPtr cmdSubCbkGroup() const {
            return cmd_sub_cbk_group;
        }

        rclcpp::CallbackGroup::SharedPtr odomTimerCbkGroup() const {
            return odom_timer_cbk_group;
        }

        rclcpp::CallbackGroup::SharedPtr globalPcPubCbkGroup() const {
            return global_pc_pub_cbk_group;
        }

        void reportSensorCadence() const {
            if (static_pc_latched_en_) {
                RCLCPP_INFO(this->get_logger(),
                        "[STATIC_PC_LATCHED_SUMMARY] enabled=1 publications=%lu points=%lu "
                        "bytes=%lu stamp_ns=%ld timers_created=%d poll_callbacks=%lu",
                        static_cast<unsigned long>(static_pc_latched_evidence_.publications),
                        static_cast<unsigned long>(static_pc_latched_evidence_.points),
                        static_cast<unsigned long>(static_pc_latched_evidence_.bytes),
                        static_cast<long>(static_pc_latched_evidence_.stamp_ns),
                        static_cast<int>(bool(global_pc_pub_timer_)) +
                            static_cast<int>(bool(global_pc_slow_pub_timer_)),
                        static_cast<unsigned long>(static_pc_latched_poll_callbacks_.load(std::memory_order_relaxed)));
            }
            double span_s = 0.0;
            if (first_sensor_frame_time_ && last_sensor_frame_time_) {
                span_s = std::chrono::duration<double>(
                        *last_sensor_frame_time_ - *first_sensor_frame_time_)
                                 .count();
            }
            const double rate_hz = span_s > 0.0 && sensor_frame_count_ > 1
                    ? static_cast<double>(sensor_frame_count_ - 1) / span_s
                    : 0.0;
            std::lock_guard<std::mutex> side_entry_lock(side_entry_v1_mutex_);
            RCLCPP_INFO(
                    this->get_logger(),
                    "[SENSOR_CADENCE_SUMMARY] frames=%lu span_s=%.6f "
                    "hz=%.6f raw_published=%lu direct_handoffs=%lu "
                    "payload_bytes=%lu side_entry_v1_enabled=%d "
                    "side_entry_v1_spawned=%d side_entry_v1_injected_frames=%lu",
                    static_cast<unsigned long>(sensor_frame_count_), span_s,
                    rate_hz,
                    static_cast<unsigned long>(raw_cloud_publish_count_),
                    static_cast<unsigned long>(direct_cloud_handoff_count_),
                    static_cast<unsigned long>(sensor_payload_bytes_),
                    side_entry_v1_cfg_.enabled ? 1 : 0,
                    side_entry_v1_spawned_ ? 1 : 0,
                    static_cast<unsigned long>(side_entry_v1_injected_frames_));
            RCLCPP_INFO(
                    this->get_logger(),
                    "[SENSOR_BURST_DROPOUT_SUMMARY] enabled=%d "
                    "warmup_s=%.6f period_s=%.6f duration_s=%.6f "
                    "phase_s=%.6f phase_env_override=%d rendered=%lu "
                    "delivered=%lu dropped=%lu bursts=%lu "
                    "max_consecutive_dropped=%lu max_delivered_gap_s=%.6f "
                    "dropped_payload_bytes=%lu",
                    sensor_burst_dropout_cfg_.enabled ? 1 : 0,
                    sensor_burst_dropout_cfg_.warmup_s,
                    sensor_burst_dropout_cfg_.period_s,
                    sensor_burst_dropout_cfg_.duration_s,
                    sensor_burst_dropout_cfg_.phase_s,
                    sensor_burst_dropout_cfg_.phase_overridden_by_environment
                            ? 1 : 0,
                    static_cast<unsigned long>(sensor_frame_count_),
                    static_cast<unsigned long>(sensor_delivered_frame_count_),
                    static_cast<unsigned long>(sensor_dropped_frame_count_),
                    static_cast<unsigned long>(sensor_dropout_burst_count_),
                    static_cast<unsigned long>(
                            sensor_dropout_max_consecutive_frames_),
                    sensor_delivered_max_gap_s_,
                    static_cast<unsigned long>(sensor_dropped_payload_bytes_));
            if (side_entry_v1_cfg_.enabled) {
                RCLCPP_INFO(
                        this->get_logger(),
                        "[SIDE_ENTRY_V1_DIAGNOSTICS] callbacks=%lu "
                        "near_corner=%lu speed_gate=%lu prediction_gate=%lu "
                        "mismatch_gate=%lu nudge_gate=%lu geometry_gate=%lu "
                        "corner_speed_max=%.6f prediction_distance_min=%.6f "
                        "prediction_distance_max=%.6f mismatch_max_deg=%.6f "
                        "inner_edge_max_deg=%.6f velocity_outer_edge_min_deg=%.6f "
                        "trap_waypoint_distance_min=%.6f "
                        "qualifying_duration_max_s=%.6f "
                        "qualifying_samples_required=%d "
                        "qualifying_samples_consecutive=%lu "
                        "qualifying_samples_max=%lu "
                        "require_yaw_velocity_mismatch=%d",
                        static_cast<unsigned long>(side_entry_v1_command_callbacks_),
                        static_cast<unsigned long>(side_entry_v1_near_corner_samples_),
                        static_cast<unsigned long>(side_entry_v1_speed_gate_samples_),
                        static_cast<unsigned long>(side_entry_v1_prediction_gate_samples_),
                        static_cast<unsigned long>(side_entry_v1_mismatch_gate_samples_),
                        static_cast<unsigned long>(side_entry_v1_nudge_gate_samples_),
                        static_cast<unsigned long>(side_entry_v1_geometry_gate_samples_),
                        side_entry_v1_corner_speed_max_,
                        std::isfinite(side_entry_v1_prediction_distance_min_)
                                ? side_entry_v1_prediction_distance_min_ : -1.0,
                        side_entry_v1_prediction_distance_max_,
                        side_entry_v1_mismatch_max_deg_,
                        std::isfinite(side_entry_v1_inner_edge_max_deg_)
                                ? side_entry_v1_inner_edge_max_deg_ : -1.0,
                        std::isfinite(side_entry_v1_velocity_outer_edge_min_deg_)
                                ? side_entry_v1_velocity_outer_edge_min_deg_ : -1.0,
                        std::isfinite(side_entry_v1_trap_waypoint_distance_min_)
                                ? side_entry_v1_trap_waypoint_distance_min_ : -1.0,
                        side_entry_v1_qualifying_duration_max_s_,
                        side_entry_v1_cfg_.qualifying_samples,
                        static_cast<unsigned long>(
                                side_entry_v1_qualifying_samples_consecutive_),
                        static_cast<unsigned long>(
                                side_entry_v1_qualifying_samples_max_),
                        side_entry_v1_cfg_.require_yaw_velocity_mismatch ? 1 : 0);
            }
        }


        void publishPC() {
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
            super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::SimRender);
#endif
            pcl::PointCloud<marsim::PointType>::Ptr local_map(new pcl::PointCloud<marsim::PointType>);
            // Capture immutable acquisition mode BEFORE rendering. Neither
            // the request nor its timestamp is replaced with the later state.
            const auto acquisition = acquisition_provider_
                    ? acquisition_provider_() : AcquisitionWindow{};
            const auto acquisition_stamp = this->get_clock()->now();
            const Eigen::Vector3f scan_position = position_.cast<float>();
            Eigen::Quaternionf scan_rotation = q_.cast<float>();
            if (acquisition.enabled) {
                if (side_entry_v1_cfg_.enabled || !acquired_cloud_observer_)
                    throw std::runtime_error("source acquisition requires typed handoff and no synthetic obstacle injection");
                render_ptr_->setHorizontalAcquisition(acquisition.full, acquisition.half_angle_deg);
                if (!acquisition.full) {
                    // Steer horizontal azimuth in the actual sensor plane;
                    // retain the vehicle's roll/pitch, not a post-cloud crop.
                    const Eigen::Vector3f world_heading(
                            std::cos(acquisition.center_yaw_rad),
                            std::sin(acquisition.center_yaw_rad), 0.0f);
                    const auto body_heading = scan_rotation.conjugate() * world_heading;
                    const float azimuth = std::atan2(body_heading.y(), body_heading.x());
                    scan_rotation = scan_rotation * Eigen::Quaternionf(
                            Eigen::AngleAxisf(azimuth, Eigen::Vector3f::UnitZ()));
                }
            }
            const auto cur_t = sensor_fixed_render_time_s_.value_or(
                    this->get_clock()->now().seconds());
            render_ptr_->renderOnceInWorld(scan_position, scan_rotation, cur_t, local_map);
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
            // Opt-in diagnostic evidence from the renderer output before any
            // synthetic injection, PointCloud2 conversion, filtering, or map
            // update.  It is never consulted by acquisition or flight logic.
            if (rog_map::contact_trace::enabled()) {
                try {
                    std::size_t roi_count = 0;
                    std::size_t retained_count = 0;
                    constexpr std::size_t kPointCap = 4096;
                    auto fields = rog_map::contact_trace::stream();
                    fields << "\"frame\":" << (sensor_frame_count_ + 1)
                           << ",\"stamp_ns\":" << acquisition_stamp.nanoseconds()
                           << ",\"acquisition_enabled\":"
                           << (acquisition.enabled ? "true" : "false")
                           << ",\"full\":" << (acquisition.full ? "true" : "false")
                           << ",\"cycle\":" << acquisition.cycle
                           << ",\"center_yaw_rad\":"
                           << rog_map::contact_trace::number(acquisition.center_yaw_rad)
                           << ",\"half_angle_deg\":"
                           << rog_map::contact_trace::number(acquisition.half_angle_deg)
                           << ",\"sensor_position\":["
                           << rog_map::contact_trace::number(scan_position.x()) << ','
                           << rog_map::contact_trace::number(scan_position.y()) << ','
                           << rog_map::contact_trace::number(scan_position.z()) << ']'
                           << ",\"sensor_quaternion_xyzw\":["
                           << rog_map::contact_trace::number(scan_rotation.x()) << ','
                           << rog_map::contact_trace::number(scan_rotation.y()) << ','
                           << rog_map::contact_trace::number(scan_rotation.z()) << ','
                           << rog_map::contact_trace::number(scan_rotation.w()) << ']'
                           << ",\"rendered_points\":" << local_map->size()
                           << ",\"roi_points\":[";
                    bool first = true;
                    for (const auto& point : *local_map) {
                        if (!rog_map::contact_trace::inRoi(point.x, point.y, point.z))
                            continue;
                        ++roi_count;
                        if (retained_count >= kPointCap) continue;
                        if (!first) fields << ',';
                        first = false;
                        fields << '[' << rog_map::contact_trace::number(point.x) << ','
                               << rog_map::contact_trace::number(point.y) << ','
                               << rog_map::contact_trace::number(point.z) << ','
                               << rog_map::contact_trace::number(point.intensity) << ']';
                        ++retained_count;
                    }
                    fields << "],\"roi_count\":" << roi_count
                           << ",\"roi_retained\":" << retained_count
                           << ",\"roi_truncated\":"
                           << (roi_count > retained_count ? "true" : "false");
                    rog_map::contact_trace::submit("sensor_render_cloud", fields.str());
                } catch (...) {
                    // Observation must not change the renderer handoff.
                }
            }
#endif
            appendSideEntryV1(position_, local_map);
            auto pc_msg = std::make_shared<sensor_msgs::msg::PointCloud2>();
            pcl::toROSMsg(*local_map, *pc_msg);
            pc_msg->header.frame_id = "world";
            pc_msg->header.stamp = acquisition.enabled ? acquisition_stamp : this->get_clock()->now();
            const auto sensor_frame_time = SensorCadenceClock::now();
            if (!first_sensor_frame_time_) {
                first_sensor_frame_time_ = sensor_frame_time;
            }
            last_sensor_frame_time_ = sensor_frame_time;
            ++sensor_frame_count_;
            if (acquisition.enabled) {
                RCLCPP_INFO(get_logger(),
                    "[SENSOR_ACQUISITION_FRAME] frame=%lu cycle=%lu full=%d stamp_ns=%ld width=%d height=%d readback_pixels=%lu conversion_rays=%lu generated_points=%lu bytes=%lu half_angle_deg=%.3f",
                    sensor_frame_count_, acquisition.cycle, acquisition.full ? 1 : 0,
                    acquisition_stamp.nanoseconds(), render_ptr_->acquisitionWidth(),
                    render_ptr_->acquisitionHeight(),
                    static_cast<unsigned long>(2ULL * render_ptr_->acquisitionWidth() * render_ptr_->acquisitionHeight()),
                    render_ptr_->conversionRays(), local_map->size(), pc_msg->data.size(),
                    acquisition.half_angle_deg);
            }
            std::cout << "Publish local map size: " << local_map->size() << std::endl;
            const double sensor_elapsed_s = std::chrono::duration<double>(
                    sensor_frame_time - *first_sensor_frame_time_).count();
            if (sensor_burst_dropout_cfg_.shouldDrop(sensor_elapsed_s)) {
                if (!sensor_dropout_active_)
                    ++sensor_dropout_burst_count_;
                sensor_dropout_active_ = true;
                ++sensor_dropped_frame_count_;
                ++sensor_dropout_consecutive_frames_;
                sensor_dropout_max_consecutive_frames_ = std::max(
                        sensor_dropout_max_consecutive_frames_,
                        sensor_dropout_consecutive_frames_);
                sensor_dropped_payload_bytes_ += pc_msg->data.size();
                if (sensor_frame_count_ % 50 == 0)
                    reportSensorCadence();
                return;
            }
            sensor_dropout_active_ = false;
            sensor_dropout_consecutive_frames_ = 0;
            if (!first_delivered_sensor_frame_time_)
                first_delivered_sensor_frame_time_ = sensor_frame_time;
            if (last_delivered_sensor_frame_time_) {
                sensor_delivered_max_gap_s_ = std::max(
                        sensor_delivered_max_gap_s_,
                        std::chrono::duration<double>(
                                sensor_frame_time -
                                *last_delivered_sensor_frame_time_).count());
            }
            last_delivered_sensor_frame_time_ = sensor_frame_time;
            ++sensor_delivered_frame_count_;
            sensor_payload_bytes_ += pc_msg->data.size();
            if (acquisition.enabled) {
                acquired_cloud_observer_(pc_msg, acquisition);
                ++direct_cloud_handoff_count_;
            } else if (local_cloud_observer_) {
                local_cloud_observer_(pc_msg);
                ++direct_cloud_handoff_count_;
            }
            if (publish_raw_cloud_ && local_pc_pub_) {
                local_pc_pub_->publish(*pc_msg);
                ++raw_cloud_publish_count_;
            }
            // Campaign runners terminate the launch tree after mission
            // completion, so destructor-time output is not guaranteed to
            // flush. Emit a compact checkpoint every 50 sensor frames; the
            // parser takes the latest complete summary.
            if (sensor_frame_count_ % 50 == 0) {
                reportSensorCadence();
            }
        }

        ~PerfectDrone() {}

    private:
        static double wrapAngle(const double angle) {
            return std::atan2(std::sin(angle), std::cos(angle));
        }

        static double yawFromQuaternion(const Eigen::Quaterniond &quaternion) {
            return std::atan2(
                    2.0 * (quaternion.w() * quaternion.z() +
                           quaternion.x() * quaternion.y()),
                    1.0 - 2.0 * (quaternion.y() * quaternion.y() +
                                 quaternion.z() * quaternion.z()));
        }

        void evaluateSideEntryV1(
                const mars_quadrotor_msgs::msg::PositionCommand::SharedPtr &msg) {
            if (!side_entry_v1_cfg_.enabled)
                return;

            std::lock_guard<std::mutex> lock(side_entry_v1_mutex_);
            ++side_entry_v1_command_callbacks_;
            if (side_entry_v1_spawned_)
                return;

            const auto reset_qualification = [this]() {
                side_entry_v1_qualify_since_.reset();
                side_entry_v1_qualifying_samples_consecutive_ = 0;
            };

            const Eigen::Vector2d position(msg->position.x, msg->position.y);
            const Eigen::Vector2d velocity(msg->velocity.x, msg->velocity.y);
            const Eigen::Vector2d acceleration(msg->acceleration.x, msg->acceleration.y);
            const Eigen::Vector2d jerk(msg->jerk.x, msg->jerk.y);
            const double speed = velocity.norm();
            const Eigen::Vector2d waypoint(
                    side_entry_v1_cfg_.trigger_waypoint_x,
                    side_entry_v1_cfg_.trigger_waypoint_y);
            const double trigger_waypoint_distance = (position - waypoint).norm();
            if (trigger_waypoint_distance >
                    side_entry_v1_cfg_.trigger_waypoint_radius_m) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_near_corner_samples_;
            side_entry_v1_corner_speed_max_ =
                    std::max(side_entry_v1_corner_speed_max_, speed);
            if (speed < side_entry_v1_cfg_.speed_min_mps) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_speed_gate_samples_;

            const double prediction_s = side_entry_v1_cfg_.prediction_s;
            Eigen::Vector2d candidate;
            if (side_entry_v1_cfg_.fixed_center_enabled) {
                candidate = Eigen::Vector2d(
                        side_entry_v1_cfg_.fixed_center_x,
                        side_entry_v1_cfg_.fixed_center_y);
            } else {
                candidate = position + velocity * prediction_s +
                        0.5 * acceleration * prediction_s * prediction_s +
                        jerk * prediction_s * prediction_s * prediction_s / 6.0;
            }
            Eigen::Vector2d delta = candidate - position;
            double distance = delta.norm();
            side_entry_v1_prediction_distance_min_ = std::min(
                    side_entry_v1_prediction_distance_min_, distance);
            side_entry_v1_prediction_distance_max_ = std::max(
                    side_entry_v1_prediction_distance_max_, distance);
            if (distance < side_entry_v1_cfg_.trigger_distance_min_m ||
                distance > side_entry_v1_cfg_.trigger_distance_max_m ||
                distance <= side_entry_v1_cfg_.radius_m) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_prediction_gate_samples_;

            const double velocity_yaw = std::atan2(velocity.y(), velocity.x());
            const double body_yaw = yawFromQuaternion(q_);
            const double signed_mismatch = wrapAngle(velocity_yaw - body_yaw);
            const double mismatch = std::abs(signed_mismatch);
            side_entry_v1_mismatch_max_deg_ = std::max(
                    side_entry_v1_mismatch_max_deg_, mismatch * 180.0 / M_PI);
            if (side_entry_v1_cfg_.require_yaw_velocity_mismatch &&
                mismatch < side_entry_v1_cfg_.yaw_velocity_mismatch_min_deg *
                                   M_PI / 180.0) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_mismatch_gate_samples_;

            double bearing = std::atan2(delta.y(), delta.x());
            double body_relative = wrapAngle(bearing - body_yaw);
            double angular_radius = std::asin(std::min(
                    1.0, side_entry_v1_cfg_.radius_m / distance));
            const double required_inner_edge =
                    (side_entry_v1_cfg_.sector_half_angle_deg +
                     side_entry_v1_cfg_.angular_margin_deg) * M_PI / 180.0;
            const double required_center_angle = required_inner_edge + angular_radius;
            const double required_nudge =
                    std::max(0.0, required_center_angle - std::abs(body_relative));
            const double max_nudge = side_entry_v1_cfg_.max_nudge_deg * M_PI / 180.0;
            if (required_nudge > max_nudge) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_nudge_gate_samples_;
            double signed_nudge = 0.0;
            if (required_nudge > 0.0) {
                const double direction =
                        std::copysign(1.0, std::abs(body_relative) > 1e-6
                                                  ? body_relative
                                                  : signed_mismatch);
                signed_nudge = direction * required_nudge;
                bearing += signed_nudge;
                candidate = position + distance * Eigen::Vector2d(
                        std::cos(bearing), std::sin(bearing));
                delta = candidate - position;
                body_relative = wrapAngle(bearing - body_yaw);
            }
            const double velocity_relative = wrapAngle(bearing - velocity_yaw);
            constexpr double geometry_epsilon_rad = 1e-9;
            const bool fully_outside_body_sector =
                    std::abs(body_relative) - angular_radius >=
                    required_inner_edge - geometry_epsilon_rad;
            const bool fully_inside_velocity_sector =
                    std::abs(velocity_relative) + angular_radius <=
                    side_entry_v1_cfg_.sector_half_angle_deg * M_PI / 180.0 +
                    geometry_epsilon_rad;
            const bool velocity_requirement_met =
                    !side_entry_v1_cfg_.require_velocity_inside ||
                    fully_inside_velocity_sector;
            const double trap_waypoint_distance = (candidate - waypoint).norm();
            side_entry_v1_inner_edge_max_deg_ = std::max(
                    side_entry_v1_inner_edge_max_deg_,
                    (std::abs(body_relative) - angular_radius) * 180.0 / M_PI);
            side_entry_v1_velocity_outer_edge_min_deg_ = std::min(
                    side_entry_v1_velocity_outer_edge_min_deg_,
                    (std::abs(velocity_relative) + angular_radius) * 180.0 / M_PI);
            side_entry_v1_trap_waypoint_distance_min_ = std::min(
                    side_entry_v1_trap_waypoint_distance_min_,
                    trap_waypoint_distance);
            const bool inside_predeclared_clear_disk =
                    trap_waypoint_distance <=
                    side_entry_v1_cfg_.trap_waypoint_radius_m + 1e-9;
            RCLCPP_INFO(
                    this->get_logger(),
                    "[SIDE_ENTRY_V1_CANDIDATE] distance=%.6f "
                    "trap_waypoint_distance=%.6f body_relative_deg=%.6f "
                    "velocity_relative_deg=%.6f angular_radius_deg=%.6f "
                    "inner_edge_deg=%.6f velocity_outer_edge_deg=%.6f "
                    "nudge_deg=%.6f outside_body=%d inside_velocity=%d "
                    "require_velocity_inside=%d inside_clear_disk=%d",
                    distance, trap_waypoint_distance,
                    body_relative * 180.0 / M_PI,
                    velocity_relative * 180.0 / M_PI,
                    angular_radius * 180.0 / M_PI,
                    (std::abs(body_relative) - angular_radius) * 180.0 / M_PI,
                    (std::abs(velocity_relative) + angular_radius) * 180.0 / M_PI,
                    signed_nudge * 180.0 / M_PI,
                    fully_outside_body_sector ? 1 : 0,
                    fully_inside_velocity_sector ? 1 : 0,
                    side_entry_v1_cfg_.require_velocity_inside ? 1 : 0,
                    inside_predeclared_clear_disk ? 1 : 0);
            if (!fully_outside_body_sector || !velocity_requirement_met ||
                !inside_predeclared_clear_disk) {
                reset_qualification();
                return;
            }
            ++side_entry_v1_geometry_gate_samples_;

            const auto now = SensorCadenceClock::now();
            if (!side_entry_v1_qualify_since_) {
                side_entry_v1_qualify_since_ = now;
            }
            ++side_entry_v1_qualifying_samples_consecutive_;
            side_entry_v1_qualifying_samples_max_ = std::max(
                    side_entry_v1_qualifying_samples_max_,
                    side_entry_v1_qualifying_samples_consecutive_);
            const double qualifying_s = std::chrono::duration<double>(
                    now - *side_entry_v1_qualify_since_).count();
            side_entry_v1_qualifying_duration_max_s_ = std::max(
                    side_entry_v1_qualifying_duration_max_s_, qualifying_s);
            if (side_entry_v1_cfg_.scenario_version >= 5) {
                if (side_entry_v1_qualifying_samples_consecutive_ <
                    static_cast<std::uint64_t>(
                            side_entry_v1_cfg_.qualifying_samples))
                    return;
            } else if (qualifying_s < side_entry_v1_cfg_.hold_s) {
                    return;
            }

            side_entry_v1_center_ = candidate;
            buildSideEntryV1Cloud();
            side_entry_v1_spawned_ = true;
            const double spawn_time_s = this->get_clock()->now().seconds();
            writeSideEntryV1Event(
                    spawn_time_s, position, body_yaw, velocity_yaw, mismatch,
                    speed, distance, body_relative, velocity_relative,
                    angular_radius, trap_waypoint_distance, signed_nudge);
            RCLCPP_WARN(
                    this->get_logger(),
                    "SIDE_ENTRY_V1_SPAWN center=(%.4f, %.4f) distance=%.3f "
                    "body_relative=%.2fdeg velocity_relative=%.2fdeg "
                    "inner_edge=%.2fdeg",
                    candidate.x(), candidate.y(), distance,
                    body_relative * 180.0 / M_PI,
                    velocity_relative * 180.0 / M_PI,
                    (std::abs(body_relative) - angular_radius) * 180.0 / M_PI);
        }

        void buildSideEntryV1Cloud() {
            side_entry_v1_cloud_.clear();
            const int theta_count = std::max(
                    16, static_cast<int>(std::ceil(
                            2.0 * M_PI * side_entry_v1_cfg_.radius_m /
                            side_entry_v1_cfg_.point_spacing_m)));
            const int z_count = std::max(
                    2, static_cast<int>(std::ceil(
                            side_entry_v1_cfg_.height_m /
                            side_entry_v1_cfg_.z_spacing_m)));
            side_entry_v1_cloud_.reserve(
                    static_cast<std::size_t>(theta_count) *
                    static_cast<std::size_t>(z_count + 1));
            for (int z_index = 0; z_index <= z_count; ++z_index) {
                const double z = side_entry_v1_cfg_.height_m *
                                 static_cast<double>(z_index) /
                                 static_cast<double>(z_count);
                for (int theta_index = 0; theta_index < theta_count; ++theta_index) {
                    const double theta = 2.0 * M_PI * theta_index / theta_count;
                    marsim::PointType point;
                    point.x = static_cast<float>(
                            side_entry_v1_center_.x() +
                            side_entry_v1_cfg_.radius_m * std::cos(theta));
                    point.y = static_cast<float>(
                            side_entry_v1_center_.y() +
                            side_entry_v1_cfg_.radius_m * std::sin(theta));
                    point.z = static_cast<float>(z);
                    point.intensity = static_cast<float>(side_entry_v1_cfg_.intensity);
                    side_entry_v1_cloud_.push_back(point);
                }
            }
        }

        void appendSideEntryV1(
                const Vec3 &camera_position,
                const pcl::PointCloud<marsim::PointType>::Ptr &local_map) {
            if (!side_entry_v1_cfg_.enabled)
                return;
            std::lock_guard<std::mutex> lock(side_entry_v1_mutex_);
            if (!side_entry_v1_spawned_)
                return;
            const double horizon_sq = side_entry_v1_cfg_.sensing_horizon_m *
                                      side_entry_v1_cfg_.sensing_horizon_m;
            std::size_t added = 0;
            for (const auto &point : side_entry_v1_cloud_) {
                const double dx = point.x - camera_position.x();
                const double dy = point.y - camera_position.y();
                const double dz = point.z - camera_position.z();
                if (dx * dx + dy * dy + dz * dz <= horizon_sq) {
                    local_map->push_back(point);
                    ++added;
                }
            }
            if (added > 0)
                ++side_entry_v1_injected_frames_;
            publishSideEntryV1Marker();
        }

        void publishSideEntryV1Marker() {
            if (!side_entry_v1_marker_pub_)
                return;
            visualization_msgs::msg::Marker marker;
            marker.header.frame_id = "world";
            marker.header.stamp = this->get_clock()->now();
            marker.ns = "side_entry_v1";
            marker.id = 1;
            marker.type = visualization_msgs::msg::Marker::CYLINDER;
            marker.action = visualization_msgs::msg::Marker::ADD;
            marker.pose.position.x = side_entry_v1_center_.x();
            marker.pose.position.y = side_entry_v1_center_.y();
            marker.pose.position.z = side_entry_v1_cfg_.height_m * 0.5;
            marker.pose.orientation.w = 1.0;
            marker.scale.x = 2.0 * side_entry_v1_cfg_.radius_m;
            marker.scale.y = 2.0 * side_entry_v1_cfg_.radius_m;
            marker.scale.z = side_entry_v1_cfg_.height_m;
            marker.color.r = 0.95f;
            marker.color.g = 0.15f;
            marker.color.b = 0.10f;
            marker.color.a = 0.9f;
            side_entry_v1_marker_pub_->publish(marker);
        }

        void writeSideEntryV1Event(
                const double spawn_time_s,
                const Eigen::Vector2d &position,
                const double body_yaw,
                const double velocity_yaw,
                const double mismatch,
                const double speed,
                const double distance,
                const double body_relative,
                const double velocity_relative,
                const double angular_radius,
                const double trap_waypoint_distance,
                const double signed_nudge) const {
            if (side_entry_v1_event_json_.empty())
                return;
            const std::string temporary_path = side_entry_v1_event_json_ + ".tmp";
            std::ofstream output(temporary_path);
            if (!output)
                return;
            output << std::fixed << std::setprecision(9)
                   << "{\n"
                   << "  \"side_entry_v1_event\": \"spawn\",\n"
                   << "  \"side_entry_v1_enabled\": true,\n"
                   << "  \"side_entry_scenario_version\": "
                   << side_entry_v1_cfg_.scenario_version << ",\n"
                   << "  \"side_entry_v1_geometry_valid\": true,\n"
                   << "  \"side_entry_v1_spawn_time_s\": " << spawn_time_s << ",\n"
                   << "  \"side_entry_v1_trigger_x\": " << position.x() << ",\n"
                   << "  \"side_entry_v1_trigger_y\": " << position.y() << ",\n"
                   << "  \"side_entry_v1_trigger_body_yaw_deg\": "
                   << body_yaw * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_trigger_velocity_yaw_deg\": "
                   << velocity_yaw * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_trigger_mismatch_deg\": "
                   << mismatch * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_trigger_speed_mps\": " << speed << ",\n"
                   << "  \"side_entry_v1_trap_x\": " << side_entry_v1_center_.x() << ",\n"
                   << "  \"side_entry_v1_trap_y\": " << side_entry_v1_center_.y() << ",\n"
                   << "  \"side_entry_v1_trap_distance_m\": " << distance << ",\n"
                   << "  \"side_entry_v1_trap_waypoint_distance_m\": "
                   << trap_waypoint_distance << ",\n"
                   << "  \"side_entry_v1_body_relative_deg\": "
                   << body_relative * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_velocity_relative_deg\": "
                   << velocity_relative * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_angular_radius_deg\": "
                   << angular_radius * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_inner_edge_deg\": "
                   << (std::abs(body_relative) - angular_radius) * 180.0 / M_PI
                   << ",\n"
                   << "  \"side_entry_v1_nudge_deg\": "
                   << signed_nudge * 180.0 / M_PI << ",\n"
                   << "  \"side_entry_v1_prediction_s\": "
                   << side_entry_v1_cfg_.prediction_s << ",\n"
                   << "  \"side_entry_require_yaw_velocity_mismatch\": "
                   << (side_entry_v1_cfg_.require_yaw_velocity_mismatch ?
                               "true" : "false")
                   << ",\n"
                   << "  \"side_entry_qualifying_samples_required\": "
                   << side_entry_v1_cfg_.qualifying_samples << ",\n"
                   << "  \"side_entry_qualifying_samples_observed\": "
                   << side_entry_v1_qualifying_samples_consecutive_ << ",\n"
                   << "  \"side_entry_require_velocity_inside\": "
                   << (side_entry_v1_cfg_.require_velocity_inside ?
                               "true" : "false")
                   << ",\n"
                   << "  \"side_entry_fixed_center_enabled\": "
                   << (side_entry_v1_cfg_.fixed_center_enabled ? "true" : "false")
                   << ",\n"
                   << "  \"side_entry_v1_sector_half_angle_deg\": "
                   << side_entry_v1_cfg_.sector_half_angle_deg << ",\n"
                   << "  \"side_entry_v1_radius_m\": "
                   << side_entry_v1_cfg_.radius_m << ",\n"
                   << "  \"side_entry_v1_height_m\": "
                   << side_entry_v1_cfg_.height_m << ",\n"
                   << "  \"side_entry_v1_intensity\": "
                   << side_entry_v1_cfg_.intensity << "\n"
                   << "}\n";
            output.close();
            if (std::rename(temporary_path.c_str(),
                            side_entry_v1_event_json_.c_str()) != 0) {
                std::remove(temporary_path.c_str());
            }
        }

        void cmdCallback(const mars_quadrotor_msgs::msg::PositionCommand::SharedPtr msg) {
            Vec3 pos(msg->position.x, msg->position.y, msg->position.z);
            Vec3 vel(msg->velocity.x, msg->velocity.y, msg->velocity.z);
            Vec3 acc(msg->acceleration.x, msg->acceleration.y, msg->acceleration.z);
            double yaw = msg->yaw;
            updateFlatness(pos, vel, acc, yaw);
            evaluateSideEntryV1(msg);
        }


        void advanceStaticPcTwoPhase() {
            if (!static_pc_two_phase_policy_.enabled()) return;
            const auto clock = this->get_clock();
            const double elapsed = clock->now().seconds() - sys_start_t;
            const bool simulated_time = clock->get_clock_type() == RCL_ROS_TIME &&
                                        clock->ros_time_is_active();
            const auto decision = static_pc_two_phase_policy_.observeAfterLegacy(
                    elapsed, simulated_time);
            if (decision.change == static_pc_two_phase::Change::Coarse) {
                // Current legacy callback has already processed this tick's
                // subscriber change before its fast timer is canceled.
                global_pc_pub_timer_->cancel();
                RCLCPP_INFO(this->get_logger(),
                            "[STATIC_PC_TWO_PHASE] enabled=true phase=coarse poll_ms=100 "
                            "ros_elapsed_s=%.9f fast_timer_canceled=%d "
                            "detection=nominal_not_delivery_guarantee",
                            elapsed, global_pc_pub_timer_->is_canceled());
            } else if (decision.change == static_pc_two_phase::Change::LegacyFallback) {
                if (decision.reset_fast_timer) global_pc_pub_timer_->reset();
                RCLCPP_WARN(this->get_logger(),
                            "[STATIC_PC_TWO_PHASE] enabled=true phase=legacy_fallback poll_ms=1 "
                            "ros_elapsed_s=%.9f reason=%s permanent=true",
                            elapsed, static_pc_two_phase::fallbackName(decision.fallback));
            }
        }

        void publishLatchedGlobalPC() {
            if (!static_pc_latched_en_ || static_pc_latched_evidence_.publications != 0 ||
                global_pc_pub_timer_ || global_pc_slow_pub_timer_)
                throw std::logic_error("invalid latched static publication state");
            const auto context = this->get_node_base_interface()->get_context();
            if (!rclcpp::ok(context))
                throw std::runtime_error("context stopped before latched static publication");
            pcl::PointCloud<marsim::PointType>::Ptr global_map(new pcl::PointCloud<marsim::PointType>);
            render_ptr_->getGlobalMap(global_map);
            if (!global_map || global_map->empty())
                throw std::runtime_error("latched static geometry is empty or failed to load");
            sensor_msgs::msg::PointCloud2 pc_msg;
            pcl::toROSMsg(*global_map, pc_msg);
            pc_msg.header.frame_id = "world";
            const auto stamp = this->get_clock()->now();
            pc_msg.header.stamp = stamp;
            if (pc_msg.point_step == 0 || pc_msg.data.empty() ||
                pc_msg.data.size() != static_cast<std::uint64_t>(pc_msg.row_step) * pc_msg.height ||
                static_cast<std::uint64_t>(pc_msg.width) * pc_msg.height != global_map->size())
                throw std::runtime_error("malformed latched static geometry");
            const std::array<std::string, 4> field_names{{"x", "y", "z", "intensity"}};
            const std::array<std::uint32_t, 4> field_offsets{{0, 4, 8, 16}};
            if (pc_msg.fields.size() != field_names.size())
                throw std::runtime_error("unexpected latched XYZI field count");
            for (std::size_t i = 0; i < field_names.size(); ++i) {
                const auto& field = pc_msg.fields[i];
                if (field.name != field_names[i] || field.offset != field_offsets[i] ||
                    field.datatype != sensor_msgs::msg::PointField::FLOAT32 || field.count != 1)
                    throw std::runtime_error("unexpected latched XYZI field layout");
            }
            static_pc_latched::canonicalizeXyziTailPadding(pc_msg.data, pc_msg.point_step);
            RCLCPP_INFO(this->get_logger(),
                    "[STATIC_PC_LATCHED_SERIALIZATION] point_step=32 tail_zeroed_bytes=12 "
                    "declared_fields_and_homogeneous_bytes_unchanged=1");
            auto evidence = static_pc_latched_evidence_;
            evidence.published(global_map->size(), pc_msg.data.size(), stamp.nanoseconds());
            if (!rclcpp::ok(context))
                throw std::runtime_error("context stopped before latched static publish call");
            global_pc_pub_->publish(pc_msg);
            // Humble publish may quietly return when context is invalid. A
            // local publish return is not a DDS delivery proof; readers verify
            // full bytes/layout and this exact timestamp in separate tests.
            if (!rclcpp::ok(context))
                throw std::runtime_error("context stopped during latched static publication");
            static_pc_latched_evidence_ = evidence;
            RCLCPP_INFO(this->get_logger(),
                    "[STATIC_PC_LATCHED_PUBLICATION] publications=%lu points=%lu bytes=%lu "
                    "stamp_ns=%ld timers_created=%d poll_callbacks=%lu complete_geometry=1",
                    static_cast<unsigned long>(static_pc_latched_evidence_.publications),
                    static_cast<unsigned long>(static_pc_latched_evidence_.points),
                    static_cast<unsigned long>(static_pc_latched_evidence_.bytes),
                    static_cast<long>(static_pc_latched_evidence_.stamp_ns),
                    static_cast<int>(bool(global_pc_pub_timer_)) +
                        static_cast<int>(bool(global_pc_slow_pub_timer_)),
                    static_cast<unsigned long>(static_pc_latched_poll_callbacks_.load(std::memory_order_relaxed)));
        }

        void rejectLatchedPoll() {
            if (static_pc_latched_en_) {
                static_pc_latched_poll_callbacks_.fetch_add(1, std::memory_order_relaxed);
                throw std::logic_error("legacy static poll called in latched-once mode");
            }
        }

        void publishGlobalPCFast() {
            rejectLatchedPoll();
            // A callback selected before cancel may arrive after handoff.
            if (!static_pc_two_phase_policy_.fastActive()) return;
            publishGlobalPC();
            advanceStaticPcTwoPhase();
        }

        void publishGlobalPCSlow() {
            rejectLatchedPoll();
            if (!static_pc_two_phase_policy_.coarseActive()) return;
            publishGlobalPC();
            advanceStaticPcTwoPhase();
        }

        void publishGlobalPC() {
            rejectLatchedPoll();
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
            super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::SimStaticCloud);
#endif
            if (static_pc_poll_ms_ == 100) {
                const auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::steady_clock::now() - static_pc_policy_start_).count();
                const auto subscribers = this->count_subscribers("/global_pc");
                const auto decision = static_pc_policy_.observe(elapsed_ns, subscribers);
                if (!decision.publish) return;
                // Same complete geometry, timestamp and publisher QoS as the
                // legacy path. This never changes acquired LiDAR scan input.
                pcl::PointCloud<marsim::PointType>::Ptr global_map(new pcl::PointCloud<marsim::PointType>);
                render_ptr_->getGlobalMap(global_map);
                sensor_msgs::msg::PointCloud2 pc_msg;
                pcl::toROSMsg(*global_map, pc_msg);
                pc_msg.header.frame_id = "world";
                pc_msg.header.stamp = this->get_clock()->now();
                global_pc_pub_->publish(pc_msg);
                static_pc_policy_.published(decision);
                RCLCPP_INFO(this->get_logger(),
                            "[STATIC_PC_PUBLICATION] points=%zu subscribers=%zu "
                            "bootstrap=%d count_change=%d poll_ms=%d",
                            global_map->size(), subscribers, decision.bootstrap,
                            decision.subscriber_change, static_pc_poll_ms_);
                return;
            }
            static int last_sub_num = 0;
            // update sub num
            int sub_num = this->count_subscribers("/global_pc");
            double cur_t = this->get_clock()->now().seconds() - sys_start_t;
            if (sub_num > 0 && last_sub_num != sub_num || (cur_t > 5.0 && cur_t < 5.1)) {
                pcl::PointCloud<marsim::PointType>::Ptr global_map(new pcl::PointCloud<marsim::PointType>);
                render_ptr_->getGlobalMap(global_map);
                sensor_msgs::msg::PointCloud2 pc_msg;
                pcl::toROSMsg(*global_map, pc_msg);
                pc_msg.header.frame_id = "world";
                pc_msg.header.stamp = this->get_clock()->now();
                global_pc_pub_->publish(pc_msg);
                std::cout << "Publish global map size: " << global_map->size() << std::endl;
            }
            last_sub_num = sub_num;
        }

        void publishOdom() {
#ifdef SUPER_SIM_CPU_PROFILE_SUPPORT
            const super_utils::callback_timing_trace::Scope wall_trace(odom_trace_, "SimOdom");
            super_utils::thread_cpu_profile::Scope cpu_scope(
                    super_utils::thread_cpu_profile::Stage::SimOdom);
#endif
            odom_.pose.pose.position.x = position_.x();
            odom_.pose.pose.position.y = position_.y();
            odom_.pose.pose.position.z = position_.z();

            odom_.pose.pose.orientation.x = q_.x();
            odom_.pose.pose.orientation.y = q_.y();
            odom_.pose.pose.orientation.z = q_.z();
            odom_.pose.pose.orientation.w = q_.w();

            odom_.twist.twist.linear.x = velocity_.x();
            odom_.twist.twist.linear.y = velocity_.y();
            odom_.twist.twist.linear.z = velocity_.z();

            odom_.header.stamp = this->get_clock()->now();


            odom_pub_->publish(odom_);

            geometry_msgs::msg::PoseStamped pose;
            pose.pose = odom_.pose.pose;
            pose.header = odom_.header;
            pose_pub_->publish(pose);

            geometry_msgs::msg::TransformStamped transformStamped;
            transformStamped.header.stamp = odom_.header.stamp;
            transformStamped.header.frame_id = "world";
            transformStamped.child_frame_id = "perfect_drone";
            transformStamped.transform.translation.x = odom_.pose.pose.position.x;
            transformStamped.transform.translation.y = odom_.pose.pose.position.y;
            transformStamped.transform.translation.z = odom_.pose.pose.position.z;
            transformStamped.transform.rotation.x = odom_.pose.pose.orientation.x;
            transformStamped.transform.rotation.y = odom_.pose.pose.orientation.y;
            transformStamped.transform.rotation.z = odom_.pose.pose.orientation.z;
            transformStamped.transform.rotation.w = odom_.pose.pose.orientation.w;

            // 发布变换
            br_map_ego_->sendTransform(transformStamped);

            visualization_msgs::msg::Marker meshROS;
            meshROS.header.frame_id = "world";
            meshROS.header.stamp = odom_.header.stamp;
            meshROS.ns = "mesh";
            meshROS.id = 0;
            meshROS.type = visualization_msgs::msg::Marker::MESH_RESOURCE;
            meshROS.action = visualization_msgs::msg::Marker::ADD;
            meshROS.pose.position = odom_.pose.pose.position;
            meshROS.pose.orientation = odom_.pose.pose.orientation;
            meshROS.scale.x = 1;
            meshROS.scale.y = 1;
            meshROS.scale.z = 1;
            meshROS.mesh_resource = mesh_resource_;
            meshROS.mesh_use_embedded_materials = true;
            meshROS.color.a = 1.0;
            meshROS.color.r = 0.0;
            meshROS.color.g = 0.0;
            meshROS.color.b = 0.0;
            robot_pub_->publish(meshROS);
            static int slow_down = 0;
            if (slow_down++ % 10 == 0) {
                if ((position_.head(2) - Vec3(0, -50, 1.5).head(2)).norm() < 1) {
                    path_.poses.clear();
                    path_.poses.reserve(10000);
                }
                path_.poses.push_back(pose);
                path_.header = odom_.header;
                path_pub_->publish(path_);
            }
        }

        void updateFlatness(const Vec3& pos, const Vec3& vel,
                            const Vec3& acc, const double yaw) {
            Vec3 gravity_ = 9.80 * Eigen::Vector3d(0, 0, 1);
            position_ = pos;
            velocity_ = vel;
            double a_T = (gravity_ + acc).norm();
            Eigen::Vector3d xB, yB, zB;
            Eigen::Vector3d xC(cos(yaw), sin(yaw), 0);

            zB = (gravity_ + acc).normalized();
            yB = ((zB).cross(xC)).normalized();
            xB = yB.cross(zB);
            Eigen::Matrix3d R;
            R << xB, yB, zB;
            q_ = Eigen::Quaterniond(R);
        }
    };
}


#endif
