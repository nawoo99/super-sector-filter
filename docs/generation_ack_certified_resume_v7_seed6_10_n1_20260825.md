# Exact full-generation ACK + certified resume — v7, seed6-10, three-mode n=1 (2026-08-25)

## 결론

§8.26의 `commit_version > source_version` proxy를 content-specific cloud ACK로
교체했다. Adaptive가 full refresh를 보낼 때 request sequence와 원본
`PointCloud2` stamp를 reliable control topic으로 알리고, ROG-Map은 해당 stamp의
scan 처리 완료 뒤 exact ACK를 발행한다. guard recovery는 guard edge 이후에
요청된 full generation의 exact ACK, 그 ACK가 가리키는 map version, fresh map,
정지 odometry, 새 `PlanFromRest`, 새 trajectory certificate가 모두 준비될 때만
비행을 재개한다.

ACK가 0.75초 안에 오지 않으면 정상 trajectory publication을 계속하지 않고 기존
certified emergency brake 경계로 들어간다. 이후 exact ACK를 받은 최신 full
generation으로 다시 계획하며, 새 후보가 기하학적으로 거부되면 기존 topology
blocker가 거부 경로를 막아 다른 homotopy를 탐색한다. ACK 누락 자체만으로 근거
없는 blocker를 만들지는 않는다.

최종 `seed6-10 x Full/Sector/Adaptive x n=1` 15회는 모두 valid, first-attempt
완주였고 live contact와 static-PCD collision은 모두 0이었다. Full/Sector는
generation request stream을 광고하지 않아 새 recovery gate가 실행되지 않았다.
이는 늦고 밀집한 맵의 local regression gate이며 population 100%, flight-ready,
hard real-time 보장은 아니다. n=1이므로 McNemar 검정도 하지 않았다.

## 구현

- ROG-Map health에 마지막 processed/committed source stamp를 저장하고,
  `/rog_map/cloud_process_ack`에 `[scan_seq, stamp_ns, map_version,
  committed_flag]`를 reliable QoS로 발행한다. map delta가 없어 version이
  증가하지 않는 scan도 처리 완료 ACK를 낸다.
- Adaptive native filter의 새 C++ 옵션 `--full-refresh-generation-ack`은
  기본값 false다. strict campaign runner만 기본 활성화한다. 각 pre-stale
  full 및 guard-edge full에 request sequence/stamp/kind를 발행한다.
- pending pre-stale state는 latest-only 0/1개다. 이전 generation이 ACK 없이
  새 full로 교체되면 `superseded`로 계수하고 동일 frame을 flood하지 않는다.
- planner의 `full_refresh_ack_sla_s` 기본값은 0이다. filtered v7 연구 설정만
  0.75초를 사용하며 Adaptive의 startup marker가 있을 때만 runtime gate를
  활성화한다. 따라서 같은 YAML을 쓰는 fixed Sector에는 gate가 걸리지 않는다.
- campaign CSV가 exact request/ACK/supersede/pending, SLA timeout, recovery
  target/ACK, topology arm/search를 기록하도록 확장했다.
- raw-cloud CIRI shadow는 계속 default false이고 실제 brake 결정에 연결하지
  않았다.

## 최종 map별 결과

시간은 초, clearance는 static-PCD body clearance, `Hz`는 관측된 ROG-Map
performance row 수를 mission time으로 나눈 update rate다.

| map | mode | complete/contact | time | clearance | points/update | map ms/update | map Hz | FSM CPU |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| seed6 | Full | 1/1, 0 | 71.15 | +0.269 | 29,556 | 34.814 | 5.07 | 91.77% |
| seed6 | Sector | 1/1, 0 | 83.84 | +0.239 | 15,089 | 13.894 | 4.15 | 68.25% |
| seed6 | Adaptive | 1/1, 0 | 91.53 | +0.268 | 25,269 | 30.301 | 3.09 | 58.93% |
| seed7 | Full | 1/1, 0 | 79.16 | +0.214 | 37,599 | 37.153 | 5.02 | 93.24% |
| seed7 | Sector | 1/1, 0 | 98.40 | +0.284 | 18,317 | 14.079 | 3.90 | 60.54% |
| seed7 | Adaptive | 1/1, 0 | 99.75 | +0.291 | 29,305 | 30.079 | 3.16 | 62.11% |
| seed8 | Full | 1/1, 0 | 73.35 | +0.274 | 33,587 | 39.251 | 4.83 | 89.10% |
| seed8 | Sector | 1/1, 0 | 77.79 | +0.157 | 16,594 | 15.152 | 4.36 | 68.16% |
| seed8 | Adaptive | 1/1, 0 | 92.49 | +0.217 | 28,669 | 31.338 | 3.19 | 58.58% |
| seed9 | Full | 1/1, 0 | 110.01 | +0.234 | 40,037 | 31.892 | 4.35 | 64.71% |
| seed9 | Sector | 1/1, 0 | 85.27 | +0.296 | 21,910 | 14.436 | 4.19 | 69.15% |
| seed9 | Adaptive | 1/1, 0 | 110.15 | +0.247 | 35,715 | 28.163 | 3.25 | 57.68% |
| seed10 | Full | 1/1, 0 | 86.34 | +0.214 | 42,548 | 36.553 | 4.49 | 83.08% |
| seed10 | Sector | 1/1, 0 | 103.29 | +0.242 | 20,967 | 13.970 | 4.11 | 59.38% |
| seed10 | Adaptive | 1/1, 0 | 88.12 | +0.224 | 35,158 | 31.473 | 3.20 | 75.67% |

## 모드 집계

points/update와 map ms/update는 update 수로 가중했고, FSM CPU는 mission
time으로 가중했다. point retention은 전체 input/kept point 합으로 계산했다.

| mode | complete | contact | mean time | worst clearance | points/update | map ms/update | map Hz | FSM CPU | point retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 5/5 | 0 | 84.00 | +0.214 | 36,973 | 35.713 | 4.71 | 82.71% | 100% |
| Sector | 5/5 | 0 | 89.72 | +0.157 | 18,696 | 14.285 | 4.13 | 64.67% | 54.53% |
| Adaptive | 5/5 | 0 | 96.41 | +0.217 | 31,011 | 30.171 | 3.18 | 62.30% | 67.61% |

Adaptive는 Full 대비 points/update 16.12%, map total/update 15.52%, observed
update rate 32.47%, time-weighted FSM CPU 24.68%를 줄였다. 같은 5개 맵 전체의
mapping point work와 mapping wall work는 각각 34.99%, 34.52% 줄었다. mission
time은 14.77% 길었지만, §8.26의 같은 seed6-10 Adaptive n=3 기술 평균
128.09초보다 이번 unpaired n=1 평균은 96.41초로 낮다. 이는 방향성 비교일 뿐
반복 표본 추정치는 아니다.

## Adaptive 전환과 exact ACK

| map | effective full-open 전환 | guard 전환 | pre-stale full | exact ACK | superseded | SLA timeout | recovery gate ACK | topology arm/search |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed6 | 2 | 2 | 111 | 98 | 13 | 5 | 45/45 | 4/4 |
| seed7 | 8 | 5 | 116 | 101 | 15 | 5 | 48/48 | 9/13 |
| seed8 | 2 | 2 | 106 | 93 | 13 | 3 | 48/48 | 6/8 |
| seed9 | 4 | 4 | 133 | 110 | 23 | 10 | 55/55 | 11/16 |
| seed10 | 12 | 9 | 116 | 110 | 6 | 3 | 29/29 | 11/13 |
| total | 28 | 22 | 582 | 512 | 70 | 26 | 225/225 | 41/54 |

처리된 exact generation의 ACK latency는 count-weighted 평균 0.0436초, 전체
최대 0.1034초였다. exact ACK 비율은 512/582(87.97%)이고, 나머지 70개는 다음
full generation이 오기 전에 처리 ACK가 없어 모두 superseded로 닫혔다. 최종
pending은 0이다. 즉 §8.26의 version-advance proxy 최대 11.245초는 특정 full
cloud의 실제 처리 latency가 아니었고, unrelated/later map version 진행과 cloud
loss를 섞어 보던 계측이었다. 같은 실행에서 기존 version-advance count는
582/582였지만 exact generation ACK는 512/582였다는 차이가 이를 직접 증명한다.

SLA timeout marker는 26회 관측됐다. 이 수치는 delivered cloud의 느린 처리라기보다
대부분 요청 token은 도착했지만 best-effort cloud generation이 exact ACK 없이
사라진 경우를 드러낸다. 모든 run이 완주했고 모든 recovery gate 225개가 exact
ACK를 받은 뒤 재개됐다. topology arm/search는 ACK 전용 수치가 아니라 기존
trajectory rejection recovery 전체의 활동량이다.

## 검증 및 한계

- `rog_map`, `mission_planner`, `super_planner`를 순차 단일 병렬도로 빌드했다.
  마지막 header 정리 후 `super_planner` 재빌드도 통과했다.
- synthetic ROS smoke에서 잘못된 stamp ACK는 pending을 해제하지 않았고,
  정확한 stamp만 ACK count를 1 증가시키며 pending을 해제했다.
- 최종 15행은 `run_valid=True`, `first_attempt_success=True`, retry 0, OOM delta
  0, FSM swap 0, memory PSI 0이다. 최소 host available memory는 4,138 MiB였다.
- Full/Sector의 generation timeout/recovery-gate 지표는 모두 0이다.
- 이번 n=1 late-map gate는 branch 실행과 관측 안전성의 regression 증거다.
  population-level 100%, 통계적 superiority, 하드웨어 timing 보장은 아니다.
- guard duty는 Adaptive seed6-10에서 79.60-94.68%로 여전히 높다. exact ACK가
  semantic 오류와 무한 대기를 제거했지만 guard 자체의 반복 발생 비용까지
  해결한 것은 아니다.

Primary raw input:
`results/generation_ack_final_3mode_seed6_10_n1_raw_20260825.csv`.
