// Exact extracted production validator; controlled map/trajectory/DDA fixtures.
// This proves its return/traversal policy, not real sensor geometry or flight.
#include <Eigen/Core>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <thread>
#include <vector>
#include <fsm/initial_footprint_egress_receipt.hpp>
#include <fsm/stop_margin_certificate.hpp>
#include <rog_map/diagnostic_trace.hpp>

using Vec3f = Eigen::Vector3d;
using StatePVAJ = Eigen::Matrix<double, 3, 4>;
template<class T> using vec_E = std::vector<T, Eigen::aligned_allocator<T>>;
namespace initial_egress = super_planner::initial_egress;
namespace stop_margin = super_planner::stop_margin;
namespace thread_cpu_profile {
enum class Stage { PlannerValidateGeometry, PlannerStopViability };
struct Scope { explicit Scope(Stage) {} };
}
namespace rog_map {
enum class GridType { OCCUPIED };
namespace raycaster {
class RayCaster {
    Vec3f midpoint_{Vec3f::Zero()};
    bool pending_{false};
public:
    explicit RayCaster(double) {}
    bool setInput(const Vec3f& a, const Vec3f& b) {
        midpoint_ = (a + b) * 0.5;
        pending_ = true;
        return true;
    }
    bool step(Vec3f& out) {
        if (!pending_) return false;
        out = midpoint_;
        pending_ = false;
        return true;
    }
};
}
}

#include "types.inc"
#include "names.inc"

struct Piece {
    double getDuration() const { return 1.0; }
    Vec3f getPos(double t) const { return {t, 0.0, 1.0}; }
};
struct Trajectory {
    double start_WT{10.0};
    bool empty_fixture{false};
    bool missing_state_fixture{false};
    bool nonfinite_state_fixture{false};
    Piece piece;
    bool empty() const { return empty_fixture; }
    std::size_t size() const { return 1; }
    const Piece& operator[](std::size_t) const { return piece; }
    double getTotalDuration() const { return 1.0; }
    bool getState(double t, StatePVAJ& state) const {
        if (missing_state_fixture && t >= 0.3) return false;
        state.setZero();
        state.col(0) = piece.getPos(t);
        if (nonfinite_state_fixture && t >= 0.3)
            state(0, 1) = std::numeric_limits<double>::quiet_NaN();
        return true;
    }
};
struct MapConfig {
    double virtual_ground_height{-10.0}, virtual_ceil_height{10.0};
    double resolution{0.05}, inflation_resolution{0.1};
};
struct Health { std::uint64_t map_version{17}; bool update_in_progress{false}; };
enum class Hazard { None, Occupied, Unknown, Outside, Version, Timeout };
struct Map {
    MapConfig config;
    Hazard hazard{Hazard::None};
    bool margin{true};
    mutable int health_reads{0};
    mutable bool visited_late_hazard{false};
    const MapConfig& getMapConfig() const { return config; }
    Health getMapHealthSnapshot() const {
        ++health_reads;
        return {(hazard == Hazard::Version && health_reads >= 3) ? 18U : 17U, false};
    }
    bool immutablePlannerSnapshotEnabled() const { return true; }
    struct ReadTransaction {};
    ReadTransaction acquireMapReadTransaction() const { return {}; }
    bool insideLocalMap(const Vec3f& p) const {
        if (p.x() >= 0.72) visited_late_hazard = true;
        return !(hazard == Hazard::Outside && p.x() >= 0.72);
    }
    bool isUnknown(const Vec3f& p) const {
        return hazard == Hazard::Unknown && p.x() >= 0.72;
    }
    bool isOccupiedInflate(const Vec3f& p) const {
        if (hazard == Hazard::Timeout && p.x() >= 0.65)
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        const bool soft = margin && p.x() >= 0.18 && p.x() <= 0.30;
        return soft || (hazard == Hazard::Occupied && std::abs(p.x() - 0.75) <= 0.055);
    }
    void boxSearch(const Vec3f& lo, const Vec3f& hi, rog_map::GridType,
                   vec_E<Vec3f>& out) const {
        out.clear();
        const Vec3f hit(0.75, 0.0, 1.0);
        if (hazard == Hazard::Occupied && (hit - lo).minCoeff() >= 0.0 &&
            (hi - hit).minCoeff() >= 0.0) out.push_back(hit);
    }
};
class SuperPlanner {
public:
    struct Config {
        bool trajectory_guard_unknown_as_occupied{true};
        double robot_r{0.025};
        double trajectory_guard_sample_dt_s{0.05};
        double trajectory_guard_escape_max_duration_s{1.0};
        double trajectory_guard_escape_entry_grace_s{0.0};
        double guard_viability_horizon_s{1.0};
        double guard_viability_sample_dt_s{0.3};
        bool trajectory_guard_initial_footprint_egress_en{false};
        struct { double max_vel{1.0}; } exp_traj_cfg;
    } cfg_;
    Map* map_ptr_;
    double trajectory_guard_hard_clearance_m_{0.05};
    vec_E<Vec3f> trajectory_guard_clearance_offsets_;
    std::atomic<bool> guard_corridor_retry_pending_{false};
    explicit SuperPlanner(Map& map): map_ptr_(&map) {}
    bool trajectoryValidationEnabled() const { return true; }
    bool certifiedStopExistsFrom(const StatePVAJ&, std::uint64_t,
                                 const Vec3f*, bool) const { return true; }
    bool candidateStopsViable(const Trajectory&, double, std::uint64_t,
                             const Vec3f*, bool) const;
    TrajectorySafetyResult validatePositionTrajectory(
        const Trajectory&, double, std::uint64_t, bool, bool, const Vec3f*, bool,
        const Vec3f*, std::chrono::steady_clock::time_point,
        const initial_egress::Receipt*, stop_margin::ValidationPolicy) const;
};
#include "validator.inc"
#include "candidate_states.inc"

int main() {
    unsetenv("SUPER_G1_CONTACT_TRACE_DIR");
    using S = TrajectorySafetyStatus;
    const auto full = stop_margin::ValidationPolicy::DeferSoftMarginUntilHardChecksComplete;
    const auto primary = stop_margin::ValidationPolicy::RejectImmediately;
    const auto run = [&](Map& map, const stop_margin::ValidationPolicy policy,
                         const bool unknown = true,
                         const std::chrono::steady_clock::time_point deadline =
                                 std::chrono::steady_clock::time_point::max()) {
        SuperPlanner planner(map);
        return planner.validatePositionTrajectory(Trajectory{}, 0.0, 9, false,
                unknown, nullptr, false, nullptr, deadline, nullptr, policy);
    };
    int cases = 0;
    for (const auto hazard : {Hazard::Occupied, Hazard::Unknown, Hazard::Outside}) {
        Map map;
        map.hazard = hazard;
        const auto old = run(map, primary);
        assert(old.status == S::CLEARANCE_MARGIN && !old.hard_checks_complete);
        assert(!map.visited_late_hazard);
        map.health_reads = 0;
        const auto checked = run(map, full);
        const auto expected = hazard == Hazard::Occupied ? S::OCCUPIED
                              : hazard == Hazard::Unknown ? S::UNOBSERVED : S::OUT_OF_MAP;
        assert(checked.status == expected && map.visited_late_hazard);
        assert(!checked.hard_checks_complete);
        assert(!stop_margin::admissibleStop(checked.safe(), checked.status == S::CLEARANCE_MARGIN,
                                            checked.hard_checks_complete));
        ++cases;
    }
    {
        Map map;
        const auto result = run(map, full);
        assert(result.status == S::CLEARANCE_MARGIN && result.hard_checks_complete);
        assert(map.visited_late_hazard && result.checked_to_tt == 1.0);
        assert(stop_margin::admissibleStop(false, true, result.hard_checks_complete));
        ++cases;
    }
    {
        Map map;
        map.margin = false;
        const auto result = run(map, full);
        assert(result.status == S::SAFE && result.hard_checks_complete);
        ++cases;
    }
    {
        Map map;
        map.hazard = Hazard::Unknown;
        const auto result = run(map, full, false);
        assert(result.status == S::CLEARANCE_MARGIN && result.hard_checks_complete);
        // Explicit false stays false; this repair does not invent unknown evidence.
        ++cases;
    }
    {
        Map map;
        map.hazard = Hazard::Version;
        const auto result = run(map, full);
        assert(result.status == S::VERSION_CHANGED && !result.hard_checks_complete);
        ++cases;
    }
    {
        Map map;
        map.hazard = Hazard::Timeout;
        const auto result = run(map, full, true,
                std::chrono::steady_clock::now() + std::chrono::milliseconds(2));
        assert(result.status == S::VALIDATION_TIMEOUT && !result.hard_checks_complete);
        ++cases;
    }
    {
        Map map;
        SuperPlanner planner(map);
        Trajectory trajectory;
        assert(planner.candidateStopsViable(trajectory, 0.0, 9, nullptr, false));
        trajectory.missing_state_fixture = true;
        assert(!planner.candidateStopsViable(trajectory, 0.0, 9, nullptr, false));
        trajectory.missing_state_fixture = false;
        trajectory.nonfinite_state_fixture = true;
        assert(!planner.candidateStopsViable(trajectory, 0.0, 9, nullptr, false));
        trajectory.nonfinite_state_fixture = false;
        trajectory.empty_fixture = true;
        assert(!planner.candidateStopsViable(trajectory, 0.0, 9, nullptr, false));
        trajectory.empty_fixture = false;
        planner.cfg_.guard_viability_sample_dt_s = 0.0;
        assert(!planner.candidateStopsViable(trajectory, 0.0, 9, nullptr, false));
        cases += 5;
    }
    std::cout << "stop_margin_validator_integration_test: PASS cases=" << cases
              << " production=extracted_validator fixtures=map_trajectory_dda\n";
}
