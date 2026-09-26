#include <fsm/async_from_rest_planning.hpp>
#include <fsm/async_certified_recovery.hpp>

#include <atomic>
#include <cassert>
#include <iostream>
#include <limits>
#include <mutex>
#include <thread>

namespace policy = super_planner::async_from_rest;

policy::Identity identity() {
    policy::Identity value;
    value.id = 1;
    value.hold_revision = 3;
    value.generation_before = 17;
    value.goal_queued = 4;
    value.goal_accepted = 4;
    value.brake_revision = 2;
    value.ack.supported = true;
    value.ack.required = false;
    value.ack.advertised_or_event = false;
    return value;
}

policy::Completion completion() {
    policy::Completion value;
    value.successful = value.goal_valid = value.generating = true;
    value.rejected = false;
    value.no_active_brake = value.hold_current = value.no_pending_goal = true;
    value.not_stopped = value.map_fresh = value.certificate_safe = true;
    value.certificate_current = value.sample_valid = value.velocity_valid = true;
    value.handoff_continuous = true;
    value.sample_finished = false;
    value.result_generation = value.current_generation = 18;
    value.current_map = 44;
    return value;
}

int main() {
    assert(!policy::enabledSetting(nullptr));
    assert(!policy::enabledSetting("0"));
    assert(!policy::enabledSetting("true"));
    assert(policy::enabledSetting("1"));
    assert(policy::freshStationaryTwist(true, 0.0, 10.0, 10.05));
    assert(policy::freshStationaryTwist(true, 0.05, 10.0, 10.05));
    assert(!policy::freshStationaryTwist(false, 0.0, 10.0, 10.05));
    assert(!policy::freshStationaryTwist(true, 0.051, 10.0, 10.05));
    assert(!policy::freshStationaryTwist(true, 0.0, 10.0, 10.101));
    assert(!policy::freshStationaryTwist(true, 0.0, 10.01, 10.0));
    assert(!policy::freshStationaryTwist(true, -0.01, 10.0, 10.05));
    const auto nan = std::numeric_limits<double>::quiet_NaN();
    const auto inf = std::numeric_limits<double>::infinity();
    for (const double invalid : {nan, inf, -inf}) {
        assert(!policy::freshStationaryTwist(true, invalid, 10.0, 10.05));
        assert(!policy::freshStationaryTwist(true, 0.0, invalid, 10.05));
        assert(!policy::freshStationaryTwist(true, 0.0, 10.0, invalid));
    }
    const auto before = identity();
    const auto proof = completion();
    assert(policy::mayComplete(before, before, proof));
    for (auto member : {&policy::Identity::id, &policy::Identity::hold_revision,
                        &policy::Identity::generation_before, &policy::Identity::goal_queued,
                        &policy::Identity::goal_accepted, &policy::Identity::brake_revision,
                        &policy::Identity::event_requested, &policy::Identity::event_completed}) {
        auto changed = before;
        ++(changed.*member);
        assert(!policy::mayComplete(before, changed, proof));
    }
    for (auto member : {&policy::Completion::successful, &policy::Completion::goal_valid,
                        &policy::Completion::generating, &policy::Completion::no_active_brake,
                        &policy::Completion::hold_current, &policy::Completion::no_pending_goal,
                        &policy::Completion::not_stopped, &policy::Completion::map_fresh,
                        &policy::Completion::certificate_safe, &policy::Completion::certificate_current,
                        &policy::Completion::sample_valid, &policy::Completion::velocity_valid,
                        &policy::Completion::handoff_continuous}) {
        auto failed = proof;
        failed.*member = false;
        assert(!policy::mayComplete(before, before, failed));
    }
    auto failed = proof;
    failed.sample_finished = true;
    assert(!policy::mayComplete(before, before, failed));
    failed = proof;
    failed.rejected = true;
    assert(!policy::mayComplete(before, before, failed));
    failed = proof;
    --failed.result_generation;
    assert(!policy::mayComplete(before, before, failed));
    failed = proof;
    ++failed.current_generation;
    assert(!policy::mayComplete(before, before, failed));

    // An explicitly armed Full recovery requires exactly its captured ACK.
    auto full = before;
    full.ack.required = full.ack.advertised_or_event = true;
    full.ack.minimum = full.ack.target = full.ack.latest_target = 6;
    full.ack.stamp = 1234;
    full.ack.map = 43;
    full.ack.boundary_map = 42;
    full.ack.target_acked = full.ack.latest_acked = true;
    assert(policy::mayComplete(full, full, proof));
    auto wrong_ack = full;
    ++wrong_ack.ack.stamp;
    assert(!policy::mayComplete(full, wrong_ack, proof));
    failed = proof;
    failed.current_map = 42;
    assert(!policy::mayComplete(full, full, failed));

    assert(policy::mayPublishPinnedHold(true, 3, 3, 17, 17, true));
    assert(!policy::mayPublishPinnedHold(false, 3, 3, 17, 17, true));
    assert(!policy::mayPublishPinnedHold(true, 3, 4, 17, 17, true));
    assert(!policy::mayPublishPinnedHold(true, 3, 3, 18, 17, true));
    assert(!policy::mayPublishPinnedHold(true, 3, 3, 17, 17, false));
    assert(!policy::mayPublishPinnedHold(true, 3, 3, 0, 0, true));
    assert(policy::mayUsePlannerSampleForBrake(false, 18, 17));
    assert(policy::mayUsePlannerSampleForBrake(true, 17, 17));
    assert(!policy::mayUsePlannerSampleForBrake(true, 18, 17));
    assert(!policy::mayUsePlannerSampleForBrake(true, 18, 0));

    assert(policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 17, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 18, 10.0, 18, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.1, 17, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 16, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 17, 0.5, 0.6, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 17, 1.1, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 17, 0.5, 0.0, 1.0, false));
    assert(!policy::mayPublishOrdinarySample(0, 10.0, 0, 10.0, 0, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, nan, 17, nan, 17, 0.5, 0.0, 1.0, true));
    assert(!policy::mayPublishOrdinarySample(17, 10.0, 17, 10.0, 17, nan, 0.0, 1.0, true));

    // Deterministic old-command ABA: the command thread prepares gen 17,
    // then pauses while main installs/release-publishes gen 18. Returning to
    // FOLLOW does not authorize the delayed gen-17 command to publish.
    std::mutex publication_mutex;
    std::atomic<bool> sample_prepared{false}, new_path_published{false};
    std::uint64_t current_generation = 17, certificate_generation = 17;
    double current_start_wt = 10.0;
    bool following = true, quarantined = false;
    bool delayed_command_published = false;
    std::thread delayed_command([&] {
        const std::uint64_t sample_generation = 17;
        const double sample_start_wt = 10.0;
        sample_prepared.store(true, std::memory_order_release);
        while (!new_path_published.load(std::memory_order_acquire)) std::this_thread::yield();
        std::lock_guard<std::mutex> lock(publication_mutex);
        assert(following && !quarantined);  // Original flag-only test would pass.
        delayed_command_published = policy::mayPublishOrdinarySample(
                sample_generation, sample_start_wt, current_generation, current_start_wt,
                certificate_generation, 0.5, 0.0, 1.0, true);
    });
    while (!sample_prepared.load(std::memory_order_acquire)) std::this_thread::yield();
    {
        std::lock_guard<std::mutex> lock(publication_mutex);
        following = false;
        quarantined = true;
        current_generation = certificate_generation = 18;
        current_start_wt = 11.0;
        following = true;
        quarantined = false;
        new_path_published.store(true, std::memory_order_release);
    }
    delayed_command.join();
    assert(!delayed_command_published);

    struct State {
        double values[3][4]{};
        double& operator()(int axis, int order) { return values[axis][order]; }
        double operator()(int axis, int order) const { return values[axis][order]; }
    };
    State held, candidate;
    const auto handoff = [&] {
        return super_planner::trajectory_handoff::compareAt<State>(10.25,
                [&](double wt, State& out) { assert(wt == 10.25); out = held; return true; },
                [&](double wt, State& out) { assert(wt == 10.25); out = candidate; return true; });
    };
    assert(handoff().continuous);
    candidate(0, 0) = 0.002;
    assert(!handoff().continuous);
    candidate = State{};
    candidate(0, 1) = 0.011;
    assert(!handoff().continuous);
    candidate = State{};
    candidate(0, 2) = 0.101;
    assert(!handoff().continuous);
    candidate(0, 2) = std::numeric_limits<double>::quiet_NaN();
    assert(!handoff().continuous);

    ::fsm::goal_retransmit::Request raw;
    raw.position = {1.0, 2.0, 3.0};
    raw.quaternion = {1.0, 0.0, 0.0, 0.0};
    raw.frame = "world";
    raw.creation_stamp_ns = 123456789;
    const auto replay = [&](const ::fsm::goal_retransmit::Request& incoming,
                            const bool active = true) {
        return policy::mayIgnoreExactInFlightReplay(active, true, true,
                before, before, raw, raw, incoming);
    };
    assert(replay(raw));
    assert(!replay(raw, false));  // Same message after draining is not this optimization.
    auto changed_raw = raw;
    ++changed_raw.creation_stamp_ns;
    assert(!replay(changed_raw));
    changed_raw = raw;
    changed_raw.frame = "map";
    assert(!replay(changed_raw));
    changed_raw = raw;
    changed_raw.quaternion[3] = 0.1;
    assert(!replay(changed_raw));
    changed_raw = raw;
    changed_raw.position[0] = 1.01;
    assert(!replay(changed_raw));
    changed_raw = raw;
    changed_raw.creation_stamp_ns = 0;
    assert(!replay(changed_raw));
    changed_raw = raw;
    changed_raw.quaternion[0] = std::numeric_limits<double>::quiet_NaN();
    assert(!replay(changed_raw));
    assert(!policy::mayIgnoreExactInFlightReplay(true, false, true,
            before, before, raw, raw, raw));
    assert(!policy::mayIgnoreExactInFlightReplay(true, true, false,
            before, before, raw, raw, raw));
    auto newer_goal = before;
    ++newer_goal.goal_queued;
    assert(!policy::mayIgnoreExactInFlightReplay(true, true, true,
            before, newer_goal, raw, raw, raw));

    struct Request { policy::Identity identity; };
    struct Result { Request request; bool successful{false}; };
    super_planner::async_recovery::SingleFlight<Request, Result> slot;
    assert(slot.submit({before}));
    std::atomic<bool> computing{false}, finish_requested{false};
    std::thread worker([&] {
        const auto request = slot.begin();
        assert(request);
        computing.store(true, std::memory_order_release);
        while (!finish_requested.load(std::memory_order_acquire)) std::this_thread::yield();
        assert(slot.finish({*request, true}));
    });
    while (!computing.load(std::memory_order_acquire)) std::this_thread::yield();
    // Main sees a new goal while computation is in progress. Latest goal is
    // retained externally; no second planner operation can overwrite receipt.
    auto current = before;
    ++current.goal_queued;
    assert(slot.busy() && !slot.submit({current}));
    finish_requested.store(true, std::memory_order_release);
    worker.join();
    const auto result = slot.completed();
    assert(result && result->successful);
    assert(!policy::mayComplete(result->request.identity, current, proof));
    assert(!slot.submit({current}));
    // Discarding receipt is NOT release of the pinned hold/quarantine.
    assert(slot.release(before.id));
    assert(!policy::mayUsePlannerSampleForBrake(true, 18, 17));
    assert(policy::mayPublishPinnedHold(true, 3, 3, 17, 17, true));
    ++current.id;
    assert(slot.submit({current}));
    std::cout << "async_from_rest_planning_test: PASS\n";
}
