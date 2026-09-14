import numpy as np

from audit_cylinder_solid_contexts import audit


def test_only_actual_three_dimensional_contexts_are_contact_evidence():
    cylinders = np.array([[0., 0., 1.]])
    report = dict(heading_trace=[dict(position_xy_m=[0., 0.])],
                  trajectory_audit_min_context=dict(nearest_trajectory_point=[0., 0., 1.5]),
                  final_x=3., final_y=0., final_z=1.5)
    result = audit(report, cylinders, 3.)
    assert len(result["contexts"]) == 1
    assert not result["definite_contact_in_saved_pose"]
    assert not result["whole_flight_safety_certified"]
    report["static_pcd_min_context"] = dict(position=[0., 0., 1.5])
    assert audit(report, cylinders, 3.)["definite_contact_in_saved_pose"]
