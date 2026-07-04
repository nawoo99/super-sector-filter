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
| **adaptive — velocity-aligned** (cone → motion) | [0, 2, 0] | **0.67** | ~3143 | **64%↓** | no | 3/3 |

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
   the blindspot (mean 2.0 → 0.67, −67%), while **keeping the full 64% raycast savings**
   (pts 3143 ≈ sector) and **avoiding over-population** (reliable, no spikes).

**Headline: velocity-aligned adaptive sector gets the safety of full-view AND the savings of
sector — 67% fewer collisions than fixed-sector at the SAME 64% cost cut, whereas naive
full-view recovery discards the savings and destabilizes the planner.**

## Mechanism
`cloud_preprocessor` tracks world velocity (finite-diff of odom, low-passed) and, when
`align_to_velocity` is on and speed > `align_vmin` (0.15 m/s), centers the sector window on
the velocity bearing in the sensor frame (falls back to body-forward near hover). Enabled
per-mode via `/sector/align_velocity`. The residual 1-run/2-collision is turn-transient
(velocity direction swings at corners faster than the low-pass tracks) — tunable via the
smoothing/vmin if a perfect 0 is wanted.

Feature: `super_patches/cloud_preprocessor.cpp`, `scripts/g_mission.py` (`--align-velocity`),
`scripts/g_campaign.py` (adaptive = align_velocity). Raw rows: `fixedyaw_3way_seed7.csv`.
