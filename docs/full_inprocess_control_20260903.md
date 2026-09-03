# Full 모드 입력 지연 제거 및 제어 검증 (2026-09-03)

## 결론

Full의 잔여 실패는 Full 시야 자체의 안전성보다, 약 10 Hz로 생성되는 대용량
`PointCloud2`가 DDS 경계를 통과한 뒤 ROG-Map에 평균 2.76 Hz만 도착하면서 생긴
stale-map 정지와 복구 지연이 지배했다. Full cloud의 점을 줄이지 않고 simulator와
SUPER를 같은 프로세스에 구성해 기존 ROG latest-only queue로 `SharedPtr`를 직접
전달하자 Map 9의 입력이 평균 10.11 Hz로 회복되고 stale 판정이 0회가 됐다.

이번 바이너리의 균형 잡힌 최종 관측 결과는 Map 1--10 각 10회, 총 100/100
완주, source static-PCD 충돌 0, 속도 제한 위반 0이다. 이는 현재 실험군에 대한
회귀 통과이지 population-level 100% 안전 보장은 아니다.

## 원인과 수정

1. 초기 footprint에서 밖으로 빠져나가는 후보는 본 trajectory 검사에서는
   허용됐지만, 그 후보에서 파생한 viability brake에는 같은 egress 문맥이
   전달되지 않았다. 따라서 실제 접촉이 아닌 시작점 자체의 점 때문에 안전한
   brake가 거짓 거부됐다. `used_initial_footprint_egress`와 시작 원점을 brake
   certificate까지 전달하도록 수정했다.
2. viability 재시도의 time scale을 이미 rescale된 trajectory에 누적 scale로
   다시 적용해 실제 배율과 로그 배율이 달라지는 결함을 고쳤다. 매 재시도에는
   `guard_viability_speed_scale_step`만 곱하고, 누적값은 판정과 로그에만 쓴다.
3. standalone Full publisher의 fallback QoS는 best-effort/keep-last-1로
   제한했다. 그러나 Map 9 A/B에서 이것만으로는 subscriber delivery가 평균
   2.76 Hz에 머물렀다.
4. opt-in `perfect_drone_full_node`를 추가했다. renderer가 만든 변경되지 않은
   Full `PointCloud2::SharedPtr`를 `FsmRos2::injectMapCloud()`와
   `ROGMapROS::injectCloud()`를 통해 기존 enqueue-only/latest-only map worker에
   직접 넣는다. PCL 변환, ray casting, inflation, map commit, planning 및
   trajectory guard는 그대로다. raw cloud DDS publish만 생략한다.
5. 캠페인 러너에 `--full-intra-process`를 추가하고 direct handoff와 DDS/logical
   payload를 구분했다. 결합 프로세스의 `fsm_cpu_pct`는 FSM 단독이 아니라
   simulator+planner 전체다.

표준 `static_seedmaps_guard_viability_tight_v7.yaml`은 변경하지 않았다. 새 경로는
launch의 `use_integrated_full`과 캠페인 러너의 `--full-intra-process`를 명시한
경우에만 활성화된다.

## Map 9 transport A/B

| 경로 | 유효 표본 | 완주 | 충돌 | 전체 유효행 시간 평균 | ROG 입력 | stale/run | recovery 평균 | map compute |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DDS best-effort depth 1 | 7 | 6/7 | 1 | 135.63 s | 2.76 Hz | 55.14 | 89.61 s | 27.22 ms |
| in-process Full | 10 | 10/10 | 0 | 76.16 s | 10.11 Hz | 0 | 19.85 s | 36.56 ms |

DDS 행은 예정된 10회 중 보존된 7개의 유효행이라 표본 수가 다르며, 통계적
효과크기 검정이 아니라 원인 분리용 A/B다. DDS 완주행만의 평균시간은 128.23초다.
In-process에서 map compute 시간이 더 길어진 것은 계산을 생략한 결과가 아니라
입력 cadence가 회복돼 실제 Full frame을 더 많이 처리한 결과와 일치한다.

## 맵별 최종 n=10 freeze gate

| Map | 완주 | 충돌 | 시간 평균±SD (범위), s | 최저 clearance | map Hz | stale | recovery 평균, s | map compute, ms | ingress, MiB/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/10 | 0 | 59.82±2.61 (56.61--63.24) | +0.244 m | 10.181 | 0 | 14.87 | 29.94 | 5.25 |
| 2 | 10/10 | 0 | 55.57±1.58 (53.58--58.32) | +0.217 m | 10.210 | 0 | 0.53 | 31.13 | 5.28 |
| 3 | 10/10 | 0 | 58.61±2.62 (54.42--62.77) | +0.218 m | 10.159 | 0 | 1.98 | 36.89 | 7.49 |
| 4 | 10/10 | 0 | 64.92±4.50 (57.72--71.94) | +0.222 m | 10.184 | 0 | 10.57 | 35.38 | 8.27 |
| 5 | 10/10 | 0 | 64.13±5.29 (58.86--77.54) | +0.225 m | 10.143 | 0 | 10.60 | 39.62 | 8.94 |
| 6 | 10/10 | 0 | 65.58±3.51 (58.63--71.80) | +0.175 m | 10.162 | 0 | 4.96 | 37.85 | 9.74 |
| 7 | 10/10 | 0 | 70.08±5.86 (62.87--83.90) | +0.247 m | 10.114 | 0 | 12.92 | 38.08 | 11.57 |
| 8 | 10/10 | 0 | 65.36±3.33 (60.25--70.55) | +0.184 m | 10.090 | 0 | 3.97 | 40.11 | 10.88 |
| 9 | 10/10 | 0 | 76.16±3.26 (71.89--81.68) | +0.232 m | 10.106 | 0 | 19.85 | 36.56 | 13.60 |
| 10 | 10/10 | 0 | 76.48±5.80 (68.79--86.64) | +0.185 m | 10.095 | 0 | 17.96 | 36.77 | 13.25 |

100행 전체 평균은 시간 65.67초, sensor 10.001 Hz, map 10.145 Hz,
map compute 36.23 ms, planner ingress 9.43 MiB/s다. direct handoff는 64,300회,
raw DDS cloud publish는 0회였고 stale/retry/OOM/PSI pressure는 없었다. 정확히
100/100 성공의 Wilson 95% 하한은 약 96.30%이므로, 관측 완주율 100%를
population guarantee로 표현하지 않는다.

전체 최저인 Map 6의 +0.175 m와 Map 8의 +0.184 m는 속도 0인 guard stop,
Map 10의 반복적인 약 +0.22 m 일부는 출발 직후 고정 초기 pose에서 측정됐다.
모두 접촉은 아니지만 최종 논문 표에서는 전체 경로 최솟값, 초기 pose 제외
최솟값 및 정지/이동 중 최솟값을 구분하는 것이 타당하다.

CPU 평균 약 1.48 cores는 결합 simulator+planner 프로세스 수치다. Linux의 100%
CPU는 논리 코어 하나이므로 148%는 약 1.48개 코어이며, 이전 standalone
`fsm_node` CPU와 직접 비교하면 안 된다. Full logical input은 평균 9.43 MiB/s로
줄지 않았고, DDS cloud만 0이 됐다. 따라서 이 단계의 주장은 Full 데이터 축소가
아니라 transport-induced stale 제거다.

## 재현 자료와 다음 gate

원자료:

- `results/full_intra_map1_10_n1_raw_20260903.csv`
- `results/full_intra_map7_10_n3_raw_20260903.csv`
- `results/full_intra_map7_10_add_n6_raw_20260903.csv`
- `results/full_intra_map8_add_n9_raw_20260903.csv`
- `results/full_intra_map9_n10_raw_20260903.csv`
- `results/full_intra_map1_10_n10_raw_20260903.csv` (최종 고유 100행)
- `results/full_raw_qos_depth1_map9_n10_raw_20260903.csv`
- `results/full_inprocess_control_map_summary_20260903.csv`

이 결과로 현재 10개 맵/프로파일에서 Full 코드와 설정을 동결한다. 이후
Full/Sector/Adaptive 비교는 이 Full을 paired control로만 재실행하고, 세 모드를
동일 cgroup 계측 경계로 재며 logical planner ingress와 external DDS를 별도 열로
보고해야 한다. Full의 추가 튜닝은 새 Full 실패 증거가 생길 때만 재개한다.
