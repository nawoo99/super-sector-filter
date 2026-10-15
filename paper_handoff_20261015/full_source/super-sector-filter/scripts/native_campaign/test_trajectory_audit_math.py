from types import SimpleNamespace

import pytest

from trajectory_audit_math import sample_future_positions


def trajectory(**overrides):
    values = {
        "piece_num_pos": 1,
        "order_pos": 1,
        "start_wt_pos": 10.0,
        "time_pos": [2.0],
        # x=2t+1, y=-t+3, z=1.5. Coefficients are [slope, constant].
        "coef_pos_x": [2.0, 1.0],
        "coef_pos_y": [-1.0, 3.0],
        "coef_pos_z": [0.0, 1.5],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_samples_current_to_one_second_future_interval():
    points = sample_future_positions(
        trajectory(), now_s=10.5, horizon_s=1.0, sample_dt_s=0.5
    )
    assert points == pytest.approx(
        [(2.0, 2.5, 1.5), (3.0, 2.0, 1.5), (4.0, 1.5, 1.5)]
    )


def test_crosses_piece_boundary_using_each_piece_local_time():
    message = trajectory(
        piece_num_pos=2,
        start_wt_pos=0.0,
        time_pos=[1.0, 1.0],
        coef_pos_x=[1.0, 0.0, 2.0, 1.0],
        coef_pos_y=[0.0, 0.0, 0.0, 0.0],
        coef_pos_z=[0.0, 1.5, 0.0, 1.5],
    )
    points = sample_future_positions(
        message, now_s=0.5, horizon_s=1.0, sample_dt_s=0.5
    )
    assert points == pytest.approx(
        [(0.5, 0.0, 1.5), (1.0, 0.0, 1.5), (2.0, 0.0, 1.5)]
    )


def test_rejects_malformed_coefficient_count():
    with pytest.raises(ValueError, match="coefficient count"):
        sample_future_positions(
            trajectory(coef_pos_x=[1.0]), now_s=10.0
        )
