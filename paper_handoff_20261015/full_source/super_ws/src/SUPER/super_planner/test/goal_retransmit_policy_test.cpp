#include <fsm/goal_retransmit_policy.hpp>

#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace policy = fsm::goal_retransmit;
void require(bool value, const char* why) {
    if (!value) throw std::runtime_error(why);
}

policy::Request request() {
    return {{1.0, 2.0, 3.0}, {1.0, 0.0, 0.0, 0.0}, "world", 123456789};
}
policy::HealthyFollow healthy() {
    policy::HealthyFollow e;
    e.guard_enabled = e.ordinary_follow = e.immutable_map = e.map_fresh = true;
    e.explicitly_safe = e.sample_valid_finite = e.final_evidence_current = true;
    e.stopped_finished_or_from_rest = e.brake_or_revalidation = false;
    e.recovery_or_refresh_pending = e.failure_or_rejection = e.special_escape = false;
    e.sample_finished = e.sample_on_backup = false;
    e.generation = e.certificate_generation = 7;
    e.map_version = e.certificate_map_version = 12;
    e.sample_tt = 0.5; e.certificate_from_tt = 0.4; e.certificate_until_tt = 1.0;
    return e;
}

int main() {
    try {
        require(!policy::enabledSetting(nullptr) && !policy::enabledSetting("0") &&
                !policy::enabledSetting("true") && policy::enabledSetting("1"), "exact default-off flag");
        require(policy::canonicalPositiveStamp(0, 0) == 0 &&
                policy::canonicalPositiveStamp(-1, 0) == 0 &&
                policy::canonicalPositiveStamp(0, 1000000000U) == 0 &&
                policy::canonicalPositiveStamp(0, 2000000000U) == 0 &&
                policy::canonicalPositiveStamp(0, 4294967295U) == 0,
                "malformed stamp cannot normalize into another identity");
        require(policy::canonicalPositiveStamp(2, 0) == 2000000000LL &&
                policy::canonicalPositiveStamp(0, 1) == 1 &&
                policy::canonicalPositiveStamp(2147483647, 999999999U) == 2147483647999999999LL,
                "canonical positive stamp int64 bounds");
        const auto a = request();
        require(policy::sameRequest(a, a), "unchanged explicit retransmission");
        for (const auto& mutate : std::vector<std::function<void(policy::Request&)>>{
                [](auto& r) { ++r.creation_stamp_ns; },
                [](auto& r) { r.creation_stamp_ns = 0; },
                [](auto& r) { r.creation_stamp_ns = -1; },
                [](auto& r) { r.frame = "map"; },
                [](auto& r) { r.frame.clear(); },
                [](auto& r) { r.position[0] = std::nextafter(r.position[0], 2.0); },
                [](auto& r) { r.position[1] += 1.0; },
                [](auto& r) { r.position[2] += .01; },
                [](auto& r) { r.quaternion[0] = -1.0; },
                [](auto& r) { r.quaternion[1] = .001; },
                [](auto& r) { r.quaternion[2] = -0.0; },
                [](auto& r) { r.quaternion[3] = .1; },
                [](auto& r) { r.position[0] = std::numeric_limits<double>::quiet_NaN(); },
                [](auto& r) { r.quaternion[0] = std::numeric_limits<double>::infinity(); }}) {
            auto b = a; mutate(b);
            require(!policy::sameRequest(a, b), "changed/invalid raw request is never coalesced");
        }
        require(policy::eligible(healthy()), "healthy existing committed motion");
        unsigned rejected = 0;
        for (const auto& mutate : std::vector<std::function<void(policy::HealthyFollow&)>>{
                [](auto& e) { e.guard_enabled = false; },
                [](auto& e) { e.ordinary_follow = false; },
                [](auto& e) { e.stopped_finished_or_from_rest = true; },
                [](auto& e) { e.brake_or_revalidation = true; },
                [](auto& e) { e.recovery_or_refresh_pending = true; },
                [](auto& e) { e.failure_or_rejection = true; },
                [](auto& e) { e.immutable_map = false; },
                [](auto& e) { e.map_fresh = false; },
                [](auto& e) { e.explicitly_safe = false; },
                [](auto& e) { e.special_escape = true; },
                [](auto& e) { e.sample_valid_finite = false; },
                [](auto& e) { e.sample_finished = true; },
                [](auto& e) { e.sample_on_backup = true; },
                [](auto& e) { e.final_evidence_current = false; },
                [](auto& e) { e.generation = 0; },
                [](auto& e) { e.map_version = 0; },
                [](auto& e) { ++e.certificate_generation; },
                [](auto& e) { ++e.certificate_map_version; },
                [](auto& e) { e.certificate_from_tt = .6; },
                [](auto& e) { e.certificate_until_tt = .4; },
                [](auto& e) { e.sample_tt = -1.0; },
                [](auto& e) { e.sample_tt = std::numeric_limits<double>::quiet_NaN(); },
                [](auto& e) { e.certificate_until_tt = std::numeric_limits<double>::infinity(); }}) {
            auto e = healthy(); mutate(e); ++rejected;
            require(!policy::eligible(e), "unhealthy retransmission preserves ordinary retry");
        }
        std::cout << "goal_retransmit_policy_test=PASS raw_change_cases=14 healthy_rejections="
                  << rejected << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "goal_retransmit_policy_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
