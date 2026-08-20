import importlib.util
import shlex
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
