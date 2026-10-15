// Match PerfectDrone's asset root; the renderer library itself resolves its
// shaders relative to marsim_render. Do not silently test with an empty map.
#undef ROOT_DIR
#define ROOT_DIR SOURCE_TEST_ASSET_ROOT
#include <marsim_render/marsim_render.hpp>
#include <iostream>
#include <stdexcept>

// Real OpenGL renderer, stationary poses only. No vehicle/planner or commands.
int main(int argc, char **argv) {
  if (argc != 2) return 2;
  try {
    marsim::MarsimRender renderer(argv[1]);
    pcl::PointCloud<marsim::PointType>::Ptr truth;
    renderer.getGlobalMap(truth);
    if (!truth || truth->empty()) throw std::runtime_error("test map failed to load");
    std::cout << "SOURCE_TEST_MAP_POINTS " << truth->size() << '\n';
    pcl::KdTreeFLANN<marsim::PointType> tree;
    tree.setInputCloud(truth);
    std::uint64_t full_rays = 0;
    for (int i = 0; i < 16; ++i) {
      const bool full = i % 4 == 0 || i % 4 == 3;
      const Eigen::Vector3f position(0.0f, 0.0f, 1.5f);
      const Eigen::Quaternionf rotation =
          Eigen::Quaternionf(Eigen::AngleAxisf(i * 0.43f, Eigen::Vector3f::UnitZ())) *
          Eigen::Quaternionf(Eigen::AngleAxisf(0.22f, Eigen::Vector3f::UnitY())) *
          Eigen::Quaternionf(Eigen::AngleAxisf(-0.14f, Eigen::Vector3f::UnitX()));
      renderer.setHorizontalAcquisition(full, 45.0);
      auto cloud = pcl::make_shared<pcl::PointCloud<marsim::PointType>>();
      renderer.renderOnceInWorld(position, rotation, i * 0.1, cloud);
      if (renderer.acquisitionWidth() != (full ? 900 : 225) || cloud->empty())
        throw std::runtime_error("wrong source viewport or empty generated cloud");
      if (full) full_rays = renderer.conversionRays();
      else if (renderer.conversionRays() * 4 != full_rays)
        throw std::runtime_error("Sector still converted the full ray grid");
      double max_angle = 0;
      double max_truth_distance = 0;
      std::vector<int> nearest(1);
      std::vector<float> squared_distance(1);
      for (const auto &p : *cloud) {
        const Eigen::Vector3f sensor_point = rotation.conjugate() *
            (Eigen::Vector3f(p.x, p.y, p.z) - position);
        const double angle = std::abs(std::atan2(sensor_point.y(), sensor_point.x())) * 180.0 / M_PI;
        max_angle = std::max(max_angle, angle);
        if (!full && angle > 45.002)
          throw std::runtime_error("out-of-window point generated at source");
        if (tree.nearestKSearch(p, 1, nearest, squared_distance) != 1)
          throw std::runtime_error("missing map nearest neighbor");
        max_truth_distance = std::max(max_truth_distance,
                                      std::sqrt(static_cast<double>(squared_distance[0])));
      }
      if (max_truth_distance > 0.8)
        throw std::runtime_error("generated geometry disagrees with truth (stale depth/pose suspected)");
      std::cout << "SOURCE_TEST frame=" << i << " full=" << full
                << " width=" << renderer.acquisitionWidth()
                << " height=" << renderer.acquisitionHeight()
                << " conversion_rays=" << renderer.conversionRays()
                << " points=" << cloud->size() << " max_angle=" << max_angle
                << " max_truth_distance=" << max_truth_distance << '\n';
    }
    std::cout << "SOURCE_ACQUISITION_TEST_PASS frames=16 stale_full_readback=0 angular_leaks=0\n";
  } catch (const std::exception &e) {
    std::cerr << "SOURCE_ACQUISITION_TEST_FAIL " << e.what() << '\n';
    return 1;
  }
}
