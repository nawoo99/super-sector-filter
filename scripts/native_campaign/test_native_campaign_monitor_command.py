import importlib.util
import shlex
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("native_campaign.py")
SPEC = importlib.util.spec_from_file_location("native_campaign", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_blind_corner_supplement_is_a_separate_registered_family():
    expected = tuple(f"occ_bw_r{tier}" for tier in range(1, 6))
    pilot = tuple(f"occ_b_r{tier}" for tier in range(1, 6))
    controlled_pilot = tuple(f"occ_bc_r{tier}" for tier in range(1, 6))

    assert MODULE.STATIC_BLIND_CORNER_SUPPLEMENT_MAPS == expected
    assert MODULE.STATIC_BLIND_CORNER_SUPPLEMENT_PILOT_MAPS == pilot
    assert MODULE.STATIC_BLIND_CORNER_CONTROLLED_PILOT_MAPS == controlled_pilot
    assert set(expected).issubset(MODULE.VALID_MAPS)
    assert set(pilot).issubset(MODULE.VALID_MAPS)
    assert set(controlled_pilot).issubset(MODULE.VALID_MAPS)
    assert not set(expected).intersection(MODULE.STATIC_OCCLUSION_CHANNEL_MAPS)


def test_angular_blind_turn_calibration_is_separate_and_uses_90deg_route():
    expected = tuple(f"abt_cal_s{severity}" for severity in range(1, 6))

    assert MODULE.STATIC_ANGULAR_BLIND_TURN_CALIBRATION_MAPS == expected
    assert set(expected).issubset(MODULE.VALID_MAPS)
    assert not set(expected).intersection(
        MODULE.STATIC_BLIND_CORNER_SUPPLEMENT_MAPS
    )
    assert MODULE.TURN90_WPS.split(";")[:3] == [
        "24,0", "24,24", "-24,24"
    ]
    assert MODULE.STATIC_ANGULAR_BLIND_TURN_HAZARD_RADII_M == {
        "abt_cal_s1": 1.10,
        "abt_cal_s2": 1.20,
        "abt_cal_s3": 1.30,
        "abt_cal_s4": 1.40,
        "abt_cal_s5": 1.50,
    }


def test_isolated_angular_blind_turn_is_a_separate_first_turn_family():
    expected = tuple(f"abt2_cal_t{tier}" for tier in range(1, 6))

    assert MODULE.STATIC_ISOLATED_ANGULAR_BLIND_TURN_CALIBRATION_MAPS == expected
    assert set(expected).issubset(MODULE.VALID_MAPS)
    assert not set(expected).intersection(
        MODULE.STATIC_ANGULAR_BLIND_TURN_CALIBRATION_MAPS
    )
    assert MODULE.TURN90_ISOLATED_WPS == "24,24;0,24"
    assert MODULE.TURN90_ISOLATED_TIMEOUT == 90.0
    assert set(MODULE.STATIC_ISOLATED_ANGULAR_BLIND_TURN_PROBES) == set(expected)
    assert all(
        probe[2] == 0.12
        for probe in MODULE.STATIC_ISOLATED_ANGULAR_BLIND_TURN_PROBES.values()
    )


def test_monitor_options_precede_positional_delimiter():
    pcd = "/tmp/seed map.pcd"
    command = MODULE.build_loop_monitor_command(
        "-24,24;24,-24",
        1.5,
        120,
        "/tmp/result.json",
        f" --static-pcd '{pcd}'",
    )

    tokens = shlex.split(command)
    delimiter = tokens.index("--")

    assert tokens.index("--static-pcd") < delimiter
    assert tokens[tokens.index("--static-pcd") + 1] == pcd
    assert tokens[delimiter + 1] == "-24,24;24,-24"


def test_speed_options_precede_positional_delimiter():
    command = MODULE.build_loop_monitor_command(
        "24,24;-24,-24",
        1.5,
        120,
        "/tmp/result.json",
        " --speed-limit-mps 7 --speed-tolerance-mps 0.01",
    )

    tokens = shlex.split(command)
    delimiter = tokens.index("--")

    assert tokens.index("--speed-limit-mps") < delimiter
    assert tokens[tokens.index("--speed-limit-mps") + 1] == "7"
    assert tokens.index("--speed-tolerance-mps") < delimiter


def test_super_config_max_velocity_parses_boundary():
    original = MODULE.SUPER_CONFIG_DIR
    try:
        with tempfile.TemporaryDirectory() as directory:
            MODULE.SUPER_CONFIG_DIR = directory
            Path(directory, "profile.yaml").write_text(
                "traj_opt:\n  boundary:\n    max_vel: 7.0 # m/s\n"
            )
            assert MODULE.super_config_max_velocity("profile.yaml") == 7.0
    finally:
        MODULE.SUPER_CONFIG_DIR = original


def test_wait_for_new_perf_log_generation():
    original = MODULE.PERF_LOG
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "performance.csv")
            MODULE.PERF_LOG = str(path)
            path.write_text("PointCloudNumber, Total\n1, 0.1\n")
            previous = MODULE.perf_log_signature()

            path.write_text("PointCloudNumber, Total\n2, 0.2\n3, 0.3\n")

            assert MODULE.wait_for_perf_log_generation(
                previous, timeout_s=0.1, poll_s=0.001
            )
    finally:
        MODULE.PERF_LOG = original


def test_unchanged_perf_log_is_not_a_new_generation():
    original = MODULE.PERF_LOG
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "performance.csv")
            MODULE.PERF_LOG = str(path)
            path.write_text("PointCloudNumber, Total\n1, 0.1\n")
            previous = MODULE.perf_log_signature()

            assert not MODULE.wait_for_perf_log_generation(
                previous, timeout_s=0.01, poll_s=0.001
            )
    finally:
        MODULE.PERF_LOG = original


def test_slice_perf_uses_attempt_snapshot():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory, "performance.csv")
        path.write_text(
            "PointCloudNumber, Total, Raycast, Update_cache, Inflation\n"
            "10, 0.010, 0.003, 0.004, 0.001\n"
            "30, 0.030, 0.009, 0.012, 0.003\n"
        )

        result = MODULE.slice_perf(0, 2, str(path))

        assert result["pts_mean"] == 20
        assert result["total_ms_mean"] == 20


def test_slice_perf_derives_map_payload_throughput():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory, "performance.csv")
        path.write_text(
            "PointCloudNumber, Total, PointCloudPayloadBytes, PointCloudPointStep\n"
            "10, 0.010, 320, 32\n"
            "20, 0.020, 400, 20\n"
        )

        result = MODULE.slice_perf(0, 2, str(path), duration_s=2.0)

        assert result["map_perf_frames"] == 2
        assert result["map_frames_s"] == 1
        assert result["map_points_s"] == 15
        assert result["map_payload_bytes_mean"] == 360
        assert result["map_payload_bytes_total"] == 720
        assert result["map_payload_mib_s"] == 360 / (1024 * 1024)
        assert result["map_payload_mbps"] == 720 * 8 / 2 / 1e6
        assert result["map_point_step_mean"] == 26
