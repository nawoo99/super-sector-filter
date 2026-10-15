#pragma once

// Diagnostic wall-time spans only. Default OFF; never a scheduling policy or
// safety decision. Use TRACE=ON flights separately from CPU comparison runs.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <sys/syscall.h>
#include <unistd.h>

namespace super_utils { namespace callback_timing_trace {
struct State {
    std::atomic<std::int64_t> last_begin{0}, last_end{0};
};
struct Event {
    const char* name;
    std::int64_t begin_ns, end_ns, epoch_begin_ns, epoch_end_ns;
    std::int64_t previous_begin_ns, previous_end_ns;
    long tid;
};
struct System {
    static bool enabled() {
        static const bool value = [] {
            const char* setting = std::getenv("SUPER_CALLBACK_TRACE");
            return setting && std::strcmp(setting, "1") == 0;
        }();
        return value;
    }
    static std::int64_t now(clockid_t clock) {
        timespec ts{};
        clock_gettime(clock, &ts);
        return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
    }
    static long tid() { return syscall(SYS_gettid); }
    static void emit(const Event& e) {
        std::fprintf(stderr, "[CALLBACK_TIMING] name=%s tid=%ld begin_ns=%lld end_ns=%lld "
                     "epoch_begin_ns=%lld epoch_end_ns=%lld previous_begin_ns=%lld "
                     "previous_end_ns=%lld start_gap_ms=%.6f duration_ms=%.6f\n",
                     e.name, e.tid, (long long)e.begin_ns, (long long)e.end_ns,
                     (long long)e.epoch_begin_ns, (long long)e.epoch_end_ns,
                     (long long)e.previous_begin_ns, (long long)e.previous_end_ns,
                     e.previous_begin_ns ? (e.begin_ns - e.previous_begin_ns) / 1e6 : 0.,
                     (e.end_ns - e.begin_ns) / 1e6);
    }
};
template<class Clock = System> class BasicScope {
    State* state_ = nullptr;
    Event event_{};
    bool long_gap_ = false;
public:
    // State is per instance/callback, whose ROS group is MutuallyExclusive.
    // A zero gap threshold disables start-gap reporting (e.g. 20Hz replan).
    BasicScope(State& state, const char* name, std::int64_t gap_ns = 20000000) {
        if (!Clock::enabled()) return; // No clocks, atomics or output when OFF.
        state_ = &state;
        event_.name = name;
        event_.begin_ns = Clock::now(CLOCK_MONOTONIC);
        event_.epoch_begin_ns = Clock::now(CLOCK_REALTIME);
        event_.tid = Clock::tid();
        event_.previous_begin_ns = state.last_begin.exchange(event_.begin_ns);
        event_.previous_end_ns = state.last_end.load();
        long_gap_ = gap_ns > 0 && event_.previous_begin_ns > 0 &&
                    event_.begin_ns - event_.previous_begin_ns > gap_ns;
    }
    BasicScope(const BasicScope&) = delete;
    BasicScope& operator=(const BasicScope&) = delete;
    ~BasicScope() {
        if (!state_) return;
        event_.end_ns = Clock::now(CLOCK_MONOTONIC);
        state_->last_end.store(event_.end_ns);
        if (long_gap_ || event_.end_ns - event_.begin_ns > 20000000) {
            event_.epoch_end_ns = Clock::now(CLOCK_REALTIME);
            Clock::emit(event_);
        }
    }
};
using Scope = BasicScope<>;
}} // namespace super_utils::callback_timing_trace
