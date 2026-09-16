#include "goal_retransmit_identity.hpp"

#include <iostream>
#include <limits>

namespace repeat = mission_planner::goal_retransmit;
unsigned checks = 0;
void require(bool condition, const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        require(!repeat::enabledFromSetting(nullptr), "default disabled");
        require(!repeat::enabledFromSetting("0"), "explicit disabled");
        require(repeat::enabledFromSetting("1"), "exact opt-in");
        for (const char* input : {"", "true", "01", "1 ", "-1"}) {
            bool caught = false;
            try { repeat::enabledFromSetting(input); }
            catch (const std::invalid_argument&) { caught = true; }
            require(caught, "invalid opt-in rejected");
        }

        const repeat::RawGoal a{{24., 24., 1.5, 0., 0., 0., 1.}, "world"};
        repeat::Identity identity;
        const auto first = identity.publication(true, a, 100);
        require(first.supported && first.new_identity && first.stamp_ns == 100, "initial creation");
        for (const auto now : {101LL, 200LL, 99LL, 0LL}) {
            const auto retransmit = identity.publication(false, a, now);
            require(retransmit.supported && !retransmit.new_identity &&
                    retransmit.stamp_ns == first.stamp_ns, "same command retains creation identity");
        }
        auto retrigger = identity.publication(true, a, 100);
        require(retrigger.supported && retrigger.new_identity && retrigger.stamp_ns == 101,
                "same-pose same-tick deliberate new intent distinct");
        retrigger = identity.publication(true, a, 50);
        require(retrigger.stamp_ns == 102, "new intent on backward positive clock distinct");

        for (std::size_t i = 0; i < a.values.size(); ++i) {
            repeat::Identity p;
            p.publication(true, a, 100);
            auto b = a;
            b.values[i] = std::nextafter(b.values[i], 2.);
            const auto changed = p.publication(false, b, 100);
            require(changed.new_identity && changed.stamp_ns == 101, "every changed raw component new identity");
        }
        repeat::Identity frame;
        frame.publication(true, a, 100);
        auto different_frame = a;
        different_frame.frame = "map";
        require(frame.publication(false, different_frame, 100).new_identity, "changed frame distinct");
        auto signed_zero = a;
        signed_zero.values[3] = -0.0;
        require(!a.exactlyEquals(signed_zero), "signed zero conservatively distinct");

        for (std::size_t i = 0; i < a.values.size(); ++i) {
            for (const auto bad : {std::numeric_limits<double>::quiet_NaN(),
                                   std::numeric_limits<double>::infinity(),
                                   -std::numeric_limits<double>::infinity()}) {
                repeat::Identity p;
                p.publication(true, a, 100);
                auto invalid = a;
                invalid.values[i] = bad;
                const auto rejected = p.publication(false, invalid, 101);
                require(!rejected.supported && rejected.stamp_ns == 0, "nonfinite forces normal receiver admission");
                require(p.publication(false, a, 102).new_identity, "fallback invalidates current cache");
            }
        }
        repeat::Identity invalid_clock;
        require(!invalid_clock.publication(true, a, 0).supported, "zero creation clock unsupported");
        require(!invalid_clock.publication(true, a, -1).supported, "negative creation clock unsupported");
        require(invalid_clock.publication(true, a, 1).stamp_ns == 1, "first positive identity");
        repeat::Identity exhaustion;
        require(exhaustion.publication(true, a, repeat::Identity::kMaxStampNs).supported, "maximum representable stamp");
        require(!exhaustion.publication(true, a, repeat::Identity::kMaxStampNs).supported, "no wrap/reused identity on exhaustion");
        require(!exhaustion.publication(false, a, 1).supported, "exhausted process remains noncoalescible");
        repeat::Identity malformed;
        auto empty_frame = a;
        empty_frame.frame.clear();
        require(!malformed.publication(true, empty_frame, 1).supported, "empty frame unsupported");

        // Synthetic producer intent sequence: five waypoints and one explicit
        // same-pose restart; periodic1Hz retransmissions preserve all six IDs.
        repeat::Identity sequence;
        std::int64_t previous = 0;
        for (int waypoint = 0; waypoint < 5; ++waypoint) {
            auto goal = a;
            goal.values[0] = waypoint;
            const auto created = sequence.publication(true, goal, 1000 + waypoint);
            require(created.new_identity && created.stamp_ns > previous, "waypoint creates new identity");
            previous = created.stamp_ns;
            for (int heartbeat = 0; heartbeat < 3; ++heartbeat)
                require(sequence.publication(false, goal, 2000 + heartbeat).stamp_ns == previous,
                        "heartbeat does not manufacture intent");
        }
        require(sequence.publication(true, a, 1).stamp_ns > previous, "restart creates new identity");
        std::cout << "goal_retransmit_identity_test=PASS checks=" << checks
                  << " runtime_timer_or_ros_integration=false\n";
    } catch (const std::exception& error) {
        std::cerr << "goal_retransmit_identity_test=FAIL " << error.what() << '\n';
        return 1;
    }
}
