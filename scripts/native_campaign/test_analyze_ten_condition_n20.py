import copy

import analyze_ten_condition_n20 as analyzer


def row(map_name, run, mode, *, contact=False):
    phase = 0.2 * ((run - 1) % 10)
    return {
        "map": map_name,
        "run": str(run),
        "mode": mode,
        "success": "True",
        "safety_collisions": "1" if contact else "0",
        "run_valid": "True",
        "first_attempt_success": "True",
        "attempt_count": "1",
        "retry_count": "0",
        "resource_valid": "True",
        "speed_limit_valid": "True",
        "static_pcd_enabled": "True",
        "oom_kill_delta": "0",
        "infrastructure_failure": "False",
        "mission_time_s": "10",
        "static_pcd_clearance_m": "-0.1" if contact else "0.5",
        "planner_ingress_payload_mib_s": "10" if mode == "full" else "3",
        "total_ms_mean": "30" if mode == "full" else "20",
        "algorithm_cpu_cores_mean": "1",
        "end_to_end_cpu_cores_mean": "1" if mode == "full" else "0.8",
        "end_to_end_cpu_core_s": "10" if mode == "full" else "8",
        "sensor_dropout_enabled": "True",
        "sensor_dropout_phase_env_override": "True",
        "sensor_dropout_expected_phase_s": str(phase),
        "sensor_dropout_phase_s": str(phase),
        "sensor_dropout_warmup_s": "1",
        "sensor_dropout_period_s": "2",
        "sensor_dropout_duration_s": "0.5",
        "sensor_rendered_frames": "100",
        "sensor_delivered_frames": "75",
        "sensor_dropped_frames": "25",
        "sensor_dropout_bursts": "5",
        "sensor_dropout_max_consecutive_dropped": "5",
        "sensor_dropout_max_delivered_gap_s": "0.6",
        "sensor_hz": "10",
    }


def matrices():
    normal = [
        row(f"seed{seed}", run, mode)
        for seed in range(1, 11)
        for run in range(1, 11)
        for mode in analyzer.MODES
    ]
    legacy = [
        row(maps[0], run, mode, contact=(mode == "sector"))
        for maps in analyzer.LEGACY_STRESS_CONDITIONS.values()
        for run in range(1, 21)
        for mode in analyzer.MODES
    ]
    extension = [
        row(maps[0], run, mode, contact=(mode == "sector"))
        for maps in analyzer.EXTENSION_STRESS_CONDITIONS.values()
        for run in range(1, 21)
        for mode in analyzer.MODES
    ]
    return normal, legacy, extension


def test_complete_result_passes():
    normal, legacy, extension = matrices()
    result = analyzer.analyze(
        normal, {"passed": True}, legacy, extension,
        {"decision": "EIGHT_CONDITION_N20_COMPLETE"},
    )
    assert result["decision"] == "TEN_CONDITION_N20_COMPLETE"
    assert result["extension_decision"] == "C4_C5_EXTENSION_OBSERVED"
    assert result["row_accounting"]["paper_table_rows"] == 600
    assert result["groups"]["stress_C4_C5"][
        "paired_adaptive_vs_sector"
    ]["sector_unsafe_adaptive_safe"] == 40
    assert all(
        condition["modes"][mode]["runs"] == 20
        for condition in result["conditions"].values()
        for mode in analyzer.MODES
    )


def test_invalid_extension_and_changed_source_hash_fail():
    normal, legacy, extension = matrices()
    damaged = copy.deepcopy(extension)
    damaged[0]["attempt_count"] = "2"
    result = analyzer.analyze(
        normal, {"passed": True}, legacy, damaged,
        {"decision": "EIGHT_CONDITION_N20_COMPLETE"},
        source_hashes_valid=False,
    )
    assert result["decision"] == "TEN_CONDITION_N20_INCOMPLETE"
    assert result["extension_decision"] == "C4_C5_EXTENSION_FAILED"
    assert not result["checks"]["frozen_source_hashes_match"]
