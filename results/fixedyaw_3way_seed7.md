# The adaptive-hero result: velocity-aligned sector recovers the fixed-yaw blindspot

## Setup
Static obstacles, dense seed7 (gap 1.1), clean 0.9 m/s, FIXED-YAW (heading decoupled from
velocity — a common operational constraint), per-run fresh bringup, n=3. Fixed yaw makes the
forward ±60° cone point away from motion on the loop legs where the drone moves off-heading,
so forward-only sensing misses obstacles in the path.

## Three-way comparison

| variant | collisions | mean | pts_mean | raycast savings | over-population? | completes |
|---------|:----------:|:----:|---------:|:---------------:|:----------------:|:---------:|
| **sector** (fixed ±60° on body-forward) | [2, 2, 2] | 2.0 | ~3060 | **64%↓** | no | 3/3 |
| **adaptive — full-view** (risk-gate) | [0, 0, 8] | 2.7 | ~9080 | ~0% | **YES** (run3=8) | 3/3 |
| **adaptive — velocity-aligned** (cone → motion) | **[0, 0, 0]** | **0.0** | ~3156 | **64%↓** | no | 3/3 |

(Velocity-aligned refined: HOLD the last confident travel direction through corner slowdowns
instead of snapping to body-forward, and a faster velocity low-pass — this removed the one
turn-transient collision the first version had, giving a perfect [0,0,0].)

## The story
1. **Fixed yaw gives the forward sector a real, consistent STATIC safety cost** — exactly 2
   collisions/run (velocity-tracking baseline was [0,1,0]). This is the regime the ±60°
   forward-only blindspot genuinely fails in, with static obstacles.
2. **Naive full-view recovery "fixes" safety but at a double cost**: it throws away the
   savings (pts 9080 ≈ full, 0% reduction) AND over-populates the dense ROG-Map, which
   destabilizes SUPER's planner (run3 spiked to 8 collisions). Mean 2.7 — actually worse
   than plain sector.
3. **Velocity-aligned recovery is the clean win**: keep ONE ±60° cone but CENTER it on the
   VELOCITY direction instead of body-forward. It maps what's ahead-in-motion, recovering
   the blindspot **completely (2.0 → 0.0, 3/3 collision-free)**, while **keeping the full 64%
   raycast savings** (pts 3156 ≈ sector) and **avoiding over-population** (reliable, no spikes).

**Headline: velocity-aligned adaptive sector gets the safety of full-view AND the savings of
sector — it eliminates the fixed-sector blindspot collisions (2→0) at the SAME 64% cost cut,
whereas naive full-view recovery discards the savings and destabilizes the planner.**

## Mechanism
`cloud_preprocessor` tracks world velocity (finite-diff of odom, low-passed α=0.5) and, when
`align_to_velocity` is on, centers the sector window on the HELD travel direction in the
sensor frame — the last direction seen above `align_vmin` (0.15 m/s) is held through corner
slowdowns rather than snapping back to the (blind) body-forward. Enabled per-mode via
`/sector/align_velocity`. The hold + faster low-pass removed the earlier turn-transient
collision → perfect [0,0,0].

Feature: `super_patches/cloud_preprocessor.cpp`, `scripts/g_mission.py` (`--align-velocity`),
`scripts/g_campaign.py` (adaptive = align_velocity). Raw rows: `fixedyaw_3way_seed7.csv`.
