// Integration seam test: real Fsm queue/getter/RAII/outcome code, linked against
// the built libsuper. It deliberately does not initialize ROS, a map or a solver.
#include <fsm/fsm.h>

#include <atomic>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
int checks = 0;
void require(bool value, const char* message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}

class Probe final : public fsm::Fsm {
public:
    using Snapshot = GoalDemandSnapshot;
    using Outcome = MovingReplanOutcome;

    Snapshot snapshot() const { return getGoalDemandSnapshot(); }
    void queue(double x) {
        enqueueGoal(super_utils::Vec3f(x, 0, 1), super_utils::Quatf::Identity());
    }
    bool started() const { return started_.load(std::memory_order_acquire); }
    bool noPendingConsume() { return tryConsumePendingGoal(); }

    // Only the consume handoff is arranged by the probe: map/goal processing
    // cannot run without a planner. The scope type and its destructor are the
    // actual production implementation, not a copy of the revision policy.
    void processForTest(bool accept, const std::function<void()>& in_gap) {
        {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!pending_goal_.valid) throw std::runtime_error("no pending goal");
            pending_goal_.valid = false;
            goal_update_in_progress_ = true;
        }
        GoalUpdateScope scope{*this};
        in_gap();
        scope.accepted = accept;
    }

    void setEarlyGate(int gate) {
        machine_state_ = gate == 1 ? WAIT_GOAL : FOLLOW_TRAJ;
        stop = gate == 0;
        finish_plan = gate == 2;
        plan_from_rest_ = gate == 3;
    }
    Outcome movingReplan() { return callReplanOnce(); }
    bool planFromRestPending() const { return plan_from_rest_.load(); }

private:
    void publishPolyTraj() override {}
    void publishCurPoseToPath() override {}
    void resetVisualizedPath() override {}
};

void queueAndScopeCases() {
    Probe probe;
    auto state = probe.snapshot();
    require(state.queued_revision == 0 && state.accepted_revision == 0 &&
                    !state.pending_or_updating, "initial metadata");
    require(!probe.noPendingConsume(), "actual empty consume returns false");
    probe.queue(1);
    state = probe.snapshot();
    require(state.queued_revision == 1 && state.accepted_revision == 0 &&
                    state.pending_or_updating && probe.started(), "enqueue metadata");
    probe.processForTest(false, [&] {
        const auto in_gap = probe.snapshot();
        require(in_gap.pending_or_updating && in_gap.queued_revision == 1 &&
                        in_gap.accepted_revision == 0, "consume gap blocks skip");
    });
    state = probe.snapshot();
    require(!state.pending_or_updating && state.accepted_revision == 0,
            "rejected scope clears progress without acceptance");

    probe.queue(2);
    probe.processForTest(true, [&] {
        require(probe.snapshot().pending_or_updating, "accepted scope still pending in gap");
        // A real callback on another thread can queue a newer goal while map
        // validation runs outside the queue mutex. Acceptance must not erase it.
        std::thread producer([&] { probe.queue(3); });
        producer.join();
        const auto in_gap = probe.snapshot();
        require(in_gap.pending_or_updating && in_gap.queued_revision == 3 &&
                        in_gap.accepted_revision == 0, "new enqueue retained during gap");
    });
    state = probe.snapshot();
    require(state.pending_or_updating && state.queued_revision == 3 &&
                    state.accepted_revision == 1, "old acceptance preserves newer pending goal");
    probe.processForTest(true, [] {});
    state = probe.snapshot();
    require(!state.pending_or_updating && state.queued_revision == 3 &&
                    state.accepted_revision == 2, "new goal accepted once");

    probe.queue(4);
    bool exception_seen = false;
    try {
        probe.processForTest(true, [] { throw std::runtime_error("map processing seam"); });
    } catch (const std::runtime_error&) {
        exception_seen = true;
    }
    state = probe.snapshot();
    require(exception_seen && !state.pending_or_updating &&
                    state.accepted_revision == 2, "unwind clears gap without accepting");
}

void synchronizedQueueCases() {
    Probe probe;
    constexpr int writes_per_thread = 1000;
    std::atomic_int writers_finished{0};
    std::atomic_bool snapshots_valid{true};
    auto writer = [&] {
        for (int i = 0; i < writes_per_thread; ++i) probe.queue(i);
        writers_finished.fetch_add(1, std::memory_order_release);
    };
    std::thread first(writer);
    std::thread second(writer);
    std::thread reader([&] {
        std::uint64_t previous = 0;
        do {
            const auto value = probe.snapshot();
            if (value.queued_revision < previous || value.accepted_revision != 0 ||
                (value.queued_revision != 0 && !value.pending_or_updating)) {
                snapshots_valid.store(false, std::memory_order_relaxed);
            }
            previous = value.queued_revision;
        } while (writers_finished.load(std::memory_order_acquire) != 2);
    });
    first.join();
    second.join();
    reader.join();
    const auto final = probe.snapshot();
    require(snapshots_valid.load(), "synchronized concurrent snapshots coherent");
    require(final.queued_revision == 2 * writes_per_thread &&
                    final.accepted_revision == 0 && final.pending_or_updating,
            "all concurrent enqueues counted latest-only");
}

void actualEarlyOutcomeCases() {
    for (int gate = 0; gate < 4; ++gate) {
        Probe probe;
        probe.setEarlyGate(gate);
        const auto outcome = probe.movingReplan();
        require(!outcome.attempted && !outcome.successful && !outcome.finished &&
                        outcome.committed_generation == 0 &&
                        outcome.committed_time == rog_map::MapHealthClock::time_point{},
                "actual early replan does not claim own commit");
        if (gate == 3) require(!probe.planFromRestPending(), "existing rest gate reset retained");
    }
}
}  // namespace

int main() {
    try {
        queueAndScopeCases();
        synchronizedQueueCases();
        actualEarlyOutcomeCases();
        std::cout << "metadata_checks=" << checks
                  << " concurrent_enqueues=2000 actual_early_replan_gates=4\n"
                  << "demand_replan_fsm_metadata_test=PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "demand_replan_fsm_metadata_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
