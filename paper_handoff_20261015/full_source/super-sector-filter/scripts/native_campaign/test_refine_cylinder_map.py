import pytest

import cylinder_map_search as search
from refine_cylinder_map import trim_baffle_tips


def test_trim_only_six_inner_tips_on_fourth_leg():
    original, paths = search.loop_baffles(.4, 5., 2.8)
    original = [search.geometry.Cylinder(30., 30., .4, "background"), *original]
    kept, removed = trim_baffle_tips(original, [4])
    assert len(kept) == len(original)-6
    assert {(round(r["cylinder"][0], 2), round(r["cylinder"][1], 2)) for r in removed} == {
        (-14., -25.2), (-9., -22.8), (-4., -25.2), (1., -22.8), (6., -25.2), (11., -22.8)}
    indices = {r["parent_index"] for r in removed}
    assert kept == [c for i, c in enumerate(original) if i not in indices]
    assert kept[0] == original[0]
    for path in paths:
        assert search.clearance(path, kept) >= search.clearance(path, original)-1e-9


def test_tip_trimming_rejects_repeat_or_invalid_leg():
    original, _ = search.loop_baffles(.4, 5., 2.8)
    kept, _ = trim_baffle_tips(original, [4])
    with pytest.raises(ValueError, match="already trimmed"):
        trim_baffle_tips(kept, [4])
    for legs in ([], [0], [6], [4, 4]):
        with pytest.raises(ValueError):
            trim_baffle_tips(original, legs)


def test_all_legs_can_be_trimmed_without_mutating_parent():
    original, _ = search.loop_baffles(.4, 5., 2.8)
    before = list(original)
    kept, removed = trim_baffle_tips(original, [1, 2, 3, 4, 5], 2)
    assert len(removed) == 48
    assert len(kept) == len(original)-48
    assert original == before
