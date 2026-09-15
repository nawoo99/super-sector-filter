#ifndef SUPER_UTILS_THREAD_CPU_PROFILE_HPP
#define SUPER_UTILS_THREAD_CPU_PROFILE_HPP

// Opt-in diagnostics only: SUPER_CPU_PROFILE=1. Timings are CPU consumed by
// the calling thread, NOT elapsed/wait time and NOT CPU of spawned workers.
// Inclusive scopes contain their nested scopes; exclusive scopes subtract
// measured children on that same thread. Do not sum inclusive stage totals.
// Disabled scopes do not read a clock, mutate counters, or log anything.
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <time.h>
#include <unistd.h>

namespace super_utils::thread_cpu_profile {

enum class Stage : std::size_t {
    MapCloudEnqueue,
    MapWorker,
    MapRosToPcl,
    MapProbUpdate,
    MapSnapshotCommitHealth,
    MapAckAndLog,
    FsmMainCallback,
    FsmMainCore,
    FsmReplanCallback,
    FsmReplanCore,
    FsmCommandCallback,
    GuardCertificate,
    GuardBrake,
    GuardRecover,
    PlannerGenerateExp,
    PlannerGenerateBackup,
    PlannerCommit,
    PlannerValidateGeometry,
    PlannerStopViability,
    PlannerPathSearch,
    PlannerExpOptimize,
    PlannerBackupOptimize,
    PlannerBackupReplay,
    PlannerCorridorSearch,
    PlannerVelocityExtrema,
    PlannerVisualizePath,
    FsmPolyPublish,
    Count
};

inline constexpr std::array<const char *, static_cast<std::size_t>(Stage::Count)>
        kStageNames{{
            "map_cloud_enqueue", "map_worker", "map_ros_to_pcl",
            "map_prob_update", "map_snapshot_commit_health", "map_ack_and_log",
            "fsm_main_callback", "fsm_main_core", "fsm_replan_callback",
            "fsm_replan_core", "fsm_command_callback", "guard_certificate",
            "guard_brake", "guard_recover", "planner_generate_exp",
            "planner_generate_backup", "planner_commit",
            "planner_validate_geometry", "planner_stop_viability",
            "planner_path_search", "planner_exp_optimize",
            "planner_backup_optimize", "planner_backup_replay",
            "planner_corridor_search", "planner_velocity_extrema",
            "planner_visualize_path", "fsm_poly_publish"}};

inline bool enabled() noexcept {
    static const bool value = [] {
        const char *setting = std::getenv("SUPER_CPU_PROFILE");
        return setting && std::strcmp(setting, "1") == 0;
    }();
    return value;
}

struct alignas(64) Counter {
    std::atomic<std::uint64_t> calls{0};
    std::atomic<std::uint64_t> inclusive_ns{0};
    std::atomic<std::uint64_t> exclusive_ns{0};
};

struct Registry {
    std::array<Counter, static_cast<std::size_t>(Stage::Count)> counters{};
    std::atomic<std::uint64_t> clock_errors{0};
    std::atomic<std::int64_t> last_report_ns{0};
};

inline Registry &registry() noexcept {
    static Registry state;
    return state;
}

inline bool threadCpuNs(std::uint64_t &value) noexcept {
    timespec now{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &now) != 0) {
        registry().clock_errors.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    value = static_cast<std::uint64_t>(now.tv_sec) * 1000000000ULL +
            static_cast<std::uint64_t>(now.tv_nsec);
    return true;
}

class Scope;
inline Scope *&activeScope() noexcept {
    static thread_local Scope *top = nullptr;
    return top;
}

class Scope {
public:
    explicit Scope(Stage stage) noexcept : stage_(stage) {
        if (!enabled() || !threadCpuNs(start_ns_)) {
            return;
        }
        active_ = true;
        parent_ = activeScope();
        activeScope() = this;
    }

    Scope(const Scope &) = delete;
    Scope &operator=(const Scope &) = delete;

    ~Scope() noexcept {
        if (!active_) {
            return;
        }
        activeScope() = parent_;
        std::uint64_t end_ns = 0;
        if (!threadCpuNs(end_ns) || end_ns < start_ns_) {
            return;
        }
        const std::uint64_t inclusive = end_ns - start_ns_;
        const std::uint64_t exclusive = inclusive > child_ns_
                ? inclusive - child_ns_ : 0;
        auto &counter = registry().counters[static_cast<std::size_t>(stage_)];
        counter.inclusive_ns.fetch_add(inclusive, std::memory_order_relaxed);
        counter.exclusive_ns.fetch_add(exclusive, std::memory_order_relaxed);
        counter.calls.fetch_add(1, std::memory_order_relaxed);
        if (parent_) {
            parent_->child_ns_ += inclusive;
        }
    }

private:
    Stage stage_;
    bool active_{false};
    std::uint64_t start_ns_{0};
    std::uint64_t child_ns_{0};
    Scope *parent_{nullptr};
};

// Called outside a measured scope by the serialized main-FSM callback.
// Counter snapshots are approximate while other threads are active. Final
// reports after worker shutdown are exact for all finished scopes. Counters
// are cumulative since process start and are never reset by reporting.
inline void report(bool final_report = false) noexcept {
    if (!enabled()) {
        return;
    }
    const auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    auto &state = registry();
    auto previous = state.last_report_ns.load(std::memory_order_relaxed);
    if (!final_report) {
        if (previous == 0) {
            state.last_report_ns.compare_exchange_strong(
                    previous, now_ns, std::memory_order_relaxed);
            return;
        }
        if (now_ns - previous < 5000000000LL ||
            !state.last_report_ns.compare_exchange_strong(
                    previous, now_ns, std::memory_order_relaxed)) {
            return;
        }
    }
    const auto errors = state.clock_errors.load(std::memory_order_relaxed);
    for (std::size_t i = 0; i < state.counters.size(); ++i) {
        const auto &counter = state.counters[i];
        const auto calls = counter.calls.load(std::memory_order_relaxed);
        if (calls == 0) {
            continue;
        }
        const auto inclusive = counter.inclusive_ns.load(std::memory_order_relaxed);
        const auto exclusive = counter.exclusive_ns.load(std::memory_order_relaxed);
        std::fprintf(stderr,
                "[THREAD_CPU_PROFILE] version=1 pid=%ld steady_ns=%lld "
                "final=%d stage=%s calls=%llu inclusive_cpu_s=%.9f "
                "exclusive_cpu_s=%.9f clock_errors=%llu\n",
                static_cast<long>(getpid()), static_cast<long long>(now_ns),
                final_report ? 1 : 0, kStageNames[i],
                static_cast<unsigned long long>(calls),
                static_cast<double>(inclusive) * 1e-9,
                static_cast<double>(exclusive) * 1e-9,
                static_cast<unsigned long long>(errors));
    }
}

}  // namespace super_utils::thread_cpu_profile

#endif
