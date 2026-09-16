#pragma once

#include <cstring>
#include <stdexcept>

namespace perfect_drone::static_pc_durable {

// Plan A changes only /global_pc offered QoS. It must not be silently combined
// with an unvalidated publication-timing optimization. Unset/0 is legacy.
inline bool parseEnabled(const char* setting, const int poll_ms,
                         const bool two_phase_enabled) {
    if (!setting || std::strcmp(setting, "0") == 0) return false;
    if (std::strcmp(setting, "1") != 0) {
        throw std::invalid_argument("SUPER_STATIC_PC_DURABLE must be 0 or 1");
    }
    if (poll_ms != 1 || two_phase_enabled) {
        throw std::invalid_argument(
                "SUPER_STATIC_PC_DURABLE=1 requires legacy static poll1ms and two-phase disabled");
    }
    return true;
}

}  // namespace perfect_drone::static_pc_durable
