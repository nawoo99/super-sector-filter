#include <fsm/stop_margin_certificate.hpp>

// Keep the frozen revision-1 fixture and its assertions unchanged. Reuse it
// as an additive revision-2 consumer test rather than rewriting its evidence.
#define main legacy_demand_replan_policy_test_main
#include "demand_replan_policy_test.cpp"
#undef main

int main() {
    if (legacy_demand_replan_policy_test_main() != 0) return 1;
    try {
        auto p = policy();
        auto e = validEvidence();
        p.viability_policy_revision =
                super_planner::stop_margin::kViabilityPolicyRevision;
        require(dr::decide(p, e).reason == dr::Reason::NEED_VIABILITY_RENEWAL,
                "revision-1 early-margin receipt cannot authorize revision-2 skip");
        e.receipt.policy_revision = p.viability_policy_revision;
        require(dr::decide(p, e).skip(), "matching revision-2 receipt may skip");
        require(dr::decide(policy(), e).reason == dr::Reason::NEED_VIABILITY_RENEWAL,
                "legacy consumer cannot silently accept revision-2 receipt");
        ++e.receipt.policy_revision;
        require(dr::decide(p, e).reason == dr::Reason::NEED_VIABILITY_RENEWAL,
                "unknown future receipt revision fails closed");
        std::cout << "stop_margin_demand_policy_test: PASS\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
