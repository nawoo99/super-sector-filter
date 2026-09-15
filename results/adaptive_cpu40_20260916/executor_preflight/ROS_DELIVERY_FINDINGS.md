# Static-PC delivery preflight: candidate not accepted

All tests used ROS_DOMAIN_ID=187, rmw_fastrtps_cpp, original best-effort/volatile
QoS, seed1's complete 241490-point / 7727680-byte static geometry. No FSM or
command publisher was started. No host socket/sysctl or SHM state was changed.
First failures were preserved, never overwritten. The runtime was not changed
after the tested install build.

| Trial directory | Actual static publications | Complete clouds received | Finding |
|---|---:|---:|---|
| ros_late_subscriber_attempt1 | 2 | 0 | Candidate100: bootstrap with zero readers, later0→1 publication; no late delivery within5s |
| ros_late_subscriber_legacy_control | 29 | 0 | Untouched legacy1 also fails the same late-reader step |
| ros_global_pc_prewarm_legacy | 20 (initial1 +bootstrap19) | 6 | Persistent reader before startup can receive full payload during old burst |
| ros_global_pc_prewarm_100 | 2 (initial1 +bootstrap1) | 0 | Even warmed single-shot bootstrap not delivered in this trial |
| ros_global_pc_count_pulse_100 | 6 (initial1 +pulse4 +bootstrap1) | 1 | Four~200ms-spaced warm count-change publications delivered none; one cloud arrived at bootstrap |

Every received payload had SHA256
`b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`.
The pulse probe's JSON `valid=true` means it eventually received a complete
cloud, NOT that the four pulse sends succeeded or the late-reader requirement
passed. It is a diagnostic, not the candidate acceptance test.

These controls show that full payload delivery is possible but single-shot
best-effort/volatile delivery is unreliable in this environment. Initial DDS
reader readiness alone does not explain the warmed single-shot failure. Large
fragmented-payload transport/resource/history loss is plausible, not isolated
to a proven component. Four spaced republishes did not establish a solution;
adding speculative retries must not be called a validated fix.

Recommendation: do not use static100 in the matched performance campaign yet.
Keep it opt-in and unaccepted; proceed separately with executor4 plus legacy1ms
static publication. Further delivery diagnosis or a separately reviewed
publication design is needed before accepting this static-map optimization.
It is outside the acquired LiDAR→planner safety input, but late-viewer delivery
was an explicit preservation requirement and its test failed.

The reader-first legacy trial exposed a pre-existing shutdown race:
`count_subscribers` executed after the ROS context became invalid and aborted
(ros2run exit250). Other trials shut down with exit0. This was preserved rather
than silently classified as a clean shutdown; no simulator child remained.

Unit-policy tests still pass; they establish local decision semantics, not DDS
delivery reliability. No C6 success or CPU-saving claim follows from them.
