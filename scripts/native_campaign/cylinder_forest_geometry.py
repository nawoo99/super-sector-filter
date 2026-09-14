"""Cylinder-only forest proposals and offline geometric route certificates.

This A* never runs in ROS and never supplies planner waypoints. It only rejects
physically blocked map proposals before expensive flight tests.
"""
import heapq
import math
import random

import numpy as np
import gen_cylinder_only_stress as geometry


def forest(seed, radius, count, clear_pockets=()):
    source_radius = .15 + ((seed-1)//2)*.125
    source = geometry.load_source(seed, source_radius)
    result = []
    def protected(candidate):
        return (geometry.protected_location(candidate) or any(
            math.dist(candidate[:2],(x,y))-candidate.radius < clearance
            for x,y,clearance in clear_pockets))
    for item in source:
        candidate = geometry.Cylinder(item.x, item.y, radius, "forest")
        if (not protected(candidate)
                and not geometry.conflicts(candidate, result, .20)):
            result.append(candidate)
        if len(result) == count:
            return result
    rng = random.Random(0xF0120000 + seed)
    for _ in range(100000):
        if len(result) == count:
            return result
        candidate = geometry.Cylinder(rng.uniform(-31,31), rng.uniform(-31,31), radius, "forest")
        if (not protected(candidate)
                and not geometry.conflicts(candidate, result, .20)):
            result.append(candidate)
    raise ValueError("Forest placement cannot satisfy disjoint cylinders/count")


def paths(cylinders):
    step, lower, size = .1, -32., 641
    axis = lower + step*np.arange(size)
    x, y = np.meshgrid(axis, axis)
    free = np.ones((size,size), dtype=bool)
    # Every edge is <= sqrt(2)*0.1 m long. Endpoint body clearance >=0.45
    # gives segment clearance >=0.379 m by the distance Lipschitz bound.
    for c in cylinders:
        free &= (x-c.x)**2 + (y-c.y)**2 >= (c.radius+.20+.45)**2
    def cell(point):
        return (round((point[1]-lower)/step), round((point[0]-lower)/step))
    neighbors = tuple((dy,dx,math.hypot(dx,dy)) for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy)
    result = []
    for start, goal in zip(geometry.LOOP_WAYPOINTS, geometry.LOOP_WAYPOINTS[1:]):
        begin, end = cell(start), cell(goal)
        if not free[begin] or not free[end]:
            raise ValueError("Forest waypoint lacks geometric clearance")
        queue = [(math.dist(begin,end),0.,begin)]
        best, parent = {begin:0.}, {}
        while queue:
            _, cost, node = heapq.heappop(queue)
            if cost > best[node]+1e-9:
                continue
            if node == end:
                break
            for dy,dx,length in neighbors:
                nxt = (node[0]+dy,node[1]+dx)
                if not (0<=nxt[0]<size and 0<=nxt[1]<size and free[nxt]):
                    continue
                candidate = cost+length
                if candidate+1e-9 < best.get(nxt,math.inf):
                    best[nxt], parent[nxt] = candidate,node
                    heapq.heappush(queue,(candidate+math.dist(nxt,end),candidate,nxt))
        else:
            raise ValueError(f"No >=0.379 m geometric path on leg {start}->{goal}")
        chain, node = [end], end
        while node != begin:
            node = parent[node]
            chain.append(node)
        chain.reverse()
        # Compress only collinear lattice steps, preserving the exact route.
        compact = [chain[0]]
        for i in range(1,len(chain)-1):
            before = (chain[i][0]-chain[i-1][0],chain[i][1]-chain[i-1][1])
            after = (chain[i+1][0]-chain[i][0],chain[i+1][1]-chain[i][1])
            if before != after:
                compact.append(chain[i])
        compact.append(chain[-1])
        result.append([(lower+col*step,lower+row*step) for row,col in compact])
    return result
