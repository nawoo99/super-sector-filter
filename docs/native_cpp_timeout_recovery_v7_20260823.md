# Native C++ Adaptive n=5와 stopped A* timeout recovery (2026-08-23)

## 결론

v=7, `loop24.txt`, timeout 240 s, fixed static-PCD monitor, seed1-10 각 5회에서
수정 후 Full과 native C++ Adaptive가 모두 **50/50 완주**, **live 접촉 0/50**,
**static-PCD 접촉 0/50**을 관측했다. 패치 전 같은 세션의 독립 코호트는 Full
49/50, Adaptive 48/50이었고 실패 세 건은 모두 seed9의 정지 상태 계획
정체였다.

이번 변경은 안전 조건을 느슨하게 하지 않았다. `PlanFromRest()`의 성공/실패를
Adaptive sensing recovery에도 발행하고, certified stop에서 발생한 bounded A*
`TIME_OUT`만 기존 `NO_PATH`와 같은 topology-change 신호로 처리한다. 이동 중
`TIME_OUT`은 계속 제외한다. raw-cloud CIRI shadow는 계속 기본값 `false`이며
실제 브레이크 결정에 연결하지 않았다.

## 원인과 변경

패치 전 실패 로그의 공통 루프는 다음과 같았다.

1. 기체가 정지한 상태에서 `GENERATE_TRAJ -> PlanFromRest`로 진입한다.
2. A*가 제한 시간 안에 후보를 만들지 못해 `TIME_OUT`을 반환한다.
3. 기존 topology recovery는 `NO_PATH`만 실패 증거로 인정한다.
4. 같은 시작점과 같은 blocker/topology를 계속 재시도하다 240초를 소진한다.

Adaptive에는 두 번째 단절도 있었다. `/planning/replan_status`가
`ReplanOnce()`에서만 발행되어, 한 번도 `FOLLOW_TRAJ`에 진입하지 못한
`PlanFromRest` 실패는 C++ filter의 bounded full-open recovery를 활성화하지
못했다.

수정 파일은 다음 두 개다.

- `super_planner/src/super_core/fsm.cpp`: `PlanFromRest()` 직후 성공 여부를
  `/planning/replan_status`로 발행한다.
- `super_planner/src/super_core/super_planner.cpp`: `planning_from_rest=true`인
  `NO_PATH` 또는 `TIME_OUT`을 stopped recovery evidence로 처리한다. blocker가
  없으면 bounded vertical recovery, blocker가 있으면 기존 epoch reset 또는
  vertical branch를 사용한다. 로그에 `reason=astar_timeout`과
  `reason=astar_no_path`를 구분해 남긴다.

이 범위 제한이 중요하다. 이동 중 A* timeout에는 이미 committed trajectory가
안전 책임을 지므로, 이를 topology 변경으로 확대하지 않았다.

## 테스트 순서

모든 캠페인은 `/root/super_ws/src/SUPER`에서 Release 빌드한 동일 바이너리와
`static_seedmaps_guard_viability_tight_v7.yaml`을 사용했다. Full은 필터 없이
`/cloud_registered`를 직접 ROG-Map에 넣었고, Adaptive는 C++
`native_sector_cpp`, `strict-burst`, 0.6 s one-shot full-open, 1.4 s cooldown,
5 Hz publication cap을 사용했다.

| 단계 | Full | Adaptive C++ | live/static 접촉 | 용도 |
|---|---:|---:|---:|---|
| 패치 전 seed1-10 x5 | 49/50 | 48/50 | 모두 0 | 동일 현상 재현 |
| 패치 후 seed9 targeted x5 | 5/5 | 5/5 | 모두 0 | 취약 시드 국소 확인 |
| 패치 후 seed1-10 x1 | 10/10 | 10/10 | 모두 0 | 전체 시드 smoke |
| 패치 후 seed1-10 x5 | **50/50** | **50/50** | **모두 0** | 최종 기능 gate |

이 코호트들은 순차 실행한 독립 반복이며 paired trial이 아니다. McNemar 검정을
하지 않았고, 아래 50/50은 population 100% 보장이 아니라 이번 50회에서의 관측값이다.

## 최종 seed별 결과

| seed | Full 완주 | Full 최저 clearance | Adaptive 완주 | Adaptive 최저 clearance |
|---:|---:|---:|---:|---:|
| 1 | 5/5 | +0.208 m | 5/5 | +0.147 m |
| 2 | 5/5 | +0.177 m | 5/5 | +0.218 m |
| 3 | 5/5 | +0.242 m | 5/5 | +0.190 m |
| 4 | 5/5 | +0.209 m | 5/5 | +0.249 m |
| 5 | 5/5 | +0.187 m | 5/5 | +0.239 m |
| 6 | 5/5 | +0.221 m | 5/5 | +0.164 m |
| 7 | 5/5 | +0.206 m | 5/5 | +0.175 m |
| 8 | 5/5 | +0.228 m | 5/5 | +0.221 m |
| 9 | **5/5** | +0.155 m | **5/5** | +0.139 m |
| 10 | **5/5** | +0.213 m | **5/5** | +0.180 m |
| 전체 | **50/50** | **+0.155 m** | **50/50** | **+0.139 m** |

모든 최종 run은 `run_valid=True`였고 waypoint 5/5를 기록했다. 두 모드의 live와
static-PCD contact episode도 모두 0이다. 최고속도는 Full 7.083 m/s, Adaptive
7.022 m/s여서 기준 속도 조건이 유지됐다.

## recovery 실행 증거

최종 Adaptive 50회 로그에는 `reason=astar_timeout` recovery action이 5회 있었다.

- seed6 run1: blocker가 있는 상태에서 epoch reset 1회
- seed7 run2: base vertical recovery 2회
- seed9 run3/run4: 시작점에서 base vertical recovery 각 1회

이 네 affected run은 모두 완주했고 접촉도 없었다. 즉 새 분기는 단순히 죽은
코드가 아니라 최종 코호트에서 실제 liveness recovery로 실행됐다. 최종 Full
50회에는 stopped `astar_timeout`이 발생하지 않았고, seed10 run2에서 기존
`reason=astar_no_path` recovery 1회가 실행된 뒤 완주했다. targeted Full seed9
검증에서는 새 timeout 분기가 실행되는 것을 실행 당시 확인했지만, `/tmp`의 같은
이름 로그는 뒤의 정식 캠페인이 덮어썼으므로 최종 증거 수에는 합산하지 않는다.

## 연산량

최종 n=50 원시 집계는 다음과 같다. 합계 mission time으로 rate를 가중하고,
점수와 mapping time은 실제 map update 수로 가중했다.

| 지표 | Full | Adaptive C++ | Adaptive 변화 |
|---|---:|---:|---:|
| map commit rate | 4.028 Hz | 3.651 Hz | -9.34% |
| processed points/update | 27,151 | 20,206 | **-25.58%** |
| processed throughput | 109.35 kpts/s | 73.78 kpts/s | **-32.53%** |
| mapping time/update | 30.880 ms | 21.734 ms | **-29.62%** |
| mapping work/mission | 12.873 s | 6.644 s | **-48.39%** |
| FSM+filter CPU-work/mission | 68.677 CPU-s | 72.394 CPU-s | +5.41% |

Adaptive filter 자체는 input 6.841 Hz, publish 4.320 Hz, retained points
46.02%, 2.700 CPU-s/mission이었다. 처리점/update와 mapping/update 감소는 최종
50회에서도 명확히 유지됐다.

다만 end-to-end CPU 수치는 이 n=50만으로 확정하지 않는다. Full 캠페인은
Adaptive 다음에 순차 실행됐고 seed5 run5에서 `fsm_node` infrastructure retry가
1회 발생했다. 그 직후 관측한 Full `fsm_node` RSS는 약 4.38 GiB였고 host swap
2 GiB가 모두 사용 중이었다. 커널 OOM 기록은 없어 종료 원인은 확정할 수 없지만,
이후 Full mission time이 90-193초로 늘고 CPU percentage가 낮아져 wall-time/CPU
비교가 오염됐다. 실제로 성공 mission 평균이 Adaptive 83.72초, 뒤에 실행한 Full
103.51초로 역전됐다.

동일 패치의 앞선 seed1-10 x1 성능 smoke에서는 Adaptive가 Full 대비
processed points/update 28.40%, throughput 60.53%, mapping/update 43.31%,
mapping work/mission 65.80%, combined CPU-work 15.62%를 줄였다. 패치 전 동일 세션
n=50에서도 combined CPU-work가 11.62% 낮았다. 따라서 native 전환과 map workload
감소 방향은 지지되지만, **patched n=50 end-to-end CPU 감소를 확정하려면 자원이
깨끗한 호스트에서 순서를 교차한 재측정이 필요하다.**

## 산출물과 해석 제한

- 패치 전 원시: `results/full_direct_strict_v7_n5_raw_20260823.csv`,
  `results/adaptive_cpp_strict_v7_n5_raw_20260823.csv`
- 패치 후 원시: `results/full_direct_strict_v7_timeoutfix_n5_raw_20260823.csv`,
  `results/adaptive_cpp_strict_v7_timeoutfix_n5_raw_20260823.csv`
- 요약: `results/full_adaptive_timeoutfix_summary_20260823.csv`

이번 결과는 사용자가 요구한 기능 패턴 중 Full/Adaptive의 관측 100% 완주와
0 contact, 그리고 Adaptive의 map workload 감소를 만족한다. fixed Sector의
의도적 성능 저하는 2026-08-22 §8.17의 46/50 static-safe 결과가 현재 대조군이다.
이번 수정은 Sector를 재실행하거나 정책을 바꾸지 않았다. 실기 안전성,
population-level 100%, paired 통계, authoritative raw-CIRI brake를 주장하지 않는다.
