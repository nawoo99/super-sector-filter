"""No-flight evidence/coverage checks for the new repair observer."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scenario7_repair_loop_monitor as monitor


def fake_run(tmp_path, monkeypatch, positions=(2., 1.1, 4., 1.1)):
    pcd = tmp_path / "urban_blocks_u01.pcd"
    out = tmp_path / "urban_blocks_u01_run1_full.attempt1.json"
    ready = tmp_path / "ready.json"
    pcd.write_text("synthetic test PCD")
    pcd.with_name(pcd.stem + "_geometry.json").write_text(json.dumps({
        "schema": "scenario-solid-geometry-v1", "map": pcd.stem, "body_radius_m": .2,
        "boxes": [{"id": "building", "cx": 0, "cy": 0, "z_min": 0,
                   "z_max": 2, "size_x": 2, "size_y": 2}], "cylinders": []}))
    source = f'''import json, time
from types import SimpleNamespace as S
ARGS = S(static_pcd={str(pcd)!r}, out_json={str(out)!r})
rclpy = S(init=lambda: None)
class StaticPcdIndex:
    pass
class LoopMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.legacy_callbacks = 0
    def odom_callback(self, msg):
        self.legacy_callbacks += 1
rclpy.init()
node = LoopMonitor()
for i, x in enumerate({positions!r}, 1):
    if x is None: x = float('nan')
    node.odom_callback(S(header=S(stamp=S(sec=0, nanosec=i*10000000)),
        pose=S(pose=S(position=S(x=x, y=0., z=1.))),
        twist=S(twist=S(linear=S(x=0., y=0., z=0.)))))
success = False
with open(ARGS.out_json, 'w') as f:
    json.dump({{"legacy_callbacks": node.legacy_callbacks, "success": success}}, f)
'''.encode()
    base = tmp_path / "fake_base.py"
    base.write_bytes(source)
    monkeypatch.setenv("SCENARIO7_BASE_MONITOR", str(base))
    monkeypatch.setenv(monitor.READY_FILE_ENV, str(ready))
    original_split = monitor.frozen_adapter.split_base_source
    monkeypatch.setattr(monitor.frozen_adapter, "split_base_source", lambda source, filename:
                        original_split(source, filename, hashlib.sha256(source).hexdigest()))
    monkeypatch.setattr(monitor, "BASE_SHA256", hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(monitor.sys, "path", list(monitor.sys.path))
    monitor.main()
    return pcd, out, out.with_suffix(".solid_audit.json"), ready


def test_all_samples_unchanged_counters_and_index_identity(tmp_path, monkeypatch):
    pcd, out, audit, ready = fake_run(tmp_path, monkeypatch)
    doc = json.loads(audit.read_text())
    assert doc["samples"] == doc["coverage"]["written_rows"] == 4
    assert doc["contact_episodes"] == 2
    assert doc["coverage"]["all_received_samples_recorded"]
    assert doc["coverage"]["upstream_delivery_verified"] is False
    assert doc["static_pcd_index_policy"] == monitor.INDEX_POLICY
    assert doc["index_code_sha256"] == monitor.sha256(doc["index_code_path"])
    assert json.loads(out.read_text()) == {"legacy_callbacks": 4, "success": False}
    assert json.loads(ready.read_text())["recorded_samples"] == 1
    assert monitor.evidence_errors(audit, pcd) == []


@pytest.mark.parametrize("key,value", [
    ("index_code_sha256", "0" * 64),
    ("observer_code_sha256", "0" * 64),
    ("static_pcd_index_policy", "approximate"),
    ("native_monitor_counters_unchanged", False),
])
def test_repair_index_identity_cannot_be_tampered(tmp_path, monkeypatch, key, value):
    pcd, _, audit, _ = fake_run(tmp_path, monkeypatch)
    doc = json.loads(audit.read_text())
    doc[key] = value
    audit.write_text(json.dumps(doc))
    assert not monitor.validate_evidence(audit, pcd)


def test_invalid_sample_remains_in_csv_and_invalidates_run(tmp_path, monkeypatch):
    pcd, out, audit, ready = fake_run(tmp_path, monkeypatch, (None, 2.))
    doc = json.loads(audit.read_text())
    assert doc["samples"] == doc["coverage"]["written_rows"] == 2
    assert len(out.with_suffix(".odometry.csv").read_text().splitlines()) == 3
    assert json.loads(ready.read_text())["recorded_samples"] == 2
    assert not monitor.validate_evidence(audit, pcd)
