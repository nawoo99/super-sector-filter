// Supplementary exact-production control-flow tests, not real-map geometry.
// Map predicates, linear trajectory, and midpoint DDA are explicit fixtures.
#include <Eigen/Core>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <thread>
#include <vector>
#include <fsm/initial_footprint_egress_receipt.hpp>
#include <fsm/stop_margin_certificate.hpp>
#include <rog_map/diagnostic_trace.hpp>

using Vec3f = Eigen::Vector3d;
template<class T> using vec_E = std::vector<T, Eigen::aligned_allocator<T>>;
namespace initial_egress = super_planner::initial_egress;
namespace stop_margin = super_planner::stop_margin;
namespace thread_cpu_profile {
enum class Stage { PlannerValidateGeometry };
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
    double duration{0.1};
    double getDuration() const { return duration; }
    Vec3f getPos(double t) const { return {t, 0.0, 1.0}; }
};
struct Trajectory {
    double start_WT{10.0};
    Piece piece;
    bool empty() const { return false; }
    std::size_t size() const { return 1; }
    const Piece& operator[](std::size_t) const { return piece; }
    double getTotalDuration() const { return piece.duration; }
};
struct MapConfig {
    double virtual_ground_height{-10.0}, virtual_ceil_height{10.0};
    double resolution{0.05}, inflation_resolution{0.1};
};
struct Health { std::uint64_t map_version{17}; bool update_in_progress{false}; };
enum class Hazard { None, Occupied, Unknown, Outside, FinalVersion, LaterTimeout };
struct Map {
    MapConfig config;
    Hazard hazard{Hazard::None};
    bool late_margin_band{false};
    bool wide_prefix_margin{false};
    mutable int health_reads{0};
    mutable bool visited_margin{false}, checked_margin_body{false};
    mutable bool visited_late_hazard{false}, visited_terminal{false};
    mutable int inflate_queries{0};
    std::chrono::steady_clock::time_point timeout_deadline{};
    bool isMargin(const Vec3f& p) const {
        if (wide_prefix_margin) return p.x() >= 0.0 && p.x() <= 0.600001;
        return late_margin_band ? p.x() >= 0.18 && p.x() <= 0.30
                                : p.x() >= 0.0 && p.x() <= 0.100001;
    }
    const MapConfig& getMapConfig() const { return config; }
    Health getMapHealthSnapshot() const {
        ++health_reads;
        if (hazard == Hazard::FinalVersion && health_reads == 3) {
            // This is the post-traversal read, not a changed initial snapshot.
            assert(visited_margin && checked_margin_body && visited_terminal);
            return {18, false};
        }
        return {17, false};
    }
    bool immutablePlannerSnapshotEnabled() const { return true; }
    struct ReadTransaction {};
    ReadTransaction acquireMapReadTransaction() const { return {}; }
    bool insideLocalMap(const Vec3f& p) const {
        if (p.x() >= 0.075 - 1e-12) visited_late_hazard = true;
        if (p.x() >= 0.1 - 1e-12) visited_terminal = true;
        return !(hazard == Hazard::Outside && p.x() >= 0.075 - 1e-12);
    }
    bool isUnknown(const Vec3f& p) const {
        return hazard == Hazard::Unknown && p.x() >= 0.075 - 1e-12;
    }
    bool isOccupiedInflate(const Vec3f& p) const {
        ++inflate_queries;
        const bool margin = isMargin(p);
        if (margin) visited_margin = true;
        if (hazard == Hazard::LaterTimeout && p.x() >= 0.65 && !timeout_trigger_visited) {
            // Real steady_clock and a generous deadline; no std clock override.
            // Fail rather than claim coverage if load expires the budget early.
            assert(visited_margin && checked_margin_body);
            timeout_trigger_visited = true;
            std::this_thread::sleep_until(timeout_deadline + std::chrono::milliseconds(10));
        }
        return margin;
    }
    mutable bool timeout_trigger_visited{false};
    void boxSearch(const Vec3f& lo, const Vec3f& hi, rog_map::GridType,
                   vec_E<Vec3f>& out) const {
        out.clear();
        const Vec3f point = (lo + hi) * 0.5;
        if (isMargin(point) && visited_margin) checked_margin_body = true;
        if (hazard == Hazard::Occupied && point.x() >= 0.075 - 1e-12)
            out.push_back(point);  // Fixture hard hit exactly at the body center.
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
        bool trajectory_guard_initial_footprint_egress_en{false};
        struct { double max_vel{1.0}; } exp_traj_cfg;
    } cfg_;
    Map* map_ptr_;
    double trajectory_guard_hard_clearance_m_{0.05};
    vec_E<Vec3f> trajectory_guard_clearance_offsets_;
    std::atomic<bool> guard_corridor_retry_pending_{false};
    explicit SuperPlanner(Map& map): map_ptr_(&map) {}
    bool trajectoryValidationEnabled() const { return true; }
    TrajectorySafetyResult validatePositionTrajectory(
        const Trajectory&, double, std::uint64_t, bool, bool, const Vec3f*, bool,
        const Vec3f*, std::chrono::steady_clock::time_point,
        const initial_egress::Receipt*, stop_margin::ValidationPolicy,
        bool allow_bounded_soft_margin_egress = false) const;
};
#include "validator.inc"

int main() {
    unsetenv("SUPER_G1_CONTACT_TRACE_DIR");
    using S = TrajectorySafetyStatus;
    const auto deferred = stop_margin::ValidationPolicy::DeferSoftMarginUntilHardChecksComplete;
    const auto ordinary = stop_margin::ValidationPolicy::RejectImmediately;
    const auto run = [&](Map& map, stop_margin::ValidationPolicy policy, double duration = 0.1,
                         std::chrono::steady_clock::time_point deadline =
                                 std::chrono::steady_clock::time_point::max(),
                         bool allow_bounded_soft_margin_egress = false) {
        SuperPlanner planner(map);
        Trajectory trajectory;
        trajectory.piece.duration = duration;
        return planner.validatePositionTrajectory(trajectory, 0.0, 9, true,
                true, nullptr, false, nullptr, deadline, nullptr, policy,
                allow_bounded_soft_margin_egress);
    };
    const auto emit = [](const char* name, const Map& map, const TrajectorySafetyResult& result) {
        std::cout << "case=" << name << " status=" << trajectorySafetyStatusName(result.status)
                  << " proof=" << result.hard_checks_complete
                  << " margin_visited=" << map.visited_margin
                  << " margin_body_checked=" << map.checked_margin_body
                  << " late_visited=" << map.visited_late_hazard
                  << " timeout_trigger_visited=" << map.timeout_trigger_visited
                  << " terminal_visited=" << map.visited_terminal
                  << " health_reads=" << map.health_reads << '\n';
    };
    int cases = 0;
    for (const auto policy : {ordinary, deferred}) {
        Map map;
        const auto result = run(map, policy);
        assert(map.visited_margin && map.checked_margin_body && map.visited_terminal);
        assert(map.inflate_queries == 5); // start, 2 midpoint DDA points, 2 endpoints.
        assert(result.status == S::CLEARANCE_MARGIN && result.first_collision_tt == 0.0);
        assert(!result.used_clearance_escape && !result.used_initial_footprint_egress);
        assert(result.checked_to_tt == 0.1);
        assert(result.hard_checks_complete == (policy == deferred));
        assert(map.health_reads == (policy == deferred ? 3 : 2));
        assert(stop_margin::admissibleStop(result.safe(), true, result.hard_checks_complete)
               == (policy == deferred));
        emit(policy == deferred ? "prefix_terminal_deferred" : "prefix_terminal_ordinary", map, result);
        ++cases;
    }
    for (const auto hazard : {Hazard::Occupied, Hazard::Unknown, Hazard::Outside}) {
        Map map;
        map.hazard = hazard;
        const auto result = run(map, deferred);
        const auto expected = hazard == Hazard::Occupied ? S::OCCUPIED
                            : hazard == Hazard::Unknown ? S::UNOBSERVED : S::OUT_OF_MAP;
        assert(map.visited_margin && map.checked_margin_body && map.visited_late_hazard);
        assert(result.status == expected && !result.hard_checks_complete);
        assert(result.first_collision_tt >= 0.075 - 1e-12);
        assert(!stop_margin::admissibleStop(result.safe(), false, result.hard_checks_complete));
        emit(hazard == Hazard::Occupied ? "prefix_then_occupied" :
             hazard == Hazard::Unknown ? "prefix_then_configured_unknown" : "prefix_then_outside", map, result);
        ++cases;
    }
    {
        Map map;
        map.hazard = Hazard::FinalVersion;
        const auto result = run(map, deferred);
        assert(map.health_reads == 3 && map.visited_terminal && map.checked_margin_body);
        assert(result.status == S::VERSION_CHANGED && !result.hard_checks_complete);
        assert(!result.used_clearance_escape);
        emit("final_prefix_then_version_change", map, result);
        ++cases;
    }
    {
        Map map;
        map.late_margin_band = true;
        const auto result = run(map, ordinary, 1.0);
        assert(map.visited_margin && map.checked_margin_body);
        assert(result.status == S::CLEARANCE_MARGIN && !result.hard_checks_complete);
        assert(result.first_collision_tt >= 0.18 && result.first_collision_tt <= 0.30);
        emit("ordinary_later_margin_control", map, result);
        ++cases;
    }
    {
        Map map;
        map.wide_prefix_margin = true;
        const auto result = run(map, ordinary, 1.0,
                std::chrono::steady_clock::time_point::max(), false);
        assert(result.status == S::CLEARANCE_MARGIN && !result.safe());
        assert(!result.used_clearance_escape && !result.hard_checks_complete);
        emit("wide_prefix_ordinary_rejected", map, result);
        ++cases;
    }
    {
        Map map;
        map.wide_prefix_margin = true;
        const auto result = run(map, ordinary, 1.0,
                std::chrono::steady_clock::time_point::max(), true);
        assert(result.status == S::SAFE && result.safe());
        assert(result.used_clearance_escape && result.hard_checks_complete);
        assert(result.clearance_escape_completed_tt > 0.6 &&
               result.clearance_escape_completed_tt < 1.0);
        emit("wide_prefix_certified_recovery_egress", map, result);
        ++cases;
    }
    {
        Map map;
        map.late_margin_band = true;
        map.hazard = Hazard::LaterTimeout;
        map.timeout_deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
        const auto result = run(map, deferred, 1.0, map.timeout_deadline);
        assert(map.visited_margin && map.checked_margin_body && map.timeout_trigger_visited);
        assert(result.status == S::VALIDATION_TIMEOUT && !result.hard_checks_complete);
        assert(!stop_margin::admissibleStop(result.safe(), false, result.hard_checks_complete));
        emit("deferred_margin_then_later_timeout", map, result);
        ++cases;
    }
    std::cout << "stop_margin_prefix_supplement_test: PASS cases=" << cases
              << " production=extracted_validator allow_initial_clearance_escape=true"
              << " fixtures=map_linear_trajectory_midpoint_dda"
              << " timeout=real_clock_visited_order_not_arbitrary_load_deterministic\n";
}
