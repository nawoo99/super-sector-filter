#pragma once

#include <fsm/startup_recovery_completion_policy.hpp>
#include <fsm/goal_retransmit_policy.hpp>
#include <fsm/trajectory_handoff_guard.hpp>
#include <cstdint>
#include <cstring>

namespace super_planner::async_from_rest {

inline bool enabledSetting(const char* value) noexcept {
    return value && std::strcmp(value, "1") == 0;
}

// The ROS2 map's legacy RobotState is pose-only. Callers must supply the
// separately received odometry twist and its receive clock, not RobotState.v.
inline bool freshStationaryTwist(const bool available, const double speed,
                                const double receive_wt, const double now_wt) noexcept {
    return available && std::isfinite(speed) && speed >= 0.0 && speed <= 0.05 &&
           std::isfinite(receive_wt) && std::isfinite(now_wt) &&
           now_wt >= receive_wt && now_wt - receive_wt <= 0.1;
}

// Evaluate under the publication lock. FOLLOW -> quarantine -> FOLLOW is an
// ABA of FSM state: a sample prepared before that sequence is still stale.
inline bool mayPublishOrdinarySample(
        const std::uint64_t sampled_generation, const double sampled_start_wt,
        const std::uint64_t current_generation, const double current_start_wt,
        const std::uint64_t certificate_generation, const double sample_tt,
        const double checked_from_tt, const double checked_to_tt,
        const bool certificate_current) noexcept {
    return sampled_generation != 0 && sampled_generation == current_generation &&
           sampled_generation == certificate_generation &&
           std::isfinite(sampled_start_wt) && std::isfinite(current_start_wt) &&
           sampled_start_wt == current_start_wt && certificate_current &&
           std::isfinite(sample_tt) && std::isfinite(checked_from_tt) &&
           std::isfinite(checked_to_tt) && sample_tt >= checked_from_tt &&
           sample_tt <= checked_to_tt;
}

// A reservation binds computation to the exact main-owned stationary episode.
// Internal planner commit is not permission to publish that new generation.
struct Identity {
    std::uint64_t id{0}, hold_revision{0}, generation_before{0};
    std::uint64_t goal_queued{0}, goal_accepted{0}, brake_revision{0};
    std::uint64_t event_requested{0}, event_completed{0};
    startup_recovery::Ack ack;
};

inline bool ready(const Identity& value) noexcept {
    return value.id != 0 && value.hold_revision != 0 &&
           value.event_requested == value.event_completed &&
           startup_recovery::ready(value.ack);
}

inline bool sameDemand(const Identity& before, const Identity& current) noexcept {
    return ready(before) && ready(current) && before.id == current.id &&
           before.hold_revision == current.hold_revision &&
           before.generation_before == current.generation_before &&
           before.goal_queued == current.goal_queued &&
           before.goal_accepted == current.goal_accepted &&
           before.brake_revision == current.brake_revision &&
           before.event_requested == current.event_requested &&
           before.event_completed == current.event_completed &&
           startup_recovery::same(before.ack, current.ack);
}

// This is in-flight request deduplication only, NOT a healthy-follow token.
// Queue/accepted identity and the exact captured raw message must still agree.
// No duplicate is suppressed after the reservation drains or while a genuinely
// different goal is pending. Invalid/nonpositive creation identities never match.
inline bool mayIgnoreExactInFlightReplay(
        const bool reservation_active, const bool no_pending_goal,
        const bool accepted_source_current,
        const Identity& before, const Identity& current,
        const ::fsm::goal_retransmit::Request& captured,
        const ::fsm::goal_retransmit::Request& accepted,
        const ::fsm::goal_retransmit::Request& incoming) noexcept {
    return reservation_active && no_pending_goal && accepted_source_current &&
           sameDemand(before, current) &&
           ::fsm::goal_retransmit::sameRequest(captured, accepted) &&
           ::fsm::goal_retransmit::sameRequest(captured, incoming);
}

struct Completion {
    bool successful{false}, rejected{true}, goal_valid{false};
    bool generating{false}, no_active_brake{false}, hold_current{false};
    bool no_pending_goal{false}, not_stopped{false}, map_fresh{false};
    bool certificate_safe{false}, certificate_current{false};
    bool sample_valid{false}, sample_finished{true}, velocity_valid{false};
    bool handoff_continuous{false};
    std::uint64_t result_generation{0}, current_generation{0}, current_map{0};
};

inline bool mayComplete(const Identity& before, const Identity& current,
                        const Completion& proof) noexcept {
    return sameDemand(before, current) && proof.successful && !proof.rejected &&
           proof.goal_valid && proof.generating && proof.no_active_brake &&
           proof.hold_current && proof.no_pending_goal && proof.not_stopped &&
           proof.map_fresh && proof.certificate_safe && proof.certificate_current &&
           proof.sample_valid && !proof.sample_finished && proof.velocity_valid && proof.handoff_continuous &&
           proof.result_generation > before.generation_before &&
           proof.result_generation == proof.current_generation && proof.current_map != 0 &&
           (!before.ack.required || proof.current_map >= before.ack.map);
}

// Evaluate under the same safety mutex that installs/replaces/releases a hold.
// A late worker commit cannot change which held sample the command timer owns.
inline bool mayPublishPinnedHold(const bool active,
                                const std::uint64_t sampled_revision,
                                const std::uint64_t current_revision,
                                const std::uint64_t sampled_generation,
                                const std::uint64_t held_generation,
                                const bool current_certificate) noexcept {
    return active && sampled_revision != 0 && sampled_revision == current_revision &&
           held_generation != 0 && sampled_generation == held_generation &&
           current_certificate;
}

// Caller must additionally establish fresh state/geometric validity. This
// predicate only prevents an unpublished ordinary result becoming a brake's
// initial sample while it is still quarantined, including after result discard.
inline bool mayUsePlannerSampleForBrake(const bool quarantine_active,
                                       const std::uint64_t sample_generation,
                                       const std::uint64_t held_generation) noexcept {
    return !quarantine_active ||
           (held_generation != 0 && sample_generation == held_generation);
}

}  // namespace super_planner::async_from_rest
