"""Offline observer tests; no ROS initialization or flight launch."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/gapfree_native_loop_monitor.py"
spec = importlib.util.spec_from_file_location("gapfree_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def observe(audit, position, index):
    return audit.observe(position, [0, 0, 0], index * 10000000, index * 10000000, index / 100)


def test_exit_and_reentry_count_two_distinct_episodes():
    audit = monitor.SampledCylinderAudit([[0, 0, .5]])
    for i, x in enumerate([1.0, .6, .6, 10.0, .6, 1.0], 1):
        observe(audit, [x, 0, 1.5], i)
    doc = audit.summary()
    assert doc["contact_episodes"] == 2
    assert doc["contact_samples"] == 3
    assert [event["kind"] for event in doc["events"]] == ["enter", "exit", "enter", "exit"]
    assert doc["audit_valid"] and not doc["swept_collision_check"]


def test_inside_and_top_corner_use_finite_solid_geometry():
    audit = monitor.SampledCylinderAudit([[0, 0, .5]])
    assert observe(audit, [0, 0, 1.5], 1) == pytest.approx(-.2)
    assert observe(audit, [0, 0, 3.3], 2) == pytest.approx(.1)
    assert observe(audit, [.65, 0, 3.15], 3) > 0  # corner distance, not a bounding box
    assert observe(audit, [.5, 0, 3.2], 4) == pytest.approx(0)
    assert audit.contact_episodes == 2  # exact tangency is contact


def test_multiple_cylinders_are_union_episodes():
    audit = monitor.SampledCylinderAudit([[0, 0, .5], [1, 0, .5]])
    observe(audit, [.5, 0, 1.5], 1)
    assert audit.contact_episodes == 1
    assert audit.events[0]["cylinder_indices"] == [0, 1]


def test_invalid_and_out_of_order_samples_are_not_valid_zero_contacts():
    audit = monitor.SampledCylinderAudit([[0, 0, .5]])
    assert not audit.summary()["audit_valid"]
    observe(audit, [2, 0, 1.5], 2)
    observe(audit, [2, 0, 1.5], 1)
    assert observe(audit, [float("nan"), 0, 1.5], 3) is None
    doc = audit.summary()
    assert not doc["audit_valid"]
    assert doc["invalid_samples"] == 1
    assert doc["timestamp_nonmonotonic_count"] == 1
    assert doc["receipt_nonmonotonic_count"] == 1
    json.dumps(doc, allow_nan=False)


def test_crossing_between_clear_samples_is_explicitly_not_swept():
    audit = monitor.SampledCylinderAudit([[0, 0, .5]])
    observe(audit, [-1, 0, 1.5], 1)
    observe(audit, [1, 0, 1.5], 2)
    assert audit.contact_episodes == 0
    assert audit.summary()["swept_collision_check"] is False
    assert audit.summary()["max_pose_step_m"] == 2


@pytest.mark.parametrize("source", [b"value=1\n", b"rclpy.init()\nrclpy.init()\n"])
def test_injection_requires_exactly_one_init(source):
    with pytest.raises(ValueError, match="exactly one"):
        monitor.split_base_source(source, "test.py", hashlib.sha256(source).hexdigest())


def test_changed_base_hash_rejected():
    with pytest.raises(ValueError, match="SHA256"):
        monitor.split_base_source(b"rclpy.init()\n", "test.py")


def test_frozen_base_and_all_five_geometries_load_without_running_ros():
    base = monitor.DEFAULT_BASE
    if not base.exists():
        pytest.skip("Frozen native monitor not installed")
    monitor.split_base_source(base.read_bytes(), str(base))
    for name in monitor.ALLOWED_MAPS:
        path = MODULE_PATH.parents[1] / "pcd/seed_maps" / f"{name}.pcd"
        cylinders, csv_path = monitor.load_cylinders(path)
        assert cylinders.shape == (410, 3) and csv_path.exists()


def test_other_maps_cannot_use_gapfree_geometry_adapter():
    with pytest.raises(ValueError, match="restricted"):
        monitor.load_cylinders("/tmp/seed1.pcd")


def test_wrapper_preserves_native_output_and_writes_complete_sample_audit(tmp_path, monkeypatch):
    """Exercise the actual hook/CSV/finalization with a tiny fake ROS module."""
    pcd = tmp_path / "gapfree_d1_m01.pcd"
    cylinders = tmp_path / "gapfree_d1_m01_cylinders.csv"
    out = tmp_path / "gapfree_d1_m01_run1_full.attempt1.json"
    ready = tmp_path / "observer.ready.json"
    pcd.write_text("synthetic PCD for observer test")
    cylinders.write_text("x,y,r,role\n0,0,0.5,test\n")
    source = f'''import json, time
from types import SimpleNamespace as S
ARGS = S(static_pcd={str(pcd)!r}, out_json={str(out)!r})
rclpy = S(init=lambda: None)
class LoopMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.legacy_callbacks = 0
    def odom_callback(self, msg):
        self.legacy_callbacks += 1
rclpy.init()
node = LoopMonitor()
for i, x in enumerate([1.0, 0.6, 10.0, 0.6], 1):
    msg = S(header=S(stamp=S(sec=0, nanosec=i*10000000)),
            pose=S(pose=S(position=S(x=x, y=0., z=1.5))),
            twist=S(twist=S(linear=S(x=0., y=0., z=0.))))
    node.odom_callback(msg)
success = False
with open(ARGS.out_json, 'w') as stream:
    json.dump({{"legacy_callbacks": node.legacy_callbacks, "success": success}}, stream)
'''.encode()
    base = tmp_path / "fake_base.py"
    base.write_bytes(source)
    monkeypatch.setenv("GAPFREE_BASE_MONITOR", str(base))
    monkeypatch.setenv(monitor.READY_FILE_ENV, str(ready))
    original_split = monitor.split_base_source
    monkeypatch.setattr(monitor, "split_base_source", lambda source, filename:
                        original_split(source, filename, hashlib.sha256(source).hexdigest()))
    monkeypatch.setattr(monitor, "load_cylinders", lambda path: ([[0, 0, .5]], cylinders))
    monkeypatch.setattr(monitor.sys, "path", list(monitor.sys.path))
    monitor.main()
    native = json.loads(out.read_text())
    assert native == {"legacy_callbacks": 4, "success": False}
    audit = json.loads(out.with_suffix(".cylinder_audit.json").read_text())
    assert audit["audit_valid"] and audit["completion"] and audit["success"] is False
    assert audit["contact_episodes"] == 2 and audit["samples"] == 4
    assert audit["native_monitor_counters_unchanged"] is True
    assert len(out.with_suffix(".odometry.csv").read_text().splitlines()) == 5
    assert audit["odometry_sha256"] == monitor.sha256(out.with_suffix(".odometry.csv"))
    readiness = json.loads(ready.read_text())
    assert readiness["schema"] == "gapfree-observer-odom-ready-v1"
    assert readiness["recorded_samples"] == 1
    assert readiness["first_position_m"] == [1.0, 0.0, 1.5]
    with pytest.raises(FileExistsError):
        monitor.main()
