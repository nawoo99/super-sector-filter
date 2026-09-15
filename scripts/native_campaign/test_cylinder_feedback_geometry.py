import math
import pytest
import cylinder_feedback_geometry as f


def test_background_adds_actual_cylinders_preserving_origin_and_nominal_route():
    cs,added=f.add_observability([])
    assert len(added)>8 and cs==added
    assert all(c.role=='origin_background' for c in cs)
    assert min(f.search.geometry.route_surface_distance(c) for c in cs)>=1.5
    assert min(math.hypot(c.x,c.y)-c.radius for c in cs)>=3
    again,extra=f.add_observability(cs)
    assert again==cs and not extra


def test_escape_preserves_background_and_removes_only_nearby_structure():
    C=f.search.geometry.Cylinder
    cs=[C(0,0,.4,'loop_rail'),C(0,1,.4,'origin_background'),C(10,0,.4,'loop_baffle')]
    kept,removed=f.open_escape(cs,(0,0),4)
    assert removed==cs[:1] and kept==cs[1:]


def test_hardening_nonidentical_and_keeps_background():
    C=f.search.geometry.Cylinder;original=[C(32,0,.4,'perimeter_background')]
    a,_=f.harden(original,1);b,_=f.harden(original,2)
    assert a!=b and a[0]==b[0]==original[0]
    assert all(f.search.geometry.surface_gap(x,y)>=.02-1e-8 for i,x in enumerate(a) for y in a[i+1:])


def test_invalid_action_refused():
    with pytest.raises(ValueError):f.transform([],dict(action='change_planner'))
