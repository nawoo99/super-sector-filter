#!/usr/bin/env python3
"""Read-only 2-D connectivity sensitivity check for Forest Full run 97036.

This is not a replay of the live ROG-Map, CIRI, or MINCO state. It tests only
whether the logged temporary XY route blockers disconnect the stop pose from
the next waypoint in the known static-cylinder geometry.
"""

import json
import math
from collections import deque
from pathlib import Path


GEOMETRY = Path(
    "/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/pcd/seed_maps/"
    "forest_cluster_f01_geometry.json"
)
START = (8.6753022, 18.9734347)
GOAL = (24.025, 22.025)
ZONES = ((7.757, 18.368, 0.8), (7.633, 19.324, 0.8))


def check(resolution, extra_clearance, zones, cylinders, directions):
    # Anchor the grid on the observed stop so the start point is not rounded
    # into an adjacent obstacle or temporary zone.
    sx = math.ceil((START[0] + 26.0) / resolution)
    sy = math.ceil((START[1] + 26.0) / resolution)
    x0 = START[0] - sx * resolution
    y0 = START[1] - sy * resolution
    nx = math.floor((26.0 - x0) / resolution) + 1
    ny = math.floor((26.0 - y0) / resolution) + 1
    start = (sx, sy)
    goal = (
        round((GOAL[0] - x0) / resolution),
        round((GOAL[1] - y0) / resolution),
    )

    blocked = bytearray(nx * ny)
    for trunk in cylinders:
        cx, cy = trunk["x"], trunk["y"]
        r = trunk["r"] + extra_clearance
        left = max(0, math.ceil((cx - r - x0) / resolution))
        right = min(nx - 1, math.floor((cx + r - x0) / resolution))
        bottom = max(0, math.ceil((cy - r - y0) / resolution))
        top = min(ny - 1, math.floor((cy + r - y0) / resolution))
        r2 = r * r
        for iy in range(bottom, top + 1):
            y = y0 + iy * resolution
            for ix in range(left, right + 1):
                x = x0 + ix * resolution
                if (x - cx) ** 2 + (y - cy) ** 2 < r2:
                    blocked[iy * nx + ix] = 1

    start_id = start[1] * nx + start[0]
    goal_id = goal[1] * nx + goal[0]
    assert not blocked[start_id], "Observed stop lies inside static inflated geometry"
    assert not blocked[goal_id], "Next waypoint lies inside static inflated geometry"

    seen = bytearray(nx * ny)
    seen[start_id] = 1
    queue = deque([(start[0], start[1], 0)])
    visited = 0
    goal_steps = None
    axial_moves = ((-1, 0), (0, -1), (0, 1), (1, 0))
    diagonal_moves = ((-1, -1), (-1, 1), (1, -1), (1, 1))
    # Eight-way is deliberately permissive (corner cutting allowed); four-way
    # is a separate conservative check for no-zone connectivity.
    moves = axial_moves if directions == 4 else axial_moves + diagonal_moves
    while queue:
        ix, iy, steps = queue.popleft()
        visited += 1
        if iy * nx + ix == goal_id:
            goal_steps = steps
            break
        current_x = x0 + ix * resolution
        current_y = y0 + iy * resolution
        for dx, dy in moves:
            jx, jy = ix + dx, iy + dy
            if jx < 0 or jx >= nx or jy < 0 or jy >= ny:
                continue
            jid = jy * nx + jx
            if seen[jid] or blocked[jid]:
                continue
            x = x0 + jx * resolution
            y = y0 + jy * resolution
            excluded = False
            for zx, zy, radius in zones:
                current_d = math.hypot(current_x - zx, current_y - zy)
                neighbor_d = math.hypot(x - zx, y - zy)
                # Match the start-inside-cylinder outward-only rule from
                # super_planner/src/super_core/astar.cpp.
                if neighbor_d < radius and (
                    current_d >= radius or
                    neighbor_d <= current_d + 0.25 * resolution
                ):
                    excluded = True
                    break
            if not excluded:
                seen[jid] = 1
                queue.append((jx, jy, steps + 1))

    return {
        "resolution_m": resolution,
        "extra_clearance_m": extra_clearance,
        "zones": len(zones),
        "directions": directions,
        "connected": goal_steps is not None,
        "goal_steps": goal_steps,
        "visited_until_goal_or_exhaustion": visited,
        "start_zone_distances_m": [
            round(math.hypot(START[0] - zx, START[1] - zy), 4)
            for zx, zy, _ in zones
        ],
    }


def main():
    cylinders = json.loads(GEOMETRY.read_text())["cylinders"]
    results = []
    for resolution in (0.1, 0.2):
        for clearance in (0.3, 0.4):
            for directions in (4, 8):
                for zones in ((), ZONES[:1], ZONES[1:], ZONES):
                    results.append(check(
                        resolution, clearance, zones, cylinders, directions
                    ))
    assert all(row["connected"] for row in results if row["zones"] == 0)
    assert all(not row["connected"] for row in results if row["zones"] == 2)
    assert all(row["connected"] for row in results
               if row["zones"] == 1 and row["directions"] == 8)
    print(json.dumps({"map": "forest_cluster_f01", "run": 97036,
                      "cylinder_count": len(cylinders),
                      "start_xy_m": START, "next_goal_xy_m": GOAL,
                      "zones": ZONES, "results": results}, indent=2))


if __name__ == "__main__":
    main()
