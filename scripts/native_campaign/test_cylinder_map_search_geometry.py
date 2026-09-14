"""Geometry-only tests; no ROS or runtime planner mutations."""
import cylinder_map_search as search
import pytest


def test_all_loop_legs_have_clear_analytic_paths():
    cylinders, paths = search.loop_slalom(.4, 2., 2.4, True)
    assert len(paths) == 5
    assert [p[0] for p in paths] == list(search.geometry.LOOP_WAYPOINTS[:-1])
    assert [p[-1] for p in paths] == list(search.geometry.LOOP_WAYPOINTS[1:])
    assert all(search.clearance(path, cylinders) > .68 for path in paths)
    assert sum(c.role == "loop_slalom" for c in cylinders) == 19


def test_disjoint_rails_fix_corner_overlaps_without_moving_features():
    original, _ = search.loop_slalom(.4, 2., 2.4, False)
    disjoint, _ = search.loop_slalom(.4, 2., 2.4, True)
    gap = lambda cs: min(search.geometry.surface_gap(a, b)
                         for i, a in enumerate(cs) for b in cs[i+1:])
    assert gap(original) < 0  # Prepared F01 is rejected before flight.
    assert gap(disjoint) >= .15 - 1e-8
    assert [c for c in original if c.role == "loop_slalom"] == [
        c for c in disjoint if c.role == "loop_slalom"]


def test_short_pitch_slalom_keeps_disjoint_posts_and_all_leg_clearance():
    cylinders, paths = search.loop_slalom(.4, 1.9, 2.8, True, 3.6, 1.8)
    assert len(paths) == 5
    assert sum(c.role == "loop_slalom" for c in cylinders) == 32
    assert min(search.clearance(path, cylinders) for path in paths) >= .35
    assert min(search.geometry.surface_gap(a, b)
               for i, a in enumerate(cylinders) for b in cylinders[i+1:]) >= .15 - 1e-8


@pytest.mark.parametrize("pitch", [0., -1., float("inf"), float("nan")])
def test_invalid_slalom_pitch_rejected(pitch):
    with pytest.raises(ValueError, match="pitch"):
        search.loop_slalom(.4, 1.9, 2.8, True, pitch, 1.8)


def test_cylinder_baffles_are_static_disjoint_and_feasible_on_five_legs():
    cylinders, paths = search.loop_baffles(.4, 5., 2.8)
    assert len(paths) == 5
    assert sum(c.role == "loop_baffle" for c in cylinders) == 120
    assert min(search.clearance(path, cylinders) for path in paths) >= .35
    assert min(search.geometry.surface_gap(a, b)
               for i, a in enumerate(cylinders) for b in cylinders[i+1:]) >= .15 - 1e-8
    assert all(c.radius == .4 for c in cylinders)
    assert [(p[0], p[-1]) for p in paths] == list(zip(
        search.geometry.LOOP_WAYPOINTS, search.geometry.LOOP_WAYPOINTS[1:]))


def test_offline_forest_certificate_preserves_mission_and_clearance():
    import cylinder_forest_geometry as forest
    cylinders = [search.geometry.Cylinder(12.,12.,2.,"forest")]
    paths = forest.paths(cylinders)
    assert len(paths) == 5
    assert all(search.clearance(path,cylinders) >= .35 for path in paths)
    for path,start,end in zip(paths,search.geometry.LOOP_WAYPOINTS,search.geometry.LOOP_WAYPOINTS[1:]):
        assert path[0] == start and path[-1] == end


def test_forest_proposal_is_deterministic_disjoint_and_keeps_goal_space():
    import cylinder_forest_geometry as forest
    cylinders = forest.forest(9,.75,410)
    assert cylinders == forest.forest(9,.75,410)
    assert len(cylinders) == 410
    assert not any(search.geometry.protected_location(c) for c in cylinders)
    assert min(search.geometry.surface_gap(a,b) for i,a in enumerate(cylinders)
               for b in cylinders[i+1:]) >= .2-1e-8
