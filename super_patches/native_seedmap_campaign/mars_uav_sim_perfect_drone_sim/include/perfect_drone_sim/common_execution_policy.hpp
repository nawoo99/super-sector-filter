#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace perfect_drone {
namespace common_execution_policy {

// Only the legacy 1 ms schedule and the reviewed 100 ms opt-in are supported.
inline int parseStaticPcPollMs(const char* setting) {
    if (!setting || std::strcmp(setting, "1") == 0) return 1;
    if (std::strcmp(setting, "100") == 0) return 100;
    throw std::invalid_argument("SUPER_STATIC_PC_POLL_MS must be 1 or 100");
}

// Pure parser, separately testable without mutating process environment.
// Unset preserves the current 10-thread side executor; invalid input fails
// startup rather than silently creating an unbounded or zero-thread pool.
inline std::size_t parseSideExecutorThreads(const char* setting) {
    if (!setting) return 10;
    if (*setting == '\0') {
        throw std::invalid_argument("SUPER_SIDE_EXECUTOR_THREADS must be an integer from 4 to 16");
    }
    unsigned value = 0;
    for (const char* cursor = setting; *cursor; ++cursor) {
        if (*cursor < '0' || *cursor > '9') {
            throw std::invalid_argument("SUPER_SIDE_EXECUTOR_THREADS must contain only decimal digits");
        }
        value = value * 10U + static_cast<unsigned>(*cursor - '0');
        if (value > 16U) {
            throw std::invalid_argument("SUPER_SIDE_EXECUTOR_THREADS must be between 4 and 16");
        }
    }
    if (value < 4U) {
        throw std::invalid_argument("SUPER_SIDE_EXECUTOR_THREADS must be between 4 and 16");
    }
    return value;
}

struct StaticPcDecision {
    bool publish{false};
    bool subscriber_change{false};
    bool bootstrap{false};
};

// Single-callback-group instance state. All publications retain the complete
// map and original QoS; only the periodic polling/publication schedule changes.
// The caller uses a real 100 ms timer, not a 1 ms early-return polling loop.
class StaticPcPolicy {
public:
    static constexpr std::int64_t kBootstrapAfterNs = 5000000000LL;

    StaticPcDecision observe(const std::int64_t elapsed_ns,
                             const std::size_t subscribers) {
        if (elapsed_ns < 0) {
            throw std::invalid_argument("static-PC elapsed time must be nonnegative");
        }
        if (subscribers > 0 && subscribers != last_subscribers_) {
            pending_subscriber_publish_ = true;
        }
        last_subscribers_ = subscribers;
        const bool bootstrap = !bootstrap_done_ && elapsed_ns >= kBootstrapAfterNs;
        return {pending_subscriber_publish_ || bootstrap,
                pending_subscriber_publish_, bootstrap};
    }

    // Invoke only after the original getGlobalMap/toROSMsg/publish succeeds.
    // A failed attempt leaves the reasons pending for the next real timer tick.
    void published(const StaticPcDecision& decision) {
        if (!decision.publish) {
            throw std::logic_error("cannot acknowledge a non-publication decision");
        }
        if (decision.subscriber_change) pending_subscriber_publish_ = false;
        if (decision.bootstrap) bootstrap_done_ = true;
    }

private:
    std::size_t last_subscribers_{0};
    bool pending_subscriber_publish_{false};
    bool bootstrap_done_{false};
};

}  // namespace common_execution_policy
}  // namespace perfect_drone
