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

#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/common/transforms.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl_conversions/pcl_conversions.h>

#include <Eigen/Geometry>
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

    rclcpp::QoS qos(rclcpp::KeepLast(5));
    qos.reliability(rclcpp::ReliabilityPolicy::Reliable);
    pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(output_topic_, qos);

    RCLCPP_INFO(get_logger(),
      "cloud_preprocessor: in='%s' -> out='%s' (target='%s') | sector_enable=%d angle=[%.0f,%.0f]deg | stride=%d(%d) voxel=%d(%.2f)",
      input_topic_.c_str(), output_topic_.c_str(), target_frame_.c_str(),
      sector_enable_?1:0, min_angle_rad_*180/M_PI, max_angle_rad_*180/M_PI,
      use_stride_?1:0, stride_, use_voxel_?1:0, voxel_leaf_);
  }

private:
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

    // 2) sector filter in SENSOR frame (forward = +x). atan2(y,x) is horizontal bearing.
    pcl::PointCloud<pcl::PointXYZ> filtered;
    filtered.reserve(cloud_sensor.size());
    for (size_t i = 0; i < cloud_sensor.size(); ++i) {
      if (use_stride_ && (i % static_cast<size_t>(stride_) != 0)) continue;
      const auto& p = cloud_sensor.points[i];
      if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) continue;
      if (sector_enable_) {
        const double ang = std::atan2(static_cast<double>(p.y), static_cast<double>(p.x));
        if (ang < min_angle_rad_ || ang > max_angle_rad_) continue;
      }
      filtered.push_back(p);
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
        "frame: %zu -> %zu pts (sector=%d), world='%s'",
        before, cloud_world.size(), sector_enable_?1:0, target_frame_.c_str());
  }

  // params
  std::string input_topic_, output_topic_, odom_topic_, target_frame_;
  double odom_timeout_;
  bool sector_enable_, use_stride_, use_voxel_;
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
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CloudPreprocessor>());
  rclcpp::shutdown();
  return 0;
}
