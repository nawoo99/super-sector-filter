# Base-NO_PATH 후속 집중 검증과 최종 3-mode n=3 gate (2026-08-27)

## 결론

Base-NO_PATH 복구 수정 뒤 map9 Adaptive를 20회 추가 실행하고, 같은 최종
바이너리로 map1~10의 Full/fixed-Sector/Adaptive를 각 3회씩 총 90회
실행했다.

- 집중 map9 Adaptive: 20/20 first-attempt 완주, contact/static collision 0,
  speed-valid 20/20
- 최종 Full: 30/30 완주, safety-qualified 30/30
- 최종 fixed-Sector: 30/30 완주, safety-qualified 26/30
- 최종 Adaptive: 30/30 완주, safety-qualified 30/30
- Sector의 비안전 4회는 map7 1회, map9 2회, map10 1회였고 Adaptive의 같은
  map/run block은 모두 안전했다.
- Adaptive는 Full 대비 processed application payload를 map별 동일가중 기준
  54.24% 줄였다. 전체 mode 평균의 비율로는 payload 53.61%, points/update
  15.68%, map total/update 21.80%, occupancy update 15.09%, FSM CPU 14.62%,
  planner+filter core-seconds 8.65% 감소했고 mission time은 4.14% 늘었다.
- Adaptive effective full-view open은 372회, 12.4회/run이었다.

이 결과는 현재 10개 map의 이번 3회 표본에서 목표한 관측 패턴을 충족한다.
다만 Full/Adaptive 30/30의 Wilson 95% lower bound는 88.65%이므로 population
100%, 형식적 collision freedom 또는 hardware-flight readiness를 뜻하지 않는다.

## 1~3단계: map9 Adaptive 집중 검증

첫 10회에서 base-NO_PATH local-escape 분기가 자연 발생하지 않아 계획대로
10회를 추가했다. 두 batch의 합계는 다음과 같다.

| 항목 | 결과 |
|---|---:|
| 실행 / first-attempt 완주 | 20 / 20 |
| Safety-qualified / speed-valid | 20 / 20 |
| Contact / static collision | 0 / 0 |
| 평균 / 범위 시간 | 90.07 / 76.71~122.25 s |
| 최저 static clearance | +0.190 m |
| 평균 processed payload | 3.280 MiB/s |
| Effective full-view opens | 165 |
| Certified brakes | 691 |
| Natural base-NO_PATH local-escape arms | 0 |
| Local-escape commits | 0 |
| Retry / OOM | 0 / 0 |

따라서 수정 뒤 map9 회귀 안전성과 liveness는 20회 모두 통과했지만, 새 분기의
자연 직접 증거는 아니다. 직접 branch proof는 앞 단계의 default-off
`SUPER_TEST_FORCE_BASE_NO_PATH_ESCAPE_ONCE=1` 두 번에서 이미 확보했다. 두
실행은 각각 base `NO_PATH` 3회, base local-escape arm 1회, 202-sample hard
guard를 통과한 0.6 m commit 1회를 기록하고 안전 완주했다. 자연 발생 빈도가
낮다는 이유로 fault hook을 실사용 profile에 켜지는 않았다.

Raw:

- `results/final_base_no_path_seed9_adaptive_n10a_raw_20260827.csv`
- `results/final_base_no_path_seed9_adaptive_n10b_raw_20260827.csv`
- 직접 분기 증거: `results/base_no_path_fault_seed1_adaptive_v2_raw_20260827.csv`

## 4단계: 최종 map1~10 세 모드 n=3

최종 캠페인은 v=7, static-PCD contact 판정, strict-burst native C++ filter,
reliable filtered map link, 180 s timeout으로 실행했다. 각 map/run에서 실행
순서는 항상 Full→Sector→Adaptive였으므로 아래 matched-block 통계에는 고정
순서 효과가 남는다.

Safety-qualified는 완주, speed-valid, live contact 0, static-PCD collision 0을
모두 만족한 경우다.

| Mode | Complete | Safety-qualified | Contact runs / events | Static collision runs / events | Mean / median / max time (s) | Worst clearance (m) | Mean payload (MiB/s) | Effective opens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 30/30 | 30/30 | 0 / 0 | 0 / 0 | 71.43 / 70.10 / 91.65 | +0.193 | 5.069 | 0 |
| Sector | 30/30 | 26/30 | 4 / 9 | 4 / 4 | 71.53 / 70.84 / 96.19 | -0.181 | 1.569 | 0 |
| Adaptive | 30/30 | 30/30 | 0 / 0 | 0 / 0 | 74.39 / 73.06 / 102.19 | +0.210 | 2.351 | 372 |

완주율은 세 모드가 모두 100%여서 이번 cohort에서는 Sector 완주율 저하가
관측되지 않았다. 차이는 안전성에서 나타났다. Sector는 전체 실행의 13.33%인
4/30에서 접촉했고, Adaptive는 그 4개 matched map/run block을 모두 contact 0으로
완주했다.

### 맵별 안전·시간·Adaptive 활성화

`F/S/A`는 Full/Sector/Adaptive 순서다. 시간은 3회 평균, clearance는 3회 중
최솟값, opens는 Adaptive 3회의 effective full-view open 합계다.

| Map | Complete F/S/A | Safe F/S/A | Contact events F/S/A | Mean time F/S/A (s) | Min clearance F/S/A (m) | A opens |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 59.00 / 60.59 / 59.57 | +0.263 / +0.275 / +0.249 | 62 |
| 2 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 56.10 / 57.81 / 58.00 | +0.233 / +0.263 / +0.281 | 64 |
| 3 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 63.42 / 64.40 / 65.73 | +0.267 / +0.267 / +0.242 | 38 |
| 4 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 71.14 / 72.47 / 77.06 | +0.266 / +0.227 / +0.233 | 23 |
| 5 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 68.27 / 72.25 / 71.95 | +0.246 / +0.145 / +0.239 | 37 |
| 6 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 75.27 / 69.74 / 80.10 | +0.273 / +0.249 / +0.228 | 36 |
| 7 | 3/3 / 3/3 / 3/3 | 3/3 / 2/3 / 3/3 | 0 / 3 / 0 | 75.73 / 77.50 / 77.56 | +0.234 / -0.181 / +0.210 | 38 |
| 8 | 3/3 / 3/3 / 3/3 | 3/3 / 3/3 / 3/3 | 0 / 0 / 0 | 77.08 / 71.00 / 78.49 | +0.216 / +0.196 / +0.248 | 27 |
| 9 | 3/3 / 3/3 / 3/3 | 3/3 / 1/3 / 3/3 | 0 / 4 / 0 | 83.39 / 85.46 / 88.77 | +0.213 / -0.165 / +0.210 | 24 |
| 10 | 3/3 / 3/3 / 3/3 | 3/3 / 2/3 / 3/3 | 0 / 2 / 0 | 84.93 / 84.11 / 86.69 | +0.193 / -0.112 / +0.225 | 23 |

## 5단계: 연산량과 processed payload

아래 payload는 ROG-Map이 실제 update에 선택한 `PointCloud2.data`의 mission
구간 처리율이다. DDS/RTPS header, metadata, retransmission, latest-only slot에서
map update 전에 overwrite된 frame은 포함하지 않는다. 같은 host에서 실행한
값이므로 NIC 또는 무선-link 대역폭이라고 부르면 안 된다.

| Map | Payload F/S/A (MiB/s) | Payload 감소 S/A vs F | Points/update F/S/A | Total/update F/S/A (ms) | FSM CPU F/S/A (%) |
|---:|---:|---:|---:|---:|---:|
| 1 | 3.636 / 0.989 / 1.352 | 72.8% / 62.8% | 15,445 / 7,011 / 12,124 | 31.37 / 11.68 / 21.10 | 114.6 / 93.0 / 99.5 |
| 2 | 3.763 / 0.968 / 1.360 | 74.3% / 63.9% | 15,766 / 6,626 / 12,224 | 32.37 / 11.89 / 22.57 | 118.0 / 96.9 / 101.7 |
| 3 | 4.106 / 1.204 / 1.902 | 70.7% / 53.7% | 22,702 / 10,567 / 19,235 | 38.11 / 14.08 / 30.21 | 103.5 / 86.9 / 87.2 |
| 4 | 4.388 / 1.285 / 2.035 | 70.7% / 53.6% | 24,556 / 12,163 / 21,668 | 36.19 / 13.80 / 29.02 | 98.9 / 83.0 / 80.6 |
| 5 | 4.967 / 1.550 / 2.189 | 68.8% / 55.9% | 26,890 / 13,642 / 22,953 | 41.23 / 14.73 / 32.24 | 102.3 / 83.4 / 85.1 |
| 6 | 4.744 / 1.610 / 2.450 | 66.1% / 48.4% | 29,556 / 15,770 / 25,230 | 37.89 / 14.65 / 29.77 | 92.0 / 83.7 / 81.6 |
| 7 | 6.007 / 1.965 / 2.857 | 67.3% / 52.4% | 36,443 / 19,424 / 30,616 | 39.17 / 14.84 / 31.18 | 96.4 / 76.1 / 80.7 |
| 8 | 5.009 / 1.618 / 2.600 | 67.7% / 48.1% | 33,391 / 17,137 / 28,454 | 41.80 / 15.75 / 33.18 | 89.7 / 79.3 / 79.6 |
| 9 | 6.709 / 2.189 / 3.370 | 67.4% / 49.8% | 43,223 / 23,266 / 36,475 | 36.48 / 14.42 / 30.60 | 84.7 / 74.2 / 74.7 |
| 10 | 7.356 / 2.306 / 3.398 | 68.7% / 53.8% | 42,631 / 23,612 / 36,050 | 37.75 / 14.56 / 31.29 | 95.5 / 76.7 / 79.5 |

전체 30회 mode 평균의 비율로 계산한 Full 대비 변화는 다음과 같다. 양수 시간은
느려졌다는 뜻이다. Core-seconds는 mission time과 `(FSM CPU + external filter
CPU)`를 적분한 값이다.

| Comparison | Payload | Points/update | Total/update | Raycast/update | Occupancy update | FSM CPU | Planner+filter core-seconds | Mission time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sector vs Full | -69.05% | -48.65% | -62.30% | -61.54% | -63.76% | -16.32% | -13.28% | +0.14% |
| Adaptive vs Full | -53.61% | -15.68% | -21.80% | -25.28% | -15.09% | -14.62% | -8.65% | +4.14% |

Payload는 map별 비율을 동일 가중하면 Sector 69.43%, Adaptive 54.24% 감소다.
Adaptive external filter CPU 평균은 3.02%였다. Filter input callback과 worker
processed frame은 26,430/26,430으로 같고 overwrite는 0이므로, 이번 감소를
“latest-only worker가 frame을 버려서 생겼다”고 해석할 수 없다.

## 전환·ACK·recovery 건전성

Adaptive 30회에서 effective full-view open 372회, certified brake 712회가
기록됐다. Trajectory-guard full-refresh ACK는 712/712, pre-stale ACK는
2,131/2,131이었고 timeout, retry, supersede, abandon, final pending은 모두 0이다.
Base-NO_PATH local-escape arm과 local-escape commit은 broad 90회에서도 0이었다.

Adaptive 시간이 Full보다 긴 경향은 안전 전환과 brake/replan 비용을 포함한다.
최대 102.19초였던 map10 Adaptive도 timeout이나 permanent hold가 아니라 5/5
waypoint를 완주했다. 이번 표본에서 180초 timeout은 한 번도 발생하지 않았다.

## 통계 해석

- Full/Adaptive safety-qualified 30/30의 Wilson 95% CI는 88.65~100.00%다.
- Sector 26/30의 Wilson 95% CI는 70.32~94.69%다.
- Matched map/run block의 안전 discordance는 Full 대 Sector 4:0,
  Sector 대 Adaptive 0:4이며 exact two-sided McNemar `p=0.125`다.
- Full 대 Adaptive는 discordance 0이라 exact `p=1.0`이고 두 모드의 차이를
  검정할 정보가 없다.

4개 Sector 실패 방향은 모두 Adaptive 개선 방향이지만 표본이 작아 0.05에서
유의하지 않다. 또한 mode 순서가 항상 Full→Sector→Adaptive였으므로 이 McNemar는
matched-block 기술 통계이며 무작위 interleaved 인과 실험으로 해석하지 않는다.

## 인프라와 검증

- 총 90회 attempt 90, retry 0, OOM delta 0
- 최대 FSM RSS/PSS 3,472/3,450 MiB, FSM swap 0
- 최소 system available memory 5,228 MiB
- host swap peak 2,043 MiB였지만 memory PSI some/full avg10 최대 0
- cgroup peak memory/swap 7,000/560 MiB
- 종료 후 ROS campaign 잔류 프로세스 없음, available memory 8.9 GiB
- campaign Python tests 20/20, `compileall` 통과
- runtime source와 mirror의 관련 C++ 6개 파일 byte-identical

앞서 한 map8 process가 약 9.1 GiB RSS로 증가해 OOM-kill된 rare infrastructure
사건의 allocation 원인은 여전히 미확정이다. 그러나 이번 90회에서는 retry,
OOM, accepted-run FSM swap 또는 memory pressure가 재현되지 않았으므로 최종
결과를 retry로 보정하지 않았다.

## Raw와 claim boundary

최종 raw:
`results/final_payload_base_no_path_3mode_seed1_10_n3_raw_20260827.csv`

이번 결과는 현재 map1~10, v=7, simulation/static-PCD 계측에서 Full과 Adaptive가
각 30/30 안전했다는 관측 증거다. 새 map 일반화, formal proof, 실제 LiDAR/network
wire bandwidth 또는 hardware flight 검증이 아니다. Raw-cloud CIRI는 계속
default false/non-authoritative다. `obs_skip_num` no-op, NaN 버그,
clearance-penalty 설계 결함, BackupTrajOpt 미커버와 `DRONE_R=robot_r` 접촉지표
한계도 해결됐다고 주장하지 않는다.
