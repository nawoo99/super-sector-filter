# Map 7 recent-hit near-field shadow n=20 and RViz path-bias analysis

Date: 2026-08-31

## Why this experiment exists

The cgroup-accounted final campaign contained one real Full-mode Map 7
contact. At 6.121 s the vehicle centre was only 0.0563 m from a static
obstacle while the simulated LiDAR blind range was 0.1 m. A short committed
tail had just passed the map-based guard because the blind local map supplied
no obstacle face. The correction under test must therefore use only recent
raw sensor hits; the static PCD remains an evaluation oracle and is never fed
to the planner.

## Implemented shadow architecture

`FsmRos2` now has a default-off recent-hit shadow path with these properties:

- Accepted raw `PointCloud2` messages are retained for a bounded 1.5 s window
  through ROG-Map's existing in-process observer. No second DDS subscription
  is created in shadow-only mode.
- A newly committed trajectory queues one latest-only job. The job records an
  as-of-enqueue cutoff, so a scan arriving after commit cannot explain the
  result.
- The worker checks the current body plus a 1.0 s trajectory tail at 0.01 s
  spacing against an exact 0.20 m observed-hit radius. It never changes a
  commit, command, brake or recovery decision.
- Accumulation, PointCloud2 conversion, spatial cropping and KD-tree queries
  happen only on the worker. The FSM callback only snapshots/enqueues.
- The raw window is first cropped to the exact AABB union of the sampled body
  spheres. This preserves every point capable of satisfying the radius test
  while discarding irrelevant far-field points.
- A no-intersection result is named `NO_HIT`, not a known-free `SAFE`
  certificate. The n=20 logs predate this semantic-only rename and therefore
  contain `status=SAFE`; the tested geometry is unchanged.

The operational profile
`static_seedmaps_guard_viability_tight_v7.yaml` is unchanged and the feature's
global default remains false. Dedicated profiles are
`static_seedmaps_guard_viability_tight_v7_nearfieldshadow.yaml` (0.20 m) and
`..._nearfieldshadow_r040.yaml` (shadow sensitivity only).

## Performance correction

The first implementation built a KD-tree from the full accumulated window:
roughly 300,000-660,000 points per job in this run, 102 completed jobs, 35
latest-only replacements, mean 154.96 ms and maximum 291.49 ms. After exact
trajectory-AABB cropping, a smoke run completed 93/93 jobs with no replacement;
mean work fell to 10.56 ms and maximum to 25.20 ms.

Across the final Map 7 n=20, the worker examined a mean 442,259 source points
but retained only 3,597 candidate-near points. Mean queue/work time was
0.046/9.979 ms, maxima 4.085/42.228 ms, and no job was replaced. A same-host
shadow-off smoke measured FSM CPU 144.44% and PSS 3,225.93 MiB versus shadow
n=20 means 145.50% and 3,289.25 MiB. This is only a one-run CPU/PSS control,
not a paired performance claim, but it rules out the earlier synchronous
shadow's planning-loop-scale regression.

## Map 7 Full results

| Campaign | Complete | Static safe | Mean time | Worst static clearance | Shadow output |
|---|---:|---:|---:|---:|---|
| r=0.20 cropped shadow n=20 | 20/20 | 20/20 | 80.463 s | +0.200003 m | 2,305 no-hit, 0 occupied, 0 skipped |
| r=0.40 sensitivity n=1 | 1/1 | 1/1 | 78.490 s | +0.267895 m | 97 no-hit, 7 occupied, 0 skipped |
| shadow-off baseline n=1 | 1/1 | 1/1 | 89.750 s | +0.250924 m | disabled |

All runs were speed-valid. The 0.20 m cohort's smallest observed raw-hit
distance was 0.2976 m. Consequently the original stochastic contact did not
recur in these 20 runs. The r=0.40 sensitivity run proves end-to-end witness
detection and proves that an `OCCUPIED` result remains non-authoritative, but
it does not prove that r=0.20 would have caught the old 0.0563 m event. That
claim remains open until an actual contact-correlated run or deterministic
replay is captured.

Raw and aggregate files:

- `results/near_field_shadow_crop_seed7_full_n20_raw_20260831.csv`
- `results/near_field_shadow_r040_seed7_full_smoke_raw_20260831.csv`
- `results/near_field_shadow_baseline_seed7_full_smoke_raw_20260831.csv`
- `results/near_field_shadow_map7_summary_20260831.csv`

## Why the RViz path hugs the left obstacle

Full sensing means that the planner receives the whole scan; it does not mean
that the optimizer maximizes bilateral clearance or follows the passage
centreline.

The retained candidate uses a nearest-corridor-face penalty only inside a
0.10 m margin. It has full weight at speed <=1.5 m/s, fades across 1.5-2.0
m/s, and is exactly zero at >=2.0 m/s. In a normal v=7 passage traversal the
cruise samples therefore receive no centring pressure. A*/JPS selects one
guide path, CIRI builds a corridor around that seed, and the back end mainly
optimizes time, dynamics and smoothness while staying feasible. If that seed
enters the passage left of centre, right-side empty space has no objective
value and the smooth solution can remain left-biased.

This is separate from the Map 7 blind-footprint defect. The former is a path
quality/objective issue with both obstacles visible; the latter is a safety
coverage issue where the obstacle face is absent. Simply enabling the generic
clearance penalty at every speed is not retained: earlier ungated candidates
increased Map 9/10 time by about 9.3/15.5%, produced a 141 s tail, and hard
terminal variants created liveness traps.

The next path-quality experiment should first log left/right passage
clearance and corridor asymmetry. If the observation is confirmed, add a
bounded bilateral face-balance or medial-axis reference only while an actual
two-sided passage is detected. Open space and one-sided wall following should
not be pulled toward an artificial centre.

## Decision and next gate

The recent-hit worker is suitable as default-off instrumentation, not yet as
a hard safety gate. Before promotion:

1. enqueue/evaluate at a bounded new-scan cadence as well as on new trajectory
   generations, so a long-lived trajectory cannot outrun its commit-time
   check;
2. obtain an actual r=0.20 contact-correlated detection or a deterministic raw
   scan replay of the old Map 7 geometry;
3. only then connect a generation-matched fresh `OCCUPIED` result to a
   body/short-tail reject, allowing only distance-monotonic egress when the
   body is already inside;
4. run Map 7 Full n>=20 again, then Map1-10 x three modes x n=3 before any
   final 300-row campaign.

Raw-cloud CIRI remains false and non-authoritative. Static-PCD evaluation,
the NaN issue, `obs_skip_num` no-op and `DRONE_R=robot_r` metric limitation are
unchanged.
