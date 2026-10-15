# Seed12/13 dynamic blind-sector scenarios

## Purpose

Seed12 and seed13 isolate the short interval in which body yaw and horizontal
velocity differ by more than the 60 degree sector half-angle. They are opt-in
safety diagnostics, not part of the seed1..11 efficiency campaign.

Both maps answer two questions:

1. Does a body-aligned sector delay insertion of an obstacle that is already
   visible to a velocity-aligned sector?
2. Is that delay long enough to produce a repeatable collision difference?

The first question is measured directly. Collision remains a secondary,
threshold-sensitive outcome.

## Setup

- Each PCD contains eight static radius-0.20 m cylinders that force a
  repeatable high-curvature turn. Seed13 keeps the same radii and corner
  offsets, but reflects each obstacle pair across that corner's radial
  diagonal so it occupies the opposite side of the turn.
- Both maps fly the same `loop24.txt` mission and score its first two waypoints.
- `native_seed12_scenario.py` sits before the filter for either map:

  `/cloud_registered -> /cloud_seed12 -> /cloud_sector`

- At 100 Hz odometry, the injector waits for:
  - speed of at least 2.0 m/s;
  - absolute yaw/velocity-yaw mismatch of at least 60 degrees;
  - a 0.7 s PVAJ trajectory prediction 0.6--2.5 m away;
  - fully adaptive-visible and body-sector-hidden geometry for 0.02 s.
- The rough trap consists of three radius-0.25 m cylinders on the predicted
  travel ray. Their center offsets from the prediction are 0.20, 0.55, and
  0.90 m.
- Trap points carry intensity `12012`. If needed, the ray is shifted by at
  most 25 degrees toward the blind side; the shift is recorded per run.

## Run

Operational comparison. `velocity` is the exact velocity-aligned-only ablation;
the current hybrid `adaptive` uses the same alignment and should not open its
stall branch in this high-speed scenario:

```bash
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
cd /root/super-sector-filter
python3 scripts/native_campaign/native_campaign.py \
  --maps seed12 seed13 --modes sector velocity adaptive --runs 5 \
  --out results/seed12_seed13_operational.csv
```

Matched-prefix control, where both modes use the body sector until the tagged
trap's first cloud frame:

```bash
SEED12_MATCHED_PREFIX=1 SEED13_MATCHED_PREFIX=1 \
python3 scripts/native_campaign/native_campaign.py \
  --maps seed12 seed13 --modes sector velocity adaptive --runs 5 \
  --out results/seed12_seed13_matched_prefix.csv
```

Visual runs:

```bash
bash scripts/watch_native.sh sector seed12
bash scripts/watch_native.sh velocity seed12
bash scripts/watch_native.sh adaptive seed12
bash scripts/watch_native.sh sector seed13
bash scripts/watch_native.sh velocity seed13
bash scripts/watch_native.sh adaptive seed13
```

Per-run diagnostics are written under `/tmp/native_campaign/`:

- `*.scenario_event.json`: trigger pose, prediction, trap centers, and angles;
- `*.scenario_trace.csv`: 100 Hz yaw, velocity yaw, and PVAJ geometry;
- `*.filt_event.json`: first raw and first kept trap timestamps;
- `*.json`: mission, trap collision, and clearance metrics.

The initial results below predate the hybrid state machine: their `adaptive`
label means the implementation now exposed as `velocity`. Do not pool those
rows with new hybrid-adaptive rows without recording that version difference.

## Initial validation

The earlier single-cylinder seed12 smoke in
`results/native_seed12_operational_smoke.csv` produced:

| mode | first-keep delay | mission | trap events | trap clearance |
|---|---:|---|---:|---:|
| sector | 95.3 ms | failed at waypoint 1/2 | 2 | -0.158 m |
| adaptive | 0.8 ms | reached waypoint 2/2 | 1 | -0.174 m |

At first raw input, the trap center was about 80--82 degrees from body yaw and
within 9 degrees of velocity yaw. This validated the intended visibility
split, but not a stable binary collision separation. The current three-post
trap deliberately broadens the interaction region; repeated paired runs are
still required before interpreting collision rate or clearance.

This also explains the original static-map result: with a 15 m sensing horizon,
persistent occupancy inserts an obstacle several seconds before the brief
mismatch interval. These scenarios remove that look-ahead by spawning the trap
during the mismatch itself.
