#pragma once

#include <cmath>
#include <cstring>
#include <stdexcept>

namespace perfect_drone::static_pc_two_phase {

inline bool parseEnabled(const char* setting, const int legacy_poll_ms) {
    if (!setting || std::strcmp(setting, "0") == 0) return false;
    if (std::strcmp(setting, "1") != 0) {
        throw std::invalid_argument("SUPER_STATIC_PC_TWO_PHASE must be 0 or 1");
    }
    if (legacy_poll_ms != 1) {
        throw std::invalid_argument("SUPER_STATIC_PC_TWO_PHASE=1 requires SUPER_STATIC_PC_POLL_MS=1");
    }
    return true;
}

enum class Change { None, Coarse, LegacyFallback };
enum class Fallback { None, SimulatedTime, InvalidElapsed, ClockRollback };

inline const char* fallbackName(const Fallback reason) noexcept {
    switch (reason) {
        case Fallback::None: return "none";
        case Fallback::SimulatedTime: return "simulated_time";
        case Fallback::InvalidElapsed: return "invalid_elapsed";
        case Fallback::ClockRollback: return "clock_rollback";
    }
    return "unknown";
}

struct Decision {
    Change change{Change::None};
    Fallback fallback{Fallback::None};
    bool reset_fast_timer{false};
};

// State is owned by the global-PC MutuallyExclusive callback group. The caller
// performs the existing legacy publication before observeAfterLegacy(); this
// class changes only which real timer may next invoke that same callback.
// Stable node time is required for coarse mode. Observed unsupported clocks
// permanently return to the legacy timer, not an oscillating new schedule.
class Policy {
public:
    static constexpr double kBootstrapWindowEndS = 5.1;
    explicit Policy(const bool enabled = false) : enabled_(enabled) {}

    bool enabled() const noexcept { return enabled_; }
    bool fastActive() const noexcept { return !coarse_; }
    bool coarseActive() const noexcept { return enabled_ && coarse_; }
    bool fallbackLatched() const noexcept { return fallback_latched_; }

    Decision observeAfterLegacy(const double ros_elapsed_s,
                                const bool ros_time_active) noexcept {
        if (!enabled_ || fallback_latched_) return {};
        Fallback reason = Fallback::None;
        if (ros_time_active) reason = Fallback::SimulatedTime;
        else if (!std::isfinite(ros_elapsed_s) || ros_elapsed_s < 0.0)
            reason = Fallback::InvalidElapsed;
        else if (have_previous_ && ros_elapsed_s < previous_elapsed_s_)
            reason = Fallback::ClockRollback;
        if (reason != Fallback::None) {
            const bool was_coarse = coarse_;
            coarse_ = false;
            fallback_latched_ = true;
            return {Change::LegacyFallback, reason, was_coarse};
        }
        previous_elapsed_s_ = ros_elapsed_s;
        have_previous_ = true;
        if (!coarse_ && ros_elapsed_s >= kBootstrapWindowEndS) {
            coarse_ = true;
            return {Change::Coarse, Fallback::None, false};
        }
        return {};
    }

private:
    bool enabled_{false};
    bool coarse_{false};
    bool fallback_latched_{false};
    bool have_previous_{false};
    double previous_elapsed_s_{0.0};
};

}  // namespace perfect_drone::static_pc_two_phase
