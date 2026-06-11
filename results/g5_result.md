# G5 result — field traversal + collision metric (verified run)

Clean HEADLESS run on `default_36`, sector filter ON, goal `(12, 0, 1.5)`.

| metric | value |
|--------|-------|
| takeoff | offboard-from-ground → 1.40 m |
| traverse | (0,0) → (5.18,1.33) → (9.86,0.67) → goal |
| goal reached | d = 0.50 m at (12.13, 0.06, 1.46) |
| mission time | 5.5 s (goal-sent → reached), ~12 m |
| altitude | held 1.0–1.5 m (no descent into ground) |
| **min surface clearance** | **0.29 m** (drone-center-to-pillar-surface) |
| **collisions** | **1** (debounced; sector ON, limited FoV → 1 close clip) |

Raw: `g5_traverse_fly.log` (g_fly pose trace), `g5_traverse_collision.log`
(collision_monitor). Reproduce: HEADLESS bringup, settle, then
`g_fly.py --z 1.5 --goal 12 0 1.5` with `collision_monitor.py --world default_36`.
