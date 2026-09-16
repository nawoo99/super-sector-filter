# C16 recovery causal audit (read-only, 2026-09-16)

## Finding

The three Adaptive Full-recovery episodes in run 9317 are **not evidenced as a command-generation/certificate-publication race**. Each has an explicit `main_pre` certificate rejection of the committed trajectory for `CLEARANCE_MARGIN` on a newly committed map. A fresh map is not necessarily a safe map for the old trajectory. This status is an inflated-clearance-policy failure, not proof of a physical body collision.

Two superficially suspicious log fields have different meanings:

- Brake log `path_status=SAFE` describes the **new brake candidate**, not the committed ordinary trajectory which triggered recovery.
- `motion_gen=2/0`, `6/2`, and `40/6` compare the current committed generation to a **recovery-only odometry differencing anchor**. That anchor is updated only when `activateEmergencyBrake` runs. It is not the safety-certificate generation. `motion_source=none` and infinity fields are expected when this first recovery sample has no recent, same-generation predecessor; the fresh last-published command is still used to initialize the brake.

No runtime, guard, lease, timer, configuration, or test was changed for this audit.

## Run evidence

Log paths are relative to `results/adaptive_cpu40_20260916/c16_frontend_executor_profile/artifacts/`.

| Adaptive episode | Last ordinary commit | Rejected ordinary trajectory | Brake result / recovery |
|---|---|---|---|
| 1 | Log line 471: gen2/map13 at 1789526448.885398 | Line 485: `main_pre CLEARANCE_MARGIN gen2/map15`, map age .004s, TTC .405s; first brake marker about 134ms after commit | Line 483: fresh command 3.334m/s initializes a certified .944s brake. Full start line482 to Sector line524: approximately1.254s. |
| 2 | Line543: gen6/map30 at 1789526450.590846 | Line561: `main_pre CLEARANCE_MARGIN gen6/map33`, map age .011s, TTC .385s; first brake marker about238ms after commit | Line558: no candidate accepted; last attempted dynamics exceed7m/s (9.219m/s), with last geometry verdict UNOBSERVED from an earlier checked attempt. Line559 begins a stationary retry; line574 accepts a certified stationary hold after .320s stability. Full start557 to Sector580: approximately.378s. |
| 3 | Line1169: gen40/map141 at 1789526461.809135 | Line1178: `main_pre CLEARANCE_MARGIN gen40/map142`, map age .004s, TTC1.050s; first brake marker about11ms after commit | Line1174: dynamic limits pass but brake geometry also fails CLEARANCE_MARGIN. Line1175 starts a stationary retry;1193 accepts after .320s stability. Full start1173 to Sector1199: approximately.367s. |

Adaptive log: `seed1_run9317_adaptive.attempt1.stack.log`.

The first episode is an ordinary moving-path clearance recovery shortly after startup; its roughly1.25s duration is not a wait for a missing motion-anchor certificate. It includes executing the accepted .944s brake, acquiring/committing Full observations, and obtaining the new path (PATH_READY gen2→3, line521).

Certificate records use `fmt::print` while brake/commit records use ROS logging. The merged stream buffers them differently: a causally prior `main_pre` certificate can appear after its brake marker. Do not infer source execution order solely from adjacent line order.

Full comparison: `seed1_run9317_full.attempt1.stack.log` has one `poly_publish VERSION_CHANGED` (line1096) immediately followed by `replan_post SAFE gen39/map124` (1097), with no corresponding `main_pre_uncertified` brake. This demonstrates a conservative version-race rejection can occur and be revalidated; it does not implicate that mechanism in the three Adaptive episodes.

## Source trace (runtime source as audited)

All source paths are relative to `/root/super_ws/src/SUPER/`.

1. `super_planner/include/ros_interface/ros2/fsm_ros2.hpp:4446`: `main_pre_uncertified` is called only after `refreshSafetyCertificate("main_pre")` returns false. It is not triggered by the recovery-motion infinity fields.
2. Same file2158–2187: a missing/mismatched cached certificate causes validation of the current committed trajectory, not an unconditional brake. Lines2190–2223 store/log the returned status and return its `safe()` value.
3. `super_planner/src/super_core/super_planner.cpp:677`: validation snapshots the committed trajectory and records its generation; lines693–695 return VERSION_CHANGED if the generation changes during validation. The three relevant Adaptive records instead say CLEARANCE_MARGIN.
4. `super_planner/include/super_core/super_planner.h:104`: SAFE and DISABLED are the only `safe()` statuses. CLEARANCE_MARGIN is not accepted for ordinary motion.
5. `fsm_ros2.hpp:2330–2362`: recovery continuity compares the current generation with `recovery_motion_last_generation_`; finite-difference evidence also requires .005–.5s odometry spacing. Lines2409–2422 update the anchor inside brake activation. Lines2459–2467 allow a fresh cached command when independent recovery-motion evidence is not yet valid.
6. `fsm_ros2.hpp:2622`: `brake_safety` is populated by `validatePositionTrajectory(candidate, ...)`, where `candidate` is the newly built brake. Lines2869–2902 print **that** result as `path_status`.
7. `fsm_ros2.hpp:2536–2547` and2651–2658: a zero-motion candidate is refused until at least.25s of independently observed positional stability. This explains the otherwise SAFE stationary retries. Do not remove this gate to shorten a recovery.
8. `fsm_ros2.hpp:3745–3771`: ordinary command publication requires a safe, current-map certificate and a command sample of exactly its generation; mismatch requests revalidation and suppresses publication. It does not directly create `main_pre_uncertified`.
9. `mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp:1189–1195,1357–1361`: the perfect-tracking simulator assigns position and velocity directly from commands; `publishOdom`1288–1299 republishes these stored fields. During suppression, unchanged position can therefore coexist with the previous nonzero velocity field. The next retry's zero position-difference versus6.810/4.931m/s odometry twist is consistent with this model, not evidence of physically instantaneous braking. These runs must not be promoted to real-dynamics safety validation.

## Decision / optimization implication

- Retain all current safety, map-version, generation, and passive-stability gates.
- Identified avoidable publication-race recoveries among these three episodes: **zero**. This audit therefore supports **no positive CPU-saving estimate** for an atomic-publication change, and does not justify implementing one as the next optimization.
- This is not a proof that all publication races are impossible. If a future `main_pre VERSION_CHANGED` episode is observed, first capture a single correlated trigger record containing original certificate status, committed generation/map before and after validation, and brake-candidate status separately. Such optional diagnostic work should precede a scoped synchronization proposal; no such implementation is included here.
- Changes to clearance policy or the simulator's passive-stop behavior would be materially different algorithm/dynamics work and are outside this no-change audit.
