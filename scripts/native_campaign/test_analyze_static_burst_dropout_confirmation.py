from analyze_static_burst_dropout_confirmation import (
    MAPS,
    MODES,
    analyze,
    exact_mcnemar_two_sided,
)


def row(map_name, run, mode, *, safe=True):
    phase = 0.2 * (run - 1)
    return {
        "map": map_name,
        "run": str(run),
        "mode": mode,
        "success": "True",
        "safety_collisions": "0" if safe else "1",
        "first_attempt_success": "True",
        "attempt_count": "1",
        "retry_count": "0",
        "resource_valid": "True",
        "resource_guard_triggered": "False",
        "speed_limit_valid": "True",
        "static_pcd_enabled": "True",
        "oom_kill_delta": "0",
        "sensor_dropout_enabled": "True",
        "sensor_dropout_phase_env_override": "True",
        "sensor_dropout_expected_phase_s": str(phase),
        "sensor_dropout_phase_s": str(phase),
        "sensor_dropout_warmup_s": "1.0",
        "sensor_dropout_period_s": "2.0",
        "sensor_dropout_duration_s": "0.5",
        "sensor_rendered_frames": "50",
        "sensor_delivered_frames": "40",
        "sensor_dropped_frames": "10",
        "sensor_dropout_bursts": "2",
        "sensor_dropout_max_consecutive_dropped": "5",
        "sensor_dropout_max_delivered_gap_s": "0.60",
        "sensor_hz": "10.0",
        "mission_time_s": "7.0",
        "algorithm_cpu_cores_mean": "0.5" if mode == "full" else "0.4",
        "planner_ingress_payload_mib_s": "2.0",
    }


def gates():
    full = [row(map_name, 1, "full") for map_name in MAPS]
    return full, {"status": "PASS"}, [{"decision": "PASS"}] * 3, {"decision": "PASS"}


def test_exact_mcnemar_ten_to_zero():
    assert exact_mcnemar_two_sided(10, 0) == 0.001953125


def test_confirmatory_transfer_when_every_frozen_condition_passes():
    rows = []
    for map_name in MAPS:
        for run in range(1, 11):
            for mode in MODES:
                rows.append(row(map_name, run, mode, safe=(mode != "sector")))
    result = analyze(rows, *gates())
    assert result["decision"] == "CONFIRMATORY_TRANSFER_OBSERVED"
    assert result["aggregate"]["paired_adaptive_vs_sector"][
        "sector_unsafe_adaptive_safe"
    ] == 30


def test_phase_mismatch_fails_integrity_without_relabeling_result():
    rows = []
    for map_name in MAPS:
        for run in range(1, 11):
            for mode in MODES:
                rows.append(row(map_name, run, mode, safe=(mode != "sector")))
    rows[0]["sensor_dropout_phase_s"] = "0.2"
    result = analyze(rows, *gates())
    assert result["decision"] == "CONFIRMATION_FAILED"
    assert not result["checks"]["all_rows_integrity_valid"]


def test_heterogeneous_sector_separation_is_partial_transfer():
    rows = []
    for map_name in MAPS:
        for run in range(1, 11):
            for mode in MODES:
                sector_safe = mode == "sector" and map_name == MAPS[-1]
                rows.append(row(map_name, run, mode, safe=(mode != "sector" or sector_safe)))
    result = analyze(rows, *gates())
    assert result["decision"] == "PARTIAL_TRANSFER"
    assert not result["checks"]["sector_unsafe_at_least_once_each_map"]


def test_incomplete_matrix_fails_closed_instead_of_crashing():
    result = analyze([row(MAPS[0], 1, "full")], *gates())
    assert result["decision"] == "CONFIRMATION_FAILED"
    assert not result["checks"]["complete_unique_paired_matrix"]
