#!/usr/bin/env python3
"""Supplement the frozen loop observer with sampled solid-cylinder contacts.

The original observer and its output are left intact.  This wrapper is only for
gapfree_d1_m01..m05 and emits a cylinder audit plus every received odometry
sample beside the original JSON.  Contacts are sphere/finite-cylinder
intersections at received poses, not a continuous/swept collision proof.
"""
import ast
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

import numpy as np


BASE_SHA256 = "f11777e680e4d4279c8d34ca7dfd86c55e98c9a7f6cd835e801a1f8a877f0813"
DEFAULT_BASE = Path("/root/super-sector-filter/scripts/native_campaign/native_loop_monitor.py")
BODY_RADIUS_M = 0.2
CYLINDER_HEIGHT_M = 3.0
READY_FILE_ENV = "SUPER_LOOP_MONITOR_READY_FILE"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_ready_file(path, value):
    """Atomically acknowledge that the first odometry sample was recorded."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x") as stream:
        json.dump(value, stream, allow_nan=False)
    os.replace(temporary, path)


def load_cylinders(pcd_path):
    pcd_path = Path(pcd_path).resolve()
    if not re.fullmatch(r"gapfree_d1_m0[1-5]\.pcd", pcd_path.name):
        raise ValueError("Solid-cylinder observer is restricted to gapfree_d1_m01..m05")
    csv_path = pcd_path.with_name(pcd_path.stem + "_cylinders.csv")
    with csv_path.open(newline="") as stream:
        rows = [[float(row[k]) for k in ("x", "y", "r")]
                for row in csv.DictReader(stream)]
    cylinders = np.asarray(rows, dtype=np.float64)
    if cylinders.shape != (410, 3) or not np.all(np.isfinite(cylinders)):
        raise ValueError("Expected exactly 410 finite cylinders")
    if not np.all(cylinders[:, 2] == 0.5):
        raise ValueError("Gapfree cylinder radius must be 0.5 m")
    return cylinders, csv_path


class SampledCylinderAudit:
    """Union contact episodes: consecutive received colliding samples = one."""

    def __init__(self, cylinders, robot_radius_m=BODY_RADIUS_M):
        self.cylinders = np.asarray(cylinders, dtype=np.float64)
        if (self.cylinders.ndim != 2 or self.cylinders.shape[1] != 3
                or len(self.cylinders) == 0
                or not np.all(np.isfinite(self.cylinders))
                or np.any(self.cylinders[:, 2] <= 0.0)
                or not math.isfinite(robot_radius_m) or robot_radius_m <= 0):
            raise ValueError("Invalid finite cylinder/body geometry")
        self.robot_radius_m = float(robot_radius_m)
        self.samples = 0
        self.invalid_samples = 0
        self.timestamp_nonmonotonic_count = 0
        self.receipt_nonmonotonic_count = 0
        self.max_header_interval_s = None
        self.max_receipt_interval_s = None
        self.max_pose_step_m = None
        self.contact_samples = 0
        self.contact_episodes = 0
        self.min_clearance_m = None
        self.min_context = None
        self.events = []
        self.in_contact = False
        self.last_header_ns = None
        self.last_receipt_ns = None
        self.last_position = None

    def observe(self, position, velocity, header_ns, receipt_ns, elapsed_s):
        self.samples += 1
        position = np.asarray(position, dtype=np.float64)
        velocity = np.asarray(velocity, dtype=np.float64)
        if (position.shape != (3,) or velocity.shape != (3,)
                or not np.all(np.isfinite(position))
                or not np.all(np.isfinite(velocity))
                or not math.isfinite(elapsed_s)):
            self.invalid_samples += 1
            return None
        if self.last_header_ns is not None:
            delta = (header_ns - self.last_header_ns) / 1e9
            if delta <= 0.0:
                self.timestamp_nonmonotonic_count += 1
            self.max_header_interval_s = max(self.max_header_interval_s or 0.0, delta)
        if self.last_receipt_ns is not None:
            delta = (receipt_ns - self.last_receipt_ns) / 1e9
            if delta <= 0.0:
                self.receipt_nonmonotonic_count += 1
            self.max_receipt_interval_s = max(self.max_receipt_interval_s or 0.0, delta)
        if self.last_position is not None:
            self.max_pose_step_m = max(self.max_pose_step_m or 0.0,
                                       float(np.linalg.norm(position - self.last_position)))
        self.last_header_ns, self.last_receipt_ns = header_ns, receipt_ns
        self.last_position = position.copy()
        radial = np.maximum(np.linalg.norm(self.cylinders[:, :2] - position[:2], axis=1)
                            - self.cylinders[:, 2], 0.0)
        vertical = max(-float(position[2]), float(position[2]) - CYLINDER_HEIGHT_M, 0.0)
        distances = np.hypot(radial, vertical)
        clearances = distances - self.robot_radius_m
        nearest = int(np.argmin(clearances))
        clearance = float(clearances[nearest])
        context = {
            "sample": self.samples, "header_ns": int(header_ns),
            "elapsed_s": float(elapsed_s), "position_m": position.tolist(),
            "velocity_mps": velocity.tolist(), "nearest_cylinder_index": nearest,
            "clearance_m": clearance,
        }
        if self.min_clearance_m is None or clearance < self.min_clearance_m:
            self.min_clearance_m, self.min_context = clearance, context
        # Include mathematical tangency; 1 nm tolerance only covers float noise.
        colliding = clearance <= 1e-9
        if colliding:
            self.contact_samples += 1
            if not self.in_contact:
                self.contact_episodes += 1
                self.events.append({**context, "kind": "enter",
                                    "episode": self.contact_episodes,
                                    "cylinder_indices": np.flatnonzero(clearances <= 1e-9).tolist()})
        elif self.in_contact:
            self.events.append({**context, "kind": "exit", "episode": self.contact_episodes})
        self.in_contact = colliding
        return clearance

    def summary(self):
        return {
            "observation": "received_odometry_samples_only",
            "contact_definition": "sphere intersects finite solid cylinder; tangency included (1e-9 m tolerance)",
            "episode_definition": "contiguous colliding received samples in the union of cylinders",
            "swept_collision_check": False, "robot_radius_m": self.robot_radius_m,
            "cylinder_z_min_m": 0.0, "cylinder_z_max_m": CYLINDER_HEIGHT_M,
            "cylinder_count": len(self.cylinders), "samples": self.samples,
            "invalid_samples": self.invalid_samples,
            "timestamp_nonmonotonic_count": self.timestamp_nonmonotonic_count,
            "receipt_nonmonotonic_count": self.receipt_nonmonotonic_count,
            "max_header_interval_s": self.max_header_interval_s,
            "max_receipt_interval_s": self.max_receipt_interval_s,
            "max_pose_step_m": self.max_pose_step_m,
            "contact_samples": self.contact_samples, "contact_episodes": self.contact_episodes,
            "in_contact_at_end": self.in_contact, "min_clearance_m": self.min_clearance_m,
            "min_context": self.min_context, "events": self.events,
            "audit_valid": bool(self.samples > 0 and self.invalid_samples == 0
                                and self.timestamp_nonmonotonic_count == 0
                                and self.receipt_nonmonotonic_count == 0),
        }


def split_base_source(source, filename, expected_sha256=BASE_SHA256):
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise ValueError("Frozen base monitor SHA256 changed; review the adapter before use")
    tree = ast.parse(source, filename=filename)
    indices = [i for i, node in enumerate(tree.body)
               if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
               and isinstance(node.value.func, ast.Attribute)
               and isinstance(node.value.func.value, ast.Name)
               and node.value.func.value.id == "rclpy" and node.value.func.attr == "init"]
    if len(indices) != 1:
        raise ValueError("Expected exactly one top-level rclpy.init injection point")
    i = indices[0]
    return (compile(ast.Module(body=tree.body[:i], type_ignores=[]), filename, "exec"),
            compile(ast.Module(body=tree.body[i:], type_ignores=[]), filename, "exec"))


def main():
    base = Path(os.environ.get("GAPFREE_BASE_MONITOR", str(DEFAULT_BASE))).resolve()
    prefix, suffix = split_base_source(base.read_bytes(), str(base))
    sys.path.insert(0, str(base.parent))
    namespace = {"__name__": "gapfree_frozen_native_monitor", "__file__": str(base)}
    exec(prefix, namespace)
    args = namespace["ARGS"]
    if not args.static_pcd:
        raise ValueError("Gapfree monitor requires --static-pcd")
    cylinders, csv_path = load_cylinders(args.static_pcd)
    out_json = Path(args.out_json)
    audit_path = out_json.with_suffix(".cylinder_audit.json")
    odometry_path = out_json.with_suffix(".odometry.csv")
    if any(path.exists() for path in (out_json, audit_path, odometry_path)):
        raise FileExistsError("Refusing to overwrite existing observer evidence")
    audit = SampledCylinderAudit(cylinders)
    metadata = {
        "schema_version": 1, "map": Path(args.static_pcd).stem,
        "base_monitor_path": str(base), "base_monitor_sha256": sha256(base),
        "pcd_path": str(Path(args.static_pcd).resolve()), "pcd_sha256": sha256(args.static_pcd),
        "cylinders_path": str(csv_path), "cylinders_sha256": sha256(csv_path),
        "odometry_csv": str(odometry_path), "native_monitor_json": str(out_json),
        "native_monitor_counters_unchanged": True,
        "legacy_static_pcd_episode_reset_defect_fixed": False,
    }
    original_class = namespace["LoopMonitor"]
    with odometry_path.open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample", "header_ns", "receipt_monotonic_ns", "elapsed_s",
                         "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps", "clearance_m"])

        class GapfreeLoopMonitor(original_class):
            def __init__(self):
                super().__init__()
                self._ready_file = os.environ.get(READY_FILE_ENV)
                self._ready_written = False

            def odom_callback(self, msg):
                p, v = msg.pose.pose.position, msg.twist.twist.linear
                position, velocity = [p.x, p.y, p.z], [v.x, v.y, v.z]
                header_ns = int(msg.header.stamp.sec) * 1000000000 + int(msg.header.stamp.nanosec)
                receipt_ns, elapsed = time.monotonic_ns(), time.time() - self.start_time
                clearance = audit.observe(position, velocity, header_ns, receipt_ns, elapsed)
                values = [audit.samples, header_ns, receipt_ns, elapsed, *position, *velocity, clearance]
                writer.writerow([value if not isinstance(value, float) or math.isfinite(value) else ""
                                 for value in values])
                if audit.samples % 100 == 0:
                    stream.flush()
                if clearance is None:
                    return  # Invalid evidence cannot enter the legacy float/point index.
                super().odom_callback(msg)
                if self._ready_file and not self._ready_written:
                    write_ready_file(self._ready_file, {
                        "schema": "gapfree-observer-odom-ready-v1",
                        "pid": os.getpid(),
                        "epoch_s": time.time(),
                        "recorded_samples": audit.samples,
                        "first_position_m": position,
                        "first_velocity_mps": velocity,
                    })
                    self._ready_written = True

        namespace["LoopMonitor"] = GapfreeLoopMonitor
        completed = False
        try:
            exec(suffix, namespace)
            completed = True
        finally:
            stream.flush()
            result = {**metadata, **audit.summary(), "completion": completed,
                      "success": namespace.get("success") if completed else None}
            result["audit_valid"] = bool(result["audit_valid"] and completed)
            result["odometry_sha256"] = sha256(odometry_path)
            with audit_path.open("x") as result_stream:
                json.dump(result, result_stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
