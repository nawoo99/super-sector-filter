#include "demand_replan_policy.hpp"
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace dr = super_planner::demand_replan;
namespace {
void require(bool condition, const std::string& name) { if (!condition) throw std::runtime_error(name); }
dr::Policy policy() { dr::Policy p; p.enabled = true; return p; }
dr::Evidence validEvidence() {
    dr::Evidence e;
    e.enforcement_enabled = e.viability_enabled = e.ordinary_follow = true;
    e.stop_finished_or_plan_from_rest = e.pending_or_updating_goal = false;
    e.goal_matches_successful_commit = true;
    e.recovery_pending = e.brake_or_revalidation_pending = e.failure_or_rejection_since_success = false;
    e.special_escape_certificate = false;
    e.map_fresh_for_motion = e.certificate_explicitly_safe = e.final_evidence_current = true;
    e.simulation_clock_monotonic = true;
    e.has_successful_ordinary_commit = true;
    e.sample_finished = e.sample_on_backup = false;
    e.generation = e.last_successful_generation = e.certificate_generation = 7;
    e.map_version = e.certificate_map_version = 5;
    e.steady_now_s = 10.066; e.last_successful_dispatch_steady_s = 10.0;
    e.trajectory_start_wt = 20.0; e.trajectory_time_s = 0.4; e.trajectory_duration_s = 4.0;
    e.certificate_from_tt = 0.2; e.certificate_until_tt = 4.0;
    e.receipt.valid = e.receipt.every_state_evaluated = true;
    e.receipt.trajectory_generation = 7; e.receipt.map_version = 5;
    e.receipt.start_wt = 20.0; e.receipt.checked_from_tt = 0.2; e.receipt.checked_until_tt = 2.2;
    e.receipt.sample_dt_s = 0.3; e.receipt.sample_count = 8; e.receipt.policy_revision = 1;
    return e;
}
}  // namespace

int main() {
    try {
        using R = dr::Reason;
        auto p = policy();
        auto e = validEvidence();
        require(dr::decide(p, e).skip(), "complete current evidence skips");
        require(!dr::decide(dr::Policy{}, e).skip(), "default policy disabled");
        require(!dr::decide(p, dr::Evidence{}).skip(), "default evidence rejects");
        struct Case { const char* name; std::function<void(dr::Evidence&)> mutate; R reason; };
        const std::vector<Case> cases{
            {"enforcement", [](auto& v) { v.enforcement_enabled = false; }, R::NOT_ORDINARY},
            {"viability", [](auto& v) { v.viability_enabled = false; }, R::NOT_ORDINARY},
            {"fsm", [](auto& v) { v.ordinary_follow = false; }, R::NOT_ORDINARY},
            {"plan_from_rest", [](auto& v) { v.stop_finished_or_plan_from_rest = true; }, R::NOT_ORDINARY},
            {"special_escape", [](auto& v) { v.special_escape_certificate = true; }, R::NOT_ORDINARY},
            {"pending_goal", [](auto& v) { v.pending_or_updating_goal = true; }, R::NEW_GOAL},
            {"goal_identity", [](auto& v) { v.goal_matches_successful_commit = false; }, R::NEW_GOAL},
            {"recovery", [](auto& v) { v.recovery_pending = true; }, R::RECOVERY_PENDING},
            {"brake", [](auto& v) { v.brake_or_revalidation_pending = true; }, R::SAFETY_PENDING},
            {"rejection", [](auto& v) { v.failure_or_rejection_since_success = true; }, R::FAILURE_OR_REJECTION},
            {"no_commit", [](auto& v) { v.has_successful_ordinary_commit = false; }, R::NO_SUCCESSFUL_LEASE},
            {"no_new_generation", [](auto& v) { --v.last_successful_generation; }, R::NO_SUCCESSFUL_LEASE},
            {"map_stale", [](auto& v) { v.map_fresh_for_motion = false; }, R::STALE_OR_UNCERTIFIED_MAP},
            {"disabled_cert", [](auto& v) { v.certificate_explicitly_safe = false; }, R::STALE_OR_UNCERTIFIED_MAP},
            {"cert_gen", [](auto& v) { --v.certificate_generation; }, R::STALE_OR_UNCERTIFIED_MAP},
            {"cert_map", [](auto& v) { --v.certificate_map_version; }, R::STALE_OR_UNCERTIFIED_MAP},
            {"finished", [](auto& v) { v.sample_finished = true; }, R::TRAJECTORY_MISMATCH},
            {"negative_tt", [](auto& v) { v.trajectory_time_s = -0.001; }, R::TRAJECTORY_MISMATCH},
            {"clock_reset", [](auto& v) { v.steady_now_s = 9.9; }, R::CLOCK_INVALID},
            {"sim_clock_backwards", [](auto& v) { v.simulation_clock_monotonic = false; }, R::CLOCK_INVALID},
            {"deadline", [](auto& v) { v.steady_now_s = 10.2; }, R::DISPATCH_DEADLINE},
            {"backup_sample", [](auto& v) { v.sample_on_backup = true; }, R::ON_BACKUP},
            {"appended_now", [](auto& v) { v.has_appended_backup = true; v.appended_backup_start_tt = 0.4; }, R::ON_BACKUP},
            {"appended_soon", [](auto& v) { v.has_appended_backup = true; v.appended_backup_start_tt = 0.5; }, R::INSUFFICIENT_MOTION_HORIZON},
            {"carry_now", [](auto& v) { v.has_carry_backup = true; v.carry_backup_start_tt = 0.3; v.carry_backup_end_tt = 0.5; }, R::ON_BACKUP},
            {"carry_soon", [](auto& v) { v.has_carry_backup = true; v.carry_backup_start_tt = 0.5; v.carry_backup_end_tt = 0.8; }, R::INSUFFICIENT_MOTION_HORIZON},
            {"short_tail", [](auto& v) { v.trajectory_duration_s = 0.5; }, R::INSUFFICIENT_MOTION_HORIZON},
            {"cert_from", [](auto& v) { v.certificate_from_tt = 0.401; }, R::INSUFFICIENT_GEOMETRY},
            {"cert_until", [](auto& v) { v.certificate_until_tt = 0.5; }, R::INSUFFICIENT_GEOMETRY},
            {"receipt_invalid", [](auto& v) { v.receipt.valid = false; }, R::NEED_VIABILITY_RENEWAL},
            {"state_failed", [](auto& v) { v.receipt.every_state_evaluated = false; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_gen", [](auto& v) { --v.receipt.trajectory_generation; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_map", [](auto& v) { --v.receipt.map_version; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_start", [](auto& v) { v.receipt.start_wt += 0.1; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_from", [](auto& v) { v.receipt.checked_from_tt = 0.5; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_until", [](auto& v) { v.receipt.checked_until_tt = 0.5; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_policy", [](auto& v) { ++v.receipt.policy_revision; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_sampling", [](auto& v) { v.receipt.sample_dt_s = 0.4; }, R::NEED_VIABILITY_RENEWAL},
            {"receipt_empty", [](auto& v) { v.receipt.sample_count = 0; }, R::NEED_VIABILITY_RENEWAL},
            {"renewal_failed", [](auto& v) { v.receipt.valid = false; v.renewal_attempted = true; }, R::VIABILITY_RENEWAL_REJECTED},
            {"final_race", [](auto& v) { v.final_evidence_current = false; }, R::EVIDENCE_CHANGED}
        };
        for (const auto& test : cases) {
            e = validEvidence(); test.mutate(e);
            const auto result = dr::decide(p, e);
            require(result.reason == test.reason, std::string(test.name) + " got " + dr::reasonName(result.reason));
        }
        unsigned nonfinite_cases = 0;
        for (const double invalid : {std::numeric_limits<double>::quiet_NaN(),
                                     std::numeric_limits<double>::infinity(),
                                     -std::numeric_limits<double>::infinity()}) {
            for (auto field : {&dr::Evidence::steady_now_s, &dr::Evidence::last_successful_dispatch_steady_s,
                               &dr::Evidence::trajectory_start_wt, &dr::Evidence::trajectory_time_s,
                               &dr::Evidence::trajectory_duration_s, &dr::Evidence::certificate_from_tt,
                               &dr::Evidence::certificate_until_tt}) {
                e = validEvidence(); e.*field = invalid;
                require(!dr::decide(p, e).skip(), "nonfinite evidence must not skip"); ++nonfinite_cases;
            }
        }
        e = validEvidence(); e.has_carry_backup = true; e.carry_backup_start_tt = 0.1; e.carry_backup_end_tt = 0.2;
        require(dr::decide(p, e).skip(), "past carried backup no longer blocks ordinary interval");
        p.max_dispatch_interval_s = 0.251;
        require(dr::decide(p, validEvidence()).reason == R::INVALID_POLICY, "initial policy max cap cannot exceed .25s");
        p = policy(); e = validEvidence();
        const auto required = dr::decide(p, e).required_until_tt;
        e.has_appended_backup = true; e.appended_backup_start_tt = required;
        require(dr::decide(p, e).reason == R::INSUFFICIENT_MOTION_HORIZON, "no commit exactly on backup boundary");
        e = validEvidence(); e.receipt.checked_until_tt = required;
        require(dr::decide(p, e).skip(), "exact checked endpoint includes required reserve");
        e.receipt.checked_until_tt = std::nextafter(required, 0.0);
        require(dr::decide(p, e).needsRenewal(), "one ULP short receipt needs renewal");

        // Scheduling simulation: the pure solver decision never owns guard or
        // command cadence. A 100 Hz loop continues through every skipped solve.
        unsigned guard_ticks = 0, command_ticks = 0, demand_ticks = 0, solves = 0, skips = 0;
        double last_dispatch = 0.0;
        for (unsigned ms = 0; ms <= 1000; ++ms) {
            if (ms % 10 == 0) { ++guard_ticks; ++command_ticks; }
            if (ms == 0 || ms % 66 != 0) continue;
            ++demand_ticks;
            e = validEvidence(); e.steady_now_s = ms * 0.001; e.last_successful_dispatch_steady_s = last_dispatch;
            e.trajectory_time_s = 0.4 + ms * 0.001;
            const auto result = dr::decide(p, e);
            if (result.skip()) ++skips;
            else { ++solves; last_dispatch = e.steady_now_s; }
        }
        require(guard_ticks == 101 && command_ticks == 101 && demand_ticks == 15,
                "all guard/command/demand timer invocations retained");
        require(skips > 0 && solves > 0 && solves + skips == demand_ticks, "bounded ordinary solve deferrals");
        std::cout << "decision_cases=" << cases.size() << " nonfinite_cases=" << nonfinite_cases
                  << " guard_ticks=" << guard_ticks << " command_ticks=" << command_ticks
                  << " demand_ticks=" << demand_ticks << " solves=" << solves << " skips=" << skips << '\n';
        std::cout << "demand_replan_policy_test=PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "demand_replan_policy_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
