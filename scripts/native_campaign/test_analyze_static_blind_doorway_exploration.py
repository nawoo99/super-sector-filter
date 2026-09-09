from analyze_static_blind_doorway_exploration import analyze


def candidate(name, degraded=False, exact=0):
    return {
        "candidate": name,
        "clear_sector_committed_conflict": True,
        "hazard_sector_degraded": degraded,
        "adaptive_shadow_hazard_matched_exact_occupied": exact,
    }


def test_stops_when_component_passes_but_sector_never_degrades():
    result = analyze(
        [candidate("c1"), candidate("c2"), candidate("c3")],
        {"decision": "PASS"},
    )
    assert result["decision"] == "STOP_C1_C3_NO_STATIC_SAFETY_SEPARATION"
    assert not result["checks"]["at_least_one_hazard_sector_degraded"]


def test_proceeds_only_with_degradation_and_hazard_matched_exact_pair():
    result = analyze(
        [candidate("c1", degraded=True, exact=2)],
        {"decision": "PASS"},
    )
    assert result["decision"] == "PROCEED_TO_PREREGISTRATION"
