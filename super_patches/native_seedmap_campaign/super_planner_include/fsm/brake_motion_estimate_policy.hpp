#pragma once

#include <algorithm>
#include <cmath>

namespace fsm {

// A finite-difference pose velocity is only a fallback for platforms whose
// odometry message does not provide a fresh twist.  It must never enlarge the
// brake velocity contract: a generation change or an above-contract jump can
// be a command discontinuity rather than physical motion.
inline bool positionDifferenceMotionEstimateAllowed(
        double measured_speed_mps,
        double configured_velocity_limit_mps,
        bool trajectory_generation_continuous) noexcept {
    return trajectory_generation_continuous &&
           std::isfinite(measured_speed_mps) &&
           std::isfinite(configured_velocity_limit_mps) &&
           configured_velocity_limit_mps > 0.0 &&
           measured_speed_mps <= configured_velocity_limit_mps * 1.001;
}

// Some simulators (and faulty drivers) can keep publishing the last commanded
// twist after pose motion has stopped.  A direct twist may exceed the nominal
// command limit for a real disturbance, but only when a same-generation pose
// delta independently corroborates it.
inline bool directOdomTwistEstimateAllowed(
        double twist_speed_mps,
        double position_difference_speed_mps,
        double velocity_disagreement_mps,
        double max_velocity_disagreement_mps,
        bool trajectory_generation_continuous) noexcept {
    constexpr double kPlausibleSensorSpeedMps = 50.0;
    constexpr double kAbsoluteAgreementFloorMps = 0.25;
    constexpr double kRelativeAgreementFraction = 0.10;
    constexpr double kStationarySpeedMps = 0.05;
    const double agreement_scale = std::max(
            std::abs(twist_speed_mps),
            std::abs(position_difference_speed_mps));
    const double agreement_min = std::min(
            std::abs(twist_speed_mps),
            std::abs(position_difference_speed_mps));
    // The absolute agreement floor is useful for two moving measurements,
    // but it must not turn a held nonzero twist into corroborated motion when
    // the independently sampled pose is stationary.  Falling back to the
    // pose difference is conservative: a stationary brake is still accepted
    // only after the separate 0.25 s / 0.03 m stability certificate.
    const bool stationary_conflict =
            agreement_min <= kStationarySpeedMps &&
            agreement_scale > kStationarySpeedMps;
    const double scale_aware_disagreement_limit = std::min(
            max_velocity_disagreement_mps,
            std::max(kAbsoluteAgreementFloorMps,
                     kRelativeAgreementFraction * agreement_scale));
    return trajectory_generation_continuous &&
           std::isfinite(twist_speed_mps) &&
           std::isfinite(position_difference_speed_mps) &&
           std::isfinite(velocity_disagreement_mps) &&
           std::isfinite(max_velocity_disagreement_mps) &&
           max_velocity_disagreement_mps >= 0.0 &&
           twist_speed_mps <= kPlausibleSensorSpeedMps &&
           position_difference_speed_mps <= kPlausibleSensorSpeedMps &&
           !stationary_conflict &&
           velocity_disagreement_mps <= scale_aware_disagreement_limit;
}

}  // namespace fsm
