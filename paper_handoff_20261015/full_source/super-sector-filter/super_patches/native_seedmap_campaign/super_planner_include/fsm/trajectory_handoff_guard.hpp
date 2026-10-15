#ifndef SUPER_TRAJECTORY_HANDOFF_GUARD_HPP
#define SUPER_TRAJECTORY_HANDOFF_GUARD_HPP

#include <cmath>
#include <limits>

namespace super_planner {
namespace trajectory_handoff {

// A moving replan carries a prefix of the currently commanded polynomial.
// At the same absolute handoff time its PVA must therefore agree, up to
// numerical reconstruction error. These are continuity tolerances, not
// obstacle clearances or allowances for a delayed odometry observation.
inline constexpr double kPositionToleranceM = 1.0e-3;
inline constexpr double kVelocityToleranceMps = 1.0e-2;
inline constexpr double kAccelerationToleranceMps2 = 1.0e-1;

struct Result {
    bool continuous{false};
    const char* reason{"INVALID_SAMPLE"};
    double position_error_m{std::numeric_limits<double>::infinity()};
    double velocity_error_mps{std::numeric_limits<double>::infinity()};
    double acceleration_error_mps2{std::numeric_limits<double>::infinity()};
};

// Accepts Eigen StatePVAJ or a small test matrix with operator()(axis, order).
// Callers must evaluate both states at the SAME absolute time. Jerk may
// legitimately change at a trajectory splice; position/velocity/acceleration
// cannot. Invalid inputs always fail closed.
template <typename Left, typename Right>
Result comparePva(const Left& previous, const Right& candidate) noexcept {
    Result out;
    double errors[3]{};
    for (int order = 0; order != 3; ++order) {
        for (int axis = 0; axis != 3; ++axis) {
            const double lhs = previous(axis, order);
            const double rhs = candidate(axis, order);
            if (!std::isfinite(lhs) || !std::isfinite(rhs)) {
                out.reason = "NONFINITE_PVA";
                return out;
            }
            errors[order] = std::hypot(errors[order], lhs - rhs);
        }
        if (!std::isfinite(errors[order])) {
            out.reason = "NONFINITE_PVA";
            return out;
        }
    }
    out.position_error_m = errors[0];
    out.velocity_error_mps = errors[1];
    out.acceleration_error_mps2 = errors[2];
    if (errors[0] > kPositionToleranceM) {
        out.reason = "POSITION_DISCONTINUITY";
    } else if (errors[1] > kVelocityToleranceMps) {
        out.reason = "VELOCITY_DISCONTINUITY";
    } else if (errors[2] > kAccelerationToleranceMps2) {
        out.reason = "ACCELERATION_DISCONTINUITY";
    } else {
        out.continuous = true;
        out.reason = "CONTINUOUS";
    }
    return out;
}

// Keeping the sampling rule in the tested helper makes it impossible for the
// admission check and stale-EXP check to silently compare different clocks.
// The sampler returns false for invalid/non-finite trajectory time/state.
template <typename State, typename PreviousSampler, typename CandidateSampler>
Result compareAt(const double absolute_wt,
                 PreviousSampler previous_sampler,
                 CandidateSampler candidate_sampler) {
    Result out;
    if (!std::isfinite(absolute_wt)) return out;
    State previous{}, candidate{};
    if (!previous_sampler(absolute_wt, previous) ||
        !candidate_sampler(absolute_wt, candidate)) return out;
    return comparePva(previous, candidate);
}

}  // namespace trajectory_handoff
}  // namespace super_planner

#endif
