#pragma once

#include <algorithm>
#include <cmath>
#include <cstring>

namespace fsm::active_yaw_scan {

constexpr double kPi = 3.14159265358979323846;

inline bool enabledSetting(const char* value) {
    return value != nullptr && std::strcmp(value, "1") == 0;
}

inline double wrapAngle(const double angle) {
    return std::remainder(angle, 2.0 * kPi);
}

inline double targetForAttempt(const double goal_bearing,
                               const unsigned attempt) {
    constexpr double offsets[] = {0.0, 0.5 * kPi, -0.5 * kPi, kPi};
    return wrapAngle(goal_bearing + offsets[std::min<unsigned>(attempt, 3)]);
}

struct Command {
    double yaw{0.0};
    double yaw_rate{0.0};
    double duration{0.0};
    bool complete{true};
};

// Cubic smoothstep gives zero yaw rate at both ends.  The duration is chosen
// from the requested maximum average rate; the peak rate is 1.5 times that
// average, which is accounted for by the caller's conservative 40 deg/s
// default.
inline Command command(const double start_yaw, const double target_yaw,
                       const double elapsed_s, const double rate_rad_s) {
    const double delta = wrapAngle(target_yaw - start_yaw);
    const double safe_rate = std::max(1.0e-3, std::abs(rate_rad_s));
    const double duration = std::max(0.05, std::abs(delta) / safe_rate);
    const double u = std::clamp(elapsed_s / duration, 0.0, 1.0);
    const double blend = u * u * (3.0 - 2.0 * u);
    const double blend_rate = 6.0 * u * (1.0 - u) / duration;
    return {wrapAngle(start_yaw + delta * blend),
            delta * blend_rate, duration, elapsed_s >= duration};
}

}  // namespace fsm::active_yaw_scan
