#!/usr/bin/env python3
"""ROS-independent helpers for auditing a PolynomialTrajectory message."""

from __future__ import annotations

import math


def _position_at(message, trajectory_time_s: float) -> tuple[float, float, float]:
    piece_count = int(message.piece_num_pos)
    order = int(message.order_pos)
    columns = order + 1
    durations = tuple(float(value) for value in message.time_pos)
    expected_coefficients = piece_count * columns
    coefficient_sets = (
        tuple(float(value) for value in message.coef_pos_x),
        tuple(float(value) for value in message.coef_pos_y),
        tuple(float(value) for value in message.coef_pos_z),
    )
    if piece_count <= 0 or order < 0 or len(durations) != piece_count:
        raise ValueError("invalid polynomial dimensions")
    if any(len(values) != expected_coefficients for values in coefficient_sets):
        raise ValueError("invalid polynomial coefficient count")
    if any(not math.isfinite(value) or value <= 0.0 for value in durations):
        raise ValueError("invalid polynomial duration")

    local_time = min(max(float(trajectory_time_s), 0.0), sum(durations))
    piece = 0
    while piece + 1 < piece_count and local_time > durations[piece]:
        local_time -= durations[piece]
        piece += 1
    local_time = min(max(local_time, 0.0), durations[piece])
    base = piece * columns

    position = []
    for coefficients in coefficient_sets:
        value = 0.0
        power = 1.0
        # SUPER stores each piece from highest power to the constant term.
        for column in range(order, -1, -1):
            value += power * coefficients[base + column]
            power *= local_time
        if not math.isfinite(value):
            raise ValueError("non-finite polynomial position")
        position.append(value)
    return tuple(position)


def sample_future_positions(
    message,
    now_s: float,
    horizon_s: float = 1.0,
    sample_dt_s: float = 0.01,
) -> list[tuple[float, float, float]]:
    """Sample the same current-to-future interval used by the C++ risk worker."""

    if not math.isfinite(now_s):
        raise ValueError("now_s must be finite")
    if not math.isfinite(horizon_s) or horizon_s <= 0.0:
        raise ValueError("horizon_s must be positive and finite")
    if not math.isfinite(sample_dt_s) or sample_dt_s <= 0.0:
        raise ValueError("sample_dt_s must be positive and finite")
    start_wt = float(message.start_wt_pos)
    if not math.isfinite(start_wt):
        raise ValueError("trajectory start wall time must be finite")

    durations = tuple(float(value) for value in message.time_pos)
    if not durations:
        raise ValueError("trajectory has no pieces")
    total_duration = sum(durations)
    from_time = min(max(now_s - start_wt, 0.0), total_duration)
    to_time = min(total_duration, from_time + horizon_s)
    points = []
    trajectory_time = from_time
    while True:
        points.append(_position_at(message, trajectory_time))
        if trajectory_time >= to_time:
            break
        trajectory_time = min(to_time, trajectory_time + sample_dt_s)
    return points
