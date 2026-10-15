#pragma once
#include <cstdint>

namespace super_planner::startup_recovery {
struct Ack {
    bool supported{false};
    bool required{true};
    bool advertised_or_event{true};
    std::uint64_t minimum{0}, target{0}, stamp{0}, map{0}, boundary_map{0};
    bool target_acked{false};
    std::uint64_t latest_target{0};
    bool latest_acked{false};
};
inline bool ready(const Ack& a) noexcept {
    if (!a.supported) return false;
    if (!a.required) return !a.advertised_or_event && a.minimum == 0;
    return a.advertised_or_event && a.minimum != 0 && a.target >= a.minimum &&
           a.stamp != 0 && a.target_acked && a.map > a.boundary_map &&
           a.latest_target >= a.target && a.latest_acked;
}
inline bool same(const Ack& a, const Ack& b) noexcept {
    return a.supported == b.supported && a.required == b.required &&
           a.advertised_or_event == b.advertised_or_event &&
           a.minimum == b.minimum && a.target == b.target && a.stamp == b.stamp &&
           a.map == b.map && a.boundary_map == b.boundary_map &&
           a.target_acked == b.target_acked && a.latest_target == b.latest_target &&
           a.latest_acked == b.latest_acked;
}
struct Before {
    bool armed{false}, announced{false}, generating_from_rest{false};
    bool no_prior_command{false}, empty_snapshot{false}, no_active_brake{false};
    bool no_pending_goal{false}, map_fresh{false}, no_recovery_demand{false};
    std::uint64_t revision{0}, generation{1};
    std::uint64_t goal_queued{0}, goal_accepted{0};
    std::uint64_t event_requested{0}, event_completed{0};
    Ack ack;
};
inline bool mustWaitForActivation(const bool generating_from_rest,
                                  const bool empty_snapshot,
                                  const std::uint64_t generation) noexcept {
    return generating_from_rest && empty_snapshot && generation == 0;
}
inline bool mayPlan(const Before& b) noexcept {
    return b.armed && b.announced && b.generating_from_rest && b.revision != 0 &&
           b.no_prior_command && b.empty_snapshot && b.generation == 0 &&
           b.no_active_brake && b.no_pending_goal && b.map_fresh &&
           b.no_recovery_demand && b.event_requested == b.event_completed &&
           ready(b.ack);
}
// Only a missing supported Full-ACK gate may delay the original initial solver.
// A pending goal/topology flag is consumed by that original work, so an invalid
// completion proof alone must not suppress it and create a circular wait.
inline bool mustWaitForAck(const Before& b) noexcept {
    return b.armed && b.announced && b.generating_from_rest && b.revision != 0 &&
           b.empty_snapshot && b.generation == 0 && b.no_active_brake &&
           b.ack.supported && !ready(b.ack);
}
struct After {
    bool armed{false}, announced{false}, following{false}, no_active_brake{false};
    bool no_pending_goal{false}, no_recovery_demand{false};
    bool explicit_safe{false}, map_fresh{false}, immutable_map{false};
    bool exact_current_certificate{false}, valid_current_sample{false};
    bool sample_finite{false}, sample_finished{true}, sample_on_backup{true};
    bool final_evidence_current{false};
    std::uint64_t revision{0}, generation{0}, map{0};
    std::uint64_t goal_queued{0}, goal_accepted{0};
    std::uint64_t event_requested{0}, event_completed{0};
    Ack ack;
};
inline bool mayComplete(const Before& b, const After& a) noexcept {
    return mayPlan(b) && a.armed && a.announced && a.revision == b.revision &&
           a.following && a.no_active_brake && a.no_pending_goal &&
           a.no_recovery_demand && a.generation > 0 && a.map != 0 &&
           a.goal_queued == b.goal_queued && a.goal_accepted == b.goal_accepted &&
           a.event_requested == b.event_requested &&
           a.event_completed == a.event_requested && ready(a.ack) && same(b.ack, a.ack) &&
           (!a.ack.required || a.map >= a.ack.map) &&
           a.explicit_safe && a.map_fresh && a.immutable_map &&
           a.exact_current_certificate && a.valid_current_sample && a.sample_finite &&
           !a.sample_finished && !a.sample_on_backup && a.final_evidence_current;
}
}  // namespace super_planner::startup_recovery
