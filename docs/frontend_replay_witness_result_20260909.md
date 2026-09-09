# Deterministic MARSIM/frontend replay witness result

Date: 2026-09-09 (Asia/Seoul)

Decision: **`FRONTEND_MECHANISM_PASS_FULL_FIXTURE_NOT_YET_ADMISSIBLE`**

## Purpose and scope

The failed `abt2_cal_t1..t5` flight calibration showed that analytic
line-of-sight did not describe the realised LiDAR ray lattice, body pose or
committed trajectory. No planner or production filter policy was changed in
this follow-up. A new `frontend_replay_witness` executable holds the existing
PerfectDrone/MARSIM renderer at one commanded state, sends its newly rendered
PointCloud2 directly through the production C++ frontend, and repeatedly
publishes a deterministic first-order committed trajectory. It records raw
and filtered hazard/path-conflict evidence plus exact frontend risk verdicts.

This is a component/mechanism witness, not a flight outcome, a statistical
sample or evidence of Adaptive safety superiority.

## Frozen replay contract

The witness reused the preserved `abt2_cal_t3` PCD but did not reuse its
failed analytic reveal pose. The state was fixed at `(24.0,23.5,1.5)` m,
body yaw 90 degrees, and measured velocity `(0,7,0)` m/s. A generation-1
linear trajectory ran from that pose to `(16.2,24.4,1.5)` m in 1.15 s. The
production risk horizon remained 1.0 s, so the evaluated endpoint was
`(17.217391,24.282609,1.5)` m. Clearance was 0.20 m. Sector used the frozen 45-degree
crop; Adaptive used the deployed 5 Hz publication/risk caps and raw 1.5 s
accumulation window.

Each mode ran for six seconds with a one-second excluded warm-up. Because
velocity and body yaw were deliberately identical, both filtered outputs had
the same north-facing angular centre; the policy difference tested here is
the Adaptive raw-cloud risk side channel, not velocity-heading rotation.

## Gate result

| Metric after warm-up | Sector | Adaptive |
|---|---:|---:|
| raw frames | 50 | 50 |
| raw hazard-visible frames | 50 | 50 |
| raw evaluated-path-conflict frames | 50 | 50 |
| raw hazard points | 23,093 | 23,093 |
| raw evaluated-path-conflict points | 819 | 819 |
| filtered frames | 50 | 25 |
| filtered hazard points | **0** | **0** |
| filtered evaluated-path-conflict points | **0** | **0** |
| future-trajectory verdicts after warm-up | disabled | 25 |
| fresh `OCCUPIED` verdicts | disabled | **25** |
| maximum consecutive fresh `OCCUPIED` | disabled | **25** |
| final minimum distance | -- | 0.147124 m |
| final source-cloud age | -- | 0.001900 s |

The fail-closed analyzer passed all 13 checks. This directly demonstrates
that the actual renderer produces trajectory-conflicting raw points, the
actual fixed Sector code removes them, and the actual asynchronous frontend
risk worker detects the same raw evidence in at least two consecutive 5 Hz
periods. It also explains the earlier negative flight: at the old
`(24,20)` assumed reveal state the actual renderer returned zero points from
the target cylinder. Moving to the realised near-corner pose made the target
surface visible in every measured frame.

Frontend diagnostic rates were 10.002/10.008 Hz input for Sector/Adaptive,
10.003/4.914 Hz output, and 4.911 Hz Adaptive risk. Sector crop compute was
0.516 ms/frame mean (1.151 ms maximum); Adaptive crop compute was 0.432 ms
mean (1.453 ms maximum), and its raw risk worker was 2.125 ms/verdict mean
(3.263 ms maximum). These six-second component figures are diagnostics, not
the end-to-end paper compute comparison.

## Boundary and next admissible step

The frontend mechanism passed, but `abt2_cal_t3` is still not an admissible
evaluation fixture. Its preserved Full flight timed out at 90.01 s after 107
topology-reroute arms and 336 searches, with repeated A* `NO_PATH`, CIRI
infeasibility and optimiser overtime. A deterministic sensor witness cannot
convert that negative closed-loop result into Full feasibility.

Therefore no repeated flight or 150-row evaluation was started. The next map
family must be newly named and must widen or remove the upper channel wall so
that an inflation-aware forward bypass is available inside the local planning
horizon. Before its first flight it must pass both this replay gate and a
separate ROG-inflation-aware route check. Then run only a small preregistered
Full feasibility smoke; Sector/Adaptive comparison is allowed only if Full is
contact-free and completes every smoke row.

## Reproducibility files

- C++ executable mirror:
  `super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim/src/ros2_frontend_replay_witness.cpp`
- build mirror:
  `super_patches/native_seedmap_campaign/mars_uav_sim_perfect_drone_sim/CMakeLists.txt`
- fail-closed analyzer and tests:
  `scripts/native_campaign/analyze_frontend_replay_witness.py`,
  `scripts/native_campaign/test_analyze_frontend_replay_witness.py`
- witness rows:
  `results/frontend_replay_witness_abt2_t3_{sector,adaptive}_20260909.json`
- frontend stats:
  `results/frontend_replay_witness_abt2_t3_{sector,adaptive}_filter_stats_20260909.json`
- gate:
  `results/frontend_replay_witness_abt2_t3_gate_20260909.json`
- source/mirror C++ SHA-256:
  `324c3ec3ec1e542fe5443e610e4bfecf8c877ee79d67f7d2aeda2e642bfa5997`
- source/mirror CMake SHA-256:
  `05dd57c596c5310965279695b662f417b58c1563c538e8d6e7e92ccccb3f8d0a`

The package built successfully with `colcon build --packages-select
perfect_drone_sim --symlink-install`; all 47 native-campaign Python tests
passed. Runtime SUPER source remained at base commit
`2ad3419c127a617c6d7df6925e81a14175a9c096`.
