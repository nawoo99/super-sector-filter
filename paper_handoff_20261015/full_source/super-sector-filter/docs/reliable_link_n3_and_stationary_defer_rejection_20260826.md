# Reliable filtered-link n=3 gate and stationary-defer rejection (2026-08-26)

## 결론

Reliable depth-1 filtered link를 켠 동일 코드로 seed6-10의
Full/Sector/Adaptive를 맵·모드당 3회, 총 45회 반복했다. 45행 모두 current
runner 기준 valid, first-attempt였고 retry/OOM/FSM swap/memory PSI는 0이었다.
Full과 Adaptive는 각각 15/15 완주·live contact 0·static-PCD collision 0이었다.
Fixed Sector는 13/15 완주, contact run 3/15, contact event 5회였다. 따라서 이
late-map 표본에서는 Adaptive가 Sector의 안전·완주 손실을 회복하면서 Full보다
mapping point work와 mapping wall work를 각각 35.97%, 36.20% 줄였다.

다만 Full seed7 run3의 `max_speed_mps`가 10.027이었다. PerfectDrone은
`PositionCommand.velocity`를 그대로 odometry에 복사하고 monitor는 그 odometry의
수평 속도를 읽으므로 단순 monitor 노이즈로 볼 수 없다. 현재 `run_valid`는
static-PCD 활성 여부만 검사하고 v=7 command bound를 검사하지 않는다. 그러므로
이 결과의 15/15는 완주/contact 기준이며 **v=7 제약까지 포함한 100% 유효성
보장으로 해석하면 안 된다.**

## 반복 게이트

실행 조건은 v=7, `loop24.txt`, static PCD, timeout 240초, strict-burst C++
filter, reliable filtered-link, raw-cloud CIRI default false/non-authoritative다.

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed6 seed7 seed8 seed9 seed10 \
  --modes full sector adaptive --runs 3 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config \
    static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-static-pcd --loop-timeout 240 \
  --filter-profile strict-burst --filter-backend cpp \
  --adaptive-pre-stale-ack-retry-age-s 0 \
  --filtered-reliable-map-link \
  --artifacts-dir /tmp/reliable_link_repeated_3mode_seed6_10_n3_artifacts \
  --out results/reliable_link_repeated_3mode_seed6_10_n3_raw_20260826.csv
```

| mode | completion | contact runs/events | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | map update (ms) | observed map Hz | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 15/15 | 0/0 | 84.85 | +0.151 | 37,114 | 36.127 | 12.186 | 4.71 | 80.50 |
| fixed Sector | 13/15 | 3/5 | 101.57 | -0.188 | 32,689 | 12.055 | 3.610 | 4.85 | 58.98 |
| Adaptive | 15/15 | 0/0 | 82.31 | +0.160 | 31,610 | 30.655 | 11.280 | 3.65 | 73.75 |

Sector 평균 시간은 두 seed10 timeout을 포함하므로 성공 run만의 성능값으로
해석하지 않는다. Adaptive의 Full 대비 변화는 mission time -3.00%,
points/update -14.83%, map total/update -15.15%, map-update compute -7.44%,
observed map rate -22.49%, time-weighted FSM CPU -8.38%다. 동일 15회 전체의
mapping point work -35.97%, mapping wall work -36.20%, FSM+filter core-seconds
-7.46%였다.

## 맵별 결과

셀은 `완주 / contact run(event) / 평균 시간 / worst clearance` 순서다.

| map | Full | fixed Sector | Adaptive |
|---|---|---|---|
| 6 | 3/3 / 0(0) / 83.58 s / +0.257 m | 3/3 / 0(0) / 74.23 s / +0.163 m | 3/3 / 0(0) / 80.60 s / +0.170 m |
| 7 | 3/3 / 0(0) / 81.53 s / +0.166 m | 3/3 / 1(2) / 76.89 s / -0.057 m | 3/3 / 0(0) / 80.89 s / +0.172 m |
| 8 | 3/3 / 0(0) / 78.95 s / +0.151 m | 3/3 / 0(0) / 75.86 s / +0.126 m | 3/3 / 0(0) / 76.30 s / +0.223 m |
| 9 | 3/3 / 0(0) / 88.74 s / +0.239 m | 3/3 / 0(0) / 96.28 s / +0.042 m | 3/3 / 0(0) / 85.64 s / +0.177 m |
| 10 | 3/3 / 0(0) / 91.44 s / +0.258 m | 1/3 / 2(3) / 184.61 s / -0.188 m | 3/3 / 0(0) / 88.11 s / +0.160 m |

Paired evidence도 방향이 일치한다. seed7 run3에서 Sector만 contact 2회였고,
seed10 run1/run2에서 Sector만 contact와 timeout이 있었다. seed9 run2 Sector는
clearance +0.042 m였지만 paired Adaptive는 +0.208 m이고 29.32초 빨랐다.

## Exact ACK와 guard 비용

Adaptive 15회의 effective full-open은 118회, direct trajectory-guard open은
78회였다. Pre-stale full 1,274개 중 1,273개가 exact ACK됐고 supersede와 SLA
timeout은 0이었다. 남은 pending 1개는 seed6 종료 시점의 final pending이며,
loss/timeout으로 관측되지 않았다. Exact ACK latency는 count-weighted 평균
0.0475초, 최대 0.1424초였다. Recovery gate 502/502가 exact ACK를 받았고 brake
success도 502회였다. 반면 brake rejection marker 906회,
`main_pre MAP_STALE` 406회, recovery-active 합 514.205초가 남았다.

906개 rejection marker의 원인을 stack log에서 분해했다.

| trigger | count |
|---|---:|
| `emergency_stop_retry` | 683 |
| `main_pre` | 168 |
| `candidate_without_safe_follow` | 44 |
| `main_post` | 8 |
| `replan_post` | 3 |

속도 0.05 m/s 이하를 정지 proxy로 쓰면 707/906(78.0%)이 정지 상태였고 199개가
이동 상태였다. 이는 rejection marker 대부분이 0.25초 passive-stop stability를
기다리는 동일 후보 재평가임을 보여주지만, 해당 대기를 생략해도 된다는 안전
증명은 아니다.

## Stationary fast-defer 후보와 기각

정지·zero-displacement 후보가 아직 passive-stop stable이 아닐 때 map/grid
certificate를 반복 계산하지 않고 같은 0.1초 fail-closed retry로 넘기는
`TRAJ_GUARD_STATIONARY_DEFER` 후보를 구현했다. 안전 조건과 resume 조건은
완화하지 않았다. Parser에는 이 marker의 계측 필드를 추가했다.

Seed9 Adaptive 세 번의 후보 실행은 모두 contact 0이었지만 mission time이
135.20/153.04/168.45초였고, 평균 152.23초였다. Baseline seed9 n=3 평균
85.64초보다 길었으며 긍정적인 효율 효과를 입증하지 못했다. 후보를 완전히
원복하고 재빌드한 isolated smoke도 213.05초로 길었기 때문에 이 증가를 후보의
인과 효과라고 단정할 수 없다. Post-build isolated execution regime 자체가
guard 반복 long-tail에 들어간 교란이 있다. 결론은 다음과 같다.

- 후보가 느리게 만들었다는 인과 주장은 하지 않는다.
- 그러나 세 표본에서 개선 증거가 없고 timing-sensitive ordering을 건드리므로
  채택하지 않는다.
- planner source는 tracked baseline과 byte-identical하게 원복했고 설치 binary도
  재빌드했다.
- parser의 `guard_brake_stationary_defers` 필드만 기각 실험의 재현성을 위해
  남긴다. Baseline에서는 0이다.

후보 세 run은 평균 guard gate 68.67회, 기존 rejection 132.33회,
stationary defer 71회, recovery-active 103.03초였다. 원복 smoke는 guard gate
99회, rejection 333회, recovery-active 171.456초였다. 반면 같은 날 baseline
seed9 n=3은 run당 guard gate 34.33회, rejection 57.67회, active 36.12초였다.
Long tail은 per-update map compute 증가보다 반복 guard episode 증가와 함께
나타났다.

## 다음 세 단계

1. `run_valid`에 velocity-bound telemetry를 추가하고 모든 exceedance의 최초
   timestamp, trajectory id, planner state, position/velocity/acceleration을
   저장한다. Post-hoc scalar만으로 원인을 추정하지 않는다.
2. v=7 limit이 optimizer constraint인지 publication/execution invariant인지
   확인하고, trajectory sampling 전체에서 tolerance를 포함한 hard validation을
   추가한다. 위반 trajectory는 정상 publish하지 않고 certified stop-and-reroute로
   보낸다.
3. 같은 map-labelled Full/Sector/Adaptive gate를 다시 실행해 completion,
   contact뿐 아니라 speed-qualified validity를 함께 보고한다. 그 뒤에만 guard
   episode 비용 최적화를 재개한다.

이 n=3 late-map gate는 population 100%, flight-ready, hard real-time 증명이
아니며 McNemar 검정을 수행하지 않았다. Overspeed threshold도 사전 등록하지
않았으므로 이번 문서에서는 Full을 임의로 14/15로 재분류하지 않는다. Raw 입력은
`results/reliable_link_repeated_3mode_seed6_10_n3_raw_20260826.csv`, 후보와 원복
smoke는 `results/stationary_defer_seed9_adaptive_smoke_raw_20260826.csv`,
`results/stationary_defer_seed9_adaptive_n2_raw_20260826.csv`,
`results/stationary_defer_reverted_seed9_adaptive_smoke_raw_20260826.csv`다.
