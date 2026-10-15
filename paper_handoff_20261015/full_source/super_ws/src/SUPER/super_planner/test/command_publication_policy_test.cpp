#include <gtest/gtest.h>

#include <fsm/command_publication_policy.hpp>

namespace fsm {
namespace {

TEST(CommandPublicationPolicy, AllowsFollowingTrajectory) {
    EXPECT_TRUE(ordinaryCommandPublicationAllowed(
            false, OrdinaryCommandState::FOLLOW_TRAJECTORY, false));
    EXPECT_TRUE(ordinaryCommandPublicationAllowed(
            true, OrdinaryCommandState::FOLLOW_TRAJECTORY, false));
}

TEST(CommandPublicationPolicy, PreservesLegacyUnguardedEmergencyStop) {
    EXPECT_TRUE(ordinaryCommandPublicationAllowed(
            false, OrdinaryCommandState::EMERGENCY_STOP, false));
}

TEST(CommandPublicationPolicy, BlocksGuardedEmergencyStop) {
    EXPECT_FALSE(ordinaryCommandPublicationAllowed(
            true, OrdinaryCommandState::EMERGENCY_STOP, false));
}

TEST(CommandPublicationPolicy, BlocksWhileCertifiedBrakeIsActive) {
    EXPECT_FALSE(ordinaryCommandPublicationAllowed(
            false, OrdinaryCommandState::FOLLOW_TRAJECTORY, true));
    EXPECT_FALSE(ordinaryCommandPublicationAllowed(
            true, OrdinaryCommandState::FOLLOW_TRAJECTORY, true));
}

TEST(CommandPublicationPolicy, BlocksOtherStates) {
    EXPECT_FALSE(ordinaryCommandPublicationAllowed(
            false, OrdinaryCommandState::OTHER, false));
    EXPECT_FALSE(ordinaryCommandPublicationAllowed(
            true, OrdinaryCommandState::OTHER, false));
}

}  // namespace
}  // namespace fsm
