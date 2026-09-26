#pragma once

#include <cstddef>
#include <cstdint>

namespace super_planner {
namespace stop_margin {

enum class ValidationPolicy {
    RejectImmediately,
    DeferSoftMarginUntilHardChecksComplete
};

// Revision 2 changes only soft-margin traversal and invalid-state handling.
// It does NOT assert strict known-free space: the caller's explicit unknown
// policy and the map's existing observation predicate remain independent.
constexpr std::uint32_t kViabilityPolicyRevision = 2;

class Traversal {
public:
    Traversal(const ValidationPolicy policy, const std::size_t query_count)
        : policy_(policy), query_count_(query_count) {}

    void beginQuery() noexcept { ++visited_queries_; }

    bool deferSoftMargin() noexcept {
        if (policy_ != ValidationPolicy::DeferSoftMarginUntilHardChecksComplete)
            return false;
        deferred_soft_margin_ = true;
        return true;
    }

    bool deferredSoftMargin() const noexcept { return deferred_soft_margin_; }

    // Invoke only after every query AND the caller's final deadline/map-
    // version checks. An early return, including one after an early soft
    // margin, must leave the result's completion proof false.
    bool completedAfterFinalChecks() const noexcept {
        return query_count_ > 0 && visited_queries_ == query_count_;
    }

private:
    ValidationPolicy policy_;
    std::size_t query_count_;
    std::size_t visited_queries_{0};
    bool deferred_soft_margin_{false};
};

inline bool admissibleStop(const bool safe, const bool soft_margin,
                           const bool hard_checks_complete) noexcept {
    return safe || (soft_margin && hard_checks_complete);
}

}  // namespace stop_margin
}  // namespace super_planner
