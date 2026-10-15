#include <fsm/stop_margin_certificate.hpp>

#include <cassert>
#include <cstddef>
#include <iostream>
#include <vector>

namespace margin = super_planner::stop_margin;

enum class Status { Safe, Margin, Occupied, Unknown, Outside, Invalid, Timeout, Version };
struct Result {
    Status status{Status::Invalid};
    bool hard_checks_complete{false};
    std::size_t visited{0};
};

// Deterministic query stream for the production policy/proof helper. Physical
// and unknown predicates are intentionally supplied by the caller, as they
// are in validatePositionTrajectory; this test does not redefine either.
Result validate(const std::vector<Status>& queries,
                const margin::ValidationPolicy policy,
                const Status final_checks = Status::Safe,
                const bool final_escape_margin = false) {
    margin::Traversal traversal(policy, queries.size());
    Result result;
    for (const auto status : queries) {
        traversal.beginQuery();
        ++result.visited;
        if (status == Status::Safe) continue;
        if (status == Status::Margin && traversal.deferSoftMargin()) continue;
        result.status = status;
        return result;
    }
    if (final_escape_margin && !traversal.deferSoftMargin()) {
        result.status = Status::Margin;
        return result;
    }
    if (final_checks != Status::Safe) {
        result.status = final_checks;
        return result;
    }
    result.hard_checks_complete = traversal.completedAfterFinalChecks();
    result.status = traversal.deferredSoftMargin() ? Status::Margin : Status::Safe;
    return result;
}

bool accepted(const Result& result) {
    return margin::admissibleStop(result.status == Status::Safe,
                                 result.status == Status::Margin,
                                 result.hard_checks_complete);
}

int main() {
    const auto immediate = margin::ValidationPolicy::RejectImmediately;
    const auto entire = margin::ValidationPolicy::DeferSoftMarginUntilHardChecksComplete;

    // Former bug: an early margin was admitted without visiting the later
    // physical collision or configured-unknown rejection.
    for (const auto hard : {Status::Occupied, Status::Unknown, Status::Outside,
                            Status::Invalid, Status::Timeout, Status::Version}) {
        auto result = validate({Status::Margin, Status::Safe, hard, Status::Safe}, entire);
        assert(result.status == hard && result.visited == 3);
        assert(!result.hard_checks_complete && !accepted(result));
    }
    auto result = validate({Status::Margin, Status::Safe, Status::Margin, Status::Safe}, entire);
    assert(result.status == Status::Margin && result.visited == 4);
    assert(result.hard_checks_complete && accepted(result));
    result = validate({Status::Safe, Status::Safe}, entire);
    assert(result.status == Status::Safe && result.hard_checks_complete && accepted(result));

    // Primary candidate policy still returns the first soft-margin failure.
    result = validate({Status::Margin, Status::Occupied}, immediate);
    assert(result.status == Status::Margin && result.visited == 1);
    assert(!result.hard_checks_complete && !accepted(result));
    assert(!margin::admissibleStop(false, true, false));
    assert(!margin::admissibleStop(false, false, true));

    for (const auto final_failure : {Status::Timeout, Status::Version}) {
        result = validate({Status::Margin, Status::Safe}, entire, final_failure);
        assert(result.visited == 2 && result.status == final_failure);
        assert(!result.hard_checks_complete && !accepted(result));
    }
    result = validate({Status::Safe, Status::Safe}, entire, Status::Safe, true);
    assert(result.status == Status::Margin && result.hard_checks_complete && accepted(result));
    result = validate({Status::Safe, Status::Safe}, immediate, Status::Safe, true);
    assert(result.status == Status::Margin && !result.hard_checks_complete && !accepted(result));

    margin::Traversal incomplete(entire, 2);
    incomplete.beginQuery();
    assert(incomplete.deferSoftMargin());
    assert(!incomplete.completedAfterFinalChecks());
    incomplete.beginQuery();
    assert(incomplete.completedAfterFinalChecks());
    incomplete.beginQuery();
    assert(!incomplete.completedAfterFinalChecks());
    assert(!margin::Traversal(entire, 0).completedAfterFinalChecks());
    assert(margin::kViabilityPolicyRevision == 2);

    std::cout << "stop_margin_certificate_test: PASS\n";
}
