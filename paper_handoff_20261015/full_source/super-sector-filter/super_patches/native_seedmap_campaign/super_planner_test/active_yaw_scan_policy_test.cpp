#include <cmath>

#include <gtest/gtest.h>

#include <fsm/active_yaw_scan_policy.hpp>

namespace fsm::active_yaw_scan {
namespace {

TEST(ActiveYawScanPolicy, IsDefaultOffAndExplicitlyOptIn) {
    EXPECT_FALSE(enabledSetting(nullptr));
    EXPECT_FALSE(enabledSetting("0"));
    EXPECT_TRUE(enabledSetting("1"));
}

TEST(ActiveYawScanPolicy, UsesShortestWrappedTurn) {
    const auto mid = command(170.0 * kPi / 180.0,
                             -170.0 * kPi / 180.0, 0.25, 0.5);
    EXPECT_GT(mid.yaw_rate, 0.0);
    const auto done = command(170.0 * kPi / 180.0,
                              -170.0 * kPi / 180.0, 10.0, 0.5);
    EXPECT_TRUE(done.complete);
    EXPECT_NEAR(wrapAngle(done.yaw + 170.0 * kPi / 180.0), 0.0, 1.0e-9);
    EXPECT_NEAR(done.yaw_rate, 0.0, 1.0e-9);
}

TEST(ActiveYawScanPolicy, SweepsGoalThenOrthogonalAndRearViews) {
    const double goal = 0.3;
    EXPECT_NEAR(targetForAttempt(goal, 0), goal, 1.0e-12);
    EXPECT_NEAR(wrapAngle(targetForAttempt(goal, 1) - goal), 0.5 * kPi, 1.0e-12);
    EXPECT_NEAR(wrapAngle(targetForAttempt(goal, 2) - goal), -0.5 * kPi, 1.0e-12);
    EXPECT_NEAR(std::abs(wrapAngle(targetForAttempt(goal, 3) - goal)), kPi, 1.0e-12);
}

}  // namespace
}  // namespace fsm::active_yaw_scan
