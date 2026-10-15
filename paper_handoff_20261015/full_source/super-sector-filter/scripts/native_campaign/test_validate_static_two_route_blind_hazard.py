from validate_static_two_route_blind_hazard import validate


def test_preregistered_two_route_structure_gate_passes():
    result = validate()

    assert result["status"] == "PASS", result["errors"]
    assert result["inflated_upper_route_exists"] is True
    assert result["inflated_lower_branch_closed"] is True
    assert result["direct_lower_route_body_clearance_m"] < 0.0
    assert result["decision_visible_hazard_samples"] >= 20
    assert result["decision_visible_samples_inside_sector"] == 0
    assert min(result["station_geometric_support_points"].values()) >= 10
