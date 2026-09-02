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
#include "tf2_ros/transform_broadcaster.h"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <mutex>
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

    struct SideEntryV1Config {
        bool enabled{false};
        double speed_min_mps{2.0};
        double yaw_velocity_mismatch_min_deg{50.0};
        double hold_s{0.02};
        double prediction_s{0.8};
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
            loader.LoadParam("side_entry_v1/enabled", enabled, false, false);
            loader.LoadParam("side_entry_v1/speed_min_mps", speed_min_mps, 2.0, false);
            loader.LoadParam("side_entry_v1/yaw_velocity_mismatch_min_deg",
                             yaw_velocity_mismatch_min_deg, 50.0, false);
            loader.LoadParam("side_entry_v1/hold_s", hold_s, 0.02, false);
            loader.LoadParam("side_entry_v1/prediction_s", prediction_s, 0.8, false);
            loader.LoadParam("side_entry_v1/trigger_distance_min_m",
                             trigger_distance_min_m, 0.8, false);
            loader.LoadParam("side_entry_v1/trigger_distance_max_m",
                             trigger_distance_max_m, 3.5, false);
            loader.LoadParam("side_entry_v1/trigger_waypoint_x",
                             trigger_waypoint_x, 24.0, false);
            loader.LoadParam("side_entry_v1/trigger_waypoint_y",
                             trigger_waypoint_y, 24.0, false);
            loader.LoadParam("side_entry_v1/trigger_waypoint_radius_m",
                             trigger_waypoint_radius_m, 2.0, false);
            loader.LoadParam("side_entry_v1/trap_waypoint_radius_m",
                             trap_waypoint_radius_m, 2.0, false);
            loader.LoadParam("side_entry_v1/sector_half_angle_deg",
                             sector_half_angle_deg, 45.0, false);
            loader.LoadParam("side_entry_v1/angular_margin_deg",
                             angular_margin_deg, 2.0, false);
            loader.LoadParam("side_entry_v1/max_nudge_deg",
                             max_nudge_deg, 20.0, false);
            loader.LoadParam("side_entry_v1/radius_m", radius_m, 0.25, false);
            loader.LoadParam("side_entry_v1/height_m", height_m, 3.0, false);
            loader.LoadParam("side_entry_v1/point_spacing_m",
                             point_spacing_m, 0.05, false);
            loader.LoadParam("side_entry_v1/z_spacing_m", z_spacing_m, 0.10, false);
            loader.LoadParam("side_entry_v1/sensing_horizon_m",
                             sensing_horizon_m, 15.0, false);
            loader.LoadParam("side_entry_v1/intensity", intensity, 14545.0, false);
        }

        void validate() const {
            if (!enabled)
                return;
            if (speed_min_mps <= 0.0 || hold_s < 0.0 || prediction_s <= 0.0 ||
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

    class PerfectDrone : public rclcpp::Node {
        std::shared_ptr<tf2_ros::TransformBroadcaster> br_map_ego_;

        Config cfg_;
        std::shared_ptr<marsim::MarsimRender> render_ptr_;
        double sys_start_t;
        rclcpp::TimerBase::SharedPtr odom_pub_timer_;
        rclcpp::TimerBase::SharedPtr global_pc_pub_timer_;
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
        bool publish_raw_cloud_{true};
        using SensorCadenceClock = std::chrono::steady_clock;
        std::optional<SensorCadenceClock::time_point> first_sensor_frame_time_;
        std::optional<SensorCadenceClock::time_point> last_sensor_frame_time_;
        std::uint64_t sensor_frame_count_{0};
        std::uint64_t raw_cloud_publish_count_{0};
        std::uint64_t direct_cloud_handoff_count_{0};
        std::uint64_t sensor_payload_bytes_{0};

        SideEntryV1Config side_entry_v1_cfg_;
        mutable std::mutex side_entry_v1_mutex_;
        std::optional<SensorCadenceClock::time_point> side_entry_v1_qualify_since_;
        bool side_entry_v1_spawned_{false};
        Eigen::Vector2d side_entry_v1_center_{Eigen::Vector2d::Zero()};
        pcl::PointCloud<marsim::PointType> side_entry_v1_cloud_;
        std::uint64_t side_entry_v1_injected_frames_{0};
        std::string side_entry_v1_event_json_;
        rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr side_entry_v1_marker_pub_;

        nav_msgs::msg::Odometry odom_;
        nav_msgs::msg::Path path_;


    public:
        explicit PerfectDrone(
                SensorCloudObserver local_cloud_observer = {},
                const bool publish_raw_cloud = true,
                const rclcpp::NodeOptions &node_options =
                        rclcpp::NodeOptions())
                : Node("perfect_tracking", node_options),
                  local_cloud_observer_(std::move(local_cloud_observer)),
                  publish_raw_cloud_(publish_raw_cloud) {
            // TODO: The current implementation uses a lenient QoS configuration for message transmission.
            const rclcpp::QoS qos(rclcpp::QoS(100)
                                          .best_effort()
                                          .keep_last(100)
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
                local_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("/cloud_registered", qos);
            }

            global_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("/global_pc", qos);
            if (side_entry_v1_cfg_.enabled) {
                side_entry_v1_marker_pub_ =
                        this->create_publisher<visualization_msgs::msg::Marker>(
                                "/side_entry_v1/marker", qos);
                RCLCPP_WARN(
                        this->get_logger(),
                        "SIDE_ENTRY_V1 armed: first corner=(%.2f, %.2f), "
                        "half_angle=%.1f deg, prediction=%.2f s, radius=%.2f m",
                        side_entry_v1_cfg_.trigger_waypoint_x,
                        side_entry_v1_cfg_.trigger_waypoint_y,
                        side_entry_v1_cfg_.sector_half_angle_deg,
                        side_entry_v1_cfg_.prediction_s,
                        side_entry_v1_cfg_.radius_m);
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
            global_pc_pub_timer_ = this->create_wall_timer(
                    std::chrono::milliseconds(1),
                    std::bind(&PerfectDrone::publishGlobalPC, this),
                    global_pc_pub_cbk_group
            );

            const int publish_dt_ms = static_cast<int>((1.0 / cfg_.sensing_rate) * 1000);
            local_pc_pub_cbk_group = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
            local_pc_pub_timer_ = this->create_wall_timer(
                    std::chrono::milliseconds(publish_dt_ms),
                    std::bind(&PerfectDrone::publishPC, this),
                    local_pc_pub_cbk_group
            );

            sys_start_t = this->get_clock()->now().seconds();
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
        }


        void publishPC() {
            pcl::PointCloud<marsim::PointType>::Ptr local_map(new pcl::PointCloud<marsim::PointType>);
            const auto cur_t = this->get_clock()->now().seconds();
            render_ptr_->renderOnceInWorld(position_.cast<float>(), q_.cast<float>(), cur_t, local_map);
            appendSideEntryV1(position_, local_map);
            auto pc_msg = std::make_shared<sensor_msgs::msg::PointCloud2>();
            pcl::toROSMsg(*local_map, *pc_msg);
            pc_msg->header.frame_id = "world";
            pc_msg->header.stamp = this->get_clock()->now();
            const auto sensor_frame_time = SensorCadenceClock::now();
            if (!first_sensor_frame_time_) {
                first_sensor_frame_time_ = sensor_frame_time;
            }
            last_sensor_frame_time_ = sensor_frame_time;
            ++sensor_frame_count_;
            sensor_payload_bytes_ += pc_msg->data.size();
            std::cout << "Publish local map size: " << local_map->size() << std::endl;
            if (local_cloud_observer_) {
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
            if (side_entry_v1_spawned_)
                return;

            const Eigen::Vector2d position(msg->position.x, msg->position.y);
            const Eigen::Vector2d velocity(msg->velocity.x, msg->velocity.y);
            const Eigen::Vector2d acceleration(msg->acceleration.x, msg->acceleration.y);
            const Eigen::Vector2d jerk(msg->jerk.x, msg->jerk.y);
            const double speed = velocity.norm();
            const Eigen::Vector2d waypoint(
                    side_entry_v1_cfg_.trigger_waypoint_x,
                    side_entry_v1_cfg_.trigger_waypoint_y);
            const double trigger_waypoint_distance = (position - waypoint).norm();
            if (speed < side_entry_v1_cfg_.speed_min_mps ||
                trigger_waypoint_distance >
                        side_entry_v1_cfg_.trigger_waypoint_radius_m) {
                side_entry_v1_qualify_since_.reset();
                return;
            }

            const double prediction_s = side_entry_v1_cfg_.prediction_s;
            Eigen::Vector2d candidate =
                    position + velocity * prediction_s +
                    0.5 * acceleration * prediction_s * prediction_s +
                    jerk * prediction_s * prediction_s * prediction_s / 6.0;
            Eigen::Vector2d delta = candidate - position;
            double distance = delta.norm();
            if (distance < side_entry_v1_cfg_.trigger_distance_min_m ||
                distance > side_entry_v1_cfg_.trigger_distance_max_m ||
                distance <= side_entry_v1_cfg_.radius_m) {
                side_entry_v1_qualify_since_.reset();
                return;
            }

            const double velocity_yaw = std::atan2(velocity.y(), velocity.x());
            const double body_yaw = yawFromQuaternion(q_);
            const double signed_mismatch = wrapAngle(velocity_yaw - body_yaw);
            const double mismatch = std::abs(signed_mismatch);
            if (mismatch < side_entry_v1_cfg_.yaw_velocity_mismatch_min_deg *
                                   M_PI / 180.0) {
                side_entry_v1_qualify_since_.reset();
                return;
            }

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
                side_entry_v1_qualify_since_.reset();
                return;
            }
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
            const bool fully_outside_body_sector =
                    std::abs(body_relative) - angular_radius >= required_inner_edge;
            const bool fully_inside_velocity_sector =
                    std::abs(velocity_relative) + angular_radius <=
                    side_entry_v1_cfg_.sector_half_angle_deg * M_PI / 180.0;
            const double trap_waypoint_distance = (candidate - waypoint).norm();
            const bool inside_predeclared_clear_disk =
                    trap_waypoint_distance <=
                    side_entry_v1_cfg_.trap_waypoint_radius_m;
            if (!fully_outside_body_sector || !fully_inside_velocity_sector ||
                !inside_predeclared_clear_disk) {
                side_entry_v1_qualify_since_.reset();
                return;
            }

            const auto now = SensorCadenceClock::now();
            if (!side_entry_v1_qualify_since_) {
                side_entry_v1_qualify_since_ = now;
                return;
            }
            const double qualifying_s = std::chrono::duration<double>(
                    now - *side_entry_v1_qualify_since_).count();
            if (qualifying_s < side_entry_v1_cfg_.hold_s)
                return;

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


        void publishGlobalPC() {
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
