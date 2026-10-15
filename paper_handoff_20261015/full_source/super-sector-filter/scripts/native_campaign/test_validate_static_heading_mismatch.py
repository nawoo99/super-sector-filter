from validate_static_heading_mismatch import validate


def test_static_heading_mismatch_structure_gate_passes():
    result = validate()

    assert result["status"] == "PASS", result["errors"]
    assert result["inflated_bypass_exists"] is True
    assert result["direct_route_body_clearance_m"] < 0.0
    assert result["raw_visible_hazard_samples"] >= 20
    assert result["body_sector_visible_samples"] == 0
    assert result["velocity_sector_visible_samples"] >= 20
