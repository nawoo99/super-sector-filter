from validate_cylinder_only_stress import validate


def test_cylinder_only_stress_structure_gate_passes():
    result = validate()

    assert result["decision"] == "PASS", result["errors"]
    assert result["checks"] == {
        "five_final_maps": True,
        "only_cylinders": True,
        "no_sensor_fault": True,
        "no_dynamic_obstacles": True,
        "fixed_count": True,
        "direct_path_blocked": True,
        "bypass_body_and_margin_feasible": True,
        "fixed_sector_excludes_conflict": True,
    }
    assert [row["map"] for row in result["maps"][1:]] == [
        f"stress_cyl_r{tier}" for tier in range(1, 6)
    ]
    assert all(row["cylinder_count"] == 410 for row in result["maps"])
    assert all(row["minimum_all_surface_gap_m"] == 0.2
               for row in result["maps"])

