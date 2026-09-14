import numpy as np
from cylinder_solid_observer import solid_clearances


def test_interior_is_collision_even_when_surface_point_distance_is_positive():
    columns=np.array([[7.989,10.233,.75]])
    assert solid_clearances((8.051,10.45,1.75),columns)[0] < -.7
    assert solid_clearances((8.05,9.85,1.15),columns)[0] < -.55


def test_sides_caps_rims_and_far_points():
    columns=np.array([[0.,0.,1.]])
    assert np.isclose(solid_clearances((1.3,0,1.5),columns)[0],.1)
    assert np.isclose(solid_clearances((0,0,3.1),columns)[0],-.1)
    assert np.isclose(solid_clearances((1.3,0,3.4),columns)[0],.3)
    assert solid_clearances((0,0,1.5),columns)[0] < 0
    assert solid_clearances((0,0,3.3),columns)[0] > 0
