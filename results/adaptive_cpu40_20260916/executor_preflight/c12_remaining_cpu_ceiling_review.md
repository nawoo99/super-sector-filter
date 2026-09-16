# Remaining CPU opportunities after C12 (read-only review)

Scope: C12 profiled seed1 n=1, not a universal or unprofiled result. No source,
timer, safety, deadline, or Full-workload changes are proposed as metric tricks.
Root is implementing C14 explicit command identity separately.

## Arithmetic constraint

C12 whole-mission experiment-cgroup mean used cores were Full0.60714837965 and
Adaptive0.44755306452 (26.286% relative reduction). With all else held equal:

- Reaching40% by removing the SAME common overhead from both requires
  **0.208160091825cores** removed from each.
- Reaching40% by removing Adaptive-only cost requires **0.08326403673cores**.
- Removing equal common0.03/0.049/0.079/0.10/0.13cores would yield
  27.65/28.59/30.22/31.47/33.45%, respectively.

These are accounting scenarios, not predicted achievable gains. Individual
stage/role measurements below cover profiler/wholly-enclosed telemetry windows,
not exactly the whole-mission denominator above. Do not add overlapping scopes.

## Ranked bounded opportunities

| Priority | Change | Measured budget / ceiling | Conditions and limitations |
|---|---|---|---|
| 1 | C14 explicit goal retransmission identity + mission serialization | Entire mission process≈0.02947F/0.03117Acores; entire replan callback inclusive≈0.10318F/0.10460Acores | These are generous separate ceilings, not savings. Only a subset of solves is induced by the35/36 duplicate accepted requests. Default-off identity+healthy current-SAFE coalescing avoids treating arbitrary fresh identical user commands as retries. Mission100Hz timer and1Hz resend stay unchanged. Actual producer preflight passes; receiver/flight still need their own validation. |
| 2 | Fix static-PC delivery, then adopt bounded post-bootstrap event/coarse handling | Entire actual static executor≈0.04831F/0.04933Acores; callback body≈0.01731F/0.01737Acores | C13 demonstrates idle removal, but late-reader failure remains in both legacy and candidate, so it is not adoptable. Preserve5.0–5.1s fast bootstrap and full geometry; declare bounded resend transport semantics separately. Initial, late0→1, additional-reader1→2, count decrease and reconnect need complete SHA validation. |
| 3 | Resolve Adaptive residual attribution before touching callbacks | Composed-process unscoped residual≈0.07743F/0.11219Acores; difference≈0.03476cores | This is not a proven frontend cost. Even hypothetically deleting that entire differential gives only≈32% reduction using whole-mission arithmetic. Existing intra-process dispatch, locks, DDS and unscoped frontend bookkeeping share the residual. Naming the actual frontend worker TID at startup and using existing/proc telemetry would be cheaper than a new heavyweight observer. |
| 4 | Eliminate duplicate stats JSON serialization, preserving required1Hz evidence | No measured material CPU budget | `native_sector_cpp.cpp:601–607` writes stats1Hz; `3082` report also writes the same full JSON every5s under state mutex. A single writer with unchanged1Hz/final records could remove only redundant5s writes. Snapshotting outside the state mutex is primarily a latency improvement; no evidence it explains0.03–0.08cores. |
| 5 | Skip truly unobserved visual-only message construction | Entire odom callback≈0.00988F/0.00905Acores, so actual savings necessarily smaller | `ros2_perfect_drone_model.hpp:1252+` publishes odom, pose, TF, mesh and accumulated path. Mandatory odom must remain100Hz; any optional observer gating needs same-frame late-viewer behavior. Path accumulation must remain if later subscribers expect history. Low ceiling; not a route to40% alone. |

Static-PC retry caution: previous `executor_preflight/ROS_DELIVERY_FINDINGS.md`
records four≈200ms-spaced count-change sends delivering no cloud before the
startup burst. Therefore a proposal of merely3–5retries is not already validated.
A larger predetermined bounded budget can be evaluated, with payload/geometry
unchanged and failed control cases retained. Empirical late-delivery success is
not a transport delivery guarantee. No host sysctl change is authorized here.

## Work that is already small or absent

- Source-acquired frontend SharedPtr forwarding does not angular-crop or copy
  PointCloud2 payloads (`native_sector_cpp.cpp:2357–2368`, `2437–2447`). Cloud
  worker processing is≈0.0177ms wall/frame across395frames,≈7ms wall total; it
  cannot by itself explain a1CPU-second residual. Input wait/CPU are different.
- Current event-only frontend does not start the expensive point-risk validator
  worker; risk-message counters are0. Static probe is disabled in these runs.
- Main callback inclusive≈0.00265F/0.00304Acores; command callback≈0.00474F/
  0.00740Acores; total guard-certificate inclusive≈0.00179F/0.00191Acores.
  They overlap other nested scopes. Weakening guard checks or slowing100Hz
  safety/control to remove tiny costs is not justified.
- Replan callback overhead excluding its nested work≈0.000226F/0.000261Acores.
  Changing15Hz decision cadence is not a useful safe overhead optimization.
- Profile histogram has only10/12 stale-map ordinary decisions and zero
  insufficient-geometry decisions; a new geometry-refresh architecture is not
  the measured next bottleneck.
- Two side-executor workers already preserve measured100Hz callbacks/odom and
  10Hz source. Going to a single shared worker would serialize potentially long
  planning against odom/command and needs a different architecture; it is not a
  safe one-line next setting.

Conclusion: there is no presently evidenced small optimization that guarantees
40%. C14 and a separately proven static delivery fix are the most credible
bounded steps. Adaptive-only overhead should be measured before claiming a
large removable cost. All final comparisons still require unprofiled matched
confirmation, contact/completion/time gates and unchanged source45/Full ACK
recovery guarantees.
