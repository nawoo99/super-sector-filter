from __future__ import annotations

from validate_angular_blind_turn_v3_gate import astar, inflate_cells


def test_inflation_matches_rog_spherical_xy_offsets() -> None:
    inflated = inflate_cells({(0, 0)}, 3)
    assert (3, 0) in inflated
    assert (2, 2) in inflated
    assert (3, 1) not in inflated
    assert len(inflated) == 29


def test_astar_rejects_corner_cut_and_finds_open_bypass() -> None:
    blocked = {(1, 0), (0, 1)}
    assert astar((0, 0), (1, 1), blocked, (0, 1, 0, 1)) is None
    blocked = {(1, 0)}
    path = astar((0, 0), (2, 0), blocked, (0, 2, -1, 1))
    assert path is not None
    assert (1, 0) not in path
