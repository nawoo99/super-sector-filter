#include <gtest/gtest.h>

#include <fsm/path_publication_policy.hpp>

namespace fsm {
namespace {

TEST(PathPublicationPolicy, DefaultPublishesWithoutSubscribers) {
    EXPECT_TRUE(visualizedPathPublicationAllowed(false, 0, 0));
}

TEST(PathPublicationPolicy, OptInSkipsOnlyWhenBothCountsAreZero) {
    EXPECT_FALSE(visualizedPathPublicationAllowed(true, 0, 0));
    EXPECT_TRUE(visualizedPathPublicationAllowed(true, 1, 0));
    EXPECT_TRUE(visualizedPathPublicationAllowed(true, 0, 1));
    EXPECT_TRUE(visualizedPathPublicationAllowed(true, 1, 1));
}

TEST(PathPublicationPolicy, ReconnectionResumesPublicationImmediately) {
    EXPECT_TRUE(visualizedPathPublicationAllowed(true, 1, 0));
    EXPECT_FALSE(visualizedPathPublicationAllowed(true, 0, 0));
    EXPECT_TRUE(visualizedPathPublicationAllowed(true, 1, 0));
}

}  // namespace
}  // namespace fsm
