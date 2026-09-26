# Follow-up: occupied-voxel volume versus center-point body checks

Date: 2026-09-26. Status: read-only mathematical/source review; **not implemented in guard-v2**.

This is a remaining safety-model caveat, not an additional fixed-v2 claim or an expansion of the v2 cohort. The examples below establish a mismatch with a **conservative closed occupied-voxel-volume contract**. They do not identify the cause of any recorded v1 contact, and they are not observed v2 flight failures. No ROS flight, production edit, or compilation was performed for this review.

## Observed source contract

The `physical_body_occupied` lambda in [super_planner.cpp:547](/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp:547) queries raw `OCCUPIED` cells with an axis-aligned search extent `robot_r + resolution/2`, then accepts a collision only when the returned **voxel-center distance** is at most `robot_r + 1e-9`; see [super_planner.cpp:585](/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp:585). Its initial-footprint mask and egress distances also use voxel centers. The surrounding comment intentionally describes a center-point contract; it should not be read as proof of solid-volume clearance or equality with the unquantized static-PCD oracle.

Snapshot indexing is `floor(position/resolution)` and the returned center is `(index + 0.5)*resolution`; see [rog_map.cpp:158](/root/super_ws/src/SUPER/rog_map/src/rog_map/rog_map.cpp:158). Both ordinary snapshot loops and the fast occupied scan enumerate from `min_id+1` through `max_id-1`, excluding both boundary index layers; see [rog_map.cpp:553](/root/super_ws/src/SUPER/rog_map/src/rog_map/rog_map.cpp:553) and [rog_map.cpp:644](/root/super_ws/src/SUPER/rog_map/src/rog_map/rog_map.cpp:644). The non-snapshot implementation uses the same exclusive bounds in [prob_map.cpp:503](/root/super_ws/src/SUPER/rog_map/src/rog_map/prob_map.cpp:503).

`boundBoxByLocalMap` clips physical search bounds to local-map outer cell centers, rather than outer cell faces; see [rog_map.cpp:519](/root/super_ws/src/SUPER/rog_map/src/rog_map/rog_map.cpp:519) and [sliding_map.cpp:87](/root/super_ws/src/SUPER/rog_map/src/rog_map/sliding_map.cpp:87). Consequently, padding an existing query alone cannot recover clipped outermost index layers.

## Concrete arithmetic

Assume raw resolution `s=0.05 m`, spherical body radius `r=0.2 m`, the stated voxel is already `OCCUPIED` in the queried snapshot, the examples are away from local-map/vertical boundaries, and no initial-footprint masking is authorized. Voxel index `i` represents the closed cube `[i*s,(i+1)*s]` in each axis **for this proposed conservative volume interpretation**. The existing search extent is `0.225 m`.

| Case | Body center `p` | Occupied voxel index | Voxel center `c` | Center distance | Distance to closed cube | Existing behavior |
| --- | --- | --- | --- | ---: | ---: | --- |
| Edge overlap | `(0.025,0.025,1.525)` | `(3,3,30)` | `(0.175,0.175,1.525)` | `0.212132034356` | `0.176776695297` | Returned, then classified noncontact |
| Upper-face query omission | `(0.01,0.025,1.525)` | `(4,0,30)` | `(0.225,0.025,1.525)` | `0.215` | `0.19` | Not returned |
| Lower-face query omission | `(-0.01,0.025,1.525)` | `(-5,0,30)` | `(-0.225,0.025,1.525)` | `0.215` | `0.19` | Not returned |
| Corner overlap | `(0.05,0.05,1.55)` | `(3,3,33)` | `(0.175,0.175,1.675)` | `0.216506350946` | `0.173205080757` | Returned, then classified noncontact |
| Exact face tangency | `(0,0.025,1.525)` | `(4,0,30)` | `(0.225,0.025,1.525)` | `0.225` | `0.2` | Not returned |

For the edge case, the cube is `[0.15,0.20] x [0.15,0.20] x [1.50,1.55]`. Center distance is `sqrt(0.15^2 + 0.15^2)`, whereas distance to its closest edge is `sqrt(0.125^2 + 0.125^2)`. Thus the raw voxel is returned but its intersecting volume is ignored by the point-center predicate.

For the upper-face omission, the closest cube face is `x=0.20`, only `0.19 m` from the body center. The search maximum is `x=0.01+0.225=0.235`; its index is `floor(0.235/0.05)=4`, and the `i<4` loop excludes exactly the required occupied cell. On the negative side, `floor((-0.01-0.225)/0.05)=-5`, and the `min_id+1` start excludes index `-5`. These omissions would remain even if only the subsequent distance predicate were changed.

For the corner example, the three center differences are `0.125`, giving `sqrt(3)*0.125`; the three nearest-cube differences are `0.1`, giving `sqrt(3)*0.1`. Arithmetic was checked with an in-memory Python calculation reproducing the documented floor-index loop bounds; no map or flight fixture was executed.

## Minimal mathematical alternative, if separately authorized later

For a closed cube with center `c` and half-side `h=s/2`, sphere/cube intersection is exactly:

```text
delta = max(abs(p-c)-h, 0)          # componentwise
contact iff dot(delta,delta) <= (r+epsilon)^2
```

Candidate enumeration must include every potentially intersecting cube. With `R=r+epsilon`, an inclusive index interval in each axis is:

```text
first = ceil((p-R)/s)-1
last  = floor((p+R)/s)
```

The lower adjacent cell is intentionally included when its upper face exactly touches the sphere's bounding box. The final sphere/cube predicate removes bounding-box-only candidates. Numerical boundary handling must be explicit and tested. Use the same captured snapshot for resolution, bounds, occupied bits, and enumeration, and clip against valid **indices**, not center-clipped floating bounds followed by exclusive loops. A body extending beyond known local-map coverage requires its own explicit unknown/out-of-map policy; empty query output is not a safety proof.

This is not a suggestion to increase `robot_r` or relax thresholds. An isotropic center-radius expansion by a voxel half-diagonal is conservative but is not the exact sphere/AABB predicate. Changing to voxel-volume semantics requires the initial-footprint membership, retained egress cells, and penetration/non-worsening metric to use a consistent geometric interpretation. Changing only the hard predicate can create inconsistent or permanently blocked escape behavior; authorized egress exceptions must remain explicit.

Suggested bounded tests are the five cases above; coordinate-sign/permutation variants; face, edge, and corner tangency plus just-separated controls; body center inside a voxel; occupied outermost map cells; identical fast/ordinary results on one snapshot; and egress disabled versus explicitly authorized with monotone non-worsening contact geometry.

## Limits relative to analytic obstacles and recorded flights

- An occupied voxel is an estimated map cell, not evidence that its entire cube is physical solid. Treating that cube as solid is conservative relative to the observations that produced it and can reject physically clear states.
- Conversely, a sampled obstacle surface inside a cell can intersect the sphere even when that cell's center does not. Unquantized PCD points, occupied voxel centers, occupied-cell volumes, and analytic closed cylinders/boxes are different collision models; their distances must not be substituted for one another.
- These examples assume the required occupancy is actually present. A voxel-volume predicate cannot recover missing sensor returns, filtered observations, cleared occupancy, or stale snapshots.
- They do not prove that the full current validator returns `SAFE`: other inflated-grid, unknown-space, vertical-boundary, trajectory, or egress rules may reject a particular trajectory. They isolate concrete deficiencies of the physical-body helper **if** its intended contract were closed occupied-cell volume.
- They do not establish continuous-time safety between checked trajectory samples or resolve the original recorded-contact causality question. No production or cohort changes are authorized by this note.

## Source identity at inspection

Paths below are relative to `/root/super_ws/src/SUPER`.

| Source | SHA-256 |
| --- | --- |
| `super_planner/src/super_core/super_planner.cpp` | `2a7127726488cc0c965edeb0e38fec9b2a4faf2770f45d6e71dc3684e4215d6b` |
| `rog_map/src/rog_map/rog_map.cpp` | `ad0f8e454075fa08409b939c1078f1e344387cd336186831c1c673f4e4d6cc77` |
| `rog_map/src/rog_map/prob_map.cpp` | `3ee0f4e6b2136ea0423313c8231acf70f056a33b3c8747b01bf11091d3d29805` |
| `rog_map/src/rog_map/sliding_map.cpp` | `72d93569357ee77ab234f4ed1e254de50a3ac8d6b2774a7775c554a6718c5eb9` |
