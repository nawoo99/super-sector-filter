from pathlib import Path

import numpy as np
import pytest

from ascii_pcd_xyz import load_ascii_pcd_xyz


def write_pcd(path, fields, rows, count=None):
    field_count = len(fields)
    counts = count or [1] * field_count
    columns = sum(counts)
    lines = [
        "# test fixture",
        "VERSION 0.7",
        "FIELDS " + " ".join(fields),
        "SIZE " + " ".join(["4"] * field_count),
        "TYPE " + " ".join(["F"] * field_count),
        "COUNT " + " ".join(str(value) for value in counts),
        f"WIDTH {len(rows)}",
        "HEIGHT 1",
        f"POINTS {len(rows)}",
        "DATA ascii",
    ]
    assert all(len(row) == columns for row in rows)
    lines.extend(" ".join(str(value) for value in row) for row in rows)
    Path(path).write_text("\n".join(lines) + "\n")


def test_loads_xyz_pcd(tmp_path):
    path = tmp_path / "xyz.pcd"
    write_pcd(path, ["x", "y", "z"], [[1, 2, 3], [4, 5, 6]])

    np.testing.assert_array_equal(
        load_ascii_pcd_xyz(path),
        np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.float32),
    )


def test_selects_xyz_from_xyzi_and_reordered_fields(tmp_path):
    path = tmp_path / "xyzi.pcd"
    write_pcd(
        path,
        ["intensity", "z", "x", "y"],
        [[9, 3, 1, 2], [8, 6, 4, 5]],
    )

    np.testing.assert_array_equal(
        load_ascii_pcd_xyz(path),
        np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.float32),
    )


def test_respects_multicount_fields(tmp_path):
    path = tmp_path / "normal.pcd"
    write_pcd(
        path,
        ["normal", "x", "y", "z"],
        [[0.1, 0.2, 0.3, 1, 2, 3]],
        count=[3, 1, 1, 1],
    )

    np.testing.assert_array_equal(
        load_ascii_pcd_xyz(path),
        np.asarray([[1, 2, 3]], dtype=np.float32),
    )


def test_rejects_missing_coordinate_field(tmp_path):
    path = tmp_path / "invalid.pcd"
    write_pcd(path, ["x", "y", "intensity"], [[1, 2, 9]])

    with pytest.raises(ValueError, match="missing coordinate fields z"):
        load_ascii_pcd_xyz(path)
