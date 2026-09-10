from validate_static_burst_dropout_confirmation import validate


def test_all_preregistered_held_out_structure_gates_pass():
    result = validate()

    assert result["status"] == "PASS", result["errors"]
    assert set(result["variants"]) == {
        "c1_mirror", "c2_wide_offset", "c3_near_short"
    }
    for variant in result["variants"].values():
        assert variant["inflated_bypass_exists"] is True
        assert variant["direct_route_body_clearance_m"] < 0.0
        assert variant["body_sector_visible_samples"] == 0
        assert variant["velocity_sector_visible_samples"] >= 20
