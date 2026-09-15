import math
import pytest
from add_cylinder_background import perimeter_background, heading_proxy
from cylinder_map_search import geometry


def test_perimeter_unique_disjoint_and_preserves_parent():
    original = [geometry.Cylinder(0,0,.4,"background")]
    combined,added,skipped = perimeter_background(original)
    assert len(added)==128 and not skipped
    assert combined[:len(original)]==original
    assert len({c[:2] for c in added})==128
    assert all(max(abs(c.x),abs(c.y))==32 for c in added)
    assert min(geometry.surface_gap(a,b) for i,a in enumerate(combined) for b in combined[i+1:])>=.2


def test_conflicting_parent_retained_added_post_skipped():
    original=[geometry.Cylinder(32,32,.4,"background")]
    combined,added,skipped=perimeter_background(original)
    assert combined[0]==original[0] and [32.,32.] in skipped
    assert len(added)==127 and len(combined)==128


def test_added_posts_keep_nominal_loop_clear():
    _,added,_=perimeter_background([])
    assert min(geometry.route_surface_distance(c) for c in added)>=7.59


def test_proxy_explicitly_not_renderer_proof():
    result=heading_proxy([geometry.Cylinder(1,0,.4)],(0,0))
    assert result['minimum_center_count']==0
    assert result['maximum_center_count']==1
    assert result['sensor_returns_verified'] is False


@pytest.mark.parametrize('args',[(0,2,.4),(32,0,.4),(32,2,-1),(32,3,.4),(math.inf,2,.4)])
def test_invalid_perimeter(args):
    with pytest.raises(ValueError): perimeter_background([], *args)
