import os
import subprocess

from native_campaign import (
    nearest_rank_percentile,
    process_tree_pids,
    read_cpu_usage_usec,
)


def test_read_cpu_usage_usec(tmp_path):
    (tmp_path / "cpu.stat").write_text(
        "usage_usec 123456\nuser_usec 120000\nsystem_usec 3456\n"
    )
    assert read_cpu_usage_usec(str(tmp_path)) == 123456


def test_nearest_rank_percentile():
    values = [0.1, 0.4, 0.2, 0.3]
    assert nearest_rank_percentile(values, 0.5) == 0.2
    assert nearest_rank_percentile(values, 0.95) == 0.4
    assert nearest_rank_percentile([], 0.95) is None


def test_process_tree_includes_child():
    child = subprocess.Popen(["sleep", "30"])
    try:
        assert child.pid in process_tree_pids(os.getpid())
    finally:
        child.terminate()
        child.wait(timeout=5)
