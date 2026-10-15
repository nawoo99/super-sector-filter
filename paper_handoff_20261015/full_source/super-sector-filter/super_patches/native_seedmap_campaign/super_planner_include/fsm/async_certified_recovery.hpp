#pragma once

#include <fsm/startup_recovery_completion_policy.hpp>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <mutex>
#include <optional>
#include <utility>

namespace super_planner::async_recovery {

inline bool enabledSetting(const char* value) noexcept {
    return value && std::strcmp(value, "1") == 0;
}

struct BrakeCommandIdentity {
    std::uint64_t revision{0}, generation{0};
    double start_wt{0.0};
};

// Evaluate under the same safety lock as recovery release/brake replacement,
// and retain that lock through command publication. Sampling alone does not
// authorize a later old-brake heartbeat after a new ordinary path is released.
inline bool mayPublishBrake(const bool active, const BrakeCommandIdentity& sampled,
                            const BrakeCommandIdentity& current) noexcept {
    return active && sampled.revision != 0 && sampled.revision == current.revision &&
           sampled.generation == current.generation && std::isfinite(sampled.start_wt) &&
           sampled.start_wt == current.start_wt;
}

// An optimizer result is not authority to release a brake. These values bind
// it to the exact stopped episode, accepted goal, and pre-compute observation.
struct Identity {
    std::uint64_t id{0}, brake_revision{0}, generation_before{0};
    std::uint64_t goal_queued{0}, goal_accepted{0};
    std::uint64_t event_requested{0}, event_completed{0};
    startup_recovery::Ack ack;
};

inline bool ready(const Identity& value) noexcept {
    return value.id != 0 && value.brake_revision != 0 &&
           value.event_requested == value.event_completed &&
           startup_recovery::ready(value.ack);
}

inline bool sameDemand(const Identity& before, const Identity& after) noexcept {
    return ready(before) && ready(after) && before.id == after.id &&
           before.brake_revision == after.brake_revision &&
           before.goal_queued == after.goal_queued &&
           before.goal_accepted == after.goal_accepted &&
           before.event_requested == after.event_requested &&
           before.event_completed == after.event_completed &&
           startup_recovery::same(before.ack, after.ack);
}

struct Completion {
    bool successful{false}, rejected{true}, goal_valid{false};
    bool brake_active{false}, brake_finished{false}, stable_pose{false};
    bool no_pending_goal{false}, not_stopped{false}, map_fresh{false};
    bool certificate_safe{false}, certificate_current{false};
    bool sample_valid{false}, sample_finished{true}, velocity_valid{false};
    std::uint64_t result_generation{0}, current_generation{0}, current_map{0};
};

inline bool mayComplete(const Identity& before, const Identity& current,
                        const Completion& proof) noexcept {
    return sameDemand(before, current) && proof.successful && !proof.rejected &&
           proof.goal_valid && proof.brake_active && proof.brake_finished &&
           proof.stable_pose && proof.no_pending_goal && proof.not_stopped &&
           proof.map_fresh && proof.certificate_safe && proof.certificate_current &&
           proof.sample_valid && !proof.sample_finished && proof.velocity_valid &&
           proof.result_generation > before.generation_before &&
           proof.result_generation == proof.current_generation && proof.current_map != 0 &&
           (!before.ack.required || proof.current_map >= before.ack.map);
}

// Exactly one outstanding operation: no growing retry queue and no detached
// thread. Ready remains reserved until the main callback completes/discards
// it, so the existing replan executor cannot replace a not-yet-finalized path.
template<class Request, class Result> class SingleFlight {
    enum class Phase { Idle, Pending, Computing, Ready };
    mutable std::mutex mutex_;
    Phase phase_{Phase::Idle};
    std::optional<Request> request_;
    std::optional<Result> result_;
public:
    bool submit(Request request) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (phase_ != Phase::Idle || request.identity.id == 0) return false;
        request_ = std::move(request);
        phase_ = Phase::Pending;
        return true;
    }
    std::optional<Request> begin() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (phase_ != Phase::Pending) return std::nullopt;
        phase_ = Phase::Computing;
        return request_;
    }
    bool finish(Result result) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (phase_ != Phase::Computing || !request_ ||
            result.request.identity.id != request_->identity.id) return false;
        result_ = std::move(result);
        phase_ = Phase::Ready;
        return true;
    }
    std::optional<Result> completed() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return phase_ == Phase::Ready ? result_ : std::nullopt;
    }
    bool release(const std::uint64_t id) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (phase_ != Phase::Ready || !request_ || request_->identity.id != id) return false;
        result_.reset(); request_.reset(); phase_ = Phase::Idle;
        return true;
    }
    bool busy() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return phase_ != Phase::Idle;
    }
};
}  // namespace super_planner::async_recovery
