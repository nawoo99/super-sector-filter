from __future__ import annotations

from pathlib import Path

from analyze_angular_blind_turn_v3_gate import analyze
import analyze_angular_blind_turn_calibration as base


FIELDS = [
    "map", "run", "mode", "success", "safety_collisions",
    "static_pcd_collisions", "static_hazard_collisions", "run_valid",
    "resource_valid", "speed_limit_valid", "perf_window_valid",
    "cgroup_cpu_accounting", "cgroup_accounting_error",
    "infrastructure_failure", "resource_guard_abort_count", "oom_kill_delta",
    "attempt_count", "retry_count", "first_attempt_success",
    "waypoints_reached", "frontend_risk_brake_events", "frontend_risk_enforced",
    "filter_static_probe_input_seen", "filter_static_probe_first_center_in_sector",
]


def row(mode: str, success: bool) -> dict[str, str]:
    value = {field: "" for field in FIELDS}
    value.update(
        {
            "map": "abt3_gate_open", "run": "1", "mode": mode,
            "success": str(success), "safety_collisions": "0",
            "static_pcd_collisions": "0", "static_hazard_collisions": "0",
            "run_valid": "True", "resource_valid": "True",
            "speed_limit_valid": "True", "perf_window_valid": "True",
            "cgroup_cpu_accounting": "True", "infrastructure_failure": "False",
            "resource_guard_abort_count": "0", "oom_kill_delta": "0",
            "attempt_count": "1", "retry_count": "0",
            "first_attempt_success": "True", "waypoints_reached": "1",
            "filter_static_probe_input_seen": "True",
            "filter_static_probe_first_center_in_sector": "False",
        }
    )
    return value


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    base.write_csv(path, rows, FIELDS)


def test_full_gate_passes_one_safe_quality_row(tmp_path: Path) -> None:
    raw = tmp_path / "full.csv"
    write_rows(raw, [row("full", True)])
    assert analyze(raw, "full")["decision"] == "PROCEED_TO_PAIRED_MECHANISM_SMOKE"


def test_comparison_requires_sector_degradation_and_adaptive_brake(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "comparison.csv"
    sector = row("sector", False)
    adaptive = row("adaptive", True)
    adaptive["frontend_risk_brake_events"] = "1"
    adaptive["frontend_risk_enforced"] = "1"
    write_rows(raw, [sector, adaptive])
    assert analyze(raw, "comparison")["decision"] == "PROCEED_TO_LARGER_CALIBRATION"


def test_comparison_fails_without_exact_adaptive_brake(tmp_path: Path) -> None:
    raw = tmp_path / "comparison.csv"
    write_rows(raw, [row("sector", False), row("adaptive", True)])
    result = analyze(raw, "comparison")
    assert result["decision"] == "STOP_PAIRED_MECHANISM_GATE_FAILED"
    assert not result["checks"]["adaptive_exact_fresh_frontend_risk_brake"]
