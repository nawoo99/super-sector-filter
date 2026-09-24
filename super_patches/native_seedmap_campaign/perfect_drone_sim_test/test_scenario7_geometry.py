"""Exact solid-distance and evidence tests; no ROS, simulator, or flights."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import scenario7_geometry as geometry
import scenario7_native_loop_monitor as monitor


def document(boxes=None, cylinders=None, name="urban_blocks_u01"):
    return {"schema": geometry.GEOMETRY_SCHEMA, "map": name, "body_radius_m": .2,
            "boxes": boxes or [], "cylinders": cylinders or []}


def box(identifier="building", cx=0, cy=0):
    return {"id": identifier, "cx": cx, "cy": cy, "z_min": 0, "z_max": 2,
            "size_x": 2, "size_y": 2}


def cylinder(identifier="trunk", x=0, y=0):
    return {"id": identifier, "x": x, "y": y, "r": .5, "z_min": 0, "z_max": 3}


def observe(audit, position, index):
    return audit.observe(position, [0, 0, 0], index * 10000000, index * 10000000, index / 100)


@pytest.mark.parametrize("position, expected", [
    ([0, 0, 1], -.2), ([.99, .99, 1.99], -.2),
    ([1.2, 0, 1], 0), ([0, 0, 2.3], .1), ([0, 0, -.3], .1),
    ([1.15, 1.15, 1], math.hypot(.15, .15) - .2),
    ([1 + .2 / math.sqrt(2), 1 + .2 / math.sqrt(2), 1], 0),
    ([1 + .2 / math.sqrt(3), 1 + .2 / math.sqrt(3), 2 + .2 / math.sqrt(3)], 0),
])
def test_box_interior_face_edge_corner_and_caps(position, expected):
    solid = geometry.SolidGeometry(document(boxes=[box()]))
    assert solid.clearances(position)[0] == pytest.approx(expected, abs=1e-12)
    audit = geometry.SampledSolidAudit(solid)
    observe(audit, position, 1)
    assert audit.contact_samples == int(expected <= 1e-9)


def test_translated_asymmetric_box_uses_full_3d_extents():
    primitive = box(cx=10, cy=-5)
    primitive.update(size_x=6, size_y=2, z_min=-2, z_max=4)
    solid = geometry.SolidGeometry(document(boxes=[primitive]))
    assert solid.clearances([13.12, -3.84, 4])[0] == pytest.approx(0)
    assert solid.clearances([10, -5, -2.21])[0] == pytest.approx(.01)


@pytest.mark.parametrize("position, expected", [
    ([0, 0, 1.5], -.2), ([0, 0, .01], -.2), ([.49, 0, 2.99], -.2),
    ([.7, 0, 1.5], 0), ([0, 0, 3.2], 0), ([0, 0, -.2], 0),
    ([.65, 0, 3.15], math.hypot(.15, .15) - .2),
    ([.5 + .2 / math.sqrt(2), 0, 3 + .2 / math.sqrt(2)], 0),
    ([.49, .49, 1], math.hypot(.49, .49) - .7),
])
def test_finite_cylinder_caps_radial_corner_and_interior(position, expected):
    solid = geometry.SolidGeometry(document(cylinders=[cylinder()]))
    assert solid.clearances(position)[0] == pytest.approx(expected, abs=1e-12)


def test_union_episodes_continue_across_primitive_transition_reset_on_exit():
    audit = geometry.SampledSolidAudit(document(boxes=[box()], cylinders=[cylinder(x=1.4)]))
    for i, x in enumerate([0, 1.1, 1.4, 4, 1.4, 4], 1):
        observe(audit, [x, 0, 1], i)
    assert audit.contact_episodes == 2 and audit.contact_samples == 4
    assert [event["kind"] for event in audit.events] == ["enter", "exit", "enter", "exit"]
    assert audit.events[0]["primitive_ids"] == ["building"]
    assert audit.events[2]["nearest_primitive_type"] == "cylinder"
    assert audit.summary()["audit_valid"]


def test_invalid_and_missing_observations_do_not_mean_valid_zero():
    audit = geometry.SampledSolidAudit(document(boxes=[box()]))
    assert not audit.summary()["audit_valid"]
    observe(audit, [4, 0, 1], 2)
    observe(audit, [4, 0, 1], 1)
    assert observe(audit, [float("nan"), 0, 1], 3) is None
    assert audit.observe([4, 0, 1], [0, float("inf"), 0], 4, 4, .04) is None
    assert not audit.summary()["audit_valid"]
    assert audit.invalid_samples == 2
    assert audit.timestamp_nonmonotonic_count == audit.receipt_nonmonotonic_count == 1
    json.dumps(audit.summary(), allow_nan=False)


def test_clear_sample_crossing_does_not_claim_swept_detection():
    audit = geometry.SampledSolidAudit(document(boxes=[box()]))
    observe(audit, [-2, 0, 1], 1)
    observe(audit, [2, 0, 1], 2)
    assert audit.contact_episodes == 0 and audit.summary()["swept_collision_check"] is False
    assert audit.summary()["max_pose_step_m"] == 4


@pytest.mark.parametrize("change", [
    lambda doc: doc.update(boxes=[]),
    lambda doc: doc.update(body_radius_m=0),
    lambda doc: doc["boxes"][0].update(cx=float("nan")),
    lambda doc: doc["boxes"][0].update(size_x=-1),
    lambda doc: doc["boxes"][0].update(size_y=True),
    lambda doc: doc["boxes"][0].update(z_max=0),
    lambda doc: doc.update(cylinders=[cylinder(identifier="building")]),
    lambda doc: doc.update(cylinders=[{**cylinder(), "r": 0}]),
    lambda doc: doc.update(cylinders=[{**cylinder(), "z_min": 4}]),
])
def test_malformed_geometry_rejected(change):
    doc = document(boxes=[box()])
    change(doc)
    with pytest.raises(ValueError):
        geometry.SolidGeometry(doc)


def test_loader_rejects_missing_malformed_mismatched_and_unknown_geometry(tmp_path):
    pcd = tmp_path / "urban_blocks_u01.pcd"
    pcd.write_text("offline test PCD")
    sidecar = pcd.with_name(pcd.stem + "_geometry.json")
    with pytest.raises(FileNotFoundError):
        geometry.load_geometry(pcd)
    sidecar.write_text('{"schema":"scenario-solid-geometry-v1","map":"a","map":"b"}')
    with pytest.raises(ValueError, match="Duplicate"):
        geometry.load_geometry(pcd)
    sidecar.write_text(json.dumps(document(boxes=[box()], name="forest_cluster_f01")))
    with pytest.raises(ValueError, match="map/body"):
        geometry.load_geometry(pcd)
    sidecar.write_text(json.dumps(document(boxes=[box()])))
    solid = geometry.load_geometry(pcd)
    assert solid.metadata()["geometry_sha256"] == geometry.sha256(sidecar)
    with pytest.raises(ValueError, match="restricted"):
        geometry.load_geometry(tmp_path / "other.pcd")


def test_legacy_csv_preserves_exact_410_cylinders_and_height(tmp_path):
    pcd = tmp_path / "gapfree_d1_m05r2.pcd"
    pcd.write_text("offline test PCD")
    csv_path = pcd.with_name(pcd.stem + "_cylinders.csv")
    csv_path.write_text("x,y,r\n" + "0,0,.5\n" * 410)
    solid = geometry.load_geometry(pcd)
    assert solid.metadata()["primitive_height_ranges_m"] == {"boxes": [], "cylinders": [[0., 3.]]}
    assert solid.metadata()["cylinder_count"] == 410
    csv_path.write_text("x,y,r\n" + "0,0,.5\n" * 409)
    with pytest.raises(ValueError, match="410"):
        geometry.load_geometry(pcd)


def run_fake_observer(tmp_path, monkeypatch, positions=None, raises=False):
    """Run adapter hook, readiness and finalization with a fake frozen loop."""
    pcd = tmp_path / "urban_blocks_u01.pcd"
    out = tmp_path / "urban_blocks_u01_run1_full.attempt1.json"
    ready = tmp_path / "observer.ready.json"
    pcd.write_text("offline test PCD")
    pcd.with_name(pcd.stem + "_geometry.json").write_text(json.dumps(document(boxes=[box()])))
    positions = positions if positions is not None else [2., 1.1, 4., 1.1]
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
for i, x in enumerate({positions!r}, 1):
    if x is None:
        x = float('nan')
    msg = S(header=S(stamp=S(sec=0, nanosec=i*10000000)),
            pose=S(pose=S(position=S(x=x, y=0., z=1.))),
            twist=S(twist=S(linear=S(x=0., y=0., z=0.))))
    node.odom_callback(msg)
if {raises!r}:
    raise RuntimeError('synthetic failure')
success = False
with open(ARGS.out_json, 'w') as stream:
    json.dump({{"legacy_callbacks": node.legacy_callbacks, "success": success}}, stream)
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
    if raises:
        with pytest.raises(RuntimeError, match="synthetic failure"):
            monitor.main()
    else:
        monitor.main()
    return pcd, out, out.with_suffix(".solid_audit.json"), ready


def test_observer_preserves_native_and_complete_unsuccessful_observation_is_valid(tmp_path, monkeypatch):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch)
    assert json.loads(out.read_text()) == {"legacy_callbacks": 4, "success": False}
    doc = json.loads(audit_path.read_text())
    assert doc["completion"] is True and doc["success"] is False and doc["audit_valid"]
    assert doc["contact_episodes"] == 2 and doc["samples"] == 4
    assert doc["coverage"]["written_rows"] == 4 and doc["coverage"]["all_received_samples_recorded"]
    assert monitor.evidence_errors(audit_path, pcd) == []
    assert monitor.validate_evidence(audit_path, pcd)
    ready_doc = json.loads(ready.read_text())
    assert ready_doc["schema"] == monitor.READY_SCHEMA
    assert ready_doc["recorded_samples"] == 1 and ready_doc["first_position_m"] == [2., 0., 1.]
    with pytest.raises(FileExistsError):
        monitor.main()


def test_ready_waits_for_finite_sample_and_invalid_sample_stays_in_csv(tmp_path, monkeypatch):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch, [None, 2.])
    assert json.loads(ready.read_text())["recorded_samples"] == 2
    assert json.loads(out.read_text())["legacy_callbacks"] == 1
    doc = json.loads(audit_path.read_text())
    assert doc["samples"] == doc["coverage"]["written_rows"] == 2
    assert doc["invalid_samples"] == 1 and doc["audit_valid"] is False
    assert len(out.with_suffix(".odometry.csv").read_text().splitlines()) == 3
    assert not monitor.validate_evidence(audit_path, pcd)


def test_observer_exception_preserves_partial_evidence_without_claiming_completion(tmp_path, monkeypatch):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch, raises=True)
    doc = json.loads(audit_path.read_text())
    assert doc["completion"] is False and doc["audit_valid"] is False and doc["success"] is None
    assert doc["samples"] == 4 and out.with_suffix(".odometry.csv").exists()
    assert not monitor.validate_evidence(audit_path, pcd)


def test_zero_sample_observer_never_claims_valid_contact_evidence(tmp_path, monkeypatch):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch, [])
    assert not ready.exists() and not monitor.validate_evidence(audit_path, pcd)
    assert json.loads(audit_path.read_text())["min_clearance_m"] is None


@pytest.mark.parametrize("mutation", ["missing", "truncated", "wrong_clearance", "wrong_count", "wrong_code", "wrong_geometry", "wrong_success", "boolean_count"])
def test_missing_or_tampered_evidence_cannot_be_valid_zero(tmp_path, monkeypatch, mutation):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch)
    doc = json.loads(audit_path.read_text())
    csv_path = out.with_suffix(".odometry.csv")
    if mutation == "missing":
        csv_path.unlink()
    elif mutation == "truncated":
        csv_path.write_text("\n".join(csv_path.read_text().splitlines()[:-1]) + "\n")
        doc["odometry_sha256"] = geometry.sha256(csv_path)
    elif mutation == "wrong_clearance":
        lines = csv_path.read_text().splitlines()
        fields = lines[2].split(",")
        fields[-1] = "3.0"
        lines[2] = ",".join(fields)
        csv_path.write_text("\n".join(lines) + "\n")
        doc["odometry_sha256"] = geometry.sha256(csv_path)
    elif mutation == "wrong_count":
        doc["contact_episodes"] = 0
    elif mutation == "boolean_count":
        doc["invalid_samples"] = False
    elif mutation == "wrong_success":
        doc["success"] = True
    elif mutation == "wrong_code":
        doc["geometry_code_sha256"] = "0" * 64
    elif mutation == "wrong_geometry":
        geometry_path = pcd.with_name(pcd.stem + "_geometry.json")
        geometry_path.write_text(json.dumps(document(boxes=[box(cx=20)])))
    audit_path.write_text(json.dumps(doc))
    assert not monitor.validate_evidence(audit_path, pcd)


def test_missing_artifact_is_invalid(tmp_path):
    assert not monitor.validate_evidence(tmp_path / "missing.solid_audit.json")


def test_byte_identical_relocated_sidecars_keep_original_provenance(tmp_path, monkeypatch):
    pcd, out, audit_path, ready = run_fake_observer(tmp_path, monkeypatch)
    destination = tmp_path / "artifacts"
    destination.mkdir()
    for source in (audit_path, out, out.with_suffix(".odometry.csv")):
        shutil.copy2(source, destination / source.name)
    relocated = destination / audit_path.name
    assert monitor.validate_evidence(relocated, pcd)
    assert relocated.read_bytes() == audit_path.read_bytes()
    document = json.loads(relocated.read_text())
    document["odometry_csv"] = str(tmp_path / "another_run.odometry.csv")
    relocated.write_text(json.dumps(document))
    assert not monitor.validate_evidence(relocated, pcd)


@pytest.mark.parametrize("value", [[], None, 0, "malformed"])
def test_malformed_json_document_is_invalid(tmp_path, value):
    path = tmp_path / "bad.solid_audit.json"
    path.write_text(json.dumps(value))
    assert not monitor.validate_evidence(path)
