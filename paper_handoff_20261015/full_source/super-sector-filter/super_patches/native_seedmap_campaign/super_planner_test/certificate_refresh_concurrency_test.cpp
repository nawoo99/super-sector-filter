// Fixtures intentionally do not substitute for physical geometry verification.
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
struct Vec3f {
    static Vec3f Zero() { return {}; }
    double x() const { return 0; } double y() const { return 0; } double z() const { return 0; }
};
#include "types.inc"
#include "names.inc"
namespace fmt { template<class... T> void print(const char*, const T&...) {} }
namespace super_utils::thread_cpu_profile {
    enum class Stage { GuardCertificate };
    struct Scope { explicit Scope(Stage) {} };
}
using Clock = std::chrono::steady_clock;
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
struct Gate {
    std::mutex mutex; std::condition_variable cv;
    bool entered{false}, released{false};
    void hold() {
        std::unique_lock<std::mutex> lock(mutex); entered = true; cv.notify_all();
        require(cv.wait_for(lock, std::chrono::seconds(2), [&]{return released;}), "release timeout");
    }
    void wait() {
        std::unique_lock<std::mutex> lock(mutex);
        require(cv.wait_for(lock, std::chrono::seconds(2), [&]{return entered;}), "entry timeout");
    }
    void release() { std::lock_guard<std::mutex> lock(mutex); released = true; cv.notify_all(); }
};
struct Snapshot { bool empty{false}; std::uint64_t generation{83}; double start_wt{0}; int pos_traj{0}; };
struct Store {
    mutable std::mutex mutex; Snapshot value;
    auto snapshot() const { std::lock_guard<std::mutex> lock(mutex); return value; }
    auto generation() const { return snapshot().generation; }
    void commit() { std::lock_guard<std::mutex> lock(mutex); ++value.generation; }
};
struct Health { std::uint64_t map_version{240}; };
struct Map {
    bool immutable{true};
    std::atomic<std::uint64_t> version{240};
    Health getMapHealthSnapshot() const { return {version.load()}; }
    bool immutablePlannerSnapshotEnabled() const { return immutable; }
};
class SuperPlanner {
public:
    Store cmd_traj_info_;
    std::function<TrajectorySafetyResult(std::uint64_t, Clock::time_point)> geometry;
    bool trajectoryValidationEnabled() const { return true; }
    auto getCommittedTrajectoryGeneration() const { return cmd_traj_info_.generation(); }
    auto getCommittedTrajectorySnapshot() const { return cmd_traj_info_.snapshot(); }
    TrajectorySafetyResult validatePositionTrajectory(int, double, std::uint64_t g, bool,
            bool, const Vec3f*, bool, const Vec3f*, Clock::time_point deadline) const { return geometry(g, deadline); }
    TrajectorySafetyResult validateCommittedTrajectory(double, Clock::time_point) const;
};
#include "validation.inc"
struct Ros { double getSimTime() const { return 10; } };
struct Fsm {
    struct { bool trajectory_guard_en{true}; } cfg_;
    Map* map_ptr_; SuperPlanner* planner_ptr_; Ros ros; Ros* ros_ptr_{&ros};
    std::mutex safety_mutex_; TrajectorySafetyResult safety_certificate_;
    bool safety_certificate_valid_{false};
    std::uint64_t safety_validation_started_{0}, safety_certificate_validation_{0};
    std::atomic<bool> safety_revalidation_requested_{true};
    enum { FOLLOW_TRAJ } machine_state_{FOLLOW_TRAJ};
    bool fresh{true}; int brakes{0};
    Fsm(Map& m, SuperPlanner& p): map_ptr_(&m), planner_ptr_(&p) {}
    bool mapFreshEnoughForMotion(const Health&, double& age, double& limit, double& speed) {
        age = .007; limit = .5; speed = 6.8; return fresh;
    }
    void activateEmergencyBrake(const char*) { ++brakes; }
    #include "refresh.inc"
    void mainPre() {
        #include "decision.inc"
    }
};
using Status = TrajectorySafetyStatus;
TrajectorySafetyResult receipt(std::uint64_t g, Status status = Status::SAFE, std::uint64_t map = 240) {
    TrajectorySafetyResult r; r.status = status; r.trajectory_generation = g; r.map_version = map; return r;
}
int main() {
    try {
        int checks = 0;
        for (int i = 0; i < 100; ++i) {
            for (auto status : {Status::SAFE, Status::OCCUPIED, Status::CLEARANCE_MARGIN, Status::UNOBSERVED, Status::INVALID_TRAJECTORY}) {
                Map m; SuperPlanner p; Fsm f(m,p); int calls = 0;
                p.geometry = [&](auto g, auto){++calls; return receipt(g,status);};
                f.mainPre();
                require(f.brakes == (status == Status::SAFE ? 0 : 1) && calls == 1, "hazard rechecked or passed"); ++checks;
            }
            // Geometry errors survive concurrent commits; never retry hazards.
            {
                Map m; SuperPlanner p; Fsm f(m,p); int calls=0;
                p.geometry = [&](auto g, auto){++calls; p.cmd_traj_info_.commit(); return receipt(g,Status::OCCUPIED);};
                f.mainPre(); require(f.brakes == 1 && calls == 1, "hazard became version retry"); ++checks;
            }
            // Controlled same-thread interleaving commits during the old check.
            {
                Map m; SuperPlanner p; Fsm f(m,p); int calls=0;
                p.geometry = [&](auto g, auto deadline){++calls; if(calls == 1) p.cmd_traj_info_.commit();
                    else { require(deadline != Clock::time_point::max(), "retry missing deadline"); }
                    return receipt(g);};
                f.mainPre(); require(f.brakes == 0 && calls == 2 && f.safety_certificate_.trajectory_generation == 84, "fresh retry failed"); ++checks;
            }
            // Repeated changes are bounded to two attempts, then brake.
            {
                Map m; SuperPlanner p; Fsm f(m,p); int calls=0;
                p.geometry = [&](auto g, auto){++calls; p.cmd_traj_info_.commit(); return receipt(g);};
                f.mainPre(); require(f.brakes == 1 && calls == 2, "unbounded retry"); ++checks;
            }
            // No additional geometry retry on the unbounded legacy map lock.
            {
                Map m; m.immutable=false; SuperPlanner p; Fsm f(m,p); int calls=0;
                p.geometry = [&](auto g, auto){++calls; p.cmd_traj_info_.commit(); return receipt(g);};
                f.mainPre(); require(f.brakes == 1 && calls == 1, "legacy map retry"); ++checks;
            }
            // Requests that arrive during geometry remain pending.
            {
                Map m; SuperPlanner p; Fsm f(m,p);
                p.geometry = [&](auto g, auto){f.safety_revalidation_requested_.store(true); return receipt(g);};
                f.mainPre(); require(f.safety_revalidation_requested_.load(), "lost revalidation request"); ++checks;
            }
            // Map replacement between validation and publication also rechecks.
            {
                Map m; SuperPlanner p; Fsm f(m,p); int calls=0;
                p.geometry = [&](auto g, auto){++calls; auto v=m.version.load(); if(calls==1) ++m.version; return receipt(g,Status::SAFE,v);};
                f.mainPre(); require(f.brakes == 0 && calls == 2 && f.safety_certificate_.map_version == 241, "map retry failed"); ++checks;
            }
            // Real threads: preserve later SAFE or unsafe publication. Older
            // validation is held until the newer result has been published.
            for (auto latest : {Status::SAFE, Status::OCCUPIED}) {
                Map m; SuperPlanner p; Fsm f(m,p); Gate gate;
                p.geometry = [&](auto g, auto){if(g==83) gate.hold(); return receipt(g,g==83 ? Status::SAFE : latest);};
                auto a=std::async(std::launch::async,[&]{f.mainPre();});
                gate.wait(); p.cmd_traj_info_.commit();
                bool b=f.refreshSafetyCertificate("replan_post");
                gate.release(); a.get();
                require(b == (latest==Status::SAFE) && f.brakes == (latest==Status::SAFE ? 0 : 1) &&
                        f.safety_certificate_.trajectory_generation == 84 && f.safety_certificate_.status == latest, "old result overwrote new certificate"); ++checks;
            }
            {
                Map m; SuperPlanner p; Fsm f(m,p); Gate gate; std::atomic<int> calls{0};
                p.geometry = [&](auto g, auto){if(++calls==1) {gate.hold(); return receipt(g);}
                    return receipt(g,Status::OCCUPIED);};
                auto a=std::async(std::launch::async,[&]{f.mainPre();});
                gate.wait(); bool b=f.refreshSafetyCertificate("replan_post");
                gate.release(); a.get();
                require(!b && f.brakes==1 && f.safety_certificate_.status==Status::OCCUPIED && calls==2,
                        "old SAFE overwrote same-version hazard"); ++checks;
            }
        }
        // Time-budget failures must not accept a late SAFE result.
        for (bool slow_retry : {false,true}) {
            Map m; SuperPlanner p; Fsm f(m,p); int calls=0;
            p.geometry = [&](auto g, auto){++calls; if(calls==1) p.cmd_traj_info_.commit();
                if((!slow_retry && calls==1) || (slow_retry && calls==2)) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(8));
                }
                return receipt(g);};
            f.mainPre(); require(f.brakes == 1 && calls == (slow_retry ? 2 : 1), "late work accepted"); ++checks;
        }
        {
            Map m; SuperPlanner p; Fsm f(m,p); f.fresh=false;
            p.geometry = [](auto,auto){throw std::runtime_error("geometry on stale map"); return receipt(0);};
            f.mainPre(); require(f.brakes==1 && f.safety_certificate_.status==Status::MAP_STALE, "stale map passed"); ++checks;
        }
        std::cout << "PASS " << checks << " assertions; 300 threaded supersession cases. No flight/geometry claim.\n";
        return 0;
    } catch(const std::exception& error) { std::cerr << "FAIL " << error.what() << '\n'; return 1; }
}
