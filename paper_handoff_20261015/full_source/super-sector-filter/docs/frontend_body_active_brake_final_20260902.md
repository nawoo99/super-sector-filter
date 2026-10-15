# Current-body safety tier and active-brake replacement (2026-09-02)

## 결론

2026-09-01 최종 300회에서 발생한 Map 10 Adaptive 접촉은 5 Hz future-tail
검사와 trajectory generation 전환 사이의 coverage gap이었다. 이 문제를 막기 위해
Adaptive sensor front end에 약 10 Hz의 저비용 current-body/0.15 s 검사 tier를
추가했다. 이 tier는 fresh raw scan과 measured odometry에 결합되며 trajectory
generation에는 결합되지 않는다. 기존 5 Hz future-tail tier는 exact-generation
계약을 그대로 유지한다.

기능 gate에서 generation이 다른 fresh current-body OCCUPIED가 이미 활성화된
future brake를 정확히 한 번 교체했고, 교체한 certified brake에서 정상 복구했다.
자연 실행에서는 Map 10 30/30, Map 7 Full/Adaptive 각 20/20, Map 1--10
Full/Adaptive/Sector 각 30/30이 모두 source-static-PCD 기준 무충돌 완주했다.

다만 이것은 population-level 100% 보장이 아니다. 각 모드 30/30 성공의 Wilson
95% 하한은 88.65%다. 또한 고정 Sector도 30/30 완주·무충돌이어서 이번 10개 맵과
±60° 조건은 Adaptive의 안전/완주 이득을 식별하는 대조군이 아니다.

## 1. 원인과 계약 분리

이전 Map 10 run6 접촉에서는 첫 접촉 99 ms 뒤 gen36 OCCUPIED가 도착했고, 그 전에
gen37이 commit되어 future-tier exact-generation gate가 결과를 무시했다. gen37
OCCUPIED brake는 접촉 뒤였다. 단순히 heavy worker를 10 Hz로 올리면 window
accumulation, crop 및 KD-tree 비용까지 두 배 가까이 늘지만 generation race를
형식적으로 없애지도 못한다.

따라서 verdict를 두 scope로 분리했다.

| scope | 입력/예측 | cadence | 소비 계약 |
|---|---|---:|---|
| `FUTURE_TRAJECTORY` | raw-window + committed polynomial tail | 최대 5 Hz | generation, result age, source age, checked time 모두 일치 |
| `CURRENT_BODY` | 최신 raw scan + measured position/velocity의 0.15 s 선분 | sensor frame, 약 10 Hz | generation-independent, result/source freshness 필수 |

Current-body 검사는 raw points를 body-to-predicted-position 선분의 clearance AABB로
먼저 제한하고, body/end/segment distance와 witness time을 계산한다. 시작점이 이미
장애물 안이고 선분 끝이 더 멀어지는 경우에는 기존 EGRESS 의미를 적용한다.
기본 clearance는 0으로 비활성화되며 실험 runner에서만 0.20 m를 준다.

## 2. FSM enforcement와 active-brake 교체

FSM은 current-body와 future OCCUPIED pending slot 및 request-id watermark를 별도로
유지한다. 같은 request를 여러 번 publish해도 두 번째 callback은 pending edge를
다시 만들지 않는다. 일반 `FOLLOW_TRAJ`에서는 fresh current-body 결과를 먼저
소비하고, 없으면 future 결과를 소비한다.

기존 구현은 brake가 활성화된 동안 verdict 소비 자체를 건너뛰었다. 이 때문에 더
새로운 근접 obstacle을 발견해도 과거 brake trajectory를 계속 수행할 수 있었다.
이제 활성 brake 구간에서도 current-body만 소비한다. witness가 현재 body보다
0.01 s 이상 앞에 있고 body distance보다 segment minimum이 0.02 m 이상 가까운
경우에만 brake를 다시 계산한다. 한 brake episode당 교체를 한 번으로 제한해
10 Hz 결과가 정지 궤적을 계속 reset하지 않게 했다.

설정은 모두 default-off다.

- `fsm/trajectory_guard/frontend_risk/current_body_enforce_en: false`
- `current_body_result_max_age_s: 0.15`
- `current_body_source_max_age_s: 0.20`
- `trajectory_guard_raw_cloud_ciri_shadow_en: false` 유지
- 표준 `tight_v7.yaml` 및 filtered profile은 변경하지 않음
- 별도 `static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml`에서만
  current-body enforcement를 활성화

## 3. 결정론적 기능 gate

| gate | 관측 | 판정 |
|---|---|---|
| stale current-body | result/source age 1.491 s, `action=IGNORE` | PASS |
| fresh current-body | 일부러 다른 generation을 넣어도 10 ms age에서 `action=BRAKE` | PASS |
| active brake replacement | future brake 뒤 99 ms에 current-body brake, duration 0.568 s | PASS |
| duplicate request | body enforce 및 `frontend_body_active_brake` trigger 각 1회 | PASS |
| recovery | replacement brake에서 `TRAJ_GUARD_RECOVERED` | PASS |

최종 기능 gate 행은 Map 1 완주, collision 0, retry 0이며
`frontend_body_active_brake_replacements=1`이다. 이 gate는 wiring과 idempotence를
검증한 것이며 자연 장면에서 교체가 빈번하다는 뜻은 아니다.

## 4. Map 10 집중 검증

최종 n=10에 추가 n=20을 이어 총 30회를 독립 실행했다.

| 지표 | Adaptive Map 10 n=30 |
|---|---:|
| 완주 / 무충돌 / valid / first-attempt | 30/30 / 30/30 / 30/30 / 30/30 |
| 시간 mean / min / max | 72.506 / 60.45 / 104.98 s |
| static-PCD clearance mean / worst | +0.247 / +0.131 m |
| topology reroute arms / searches | 232 / 420 |
| body OCCUPIED / body brakes | 7 / 5 |
| 자연 active-brake replacement | 0 |
| body compute mean / worst row max | 0.394 / 2.361 ms |
| algorithm mean cores / core·s | 1.033 / 76.864 |
| algorithm PSS mean / max | 3205.49 / 3291.14 MiB |
| retry / OOM | 0 / 0 |

자연 replacement가 0인 것은 결함이 아니다. 활성 brake 도중 별도의 더 앞쪽 body
witness가 나타나는 좁은 race 조건이며, 그 경로는 결정론적 fault gate로 검증했다.

## 5. Map 7 resource-normal liveness 재검증

이전 300회에서 Map 7 Full/Adaptive run1 timeout은 topology trap과 심한 host memory
reclaim이 함께 있었다. 메모리가 회복된 상태에서 각 20회를 재실행했다.

| mode | complete/safe/first | 시간 mean (min--max), s | worst clearance, m | reroute arms/searches | algorithm cores / core·s | retry/OOM |
|---|---:|---:|---:|---:|---:|---:|
| Full | 20/20 | 86.952 (64.03--108.42) | +0.021 | 162 / 270 | 0.807 / 71.125 | 0/0 |
| Adaptive | 20/20 | 67.730 (60.98--84.74) | +0.128 | 139 / 189 | 1.063 / 74.277 | 0/0 |

두 모드 모두 PSI full 0이었고 minimum available memory는 5.65/5.73 GiB였다. 이는
이전 실패가 순수 host 문제였다는 증명은 아니다. 정상 자원에서는 재현되지 않았고,
실제 topology 민감도가 memory reclaim에 의해 증폭되었다는 분리 근거다.

## 6. Map 1--10, 세 모드, 맵당 3회

Full/Adaptive는 rotating order 60행, Sector는 같은 설정의 별도 30행으로 실행했다.
`static_pcd`를 source-of-truth contact 판정으로 사용했고 속도 제한, performance
window 및 cgroup 계측 validity를 함께 확인했다.

각 셀은 `완주/무충돌, 평균시간, 최악 clearance`다.

| 맵 | Full | Sector | Adaptive | Adaptive effective Full-open / body brake |
|---|---|---|---|---:|
| Map 1 | 3/3, 64.25 s, +0.203 m | 3/3, 55.84 s, +0.266 m | 3/3, 57.45 s, +0.313 m | 57 / 0 |
| Map 2 | 3/3, 58.43 s, +0.225 m | 3/3, 55.73 s, +0.271 m | 3/3, 56.79 s, +0.274 m | 67 / 0 |
| Map 3 | 3/3, 76.74 s, +0.202 m | 3/3, 55.23 s, +0.304 m | 3/3, 55.74 s, +0.290 m | 66 / 0 |
| Map 4 | 3/3, 72.42 s, +0.240 m | 3/3, 61.40 s, +0.239 m | 3/3, 62.95 s, +0.265 m | 39 / 0 |
| Map 5 | 3/3, 74.55 s, +0.212 m | 3/3, 61.22 s, +0.222 m | 3/3, 57.76 s, +0.239 m | 60 / 0 |
| Map 6 | 3/3, 85.69 s, +0.218 m | 3/3, 73.03 s, +0.180 m | 3/3, 65.35 s, +0.235 m | 56 / 0 |
| Map 7 | 3/3, 80.06 s, +0.246 m | 3/3, 68.35 s, +0.255 m | 3/3, 68.40 s, +0.121 m | 59 / 1 |
| Map 8 | 3/3, 87.25 s, +0.276 m | 3/3, 61.40 s, +0.199 m | 3/3, 61.37 s, +0.224 m | 66 / 0 |
| Map 9 | 3/3, 86.74 s, +0.223 m | 3/3, 74.16 s, +0.238 m | 3/3, 70.87 s, +0.179 m | 64 / 0 |
| Map 10 | 3/3, 92.94 s, +0.166 m | 3/3, 69.90 s, +0.182 m | 3/3, 76.02 s, +0.192 m | 61 / 0 |

합계는 세 모드 모두 30/30 완주·30/30 무충돌이다. Full과 Adaptive는
first-attempt 30/30이다. Sector는 최종 30행은 모두 성공했지만 Map 6 run1의 첫
시도가 OOM으로 죽어 first-attempt는 29/30이다.

Adaptive 전환은 stall-open 9회, trajectory-guard open 95회, 모든 원인을 합친
effective Full-open 595회였다. 자연 current-body OCCUPIED/brake는 Map 7의 1회였고
active-brake replacement는 0회였다.

## 7. 계산량과 대역폭

`algorithm_cpu_*`는 planner와 in-process filter를 포함한 cgroup CPU다. 100%는 한
logical core이므로 1.066 cores는 약 106.6%와 같은 뜻이다. DDS는 wire에 가장
가까운 비교를 위해 planner로 전달되는 cloud와 compact verdict만 합산했다.
Adaptive의 zero-copy raw input은 논리 입력량이지 DDS wire traffic이 아니므로 이
열에 더하지 않았다.

| mode | time, s | algorithm cores | algorithm core·s | end-to-end cores | end-to-end core·s | DDS cloud+verdict, MiB/s | ROG input, MiB/s | ROG ms/frame | PSS, MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 77.908 | 0.910 | 71.012 | 1.092 | 85.606 | 4.655 | 4.655 | 35.378 | 3190.32 |
| Sector | 63.625 | 1.067 | 69.851 | 1.282 | 84.040 | 3.139 | 3.139 | 13.256 | 3175.94 |
| Adaptive | 63.270 | 1.066 | 69.609 | 1.327 | 86.760 | 2.355 | 2.352 | 23.890 | 3182.29 |

Adaptive versus Full:

- mission time 18.789% 감소;
- DDS cloud+verdict 49.405%, ROG input 49.464% 감소;
- ROG per-frame compute 32.474% 감소;
- algorithm core·s 1.975% 감소;
- 그러나 mean algorithm cores는 17.122% 증가;
- end-to-end core·s는 1.348% 증가;
- PSS는 0.252% 차이로 사실상 동일.

Current-body tier 자체는 Adaptive에서 평균 약 10.000 Hz, 0.320 ms/verdict,
0.00340 core equivalent였다. compact body verdict traffic은 평균 0.001829 MiB/s다.
따라서 새 tier의 직접 비용은 작지만, 이 캠페인은 전체 end-to-end computation
reduction을 보여주지 않는다.

## 8. Sector 대조군 판정

이번 표본에서 Sector는 Adaptive보다 열화되지 않았다. 완주와 contact safety가
같고, 평균시간은 0.356 s만 길며 algorithm core·s와 end-to-end core·s는 오히려
조금 낮다. 따라서 이 결과만으로 “Adaptive가 Sector의 완주율/충돌률을 개선한다”는
논문 주장을 만들 수 없다.

다음 비교는 실패를 사후적으로 만들도록 threshold를 튜닝하는 방식이면 안 된다.
같은 10개 맵에서 sector half-angle을 사전 등록한 작은 sweep으로 바꾸고, 각 angle의
고정 Sector와 동일 base angle을 쓰는 Adaptive를 paired 비교해야 한다. 그렇게 해야
angular information loss가 실제로 필요한 구간과 Adaptive full-open의 회복 효과를
분리할 수 있다. 새 맵 일반화 없이도 가능하지만, 현 ±60° 조건만으로는 식별력이 없다.

## 9. Sector Map 6 OOM 첫 시도

Map 6 run1 Sector attempt1은 약 41 s wall time에 로그 exception 없이 중단됐고
runner가 `fsm_node exited during mission`으로 재시도했다. 계측은 다음을 보였다.

- `oom_kill_delta=1`;
- FSM PSS 약 3.14 GiB에서 6.31 GiB로 증가;
- system available minimum 1393.18 MiB;
- swap used 2047.996 MiB로 포화;
- cgroup peak memory 10504.86 MiB;
- memory PSI some/full max 1.23/1.20%;
- 마지막 planner 로그는 정상적인 `ReplanOnce` overtime이며 C++ exception은 없음.

재시도는 80.56 s에 무충돌 완주했고 다음 Map 6 두 회도 first-attempt 완주했다.
Sector는 risk verdict/current-body tier가 비활성화되어 있으므로 이 OOM은 이번 새
safety tier가 만든 현상이 아니다. 다만 2,048 iteration cap이 모든 transient
allocation/RSS growth를 막는다는 의미도 아니며, planner/optimizer memory 안정성은
별도 미해결 문제다. 원인 확정 전에는 이를 단순 외부 infrastructure fault로만
표현하지 않는다.

## 10. 검증과 evidence

- Release build: `mars_quadrotor_msgs`, `marsim_render`, `perfect_drone_sim`,
  `super_planner`, `mission_planner` 모두 PASS.
- runner/parser pytest: 7 PASS.
- standalone native geometry/stats/witness equivalence: PASS, retained 3,
  witness 3.
- `git diff --check`: PASS.

주요 raw/summary:

- active replacement gate:
  `results/frontend_body_active_brake_fault_seed1_dedupe_raw_20260902.csv`
- Map 10 n=30:
  `results/frontend_body_active_brake_map10_{n10,additional_n20}_raw_20260902.csv`
- Map 7 Full/Adaptive n=20:
  `results/frontend_body_map7_full_adaptive_n20_raw_20260902.csv`
- Map 1--10 Full/Adaptive n=3:
  `results/frontend_body_full_adaptive_map1_10_n3_raw_20260902.csv`
- Map 1--10 Sector n=3:
  `results/frontend_body_sector_map1_10_n3_raw_20260902.csv`
- Map 6 Sector OOM attempt:
  `results/frontend_body_sector_map1_10_n3_artifacts_20260902/seed6_run1_sector.attempt1.{memory,cgroup}.csv`
  및 같은 prefix의 `.stack.log`
- combined map/mode summary and Full-to-Adaptive reductions:
  `results/frontend_body_map1_10_three_mode_n3_{summary,reductions}_20260902.csv`

## 11. 주장 경계와 다음 순서

현재 주장 가능한 것은 다음과 같다.

1. 5 Hz generation race를 보완하는 독립 current-body safety contract를 구현했다.
2. stale/source-stale rejection, generation independence, duplicate idempotence 및
   active-brake one-shot replacement를 결정론적으로 검증했다.
3. Map 10 n=30과 전체 10맵 n=3에서 관측 접촉은 0이었다.
4. Full 대비 Adaptive의 planner DDS와 ROG input/프레임 비용은 크게 줄었다.

아직 주장할 수 없는 것은 population collision-free 보장, Adaptive의 Sector 대비
통계적 안전 우위, 전체 CPU/메모리 절감이다. 다음 구현/실험 우선순위는
`(1)` Sector/Adaptive paired angle operating-envelope 실험,
`(2)` OOM 재현 시 allocator/optimizer phase별 RSS 계측과 hard memory/deadline guard,
`(3)` 식별력 있는 조건에서 필요한 표본수로 재검증 순이다.
