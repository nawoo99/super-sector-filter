// Real Fsm enqueue/token/epoch/GoalUpdateScope integration seam. The probe
// supplies healthy-proof booleans and arranges consume handoff without ROS/map.
// This does NOT prove actual optimizer/certificate/ROS callback integration.
#include <fsm/fsm.h>

#include <atomic>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

namespace {
using Request = fsm::goal_retransmit::Request;
int checks = 0;
void require(bool condition, const char* why) {
    ++checks;
    if (!condition) throw std::runtime_error(why);
}
Request makeRequest(const std::int64_t id = 100) {
    return {{1.0, 2.0, 3.0}, {1.0, 0.0, 0.0, 0.0}, "world", id};
}

class Probe final : public fsm::Fsm {
public:
    using Snapshot = GoalDemandSnapshot;
    using Token = GoalRetransmissionToken;
    Probe() { machine_state_ = FOLLOW_TRAJ; }
    void queue(const Request& r) {
        enqueueGoal(super_utils::Vec3f(r.position[0], r.position[1], r.position[2]),
                    super_utils::Quatf(r.quaternion[0], r.quaternion[1], r.quaternion[2], r.quaternion[3]),
                    r.frame, r.creation_stamp_ns);
    }
    Snapshot snapshot() const { return getGoalDemandSnapshot(); }
    std::uint64_t epoch() const { return goalRetransmissionEpoch(); }
    std::uint64_t coalesced() const { return goalRetransmissionCoalescedCount(); }
    Token candidate(const Request& r) const { return goalRetransmissionCandidate(r); }
    Request acceptedRaw() const {
        std::lock_guard<std::mutex> lock(pending_goal_mutex_);
        return accepted_raw_goal_request_;
    }
    std::uint64_t acceptedSourceRevision() const {
        std::lock_guard<std::mutex> lock(pending_goal_mutex_);
        return accepted_raw_goal_source_revision_;
    }
    void consumeForTest(const bool accepted, const std::function<void()>& in_gap = [] {}) {
        PendingGoal consumed;
        {
            std::lock_guard<std::mutex> lock(pending_goal_mutex_);
            if (!pending_goal_.valid) throw std::runtime_error("no pending goal");
            consumed = pending_goal_;
            pending_goal_.valid = false;
            goal_update_in_progress_ = true;
        }
        GoalUpdateScope scope{*this};
        scope.consumed = consumed;
        in_gap();
        scope.accepted = accepted;
    }
    bool arm(const std::uint64_t generation = 7, const std::uint64_t brake = 1,
             const std::uint64_t event = 2, const std::uint64_t refresh = 3) {
        return publishGoalRetransmissionToken(snapshot(), epoch(), generation,
                                             brake, event, refresh, [] { return true; });
    }
    bool admit(const Request& request, const bool healthy = true) {
        const auto token = candidate(request);
        const bool skip = token.valid && tryCoalesceGoalRetransmission(
                request, token, [&] { return healthy; });
        if (!skip) queue(request);  // Actual latest-wins fallback.
        return skip;
    }
    bool useOldToken(const Request& request, const Token& token) {
        return tryCoalesceGoalRetransmission(request, token, [] { return true; });
    }
    void invalidateFailureForTest() { invalidateGoalRetransmissionToken(); }
    void stateAba() { ChangeState("test", EMER_STOP); ChangeState("test", FOLLOW_TRAJ); }
    void completedState() { ChangeState("test", WAIT_GOAL); }
private:
    void publishPolyTraj() override {}
    void publishCurPoseToPath() override {}
    void resetVisualizedPath() override {}
};

void prepare(Probe& p, const Request& r) {
    p.queue(r); p.consumeForTest(true);
    require(p.arm(), "qualified commit seam arms token");
}

void identityAndEpochCases() {
    const auto r = makeRequest();
    Probe p; prepare(p, r);
    const auto before = p.snapshot();
    const auto epoch = p.epoch();
    const auto token = p.candidate(r);
    require(p.admit(r), "healthy exact retransmission coalesced");
    const auto after = p.snapshot();
    require(before.queued_revision == after.queued_revision &&
            before.accepted_revision == after.accepted_revision &&
            !after.pending_or_updating && p.epoch() == epoch &&
            p.candidate(r).generation == token.generation && p.coalesced() == 1,
            "coalescing changes only its diagnostic count, not goal/epoch/generation");

    for (const auto& change : std::vector<std::function<void(Request&)>>{
            [](auto& x) { ++x.creation_stamp_ns; },
            [](auto& x) { x.creation_stamp_ns = 0; },
            [](auto& x) { x.frame = "map"; },
            [](auto& x) { x.position[0] += .001; },
            [](auto& x) { x.position[1] += .001; },
            [](auto& x) { x.position[2] += .001; },
            [](auto& x) { x.quaternion[0] = -1.0; },
            [](auto& x) { x.quaternion[3] = .01; },
            [](auto& x) { x.position[2] = std::numeric_limits<double>::quiet_NaN(); }}) {
        Probe q; prepare(q, r); auto changed = r; change(changed);
        require(!q.admit(changed), "new stamp/raw pose/yaw/frame always enters normal queue");
        require(q.snapshot().queued_revision == 2 && q.snapshot().pending_or_updating,
                "changed request is not lost");
    }
    Probe unhealthy; prepare(unhealthy, r);
    require(!unhealthy.admit(r, false) && unhealthy.snapshot().pending_or_updating,
            "blocked/recovery/uncertified same identity preserves retry");
    Probe failed; prepare(failed, r); failed.invalidateFailureForTest();
    require(!failed.admit(r), "failure invalidates old successful token");
    Probe aba; prepare(aba, r); const auto old = aba.candidate(r); aba.stateAba();
    require(!aba.useOldToken(r, old) && !aba.admit(r), "FOLLOW emergency FOLLOW cannot reuse token");
    Probe done; prepare(done, r); done.completedState();
    require(!done.admit(r), "completed state preserves same-identity retry");
}

void pendingAndConsumeCases() {
    const auto first = makeRequest(100), second = makeRequest(101);
    Probe p; prepare(p, first); p.queue(second);
    require(!p.candidate(first).valid, "pending new goal excludes old accepted retransmission");
    p.consumeForTest(true, [&] {
        require(p.snapshot().pending_or_updating, "consume-to-accept gap visible");
        require(!p.candidate(second).valid, "processing request has no successful token");
        p.queue(makeRequest(102));
    });
    require(p.acceptedRaw().creation_stamp_ns == 101 && p.acceptedSourceRevision() == 2 &&
            p.snapshot().queued_revision == 3 && p.snapshot().pending_or_updating,
            "accepted identity belongs to consumed request, not newer overwritten pending slot");
    require(!p.arm(), "new pending request prevents token publication");
    p.consumeForTest(true);
    require(p.acceptedRaw().creation_stamp_ns == 102 && p.acceptedSourceRevision() == 3 && p.arm(),
            "newest consumed request gets its own token only after qualified commit seam");
    p.queue(makeRequest(103)); p.consumeForTest(false);
    require(!p.arm() && !p.admit(makeRequest(103)), "rejected goal remains a normal retry");
}

void concurrentCases() {
    const auto request = makeRequest();
    for (const bool mix_new_requests : {false, true}) {
        Probe p; prepare(p, request);
        constexpr unsigned count = 1000;
        std::atomic_int ready{0}, finished{0};
        std::atomic_bool go{false}, valid{true};
        std::atomic_uint kept{0}, suppressed{0};
        auto start = [&] {
            ready.fetch_add(1, std::memory_order_release);
            while (!go.load(std::memory_order_acquire)) std::this_thread::yield();
        };
        auto producer = [&](bool fresh) {
            start();
            for (unsigned n = 0; n < count; ++n) {
                const auto input = fresh ? makeRequest(1000 + n) : request;
                const bool skip = p.admit(input);
                if (fresh && skip) valid.store(false);
                (skip ? suppressed : kept).fetch_add(1);
            }
            finished.fetch_add(1, std::memory_order_release);
        };
        std::thread a(producer, false), b(producer, mix_new_requests);
        std::thread reader([&] {
            start(); std::uint64_t last = 1;
            do {
                const auto snap = p.snapshot();
                if (snap.queued_revision < last || snap.accepted_revision != 1 ||
                    (snap.queued_revision > 1 && !snap.pending_or_updating)) valid.store(false);
                last = snap.queued_revision;
            } while (finished.load(std::memory_order_acquire) != 2);
        });
        while (ready.load(std::memory_order_acquire) != 3) std::this_thread::yield();
        go.store(true, std::memory_order_release);
        a.join(); b.join(); reader.join();
        require(valid.load(), "barrier-started concurrent queue snapshots coherent");
        require(kept + suppressed == 2 * count && p.coalesced() == suppressed &&
                p.snapshot().queued_revision == 1 + kept,
                "all concurrent requests counted as one normal enqueue or one coalescing");
        if (!mix_new_requests)
            require(suppressed == 2 * count && kept == 0, "identical concurrent retransmissions preserve revisions");
        else require(kept >= count, "all fresh identity requests survive concurrent repeats");
    }
}
}  // namespace

int main() {
    try {
        if (!fsm::goal_retransmit::enabledSetting(std::getenv("SUPER_GOAL_RETRANSMIT_IDENTITY"))) {
            Probe disabled;
            const auto r = makeRequest();
            disabled.queue(r); disabled.consumeForTest(true);
            require(!disabled.arm() && !disabled.admit(r) &&
                    disabled.snapshot().queued_revision == 2 && disabled.coalesced() == 0,
                    "default-off retains normal repeated-goal queue behavior");
            std::cout << "goal_retransmit_fsm_metadata_test=PASS default_disabled_queue=true\n";
            return 0;
        }
        identityAndEpochCases(); pendingAndConsumeCases(); concurrentCases();
        std::cout << "goal_retransmit_fsm_metadata_test=PASS checks=" << checks
                  << " concurrent_requests=4000 proof=stubbed_no_ROS_solver\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "goal_retransmit_fsm_metadata_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
