#include <limits>

#include <gtest/gtest.h>

#include <fsm/brake_motion_estimate_policy.hpp>

namespace fsm {
namespace {

TEST(BrakeMotionEstimatePolicy, AcceptsFiniteContinuousMotionWithinLimit) {
    EXPECT_TRUE(positionDifferenceMotionEstimateAllowed(
            6.9, 7.0, true));
    EXPECT_TRUE(positionDifferenceMotionEstimateAllowed(
            7.007, 7.0, true));
}

TEST(BrakeMotionEstimatePolicy, RejectsTrajectoryGenerationDiscontinuity) {
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            3.0, 7.0, false));
}

TEST(BrakeMotionEstimatePolicy, RejectsPositionJumpAboveCommandContract) {
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            7.069, 7.0, true));
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            32.169, 7.0, true));
}

TEST(BrakeMotionEstimatePolicy, RejectsNonFiniteOrInvalidLimits) {
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            std::numeric_limits<double>::infinity(), 7.0, true));
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            std::numeric_limits<double>::quiet_NaN(), 7.0, true));
    EXPECT_FALSE(positionDifferenceMotionEstimateAllowed(
            1.0, 0.0, true));
}

TEST(BrakeMotionEstimatePolicy, AcceptsCorroboratedDirectOdomOverspeed) {
    EXPECT_TRUE(directOdomTwistEstimateAllowed(
            10.0, 9.8, 0.2, 2.0, true));
    EXPECT_TRUE(directOdomTwistEstimateAllowed(
            1.0, 0.8, 0.2, 2.0, true));
    EXPECT_TRUE(directOdomTwistEstimateAllowed(
            0.04, 0.0, 0.04, 2.0, true));
}

TEST(BrakeMotionEstimatePolicy, RejectsHeldTwistAtStationaryPosition) {
    EXPECT_FALSE(directOdomTwistEstimateAllowed(
            6.256, 0.0, 6.256, 2.0, true));
    // A fixed 2 m/s disagreement allowance is too permissive at low speed:
    // PerfectDrone can retain a 1.664 m/s terminal twist while its pose is
    // physically stationary.  Treat that as stale sensor state as well.
    EXPECT_FALSE(directOdomTwistEstimateAllowed(
            1.664, 0.0, 1.664, 2.0, true));
    // Map9/Sector run 9 exposed the same simulator failure at a much lower
    // residual twist.  The vehicle pose remained fixed for 136 s while the
    // last odometry twist stayed at 0.149 m/s, preventing the independently
    // stable stationary-hold path from ever running.
    EXPECT_FALSE(directOdomTwistEstimateAllowed(
            0.149, 0.0, 0.149, 2.0, true));
    EXPECT_FALSE(directOdomTwistEstimateAllowed(
            1.0, 0.6, 0.4, 2.0, true));
}

TEST(BrakeMotionEstimatePolicy, RejectsDirectTwistAcrossGenerationChange) {
    EXPECT_FALSE(directOdomTwistEstimateAllowed(
            4.0, 4.0, 0.0, 2.0, false));
}

}  // namespace
}  // namespace fsm
