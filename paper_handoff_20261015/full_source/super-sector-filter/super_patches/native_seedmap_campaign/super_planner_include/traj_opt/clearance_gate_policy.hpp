#pragma once

#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

namespace traj_opt::clearance_gate_policy {

inline bool parseEnabled(const char* value) {
    if (value == nullptr || *value == '\0' || std::strcmp(value, "0") == 0) return false;
    if (std::strcmp(value, "1") == 0) return true;
    throw std::invalid_argument("SUPER_OPT_CLEARANCE_GATE_FIRST must be exactly 0 or 1");
}

// Both optimizer constructors force this parse before solving. A running
// process cannot silently change optimization behavior through environment edits.
inline bool enabled() {
    static const bool value = parseEnabled(std::getenv("SUPER_OPT_CLEARANCE_GATE_FIRST"));
    return value;
}

enum class Optimizer { Exp, Backup };

// Called once after an evaluation that actually skipped a zero-gate face scan,
// never inside the quadrature loop. Only the first occurrence emits a marker.
template<Optimizer optimizer>
inline void reportSkipOnce() {
    static std::atomic<bool> reported{false};
    if (reported.load(std::memory_order_relaxed)) return;
    bool expected = false;
    if (reported.compare_exchange_strong(expected, true, std::memory_order_relaxed)) {
        std::fprintf(stderr, "[OPT_CLEARANCE_GATE_SKIP] optimizer=%s gate=0\n",
                     optimizer == Optimizer::Exp ? "exp" : "backup");
    }
}

}  // namespace traj_opt::clearance_gate_policy
