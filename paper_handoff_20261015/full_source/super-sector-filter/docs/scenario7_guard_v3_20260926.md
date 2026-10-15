# Scenario7 follow-up: first-entry evidence and nonblocking generation

Prospective scope after rejected guard-v2 (`efcd7e7`): retain maps/missions,
original/v1/v2 installs and all failed results. No retry replacing a failed
trial, radius reduction, A* budget increase, timing/resource relaxation, or
CIRI activation. New simulation attempts are diagnostic until explicitly
admitted into a fresh ON/OFF cohort.

## First diagnostic

Before changing production code, use the frozen guard-v2 binary and existing
opt-in renderer/map/query/command tracing at the **actual** Urban building10
east face (-4,3.5), and if needed G4 cylinder40(-18.556532,-.319020). The v1
probe's Urban ROI at building12 is not suitable for this contact. Each new
probe is a separate attempt, never primary CPU/safety evidence or an ON
reference. The trace already records actual render quaternion and acquisition
request; point caps, sequence losses and missing footers must be disclosed.

Preserved current production sources:
`results/scenario7_guard_v3_20260926/preservation/production_source_v2.tgz`,
SHA256 `9b6ddf633a52108277cad2e51044748bd344a2bc07e363876c0c7088290ab49c`.

Independently review ordinary GENERATE_TRAJ/PlanFromRest so expensive search
runs off the 100Hz main callback while safe holds and generation/goal/map
identity remain enforced. Proposed concurrency changes require source/locking
review before implementation. Add supplementary prefix/timeout stop tests
without changing frozen v2 fixtures. No production change during an unchanged
v2 diagnostic flight.

Near-range filtering (renderer blind0.1m versus mapper minimum0.5m) is one
testable hypothesis: a Full refresh near a wall may still discard the closest
patch. This is not established as the flight cause before matching raw points,
map sensor pose, retained occupancy and the decisive guard queries.

## Bounded candidate changes after the unchanged-v2 diagnostic

The actual v2 ROG archive reproduced a constructed wall hole at the recorded
held pose: a 0.5m hit cutoff misses raw-body and inflated collision at the first
contact pose; a 0.1m cutoff detects it. The diagnostic also retains positive
near-wall input points rejected by the 0.5m rule. This supports a bounded repair,
not a claim that every recorded flight contact has a fully reconstructed cause.

The new YAML option `rog_map/raycasting/occupancy_only_min_range` defaults to
the legacy ray minimum. Explicit values must be finite and within
`[0, ray_range[0]]`. Only the no-raycasting occupied-hit cutoff changes. Closer
accepted hits contribute occupancy/multiplicity but do not generate backwards
or additional free-space ray marks. Genuine raycasting, free-ray minimum,
startup clearing, robot radius and guard margins remain unchanged.

Candidate `c28_observed_nearfield_async_generate` uses three new
`*_nearhit_v3.yaml` profiles, each differing from its effective previous mode
profile by exactly this one 0.1m key, matching the selected simulated sensors'
blind setting. Their previous `ray_range[0]=0.5` remains. These are static
simulation profiles, not validation for real-LiDAR self returns or noise.

Ordinary asynchronous generation is separately opt-in/default-off with
`SUPER_ASYNC_GENERATE_TRAJ=1`, common to all candidate modes. The worker uses
the existing separate replan executor. Internal planner commits are quarantined
until main accepts current goal/hold/brake/map/ACK/certificate identity; no
generic Full conversion of ordinary planning is allowed. Exact same-creation
goal retransmissions may be recognized only while the matching request is in
flight; new intent must invalidate it. The design is in
`results/scenario7_guard_v3_20260926/async_generate_design.md`.

Build all affected packages into the separate ABI-consistent prefix
`/root/super_ws/scenario7_guard_v3_20260926/install`, serially. In particular
the changed Config layout must not be mixed with old archive objects. First
run fresh G1/G4/Urban three-mode n=1 ON/OFF checks under the unchanged gates;
no old profile reference reuse, no retry replacing a failure, no ON/OFF pooling.
Do not promote or start seven-map confirmation based on offline tests alone.

## Publication-continuity admission

Review exposed an existing stopped-planning clock limitation: PlanFromRest
timestamps a path at computation start, not main-thread release. A nonexpired
geometric certificate alone does not prove a continuous transition from the
pinned stationary command. V3 therefore requires the existing PVA handoff
tolerances (1mm position, 0.01m/s velocity, 0.1m/s² acceleration), without
loosening them or changing message timestamps alone. Fresh finite stationary
odometry is obtained from the separately maintained ROS2 twist API, not the
legacy pose-only RobotState velocity. Ordinary command publication also binds
its sampled generation/start clock to the current committed snapshot and
certificate under the final release lock. A rejected handoff stays quarantined and is retained
as a failure, not counted as a successful safety repair.

First run the G1 three-mode n=1 checks. If stopped-path timestamps prevent
ordinary startup, stop expansion rather than spend the full G4/Urban campaign
on the same known defect. A correct whole-planner time-rebase mechanism needs
its own implementation/review, including EXP/backup/receipt consistency and a
prefix-from-zero certificate; this prospective v3 does not claim to supply it.
