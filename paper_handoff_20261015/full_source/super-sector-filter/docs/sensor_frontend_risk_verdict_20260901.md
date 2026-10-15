# Sensor-front-end filtering과 compact trajectory-risk verdict

날짜: 2026-09-01

## 1. 목적

이 단계는 기존 `cpp-intra` 구조보다 필터를 한 단계 더 앞에 놓아, raw LiDAR
`PointCloud2`가 DDS 경계를 전혀 넘지 않게 만드는 실험이다. 연구 목표에 맞춘
모드별 외부 인터페이스는 다음과 같다.

```text
Full
  renderer -> /cloud_registered DDS -> ROG-Map/FSM

Sector
  renderer --SharedPtr--> sensor front-end
                          `-> /cloud_sector DDS -> ROG-Map/FSM

Adaptive
  renderer --SharedPtr--> sensor front-end
                          |-> /cloud_sector DDS -> ROG-Map
                          `-> compact risk verdict DDS -> FSM
```

핵심 contribution 후보는 단순히 필터 코드의 위치를 옮긴 것이 아니라 다음 세
가지 계약을 함께 만든 것이다.

1. Sector/Adaptive에서는 `/cloud_registered` publisher 자체를 생성하지 않는다.
2. front-end는 현재 committed polynomial의 64-bit generation을 입력으로 받고,
   동일 generation과 source-cloud timestamp를 가진 작은 verdict를 반환한다.
3. FSM은 enforcement를 켠 경우 generation, result age, source-cloud age, checked
   trajectory-time 범위를 모두 확인한 OCCUPIED verdict만 브레이크 후보로 사용한다.

`certified`라는 표현은 쓰지 않는다. 이 결과는 formal certificate가 아니라
`generation/freshness-validated risk verdict`다.

## 2. 구현

### 2.1 raw DDS 제거

`PerfectDrone`에 optional cloud observer와 raw-publish switch를 추가했다. 새
`perfect_drone_frontend_node`는 simulator와 native C++ filter를 한 프로세스에
구성하고, renderer가 만든 `PointCloud2::SharedPtr`를 filter의 direct-input
queue로 넘긴다. 이 경로에서는 `/cloud_registered` publisher가 만들어지지 않는다.

기존 GLFW/OpenGL 제약은 유지한다. render callback은 생성 thread의
single-thread executor에 남고, odom/cmd/global-cloud/filter subscription은 side
executor에 둔다.

### 2.2 trajectory/verdict 계약

기존 `PolynomialTrajectory.trajectory_id`는 controller 호환용으로 유지하고,
비동기 안전 소비자가 wraparound 없이 정확히 비교하도록
`uint64 trajectory_generation`을 추가했다. Full polynomial과 100 Hz heartbeat
모두 현재 generation을 싣는다.

새 `TrajectoryRiskVerdict`에는 request/generation/cloud sequence/source stamp,
status, checked time range, witness 위치/시간, 최소 거리, point 수, source age와
compute time이 들어간다. 실제 CDR 직렬화 크기를 publisher에서 계측한다.

### 2.3 독립 latest-only worker

raw callback은 SharedPtr와 최신 job만 저장한다. Angular filtering과 verdict
계산은 서로 다른 worker에서 수행한다. verdict worker는 1.5 s raw window를
trajectory tail의 AABB로 crop하고 KD-tree nearest-hit/egress 검사를 수행한다.
따라서 22 ms 수준의 최악 verdict 계산도 filtered-cloud publish나 100 Hz FSM을
동기적으로 막지 않는다.

### 2.4 opt-in 경계

- 새 planner profile:
  `static_seedmaps_guard_viability_tight_v7_frontend_risk_shadow.yaml`
- 새 runner backend: `--filter-backend cpp-frontend`
- `frontend_risk.shadow_en: true`, `enforce_en: false`
- 표준 `tight_v7`과 기존 실사용 profile은 변경하지 않았다.
- 실제 브레이크 연결은 이번 단계 범위 밖이며 default-off다.

## 3. 검증

Release build는 `mars_quadrotor_msgs`부터 `super_planner`까지 통과했다. Campaign
pytest 24개와 standalone C++ geometry/stats/witness equivalence test도 통과했다.
Source와 mirror 15개 대응 파일은 byte-identical이다.

Planner 없는 runtime contract smoke에서는 다음을 직접 확인했다.

- `/cloud_registered`: unknown topic, publisher 0
- `/cloud_sector`: publisher 1
- `/planning/trajectory_risk_verdict`: publisher 1
- 203 raw direct inputs, 203 filtered frames, 203 verdicts
- filter/verdict worker overwrite 0
- trajectory가 없을 때 status `EMPTY_TRAJECTORY`

첫 Map7 Adaptive smoke는 72.95 s에 완주했고 static collision 0, clearance
+0.254 m였다. 770 scans/verdicts 중 OCCUPIED 4건을 front-end와 FSM이 같은
generation으로 기록했다. `enforce=false`이므로 비행 결정에는 영향이 없었다.

## 4. Map7/9/10 × Full/Sector/Adaptive × n=1

조건은 v=7, loop24, source static PCD, 180 s timeout, rotating mode order다. 모든
9행이 first-attempt 완주, static-safe, speed-valid였고 retry/OOM은 0이었다.

| Map | Mode | 완주 | static collision | 시간(s) | clearance(m) | DDS cloud+verdict (MiB/s) | raw direct (MiB/s) | kept | Full-open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | Full | 1/1 | 0 | 99.66 | +0.245 | 4.2440 | 0 | - | - |
| 7 | Sector | 1/1 | 0 | 64.21 | +0.207 | 4.1721 | 12.1596 | 55.171% | 0 |
| 7 | Adaptive | 1/1 | 0 | 62.95 | +0.306 | 3.6024 | 11.4888 | 45.784% | 25 |
| 9 | Full | 1/1 | 0 | 100.45 | +0.281 | 5.6179 | 0 | - | - |
| 9 | Sector | 1/1 | 0 | 68.07 | +0.220 | 4.7513 | 13.8458 | 55.158% | 0 |
| 9 | Adaptive | 1/1 | 0 | 72.12 | +0.207 | 4.5499 | 13.8075 | 48.111% | 24 |
| 10 | Full | 1/1 | 0 | 93.67 | +0.265 | 5.2211 | 0 | - | - |
| 10 | Sector | 1/1 | 0 | 75.75 | +0.296 | 4.2204 | 12.8613 | 52.902% | 0 |
| 10 | Adaptive | 1/1 | 0 | 63.22 | +0.188 | 4.2084 | 13.4653 | 45.380% | 22 |

세 map 평균에서 Adaptive는 Full 대비 mission time -32.504%, ROG/DDS cloud rate
-18.085%였다. Compact verdict는 평균 0.001815 MiB/s로 전체 algorithm DDS의 약
0.044%였고, 정확히 180 CDR bytes/message였다. Adaptive 2,096 verdict의 평균
계산시간은 5.201 ms, run별 최대 중 최댓값은 16.924 ms, overwrite는 0이었다.
이 3개 map × n=1 결과는 population 성능 추정이 아니라 architecture gate다.

`raw direct` 열은 wire traffic가 아니다. simulator/front-end 프로세스 내부에서
소비한 raw logical payload다. 반대로 Full의 값은 현재 runner가 ROG-Map에서 실제
처리한 raw payload이며 sensor publish 총량과 동일하다고 가정하면 안 된다.

## 5. CPU 결과와 반대 증거

Map7을 추가로 Full/Sector/Adaptive 각 1회 실행해 CPU 경계를 보강했다.

| Mode | 시간(s) | FSM core | simulator/front-end core | cloud worker core | verdict worker core | front-end worker 합 |
|---|---:|---:|---:|---:|---:|---:|
| Full | 89.38 | 0.768 | 0.140 | - | - | - |
| Sector | 66.01 | 1.068 | 0.165 | 0.0127 | 0 | 0.0127 |
| Adaptive | 64.21 | 1.153 | 0.270 | 0.0118 | 0.0529 | 0.0646 |

이 gate에서는 총 연산량 감소 주장이 성립하지 않는다. Map7/9/10 n=1 평균도
Adaptive FSM core 1.112로 Full 0.679보다 높았고, 평균 FSM core-seconds는
73.496 대 66.406으로 +10.677%였다. 이전 `cpp-intra` n=3 결과의 감소와 반대다.

가장 큰 confound는 처리 cadence다. 이 campaign의 Full ROG 처리율은
3.82~4.49 Hz였지만 front-end Sector는 10.20~10.34 Hz였다. Raw DDS와 큰 scan을
없애면서 map callback 처리율이 회복됐고, 그만큼 FSM/ROG가 더 많은 generation을
처리했다. 따라서 현재 숫자는 front-end 계산비용만의 차이가 아니다. 낮아진
bandwidth를 확인했어도 “Adaptive가 Full보다 computation도 작다”고 쓰면 안 된다.

메모리도 감소 주장이 없다. 9행 FSM peak PSS는 약 3.18~3.23 GiB 범위였고,
호스트 swap은 실험 시작부터 약 2.04 GiB로 거의 포화 상태였다. 그럼에도 이번
9행에는 OOM/retry가 없었다.

## 6. 결론과 다음 단계

이번 단계에서 확정된 것은 다음이다.

- 필터를 sensor publisher 앞단으로 옮겨 Sector/Adaptive raw DDS를 구조적으로
  제거했다.
- Sector는 filtered cloud만, Adaptive는 filtered cloud+180-byte verdict만 DDS로
  보낸다.
- 어려운 Map7/9/10 n=1에서 Full/Sector/Adaptive 모두 완주·충돌 0이었다.
- verdict 계산은 독립 latest-only worker이며 planning/filter publish를 막지 않는다.
- 브레이크 enforcement와 표준 profile은 변경하지 않았다.

다음 최적화는 안전 threshold를 건드리는 것이 아니라 cadence를 정합하는 것이다.

1. Full과 Adaptive의 source publish/ROG commit cadence를 동시에 계측한다.
2. 동일 accepted-generation rate 또는 동일 sensor cadence에서 CPU/core-seconds를
   비교한다.
3. front-end cloud publish cap과 generation refresh를 조절해 completion/contact가
   유지되는 최소 map callback rate를 찾는다.
4. CPU 감소 gate가 성립한 뒤 verdict enforcement를 별도 fault-replay와 repeated
   Map7/9/10 gate로 승격한다.
5. 마지막에만 Map1-10 n=10을 실행한다.

근거 파일:

- `results/frontend_risk_shadow_map7_n1_raw_20260901.csv`
- `results/frontend_risk_shadow_maps7_9_10_three_mode_n1_raw_20260901.csv`
- `results/frontend_risk_cpu_map7_three_mode_n1_raw_20260901.csv`
- 각 CSV와 같은 이름의 `_artifacts_20260901/` 디렉터리
