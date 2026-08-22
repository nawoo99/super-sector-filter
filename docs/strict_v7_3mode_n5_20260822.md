# Strict v7 Full/Sector/Adaptive seed1-10 × n=5

> **2026-08-23 native 후속:** strict Adaptive를 별도 C++ ROS2 node로 옮긴
> seed1-10 n=1 두 cohort는 모두 raw/static-safe 10/10이었다. 정확한 CPU cohort의
> filter/전체 CPU-work는 2.522/54.559 CPU-s/mission으로 Python Adaptive보다
> 76.17%/14.88% 낮고 Full보다 전체가 2.44% 낮게 관측됐다. 다만 seed10 live-only
> 경계 event 1회(static contact 0)가 있었고 n=1-per-seed라 아래 n=50 결과를
> 대체하지 않는다. 상세는 `docs/adaptive_cpp_v7_n1_20260823.md`와 viability
> §8.19를 볼 것.

> **후속 결과:** 이 문서 아래의 `Adaptive liveness 복구와 발행률 제한` 절이
> 최초 Adaptive 49/50 행을 대체한다. 최종 별도 Adaptive cohort는 50/50
> raw/safe completion과 접촉 0을 관측했고, Full 대비 mapping throughput은
> 25.55% 감소했다. 다만 Python filter를 포함한 end-to-end CPU-work는 Full보다
> 14.61% 높아 전체 CPU 감소까지 달성한 것은 아니다.

실험일은 2026-08-22이며 속도는 `v=7`, 경로는 `loop24.txt`, timeout은
240 s다. 각 모드는 seed1-10에서 5회씩 실행했다. Full 50회와
Sector/Adaptive 100회는 서로 다른 캠페인으로 실행했으므로 Full과 다른 두 모드
사이에 paired 추론은 하지 않는다. Sector/Adaptive는 동일 seed/run의 모드 순서를
회전했다.

Full은 `/cloud_registered`를 ROG-Map에 직접 연결하고
`static_seedmaps_guard_viability_tight_v7.yaml`을 사용했다. Sector와 Adaptive는
`/cloud_sector`와 `static_seedmaps_guard_viability_tight_v7_filtered.yaml`, 새
`strict-burst` 필터 프로파일을 사용했다. 모든 유효 run에서 seed별 static PCD가
로드됐고, point count는 241,490-1,042,220이었다. Full seed5에서 odometry가 전혀
오지 않은 infrastructure HUNG 1회는 자동 재시도됐으며 아래 150개 유효 run에는
포함하지 않았다.

## 결론

| mode | raw 완주 @240 | raw 완주 @180 | 안전 완주 @240 | live 접촉 run/episode | static 접촉 run/episode | 최악 body clearance | 평균 시간 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | **50/50 (100%)** | 48/50 (96%) | **50/50 (100%)** | **0/50, 0** | **0/50, 0** | +0.110 m | 117.61 s |
| Sector | **50/50 (100%)** | 49/50 (98%) | **46/50 (92%)** | **4/50, 6** | **4/50, 4** | -0.184 m | 111.78 s |
| Adaptive | **49/50 (98%)** | 46/50 (92%) | **49/50 (98%)** | **0/50, 0** | **0/50, 0** | +0.103 m | 123.27 s |

여기서 안전 완주는 `waypoint 5/5 AND static-PCD contact 0`이다. Sector는 raw
완주만 보면 50/50이지만 네 run이 실제 PCD에 침범했으므로 planner의 안전한
완주로 셀 수 없다. Adaptive는 이 네 접촉을 모두 제거해 안전 완주를
92%에서 98%로 회복했지만, seed9 timeout 1건 때문에 raw 완주율은 Sector보다
낮다. 따라서 현재 결과는 사용자가 의도한 안전/연산량 패턴을 지지하지만,
Adaptive liveness까지 완전히 회복했다는 결과는 아니다.

## 연산량과 주파수

| mode | map commit | cloud callback | 처리점/update | 처리량 | 입력점 감소 | full-open frame duty | mapping/update | raycast | update | inflation | FSM CPU | filter CPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 2.977 Hz | 미계측 | 27,158.8 | 80.858 kpts/s | 기준 | 해당 없음 | 22.972 ms | 14.581 ms | 8.389 ms | 1.915 ms | 47.55% | 해당 없음 |
| Sector | 3.216 Hz | 4.070 Hz | 12,928.7 | 41.579 kpts/s | **46.09%** | 0% | 9.869 ms | 6.339 ms | 3.529 ms | 1.085 ms | 47.11% | 11.00% |
| Adaptive | 2.816 Hz | 3.982 Hz | 16,149.3 | 45.474 kpts/s | **30.30%** | 15.28% | 12.132 ms | 7.764 ms | 4.367 ms | 1.284 ms | 42.06% | 11.36% |

Full 대비 변화는 다음과 같다.

| mode | 처리점/update | 처리량 | mapping/update | raycast | update | inflation | 평균 mission time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sector | **-52.40%** | **-48.58%** | **-57.04%** | -56.52% | -57.94% | -43.37% | -4.96% |
| Adaptive | **-40.54%** | **-43.76%** | **-47.19%** | -46.75% | -47.95% | -32.94% | +4.81% |

설정값은 모든 모드가 LiDAR 10 Hz, replan 15 Hz, main FSM 100 Hz, command
100 Hz로 동일하다. 표의 map/cloud 값은 달성된 관측치이지 설정 주파수가 아니다.
Full direct 경로는 의도적으로 filter observer를 거치지 않아 cloud callback Hz를
계측하지 않았으며, 이를 10 Hz로 간주해서는 안 된다. 평균값은 run 평균이 아니라
총 mission time 또는 map commit 수로 가중한 값이다.

## seed별 안전성과 liveness

| seed | Full raw/safe | Sector raw/safe | Adaptive raw/safe | Sector static 접촉 run | Adaptive static 접촉 run | 평균 시간 F/S/A |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 77.17 / 63.08 / 73.46 s |
| 2 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 78.59 / 63.05 / 68.27 s |
| 3 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 102.16 / 93.66 / 113.27 s |
| 4 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 115.96 / 118.61 / 115.03 s |
| 5 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 102.23 / 110.71 / 118.78 s |
| 6 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 | 0 | 0 | 141.70 / 121.68 / 115.49 s |
| 7 | 5/5 · 5/5 | 5/5 · **3/5** | 5/5 · 5/5 | **2** | 0 | 135.65 / 132.81 / 161.80 s |
| 8 | 5/5 · 5/5 | 5/5 · **4/5** | 5/5 · 5/5 | **1** | 0 | 139.40 / 109.33 / 136.68 s |
| 9 | 5/5 · 5/5 | 5/5 · 5/5 | **4/5 · 4/5** | 0 | 0 | 143.76 / 141.57 / 168.58 s |
| 10 | 5/5 · 5/5 | 5/5 · **4/5** | 5/5 · 5/5 | **1** | 0 | 139.51 / 163.35 / 161.37 s |

Sector 접촉은 seed7 run2/run4, seed8 run3, seed10 run5다. 네 건 모두 live-cloud와
static PCD 양쪽에서 확인됐다. 최초 live marker 속도는 5.45-6.91 m/s였고 static
body clearance는 각각 -0.179, -0.174, -0.035, -0.184 m였다. 따라서 이전의
live-only 오탐과 달리 실제 접촉으로 분류한다.

Adaptive 실패는 seed9 run1 하나다. 240 s에 waypoint 4/5, 최종 위치
`(6.012, -8.327, 2.402)`, static body clearance +0.173 m였다. 지도는 계속
갱신됐고 trajectory commit도 끝까지 발생했다. 로그에는 guard clearance reject
75회, reroute arm 21회, search 46회, stall 23회, accepted brake 96회가 있어
단일 generation/map freeze가 아니라 마지막 waypoint로 가는 동안 stop/recovery와
topology 전환이 누적된 liveness churn이다. Adaptive가 이 run에서도 입력점의 77.16%를
유지했으므로 full-open 비율만 더 높이는 튜닝은 직접적인 해법으로 보기 어렵다.

## 통계와 해석 제한

동일 seed/run인 Sector/Adaptive의 안전 완주 discordant pair는 Adaptive만 성공 4,
Sector만 성공 1이며 exact two-sided McNemar `p=0.375`다. static contact는
Sector만 4, Adaptive만 0으로 `p=0.125`, raw 완주는 Sector만 1, Adaptive만 0으로
`p=1.0`이다. 현재 n=50으로 population 우월성을 주장할 수 없다. Full은 별도
캠페인이므로 이 paired 검정에 넣지 않았다.

현재 코드는 saturation 시 수직 recovery를 1회 허용하는 bounded branch도 포함하지만
150회에서 해당 marker는 0회였다. 따라서 Full 50/50이나 Adaptive 결과를 이 branch의
효과로 설명하면 안 된다. raw-cloud CIRI는 계속 shadow-only/default false다.

원시는 `results/strict_v7_full_n5_raw_20260822.csv`와
`results/strict_v7_sector_adaptive_n5_raw_20260822.csv`, 요약은
`results/strict_v7_3mode_n5_summary_20260822.csv`에 보존했다.

## 후속: Adaptive liveness 복구와 발행률 제한

위 Adaptive의 seed9 timeout을 재분석하고 같은 날 후속 실험을 수행했다. 실패
run은 마지막 목표로 가는 단순 지연이 아니라, 세 번째 목표 구간에서 약 5 m/s로
비행하던 중 map-stale stop/recovery가 누적된 뒤 `(18.633, -24.281, 1.332)`에
정지한 사례였다. static-PCD body clearance는 아직 +0.091 m였지만 CIRI가 보는
가까운 장애물 거리는 약 0.182 m여서 시작점 corridor 자체가 infeasible했다.
그 뒤에는 같은 EXP/backup fallback이 즉시 `OCCUPIED`로 거절되어 240 s까지
certified hold에서 탈출하지 못했다.

replan failure 세 번마다 full cloud를 여는 기존 nearly-continuous guard를 그대로
복원하지 않고, 매 trigger가 반드시 끝나는 one-shot worker를 추가했다. 첫 후보는
0.25 s burst/1.75 s cooldown이었다. 이것은 seed9 targeted 5/5를 통과했지만 broad
seed1-10 x n=5에서 다시 seed9 run5가 waypoint 3/5, 240 s timeout되어 **49/50**에
그쳤다. 접촉은 0이었지만 liveness 목표 때문에 불채택했다.

0.6 s one-shot/1.4 s cooldown은 별도 broad test에서 50/50을 만들었으나 rate cap이
없을 때 map commit이 빨라져 처리량이 Full보다 16.56% 높아졌다. 그 cohort에는
static clearance +0.015 m와 7.808 m/s 과속도 각각 한 건 있었다. 따라서 burst는
0.6 s로 유지하되 Adaptive가 ROG-Map으로 발행하는 filtered cloud에 5 Hz 상한을
추가했다. limiter는 최신 input callback과 recovery 상태 갱신은 모두 수행하고,
이상적인 누적 deadline을 기준으로 publication만 생략한다. 현재 입력 시각으로
deadline을 매번 재설정해 실제 2.65 Hz밖에 내지 못한 첫 구현과 4 Hz 후보는
불채택했다. 최종 5 Hz 설정의 실제 발행률은 4.188 Hz였다.

최종 후속 cohort는 v=7, `loop24.txt`, timeout 240 s, seed1-10 x n=5,
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, static-PCD monitor라는 동일
조건에서 Adaptive만 다시 실행했다.

| mode/cohort | raw 완주 | 안전 완주 | live 접촉 | static 접촉 | 최악 clearance | 평균/최대 시간 | 최고속도 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 기존 Full direct | **50/50** | **50/50** | 0/50 | 0/50 | +0.110 m | 117.61 / 198.25 s | 7.054 m/s |
| 기존 fixed Sector | **50/50** | **46/50** | 4/50 | 4/50 | -0.184 m | 111.78 / 192.76 s | 7.108 m/s |
| **Adaptive recovered** | **50/50** | **50/50** | **0/50** | **0/50** | +0.100 m | **88.84 / 133.50 s** | 7.102 m/s |

안전 완주는 여전히 waypoint 5/5와 static-PCD contact 0을 모두 요구한다. 최종
Adaptive는 180 s 기준도 50/50이었다. 속도 7.1 m/s 초과는 seed6 run2의
7.102 m/s 한 건으로, 과거 7.808 m/s는 재현되지 않았지만 Full의 최대 7.054 m/s
보다는 높다.

| seed | raw/safe | 평균 시간 | 최악 static clearance | 최고속도 | raw input 전달률 |
|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 · 5/5 | 65.69 s | +0.220 m | 7.000 | 39.62% |
| 2 | 5/5 · 5/5 | 60.47 s | +0.291 m | 7.001 | 38.55% |
| 3 | 5/5 · 5/5 | 75.19 s | +0.224 m | 7.000 | 43.43% |
| 4 | 5/5 · 5/5 | 84.80 s | +0.222 m | 7.000 | 45.31% |
| 5 | 5/5 · 5/5 | 76.45 s | +0.100 m | 7.001 | 43.86% |
| 6 | 5/5 · 5/5 | 92.68 s | +0.126 m | 7.102 | 47.19% |
| 7 | 5/5 · 5/5 | 103.67 s | +0.212 m | 7.004 | 50.82% |
| 8 | 5/5 · 5/5 | 92.37 s | +0.182 m | 7.001 | 49.56% |
| 9 | 5/5 · 5/5 | 118.16 s | +0.211 m | 7.000 | 52.21% |
| 10 | 5/5 · 5/5 | 118.97 s | +0.202 m | 7.001 | 50.59% |

최종 연산 지표는 다음과 같다. `raw input 전달률`은 각도 절단뿐 아니라 5 Hz
publication cap으로 생략한 frame까지 포함하므로 순수 angular-kept 비율이 아니다.
입력 callback 6.509 Hz에서 상태 판정은 계속 실행됐고 실제 발행은 4.188 Hz였다.

| mode | map commit | 처리점/update | 처리량 | mapping/update | 임무당 mapping work | FSM CPU | filter CPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 2.977 Hz | 27,158.8 | 80.858 kpts/s | 22.972 ms | 8.044 s | 47.55% | - |
| Sector | 3.216 Hz | 12,928.7 | 41.579 kpts/s | 9.869 ms | 3.548 s | 47.11% | 11.00% |
| **Adaptive recovered** | 3.132 Hz | 19,223.0 | 60.197 kpts/s | 15.528 ms | 4.320 s | 60.23% | 11.91% |

Adaptive recovered의 Full 대비 변화는 처리점/update **-29.22%**, 처리량
**-25.55%**, mapping/update **-32.40%**, 임무당 누적 mapping work
**-46.29%**다. 따라서 지도 처리 기준에서는 Full과 Sector 사이의 의도한
trade-off가 유지된다. 단, Python filter까지 합친 관측 CPU-work는 임무당
64.09 CPU-s로 Full의 55.92 CPU-s보다 **14.61% 높다**. 이는 프로토타입 필터
오버헤드가 남아 있다는 뜻이며, 전체 시스템 CPU까지 감소했다고 주장하면 안 된다.
그 주장을 하려면 C++/in-map filter 구현 또는 동등한 end-to-end CPU 최적화 후 별도
재측정이 필요하다.

Full/Sector와 새 Adaptive는 같은 seed/run 번호를 썼지만 서로 다른 캠페인에서
실행됐으므로 paired McNemar 검정을 적용하지 않는다. 관측 50/50은 이번 cohort의
결과이지 population 100%나 flight-ready 증명이 아니다. raw-cloud CIRI shadow는
계속 default false이고 live brake 결정에 연결되지 않았다.

불채택 0.25 s 원시는
`results/adaptive_replan025_strict_v7_n5_raw_20260822.csv`, 최종 원시는
`results/adaptive_replan060_cap5_strict_v7_n5_raw_20260822.csv`, 새 요약은
`results/strict_v7_adaptive_recovery_n5_summary_20260822.csv`에 보존했다.
