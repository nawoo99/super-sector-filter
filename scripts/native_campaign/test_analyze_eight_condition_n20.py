import copy

import analyze_eight_condition_n20 as analyzer


def row(map_name, run, mode, *, contact=False):
    phase = 0.2 * ((run - 1) % 10)
    value = {
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
    return value


def matrices():
    normal = [
        row(f"seed{seed}", run, mode)
        for seed in range(1, 11)
        for run in range(1, 11)
        for mode in analyzer.MODES
    ]
    stress = []
    for maps in analyzer.STRESS_CONDITIONS.values():
        for run in range(1, 21):
            for mode in analyzer.MODES:
                stress.append(row(maps[0], run, mode, contact=(mode == "sector")))
    block1 = [copy.deepcopy(value) for value in stress if int(value["run"]) <= 10]
    return normal, stress, block1


def test_complete_result_passes():
    normal, stress, block1 = matrices()
    result = analyzer.analyze(
        normal, {"passed": True}, stress, block1,
        {"decision": "CONFIRMATORY_TRANSFER_OBSERVED"},
    )
    assert result["decision"] == "EIGHT_CONDITION_N20_COMPLETE"
    assert result["stress_replication_decision"] == "STRESS_REPLICATION_OBSERVED"
    assert result["row_accounting"]["paper_table_rows"] == 480
    assert result["groups"]["stress_C1_C3_block2"][
        "paired_adaptive_vs_sector"
    ]["sector_unsafe_adaptive_safe"] == 30
    assert all(
        condition["modes"][mode]["runs"] == 20
        for condition in result["conditions"].values()
        for mode in analyzer.MODES
    )


def test_changed_block1_and_invalid_block2_fail():
    normal, stress, block1 = matrices()
    stress[0]["mission_time_s"] = "11"
    block2_full = next(
        value for value in stress
        if int(value["run"]) == 11 and value["mode"] == "full"
    )
    block2_full["attempt_count"] = "2"
    result = analyzer.analyze(
        normal, {"passed": True}, stress, block1,
        {"decision": "CONFIRMATORY_TRANSFER_OBSERVED"},
    )
    assert result["decision"] == "EIGHT_CONDITION_N20_INCOMPLETE"
    assert not result["checks"]["block1_rows_copied_exactly"]
    assert result["stress_replication_decision"] == "STRESS_REPLICATION_FAILED"
