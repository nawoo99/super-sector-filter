#include "startup_recovery_completion_policy.hpp"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace sr = super_planner::startup_recovery;
namespace {
int checks = 0;
void require(bool v, const char* m) { ++checks; if (!v) throw std::runtime_error(m); }
sr::Before before(bool frontend) {
    sr::Before b;
    b.armed = b.announced = b.generating_from_rest = b.no_prior_command = true;
    b.empty_snapshot = b.no_active_brake = b.no_pending_goal = b.map_fresh = true;
    b.no_recovery_demand = true;
    b.revision = 3; b.generation = 0; b.goal_queued = b.goal_accepted = 1;
    b.ack.supported = true;
    b.ack.required = b.ack.advertised_or_event = frontend;
    if (frontend) {
        b.ack.minimum = b.ack.target = b.ack.latest_target = 2;
        b.ack.stamp = 345; b.ack.map = 20; b.ack.boundary_map = 15;
        b.ack.target_acked = b.ack.latest_acked = true;
        b.event_requested = b.event_completed = 1;
    }
    return b;
}
sr::After after(const sr::Before& b) {
    sr::After a;
    a.armed = a.announced = a.following = a.no_active_brake = true;
    a.no_pending_goal = a.no_recovery_demand = a.explicit_safe = a.map_fresh = true;
    a.immutable_map = a.exact_current_certificate = a.valid_current_sample = true;
    a.sample_finite = a.final_evidence_current = true;
    a.sample_finished = a.sample_on_backup = false;
    a.revision = b.revision; a.generation = 1; a.map = 21;
    a.goal_queued = b.goal_queued; a.goal_accepted = b.goal_accepted;
    a.event_requested = b.event_requested; a.event_completed = b.event_completed;
    a.ack = b.ack;
    return a;
}
}  // namespace

int main() {
    try {
        require(!sr::mayPlan({}), "defaults may not plan");
        require(!sr::mayComplete({}, {}), "defaults may not close");
        require(sr::mustWaitForActivation(true, true, 0), "contended activation holds only first-path planning");
        require(!sr::mustWaitForActivation(false, true, 0), "contention does not suppress other FSM work");
        require(!sr::mustWaitForActivation(true, false, 0), "nonempty path is not initial contention hold");
        require(!sr::mustWaitForActivation(true, true, 1), "known generation keeps original behavior");
        for (bool frontend : {false, true}) {
            auto b = before(frontend);
            const auto a = after(b);
            require(sr::mayPlan(b), "valid initial planning proof");
            require(!sr::mustWaitForAck(b), "ready ACK does not stop original work");
            require(sr::mayComplete(b, a), "valid initial completion proof");
            const std::vector<std::function<void(sr::Before&)>> bad_before{
                [](auto& v) { v.armed = false; }, [](auto& v) { v.announced = false; },
                [](auto& v) { v.generating_from_rest = false; }, [](auto& v) { v.revision = 0; },
                [](auto& v) { v.no_prior_command = false; }, [](auto& v) { v.empty_snapshot = false; },
                [](auto& v) { v.generation = 1; }, [](auto& v) { v.no_active_brake = false; },
                [](auto& v) { v.no_pending_goal = false; }, [](auto& v) { v.map_fresh = false; },
                [](auto& v) { v.no_recovery_demand = false; }, [](auto& v) { ++v.event_requested; }
            };
            for (const auto& mutate : bad_before) {
                auto fault = b; mutate(fault);
                require(!sr::mayComplete(fault, a), "missing pre-plan proof cannot be reconstructed afterward");
            }
            const std::vector<std::function<void(sr::After&)>> bad_after{
                [](auto& v) { v.armed = false; }, [](auto& v) { v.announced = false; },
                [](auto& v) { ++v.revision; }, [](auto& v) { v.following = false; },
                [](auto& v) { v.no_active_brake = false; }, [](auto& v) { v.no_pending_goal = false; },
                [](auto& v) { v.no_recovery_demand = false; }, [](auto& v) { v.generation = 0; },
                [](auto& v) { v.map = 0; }, [](auto& v) { ++v.goal_queued; },
                [](auto& v) { ++v.goal_accepted; }, [](auto& v) { ++v.event_requested; },
                [](auto& v) { ++v.event_completed; }, [](auto& v) { v.explicit_safe = false; },
                [](auto& v) { v.map_fresh = false; }, [](auto& v) { v.immutable_map = false; },
                [](auto& v) { v.exact_current_certificate = false; },
                [](auto& v) { v.valid_current_sample = false; },
                [](auto& v) { v.sample_finite = false; }, [](auto& v) { v.sample_finished = true; },
                [](auto& v) { v.sample_on_backup = true; },
                [](auto& v) { v.final_evidence_current = false; }
            };
            for (const auto& mutate : bad_after) {
                auto fault = a; mutate(fault);
                require(!sr::mayComplete(b, fault), "new demand or incomplete proof blocks release");
            }
        }
        auto b = before(true); const auto a = after(b);
        auto newer = b;
        ++newer.ack.latest_target;
        require(sr::mayPlan(newer) && !sr::mustWaitForAck(newer), "newer ACKed request does not deadlock selected target");
        require(sr::mayComplete(newer, after(newer)), "selected exact target plus newer ACKed request completes");
        newer.ack.latest_acked = false;
        require(!sr::mayPlan(newer) && sr::mustWaitForAck(newer), "newer unACKed request holds no-trajectory planning");
        for (int kind = 0; kind < 2; ++kind) {
            auto consumer_needed = b;
            if (kind == 0) consumer_needed.no_pending_goal = false;
            else consumer_needed.no_recovery_demand = false;
            require(!sr::mayPlan(consumer_needed) && !sr::mustWaitForAck(consumer_needed),
                    "ineligible proof must not block work that consumes goal/topology demand");
        }
        auto legacy = b;
        legacy.ack.supported = false;
        legacy.ack.target_acked = false;
        require(!sr::mayPlan(legacy) && !sr::mustWaitForAck(legacy),
                "unsupported legacy frontend unchanged and may not complete");
        for (const auto& mutate : std::vector<std::function<void(sr::Ack&)>>{
                [](auto& v) { v.required = false; }, [](auto& v) { v.minimum = 0; },
                [](auto& v) { v.target = 1; }, [](auto& v) { v.stamp = 0; },
                [](auto& v) { v.target_acked = false; }, [](auto& v) { v.latest_acked = false; },
                [](auto& v) { v.latest_target = 1; }, [](auto& v) { v.map = v.boundary_map; }}) {
            auto fault = b; mutate(fault.ack);
            require(!sr::mayComplete(fault, a), "post-path ACK cannot substitute missing pre-plan ACK");
            auto final = a; mutate(final.ack);
            require(!sr::mayComplete(b, final), "changed or unacked final token cannot close");
        }
        auto changed = a; ++changed.ack.stamp;
        require(!sr::mayComplete(b, changed), "another exact stamp never substitutes");
        changed = a; changed.map = b.ack.map - 1;
        require(!sr::mayComplete(b, changed), "certificate predating ACK rejects");
        std::cout << "startup_recovery_checks=" << checks << '\n'
                  << "startup_recovery_completion_test=PASS\n";
    } catch (const std::exception& e) {
        std::cerr << "startup_recovery_completion_test=FAIL reason=" << e.what() << '\n';
        return 1;
    }
}
