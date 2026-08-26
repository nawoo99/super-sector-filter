# Guarded v7 velocity bound and stopped-recovery liveness (2026-08-26)

## 결론

Reliable-link n=3 gate의 Full seed7 run3에서 v=7 설정인데도 odometry 수평
속도 10.027 m/s가 기록된 원인을 비상정지 초기상태 추정의 시간축 오류로
확정했다. Planner가 위치 두 개를 odometry 표본으로 사용하면서 시간 차이는
그 표본의 수신 시각이 아니라, 서로 다른 guard callback이 표본을 읽은 시각으로
계산했다. 그 결과 정상 `PositionCommand` 6.323 m/s를 6 ms callback 간격으로
나눠 10.055 m/s라는 가짜 `odom_motion`을 만들고, 그 상태에서 시작하는 brake를
인증·발행했다.

수정은 세 경계로 나눴다.

1. Guarded candidate를 commit하기 전에 polynomial의 정확한 최대 속도를 구하고,
   v=7을 넘으면 공간 경로를 바꾸지 않는 time scaling을 적용한다. 재검사에도
   실패하거나 값이 비유한이면 candidate를 거부한다.
2. Emergency brake의 정확한 최대 속도도 acceleration/jerk와 함께 검사하고,
   위치 차분의 시간축을 `robot_state_.rcv_time`으로 통일한다.
3. Polynomial publish와 매 `PositionCommand` sample 직전에 다시 속도 경계를
   검사한다. 정상 command 위반은 발행하지 않고 기존 certified
   stop-and-reroute 경로로 보낸다.

과거 seed10에서 실제 contact를 만든 `odometry twist -> RobotState.v` 직접
대입은 되살리지 않았다. Raw-cloud CIRI도 계속 default false이고 실제 비행
결정에 연결하지 않았다.

## 재현과 근본 원인

원본 반례는
`/tmp/reliable_link_repeated_3mode_seed6_10_n3_artifacts/`
`seed7_run3_full.attempt1.stack.log`의 연속된 두 marker다.

- `replan_post_uncertified`: fresh command 6.323 m/s, command age 0.004 s,
  UNOBSERVED라 brake 후보 거부
- 5.2 ms 뒤 `emergency_stop_retry`: `motion_dt=0.006 s`,
  `odom_motion=10.055 m/s`, command과의 차이 3.733 m/s
- 잘못 추정한 10.055 m/s 초기상태의 0.754 s brake가 dynamics/path 검사를
  통과해 발행됨

PerfectDrone은 `PositionCommand.velocity`를 odometry twist로 복사한다. 따라서
10.027 m/s odometry 기록은 monitor의 위치 미분 노이즈가 아니라 planner가 실제로
보낸 속도 명령이었다. 동시에 정상 committed trajectory의 guard marker는 최대
7.000 m/s였으므로 optimizer 경로 자체만 조사해서는 이 반례를 찾을 수 없다.

오류 코드는 두 odometry 위치를
`selection_wt - recovery_motion_last_wt_`로 나눴다. `selection_wt`는
odometry 표본시각이 아니라 동기/비동기 guard callback이 해당 상태를 읽은
wall/sim 시각이다. 동일하거나 10 ms cadence인 odometry 갱신을 5~6 ms 간격의
retry가 읽으면 분자와 분모의 표본 정의가 달라진다. 수정 후에는 위치와 시각이
모두 같은 odometry 표본인 `robot_state_.p`와 `robot_state_.rcv_time`에서 나온다.

## 구현

Source-of-truth 변경은 `/root/super_ws/src/SUPER`에서 했고 다음 파일로 미러한다.

- `super_planner/include/super_core/super_planner.h`
  - configured maximum velocity accessor
- `super_planner/src/super_core/super_planner.cpp`
  - guarded candidate의 exact max-velocity commit gate
  - 공간 경로를 보존하는 position/yaw/backup metadata time scaling
  - slowdown/rejection marker
- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`
  - odometry receive-time 기반 emergency motion estimate
  - exact brake max-velocity validation
  - polynomial/sample publication 경계 validation
  - emergency sample에도 source trajectory generation 부여
- `scripts/native_campaign/native_loop_monitor.py`
  - 3-D command/odometry 속도, 최초 위반 context, 최대속도 context
- `scripts/native_campaign/native_campaign.py`
  - 선택한 SUPER config의 `max_vel` 자동 검출
  - speed-qualified `run_valid`; 실제 속도 위반은 infrastructure retry로 숨기지 않음

Guarded candidate가 제한을 초과하면 scale은
`max_velocity / velocity_limit * 1.001`이다. 위치 polynomial을
`q(t') = p(t'/scale)`로 변환하기 때문에 공간 경로는 같고 속도·가속도·jerk만
낮아진다. Scaling 뒤 exact extremum을 다시 검사한다. Runtime과 monitor는
부동소수점/메시지 변환을 위해 0.1%와 절대 0.01 m/s의 명시적 허용오차를 각각
사용한다. 이 허용오차는 7.01 m/s보다 작은 수치 오차를 허용한다는 뜻이며,
수학적으로 정확한 `<= 7.000000` 증명과 같지 않다.

Emergency brake가 외란으로 이미 제한을 넘은 측정 상태에서 시작하면 brake 자체를
막을 수 없으므로, 그 brake는 `max(configured limit, initial speed)`보다 새 최대를
만들지 않는 조건으로 검사한다. 이 경우 monitor는 관측된 제한 초과를 그대로
invalid로 기록한다. 정상 trajectory가 제한을 넘는 경우에는 publish하지 않고
`command_velocity_limit` emergency path로 들어간다.

## 검증 방법

Build는 ROS Humble 환경에서 `super_planner`를 sequential executor로 두 번
완료했다. 첫 build는 66초, generation context 추가 뒤 build는 46초였으며 기존
constructor reorder warning 외 새 오류는 없었다.

집중 재현은 seed7 Full로 먼저 수행했다. 그 뒤 seed6-10의 Full/Sector/Adaptive를
mode order를 회전해 각 3회 검증한다.

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed6 seed7 seed8 seed9 seed10 \
  --modes full sector adaptive --runs 2 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config \
    static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-static-pcd --loop-timeout 240 \
  --filter-profile strict-burst --filter-backend cpp \
  --adaptive-pre-stale-ack-retry-age-s 0 \
  --filtered-reliable-map-link
```

여기서 `--runs 2` 결과는 바로 앞의 동일 코드 n=1 gate와 합쳐 맵·모드당 n=3으로
집계한다. 최종 표와 raw artifact 경로는 반복 gate 종료 후 이 문서에 기록한다.

## 검증 결과

Seed7 Full 집중 검증 4회는 모두 완주, contact 0, static-PCD collision 0,
speed exceedance 0이었다. 최대 3-D command/odometry 속도는 7.006587 m/s였고,
한 candidate가 7.017723에서 6.993007 m/s로 time-scaled됐다. 원본 반례의
10.055 m/s motion estimate는 재발하지 않았으며 새 로그의 motion estimate는
최대 2.293 m/s, 최소 유효 표본간격 0.010 s였다.

맵 6-10 반복을 동일 코드로 맵·모드당 3회까지 넓히자 속도는 45/45 유효했지만
서로 다른 liveness 반례 두 개가 나왔다. Full seed10 한 회는 정지 뒤 동일
PlanFromRest 경로를 재시도하다 timeout했고, Adaptive seed8 한 회는
166.68초였다. 후자는 full-cloud generation ACK가 한 번 유실돼 84초 뒤 다음
요청에서 회복한 사례였다. Recovery 중에만 0.75초 간격으로 최신 full generation
하나를 stop-and-wait 재전송하는 opt-in 경로를 추가했다. 정상 비행, pre-stale
재전송 및 기본값(0/off)은 바꾸지 않았다.

그 뒤 seed8 Adaptive n=5에서 generation ACK는 모두 0.128초 안에 왔지만 한
실행이 다시 151.77초였다. ACK는 0.042초 만에 처리됐고 실제 원인은 정지 위치의
동일 수평 출구를 59.69초 재시도한 것이었다. 최신 충돌점 하나는 optimizer
jitter로 차량 양쪽을 오갈 수 있어, 단일 `away-from-collision` 방향이 원래
차단된 경로 쪽으로 뒤집혔다. 정지·횟수 제한은 유지한 채 수평 네 방향을 각 한
번만 만들고 기존 hard guard를 통과한 첫 candidate만 commit하도록 바꿨다.
모두 거부되면 기존 vertical/certified reroute로 돌아간다.

보완 후 seed8 Adaptive n=5는 5/5 완주, contact/static-PCD collision 0,
speed-qualified 5/5였다. 시간은 70.40~91.47초(평균 81.21초), 최대 연속
recovery는 2.52초였다. 이 다섯 회에는 네 방향 local-escape 분기가 직접
실행되지는 않았으므로 branch proof는 아니다.

최종 동일 바이너리 map1-10 x Full/Sector/Adaptive x n=1 결과는 다음과 같다.
모든 행이 완주, live contact 0, static-PCD collision 0, speed-qualified였다.
`전환`은 Adaptive가 실제 full-view 상태로 열린 횟수이고 `guard`는 distinct
trajectory-guard active episode 수다.

| 맵 | Full 시간(s) | Sector 시간(s) | Adaptive 시간(s) | Adaptive 전환 | guard | Adaptive points/update | Adaptive update(ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| map1 | 55.69 | 56.47 | 59.89 | 18 | 9 | 12,975 | 8.74 |
| map2 | 54.71 | 68.24 | 58.77 | 12 | 4 | 12,596 | 9.57 |
| map3 | 71.89 | 57.40 | 73.63 | 15 | 21 | 18,354 | 10.47 |
| map4 | 79.45 | 66.46 | 72.07 | 12 | 21 | 21,180 | 11.64 |
| map5 | 64.68 | 83.57 | 72.80 | 17 | 22 | 22,067 | 11.71 |
| map6 | 69.01 | 72.59 | 79.69 | 16 | 20 | 25,393 | 12.25 |
| map7 | 78.02 | 83.12 | 91.32 | 1 | 51 | 29,146 | 12.92 |
| map8 | 73.16 | 77.84 | 97.81 | 8 | 37 | 29,114 | 14.60 |
| map9 | 76.55 | 78.28 | 83.67 | 14 | 24 | 37,051 | 11.10 |
| map10 | 87.25 | 76.58 | 99.20 | 10 | 32 | 37,082 | 10.72 |

모드 평균 시간은 Full/Sector/Adaptive 71.04/72.05/78.89초다. Update-weighted
연산 지표는 다음과 같다. 이 n=1 기술 통계에서 Adaptive는 Full 대비
points/update 12.88%, total/update 22.91%, map update 16.09%, FSM+filter
core-seconds 8.86%를 줄였고 평균 mission time은 11.04% 길었다. Sector는
각각 48.61/63.69/64.92/15.92%를 줄였지만 연구상 안전한 대안이 아니라 잘린
FoV control이다.

| 모드 | 평균 시간(s) | points/update | total/update(ms) | update(ms) | FSM+filter core-s | worst static clearance(m) | 최대 command(m/s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 71.04 | 28,793 | 39.97 | 13.57 | 740.42 | +0.174 | 7.005352 |
| Sector | 72.05 | 14,797 | 14.51 | 4.76 | 622.55 | +0.196 | 7.005983 |
| Adaptive | 78.89 | 25,083 | 30.81 | 11.39 | 674.84 | +0.175 | 7.005280 |

Adaptive의 full-view 전환은 총 123회, guard episode는 241회였다. Recovery
full-generation은 241/241 exact ACK, superseded/retry/abandoned 0이고 최대
ACK 지연은 0.101465초였다. 따라서 0.75초 recovery retry branch도 최종 gate에서
실행되지 않았다. Corridor failure epoch-reset은 map7 Adaptive에서 1회 실제
실행됐고 0.64초 뒤 새 trajectory가 commit됐다. Start-adjacent가 아니어서 새
네 방향 local-escape branch는 실행되지 않았다.

Raw 결과는 다음 파일에 있다.

- `results/velocity_guard_3mode_seed6_10_n1_raw_20260826.csv`
- `results/velocity_guard_3mode_seed6_10_n2_raw_20260826.csv`
- `results/corridor_escape_seed10_full_n5_raw_20260826.csv`
- `results/recovery_ack_retry_seed8_adaptive_n5_raw_20260826.csv`
- `results/multiexit_seed8_adaptive_n5_raw_20260826.csv`
- `results/final_multiexit_3mode_seed1_10_n1_raw_20260826.csv`

## 해석 범위

이 수정은 관측된 10 m/s 반례의 원인을 제거하고 guarded publish 경계에 방어층을
추가한다. 그래도 다음을 주장하지 않는다.

- 유한한 seed6-10 x n=3 결과만으로 모든 맵·초기상태·스케줄링에 대한 population
  100%를 증명하지 않는다.
- 실제 비행의 hard real-time 또는 flight-ready certification이 아니다.
- Sector와 Adaptive의 차이에 McNemar 검정을 수행하지 않았다.
- Raw-cloud CIRI는 default false/non-authoritative이고 이번 속도 수정의 근거가
  아니다.
- Recovery ACK retry와 네 방향 local-escape는 최종 gate에서 trigger되지 않아
  build/regression evidence는 있지만 직접적인 branch 실행 증명은 아니다.
