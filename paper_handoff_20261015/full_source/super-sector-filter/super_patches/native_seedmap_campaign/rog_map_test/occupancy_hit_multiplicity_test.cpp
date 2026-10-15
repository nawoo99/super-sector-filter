#include <rog_map/prob_map.h>

#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

// Offline regression against the real ProbMap implementation.  Supply the
// campaign YAML as argv[1].  --probe records the pre-fix behavior without
// asserting the desired hit-multiplicity contract; no ROS node is started.
class OccupancyProbe final : public rog_map::ProbMap {
 public:
  explicit OccupancyProbe(const char* config_path) {
    cfg_ = rog_map::Config(config_path);
    if (cfg_.raycasting_en || cfg_.point_filt_num != 1) {
      throw std::runtime_error("requires no-raycast campaign with point_filt_num=1");
    }
    // Keep the production probabilities and resolution; bound test allocation.
    cfg_.map_size_d = rog_map::Vec3f(16, 4, 4);
    cfg_.fix_map_origin = rog_map::Vec3f(0, 0, 1);
    cfg_.virtual_ground_height = -10;
    cfg_.virtual_ceil_height = 10;
    cfg_.resetMapSize();
    initProbMap();
  }

  struct Result {
    double before;
    double after;
    int hit_count;
    int miss_count;
    bool occupied;
    bool inflated;
  };

  Result duplicateHits(int point_count, bool reference) {
    const rog_map::Vec3f point(1.025, .025, 1.025);
    const int hash = getHashIndexFromPos(point);
    missPointUpdate(point, hash, 999);
    const double before = occupancy_buffer_[hash];
    int retained = point_count;
    if (reference) {
      // Original cache semantics: every retained sensor hit contributes once.
      hitPointUpdate(point, hash, point_count);
    } else {
      rog_map::PointCloud cloud;
      for (int i = 0; i < point_count; ++i) cloud.push_back(pclPoint(point));
      raycastProcess(cloud, rog_map::Vec3f(0, 0, 1));
      retained = raycast_data_.sparse_update_counts.at(hash).hit_cnt;
      probabilisticMapFromCache();
    }
    return {before, occupancy_buffer_[hash], retained, 0,
            ProbMap::isOccupied(point), isOccupiedInflate(point)};
  }

  Result observedMisses(bool full_raycast, bool on_axis,
                        bool seed_occupied = true) {
    for (const rog_map::Vec3f point : {
             rog_map::Vec3f(1.025, .025, 1.025),
             rog_map::Vec3f(.825, .075, .975),
             rog_map::Vec3f(.825, .025, 1.025)}) {
      missPointUpdate(point, getHashIndexFromPos(point), 999);
    }
    cfg_.raycasting_en = full_raycast;
    if (full_raycast && raycast_data_.operation_cnt.empty()) {
      raycast_data_.operation_cnt.resize(occupancy_buffer_.size(), 0);
      raycast_data_.hit_cnt.resize(occupancy_buffer_.size(), 0);
    }
    // The exact sensor rays have y<.001 and z>=1.0 throughout. They cannot
    // intersect this raw cell: x[.8,.85), y[.05,.1), z[.95,1.0).
    // The 0.15 m observed DDA nevertheless emits its centre (.825,.075,.975).
    const rog_map::Vec3f point = on_axis ? rog_map::Vec3f(.825, .025, 1.025)
                                        : rog_map::Vec3f(.825, .075, .975);
    const int hash = getHashIndexFromPos(point);
    missPointUpdate(point, hash, 999);
    hitPointUpdate(point, hash, seed_occupied ? 2 : 1);
    const double before = occupancy_buffer_[hash];
    rog_map::PointCloud cloud;
    // Distinct raw endpoint voxels bypass only the same-hit-voxel ray dedup.
    for (int i = 0; i < 100; ++i) {
      cloud.push_back(pclPoint(rog_map::Vec3f(1.525 + .05 * i, .001, 1.001)));
    }
    const rog_map::Vec3f sensor(0, 0, 1);
    updateLocalBox(sensor);
    raycastProcess(cloud, sensor);
    const auto found = raycast_data_.sparse_update_counts.find(hash);
    const int hits = full_raycast ? raycast_data_.hit_cnt[hash]
                      : found == raycast_data_.sparse_update_counts.end()
                            ? 0 : found->second.hit_cnt;
    const int operations = full_raycast ? raycast_data_.operation_cnt[hash]
                      : found == raycast_data_.sparse_update_counts.end()
                            ? 0 : found->second.operation_cnt;
    probabilisticMapFromCache();
    return {before, occupancy_buffer_[hash], hits, operations - hits,
            ProbMap::isOccupied(point), isOccupiedInflate(point)};
  }

 private:
  static pcl::PointXYZI pclPoint(const rog_map::Vec3f& point) {
    pcl::PointXYZI result;
    result.x = point.x();
    result.y = point.y();
    result.z = point.z();
    result.intensity = 100;
    return result;
  }
};

static void print(const char* label, const OccupancyProbe::Result& result) {
  std::cout << "PROBE " << label << " before=" << result.before
            << " after=" << result.after << " hit_count=" << result.hit_count
            << " miss_count=" << result.miss_count
            << " occupied=" << result.occupied
            << " inflated=" << result.inflated << '\n';
}

int main(int argc, char** argv) {
  if (argc < 2 || argc > 3) {
    std::cerr << "usage: occupancy_hit_multiplicity_test CONFIG [--probe]\n";
    return 2;
  }
  const bool probe_only = argc == 3 && std::string(argv[2]) == "--probe";
  OccupancyProbe map(argv[1]);
  std::cout << std::setprecision(12);
  bool passed = true;
  for (const int count : {2, 100}) {
    const auto actual = map.duplicateHits(count, false);
    const auto reference = map.duplicateHits(count, true);
    print("duplicate_actual", actual);
    print("original_multiplicity_reference", reference);
    passed = passed && actual.hit_count == count && actual.occupied &&
             actual.inflated && std::abs(actual.after - reference.after) < 1e-6;
  }
  const auto coarse_misses = map.observedMisses(false, false);
  const auto unknown_markers = map.observedMisses(false, false, false);
  const auto exact_off_axis = map.observedMisses(true, false);
  const auto exact_on_axis = map.observedMisses(true, true);
  print("no_raycast_off_axis_observed_misses", coarse_misses);
  print("no_raycast_unknown_cell_free_markers", unknown_markers);
  print("full_raycast_off_axis_misses", exact_off_axis);
  print("full_raycast_on_axis_misses", exact_on_axis);
  passed = passed && coarse_misses.miss_count == 100 &&
           coarse_misses.occupied && coarse_misses.inflated &&
           coarse_misses.before == coarse_misses.after &&
           unknown_markers.miss_count == 100 && !unknown_markers.occupied &&
           !unknown_markers.inflated && unknown_markers.after < 0 &&
           unknown_markers.after < unknown_markers.before &&
           exact_off_axis.miss_count == 0 && exact_off_axis.occupied &&
           exact_off_axis.inflated && exact_on_axis.miss_count == 100 &&
           !exact_on_axis.occupied && !exact_on_axis.inflated;
  if (!passed && !probe_only) {
    std::cerr << "FAIL: hit multiplicity or observed-free occupancy preservation\n";
    return 1;
  }
  return 0;
}
