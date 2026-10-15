#pragma once

#include <algorithm>
#include <array>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <limits>

namespace super_planner {
namespace demand_replan {

struct Policy {
    bool enabled{false};
    bool allow_extended_dispatch_lease{false};
    double max_dispatch_interval_s{0.25};
    double demand_timer_period_s{0.066};
    double scheduling_reserve_s{0.02};
    double solve_budget_s{0.10};
    double command_handoff_reserve_s{0.02};
    std::uint32_t viability_policy_revision{1};
    double viability_sample_dt_s{0.3};
};

// Runtime selects only .25 (default) or .5 (exact additional opt-in).
// This never enables the main demand policy by itself.
inline Policy policyForExactExtendedOptIn(const bool enabled,
                                          const char* setting) noexcept {
    Policy policy;
    policy.enabled = enabled;
    policy.allow_extended_dispatch_lease = enabled && setting && std::strcmp(setting, "1") == 0;
    if (policy.allow_extended_dispatch_lease) policy.max_dispatch_interval_s = 0.5;
    return policy;
}

struct StopViabilityReceipt {
    bool valid{false};
    bool every_state_evaluated{false};
    std::uint64_t trajectory_generation{0};
    std::uint64_t map_version{0};
    double start_wt{0.0};
    double checked_from_tt{0.0};
    double checked_until_tt{0.0};
    double sample_dt_s{0.0};
    std::uint64_t sample_count{0};
    std::uint32_t policy_revision{0};
};

// A caller-owned coherent snapshot; unknown/default evidence never permits skip.
struct Evidence {
    bool enforcement_enabled{false};
    bool viability_enabled{false};
    bool ordinary_follow{false};
    bool stop_finished_or_plan_from_rest{true};
    bool pending_or_updating_goal{true};
    bool goal_matches_successful_commit{false};
    bool recovery_pending{true};
    bool brake_or_revalidation_pending{true};
    bool failure_or_rejection_since_success{true};
    bool special_escape_certificate{true};
    bool map_fresh_for_motion{false};
    bool certificate_explicitly_safe{false};
    bool final_evidence_current{false};
    bool simulation_clock_monotonic{false};
    bool has_successful_ordinary_commit{false};
    bool sample_finished{true};
    bool sample_on_backup{true};
    bool has_appended_backup{false};
    bool has_carry_backup{false};
    bool renewal_attempted{false};
    std::uint64_t generation{0};
    std::uint64_t map_version{0};
    std::uint64_t last_successful_generation{0};
    std::uint64_t certificate_generation{0};
    std::uint64_t certificate_map_version{0};
    double steady_now_s{0.0};
    double last_successful_dispatch_steady_s{0.0};
    double trajectory_start_wt{0.0};
    double trajectory_time_s{0.0};
    double trajectory_duration_s{0.0};
    double certificate_from_tt{0.0};
    double certificate_until_tt{0.0};
    double appended_backup_start_tt{std::numeric_limits<double>::infinity()};
    double carry_backup_start_tt{-1.0};
    double carry_backup_end_tt{-1.0};
    StopViabilityReceipt receipt{};
};

enum class Reason {
    DISABLED,
    INVALID_POLICY,
    NOT_ORDINARY,
    NEW_GOAL,
    RECOVERY_PENDING,
    SAFETY_PENDING,
    FAILURE_OR_REJECTION,
    NO_SUCCESSFUL_LEASE,
    STALE_OR_UNCERTIFIED_MAP,
    TRAJECTORY_MISMATCH,
    CLOCK_INVALID,
    DISPATCH_DEADLINE,
    ON_BACKUP,
    INSUFFICIENT_GEOMETRY,
    INSUFFICIENT_MOTION_HORIZON,
    NEED_VIABILITY_RENEWAL,
    VIABILITY_RENEWAL_REJECTED,
    EVIDENCE_CHANGED,
    SKIP
};

// Replan-callback-owned, cumulative final outcomes (after any renewal).
// No atomics, allocation, clocks or per-point work on the decision hot path.
struct DecisionCounters {
    static constexpr std::size_t size = static_cast<std::size_t>(Reason::SKIP) + 1;
    std::array<std::uint64_t, size> values{};
    void record(const Reason reason) noexcept {
        const auto index = static_cast<std::size_t>(reason);
        if (index < size) ++values[index];
    }
    std::uint64_t count(const Reason reason) const noexcept {
        const auto index = static_cast<std::size_t>(reason);
        return index < size ? values[index] : 0;
    }
    std::uint64_t total() const noexcept {
        std::uint64_t sum = 0;
        for (const auto value : values) sum += value;
        return sum;
    }
};

struct Decision {
    Reason reason{Reason::DISABLED};
    double required_until_tt{0.0};
    double dispatch_deadline_steady_s{0.0};
    bool skip() const noexcept { return reason == Reason::SKIP; }
    bool needsRenewal() const noexcept { return reason == Reason::NEED_VIABILITY_RENEWAL; }
};

inline const char* reasonName(const Reason reason) noexcept {
    switch (reason) {
        case Reason::DISABLED: return "DISABLED";
        case Reason::INVALID_POLICY: return "INVALID_POLICY";
        case Reason::NOT_ORDINARY: return "NOT_ORDINARY";
        case Reason::NEW_GOAL: return "NEW_GOAL";
        case Reason::RECOVERY_PENDING: return "RECOVERY_PENDING";
        case Reason::SAFETY_PENDING: return "SAFETY_PENDING";
        case Reason::FAILURE_OR_REJECTION: return "FAILURE_OR_REJECTION";
        case Reason::NO_SUCCESSFUL_LEASE: return "NO_SUCCESSFUL_LEASE";
        case Reason::STALE_OR_UNCERTIFIED_MAP: return "STALE_OR_UNCERTIFIED_MAP";
        case Reason::TRAJECTORY_MISMATCH: return "TRAJECTORY_MISMATCH";
        case Reason::CLOCK_INVALID: return "CLOCK_INVALID";
        case Reason::DISPATCH_DEADLINE: return "DISPATCH_DEADLINE";
        case Reason::ON_BACKUP: return "ON_BACKUP";
        case Reason::INSUFFICIENT_GEOMETRY: return "INSUFFICIENT_GEOMETRY";
        case Reason::INSUFFICIENT_MOTION_HORIZON: return "INSUFFICIENT_MOTION_HORIZON";
        case Reason::NEED_VIABILITY_RENEWAL: return "NEED_VIABILITY_RENEWAL";
        case Reason::VIABILITY_RENEWAL_REJECTED: return "VIABILITY_RENEWAL_REJECTED";
        case Reason::EVIDENCE_CHANGED: return "EVIDENCE_CHANGED";
        case Reason::SKIP: return "SKIP";
    }
    return "UNKNOWN";
}

inline Decision decide(const Policy& p, const Evidence& e) noexcept {
    Decision out;
    const auto finish = [&](Reason reason) { out.reason = reason; return out; };
    if (!p.enabled) return finish(Reason::DISABLED);
    if (!std::isfinite(p.max_dispatch_interval_s) || p.max_dispatch_interval_s <= 0.0 ||
        p.max_dispatch_interval_s > (p.allow_extended_dispatch_lease ? 0.5 : 0.25) ||
        !std::isfinite(p.demand_timer_period_s) ||
        p.demand_timer_period_s <= 0.0 || !std::isfinite(p.scheduling_reserve_s) ||
        p.scheduling_reserve_s < 0.0 || !std::isfinite(p.solve_budget_s) || p.solve_budget_s <= 0.0 ||
        !std::isfinite(p.command_handoff_reserve_s) || p.command_handoff_reserve_s <= 0.0 ||
        p.viability_policy_revision == 0 || !std::isfinite(p.viability_sample_dt_s) ||
        p.viability_sample_dt_s <= 0.0) return finish(Reason::INVALID_POLICY);
    if (!e.enforcement_enabled || !e.viability_enabled || !e.ordinary_follow ||
        e.stop_finished_or_plan_from_rest || e.special_escape_certificate)
        return finish(Reason::NOT_ORDINARY);
    if (e.pending_or_updating_goal || !e.goal_matches_successful_commit)
        return finish(Reason::NEW_GOAL);
    if (e.recovery_pending) return finish(Reason::RECOVERY_PENDING);
    if (e.brake_or_revalidation_pending) return finish(Reason::SAFETY_PENDING);
    if (e.failure_or_rejection_since_success) return finish(Reason::FAILURE_OR_REJECTION);
    if (!e.has_successful_ordinary_commit || e.generation == 0 ||
        e.last_successful_generation != e.generation) return finish(Reason::NO_SUCCESSFUL_LEASE);
    if (!e.map_fresh_for_motion || !e.certificate_explicitly_safe || e.map_version == 0 ||
        e.certificate_generation != e.generation || e.certificate_map_version != e.map_version)
        return finish(Reason::STALE_OR_UNCERTIFIED_MAP);
    if (!std::isfinite(e.trajectory_start_wt) || !std::isfinite(e.trajectory_time_s) ||
        !std::isfinite(e.trajectory_duration_s) || e.trajectory_time_s < 0.0 ||
        e.trajectory_duration_s <= 0.0 || e.sample_finished ||
        e.trajectory_time_s >= e.trajectory_duration_s) return finish(Reason::TRAJECTORY_MISMATCH);
    if (!e.simulation_clock_monotonic ||
        !std::isfinite(e.steady_now_s) || !std::isfinite(e.last_successful_dispatch_steady_s) ||
        e.steady_now_s < e.last_successful_dispatch_steady_s)
        return finish(Reason::CLOCK_INVALID);
    out.dispatch_deadline_steady_s = e.last_successful_dispatch_steady_s + p.max_dispatch_interval_s;
    const double next_dispatch = e.steady_now_s + p.demand_timer_period_s + p.scheduling_reserve_s;
    if (!std::isfinite(next_dispatch) || !std::isfinite(out.dispatch_deadline_steady_s) ||
        next_dispatch > out.dispatch_deadline_steady_s) return finish(Reason::DISPATCH_DEADLINE);
    out.required_until_tt = e.trajectory_time_s + p.demand_timer_period_s +
                           p.scheduling_reserve_s + p.solve_budget_s + p.command_handoff_reserve_s;
    if (!std::isfinite(out.required_until_tt)) return finish(Reason::CLOCK_INVALID);
    if (e.sample_on_backup) return finish(Reason::ON_BACKUP);
    double moving_until_tt = e.trajectory_duration_s;
    if (e.has_appended_backup) {
        if (!std::isfinite(e.appended_backup_start_tt) || e.appended_backup_start_tt <= e.trajectory_time_s)
            return finish(Reason::ON_BACKUP);
        moving_until_tt = std::min(moving_until_tt, e.appended_backup_start_tt);
    }
    if (e.has_carry_backup) {
        if (!std::isfinite(e.carry_backup_start_tt) || !std::isfinite(e.carry_backup_end_tt) ||
            e.carry_backup_start_tt < 0.0 || e.carry_backup_end_tt < e.carry_backup_start_tt)
            return finish(Reason::TRAJECTORY_MISMATCH);
        if (e.trajectory_time_s >= e.carry_backup_start_tt && e.trajectory_time_s <= e.carry_backup_end_tt)
            return finish(Reason::ON_BACKUP);
        if (e.trajectory_time_s < e.carry_backup_start_tt)
            moving_until_tt = std::min(moving_until_tt, e.carry_backup_start_tt);
    }
    if (!std::isfinite(e.certificate_from_tt) || !std::isfinite(e.certificate_until_tt) ||
        e.certificate_from_tt > e.trajectory_time_s || e.certificate_until_tt < out.required_until_tt)
        return finish(Reason::INSUFFICIENT_GEOMETRY);
    if (moving_until_tt <= out.required_until_tt) return finish(Reason::INSUFFICIENT_MOTION_HORIZON);
    const auto& receipt = e.receipt;
    const bool receipt_current = receipt.valid && receipt.every_state_evaluated && receipt.sample_count > 0 &&
        receipt.trajectory_generation == e.generation && receipt.map_version == e.map_version &&
        receipt.policy_revision == p.viability_policy_revision && receipt.sample_dt_s == p.viability_sample_dt_s &&
        std::isfinite(receipt.start_wt) && receipt.start_wt == e.trajectory_start_wt &&
        std::isfinite(receipt.checked_from_tt) && std::isfinite(receipt.checked_until_tt) &&
        receipt.checked_from_tt <= e.trajectory_time_s && receipt.checked_until_tt >= out.required_until_tt;
    if (!receipt_current) return finish(e.renewal_attempted ? Reason::VIABILITY_RENEWAL_REJECTED :
                                                               Reason::NEED_VIABILITY_RENEWAL);
    if (!e.final_evidence_current) return finish(Reason::EVIDENCE_CHANGED);
    return finish(Reason::SKIP);
}

}  // namespace demand_replan
}  // namespace super_planner
