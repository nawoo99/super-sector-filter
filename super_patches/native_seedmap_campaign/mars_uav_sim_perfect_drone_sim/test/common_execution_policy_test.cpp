#include "perfect_drone_sim/common_execution_policy.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace policy = perfect_drone::common_execution_policy;

void require(const bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template <typename Function>
void requireInvalid(Function&& function) {
    bool threw = false;
    try { function(); }
    catch (const std::invalid_argument&) { threw = true; }
    require(threw, "expected invalid_argument");
}

int main() {
    try {
        require(policy::parseStaticPcPollMs(nullptr) == 1, "static polling default");
        require(policy::parseStaticPcPollMs("1") == 1, "legacy 1 ms preserved");
        require(policy::parseStaticPcPollMs("100") == 100, "opt-in 100 ms");
        for (const char* bad : {"", "0", "10", "99", "101", "true", "100 ", " 100"})
            requireInvalid([&] { policy::parseStaticPcPollMs(bad); });
        require(policy::parseSideExecutorThreads(nullptr) == 10, "default executor");
        for (unsigned n = 4; n <= 16; ++n) {
            const auto value = std::to_string(n);
            require(policy::parseSideExecutorThreads(value.c_str()) == n, "valid executor range");
        }
        require(policy::parseSideExecutorThreads("04") == 4, "decimal leading zero");
        for (const char* bad : {"", "0", "3", "17", "-4", "+4", "4.0", "4 ", " 4", "4x",
                                "999999999999999999999999999999999999"}) {
            requireInvalid([&] { policy::parseSideExecutorThreads(bad); });
        }

        policy::StaticPcPolicy idle;
        for (std::int64_t tick = 0; tick < 50; ++tick)
            require(!idle.observe(tick * 100000000, 0).publish, "idle before bootstrap");
        const auto bootstrap = idle.observe(5000000000LL, 0);
        require(bootstrap.publish && bootstrap.bootstrap && !bootstrap.subscriber_change,
                "bootstrap without listeners");
        idle.published(bootstrap);
        for (std::int64_t tick = 51; tick < 100; ++tick)
            require(!idle.observe(tick * 100000000, 0).publish, "one-shot bootstrap");
        const auto late = idle.observe(60000000000LL, 1);
        require(late.publish && late.subscriber_change && !late.bootstrap, "late RViz");
        idle.published(late);
        require(!idle.observe(60100000000LL, 1).publish, "unchanged late listener");

        policy::StaticPcPolicy changing;
        for (const std::size_t subscribers : {1U, 2U, 1U, 3U}) {
            const auto next = changing.observe(1000000000LL, subscribers);
            require(next.publish && next.subscriber_change && !next.bootstrap,
                    "nonzero count changes including decreases");
            changing.published(next);
        }
        require(!changing.observe(1100000000LL, 0).publish, "disconnect to zero");
        const auto reconnect = changing.observe(1200000000LL, 1);
        require(reconnect.publish, "reconnect");
        changing.published(reconnect);
        const auto combined = changing.observe(5000000000LL, 2);
        require(combined.bootstrap && combined.subscriber_change, "coalesced reasons");
        // No acknowledgement simulates a failed publication: keep both reasons.
        const auto retry = changing.observe(5100000000LL, 2);
        require(retry.bootstrap && retry.subscriber_change, "failed publication retry");
        changing.published(retry);
        require(!changing.observe(5200000000LL, 2).publish, "successful retry clears reasons");

        policy::StaticPcPolicy delayed;
        require(!delayed.observe(4900000000LL, 0).publish, "not yet bootstrap");
        require(delayed.observe(8000000000LL, 0).bootstrap, "late tick does not miss bootstrap");
        policy::StaticPcPolicy independent;
        require(independent.observe(60000000000LL, 1).bootstrap, "independent instance state");
        requireInvalid([&] { independent.observe(-1, 0); });
        std::cout << "common_execution_policy_test=PASS parser_valid_range=4..16 "
                  << "default_threads=10 static_default_ms=1 optin_ms=100\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "common_execution_policy_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
