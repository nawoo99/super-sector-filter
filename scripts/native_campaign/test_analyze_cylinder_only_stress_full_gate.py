import csv
from pathlib import Path

from analyze_cylinder_only_stress_full_gate import MAPS, analyze


FIELDS = [
    "map", "run", "mode", "success", "waypoints_reached",
    "safety_collisions", "static_pcd_collisions", "static_pcd_clearance_m",
    "speed_limit_valid", "run_valid", "resource_valid",
    "infrastructure_failure", "attempt_count", "retry_count",
]


def write_rows(path: Path, failed_map=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for map_name in MAPS:
            success = map_name != failed_map
            writer.writerow({
                "map": map_name,
                "run": 1,
                "mode": "full",
                "success": success,
                "waypoints_reached": 5 if success else 0,
                "safety_collisions": 0,
                "static_pcd_collisions": 0,
                "static_pcd_clearance_m": 0.3,
                "speed_limit_valid": True,
                "run_valid": True,
                "resource_valid": True,
                "infrastructure_failure": False,
                "attempt_count": 1,
                "retry_count": 0,
            })


def test_passes_only_when_all_five_full_rows_complete(tmp_path):
    raw = tmp_path / "pass.csv"
    write_rows(raw)

    result = analyze(raw)

    assert result["decision"] == "PROCEED_TO_PAIRED_THREE_MODE_PILOT"
    assert all(result["checks"].values())


def test_valid_contact_free_timeout_fails_completion_gate(tmp_path):
    raw = tmp_path / "fail.csv"
    write_rows(raw, failed_map="stress_cyl_r4")

    result = analyze(raw)

    assert result["decision"] == (
        "STOP_PAIRED_CAMPAIGN_FULL_FEASIBILITY_GATE_FAILED"
    )
    assert result["checks"]["all_rows_quality_valid"]
    assert result["checks"]["all_rows_contact_free"]
    assert not result["checks"]["all_rows_complete"]
