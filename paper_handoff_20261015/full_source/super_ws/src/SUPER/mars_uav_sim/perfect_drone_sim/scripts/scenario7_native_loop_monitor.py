#!/usr/bin/env python3
"""Add solid box/cylinder observation to the unchanged, hash-pinned native loop.

This adapter records every received odometry callback.  It publishes no planner
input, keeps the legacy JSON/counters, and acknowledges readiness only after a
finite sample has been appended and flushed.  Observer completion is independent
of mission success, including completed timeout/failure observations.
"""
import csv
import json
import math
import os
from pathlib import Path
import sys
import time

import gapfree_native_loop_monitor as frozen_adapter
from scenario7_geometry import SampledSolidAudit, load_geometry, sha256


AUDIT_SCHEMA = "scenario-solid-audit-v1"
READY_SCHEMA = "scenario7-observer-odom-ready-v1"
READY_FILE_ENV = frozen_adapter.READY_FILE_ENV
BASE_SHA256 = frozen_adapter.BASE_SHA256
DEFAULT_BASE = frozen_adapter.DEFAULT_BASE
CSV_FIELDS = ["sample", "header_ns", "receipt_monotonic_ns", "elapsed_s",
              "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps", "clearance_m"]


def code_metadata(base):
    import scenario7_geometry
    paths = {"base_monitor": Path(base).resolve(), "observer_code": Path(__file__).resolve(),
             "geometry_code": Path(scenario7_geometry.__file__).resolve(),
             "adapter_code": Path(frozen_adapter.__file__).resolve()}
    result = {}
    for label, path in paths.items():
        result[label + "_path"] = str(path)
        result[label + "_sha256"] = sha256(path)
    return result


def evidence_errors(audit_path, pcd_path=None):
    """Recompute the complete recorded stream; missing/bad evidence never means zero.

    Verifies sidecars, hashes, ordered sample indices, finite pose/time/clearance,
    and every summary field against a fresh analytic replay.  This proves
    coverage of the *received* stream, not delivery of every simulator sample.
    """
    errors = []
    try:
        audit_path = Path(audit_path)
        with audit_path.open() as stream:
            document = json.load(stream)
        if not isinstance(document, dict):
            return ["audit must be a JSON object"]
        if document.get("schema") != AUDIT_SCHEMA or document.get("schema_version") != 1:
            return ["unrecognized audit schema"]
        if document.get("completion") is not True or document.get("audit_valid") is not True:
            return ["observer incomplete or audit invalid"]
        for key in ("samples", "invalid_samples", "contact_samples", "contact_episodes",
                    "timestamp_nonmonotonic_count", "receipt_nonmonotonic_count",
                    "box_count", "cylinder_count", "primitive_count"):
            if type(document.get(key)) is not int or document[key] < 0:
                return [f"invalid audit integer: {key}"]
        if document.get("native_monitor_counters_unchanged") is not True:
            errors.append("native observer counters not preserved")
        geometry = load_geometry(pcd_path if pcd_path is not None else document["pcd_path"])
        for key, value in geometry.metadata().items():
            if document.get(key) != value:
                errors.append(f"geometry metadata mismatch: {key}")
        if document.get("base_monitor_sha256") != BASE_SHA256:
            errors.append("frozen base monitor hash mismatch")
        for label in ("base_monitor", "observer_code", "geometry_code", "adapter_code"):
            if sha256(document[label + "_path"]) != document.get(label + "_sha256"):
                errors.append(f"code hash mismatch: {label}")
        # Pin the currently executing observer implementation as well as files
        # identified by the artifact; a stale observer cannot bless a new one.
        current = code_metadata(document["base_monitor_path"])
        for label in ("observer_code", "geometry_code", "adapter_code"):
            if current[label + "_sha256"] != document.get(label + "_sha256"):
                errors.append(f"current code differs: {label}")
        prefix = audit_path.name.removesuffix(".solid_audit.json")
        if prefix == audit_path.name:
            return errors + ["audit filename suffix mismatch"]
        odometry = audit_path.with_name(prefix + ".odometry.csv")
        native = audit_path.with_name(prefix + ".json")
        # The campaign copies byte-identical sidecars out of scratch. Preserve
        # original absolute paths as provenance and bind relocated files using
        # exact basenames plus hashes, never by rewriting observation metadata.
        if Path(document["odometry_csv"]).name != odometry.name:
            errors.append("odometry sidecar basename mismatch")
        if Path(document["native_monitor_json"]).name != native.name:
            errors.append("native sidecar basename mismatch")
        if sha256(odometry) != document.get("odometry_sha256"):
            errors.append("odometry SHA256 mismatch")
        if sha256(native) != document.get("native_monitor_sha256"):
            errors.append("native observer SHA256 mismatch")
        with native.open() as stream:
            native_document = json.load(stream)
        if (not isinstance(native_document, dict) or type(document.get("success")) is not bool
                or document["success"] != native_document.get("success")):
            errors.append("mission success does not match native observer")
        audit = SampledSolidAudit(geometry)
        rows = 0
        with odometry.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != CSV_FIELDS:
                return errors + ["odometry CSV header mismatch"]
            for index, row in enumerate(reader, 1):
                rows = index
                if set(row) != set(CSV_FIELDS) or any(value is None for value in row.values()):
                    return errors + ["incomplete odometry CSV row"]
                if int(row["sample"]) != index:
                    return errors + ["noncontiguous odometry CSV sample index"]
                position = [float(row[key]) for key in ("x_m", "y_m", "z_m")]
                velocity = [float(row[key]) for key in ("vx_mps", "vy_mps", "vz_mps")]
                clearance = audit.observe(position, velocity, int(row["header_ns"]),
                                          int(row["receipt_monotonic_ns"]), float(row["elapsed_s"]))
                recorded = float(row["clearance_m"])
                if clearance is None or not math.isfinite(recorded) or not math.isclose(clearance, recorded, abs_tol=1e-12, rel_tol=1e-12):
                    return errors + ["odometry clearance replay mismatch"]
        expected_coverage = {"received_samples": audit.samples, "written_rows": rows,
                             "first_sample": 1 if rows else None, "last_sample": rows if rows else None,
                             "all_received_samples_recorded": rows == audit.samples,
                             "source": "received_odometry_callbacks", "upstream_delivery_verified": False}
        if document.get("coverage") != expected_coverage or rows != document.get("samples"):
            errors.append("recorded stream coverage mismatch")
        for key, value in audit.summary().items():
            if document.get(key) != value:
                errors.append(f"analytic replay mismatch: {key}")
    except (OSError, ValueError, TypeError, KeyError, OverflowError, csv.Error) as error:
        errors.append(f"missing or malformed evidence: {error}")
    return errors


def validate_evidence(audit_path, pcd_path=None):
    return not evidence_errors(audit_path, pcd_path)


def main():
    base = Path(os.environ.get("SCENARIO7_BASE_MONITOR", str(DEFAULT_BASE))).resolve()
    prefix, suffix = frozen_adapter.split_base_source(base.read_bytes(), str(base))
    sys.path.insert(0, str(base.parent))
    namespace = {"__name__": "scenario7_frozen_native_monitor", "__file__": str(base)}
    exec(prefix, namespace)
    args = namespace["ARGS"]
    if not args.static_pcd:
        raise ValueError("Seven-map solid monitor requires --static-pcd")
    geometry = load_geometry(args.static_pcd)
    out_json = Path(args.out_json).resolve()
    audit_path, odometry_path = out_json.with_suffix(".solid_audit.json"), out_json.with_suffix(".odometry.csv")
    ready_path = os.environ.get(READY_FILE_ENV)
    if any(path.exists() for path in (out_json, audit_path, odometry_path)):
        raise FileExistsError("Refusing to overwrite existing observer evidence")
    if ready_path and Path(ready_path).exists():
        raise FileExistsError("Refusing stale observer readiness evidence")
    audit = SampledSolidAudit(geometry)
    metadata = {"schema": AUDIT_SCHEMA, "schema_version": 1,
                **geometry.metadata(), **code_metadata(base),
                "odometry_csv": str(odometry_path), "native_monitor_json": str(out_json),
                "native_monitor_counters_unchanged": True,
                "legacy_static_pcd_episode_reset_defect_fixed": False}
    original_class = namespace["LoopMonitor"]
    with odometry_path.open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(CSV_FIELDS)
        written_rows = 0

        class Scenario7LoopMonitor(original_class):
            def __init__(self):
                super().__init__()
                self._solid_ready_written = False

            def odom_callback(self, msg):
                nonlocal written_rows
                p, v = msg.pose.pose.position, msg.twist.twist.linear
                position, velocity = [p.x, p.y, p.z], [v.x, v.y, v.z]
                header_ns = int(msg.header.stamp.sec) * 1000000000 + int(msg.header.stamp.nanosec)
                receipt_ns, elapsed = time.monotonic_ns(), time.time() - self.start_time
                clearance = audit.observe(position, velocity, header_ns, receipt_ns, elapsed)
                values = [audit.samples, header_ns, receipt_ns, elapsed, *position, *velocity, clearance]
                writer.writerow([value if not isinstance(value, float) or math.isfinite(value) else ""
                                 for value in values])
                written_rows += 1
                if audit.samples % 100 == 0:
                    stream.flush()
                if clearance is None:
                    return  # Invalid evidence cannot enter legacy float/point indexing.
                super().odom_callback(msg)
                if ready_path and not self._solid_ready_written:
                    stream.flush()
                    frozen_adapter.write_ready_file(ready_path, {
                        "schema": READY_SCHEMA, "pid": os.getpid(), "epoch_s": time.time(),
                        "recorded_samples": audit.samples, "first_position_m": position,
                        "first_velocity_mps": velocity,
                    })
                    self._solid_ready_written = True

        namespace["LoopMonitor"] = Scenario7LoopMonitor
        completed = False
        try:
            exec(suffix, namespace)
            completed = True
        finally:
            stream.flush()
            result = {**metadata, **audit.summary(), "completion": completed,
                      "success": namespace.get("success") if completed else None,
                      "coverage": {"received_samples": audit.samples, "written_rows": written_rows,
                                   "first_sample": 1 if written_rows else None,
                                   "last_sample": written_rows if written_rows else None,
                                   "all_received_samples_recorded": written_rows == audit.samples,
                                   "source": "received_odometry_callbacks", "upstream_delivery_verified": False}}
            result["native_monitor_sha256"] = sha256(out_json) if out_json.is_file() else None
            result["audit_valid"] = bool(result["audit_valid"] and completed
                                        and written_rows == audit.samples and out_json.is_file())
            result["odometry_sha256"] = sha256(odometry_path)
            with audit_path.open("x") as result_stream:
                json.dump(result, result_stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
