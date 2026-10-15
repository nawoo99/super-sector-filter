# SUPER 맵별 모드별 최종 실험 결과

기존 본실험 수치는 2026년 10월 12일 정리본과 같고, 2026년 10월 14일에 원래 함수별 CPU 로그의 사후 집계를 추가했다. 본실험은 V6의 7개 정적 맵에서 Full, Active-Yaw Sector, Adaptive를 맵·모드당 10회씩 실행한 210회다. 별도 숲 사전시험 30회와 이전 구현의 600회는 본실험 수치에 합산하지 않는다.

Full과 Adaptive는 각각 70회 모두 무접촉 완주했다. Active-Yaw Sector는 목표 도달 68회, 접촉 주행 2회, 무접촉 완주 67회, 미션 실패 3회다. 접촉과 미완주가 중첩되는 주행은 실패에 한 번만 포함한다.

## 모드별 전체 판정

| Mode | N | Goal complete | Contact runs | Contact-free complete | Mission failure |
| --- | --- | --- | --- | --- | --- |
| Full | 70 | 70 | 0 | 70 | 0 |
| Active-Yaw Sector | 70 | 68 | 2 | 67 | 3 |
| Adaptive | 70 | 70 | 0 | 70 | 0 |

전체 판정 표는 주행 수 집계용이다. 주 처리 비용은 아래의 Normal1–5, Urban, Forest를 따로 비교한다.

## 맵별 목표 도달 접촉 미션 성공

| Map | Mode | N | Goal complete | Contact runs | Contact episodes | Contact-free complete | Mission failure | Success (%) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Map1 | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map1 | Active-Yaw Sector | 10 | 10 | 1 | 1 | 9 | 1 | 90.0 |
| Map1 | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map2 | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map2 | Active-Yaw Sector | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map2 | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map3 | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map3 | Active-Yaw Sector | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map3 | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map4 | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map4 | Active-Yaw Sector | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map4 | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map5-R2 | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map5-R2 | Active-Yaw Sector | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Map5-R2 | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Urban | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Urban | Active-Yaw Sector | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Urban | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Forest | Full | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |
| Forest | Active-Yaw Sector | 10 | 8 | 1 | 1 | 8 | 2 | 80.0 |
| Forest | Adaptive | 10 | 10 | 0 | 0 | 10 | 0 | 100.0 |

미션 성공은 무접촉 완주다. 맵 1 Sector의 접촉 후 목표 도달은 목표 도달에는 포함되지만 미션 성공에는 제외된다. 숲 Sector의 무접촉 미완주 1회는 미션 실패지만 접촉 주행은 아니다. 이 분류는 원본 판정을 변경하지 않은 파생 지표다.

## 맵별 주행시간

| Map | Mode | Observed mean (s) | Goal-complete N | Goal-complete mean (s) | Median (s) | SD (s) | Contact-free N | Contact-free mean (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Map1 | Full | 51.860 | 10 | 51.860 | 50.375 | 4.490 | 10 | 51.860 |
| Map1 | Active-Yaw Sector | 99.689 | 10 | 99.689 | 85.295 | 34.151 | 9 | 98.757 |
| Map1 | Adaptive | 54.692 | 10 | 54.692 | 54.730 | 2.735 | 10 | 54.692 |
| Map2 | Full | 48.939 | 10 | 48.939 | 48.255 | 5.006 | 10 | 48.939 |
| Map2 | Active-Yaw Sector | 69.665 | 10 | 69.665 | 65.750 | 9.528 | 10 | 69.665 |
| Map2 | Adaptive | 49.365 | 10 | 49.365 | 48.825 | 3.508 | 10 | 49.365 |
| Map3 | Full | 48.625 | 10 | 48.625 | 47.850 | 3.979 | 10 | 48.625 |
| Map3 | Active-Yaw Sector | 83.283 | 10 | 83.283 | 72.730 | 21.998 | 10 | 83.283 |
| Map3 | Adaptive | 55.026 | 10 | 55.026 | 56.680 | 5.228 | 10 | 55.026 |
| Map4 | Full | 51.977 | 10 | 51.977 | 50.475 | 4.049 | 10 | 51.977 |
| Map4 | Active-Yaw Sector | 67.964 | 10 | 67.964 | 68.770 | 5.004 | 10 | 67.964 |
| Map4 | Adaptive | 52.336 | 10 | 52.336 | 51.110 | 3.860 | 10 | 52.336 |
| Map5-R2 | Full | 46.535 | 10 | 46.535 | 45.545 | 4.031 | 10 | 46.535 |
| Map5-R2 | Active-Yaw Sector | 66.277 | 10 | 66.277 | 64.210 | 7.681 | 10 | 66.277 |
| Map5-R2 | Adaptive | 50.934 | 10 | 50.934 | 50.265 | 3.237 | 10 | 50.934 |
| Urban | Full | 47.150 | 10 | 47.150 | 46.635 | 1.314 | 10 | 47.150 |
| Urban | Active-Yaw Sector | 77.850 | 10 | 77.850 | 75.180 | 9.490 | 10 | 77.850 |
| Urban | Adaptive | 53.663 | 10 | 53.663 | 53.615 | 4.528 | 10 | 53.663 |
| Forest | Full | 60.099 | 10 | 60.099 | 58.870 | 9.267 | 10 | 60.099 |
| Forest | Active-Yaw Sector | 112.277 | 8 | 96.926 | 92.525 | 27.349 | 8 | 96.926 |
| Forest | Adaptive | 59.766 | 10 | 59.766 | 59.370 | 3.574 | 10 | 59.766 |

Observed mean은 미완주를 포함한 전체 관측시간이다. Goal-complete mean은 접촉 후 도달도 포함하며 숲 Sector의 분모는 8회다. Contact-free mean은 무접촉 완주만 포함하며 맵 1 Sector의 분모는 9회다. SD는 표본 표준편차다. 총 미션시간 상한은 없지만 동일 목표에서 기준 위치 반경 2 cm 안에 60초 정체하면 관측을 종료한 조건은 유지했다.

## 맵별 처리 비용

| Map | Mode | CPU (cores) | CPU time (core-s/run) | Bandwidth (MiB/s) | Payload (MiB/run) | Mapping (ms/frame) | Accumulated mapping (s/run) | Map frames/run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Map1 | Full | 0.698 | 37.433 | 10.701 | 556.342 | 25.574 | 13.655 | 534.0 |
| Map1 | Active-Yaw Sector | 0.442 | 44.467 | 2.908 | 298.218 | 8.380 | 8.250 | 1013.9 |
| Map1 | Adaptive | 0.519 | 29.346 | 3.850 | 211.381 | 11.930 | 6.703 | 562.0 |
| Map2 | Full | 0.708 | 36.012 | 10.561 | 515.701 | 27.538 | 13.897 | 505.9 |
| Map2 | Active-Yaw Sector | 0.454 | 32.328 | 2.547 | 177.760 | 9.515 | 6.761 | 712.4 |
| Map2 | Adaptive | 0.525 | 26.916 | 3.437 | 170.252 | 11.782 | 6.001 | 508.6 |
| Map3 | Full | 0.700 | 35.501 | 10.869 | 528.613 | 26.510 | 13.354 | 504.7 |
| Map3 | Active-Yaw Sector | 0.450 | 38.061 | 2.875 | 241.902 | 8.689 | 7.265 | 849.5 |
| Map3 | Adaptive | 0.533 | 30.349 | 4.135 | 229.140 | 11.875 | 6.711 | 565.7 |
| Map4 | Full | 0.698 | 37.772 | 10.842 | 565.439 | 25.676 | 13.791 | 539.0 |
| Map4 | Active-Yaw Sector | 0.452 | 31.552 | 2.760 | 187.616 | 9.082 | 6.307 | 696.2 |
| Map4 | Adaptive | 0.511 | 27.784 | 3.678 | 193.331 | 11.622 | 6.281 | 539.4 |
| Map5-R2 | Full | 0.685 | 33.010 | 10.875 | 504.813 | 25.398 | 12.155 | 479.9 |
| Map5-R2 | Active-Yaw Sector | 0.450 | 30.553 | 2.844 | 188.575 | 8.959 | 6.063 | 678.1 |
| Map5-R2 | Adaptive | 0.515 | 27.213 | 3.811 | 194.824 | 11.407 | 5.989 | 524.5 |
| Urban | Full | 0.693 | 34.197 | 11.376 | 536.402 | 28.102 | 13.678 | 486.8 |
| Urban | Active-Yaw Sector | 0.440 | 35.047 | 2.642 | 205.346 | 9.725 | 7.318 | 753.0 |
| Urban | Adaptive | 0.537 | 29.788 | 3.373 | 181.265 | 12.693 | 6.787 | 534.1 |
| Forest | Full | 0.719 | 44.646 | 10.876 | 665.091 | 28.245 | 17.268 | 617.1 |
| Forest | Active-Yaw Sector | 0.423 | 47.806 | 2.957 | 358.552 | 8.476 | 9.029 | 1136.8 |
| Forest | Adaptive | 0.514 | 31.798 | 3.582 | 214.718 | 12.541 | 7.675 | 611.9 |

비용 평균은 접촉·미완주를 포함한 각 맵·모드의 전체 10회다. Accumulated mapping은 각 주행의 유효 측정 구간에 기록된 ROG-Map Total 경과시간을 합산한 뒤 주행별 산술평균을 구한 값이다. CPU 시간 또는 전체 지도 서브시스템의 경과시간이 아니다. Raycast, Update_cache, Inflation은 중첩될 수 있으므로 서로 더해 Total을 대체하지 않는다.

## 환경별 처리 비용

| Environment | Mode | N | CPU (cores) | CPU time (core-s/run) | Bandwidth (MiB/s) | Payload (MiB/run) | Mapping (ms/frame) | Accumulated mapping (s/run) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Normal1-5 | Full | 50 | 0.698 | 35.946 | 10.770 | 534.181 | 26.139 | 13.371 |
| Normal1-5 | Active-Yaw Sector | 50 | 0.449 | 35.392 | 2.787 | 218.814 | 8.925 | 6.929 |
| Normal1-5 | Adaptive | 50 | 0.521 | 28.322 | 3.782 | 199.786 | 11.723 | 6.337 |
| Urban | Full | 10 | 0.693 | 34.197 | 11.376 | 536.402 | 28.102 | 13.678 |
| Urban | Active-Yaw Sector | 10 | 0.440 | 35.047 | 2.642 | 205.346 | 9.725 | 7.318 |
| Urban | Adaptive | 10 | 0.537 | 29.788 | 3.373 | 181.265 | 12.693 | 6.787 |
| Forest | Full | 10 | 0.719 | 44.646 | 10.876 | 665.091 | 28.245 | 17.268 |
| Forest | Active-Yaw Sector | 10 | 0.423 | 47.806 | 2.957 | 358.552 | 8.476 | 9.029 |
| Forest | Adaptive | 10 | 0.514 | 31.798 | 3.582 | 214.718 | 12.541 | 7.675 |

Normal1–5는 50회/모드의 평균이며 Urban과 Forest는 각각 10회/모드의 평균이다. 그룹 평균의 프레임당 시간과 평균 프레임 수를 곱한 값은 주행별 누적값의 평균과 같지 않을 수 있다.

## Full 대비 처리 비용 감소율

| Environment | Mode | Mean CPU (%) | CPU time (%) | Bandwidth (%) | Payload (%) | Mapping/frame (%) | Accumulated mapping (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal1-5 | Active-Yaw Sector | 35.58 | 1.54 | 74.12 | 59.04 | 65.86 | 48.18 |
| Normal1-5 | Adaptive | 25.36 | 21.21 | 64.88 | 62.60 | 55.15 | 52.60 |
| Urban | Active-Yaw Sector | 36.55 | -2.49 | 76.78 | 61.72 | 65.39 | 46.50 |
| Urban | Adaptive | 22.58 | 12.89 | 70.35 | 66.21 | 54.83 | 50.38 |
| Forest | Active-Yaw Sector | 41.16 | -7.08 | 72.81 | 46.09 | 69.99 | 47.71 |
| Forest | Adaptive | 28.62 | 28.78 | 67.06 | 67.72 | 55.60 | 55.55 |

감소율은 100 × (1 − 해당 모드의 주행별 평균 / Full의 주행별 평균)이다. 양수는 감소, 음수는 증가다. 실패 비행도 비용 평균에 포함하므로 저비용 자체를 동일한 미션 수행 성능으로 해석하지 않는다.

## CPU 메모리 처리 주파수

| Environment | Mode | Host CPU (%) | Experiment capacity (%) | Peak sampled RSS (MiB) | Peak sampled PSS (MiB) | Map frames/s | Trajectory commits/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal1-5 | Full | 6.183 | 3.488 | 3547.017 | 3479.214 | 10.342 | 4.785 |
| Normal1-5 | Active-Yaw Sector | 5.267 | 2.247 | 3525.905 | 3458.112 | 10.220 | 3.250 |
| Normal1-5 | Adaptive | 5.536 | 2.603 | 3528.664 | 3460.838 | 10.294 | 4.482 |
| Urban | Full | 6.323 | 3.466 | 3491.130 | 3423.190 | 10.326 | 4.915 |
| Urban | Active-Yaw Sector | 5.262 | 2.199 | 3476.600 | 3408.676 | 9.689 | 3.107 |
| Urban | Adaptive | 5.677 | 2.683 | 3479.587 | 3411.753 | 9.959 | 4.197 |
| Forest | Full | 6.376 | 3.597 | 3540.776 | 3472.855 | 10.273 | 4.281 |
| Forest | Active-Yaw Sector | 5.210 | 2.117 | 3520.889 | 3453.056 | 10.145 | 2.534 |
| Forest | Adaptive | 5.822 | 2.568 | 3510.649 | 3442.784 | 10.239 | 4.171 |

Host CPU는 배경 부하를 포함한다. Experiment capacity는 실험 cgroup의 CPU cores를 20개 논리 프로세서 용량으로 나눈 비율이며 배경을 차감한 호스트 CPU가 아니다. 메모리는 샘플링으로 얻은 프로세스 합계의 주행별 peak 평균이므로 실제 순간 최대값을 보장하지 않는다. Trajectory commits/s는 고유 커밋 세대의 첫 시각과 마지막 시각 사이에서 계산한 빈도이며 플래너 루프 주파수가 아니다.

## Adaptive Full 전환

| Map | Runs | Full transitions | Mean/run | Median/run |
| --- | --- | --- | --- | --- |
| Map1 | 10 | 85 | 8.5 | 8.5 |
| Map2 | 10 | 54 | 5.4 | 5.0 |
| Map3 | 10 | 80 | 8.0 | 8.5 |
| Map4 | 10 | 69 | 6.9 | 6.5 |
| Map5-R2 | 10 | 72 | 7.2 | 7.0 |
| Urban | 10 | 61 | 6.1 | 6.5 |
| Forest | 10 | 88 | 8.8 | 8.5 |

본실험 전환 합계는 509회다. 별도 숲 사전시험의 109회는 합산하지 않는다. 전환 주기별 프레임·맵 ACK·경로 준비·Sector 복귀는 14_adaptive_cycles_509.csv와 원본 독립 감사에 기록돼 있다. 전환을 확인한 것은 위험 탐지율이나 미탐률을 측정한 것과 다르다.

## 접촉과 미완주 사례

| Map | Mode | Repeat | Goal complete | Contact | Observed time (s) | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| Map1 | Active-Yaw Sector | 6 | Yes | Yes | 108.080 | Contact then goal completion |
| Forest | Active-Yaw Sector | 4 | No | Yes | 193.310 | Contact then 60 s stall |
| Forest | Active-Yaw Sector | 5 | No | No | 154.050 | Departure rejected then 60 s stall |

숲 5회차는 새 맵에서의 출발 인증과 공통 복구 예산의 진행성 민감도가 함께 관여했다. 시야 제한만을 배타적인 원인으로 확정하지 않는다. 자세한 원본 분석과 사례 그림은 source_frozen/failure_analysis.md 및 source_frozen/case_*.png에 있다.

## 환경 지도

맵 1~5는 동일 조건의 비중첩 무작위 원기둥 배치이며 맵 5는 R2 수정본이다. 도심지는 4×4 건물 블록, 숲은 10개 군집의 270개 수목과 배경 140개 수목이다. 모든 맵은 64×64 m, 초기 위치와 목표 고도는 1.5 m다. 지도는 environment_maps/에 있으며 실제 정적 형상과 웨이포인트를 나타낸다. 점선은 목표 방문 순서이지 실제 비행 경로나 통과 가능성 증명이 아니다.

## 해석 범위

현재 PerfectDrone은 이상적 궤적 추종을 사용하며 충격·파손·추락 물리를 평가하지 않는다. 접촉 판정은 수신 위치 표본의 반경 0.2 m 구체와 정적 실체의 기하학적 교차다. 연속 swept-volume이나 실제 비행 안전 보장이 아니다. 반복 주행은 같은 환경에서의 반복이며 독립적인 새 환경 210개를 뜻하지 않는다. 현행 Urban·Forest는 통제된 blind-zone stress로 재분류하지 않는다. 현행 결과에 새로운 통계적 안전성 우위나 인과 검정을 추가하지 않았다.

## 시뮬레이터 콜백을 제외한 계측 함수 CPU

기존 실험 cgroup CPU 표와 별도로, 최종 210회의 원래 thread CPU 로그에서 map/frontend/FSM/guard/planner 범위의 exclusive CPU 소계를 구했다. 시뮬레이터 콜백과 계측·시각화 함수를 제외한 **계측 함수 소계**이며, 실행기·DDS 등 미계측 작업과 별도 미션 프로세스까지 포함한 완전한 자율주행 CPU 총량은 아니다.

| Environment | Runs/mode | Full subtotal (cores) | Active-Yaw Sector subtotal (cores) | Adaptive subtotal (cores) | Adaptive reduction vs Full (%) |
|---|---:|---:|---:|---:|---:|
| Normal1–5 | 50 | 0.495228 | 0.233385 | 0.317182 | 35.95 |
| Urban | 10 | 0.476129 | 0.217432 | 0.314620 | 33.92 |
| Forest | 10 | 0.516241 | 0.211110 | 0.310629 | 39.83 |

각 주행의 계측 구간 CPU core-s를 같은 구간 길이로 나눈 후 주행별 산술평균을 냈다. 계측 구간은 첫·마지막 프로파일 보고 사이이며 해당 주행의 관측 기간 안에 있다. 원자료에서 이 구간은 관측 기간의 79.15~96.74%였다. 모든 주행에서 계측·필수 단계·로그 해시를 확인했으며 CPU 시계 오류는 0건이다.

| Environment | Runs/mode | Full subtotal (core-s/profile window) | Active-Yaw Sector subtotal (core-s/profile window) | Adaptive subtotal (core-s/profile window) |
|---|---:|---:|---:|---:|
| Normal1–5 | 50 | 21.482805 | 16.194296 | 14.629291 |
| Urban | 10 | 19.304903 | 15.481996 | 15.135387 |
| Forest | 10 | 27.722656 | 21.195929 | 16.804767 |

위 누적값은 계측 구간의 함수 CPU이며 전체 주행 누적 CPU와 다르다. 앞의 전체 실험 CPU 시간 표를 대체하거나 평균 cores × 전체 주행시간으로 역산하지 않는다. 자세한 맵별 21행, 환경별 9행, 주행별 210행, 단계별 값과 감소율은 `cpu_analysis/`에 있고, 분류와 적용 범위는 `08_cpu_without_simulator.md`에 있다.
