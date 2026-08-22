# Strict v7 Full/Sector/Adaptive seed1-10 × n=5

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
