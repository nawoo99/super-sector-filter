import csv
import importlib.util
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "analyze_static_blind_corner_supplement.py"
)
SPEC = importlib.util.spec_from_file_location("blind_analyzer", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_complete_safe_fixture_passes_quality_but_not_separation():
    rows = []
    for map_name in MODULE.MAPS:
        for run in MODULE.RUNS:
            for mode in MODULE.MODES:
                filtered = mode != "full"
                adaptive = mode == "adaptive"
                rows.append(
                    {
                        "map": map_name,
                        "run": run,
                        "mode": mode,
                        "success": True,
                        "safety_collisions": 0,
                        "run_valid": True,
                        "resource_valid": True,
                        "speed_limit_valid": True,
                        "perf_window_valid": True,
                        "cgroup_cpu_accounting": True,
                        "cgroup_accounting_error": "",
                        "infrastructure_failure": False,
                        "attempt_count": 1,
                        "retry_count": 0,
                        "resource_guard_abort_count": 0,
                        "oom_kill_delta": 0,
                        "static_pcd_clearance_m": 0.2,
                        "static_hazard_enabled": True,
                        "static_hazard_center_x": 18.4,
                        "static_hazard_center_y": 24.0,
                        "static_hazard_radius_m": 0.95,
                        "static_hazard_height_m": 3.2,
                        "static_hazard_collisions": 0,
                        "static_hazard_min_clearance_m": 0.2,
                        "mission_time_s": 60.0,
                        "filter_static_probe_enabled": filtered,
                        "filter_static_probe_input_seen": filtered,
                        "filter_static_probe_first_point_count": 10 if filtered else 0,
                        "filter_static_probe_first_horizontal_distance_m": (
                            4.0 if filtered else ""
                        ),
                        "filter_static_probe_first_center_in_sector": False,
                        "filter_effective_full_open_transitions": 1 if adaptive else 0,
                        "filter_trajectory_guard_open_transitions": (
                            1 if adaptive else 0
                        ),
                        "planner_ingress_mib_s": 1.0,
                        "map_compute_ms_per_frame": 1.0,
                        "end_to_end_cores_mean": 1.0,
                        "end_to_end_core_s": 60.0,
                        "end_to_end_peak_pss_mib": 100.0,
                    }
                )

    with tempfile.TemporaryDirectory() as directory:
        campaign = Path(directory) / "campaign.csv"
        prefix = Path(directory) / "summary"
        with campaign.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        result = MODULE.analyze(campaign, prefix)

        assert result["quality_valid_rows"] == 150
        assert result["probe_valid_rows"] == 100
        assert result["hazard_metric_valid_rows"] == 150
        assert result["gates"]["validity"]
        assert result["gates"]["protected_modes"]
        assert result["gates"]["physical_delivery"]
        assert not result["gates"]["safety_separation_either_route"]
        assert result["decision"] == "SUPPLEMENT_COMPLETE_NO_SAFETY_SEPARATION"
