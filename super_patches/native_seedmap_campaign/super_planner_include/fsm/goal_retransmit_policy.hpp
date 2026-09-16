#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>

namespace fsm::goal_retransmit {

inline bool enabledSetting(const char* setting) noexcept {
    return setting && std::strcmp(setting, "1") == 0;
}

inline std::int64_t canonicalPositiveStamp(const std::int32_t sec,
                                         const std::uint32_t nanosec) noexcept {
    if (sec < 0 || nanosec >= 1000000000U) return 0;
    // Nonnegative int32 seconds fit safely in signed64 nanoseconds.
    const auto stamp = static_cast<std::int64_t>(sec) * 1000000000LL + nanosec;
    return stamp > 0 ? stamp : 0;
}

struct Request {
    std::array<double, 3> position{};
    // Preserve original coefficients, not normalized yaw/quaternion equivalence.
    std::array<double, 4> quaternion{};  // w,x,y,z
    std::string frame;
    std::int64_t creation_stamp_ns{0};

    bool validIdentity() const noexcept {
        if (creation_stamp_ns <= 0 || frame.empty()) return false;
        for (const auto value : position) if (!std::isfinite(value)) return false;
        for (const auto value : quaternion) if (!std::isfinite(value)) return false;
        return true;
    }
};

inline bool sameRequest(const Request& a, const Request& b) noexcept {
    return a.validIdentity() && b.validIdentity() &&
            a.creation_stamp_ns == b.creation_stamp_ns && a.frame == b.frame &&
            std::memcmp(a.position.data(), b.position.data(), sizeof(double) * 3) == 0 &&
            std::memcmp(a.quaternion.data(), b.quaternion.data(), sizeof(double) * 4) == 0;
}

struct HealthyFollow {
    bool guard_enabled{false};
    bool ordinary_follow{false};
    bool stopped_finished_or_from_rest{true};
    bool brake_or_revalidation{true};
    bool recovery_or_refresh_pending{true};
    bool failure_or_rejection{true};
    bool immutable_map{false};
    bool map_fresh{false};
    bool explicitly_safe{false};
    bool special_escape{true};
    bool sample_valid_finite{false};
    bool sample_finished{true};
    bool sample_on_backup{true};
    bool final_evidence_current{false};
    std::uint64_t generation{0};
    std::uint64_t map_version{0};
    std::uint64_t certificate_generation{0};
    std::uint64_t certificate_map_version{0};
    double sample_tt{0.0};
    double certificate_from_tt{0.0};
    double certificate_until_tt{0.0};
};

inline bool eligible(const HealthyFollow& e) noexcept {
    return e.guard_enabled && e.ordinary_follow && !e.stopped_finished_or_from_rest &&
            !e.brake_or_revalidation && !e.recovery_or_refresh_pending &&
            !e.failure_or_rejection && e.immutable_map && e.map_fresh &&
            e.explicitly_safe && !e.special_escape && e.sample_valid_finite &&
            !e.sample_finished && !e.sample_on_backup && e.final_evidence_current &&
            e.generation != 0 && e.map_version != 0 &&
            e.certificate_generation == e.generation &&
            e.certificate_map_version == e.map_version &&
            std::isfinite(e.sample_tt) && e.sample_tt >= 0.0 &&
            std::isfinite(e.certificate_from_tt) && std::isfinite(e.certificate_until_tt) &&
            e.certificate_from_tt <= e.sample_tt && e.certificate_until_tt >= e.sample_tt;
}

}  // namespace fsm::goal_retransmit
