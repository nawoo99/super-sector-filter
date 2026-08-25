# Reliable filtered link and guard-duty reduction — v7, seed6-10, three-mode n=1 (2026-08-26)

## 결론

Exact generation ACK gate에서 확인된 26회의 timeout은 ROG-Map 계산 지연이
아니라 native filter의 `/cloud_sector` 출력과 ROG-Map 입력 사이 best-effort
전달 손실이었다. 누락된 ACK마다 Full cloud를 추가 발행하는 후보는 map worker
부하와 guard 반복을 늘려 기각했다. 대신 이 한 내부 hop만 reliable depth-1로
맞췄다. cloud 수나 guard certificate는 늘리거나 약화하지 않았다.

최종 `seed6-10 x Full/Sector/Adaptive x n=1` 15회는 모두 valid,
first-attempt 완주였다. Full과 Adaptive는 각 5/5, live contact 0,
static-PCD collision 0이다. fixed Sector는 5/5 완주했지만 seed8에서 live
contact 1회와 static-PCD collision 1회가 함께 검출됐다. 해당 seed8의 paired
Full/Adaptive는 contact 0이었다. 이는 연구 목표와 맞는 관측 패턴이지만 n=1
표본이므로 모드별 population 확률이나 통계적 우월성을 뜻하지 않는다.

## 원인 분해와 기각한 후보

이전 best-effort exact-ACK 최종 실행의 Adaptive 로그에는 pre-stale full
582개 중 exact ACK 512개, superseded 70개, SLA timeout 26개가 있었다. 전달된
cloud의 ACK latency는 최대 0.1034초였지만 누락된 cloud는 다음 generation이
올 때까지 ACK되지 않았다. guard의 `MAP_STALE` 판정 184회는 모두 0.50초
threshold를 약 4--5ms 넘긴 구간에 몰렸고, 225개 guard/recovery episode가
247.457초 동안 활성화됐다. 즉 ACK 처리 속도보다 전달 손실과 반복 stop/replan이
병목이었다.

첫 후보는 ACK가 늦으면 동일 source map version에서 더 최신 Full generation을
한 번 발행하는 bounded retry였다. 옵션
`--map-commit-pre-stale-ack-retry-age-s=0.05`로 seed6-10 Adaptive n=1을
확인했을 때 5/5·contact 0이고 timeout은 26->5로 줄었다. 그러나 pre-stale
full은 582->657, guard gate는 225->258, stale 판정은 184->223, guard active
시간은 247.457->291.722초로 늘었다. 평균 mission time도 96.408->104.306초
(+8.19%)로 악화됐다. 따라서 이 옵션은 구현에 default 0/off로만 남기고 최종
프로파일에서는 사용하지 않는다.

## 채택 후보 구현

- ROG-Map 설정에 `rog_map/ros_callback/cloud_reliable`을 추가했다. 기본값은
  false이며 기존 프로파일의 QoS는 바뀌지 않는다.
- native C++ filter에 `--reliable-output`을 추가했다. 이 옵션에서만
  `/cloud_sector` publisher가 reliable depth-1을 사용한다.
- 새 연구 설정
  `static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml`만 ROG-Map의
  대응 subscription을 reliable depth-1로 맞춘다. simulator->filter 입력은
  기존 best-effort다.
- campaign runner의 `--filtered-reliable-map-link`는 native C++ backend에서만
  허용되며 기본값 false다. fixed Sector와 Adaptive 양쪽에 같은 내부 링크를
  적용해 sensor-link 조건을 맞춘다.
- 추가 Full retry age는 최종 gate에서 0이다. exact ACK, 0.75초 fail-closed SLA,
  certified stop/fresh-map replan/trajectory certificate는 그대로 유지한다.
- raw-cloud CIRI shadow는 계속 default false이고 brake 결정에 권한이 없다.

## 최종 map별 결과

시간은 초, clearance는 static-PCD body clearance다. `adaptive open`은
effective full-open 전환 횟수이고 `guard`는 direct trajectory-guard 전환
횟수다.

| map | mode | complete/contact | time | clearance | points/update | map ms/update | map Hz | adaptive open/guard |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| seed6 | Full | 1/1, 0 | 65.83 | +0.293 | 29,806 | 35.673 | 5.41 | - |
| seed6 | Sector | 1/1, 0 | 74.91 | +0.241 | 13,409 | 14.178 | 5.07 | 0/0 |
| seed6 | Adaptive | 1/1, 0 | 83.63 | +0.255 | 25,319 | 30.260 | 3.75 | 9/6 |
| seed7 | Full | 1/1, 0 | 71.87 | +0.263 | 37,160 | 38.373 | 4.93 | - |
| seed7 | Sector | 1/1, 0 | 91.35 | +0.286 | 18,822 | 14.368 | 3.81 | 0/0 |
| seed7 | Adaptive | 1/1, 0 | 80.04 | +0.286 | 31,929 | 31.386 | 3.17 | 5/3 |
| seed8 | Full | 1/1, 0 | 95.25 | +0.252 | 33,287 | 36.921 | 3.34 | - |
| seed8 | Sector | 1/1, **1** | 79.92 | **-0.079** | 17,600 | 14.871 | 4.54 | 0/0 |
| seed8 | Adaptive | 1/1, 0 | 80.36 | +0.278 | 28,675 | 33.404 | 3.43 | 3/2 |
| seed9 | Full | 1/1, 0 | 102.74 | +0.177 | 41,182 | 33.700 | 4.36 | - |
| seed9 | Sector | 1/1, 0 | 90.16 | +0.249 | 22,812 | 13.760 | 4.20 | 0/0 |
| seed9 | Adaptive | 1/1, 0 | 92.88 | +0.255 | 35,842 | 30.366 | 3.06 | 6/3 |
| seed10 | Full | 1/1, 0 | 85.09 | +0.228 | 43,329 | 37.013 | 5.41 | - |
| seed10 | Sector | 1/1, 0 | 83.38 | +0.220 | 24,069 | 14.478 | 5.19 | 0/0 |
| seed10 | Adaptive | 1/1, 0 | 93.17 | +0.193 | 33,645 | 29.858 | 3.54 | 9/7 |

## 모드 집계

points/update와 map ms/update는 update 수로 가중했고, FSM CPU는 mission
time으로 가중했다. point retention은 전체 filter input/kept point 합이다.

| mode | completion | contact | mean time | worst clearance | points/update | map ms/update | map Hz | FSM CPU | point retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 5/5 | 0 | 84.16 | +0.177 | 37,568 | 36.234 | 4.60 | 80.14% | 100% |
| fixed Sector | 5/5 | 1 | 83.94 | -0.079 | 19,497 | 14.330 | 4.53 | 71.33% | 52.97% |
| Adaptive | 5/5 | 0 | 86.02 | +0.193 | 31,040 | 30.981 | 3.39 | 67.90% | 64.24% |

Adaptive는 Full 대비 points/update 17.38%, map total/update 14.50%, map
update 계산 성분 6.93%, observed map rate 26.32%, time-weighted FSM CPU
15.28%를 줄였다. 다섯 맵 전체 mapping point work는 37.78%, mapping wall
work는 35.61%, FSM+filter core-seconds는 9.59% 감소했다. 평균 mission time은
Full보다 2.21% 길었다.

이전 best-effort exact-ACK n=1과의 비대응 기술 비교에서 Full 평균 시간은
84.00->84.16초(+0.18%)로 거의 같았고 Adaptive는 96.41->86.02초(-10.78%)였다.
Adaptive guard gate는 225->195, stale 판정은 184->164, recovery active 합은
247.457->205.638초(-16.90%)다. 별도로 Adaptive만 연속 실행한 seed6-10 n=1도
5/5·contact 0, 평균 87.16초, timeout 0을 보여 방향을 재확인했다. 두 비교 모두
반복 표본 추정이나 paired 통계 검정은 아니다.

## Adaptive ACK와 guard 계측

| map | pre-stale full/ACK | superseded/timeout | recovery gate ACK/arm | stale 판정 | guard active 합 (s) |
|---|---:|---:|---:|---:|---:|
| seed6 | 79/79 | 0/0 | 33/33 | 31 | 34.392 |
| seed7 | 66/66 | 0/0 | 41/41 | 38 | 38.488 |
| seed8 | 72/72 | 0/0 | 35/36 | 29 | 39.918 |
| seed9 | 83/83 | 0/0 | 46/46 | 33 | 48.981 |
| seed10 | 93/93 | 0/0 | 38/39 | 33 | 43.859 |
| total | **393/393** | **0/0** | **193/195** | **164** | **205.638** |

모든 pre-stale full generation이 자신의 exact ACK를 받았고 final pending도
0이다. ACK latency는 count-weighted 평균 0.0468초, 최대 0.1357초다. seed8과
seed10의 마지막 recovery gate는 각각 mission 종료 시점에 ACK 이후 재개까지
완료되지 않아 arm보다 recovery ACK가 하나씩 적다. 이를 timeout이나 정상
trajectory로의 무인증 재개로 세지 않았다. 성공 brake는 195회, brake reject는
310회, recovery 완료 marker는 192회였다.

## 검증과 한계

- `mission_planner`, `rog_map`, `super_planner`를 순차 빌드해 통과했다.
- 최종 15행은 모두 `run_valid=True`, `attempt_count=1`, retry 0, OOM delta 0,
  FSM swap 0, memory PSI 0이다. host swap은 기존 점유 상태였지만 campaign 중
  FSM swap은 발생하지 않았고 최소 available memory는 3,876 MiB였다.
- Full/Adaptive contact 0은 이번 seed6-10 n=1 local regression gate에서만
  관측된 결과다. population-level 100%, flight-ready, hard real-time 보장이
  아니며 n=1이라 McNemar 검정을 수행하지 않았다.
- fixed Sector의 seed8 contact는 목표한 대조군 열화를 한 번 재현했지만 Sector
  자체의 population contact rate 역시 이 표본으로 추정할 수 없다. 기존 §8.26
  n=3의 seed9/10 contact 증거를 함께 유지한다.
- reliable filtered link는 새 opt-in 연구 프로파일에만 적용했다. 기존 validated
  profile과 실행 파일 기본값은 변경하지 않았다.

Primary raw inputs:

- final three-mode gate:
  `results/reliable_link_final_3mode_seed6_10_n1_raw_20260826.csv`
- targeted Adaptive confirmation:
  `results/reliable_link_adaptive_seed6_10_n1_raw_20260826.csv`
- rejected retry candidate:
  `results/ack_retry_adaptive_seed6_10_n1_raw_20260825.csv`
