from analyze_static_heading_mismatch_campaign import (
    analyze,
    exact_mcnemar_two_sided,
)


def row(run, mode, *, safe=True):
    return {
        "map": "shm1_h9_hazard",
        "run": str(run),
        "mode": mode,
        "success": "True",
        "safety_collisions": "0" if safe else "1",
        "first_attempt_success": "True",
        "resource_valid": "True",
        "speed_limit_valid": "True",
        "static_pcd_enabled": "True",
        "mission_time_s": "5",
        "algorithm_cpu_cores_mean": "0.5" if mode == "full" else "0.4",
        "planner_ingress_payload_mib_s": "2.0",
    }


def test_exact_mcnemar_nine_to_zero():
    assert exact_mcnemar_two_sided(9, 0) == 0.00390625


def test_observes_paired_exploratory_separation():
    rows = []
    for run in range(1, 11):
        rows += [
            row(run, "full"),
            row(run, "sector", safe=(run == 3)),
            row(run, "adaptive"),
        ]
    result = analyze(rows, {"decision": "PASS"}, "shm1_h9_hazard", 10)
    assert result["decision"] == "EXPLORATORY_SEPARATION_OBSERVED"
    assert result["modes"]["sector"]["contact_run_count"] == 9
    assert result["paired_adaptive_vs_sector"]["exact_mcnemar_two_sided_p"] == 0.00390625


def test_fails_when_sector_is_also_safe():
    rows = [row(run, mode) for run in range(1, 11) for mode in ("full", "sector", "adaptive")]
    result = analyze(rows, {"decision": "PASS"}, "shm1_h9_hazard", 10)
    assert result["decision"] == "GATE_FAILED"
    assert not result["checks"]["sector_has_safety_degradation"]
