import importlib.util
import shlex
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("native_campaign.py")
SPEC = importlib.util.spec_from_file_location("native_campaign", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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
