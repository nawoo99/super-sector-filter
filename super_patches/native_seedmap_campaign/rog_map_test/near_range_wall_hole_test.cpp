#include <rog_map/rog_map.h>

#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <cstdio>
#include <unistd.h>

// Offline, real-library diagnostic regression. This is a deliberately
// constructed dense wall, not a replay of unrecorded sensor points. Run each
// range in a fresh process: ProbMap initialization and startup clearing have
// process-static guards. No ROS node, renderer, or planner is started.
//
// CLI: near_range_wall_hole_test CONFIG --occupancy-min-range legacy|0.5|0.1
//      near_range_wall_hole_test CONFIG --test-config
// Only the new occupancy-hit minimum changes; ray_range/startup/free rays stay
// at the production .5m minimum. Original v2 broad-range fixture is preserved
// separately in results/scenario7_guard_v3_20260926/offline_wall_hole/.
class WallHoleProbe final : public rog_map::ROGMap {
 public:
  static rog_map::Vec3f heldSensor() {
    return {-3.7268038947764675, 3.5052099309384137, 2.467517505190736};
  }
  static rog_map::Vec3f firstContact() {
    return {-3.818210616665875, 3.483847125503175, 2.4686617574571397};
  }
  static rog_map::Vec3f centreInside() {
    return {-4.013501266431111, 3.484294077239634, 2.4389091380733467};
  }

  WallHoleProbe(const char* config, const double occupancy_min_range) {
    cfg_ = rog_map::Config(config);
    if (cfg_.raycasting_en || cfg_.map_sliding_en || cfg_.unk_inflation_en ||
        cfg_.point_filt_num != 1 || cfg_.batch_update_size != 1 ||
        std::abs(cfg_.resolution - .05) > 1e-12 ||
        std::abs(cfg_.inflation_resolution - .1) > 1e-12 ||
        cfg_.inflation_step != 3 || std::abs(cfg_.raycast_range_min - .5) > 1e-12 ||
        std::abs(YAML::LoadFile(config)["super_planner"]["robot_r"].as<double>() - .2) > 1e-12) {
      throw std::runtime_error("requires the fixed occupancy-only v2 campaign geometry settings");
    }
    // Bounded allocation; retain actual resolutions, probabilities, inflation,
    // ground/ceiling, point filter and observed-space marching policy.
    cfg_.map_size_d = rog_map::Vec3f(8, 8, 4);
    cfg_.fix_map_origin = rog_map::Vec3f(-3, 3, 1.5);
    cfg_.occupancy_only_min_range = occupancy_min_range;
    // Config construction already discretizes virtual bounds. resetMapSize
    // is not idempotent for those fields; resizing allocation must not apply
    // its inflation margin a second time in this fixture.
    const double ground = cfg_.virtual_ground_height;
    const double ceiling = cfg_.virtual_ceil_height;
    const int inf_ground = cfg_.inf_virtual_ground_height_id_g;
    const int inf_ceiling = cfg_.inf_virtual_ceil_height_id_g;
    cfg_.resetMapSize();
    cfg_.virtual_ground_height = ground;
    cfg_.virtual_ceil_height = ceiling;
    cfg_.inf_virtual_ground_height_id_g = inf_ground;
    cfg_.inf_virtual_ceil_height_id_g = inf_ceiling;
    initProbMap();
    // Use production publication/query functions without ROGMap::init(),
    // which opens shared diagnostic log files. These members are protected.
    immutable_snapshot_enabled_ = true;
    publishCommittedSnapshot(0);

    // Exercise the real startup-only clear at the mission's initial position,
    // far from the wall, BEFORE any held-pose Full fixture. This keeps the
    // startup clear distinct from the per-frame near-range hit rejection.
    const rog_map::Vec3f startup(0, 0, 1.5);
    rog_map::PointCloud startup_cloud;
    startup_cloud.push_back(point({0, 0, 2.5}));
    process(startup_cloud, startup);
    if (!ProbMap::isKnownFree(startup) ||
        !ProbMap::isKnownFree(rog_map::Vec3f(.35, 0, 1.5))) {
      throw std::runtime_error("real initial near-body clearing was not exercised");
    }
    std::cout << "STARTUP_CLEAR exercised=true sensor=[0,0,1.5] wall_distance_m="
              << (heldSensor() - startup).norm()
              << " unchanged_clear_radius_m=" << cfg_.raycast_range_min
              << " body_radius_m=0.2\n";
  }

  void assertNearHitAndRayContracts() {
    const double selected_minimum = cfg_.occupancy_only_min_range;
    const rog_map::Vec3f sensor(-1.5, 5, 1.5);
    const rog_map::Vec3f near(-1.25, 5, 1.5);
    rog_map::PointCloud duplicate_near;
    duplicate_near.push_back(point(near));
    duplicate_near.push_back(point(near));
    updateLocalBox(sensor);
    raycastProcess(duplicate_near, sensor);
    std::size_t hits = 0, misses = 0;
    for (const auto& entry : raycast_data_.sparse_update_counts) {
      hits += entry.second.hit_cnt;
      misses += entry.second.operation_cnt - entry.second.hit_cnt;
    }
    const bool retain_near = cfg_.occupancyOnlyMinRange() <= .25;
    if (hits != (retain_near ? 2U : 0U) || misses != 0)
      throw std::runtime_error("near-hit multiplicity/free-march separation violated");
    probabilisticMapFromCache();
    std::cout << "NEAR_HIT duplicate_hits=" << hits
              << " miss_candidates=" << misses << '\n';

    // A distant return must keep the exact original observed-ray candidates
    // when only the occupancy-hit minimum changes.
    rog_map::PointCloud far;
    far.push_back(point({0, 5, 1.5}));
    using Counts = std::map<int, std::pair<int, int>>;
    const auto cache_far = [&](double minimum) {
      cfg_.occupancy_only_min_range = minimum;
      raycastProcess(far, sensor);
      Counts out;
      for (const auto& entry : raycast_data_.sparse_update_counts)
        out.emplace(entry.first, std::make_pair(entry.second.operation_cnt,
                                               entry.second.hit_cnt));
      probabilisticMapFromCache();
      return out;
    };
    const auto legacy_far = cache_far(.5);
    const auto near_far = cache_far(.1);
    if (legacy_far != near_far)
      throw std::runtime_error("far observed-free ray cache changed");

    // Actual genuine-raycast branch must still apply ray_range[0]=.5 even
    // when the new occupancy-only override is .1.
    cfg_.raycasting_en = true;
    raycast_data_.operation_cnt.assign(occupancy_buffer_.size(), 0);
    raycast_data_.hit_cnt.assign(occupancy_buffer_.size(), 0);
    const rog_map::Vec3f ray_sensor(-1, 6, 1.5);
    const rog_map::Vec3f ray_near(-.75, 6, 1.5);
    rog_map::PointCloud ray_cloud;
    ray_cloud.push_back(point(ray_near));
    updateLocalBox(ray_sensor);
    raycastProcess(ray_cloud, ray_sensor);
    if (!raycast_data_.update_cache_id_g.empty() || ProbMap::isOccupied(ray_near))
      throw std::runtime_error("genuine raycasting near-range semantics changed");
    cfg_.raycasting_en = false;
    cfg_.occupancy_only_min_range = selected_minimum;
    std::cout << "RAY_CONTRACT far_cache_identical=true genuine_near_hit_rejected=true"
              << " original_min_m=" << cfg_.raycast_range_min
              << " effective_hit_min_m=" << cfg_.occupancyOnlyMinRange() << '\n';
  }

  void processWall() {
    rog_map::PointCloud wall;
    for (int j = 0; j <= 30; ++j) {
      for (int k = 0; k <= 30; ++k) {
        const auto p = point({-4, 3 + .05 * j, 1.5 + .05 * k});
        wall.push_back(p);
        const rog_map::Vec3f p64(p.x, p.y, p.z);
        rog_map::Vec3i id;
        posToGlobalIndex(p64, id);
        wall_ids_.emplace(id.x(), id.y(), id.z());
        if ((p64 - heldSensor()).norm() < cfg_.occupancyOnlyMinRange())
          ++near_rejected_;
      }
    }
    // Corresponds only to the count of the recent Full window, not its
    // unrecorded changing clouds. Repetition tests that repeated Full alone
    // cannot recover hits excluded by a deterministic range predicate.
    for (int frame = 0; frame < 14; ++frame) process(wall, heldSensor());
    std::cout << "WALL points_per_frame=" << wall.size()
              << " near_range_rejected_per_frame=" << near_rejected_
              << " accepted_per_frame=" << wall.size() - near_rejected_
              << " repeated_frames=14 snapshot_version="
              << loadPublishedSnapshot()->version << '\n';
  }

  struct Query {
    bool mutable_inflated;
    bool snapshot_inflated;
    bool physical_body_occupied;
    bool exhaustive_body_occupied;
    bool unknown;
    double nearest_raw;
    double nearest_box;
    std::size_t box_candidates;
  };

  Query query(const rog_map::Vec3f& p) const {
    Query out{};
    out.mutable_inflated = ProbMap::isOccupiedInflate(p);
    out.snapshot_inflated = ROGMap::isOccupiedInflate(p);
    out.unknown = ROGMap::isUnknown(p);
    out.nearest_raw = std::numeric_limits<double>::infinity();
    for (const auto& [x, y, z] : wall_ids_) {
      const rog_map::Vec3i id(x, y, z);
      if (!ProbMap::isOccupied(id)) continue;
      rog_map::Vec3f centre;
      globalIndexToPos(id, centre);
      out.nearest_raw = std::min(out.nearest_raw, (centre - p).norm());
      // Compare real mutable occupancy and real committed snapshot at the
      // same cell centre. This is a publication/index invariant, not a mock.
      if (!ROGMap::isOccupied(centre))
        throw std::runtime_error("mutable occupied wall cell missing from snapshot");
    }
    out.exhaustive_body_occupied = out.nearest_raw <= .2 + 1e-9;

    // Match current validatePositionTrajectory::physical_body_occupied's
    // unmasked body predicate using the real production boxSearch. This does
    // NOT invoke or claim to reproduce the complete trajectory validator.
    rog_map::vec_E<rog_map::Vec3f> occupied;
    const rog_map::Vec3f extent = rog_map::Vec3f::Constant(.2 + .5 * cfg_.resolution);
    ROGMap::boxSearch(p - extent, p + extent, rog_map::GridType::OCCUPIED, occupied);
    out.nearest_box = std::numeric_limits<double>::infinity();
    for (const auto& centre : occupied)
      out.nearest_box = std::min(out.nearest_box, (centre - p).norm());
    out.physical_body_occupied = out.nearest_box <= .2 + 1e-9;
    out.box_candidates = occupied.size();
    if (out.mutable_inflated != out.snapshot_inflated)
      throw std::runtime_error("mutable and snapshot inflation disagree");
    if (out.exhaustive_body_occupied != out.physical_body_occupied)
      throw std::runtime_error("body boxSearch disagrees with exhaustive wall-cell centres");
    return out;
  }

  bool nearWallOccupied() const {
    const auto p = point({-4, 3.5, 2.45});
    const rog_map::Vec3f q(p.x, p.y, p.z);
    const bool occupied = ProbMap::isOccupied(q);
    if (occupied != ROGMap::isOccupied(q))
      throw std::runtime_error("raw near-wall query differs across snapshot publication");
    return occupied;
  }

 private:
  const double getSystemWalltimeNow() override { return 0.0; }
  static pcl::PointXYZI point(const rog_map::Vec3f& p) {
    pcl::PointXYZI out;
    out.x = p.x(); out.y = p.y(); out.z = p.z(); out.intensity = 100;
    return out;
  }
  void process(const rog_map::PointCloud& cloud, const rog_map::Vec3f& p) {
    const rog_map::Pose pose(p, super_utils::Quatf::Identity());
    const auto result = updateProbMap(cloud, pose);
    if (!result.scan_processed || !result.map_committed)
      throw std::runtime_error("fixture cloud did not commit");
    publishCommittedSnapshot(++version_);
  }
  std::uint64_t version_{0};
  std::size_t near_rejected_{0};
  std::set<std::tuple<int, int, int>> wall_ids_;
};

static void printQuery(const char* label, const WallHoleProbe::Query& q) {
  std::cout << "QUERY label=" << label
            << " mutable_inflated=" << q.mutable_inflated
            << " snapshot_inflated=" << q.snapshot_inflated
            << " physical_body_occupied=" << q.physical_body_occupied
            << " exhaustive_body_occupied=" << q.exhaustive_body_occupied
            << " unknown_neighborhood=" << q.unknown
            << " nearest_raw_center_m=" << q.nearest_raw
            << " nearest_box_center_m=" << q.nearest_box
            << " box_candidates=" << q.box_candidates
            << " mandatory_pose_hard_check_reject=" << q.physical_body_occupied
            << " intermediate_inflation_short_circuit_clear=" << !q.snapshot_inflated
            << '\n';
}

int main(int argc, char** argv) {
  if (argc == 3 && std::string(argv[2]) == "--test-config") {
    try {
      const auto original = YAML::LoadFile(argv[1]);
      for (const std::string value : {"omitted", "0", "0.1", "0.5", "-1", "0.6", ".nan", ".inf"}) {
        auto modified = YAML::Clone(original);
        auto ray = modified["rog_map"]["raycasting"];
        if (value == "omitted") ray.remove("occupancy_only_min_range");
        else ray["occupancy_only_min_range"] = YAML::Load(value);
        YAML::Emitter emitter;
        emitter << modified;
        char path[] = "/tmp/scenario7_near_range_config_XXXXXX";
        const int descriptor = mkstemp(path);
        if (descriptor < 0) throw std::runtime_error("cannot create owned config fixture");
        FILE* file = fdopen(descriptor, "w");
        if (!file) { close(descriptor); unlink(path); throw std::runtime_error("fdopen failed"); }
        const auto written = fwrite(emitter.c_str(), 1, emitter.size(), file);
        const int closed = fclose(file);
        if (written != emitter.size() || closed != 0) {
          unlink(path); throw std::runtime_error("cannot write owned config fixture");
        }
        bool accepted = false;
        double effective = std::numeric_limits<double>::quiet_NaN();
        try {
          const rog_map::Config cfg(path);
          effective = cfg.occupancyOnlyMinRange();
          accepted = std::isfinite(effective) && cfg.raycast_range_min == .5;
        } catch (const std::exception&) {
          accepted = false;
        }
        unlink(path);
        const bool expected = value == "omitted" || value == "0" || value == "0.1" || value == "0.5";
        const double expected_minimum = value == "omitted" ? .5 : expected ? std::stod(value) : 0;
        if (accepted != expected || (accepted && std::abs(effective - expected_minimum) > 1e-12))
          throw std::runtime_error("config parser mismatch for " + value);
        std::cout << "CONFIG_CASE value=" << value << " accepted=" << accepted
                  << " effective_minimum=" << effective << '\n';
      }
      std::cout << "PASS actual_config_defaults_and_invalid_values\n";
      return 0;
    } catch (const std::exception& e) {
      std::cerr << "FAIL " << e.what() << '\n';
      return 1;
    }
  }
  if (argc != 4 || std::string(argv[2]) != "--occupancy-min-range" ||
      (std::string(argv[3]) != "legacy" && std::string(argv[3]) != "0.5" &&
       std::string(argv[3]) != "0.1")) {
    std::cerr << "usage: near_range_wall_hole_test CONFIG --occupancy-min-range legacy|0.5|0.1\n"
              << "       near_range_wall_hole_test CONFIG --test-config\n";
    return 2;
  }
  try {
    const bool current = std::string(argv[3]) != "0.1";
    const double min_range = std::string(argv[3]) == "legacy" ? -1 : current ? .5 : .1;
    std::cout << std::setprecision(15) << std::boolalpha
              << "FIXTURE constructed_not_flight_replay=true min_range_m="
              << min_range << " startup_clear_isolated=true\n";
    WallHoleProbe map(argv[1], min_range);
    map.assertNearHitAndRayContracts();
    map.processWall();
    const auto held = map.query(WallHoleProbe::heldSensor());
    const auto contact = map.query(WallHoleProbe::firstContact());
    const auto inside = map.query(WallHoleProbe::centreInside());
    printQuery("held_sensor", held);
    printQuery("first_analytic_contact", contact);
    printQuery("centre_inside", inside);
    const bool near_wall_occupied = map.nearWallOccupied();
    std::cout << "NEAR_WALL raw_and_snapshot_occupied=" << near_wall_occupied << '\n';
    const bool expected_hole = !near_wall_occupied &&
            !contact.snapshot_inflated && !contact.physical_body_occupied &&
            !inside.snapshot_inflated && !inside.physical_body_occupied;
    const bool expected_control = near_wall_occupied &&
            contact.snapshot_inflated && contact.physical_body_occupied &&
            inside.snapshot_inflated && inside.physical_body_occupied;
    if (!(current ? expected_hole : expected_control)) {
      std::cerr << "FAIL fixture did not establish the expected range-dependent contract\n";
      return 1;
    }
    std::cout << "PASS actual_library_range_fixture current_hole=" << current
              << " production_range_unchanged=true full_validator_invoked=false\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "FAIL " << e.what() << '\n';
    return 1;
  }
}
