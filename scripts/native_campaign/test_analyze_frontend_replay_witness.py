from __future__ import annotations

import copy

from analyze_frontend_replay_witness import analyze


def witness(mode: str) -> dict:
    cloud = {
        "frames": 10,
        "points": 1000,
        "hazard_frames": 10,
        "hazard_points": 100,
        "conflict_frames": 10,
        "conflict_points": 20,
        "max_conflict_points_per_frame": 2,
    }
    return {
        "schema": "frontend-replay-witness-v1",
        "mode": mode,
        "replay_position_xyz_m": [24.0, 23.5, 1.5],
        "replay_yaw_deg": 90.0,
        "replay_velocity_xyz_mps": [0.0, 7.0, 0.0],
        "trajectory_end_xyz_m": [16.2, 24.4, 1.5],
        "trajectory_duration_s": 1.2,
        "risk_horizon_s": 1.0,
        "trajectory_generation": 1,
        "conflict_clearance_m": 0.2,
        "hazard_xy_radius_m": [16.2, 24.4, 1.25],
        "raw": copy.deepcopy(cloud),
        "filtered": copy.deepcopy(cloud),
        "verdict_messages": 6,
        "future_verdict_messages": 6,
        "occupied_verdicts": 6,
        "fresh_occupied_verdicts": 6,
        "max_consecutive_fresh_occupied": 6,
        "last_verdict_generation": 1,
        "last_verdict_status": 6,
        "last_verdict_source_cloud_age_s": 0.01,
        "last_verdict_minimum_distance_m": 0.18,
    }


def test_gate_passes_only_with_visible_raw_removed_sector_and_fresh_risk() -> None:
    sector = witness("sector")
    sector["filtered"]["hazard_points"] = 0
    sector["filtered"]["conflict_points"] = 0
    result = analyze(sector, witness("adaptive"))
    assert result["decision"] == "PASS"
    assert not result["failure_reasons"]


def test_gate_fails_when_adaptive_has_no_consecutive_occupied() -> None:
    sector = witness("sector")
    sector["filtered"]["hazard_points"] = 0
    sector["filtered"]["conflict_points"] = 0
    adaptive = witness("adaptive")
    adaptive["fresh_occupied_verdicts"] = 1
    adaptive["max_consecutive_fresh_occupied"] = 1
    result = analyze(sector, adaptive)
    assert result["decision"] == "FAIL"
    assert "adaptive_two_consecutive_fresh_occupied" in result["failure_reasons"]


def test_gate_fails_when_replay_contract_differs() -> None:
    sector = witness("sector")
    sector["filtered"]["hazard_points"] = 0
    sector["filtered"]["conflict_points"] = 0
    adaptive = witness("adaptive")
    adaptive["replay_yaw_deg"] = 89.0
    result = analyze(sector, adaptive)
    assert result["decision"] == "FAIL"
    assert "identical_replay_contract" in result["failure_reasons"]
