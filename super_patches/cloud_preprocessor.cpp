// cloud_preprocessor.cpp
// ------------------------------------------------------------------
// Gazebo LiDAR(/points, sensor frame) -> [sector filter ±60°, sensor frame]
//   -> TF transform kept points to world frame -> /cloud_registered (world)
//
// SUPER's ROG-Map expects the input cloud already in the WORLD frame
// (it does NOT apply TF; odom is used only as the raycast origin).
// This node is also where our sector-filter contribution lives:
// filtering is done in the SENSOR frame BEFORE the TF transform, so the
// (expensive) transform only runs on the reduced cloud.
//
// G1 goal: verify /cloud_registered overlaps the obstacles in world frame.
// Adaptive recovery (full-view on waypoint/replan) is added later (G6).
// ------------------------------------------------------------------
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <std_msgs/msg/bool.hpp>

#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/common/transforms.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl_conversions/pcl_conversions.h>

#include <Eigen/Geometry>
#include <atomic>
#include <cmath>
#include <mutex>
#include <string>

class CloudPreprocessor : public rclcpp::Node
{
public:
  CloudPreprocessor() : rclcpp::Node("cloud_preprocessor")
  {
    // --- I/O ---
    input_topic_  = declare_parameter<std::string>("input_topic", "/points");
    output_topic_ = declare_parameter<std::string>("output_topic", "/cloud_registered");
    odom_topic_   = declare_parameter<std::string>("odom_topic", "/odometry");
    target_frame_ = declare_parameter<std::string>("target_frame", "world");
    odom_timeout_ = declare_parameter<double>("odom_timeout_sec", 0.5);

    // static body->lidar extrinsic (identity by default; this Gazebo setup has lidar at body origin).
    ext_xyz_ = declare_parameter<std::vector<double>>("lidar_ext_xyz", {0.0, 0.0, 0.0});
    ext_rpy_ = declare_parameter<std::vector<double>>("lidar_ext_rpy", {0.0, 0.0, 0.0});

    // --- sector filter ---
    sector_enable_ = declare_parameter<bool>("sector_enable", true);
    min_angle_rad_ = declare_parameter<double>("min_angle_deg", -60.0) * M_PI / 180.0;
    max_angle_rad_ = declare_parameter<double>("max_angle_deg",  60.0) * M_PI / 180.0;
    // runtime toggle: publish Bool here to turn the sector filter off (full 360 view)
    // for adaptive recovery at waypoints, then back on.
    sector_toggle_topic_ = declare_parameter<std::string>("sector_toggle_topic", "/sector/enable");

    // --- risk-gated auto-expansion (adaptive sector) ---
    // The ±60° forward cone is blind to obstacles abeam/behind. In a dense field the
    // drone passes side obstacles that were never freshly mapped -> clips. This gate
    // scans the RAW 360° cloud each frame: if any obstacle point OUTSIDE the sector is
    // within risk_range, that frame is expanded to full view (filter dropped) so ROG-Map
    // sees the side obstacle. Open legs (no near side obstacle) keep the ±60° savings.
    risk_gate_enable_ = declare_parameter<bool>("risk_gate_enable", false);
    risk_range_       = declare_parameter<double>("risk_range", 2.0);   // m (horizontal) side-obstacle trigger
    risk_hold_frames_ = std::max<int>(0, declare_parameter<int>("risk_hold_frames", 5)); // hysteresis: frames to stay expanded after last trigger
    risk_gate_topic_  = declare_parameter<std::string>("risk_gate_topic", "/sector/risk_gate");

    // --- performance options (match EGO defaults) ---
    use_stride_ = declare_parameter<bool>("use_stride", true);
    stride_     = std::max<int>(1, declare_parameter<int>("stride", 2));
    use_voxel_  = declare_parameter<bool>("use_voxel", true);
    voxel_leaf_ = declare_parameter<double>("voxel_leaf", 0.15);

    // static body->lidar extrinsic as Eigen affine
    T_body_lidar_ = Eigen::Affine3f::Identity();
    T_body_lidar_.translation() = Eigen::Vector3f(ext_xyz_[0], ext_xyz_[1], ext_xyz_[2]);
    T_body_lidar_.linear() =
        (Eigen::AngleAxisf(ext_rpy_[2], Eigen::Vector3f::UnitZ()) *
         Eigen::AngleAxisf(ext_rpy_[1], Eigen::Vector3f::UnitY()) *
         Eigen::AngleAxisf(ext_rpy_[0], Eigen::Vector3f::UnitX())).toRotationMatrix();

    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
        odom_topic_, rclcpp::SensorDataQoS(),
        std::bind(&CloudPreprocessor::odomCallback, this, std::placeholders::_1));

    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
        input_topic_, rclcpp::SensorDataQoS(),
        std::bind(&CloudPreprocessor::cloudCallback, this, std::placeholders::_1));

    sector_sub_ = create_subscription<std_msgs::msg::Bool>(
        sector_toggle_topic_, rclcpp::QoS(1).reliable(),
        std::bind(&CloudPreprocessor::sectorToggleCallback, this, std::placeholders::_1));

    risk_sub_ = create_subscription<std_msgs::msg::Bool>(
        risk_gate_topic_, rclcpp::QoS(1).reliable(),
        std::bind(&CloudPreprocessor::riskGateCallback, this, std::placeholders::_1));

    rclcpp::QoS qos(rclcpp::KeepLast(5));
    qos.reliability(rclcpp::ReliabilityPolicy::Reliable);
    pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(output_topic_, qos);

    RCLCPP_INFO(get_logger(),
      "cloud_preprocessor: in='%s' -> out='%s' (target='%s') | sector_enable=%d angle=[%.0f,%.0f]deg | risk_gate=%d range=%.2fm hold=%d | stride=%d(%d) voxel=%d(%.2f)",
      input_topic_.c_str(), output_topic_.c_str(), target_frame_.c_str(),
      sector_enable_?1:0, min_angle_rad_*180/M_PI, max_angle_rad_*180/M_PI,
      risk_gate_enable_?1:0, risk_range_, risk_hold_frames_,
      use_stride_?1:0, stride_, use_voxel_?1:0, voxel_leaf_);
  }

private:
  void sectorToggleCallback(const std_msgs::msg::Bool::SharedPtr msg)
  {
    const bool prev = sector_enable_.exchange(msg->data);
    if (prev != msg->data) {
      RCLCPP_INFO(get_logger(), "sector filter -> %s (runtime toggle)",
                  msg->data ? "ON (sector)" : "OFF (full 360 view)");
    }
  }

  void riskGateCallback(const std_msgs::msg::Bool::SharedPtr msg)
  {
    const bool prev = risk_gate_enable_.exchange(msg->data);
    if (prev != msg->data) {
      RCLCPP_INFO(get_logger(), "risk-gated auto-expansion -> %s",
                  msg->data ? "ON (sector expands to full-view near side obstacles)" : "OFF (fixed sector)");
    }
  }

  void odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
  {
    std::lock_guard<std::mutex> lk(odom_mtx_);
    // world <- body (world == map identity in this Gazebo setup)
    T_world_body_.translation() = Eigen::Vector3f(
        static_cast<float>(msg->pose.pose.position.x),
        static_cast<float>(msg->pose.pose.position.y),
        static_cast<float>(msg->pose.pose.position.z));
    T_world_body_.linear() = Eigen::Quaternionf(
        static_cast<float>(msg->pose.pose.orientation.w),
        static_cast<float>(msg->pose.pose.orientation.x),
        static_cast<float>(msg->pose.pose.orientation.y),
        static_cast<float>(msg->pose.pose.orientation.z)).toRotationMatrix();
    last_odom_t_ = now().seconds();
    have_odom_ = true;
  }

  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    // require fresh odom for a deterministic world transform
    Eigen::Affine3f T_world_lidar;
    {
      std::lock_guard<std::mutex> lk(odom_mtx_);
      if (!have_odom_) {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "no odom yet, skip cloud");
        return;
      }
      if (now().seconds() - last_odom_t_ > odom_timeout_) {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "odom timeout, skip cloud");
        return;
      }
      T_world_lidar = T_world_body_ * T_body_lidar_;
    }

    // 1) ROS -> PCL
    pcl::PointCloud<pcl::PointXYZ> cloud_sensor;
    pcl::fromROSMsg(*msg, cloud_sensor);
    if (cloud_sensor.empty()) return;
    const size_t before = cloud_sensor.size();

    // 2a) risk-gated auto-expansion: if the sector is ON and a close obstacle sits OUTSIDE
    //     the forward cone, expand THIS frame to full view so ROG-Map sees the side obstacle.
    //     Scans the raw cloud (strided) for the nearest out-of-sector point; a hysteresis
    //     hold keeps the full view for a few frames after the last trigger to avoid flapping
    //     and to cover the moment the obstacle passes abeam.
    bool sector_now = sector_enable_.load();
    bool risk_expanded = false;
    if (sector_now && risk_gate_enable_.load()) {
      const double risk_sq = risk_range_ * risk_range_;
      bool near_side = false;
      for (size_t i = 0; i < cloud_sensor.size() && !near_side; ++i) {
        if (use_stride_ && (i % static_cast<size_t>(stride_) != 0)) continue;
        const auto& p = cloud_sensor.points[i];
        if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) continue;
        const double ang = std::atan2(static_cast<double>(p.y), static_cast<double>(p.x));
        if (ang < min_angle_rad_ || ang > max_angle_rad_) {          // point is OUTSIDE the sector
          const double r_sq = static_cast<double>(p.x)*p.x + static_cast<double>(p.y)*p.y;
          if (r_sq < risk_sq) near_side = true;                      // ...and close -> risk
        }
      }
      if (near_side) risk_hold_ = risk_hold_frames_ + 1;             // (re)arm hold
      if (risk_hold_ > 0) { sector_now = false; --risk_hold_; risk_expanded = true; }
    }

    // 2b) sector filter in SENSOR frame (forward = +x). atan2(y,x) is horizontal bearing.
    pcl::PointCloud<pcl::PointXYZ> filtered;
    filtered.reserve(cloud_sensor.size());
    for (size_t i = 0; i < cloud_sensor.size(); ++i) {
      if (use_stride_ && (i % static_cast<size_t>(stride_) != 0)) continue;
      const auto& p = cloud_sensor.points[i];
      if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) continue;
      if (sector_now) {
        const double ang = std::atan2(static_cast<double>(p.y), static_cast<double>(p.x));
        if (ang < min_angle_rad_ || ang > max_angle_rad_) continue;
      }
      filtered.push_back(p);
    }
    if (risk_expanded) {
      RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000,
          "risk-gate: side obstacle < %.2fm outside sector -> full-view this frame", risk_range_);
    }
    if (filtered.empty()) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000,
                           "filtered cloud empty, skip frame");
      return;
    }

    // 3) optional voxel downsample (still in sensor frame)
    if (use_voxel_) {
      pcl::PointCloud<pcl::PointXYZ> voxel_out;
      pcl::VoxelGrid<pcl::PointXYZ> vg;
      vg.setInputCloud(filtered.makeShared());
      vg.setLeafSize(static_cast<float>(voxel_leaf_),
                     static_cast<float>(voxel_leaf_),
                     static_cast<float>(voxel_leaf_));
      vg.filter(voxel_out);
      filtered.swap(voxel_out);
    }

    // 4+5) transform kept points to world frame using odom-derived T (deterministic, no TF buffer)
    pcl::PointCloud<pcl::PointXYZ> cloud_world;
    pcl::transformPointCloud(filtered, cloud_world, T_world_lidar);

    // 6) publish in world frame
    sensor_msgs::msg::PointCloud2 out;
    pcl::toROSMsg(cloud_world, out);
    out.header.stamp = msg->header.stamp;
    out.header.frame_id = target_frame_;
    pub_->publish(out);

    RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000,
        "frame: %zu -> %zu pts (sector=%d%s), world='%s'",
        before, cloud_world.size(), sector_now?1:0,
        risk_expanded ? ",risk-expanded" : "", target_frame_.c_str());
  }

  // params
  std::string input_topic_, output_topic_, odom_topic_, target_frame_, sector_toggle_topic_, risk_gate_topic_;
  double odom_timeout_;
  std::atomic<bool> sector_enable_{true};   // runtime-toggleable (adaptive full-view recovery)
  std::atomic<bool> risk_gate_enable_{false}; // risk-gated auto-expansion of the sector
  double risk_range_{2.0};
  int risk_hold_frames_{5};
  int risk_hold_{0};                        // hysteresis countdown (touched only in cloudCallback)
  bool use_stride_, use_voxel_;
  double min_angle_rad_, max_angle_rad_, voxel_leaf_;
  int stride_;
  std::vector<double> ext_xyz_, ext_rpy_;

  // odom-derived transforms
  std::mutex odom_mtx_;
  bool have_odom_{false};
  double last_odom_t_{0.0};
  Eigen::Affine3f T_world_body_{Eigen::Affine3f::Identity()};
  Eigen::Affine3f T_body_lidar_{Eigen::Affine3f::Identity()};

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr sector_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr risk_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CloudPreprocessor>());
  rclcpp::shutdown();
  return 0;
}
