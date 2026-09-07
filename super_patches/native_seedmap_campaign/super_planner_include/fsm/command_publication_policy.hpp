#pragma once

namespace fsm {

enum class OrdinaryCommandState {
    OTHER,
    FOLLOW_TRAJECTORY,
    EMERGENCY_STOP,
};

constexpr bool ordinaryCommandPublicationAllowed(
        bool trajectory_guard_enabled,
        OrdinaryCommandState state,
        bool emergency_brake_active) noexcept {
    return !emergency_brake_active &&
           (state == OrdinaryCommandState::FOLLOW_TRAJECTORY ||
           (!trajectory_guard_enabled &&
            state == OrdinaryCommandState::EMERGENCY_STOP));
}

}  // namespace fsm
