#include <fsm/async_certified_recovery.hpp>
#include <atomic>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

namespace ar = super_planner::async_recovery;
namespace {
int checks = 0;
void require(bool value, const char* message) { ++checks; if (!value) throw std::runtime_error(message); }
ar::Identity identity(const bool frontend) {
    ar::Identity value;
    value.id = 1; value.brake_revision = 2; value.generation_before = 3;
    value.goal_queued = value.goal_accepted = 4;
    value.ack.supported = true;
    value.ack.required = value.ack.advertised_or_event = frontend;
    if (frontend) {
        value.event_requested = value.event_completed = 5;
        value.ack.minimum = value.ack.target = value.ack.latest_target = 6;
        value.ack.stamp = 700; value.ack.map = 8; value.ack.boundary_map = 7;
        value.ack.target_acked = value.ack.latest_acked = true;
    }
    return value;
}
ar::Completion completion() {
    ar::Completion value;
    value.successful = value.goal_valid = value.brake_active = value.brake_finished = true;
    value.stable_pose = value.no_pending_goal = value.not_stopped = value.map_fresh = true;
    value.certificate_safe = value.certificate_current = value.sample_valid = value.velocity_valid = true;
    value.rejected = value.sample_finished = false;
    value.result_generation = value.current_generation = 9; value.current_map = 10;
    return value;
}
struct Request { ar::Identity identity; };
struct Result { Request request; };
}

int main() {
    try {
        for (const char* setting : std::vector<const char*>{nullptr, "", "0", "true", "01", "1 "})
            require(!ar::enabledSetting(setting), "only exact opt-in enables policy");
        require(ar::enabledSetting("1"), "exact opt-in");
        const ar::BrakeCommandIdentity original{3, 5, 123.5};
        require(ar::mayPublishBrake(true, original, original), "current active brake may publish");
        require(!ar::mayPublishBrake(false, original, original), "recovered old brake may not publish");
        require(!ar::mayPublishBrake(true, original, {4, 5, 123.5}), "replacement revision binds sample even at same generation/time");
        require(!ar::mayPublishBrake(true, original, {3, 6, 123.5}), "replacement generation binds sample");
        require(!ar::mayPublishBrake(true, original, {3, 5, 124.5}), "replacement time binds sample");
        require(!ar::mayPublishBrake(true, {}, {}), "uninitialized brake receipt is invalid");
        // Deterministic real-thread interleaving: command captures an old brake;
        // main then publishes/releases a new path; only then may command attempt
        // its final publication transaction. No old EMER_STOP message may leak.
        for (const bool replace_instead_of_release : {false, true}) {
            std::mutex safety; std::condition_variable cv;
            bool sampled = false, transitioned = false, active = true, stale_published = false;
            auto current = original;
            std::thread command([&] {
                ar::BrakeCommandIdentity captured;
                {
                    std::lock_guard<std::mutex> lock(safety);
                    captured = current; sampled = true;
                }
                cv.notify_one();
                std::unique_lock<std::mutex> lock(safety);
                cv.wait(lock, [&] { return transitioned; });
                stale_published = ar::mayPublishBrake(active, captured, current);
            });
            {
                std::unique_lock<std::mutex> lock(safety);
                cv.wait(lock, [&] { return sampled; });
                if (replace_instead_of_release) ++current.revision;
                else active = false;
                transitioned = true;
            }
            cv.notify_one(); command.join();
            require(!stale_published, "old captured brake cannot publish after main transition");
        }
        require(!ar::mayComplete({}, {}, {}), "default is fail-closed");
        for (const bool frontend : {false, true}) {
            const auto before = identity(frontend); const auto proof = completion();
            require(ar::mayComplete(before, before, proof), "valid completion");
            const std::vector<std::function<void(ar::Identity&)>> changes{
                [](auto& x){ ++x.id; }, [](auto& x){ ++x.brake_revision; },
                [](auto& x){ ++x.goal_queued; }, [](auto& x){ ++x.goal_accepted; },
                [](auto& x){ ++x.event_requested; }, [](auto& x){ ++x.event_completed; },
                [](auto& x){ ++x.ack.target; }, [](auto& x){ ++x.ack.stamp; },
                [](auto& x){ ++x.ack.map; }, [](auto& x){ ++x.ack.latest_target; },
                [](auto& x){ x.ack.supported = false; }
            };
            for (const auto& change : changes) {
                auto now = before; change(now);
                require(!ar::mayComplete(before, now, proof), "stale identity cannot release stop");
            }
            const std::vector<std::function<void(ar::Completion&)>> failures{
                [](auto& x){ x.successful = false; }, [](auto& x){ x.rejected = true; },
                [](auto& x){ x.goal_valid = false; }, [](auto& x){ x.brake_active = false; },
                [](auto& x){ x.brake_finished = false; }, [](auto& x){ x.stable_pose = false; },
                [](auto& x){ x.no_pending_goal = false; }, [](auto& x){ x.not_stopped = false; },
                [](auto& x){ x.map_fresh = false; }, [](auto& x){ x.certificate_safe = false; },
                [](auto& x){ x.certificate_current = false; }, [](auto& x){ x.sample_valid = false; },
                [](auto& x){ x.sample_finished = true; }, [](auto& x){ x.velocity_valid = false; },
                [](auto& x){ x.result_generation = 3; }, [](auto& x){ ++x.current_generation; },
                [](auto& x){ x.current_map = 0; }
            };
            for (const auto& fail : failures) {
                auto bad = proof; fail(bad);
                require(!ar::mayComplete(before, before, bad), "missing final proof keeps stop");
            }
        }
        auto front = identity(true); auto stale_map = completion(); stale_map.current_map = 7;
        require(!ar::mayComplete(front, front, stale_map), "map must include exact ACK");
        ar::SingleFlight<Request, Result> slot;
        require(!slot.busy() && !slot.begin() && !slot.completed(), "empty lifecycle");
        require(!slot.submit({{}}), "zero request ID forbidden");
        for (std::uint64_t id = 1; id <= 20000; ++id) {
            Request request{identity(false)}; request.identity.id = id;
            require(slot.submit(request), "idle submission");
            require(slot.busy() && !slot.submit(request), "one operation maximum");
            const auto compute = slot.begin();
            require(compute && !slot.begin() && !slot.release(id), "computing cannot be replaced/released");
            Result wrong{request}; ++wrong.request.identity.id;
            require(!slot.finish(wrong), "wrong result cannot finalize another request");
            require(slot.finish({request}) && !slot.finish({request}), "single result publication");
            require(slot.completed().has_value() && slot.busy(), "ready reserves replan ownership");
            require(!slot.release(id + 1) && slot.release(id) && !slot.busy(), "exact release/discard");
        }
        // Exercise actual producer/consumer hand-off; pending work can outlive
        // an episode, but only the main-side identity check can authorize it.
        std::atomic<bool> done{false};
        std::thread worker([&] {
            while (!done.load()) {
                if (const auto job = slot.begin()) slot.finish(Result{*job});
                else std::this_thread::yield();
            }
        });
        for (std::uint64_t id = 1; id <= 1000; ++id) {
            Request request{identity(true)}; request.identity.id = id;
            if (!slot.submit(request)) std::terminate();
            while (!slot.completed()) std::this_thread::yield();
            auto newer = request.identity; ++newer.brake_revision;
            require(!ar::mayComplete(slot.completed()->request.identity, newer, completion()),
                    "new brake cannot be released by finished old job");
            require(slot.release(id), "discard stale asynchronous result");
        }
        done.store(true); worker.join();
        std::cout << "async certified recovery checks=" << checks << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
