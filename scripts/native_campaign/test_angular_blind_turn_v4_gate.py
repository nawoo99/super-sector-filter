from __future__ import annotations

import json
from pathlib import Path

from analyze_angular_blind_turn_v4_liveness import analyze
from validate_angular_blind_turn_v4_gate import in_forward_sector


def test_forward_sector_geometry() -> None:
    assert in_forward_sector((0.0, 5.0), (10.0, 0.0), 180.0, 45.0, 15.0)
    assert not in_forward_sector((10.0, 5.0), (10.0, 0.0), 180.0, 45.0, 15.0)
    assert not in_forward_sector((-10.0, 0.0), (10.0, 0.0), 180.0, 45.0, 15.0)


def witness(position: tuple[float, float, float], points: int = 1500) -> dict:
    return {
        "schema": "frontend-replay-witness-v1",
        "mode": "sector",
        "replay_position_xyz_m": list(position),
        "replay_yaw_deg": 180.0,
        "replay_velocity_xyz_mps": [-7.0, 0.0, 0.0],
        "raw": {"frames": 15},
        "filtered": {"frames": 15, "points": points},
    }


def test_liveness_analyzer_is_fail_closed(tmp_path: Path) -> None:
    paths = []
    for name, position in (
        ("x20", (20.0, 26.3, 1.2)),
        ("x12", (12.0, 26.3, 1.2)),
        ("x4", (4.0, 26.3, 1.2)),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(witness(position)))
        paths.append(path)
    assert analyze(paths)["status"] == "PASS"
    bad = witness((4.0, 26.3, 1.2), points=0)
    paths[-1].write_text(json.dumps(bad))
    result = analyze(paths)
    assert result["status"] == "FAIL"
    assert any("insufficient" in error for error in result["errors"])
