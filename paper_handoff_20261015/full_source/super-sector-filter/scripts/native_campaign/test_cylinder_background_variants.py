import pytest
import cylinder_background_variants as variants


def parent_fixture():
    structure,_=variants.search.loop_baffles(.4,5.,2.8)
    g=variants.search.geometry
    return [g.Cylinder(32,32,.4,'perimeter_background'),g.Cylinder(30,0,.4,'background'),*structure]


@pytest.mark.parametrize('recipe',variants.RECIPES)
def test_background_and_rails_preserved(recipe):
    parent=parent_fixture(); cs,features=variants.variant(parent,recipe)
    for role in ('background','perimeter_background','loop_rail'):
        assert [c for c in cs if c.role==role]==[c for c in parent if c.role==role]
    assert features and all(c.radius>0 for c in cs)
    assert len({c[:2] for c in cs})==len(cs)


def test_corner_posts_block_outgoing_line_but_not_waypoints():
    parent=parent_fixture(); cs,features=variants.variant(parent,variants.RECIPES[-1])
    assert cs[:len(parent)]==parent and len(features)==4
    g=variants.search.geometry
    for c,start,end in zip(features,g.LOOP_WAYPOINTS[1:5],g.LOOP_WAYPOINTS[2:6]):
        assert g.point_segment_distance(c[:2],start,end)<1e-10
        assert min(__import__('math').dist(c[:2],p)-c.radius-.2 for p in g.LOOP_WAYPOINTS)>2


def test_unknown_recipe_refused():
    with pytest.raises(ValueError): variants.variant(parent_fixture(),dict(name='not_predeclared'))
