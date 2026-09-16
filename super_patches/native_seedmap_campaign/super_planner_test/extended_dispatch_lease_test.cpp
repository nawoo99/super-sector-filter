// Includes the unchanged default-policy regression as a separate entry point.
#define main default_policy_regression_main
#include "demand_replan_policy_test.cpp"
#undef main

namespace {
void checkExtendedRejectionMatrix() {
    using R = dr::Reason;
    auto p = dr::policyForExactExtendedOptIn(true, "1");
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
        // The sole intentionally relaxed gate receives its own boundary tests.
        if (std::string(test.name) == "deadline") continue;
        auto e = validEvidence(); test.mutate(e);
        require(dr::decide(p, e).reason == test.reason,
                std::string("extended unchanged gate: ") + test.name);
    }
}

void checkExactOptInAndBounds() {
    for (const char* setting : std::vector<const char*>{nullptr, "", "0", "true", "1 ", " 1", "500", ".5"}) {
        const auto p = dr::policyForExactExtendedOptIn(true, setting);
        require(p.enabled && !p.allow_extended_dispatch_lease && p.max_dispatch_interval_s == .25,
                "invalid/unset extended opt-in preserves default");
    }
    const auto disabled = dr::policyForExactExtendedOptIn(false, "1");
    require(!disabled.enabled && !disabled.allow_extended_dispatch_lease &&
            disabled.max_dispatch_interval_s == .25, "extension never enables main policy");
    auto p = dr::policyForExactExtendedOptIn(true, "1");
    require(p.enabled && p.allow_extended_dispatch_lease && p.max_dispatch_interval_s == .5,
            "exact additional opt-in selects .5");
    p.allow_extended_dispatch_lease = false;
    require(dr::decide(p, validEvidence()).reason == dr::Reason::INVALID_POLICY,
            ".5 cap cannot bypass explicit policy permission");
    p.allow_extended_dispatch_lease = true;
    for (double cap : {0.0, -.5, .500001, std::numeric_limits<double>::quiet_NaN(),
                       std::numeric_limits<double>::infinity()}) {
        p.max_dispatch_interval_s = cap;
        require(dr::decide(p, validEvidence()).reason == dr::Reason::INVALID_POLICY,
                "invalid extended bound rejects");
    }
}

void checkDeadlineAndHorizon() {
    auto base = dr::policyForExactExtendedOptIn(true, nullptr);
    auto extended = dr::policyForExactExtendedOptIn(true, "1");
    auto e = validEvidence();
    const auto base_required = dr::decide(base, e).required_until_tt;
    require(dr::decide(extended, e).required_until_tt == base_required,
            "rolling geometry/viability/backup horizon unchanged");
    e.steady_now_s = 10.30;
    require(dr::decide(base, e).reason == dr::Reason::DISPATCH_DEADLINE &&
            dr::decide(extended, e).skip(), "only dispatch deadline is extended");
    const double required = dr::decide(extended, e).required_until_tt;
    for (int boundary = 0; boundary < 3; ++boundary) {
        auto short_path = e;
        if (boundary == 0) short_path.trajectory_duration_s = required;
        else if (boundary == 1) {
            short_path.has_appended_backup = true;
            short_path.appended_backup_start_tt = required;
        } else {
            short_path.has_carry_backup = true;
            short_path.carry_backup_start_tt = required;
            short_path.carry_backup_end_tt = required + .1;
        }
        require(dr::decide(extended, short_path).reason == dr::Reason::INSUFFICIENT_MOTION_HORIZON,
                "fresh .5 lease cannot cross exact moving/backup endpoint");
    }
    auto short_receipt = e;
    short_receipt.receipt.checked_until_tt = std::nextafter(required, 0.0);
    require(dr::decide(extended, short_receipt).needsRenewal(), "expired receipt renews despite lease time left");
    short_receipt.renewal_attempted = true;
    require(dr::decide(extended, short_receipt).reason == dr::Reason::VIABILITY_RENEWAL_REJECTED,
            "failed renewal does not fall through to skip");
    for (double cap : {.25, .5}) {
        auto p = extended;
        p.max_dispatch_interval_s = cap;
        // Binary-exact periods isolate deadline comparison from decimal-sum rounding.
        p.demand_timer_period_s = .0625;
        p.scheduling_reserve_s = .03125;
        auto boundary = validEvidence();
        boundary.last_successful_dispatch_steady_s = 0;
        boundary.steady_now_s = cap - .09375;
        require(dr::decide(p, boundary).skip(), "deadline equality allowed");
        p.max_dispatch_interval_s = std::nextafter(cap, 0.0);
        require(dr::decide(p, boundary).reason == dr::Reason::DISPATCH_DEADLINE,
                "one-ULP-short deadline rejects");
        p.max_dispatch_interval_s = cap;
        boundary.steady_now_s += .001;
        require(dr::decide(p, boundary).reason == dr::Reason::DISPATCH_DEADLINE,
                "renewal elapsed time cannot spend expired lease");
    }
    for (auto mutate : std::vector<std::function<void(dr::Evidence&)>>{
            [](auto& v) { v.pending_or_updating_goal = true; },
            [](auto& v) { v.recovery_pending = true; },
            [](auto& v) { v.brake_or_revalidation_pending = true; },
            [](auto& v) { v.failure_or_rejection_since_success = true; },
            [](auto& v) { ++v.map_version; },
            [](auto& v) { v.final_evidence_current = false; }}) {
        auto changed = e; mutate(changed);
        require(!dr::decide(extended, changed).skip(), "intervening demand or map invalidates continuation");
    }
}

void checkCadenceAndCounters() {
    for (bool use_extended : {false, true}) {
        auto p = dr::policyForExactExtendedOptIn(true, use_extended ? "1" : nullptr);
        unsigned guards = 0, commands = 0, demands = 0, solves = 0, skips = 0;
        double last_dispatch = 0.0, max_dispatch_gap = 0.0;
        dr::DecisionCounters counters;
        for (unsigned ms = 0; ms <= 1000; ++ms) {
            if (ms % 10 == 0) { ++guards; ++commands; }
            if (ms == 0 || ms % 66 != 0) continue;
            ++demands;
            auto e = validEvidence();
            e.steady_now_s = ms * .001;
            e.last_successful_dispatch_steady_s = last_dispatch;
            e.trajectory_time_s = .4 + ms * .001;
            const auto d = dr::decide(p, e);
            counters.record(d.reason);
            if (d.skip()) ++skips;
            else {
                ++solves;
                max_dispatch_gap = std::max(max_dispatch_gap, e.steady_now_s - last_dispatch);
                last_dispatch = e.steady_now_s;  // Mock an own successful commit only.
            }
        }
        require(guards == 101 && commands == 101 && demands == 15,
                "all timer callbacks retained for each cap");
        require(solves == (use_extended ? 2u : 5u) && skips == (use_extended ? 13u : 10u),
                "bounded synthetic dispatch cadence");
        require(std::abs(max_dispatch_gap - (use_extended ? .462 : .198)) < 1e-12,
                "skips never slide the dispatch origin");
        require(counters.total() == demands && counters.count(dr::Reason::SKIP) == skips,
                "final reason histogram sums to actual checks");
    }
    dr::DecisionCounters counters;
    for (std::size_t i = 0; i < dr::DecisionCounters::size; ++i)
        counters.record(static_cast<dr::Reason>(i));
    require(counters.total() == dr::DecisionCounters::size, "all reason enum bins counted once");
    counters.record(static_cast<dr::Reason>(999));
    require(counters.total() == dr::DecisionCounters::size &&
            counters.count(static_cast<dr::Reason>(999)) == 0, "invalid reason cannot index out of bounds");
}
}  // namespace

int main() {
    if (default_policy_regression_main() != 0) return 1;
    try {
        checkExtendedRejectionMatrix();
        checkExactOptInAndBounds();
        checkDeadlineAndHorizon();
        checkCadenceAndCounters();
        std::cout << "extended_rejection_cases=40 caps=0.25,0.5 rolling_horizon_unchanged=true\n"
                  << "extended_dispatch_lease_test=PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "extended_dispatch_lease_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
