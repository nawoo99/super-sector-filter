# Why the sector filter collides: SUPER's FoV-aware safety is disabled in our config

Reading the SUPER paper (Ren et al., *Sci. Robot.* 10, eado6187, 2025) against our config
resolves *why* the sector filter produces collisions — and reframes the whole contribution.

## What the SUPER paper actually reports

- **SUPER never collides.** In 1080 simulated flights (varying speed/density): **0 collisions,
  "perfect safe rate."** Success 99.63%; the 0.37% were **"Unfinished"** (planner failed to
  return a trajectory within 30 s = a *safe stop*, not a crash). Real world: **100%** across 8
  forest trials at up to 20 m/s.
- Baselines DO collide: Faster 12.78%, Bubble 31.20%, Raptor 38.33%.

## How SUPER guarantees safety (two-trajectory + FoV-aware known-free)

Each 10 Hz replan makes two trajectories:
- **exploratory** (known + unknown space, treats unknown as free — for speed), and
- **backup** (entirely in **known-free** space, ends at zero speed).

The **committed** trajectory = known-free part + backup. Paper: *"if the replan fails, the MAV
executes the last committed trajectory. Given that it remains in known-free space, executing it
ensures collision avoidance… even at planning failure."* → **SUPER's failure = "stop," never
"collide."**

Crucially, SUPER is **FoV-aware**: it warns that prior methods *"assume unknown regions caused by
occlusions or limited sensor FOV are free… posing a risk of colliding with hidden obstacles"* —
the exact thing it prevents by intersecting the backup corridor with the **LiDAR FoV** (Fig. 8C-iii)
so FoV-excluded space stays **unknown**, not free.

## Our config DISABLES every FoV/known-free safety feature

`super_planner/config/static_gazebo.yaml` + `super_core` code:

| flag | value | effect (code) |
|------|:-----:|---------------|
| `raycasting.enable` | **false** | map keeps only OCCUPIED; *all non-occupied = UNKNOWN* (no free-space carving) |
| `frontend_in_known_free` | **false** | `super_planner.cpp:1130` → `UNKNOWN_AS_FREE`: planner treats UNKNOWN cells as FREE/traversable |
| `use_fov_cut` | **false** | `super_planner.cpp:941` FoV corridor cut skipped |
| FOVChecker type | **OMNI** (hard-coded `super_planner.cpp:59`) | even if cut were on, FoV = 360° → no angular restriction |
| `sensing_horizon` | **-1** | `super_planner.cpp:949` sensing-horizon cut also skipped |

**Net effect: any direction with no LiDAR points — including everything the ±60° sector filter
removes — is treated as FREE space that SUPER confidently plans and flies through.** When a real
obstacle sits there but was filtered out (the blind legs of the fixed-yaw runs), SUPER plans a
straight path through it → **collision.**

This is precisely the "optimistic FoV → hidden-obstacle collision" failure SUPER was built to
prevent — **but the prevention is turned off in this config** (these were disabled during earlier
tuning to avoid conservative stalls in the constrained perimeter-loop setup).

## Consequence: the "sector safety cost" is not fundamental — it's a bypassed guarantee

- With SUPER's FoV-awareness **on**, the sector filter should make the drone **conservative**
  (won't commit into filtered = unknown directions → slows / backs up), **NOT crash**. The cost
  of filtering would show up as *reduced speed*, which is exactly SUPER's safety-vs-speed axis.
- Our `[2,2,2]` fixed-yaw collisions come from FoV-awareness being **off** (unknown-as-free), so
  the filtered directions read as free and the committed trajectory drives through them.

## Two aligned fixes

1. **Restore FoV-awareness (SUPER-correct).** Enable `use_fov_cut: true`, give the FoV checker the
   **±60° sector geometry** (needs a non-OMNI `FOVType` + planes — a small code change, not just
   config), and/or `frontend_in_known_free: true` so UNKNOWN is treated as occupied. → the sector
   filter becomes **safe but conservative** (SUPER slows/stops toward unsensed space). Needs
   re-validation (may reintroduce stalls in the tight loop).
2. **Adaptive (velocity-aligned / trigger).** Point the ±60° FoV where the drone is *going* so
   known-free extends along the motion → keep speed **and** safety. The velocity-aligned sector
   already does this continuously; a discrete version fits the trigger design below.

## Trigger design — the user's instinct, now rigorous

Earlier I argued "replan-failure can't catch the blindspot because it's a *silent* collision."
That is true **only in the current unknown-as-free config**. With FoV-awareness restored
(unknown = unknown), the blindspot stops being silent: wanting to go into a filtered = unknown
direction means SUPER **cannot build a known-free committed trajectory there → it backs
up / the replan can't make progress.** *That* is the trigger — "I want to go where I can't see" —
and it is exactly the user's "path lost / needs replan" idea. So:

- **Default:** sector (±60°, keeps the ~64% raycast savings).
- **Precondition:** filtered/unsensed = **unknown**, not free (restore FoV-awareness).
- **Trigger:** committed trajectory can't progress toward the goal because the goal direction is
  unknown (backup engaged / replan fails) → **expand the FoV toward the goal/velocity**, then
  revert once known-free is re-established.

## References
SUPER: Ren, Zhu, Lu, Cai, Yin, Kong, Lin, Chen, Zhang, "Safety-assured high-speed navigation for
MAVs," *Sci. Robot.* 10, eado6187 (2025). Code: github.com/hku-mars/SUPER.
