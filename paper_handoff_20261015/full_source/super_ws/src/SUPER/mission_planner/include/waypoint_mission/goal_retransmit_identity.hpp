#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>

namespace mission_planner::goal_retransmit {

inline bool enabledFromSetting(const char* setting) {
    if (!setting || std::strcmp(setting, "0") == 0) return false;
    if (std::strcmp(setting, "1") == 0) return true;
    throw std::invalid_argument("SUPER_GOAL_RETRANSMIT_IDENTITY must be 0 or 1");
}

struct RawGoal {
    // Exact original x,y,z,qx,qy,qz,qw; never voxel/projected coordinates.
    std::array<double, 7> values{};
    std::string frame;
    bool finite() const noexcept {
        for (const double value : values) if (!std::isfinite(value)) return false;
        return true;
    }
    bool exactlyEquals(const RawGoal& other) const noexcept {
        if (frame != other.frame) return false;
        for (std::size_t i = 0; i < values.size(); ++i) {
            // Per-scalar compare avoids Eigen/struct padding and rejects even
            // changed signed-zero representations; no tolerance/normalization.
            if (std::memcmp(&values[i], &other.values[i], sizeof(double)) != 0) return false;
        }
        return true;
    }
};

struct Decision {
    std::int64_t stamp_ns{0};
    bool new_identity{false};
    bool supported{false};
};

// Owned only by the opted-in SingleThreadedExecutor's mission callbacks.
// Retained header.stamp is a command-creation identity, NOT each retransmit's
// send time. Same-clock new intents use the next nanosecond to stay distinct.
class Identity {
public:
    static constexpr std::int64_t kMaxStampNs =
            static_cast<std::int64_t>(std::numeric_limits<std::int32_t>::max()) *
            1000000000LL + 999999999LL;

    Decision publication(const bool new_intent, const RawGoal& raw,
                         const std::int64_t now_ns) {
        if (!raw.finite() || raw.frame.empty()) return unsupported();
        if (!new_intent && have_current_ && raw.exactlyEquals(current_raw_)) {
            return {current_stamp_ns_, false, true};
        }
        if (now_ns <= 0 || now_ns > kMaxStampNs || last_issued_ns_ == kMaxStampNs) {
            return unsupported();
        }
        const auto next = std::max(now_ns, last_issued_ns_ + 1);
        current_raw_ = raw;
        current_stamp_ns_ = next;
        last_issued_ns_ = next;
        have_current_ = true;
        return {next, true, true};
    }

private:
    Decision unsupported() noexcept {
        // Preserve publication/admission instead of losing a command. A zero
        // stamp explicitly disables receiver coalescing for this message.
        have_current_ = false;
        return {};
    }
    bool have_current_{false};
    RawGoal current_raw_;
    std::int64_t current_stamp_ns_{0};
    std::int64_t last_issued_ns_{0};
};

}  // namespace mission_planner::goal_retransmit
