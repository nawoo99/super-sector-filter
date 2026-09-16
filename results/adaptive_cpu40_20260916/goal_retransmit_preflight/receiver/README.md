# Explicit goal retransmission receiver proposal

Status: parent and independent review authorized application; six receiver files
were applied and mirrored. Sequential super_planner/perfect_drone_sim build PASS
in 6m25s, recorded in build_attempt1.log (both packages and composed consumers).
Applied-source pure helper optimized and ASan/UBSan tests PASS, as do the real-Fsm
metadata tests and pre-existing demand metadata regression with the flag off/on.
No flight result is claimed. receiver_binding.patch is the initial review artifact; authoritative
applied files are the runtime and corresponding mirrors (including the separately
prepared real-Fsm test and the allocation-free accepted-frame move refinement).

## Intent identity, not pose heuristics

Paired opt-in `SUPER_GOAL_RETRANSMIT_IDENTITY=1`; receiver also requires existing
guarded-demand opt-in. The reviewed producer retains one positive creation stamp
on its1Hz retransmissions, but allocates a fresh stamp for each new waypoint or
explicit retrigger. Incoming same-pose NEW stamp is always a normal new goal.
Receiver requires identical original p, quaternion coefficients, frame and
creation stamp. Comparisons are finite bit-exact (including signed zero), with no
normalization, yaw conversion, voxel rounding or mapped-goal equivalence. Empty
frame, nonfinite input, zero/negative/malformed stamp always queues normally.
Stamp parser refuses sec<0 or nanosec>=1e9 rather than normalizing into another ID.

An explicit retransmission means the already accepted raw command remains the
same command; suppressing it does not repeat raw→nearest-free projection merely
because a map changed. Ordinary replanning's existing effective-goal remapping,
map updates and safety guards remain. This is a declared command-idempotence
protocol, not a claim of exact old planner trace equivalence.

## Qualified token and live proof

- Base Fsm retains the RAW identity and source queue revision of the request
  actually consumed. Newer pending data cannot be mistaken for that acceptance.
- A token is minted only after existing recordDemandReplanOutcome qualified an
  own successful ordinary commit, and after a new read-only healthy-current proof.
  The token records goal revisions, generation, goal/state epoch and existing
  brake activation revision / event request / Full request identities.
- New normal enqueue, goal processing completion, actual non-success ordinary
  replan, or candidate rejection invalidates the token. ChangeState invalidates
  the epoch AND stores the new state in one goal-mutex transaction. A
  FOLLOW→EMER→FOLLOW episode cannot revive an old token.
- Recovery begin/completion ABA is excluded by the existing monotonically
  changing brake/event/Full-request identities; no new writes to shared safety
  flags are introduced. A transient revalidation that completes with a still-
  current exact SAFE certificate is not itself treated as a new user intent.
- Callback takes activation→Full-refresh→safety locks with try_lock only. Any
  outer-lock contention queues normally. Under those locks, the short base goal transaction
  rechecks token/queue/identity and samples current trajectory generation plus
  current immutable map/certificate. Its existing goal/CmdTraj/MapHealth mutex
  reads may wait briefly; this is not an entirely wait-free callback. No
  pending/updating goal is eligible.
- Proof requires ordinary FOLLOW, no stop/finish/from-rest, active brake,
  revalidation, recovery/Full ACK/event demand, rejection/topology retry; exact
  SAFE/current map/gen without escape exceptions; finite unfinished nonbackup
  command sample inside the certificate interval. Map freshness uses the stricter
  min(low/high-speed configured limit), avoiding command-cache lock nesting.
- Existing command100Hz and demand15Hz callbacks remain untouched. Coalescing
  writes only its diagnostic counter: not queued/accepted revisions, new_goal,
  trajectory, certificates, recovery, demand success timestamps or viability
  receipts. Existing qualified ordinary commits alone renew demand leases.

## Locks / source inspection

New coalescing/mint nesting is activation→full_refresh→safety→pending_goal→short
CmdTraj/MapHealth reads. Existing command publication already uses safety before
ChangeState/pending_goal. Existing startup completion uses activation, a released
safety scope, then full_refresh→pending_goal. CmdTraj and MapHealth readers do not
call back into goal metadata. No pending_goal→safety/full_refresh/activation path
is added. All large solver/map-processing work stays outside pending_goal.
The immutable map can publish after the final version read; the linearization is
that matching read under the held certificate lock, followed by existing100Hz
safety enforcement. This is not a new hard real-time safety guarantee.

## Runtime diagnostics

`[GOAL_RETRANSMIT_IDENTITY] enabled=true role=receiver guarded_demand=true identity=creation_stamp_raw_pose_frame default_off=true`

Each actual suppression:
`[GOAL_RETRANSMIT_COALESCED] stamp_ns=... generation=... map=... queued_revision=... accepted_revision=... coalesced_total=...`

Both Full/Adaptive must show positive coalescing coverage before comparing this
optimization, and all identities must link to actual producer retransmissions.
No-coalescing Full is not a valid optimized-reference success claim.

## Tests and limitations

`goal_retransmit_policy_test.cpp`: exact ID/raw equality, fresh same-pose intent,
canonical stamp boundaries/alias rejection, each live-proof rejection boundary.

`goal_retransmit_fsm_metadata_test.cpp`: actual Fsm enqueue/token/GoalUpdateScope/
ChangeState methods, fresh raw/stamp/frame, unhealthy fallback, pending and
consume-to-accept gap, consumed-vs-newer identity, failed-token invalidation,
state ABA/completion, and4000 requests in barrier-started identical/mixed races.
Its proof function is intentionally stubbed, and its consume handoff is arranged
without a map. It does not exercise the actual solver, ROS certificate mutexes or
producer/consumer communication. Failed planner return hook and demand-timestamp
nonmutation additionally require source review and subsequent live audit.

### Executed evidence

- `build_receiver_attempt1.sh` / `build_attempt1.log`: exit 0, two packages in
  6m25s; super_planner 2m18s, perfect_drone_sim 4m7s. Full/Adaptive composed
  executables and both planner executables installed successfully.
- `run_metadata_tests_attempt1.sh` / `metadata_tests_attempt1.log`: exit 0.
  Real-Fsm retransmission default-off queue test PASS; enabled 54 checks and
  4,000 barrier-started concurrent requests PASS. Existing demand metadata test
  PASS with retransmission disabled and enabled (17 checks, 2,000 enqueues and
  four actual early replan gates per invocation).
- `run_policy_tests_attempt1.sh` / `policy_tests_attempt1.log`: optimized and
  ASan/UBSan PASS against applied runtime source, including 14 raw-change cases,
  23 unhealthy gates and canonical timestamp parser checks.
- Six receiver runtime files and their prescribed mirrors compared byte-identical
  before and after testing. No default policy or flight result is changed by
  these tests; no actual-Fsm sanitizer/TSAN or live certificate proof is claimed.
- Completed attempt executables/objects were moved recoverably outside the
  repository to `/tmp/super_goal_receiver_completed_Tun9fRTD`. Runner scripts now
  allocate task-specific `mktemp` output directories and print their paths;
  no ELF/object files belong in source commits. Their current output-path-only
  refinement occurred after the successful tests above, without another compile.

Required next: parent audits producer-only ROS fixture and conducts paired seed1
flight with static-two-phase OFF, checking positive coalescing in both modes and
producer identity linkage. No source/model benchmark generalization or final
adoption is claimed by these unit tests.
