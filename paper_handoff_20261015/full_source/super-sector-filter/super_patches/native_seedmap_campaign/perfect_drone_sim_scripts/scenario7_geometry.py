#!/usr/bin/env python3
"""Closed solid geometry for the additive seven-map campaign.

Clearance is distance from the body centre to the *solid* minus sphere radius.
It is therefore -radius throughout a solid's interior, not a penetration depth.
Ground and virtual flight boundaries remain the frozen observer's policy.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


GEOMETRY_SCHEMA = "scenario-solid-geometry-v1"
BODY_RADIUS_M = 0.2
LEGACY_MAPS = tuple(f"gapfree_d1_m{i:02d}" for i in range(1, 5)) + ("gapfree_d1_m05r2",)
NEW_MAPS = ("urban_blocks_u01", "forest_cluster_f01")
ALLOWED_MAPS = LEGACY_MAPS + NEW_MAPS
CONTACT_TOLERANCE_M = 1e-9


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Expected finite number: {field}")
    return float(value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


class SolidGeometry:
    """Validated axis-aligned boxes and vertical, capped cylinders."""

    def __init__(self, document, geometry_path=None, pcd_path=None):
        if not isinstance(document, dict) or document.get("schema") != GEOMETRY_SCHEMA:
            raise ValueError("Expected scenario-solid-geometry-v1 geometry")
        if not isinstance(document.get("map"), str) or not document["map"]:
            raise ValueError("Geometry requires a map name")
        self.map = document["map"]
        self.robot_radius_m = _number(document.get("body_radius_m"), "body_radius_m")
        if self.robot_radius_m <= 0:
            raise ValueError("Body radius must be positive")
        boxes, cylinders = document.get("boxes"), document.get("cylinders")
        if not isinstance(boxes, list) or not isinstance(cylinders, list) or not (boxes or cylinders):
            raise ValueError("Geometry requires nonempty solid primitives and both primitive lists")
        self.primitive_ids = []
        self.primitive_types = []
        self.primitive_height_ranges_m = {"boxes": [], "cylinders": []}
        box_bounds, cylinder_values = [], []
        for kind, primitives in (("box", boxes), ("cylinder", cylinders)):
            for primitive in primitives:
                if not isinstance(primitive, dict):
                    raise ValueError("Primitive must be an object")
                identifier = primitive.get("id")
                if not isinstance(identifier, str) or not identifier or identifier in self.primitive_ids:
                    raise ValueError("Primitive IDs must be unique nonempty strings")
                keys = (("cx", "cy", "z_min", "z_max", "size_x", "size_y") if kind == "box"
                        else ("x", "y", "r", "z_min", "z_max"))
                values = {key: _number(primitive.get(key), key) for key in keys}
                if values["z_max"] <= values["z_min"]:
                    raise ValueError("Primitive height must be positive")
                if kind == "box":
                    if values["size_x"] <= 0 or values["size_y"] <= 0:
                        raise ValueError("Box dimensions must be positive")
                    box_bounds.append([
                        values["cx"] - values["size_x"] / 2, values["cy"] - values["size_y"] / 2,
                        values["z_min"], values["cx"] + values["size_x"] / 2,
                        values["cy"] + values["size_y"] / 2, values["z_max"],
                    ])
                else:
                    if values["r"] <= 0:
                        raise ValueError("Cylinder radius must be positive")
                    cylinder_values.append([values[key] for key in keys])
                self.primitive_ids.append(identifier)
                self.primitive_types.append(kind)
                ranges = self.primitive_height_ranges_m["boxes" if kind == "box" else "cylinders"]
                interval = [values["z_min"], values["z_max"]]
                if interval not in ranges:
                    ranges.append(interval)
        self.box_bounds = np.asarray(box_bounds, dtype=np.float64).reshape(-1, 6)
        self.cylinders = np.asarray(cylinder_values, dtype=np.float64).reshape(-1, 5)
        if not np.all(np.isfinite(self.box_bounds)):
            raise ValueError("Box bounds overflow")
        self.geometry_path = Path(geometry_path).resolve() if geometry_path is not None else None
        self.pcd_path = Path(pcd_path).resolve() if pcd_path is not None else None

    @property
    def primitive_count(self):
        return len(self.primitive_ids)

    def clearances(self, position, robot_radius_m=None):
        """Exact sphere clearance per solid, ordered boxes then cylinders."""
        point = np.asarray(position, dtype=np.float64)
        if point.shape != (3,) or not np.all(np.isfinite(point)):
            raise ValueError("Position must be three finite coordinates")
        radius = self.robot_radius_m if robot_radius_m is None else _number(robot_radius_m, "robot_radius_m")
        if radius <= 0:
            raise ValueError("Body radius must be positive")
        distances = []
        if len(self.box_bounds):
            offset = np.maximum(np.maximum(self.box_bounds[:, :3] - point,
                                           point - self.box_bounds[:, 3:]), 0.0)
            distances.append(np.hypot(np.hypot(offset[:, 0], offset[:, 1]), offset[:, 2]))
        if len(self.cylinders):
            radial = np.maximum(np.hypot(self.cylinders[:, 0] - point[0],
                                         self.cylinders[:, 1] - point[1]) - self.cylinders[:, 2], 0.0)
            vertical = np.maximum(np.maximum(self.cylinders[:, 3] - point[2],
                                             point[2] - self.cylinders[:, 4]), 0.0)
            distances.append(np.hypot(radial, vertical))
        return np.concatenate(distances) - radius

    def metadata(self):
        result = {
            "map": self.map, "geometry_schema": GEOMETRY_SCHEMA,
            "box_count": len(self.box_bounds), "cylinder_count": len(self.cylinders),
            "primitive_count": self.primitive_count,
            "primitive_height_ranges_m": self.primitive_height_ranges_m,
            "robot_radius_m": self.robot_radius_m,
        }
        for label, path in (("geometry", self.geometry_path), ("pcd", self.pcd_path)):
            if path is not None:
                result[label + "_path"] = str(path)
                result[label + "_sha256"] = sha256(path)
        return result


def load_geometry(pcd_path):
    """Load only admitted campaign maps; never substitute missing geometry."""
    pcd_path = Path(pcd_path).resolve()
    if pcd_path.suffix != ".pcd" or pcd_path.stem not in ALLOWED_MAPS:
        raise ValueError("Solid observer is restricted to the admitted seven-map campaign")
    if not pcd_path.is_file():
        raise FileNotFoundError(pcd_path)
    if pcd_path.stem in LEGACY_MAPS:
        geometry_path = pcd_path.with_name(pcd_path.stem + "_cylinders.csv")
        with geometry_path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 410:
            raise ValueError("Legacy geometry requires exactly 410 cylinders")
        cylinders = []
        for index, row in enumerate(rows):
            values = {key: float(row[key]) for key in ("x", "y", "r")}
            if values["r"] != 0.5:
                raise ValueError("Legacy cylinder radius must be 0.5 m")
            cylinders.append({"id": f"cylinder_{index:04d}", **values, "z_min": 0.0, "z_max": 3.0})
        document = {"schema": GEOMETRY_SCHEMA, "map": pcd_path.stem,
                    "body_radius_m": BODY_RADIUS_M, "boxes": [], "cylinders": cylinders}
    else:
        geometry_path = pcd_path.with_name(pcd_path.stem + "_geometry.json")
        with geometry_path.open() as stream:
            document = json.load(stream, object_pairs_hook=_unique_object)
    geometry = SolidGeometry(document, geometry_path, pcd_path)
    if geometry.map != pcd_path.stem or geometry.robot_radius_m != BODY_RADIUS_M:
        raise ValueError("Geometry map/body radius does not match campaign")
    return geometry


class SampledSolidAudit:
    """Measurement only: no planner feedback and no inter-sample collision claim."""

    def __init__(self, geometry, robot_radius_m=None):
        if not isinstance(geometry, SolidGeometry):
            geometry = SolidGeometry(geometry)
        self.geometry = geometry
        self.robot_radius_m = geometry.robot_radius_m if robot_radius_m is None else _number(robot_radius_m, "robot_radius_m")
        if self.robot_radius_m <= 0:
            raise ValueError("Body radius must be positive")
        self.samples = self.invalid_samples = 0
        self.timestamp_nonmonotonic_count = self.receipt_nonmonotonic_count = 0
        self.max_header_interval_s = self.max_receipt_interval_s = self.max_pose_step_m = None
        self.contact_samples = self.contact_episodes = 0
        self.min_clearance_m = self.min_context = None
        self.events = []
        self.in_contact = False
        self.last_header_ns = self.last_receipt_ns = self.last_position = None

    def observe(self, position, velocity, header_ns, receipt_ns, elapsed_s):
        self.samples += 1
        try:
            position, velocity = np.asarray(position, dtype=np.float64), np.asarray(velocity, dtype=np.float64)
            valid = (position.shape == (3,) and velocity.shape == (3,)
                     and np.all(np.isfinite(position)) and np.all(np.isfinite(velocity))
                     and math.isfinite(elapsed_s)
                     and isinstance(header_ns, int) and not isinstance(header_ns, bool) and header_ns >= 0
                     and isinstance(receipt_ns, int) and not isinstance(receipt_ns, bool) and receipt_ns >= 0)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            self.invalid_samples += 1
            self.in_contact = False
            return None
        clearances = self.geometry.clearances(position, self.robot_radius_m)
        nearest = int(np.argmin(clearances))
        clearance = float(clearances[nearest])
        pose_step = math.dist(position, self.last_position) if self.last_position is not None else None
        if not math.isfinite(clearance) or (pose_step is not None and not math.isfinite(pose_step)):
            self.invalid_samples += 1
            self.in_contact = False
            return None
        if self.last_header_ns is not None:
            delta = (header_ns - self.last_header_ns) / 1e9
            self.timestamp_nonmonotonic_count += int(delta <= 0.0)
            self.max_header_interval_s = max(self.max_header_interval_s or 0.0, delta)
        if self.last_receipt_ns is not None:
            delta = (receipt_ns - self.last_receipt_ns) / 1e9
            self.receipt_nonmonotonic_count += int(delta <= 0.0)
            self.max_receipt_interval_s = max(self.max_receipt_interval_s or 0.0, delta)
        if self.last_position is not None:
            self.max_pose_step_m = max(self.max_pose_step_m or 0.0, pose_step)
        self.last_header_ns, self.last_receipt_ns, self.last_position = header_ns, receipt_ns, position.copy()
        context = {"sample": self.samples, "header_ns": header_ns, "elapsed_s": float(elapsed_s),
                   "position_m": position.tolist(), "velocity_mps": velocity.tolist(),
                   "nearest_primitive_index": nearest,
                   "nearest_primitive_id": self.geometry.primitive_ids[nearest],
                   "nearest_primitive_type": self.geometry.primitive_types[nearest], "clearance_m": clearance}
        if self.min_clearance_m is None or clearance < self.min_clearance_m:
            self.min_clearance_m, self.min_context = clearance, context
        colliding = clearance <= CONTACT_TOLERANCE_M
        if colliding:
            self.contact_samples += 1
            if not self.in_contact:
                self.contact_episodes += 1
                indices = np.flatnonzero(clearances <= CONTACT_TOLERANCE_M).tolist()
                self.events.append({**context, "kind": "enter", "episode": self.contact_episodes,
                                    "primitive_indices": indices,
                                    "primitive_ids": [self.geometry.primitive_ids[index] for index in indices]})
        elif self.in_contact:
            self.events.append({**context, "kind": "exit", "episode": self.contact_episodes})
        self.in_contact = colliding
        return clearance

    def summary(self):
        return {
            "observation": "received_odometry_samples_only", "swept_collision_check": False,
            "contact_definition": "sphere intersects closed solid AABB or finite capped cylinder; tangency included (1e-9 m tolerance)",
            "clearance_definition": "distance from body centre to closed solid minus body radius; not signed penetration depth",
            "episode_definition": "contiguous colliding received samples in union of solids; invalid samples invalidate audit",
            "floor_policy": "unchanged frozen native observer; no added ground or boundary solids",
            "robot_radius_m": self.robot_radius_m,
            "box_count": len(self.geometry.box_bounds), "cylinder_count": len(self.geometry.cylinders),
            "primitive_count": self.geometry.primitive_count,
            "primitive_height_ranges_m": self.geometry.primitive_height_ranges_m,
            "samples": self.samples, "invalid_samples": self.invalid_samples,
            "timestamp_nonmonotonic_count": self.timestamp_nonmonotonic_count,
            "receipt_nonmonotonic_count": self.receipt_nonmonotonic_count,
            "max_header_interval_s": self.max_header_interval_s,
            "max_receipt_interval_s": self.max_receipt_interval_s, "max_pose_step_m": self.max_pose_step_m,
            "contact_samples": self.contact_samples, "contact_episodes": self.contact_episodes,
            "in_contact_at_end": self.in_contact, "min_clearance_m": self.min_clearance_m,
            "min_context": self.min_context, "events": self.events,
            "audit_valid": bool(self.samples > 0 and self.invalid_samples == 0
                                and self.timestamp_nonmonotonic_count == 0 and self.receipt_nonmonotonic_count == 0),
        }
