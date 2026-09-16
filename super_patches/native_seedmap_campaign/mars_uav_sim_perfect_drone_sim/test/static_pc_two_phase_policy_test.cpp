#include <perfect_drone_sim/static_pc_two_phase_policy.hpp>

#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace phase = perfect_drone::static_pc_two_phase;

void require(const bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template <typename Function>
void invalid(Function&& function) {
    bool caught = false;
    try { function(); } catch (const std::invalid_argument&) { caught = true; }
    require(caught, "expected invalid argument");
}

// A scheduling fixture, not an actual ROS timer test. Publication exactly uses
// the existing predicate and subscriber-state update to check the handoff.
struct Fixture {
    phase::Policy policy{true};
    int last_subscribers{0};
    unsigned calls{0}, publications{0}, cancel_fast{0}, reset_fast{0};

    void dispatch(const bool slow, const double elapsed, const int subscribers,
                  const bool ros_active = false) {
        if (slow ? !policy.coarseActive() : !policy.fastActive()) return;
        ++calls;
        if ((subscribers > 0 && subscribers != last_subscribers) ||
            (elapsed > 5.0 && elapsed < 5.1)) ++publications;
        last_subscribers = subscribers;
        const auto decision = policy.observeAfterLegacy(elapsed, ros_active);
        cancel_fast += decision.change == phase::Change::Coarse;
        reset_fast += decision.reset_fast_timer;
    }
};

int main() {
    try {
        require(!phase::parseEnabled(nullptr, 1), "default legacy");
        require(!phase::parseEnabled("0", 1), "explicit legacy");
        require(!phase::parseEnabled(nullptr, 100), "old100 remains separate");
        require(phase::parseEnabled("1", 1), "exact two-phase opt-in");
        invalid([] { phase::parseEnabled("1", 100); });
        for (const char* value : {"", "true", "01", "1 ", " 1", "100", "-1"})
            invalid([&] { phase::parseEnabled(value, 1); });

        phase::Policy disabled;
        for (const double t : {-1.0, 0.0, 5.1, 10.0, 2.0}) {
            require(disabled.observeAfterLegacy(t, true).change == phase::Change::None,
                    "disabled policy does not alter old schedules");
            require(disabled.fastActive() && !disabled.coarseActive(), "disabled remains legacy");
        }

        Fixture schedule;
        schedule.dispatch(false, 0.0, 1);  // Reader first, same first opportunity.
        require(schedule.publications == 1, "reader-first count transition");
        schedule.dispatch(true, 1.0, 2);
        require(schedule.calls == 1 && schedule.last_subscribers == 1,
                "early slow timer performs no graph/publication-state work");
        for (const double t : {4.999, 5.0, 5.001, 5.025, 5.050, 5.099})
            schedule.dispatch(false, t, 1);
        require(schedule.publications == 5 && schedule.cancel_fast == 0,
                "all scripted legacy bootstrap opportunities retained");
        // A new subscriber on the exact handoff tick must be handled before cancel.
        schedule.dispatch(false, 5.1, 2);
        require(schedule.publications == 6 && schedule.last_subscribers == 2 &&
                schedule.cancel_fast == 1 && schedule.policy.coarseActive(),
                "handoff after legacy count-change check at exact5.1");
        const auto handoff_calls = schedule.calls;
        schedule.dispatch(false, 5.101, 3);  // Already queued canceled fast callback.
        require(schedule.calls == handoff_calls && schedule.last_subscribers == 2,
                "queued canceled fast callback cannot publish");
        schedule.dispatch(true, 5.1, 2);  // Simultaneously-ready slow callback.
        require(schedule.publications == 6, "no duplicate bootstrap at handoff");
        schedule.dispatch(true, 5.2, 1);
        schedule.dispatch(true, 5.3, 0);
        schedule.dispatch(true, 5.4, 1);
        require(schedule.publications == 8 && schedule.last_subscribers == 1,
                "same subscriber state across coarse disconnect/reconnect");

        schedule.dispatch(true, 5.05, 1);  // Clock rolls back into bootstrap window.
        require(schedule.policy.fallbackLatched() && schedule.policy.fastActive() &&
                schedule.reset_fast == 1 && schedule.publications == 9,
                "clock rollback restores fast timer after current legacy work");
        const auto rollback_calls = schedule.calls;
        schedule.dispatch(true, 5.06, 2);
        require(schedule.calls == rollback_calls, "slow callback disabled after fallback");
        schedule.dispatch(false, 5.07, 1);
        schedule.dispatch(false, 10.0, 1);
        require(schedule.policy.fastActive() && schedule.cancel_fast == 1,
                "fallback never reenters coarse mode");

        for (const double invalid_time : {-1.0, std::numeric_limits<double>::quiet_NaN(),
                                         std::numeric_limits<double>::infinity()}) {
            phase::Policy p(true);
            require(p.observeAfterLegacy(5.2, false).change == phase::Change::Coarse,
                    "test enters coarse");
            const auto decision = p.observeAfterLegacy(invalid_time, false);
            require(decision.change == phase::Change::LegacyFallback &&
                    decision.fallback == phase::Fallback::InvalidElapsed && decision.reset_fast_timer,
                    "invalid time restores fast mode");
        }
        phase::Policy simulated(true);
        const auto sim = simulated.observeAfterLegacy(0.0, true);
        require(sim.change == phase::Change::LegacyFallback &&
                sim.fallback == phase::Fallback::SimulatedTime && !sim.reset_fast_timer,
                "simulated time preserves already-active legacy mode");
        require(simulated.observeAfterLegacy(100.0, false).change == phase::Change::None &&
                simulated.fastActive(), "simulated-clock exclusion is permanent");
        phase::Policy repeated(true);
        require(repeated.observeAfterLegacy(5.099999, false).change == phase::Change::None,
                "strict just-before boundary");
        require(repeated.observeAfterLegacy(5.1, false).change == phase::Change::Coarse,
                "exact endpoint changes once");
        require(repeated.observeAfterLegacy(5.1, false).change == phase::Change::None,
                "equal clock value is not rollback");
        std::cout << "static_pc_two_phase_policy_test=PASS default_ms=1 handoff_ros_s=5.1 "
                     "coarse_ms=100 rollback=permanent_legacy timings=synthetic_only\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "static_pc_two_phase_policy_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
