from __future__ import annotations

from pathlib import Path

import analyze_angular_blind_turn_calibration as base
from analyze_angular_blind_turn_v4_flight import analyze


FIELDS = [
    "map", "run", "mode", "success", "safety_collisions",
    "static_pcd_collisions", "static_hazard_collisions", "run_valid",
    "resource_valid", "speed_limit_valid", "perf_window_valid",
    "cgroup_cpu_accounting", "cgroup_accounting_error", "infrastructure_failure",
    "resource_guard_abort_count", "oom_kill_delta", "attempt_count", "retry_count",
    "first_attempt_success", "waypoints_reached", "guard_main_pre_map_stale",
    "frontend_risk_brake_events", "frontend_risk_enforced",
    "filter_static_probe_input_seen", "filter_static_probe_first_center_in_sector",
]


def row(run: int, mode: str, success: bool) -> dict[str, str]:
    value = {field: "" for field in FIELDS}
    value.update(
        {
            "map": "abt4_observed_exit", "run": str(run), "mode": mode,
            "success": str(success), "safety_collisions": "0",
            "static_pcd_collisions": "0", "static_hazard_collisions": "0",
            "run_valid": "True", "resource_valid": "True",
            "speed_limit_valid": "True", "perf_window_valid": "True",
            "cgroup_cpu_accounting": "True", "infrastructure_failure": "False",
            "resource_guard_abort_count": "0", "oom_kill_delta": "0",
            "attempt_count": "1", "retry_count": "0", "first_attempt_success": "True",
            "waypoints_reached": "2" if success else "1",
            "guard_main_pre_map_stale": "0",
            "filter_static_probe_input_seen": "True",
            "filter_static_probe_first_center_in_sector": "False",
        }
    )
    return value


def write(path: Path, rows: list[dict[str, str]]) -> None:
    base.write_csv(path, rows, FIELDS)


def test_full_gate(tmp_path: Path) -> None:
    raw = tmp_path / "full.csv"
    write(raw, [row(1, "full", True)])
    assert analyze(raw, "full")["decision"] == "PROCEED_TO_THREE_MODE_N3"


def test_pilot_passes_only_without_stale_confound(tmp_path: Path) -> None:
    raw = tmp_path / "pilot.csv"
    rows = []
    for run in range(1, 4):
        rows.extend((row(run, "full", True), row(run, "sector", False)))
        adaptive = row(run, "adaptive", True)
        adaptive["frontend_risk_brake_events"] = "1"
        adaptive["frontend_risk_enforced"] = "1"
        rows.append(adaptive)
    write(raw, rows)
    assert analyze(raw, "pilot")["decision"] == "PROCEED_TO_HELD_OUT_MAP_DESIGN"
    rows[1]["guard_main_pre_map_stale"] = "1"
    write(raw, rows)
    result = analyze(raw, "pilot")
    assert result["decision"] == "STOP_V4_THREE_MODE_GATE_FAILED"
    assert not result["checks"]["sector_degradation_has_no_map_stale_confound"]
