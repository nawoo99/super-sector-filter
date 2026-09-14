"""Small fail-closed loader for XYZ columns in an ASCII PCD file."""

from pathlib import Path

import numpy as np


def load_ascii_pcd_xyz(path):
    """Return finite XYZ rows while respecting PCD FIELDS/COUNT columns."""
    header = {}
    source = Path(path)
    with source.open() as stream:
        while True:
            line = stream.readline()
            if not line:
                raise ValueError(f"PCD has no DATA header: {source}")
            tokens = line.strip().split()
            if not tokens or tokens[0].startswith("#"):
                continue
            key = tokens[0].upper()
            values = tokens[1:]
            if key == "DATA":
                if [value.lower() for value in values] != ["ascii"]:
                    raise ValueError(f"only ASCII PCD is supported: {source}")
                break
            header[key] = values

        fields = [field.lower() for field in header.get("FIELDS", [])]
        if not fields:
            raise ValueError(f"PCD has no FIELDS header: {source}")
        count_tokens = header.get("COUNT")
        if count_tokens is None:
            counts = [1] * len(fields)
        else:
            if len(count_tokens) != len(fields):
                raise ValueError(f"PCD FIELDS/COUNT length mismatch: {source}")
            try:
                counts = [int(value) for value in count_tokens]
            except ValueError as error:
                raise ValueError(f"PCD has a non-integer COUNT: {source}") from error
            if any(count <= 0 for count in counts):
                raise ValueError(f"PCD COUNT values must be positive: {source}")

        offsets = {}
        column = 0
        for field, count in zip(fields, counts):
            if field in offsets:
                raise ValueError(f"PCD has duplicate field {field!r}: {source}")
            offsets[field] = (column, count)
            column += count

        missing = [axis for axis in ("x", "y", "z") if axis not in offsets]
        if missing:
            raise ValueError(
                f"PCD is missing coordinate fields {', '.join(missing)}: {source}"
            )
        if any(offsets[axis][1] != 1 for axis in ("x", "y", "z")):
            raise ValueError(f"PCD x/y/z fields must each have COUNT 1: {source}")
        xyz_columns = tuple(offsets[axis][0] for axis in ("x", "y", "z"))

        try:
            points = np.loadtxt(
                stream,
                dtype=np.float32,
                usecols=xyz_columns,
                ndmin=2,
            )
        except (IndexError, ValueError) as error:
            raise ValueError(f"invalid ASCII PCD rows: {source}: {error}") from error

    if points.ndim != 2 or points.shape[1] != 3 or not len(points):
        raise ValueError(f"PCD contains no XYZ points: {source}")
    return points[np.isfinite(points).all(axis=1)]

