#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>

struct Vec3f {
    static Vec3f Zero() { return {}; }
    double x() const { return 0; }
    double y() const { return 0; }
    double z() const { return 0; }
};
#include "production_types.inc"
#include "production_names.inc"
namespace fmt { template<class... T> void print(const char*, const T&...) {} }
namespace super_utils::thread_cpu_profile {
    enum class Stage { GuardCertificate };
    struct Scope { explicit Scope(Stage) {} };
}

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
struct Gate {
    std::mutex mutex;
    std::condition_variable condition;
    bool entered{false}, released{false};
    void hold() {
        std::unique_lock<std::mutex> lock(mutex);
        entered = true;
        condition.notify_all();
        require(condition.wait_for(lock, std::chrono::seconds(5), [&]{return released;}), "gate release timeout");
    }
    void waitEntered() {
        std::unique_lock<std::mutex> lock(mutex);
        require(condition.wait_for(lock, std::chrono::seconds(5), [&]{return entered;}), "gate entry timeout");
    }
    void release() {
        std::lock_guard<std::mutex> lock(mutex);
        released = true;
        condition.notify_all();
    }
};
struct Snapshot {
    bool empty{false};
    std::uint64_t generation{83};
    double start_wt{0};
    int pos_traj{0};
};
struct CommandFixture {
    mutable std::mutex mutex;
    Snapshot value;
    Snapshot snapshot() const { std::lock_guard<std::mutex> lock(mutex); return value; }
    std::uint64_t generation() const { return snapshot().generation; }
    void commit() { std::lock_guard<std::mutex> lock(mutex); ++value.generation; }
};
struct Health { std::uint64_t map_version{240}; };
struct MapFixture {
    std::atomic<std::uint64_t> version{240};
    Health getMapHealthSnapshot() const { return {version.load()}; }
};
class SuperPlanner {
public:
    CommandFixture cmd_traj_info_;
    std::function<TrajectorySafetyResult(std::uint64_t)> geometry;
    bool trajectoryValidationEnabled() const { return true; }
    auto getCommittedTrajectoryGeneration() const { return cmd_traj_info_.generation(); }
    auto getCommittedTrajectorySnapshot() const { return cmd_traj_info_.snapshot(); }
    TrajectorySafetyResult validatePositionTrajectory(int, double, std::uint64_t gen, bool) const { return geometry(gen); }
    TrajectorySafetyResult validateCommittedTrajectory(double now_wt) const;
};
#include "production_validation.inc"
struct ClockFixture { double getSimTime() const { return 10; } };
struct FsmFixture {
    struct { bool trajectory_guard_en{true}; } cfg_;
    MapFixture* map_ptr_;
    SuperPlanner* planner_ptr_;
    ClockFixture clock;
    ClockFixture* ros_ptr_{&clock};
    std::mutex safety_mutex_;
    TrajectorySafetyResult safety_certificate_;
    bool safety_certificate_valid_{false};
    std::atomic<bool> safety_revalidation_requested_{true};
    enum { FOLLOW_TRAJ } machine_state_{FOLLOW_TRAJ};
    bool fresh{true};
    int brakes{0};
    bool mapFreshEnoughForMotion(const Health&, double& age, double& limit, double& speed) {
        age = .007; limit = .5; speed = 6.8; return fresh;
    }
    void activateEmergencyBrake(const char*) { ++brakes; }
    FsmFixture(MapFixture& map, SuperPlanner& planner): map_ptr_(&map), planner_ptr_(&planner) {}
    #include "production_refresh.inc"
    void mainPre() {
        #include "production_decision.inc"
    }
};
TrajectorySafetyResult result(std::uint64_t gen, TrajectorySafetyStatus status = TrajectorySafetyStatus::SAFE) {
    TrajectorySafetyResult r;
    r.status = status; r.trajectory_generation = gen; r.map_version = 240;
    if (status == TrajectorySafetyStatus::OCCUPIED || status == TrajectorySafetyStatus::CLEARANCE_MARGIN) r.first_collision_tt = 1;
    return r;
}
int main() {
    try {
        for (int i = 0; i < 100; ++i) {
            // Baseline and real hazard/stale controls, with unchanged generation.
            for (auto status : {TrajectorySafetyStatus::SAFE, TrajectorySafetyStatus::OCCUPIED, TrajectorySafetyStatus::CLEARANCE_MARGIN, TrajectorySafetyStatus::VERSION_CHANGED}) {
                MapFixture map; SuperPlanner p; FsmFixture f(map, p);
                p.geometry = [=](auto gen){return result(gen, status);};
                f.mainPre();
                require(f.brakes == (status == TrajectorySafetyStatus::SAFE ? 0 : 1), "baseline/hazard decision mismatch");
            }
            {
                MapFixture map; SuperPlanner p; FsmFixture f(map, p);
                p.geometry = [](auto){throw std::runtime_error("stale map incorrectly checked geometry"); return result(0);};
                f.fresh = false; f.mainPre();
                require(f.brakes == 1 && f.safety_certificate_.status == TrajectorySafetyStatus::MAP_STALE, "map stale control failed");
            }
            // SAFE geometry becomes VERSION_CHANGED if a commit arrives mid-check.
            {
                MapFixture map; SuperPlanner p; FsmFixture f(map, p); Gate gate;
                p.geometry = [&](auto gen){ if(gen == 83) gate.hold(); return result(gen); };
                auto a = std::async(std::launch::async, [&]{f.mainPre();});
                gate.waitEntered(); p.cmd_traj_info_.commit(); gate.release(); a.get();
                require(f.brakes == 1 && f.safety_certificate_.status == TrajectorySafetyStatus::VERSION_CHANGED && f.safety_certificate_.trajectory_generation == 83, "generation replacement not reproduced");
                require(f.refreshSafetyCertificate("diagnostic_recheck") && f.safety_certificate_.trajectory_generation == 84, "fresh validation control failed");
            }
            // New SAFE certificate can be overwritten by older finishing work.
            {
                MapFixture map; SuperPlanner p; FsmFixture f(map, p); Gate gate;
                p.geometry = [&](auto gen){ if(gen == 83) gate.hold(); return result(gen); };
                auto a = std::async(std::launch::async, [&]{f.mainPre();});
                gate.waitEntered(); p.cmd_traj_info_.commit();
                const bool b_safe = f.refreshSafetyCertificate("replan_post");
                const auto b_certificate = f.safety_certificate_;
                gate.release(); a.get();
                require(b_safe && b_certificate.trajectory_generation == 84 && b_certificate.safe(), "new certificate not published");
                require(f.brakes == 1 && f.safety_certificate_.trajectory_generation == 83 && f.safety_certificate_.status == TrajectorySafetyStatus::VERSION_CHANGED, "old overwrite not reproduced");
            }
        }
        std::cout << "PASS 500/500 stable SAFE, OCCUPIED, CLEARANCE_MARGIN, map-stale and injected version-status controls\n"
                  << "REPRODUCED 100/100 SAFE geometry + concurrent commit -> VERSION_CHANGED -> brake request\n"
                  << "PASS 100/100 separate fresh-version rechecks return SAFE for controlled SAFE geometry\n"
                  << "REPRODUCED 100/100 old VERSION_CHANGED certificate overwrites already-published newer SAFE certificate\n"
                  << "Scope: extracted production control flow; stub geometry/store/time/map. No flight replay, no deployed fix.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n'; return 1;
    }
}
