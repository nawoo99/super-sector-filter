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

## 동결 Full을 사용한 3모드 hard-map gate

동결 뒤 첫 비교는 Map 7/9/10, Full/Sector/Adaptive, 모드당 맵별 3회로
실행했다. 모드 순서는 반복마다 회전했고, source static-PCD collision oracle,
45도 Sector/Adaptive, C++ sensor front end, Adaptive 5 Hz cloud/risk cap 및 180초
timeout을 유지했다. Full에만 위에서 검증한 `--full-intra-process`를 사용했다.

스모크 Map 7 3행과 별도로 본 campaign은 정확히 27개 고유
`(map, run, mode)` 행이다. 전 행이 first-attempt, run/speed/performance/cgroup-valid,
완주 및 무접촉이었다. Retry와 OOM도 0이다.

| Map | Mode | 완주 | 충돌 | 시간 평균±SD, s | clearance 평균/최저, m | logical ingress, MiB/s | E2E cores | E2E core·s | Adaptive effective-open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | Full | 3/3 | 0 | 77.71±7.27 | 0.276/0.259 | 11.727 | 1.464 | 116.457 | -- |
| 7 | Sector | 3/3 | 0 | 66.53±2.47 | 0.249/0.183 | 3.632 | 1.272 | 87.388 | -- |
| 7 | Adaptive | 3/3 | 0 | 69.79±3.80 | 0.254/0.241 | 2.836 | 1.304 | 93.571 | 64 (21.33/run) |
| 9 | Full | 3/3 | 0 | 75.23±4.50 | 0.241/0.195 | 13.624 | 1.499 | 116.359 | -- |
| 9 | Sector | 3/3 | 0 | 77.39±1.23 | 0.196/0.174 | 4.393 | 1.258 | 99.813 | -- |
| 9 | Adaptive | 3/3 | 0 | 72.27±4.67 | 0.242/0.214 | 3.530 | 1.334 | 98.960 | 68 (22.67/run) |
| 10 | Full | 3/3 | 0 | 73.89±4.29 | 0.207/0.182 | 13.077 | 1.529 | 116.805 | -- |
| 10 | Sector | 3/3 | 0 | 71.96±2.73 | 0.238/0.205 | 4.304 | 1.255 | 92.662 | -- |
| 10 | Adaptive | 3/3 | 0 | 71.05±1.32 | 0.246/0.243 | 3.368 | 1.347 | 98.743 | 59 (19.67/run) |

세 맵 합계의 Adaptive effective Full-open은 191회다. 원인 계수는 stall-open
6회, replan-guard open 250회, trajectory-guard open 54회다. 원인들이 겹치고
cooldown 동안 재발할 수 있으므로 원인 계수의 합은 실제 effective-open 전환 수와
같지 않다. Future-tail risk OCCUPIED는 12회, generation-independent current-body
OCCUPIED는 1회였고 접촉은 없었다.

### 동일 CPU 경계 해석

Linux cgroup은 한 프로세스를 구성요소별로 나눌 수 없다. 결합 Full의
`algorithm` child에는 simulator+planner가 함께 들어가지만, `cpp-frontend`
Sector/Adaptive의 simulator+filter는 별도 결합 프로세스이고 `algorithm` child에는
planner만 들어간다. 따라서 이 세 모드의 `algorithm_cpu_*`를 서로 비교하면 안 된다.
러너는 이제 각 행에 `algorithm_cpu_scope`,
`algorithm_cpu_excludes_simulator`, `end_to_end_cpu_scope`를 기록한다.

세 모드에 동일하게 simulator+frontend+planner+mission을 포함하는 parent cgroup의
`end_to_end_cpu_*`만 총 연산량의 직접 비교값으로 사용했다.

| 지표 | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| 시간, s | 75.609 | 71.959 | 71.039 | 6.044% 감소 | 1.279% 감소 |
| logical planner ingress, MiB/s | 12.809 | 4.110 | 3.245 | 74.669% 감소 | 21.050% 감소 |
| map update, Hz | 10.119 | 10.256 | 5.650 | 44.159% 감소 | 44.908% 감소 |
| ROG ms/frame | 37.151 | 11.013 | 23.395 | 37.028% 감소 | 112.431% 증가 |
| map-compute core equivalent | 0.376 | 0.113 | 0.132 | 64.857% 감소 | 16.956% 증가 |
| end-to-end mean cores | 1.498 | 1.261 | 1.328 | 11.300% 감소 | 5.303% 증가 |
| end-to-end core·s | 116.540 | 93.288 | 97.091 | 16.689% 감소 | 4.077% 증가 |
| peak end-to-end PSS, MiB | 3496.91 | 3518.03 | 3557.46 | 1.732% 증가 | 1.121% 증가 |

새 Full은 raw cloud DDS를 아예 통과하지 않으므로 external DDS는 0이다.
Sector/Adaptive external DDS는 4.110/3.247 MiB/s이고 Adaptive는 Sector보다
20.984% 낮다. 따라서 새 topology에서 Adaptive가 Full보다 DDS를 줄인다고
표현하면 안 된다. 반면 planner가 실제 ROG 입력으로 처리하는 logical ingress는
Adaptive가 Full보다 74.669% 작다.

이 gate는 Full의 잔여 hard-map 안정성과 Adaptive의 Full 대비 처리량/총 CPU 감소를
동시에 확인했다. Adaptive의 세 맵 worst clearance 0.214 m는 Sector의 0.174 m보다
높았지만, Sector도 9/9 완주·무접촉이어서 이 n=3 표본만으로 Adaptive의
완주율/충돌률 개선을 주장할 수는 없다. 다음 비교 단계는 같은 topology와 계측을
유지한 채 나머지 Map 1--6/8의 n=3을 채워 10맵 paired table을 완성하는 것이다.

추가 원자료:

- `results/full_control_three_mode_map7_9_10_n3_raw_20260903.csv`
- `results/full_control_three_mode_map7_9_10_n3_summary_20260903.csv`
- `results/full_control_three_mode_map7_9_10_n3_reductions_20260903.csv`

## 10맵 paired n=3 완성

같은 frozen profile로 남은 Map 1--6/8을 세 모드 각 3회 실행했다. 새 63행은
74.6분에 끝났고 전부 first-attempt 완주·무접촉이었다. Map 6의 과거 OOM도
재현되지 않았다. 앞선 hard-map 27행과 합친 최종 cohort는 Map 1--10,
Full/Sector/Adaptive, 맵·모드당 정확히 3회인 고유 90행이다. 모든 행이
run/speed/performance/cgroup-valid이고 retry/OOM은 0이다.

| Map | Full 시간 / 최저 clearance | Sector 시간 / 최저 clearance | Adaptive 시간 / 최저 clearance | Adaptive effective-open |
|---:|---:|---:|---:|---:|
| 1 | 58.36 s / 0.244 m | 60.24 s / 0.235 m | 59.34 s / 0.196 m | 47 |
| 2 | 57.35 s / 0.259 m | 55.74 s / 0.320 m | 55.37 s / 0.208 m | 61 |
| 3 | 58.30 s / 0.256 m | 57.37 s / 0.236 m | 57.60 s / 0.216 m | 63 |
| 4 | 61.65 s / 0.233 m | 64.23 s / 0.212 m | 61.23 s / 0.233 m | 55 |
| 5 | 59.88 s / 0.274 m | 61.96 s / 0.287 m | 59.33 s / 0.216 m | 52 |
| 6 | 67.87 s / 0.179 m | 66.96 s / 0.282 m | 64.58 s / 0.173 m | 69 |
| 7 | 77.71 s / 0.259 m | 66.53 s / 0.183 m | 69.79 s / 0.241 m | 64 |
| 8 | 63.42 s / 0.250 m | 65.57 s / 0.194 m | 63.88 s / 0.194 m | 67 |
| 9 | 75.23 s / 0.195 m | 77.39 s / 0.174 m | 72.27 s / 0.214 m | 68 |
| 10 | 73.89 s / 0.182 m | 71.96 s / 0.205 m | 71.05 s / 0.243 m | 59 |

시간은 각 맵의 3회 평균이고 clearance는 그 3회의 최솟값이다. 각 모드는
모든 맵에서 3/3 완주·충돌 0이다. Adaptive effective-open은 전체 605회,
평균 20.17회/run이다. 겹칠 수 있는 원인별 계수는 stall 8회, replan-guard
762회, trajectory-guard 122회다. Future-tail/current-body OCCUPIED verdict는
각각 12/1회였다.

| 지표 | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| 완주 / 충돌 | 30/30 / 0 | 30/30 / 0 | 30/30 / 0 | 동률 | 동률 |
| 시간 평균±SD, s | 65.37±8.11 | 64.79±7.04 | 63.45±6.15 | 2.939% 감소 | 2.081% 감소 |
| clearance 평균/최저, m | 0.260/0.179 | 0.262/0.174 | 0.249/0.173 | 평균 0.012 m 낮음 | 평균 0.014 m 낮음 |
| logical planner ingress, MiB/s | 9.409 | 2.808 | 2.270 | 75.876% 감소 | 19.178% 감소 |
| external DDS, MiB/s | 0 | 2.808 | 2.272 | 비교 불가 | 19.081% 감소 |
| map update, Hz | 10.124 | 10.273 | 5.459 | 46.076% 감소 | 46.856% 감소 |
| ROG ms/frame | 36.398 | 10.433 | 22.352 | 38.590% 감소 | 114.244% 증가 |
| map-compute core equivalent | 0.368 | 0.107 | 0.122 | 66.862% 감소 | 13.900% 증가 |
| end-to-end mean cores | 1.527 | 1.266 | 1.328 | 13.001% 감소 | 4.950% 증가 |
| end-to-end core·s | 102.630 | 84.422 | 86.853 | 15.373% 감소 | 2.879% 증가 |
| peak E2E PSS 평균, MiB | 3475.31 | 3429.10 | 3469.81 | 0.158% 감소 | 1.187% 증가 |

Map 6 run 1 Adaptive의 최저 clearance +0.173 m는 속도 1.46 m/s에서 발생해
초기 pose나 완전 정지값으로 제외할 수 없다. 이후 두 Adaptive 반복은
+0.248/+0.243 m였고 접촉은 없었으므로 현재는 단일 low-margin 관측이다.
Full 최저 +0.179 m는 Map 6 출발 직후 0.48 m/s, Sector 최저 +0.174 m는 Map 9
출발부 0.51 m/s였다. 최종 주장에서는 충돌 0과 0.20 m clearance contract를
구분해야 한다.

메모리 계측은 전 행 OOM 0, 전체 system available 최저 약 3.86 GiB,
swap 최고 약 1,022 MiB였다. Map 3 run 2 Adaptive 한 행에 PSI some/full 0.69가
짧게 기록됐지만 available 4.51 GiB, end-to-end PSS 3.40 GiB였고 재시도 없이
완주했다. 이전의 swap 포화·수백 MiB available·높은 PSI 상황과 다르므로
infrastructure/memory failure로 분류하지 않는다.

이 표본은 Full 동결을 다시 지지하고 Adaptive의 Full 대비 처리량 및 총 CPU
절감을 보여준다. 반면 Sector도 30/30 무접촉이고 Adaptive의 평균 clearance와
Sector 대비 CPU는 개선되지 않았다. 따라서 현재 10개 static map은
`Full과 같은 관측 안전을 더 적은 처리량으로 달성`하는 결과에는 적합하지만,
`Sector의 완주/충돌 열화를 Adaptive가 회복`한다는 별도 가설에는 식별력이 없다.

최종 자료:

- `results/full_control_three_mode_map1_10_n3_raw_20260903.csv`
- `results/full_control_three_mode_map1_10_n3_summary_20260903.csv`
- `results/full_control_three_mode_map1_10_n3_reductions_20260903.csv`
- 원래 두 실행 cohort는 combined raw의 `source_cohort`와
  `source_campaign_sequence_index`로 보존했다.

## 10맵 paired n=5 반복 확대

동일한 frozen profile과 mode rotation을 유지하고 run 4--5만 추가했다. 추가
60행은 76.7분에 끝났고, 전체 자료는 Map 1--10 × 3모드 × 5회인 고유 150행이다.
모든 행이 run/speed/performance/cgroup-valid이고 retry/OOM은 0이다. Full과
Adaptive는 50/50 완주, Sector는 49/50 완주였으며 세 모드 모두 static-PCD
충돌은 0이다.

| Map | Full 완주 / 시간 / 최저 clearance | Sector 완주 / 시간 / 최저 clearance | Adaptive 완주 / 시간 / 최저 clearance | Adaptive effective-open |
|---:|---:|---:|---:|---:|
| 1 | 5/5 / 57.92 s / 0.244 m | 5/5 / 59.27 s / 0.235 m | 5/5 / 58.51 s / 0.196 m | 89 |
| 2 | 5/5 / 57.21 s / 0.259 m | 5/5 / 54.96 s / 0.299 m | 5/5 / 55.01 s / 0.208 m | 106 |
| 3 | 5/5 / 58.70 s / 0.256 m | 5/5 / 56.93 s / 0.236 m | 5/5 / 57.18 s / 0.216 m | 110 |
| 4 | 5/5 / 62.87 s / 0.233 m | 5/5 / 62.88 s / 0.212 m | 5/5 / 61.43 s / 0.227 m | 103 |
| 5 | 5/5 / 61.58 s / 0.273 m | 5/5 / 64.00 s / 0.199 m | 5/5 / 58.17 s / 0.216 m | 98 |
| 6 | 5/5 / 67.46 s / 0.179 m | 5/5 / 67.26 s / 0.282 m | 5/5 / 65.30 s / 0.173 m | 111 |
| 7 | 5/5 / 75.39 s / 0.187 m | 5/5 / 66.81 s / 0.183 m | 5/5 / 68.63 s / 0.186 m | 98 |
| 8 | 5/5 / 62.78 s / 0.213 m | 5/5 / 65.19 s / 0.194 m | 5/5 / 63.34 s / 0.194 m | 110 |
| 9 | 5/5 / 74.62 s / 0.183 m | 5/5 / 79.33 s / 0.174 m | 5/5 / 72.85 s / 0.214 m | 107 |
| 10 | 5/5 / 76.66 s / 0.182 m | 4/5 / 94.94 s / 0.021 m | 5/5 / 71.06 s / 0.178 m | 99 |

시간은 timeout을 포함한 맵별 5회 평균이다. Map 10 Sector 성공 4행만의 평균은
73.67초다. 이 모드의 run 4는 waypoint 4까지 간 뒤 180초 timeout으로 끝났고,
동일 paired run의 Full은 86.70초, Adaptive는 68.96초에 완주했다.

| 지표 | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| 완주 / 충돌 | 50/50 / 0 | 49/50 / 0 | 50/50 / 0 | 완주 동률 | +1 완주 |
| 종료시간 평균±SD, s | 65.52±7.99 | 67.16±17.99 | 63.15±6.31 | 3.617% 감소 | 5.966% 감소 |
| 성공행 시간 평균, s | 65.52 | 64.85 | 63.15 | 3.617% 감소 | 2.627% 감소 |
| clearance 평균/최저, m | 0.265/0.179 | 0.259/0.021 | 0.254/0.173 | 평균 0.011 m 낮음 | 평균 0.005 m 낮음 |
| logical planner ingress, MiB/s | 9.407 | 2.846 | 2.237 | 76.220% 감소 | 21.404% 감소 |
| external DDS, MiB/s | 0 | 2.846 | 2.240 | 비교 불가 | 21.308% 감소 |
| map update, Hz | 10.124 | 10.256 | 5.415 | 46.512% 감소 | 47.198% 감소 |
| ROG ms/frame | 36.452 | 10.369 | 21.956 | 39.769% 감소 | 111.747% 증가 |
| map-compute core equivalent | 0.369 | 0.106 | 0.119 | 67.734% 감소 | 11.929% 증가 |
| end-to-end mean cores | 1.530 | 1.256 | 1.325 | 13.378% 감소 | 5.483% 증가 |
| end-to-end core·s | 103.180 | 85.703 | 86.339 | 16.323% 감소 | 0.742% 증가 |
| peak E2E PSS 평균, MiB | 3476.82 | 3432.68 | 3472.32 | 0.129% 감소 | 1.155% 증가 |

Map 10 run 4 Sector 실패는 infrastructure failure가 아니다. 실패 행은 retry 0,
OOM 0, memory PSI 0이었고 system available 2.12 GiB였다. 로그에서는
`[19.525,-19.425,1.925]` 부근 certified stop 뒤 exclusion zone 6개가 포화되고,
거의 같은 짧은 후보가 CIRI에서 즉시 OCCUPIED로 100회 이상 반복 거절됐다.
`TRAJ_GUARD_REROUTE_STALL`은 saturated/hold를 반복했으므로, 원인은 안전 정지는
유지하지만 새로운 topology로 빠져나오지 못하는 Sector liveness trap이다.
동일 run Adaptive는 effective-open 19회, replan-guard 27회, trajectory-guard 8회와
future-tail/current-body OCCUPIED 각 1회를 기록하고 완주했다.

Adaptive effective-open은 총 1,031회(20.62회/run)다. 겹칠 수 있는 원인 계수는
stall-open 발생 run 11개, replan-guard 1,266회, trajectory-guard 198회이고,
future-tail/current-body OCCUPIED verdict는 21/3회다. 0.20 m 미만 clearance는
여러 모드에서 관측됐으므로 여전히 contact-free와 clearance contract를 분리한다.

전체 150행에서 system available 최저는 2.06 GiB, swap 최고는 1.87 GiB였지만
OOM은 0이고 새 실패의 PSI는 0이다. 완주 50/50의 Wilson 95% 하한은 92.87%,
Sector 49/50은 89.50%다. 이 체크포인트는 Full/Adaptive 안정성과 첫 paired
Sector 열화→Adaptive 회복 사례를 제공하지만, 단일 discordant pair이므로 설정을
동결한 채 run 6--10을 추가한다.

체크포인트 자료:

- `results/full_control_three_mode_map1_10_n5_raw_20260903.csv`
- `results/full_control_three_mode_map1_10_n5_summary_20260903.csv`
- `results/full_control_three_mode_map1_10_n5_reductions_20260903.csv`

## 10맵 paired n=10 확장 및 resource-pressure audit

동일 frozen profile과 mode rotation으로 run 6--10을 추가했다. 공식 cohort는
Map 1--10 × Full/Sector/Adaptive × 10회인 정확히 300개 고유 행이다. 모든 행이
run/speed/performance/cgroup-valid이고 retry와 OOM kill은 0이다. 명목 완주는
Full/Sector/Adaptive 모두 99/100, source static-PCD 충돌은 모두 0이다.

| Map | Full 완주 / 시간 / 최저 clearance | Sector 완주 / 시간 / 최저 clearance | Adaptive 완주 / 시간 / 최저 clearance | Adaptive effective-open |
|---:|---:|---:|---:|---:|
| 1 | 10/10 / 58.17 s / 0.244 m | 10/10 / 60.27 s / 0.218 m | 10/10 / 58.24 s / 0.196 m | 189 |
| 2 | 10/10 / 57.43 s / 0.259 m | 10/10 / 55.37 s / 0.297 m | 10/10 / 54.62 s / 0.208 m | 203 |
| 3 | 10/10 / 58.95 s / 0.256 m | 10/10 / 56.55 s / 0.170 m | 10/10 / 57.06 s / 0.216 m | 194 |
| 4 | 10/10 / 63.08 s / 0.233 m | 10/10 / 64.50 s / 0.191 m | 10/10 / 61.91 s / 0.169 m | 198 |
| 5 | 10/10 / 62.20 s / 0.222 m | 10/10 / 62.42 s / 0.199 m | 10/10 / 59.39 s / 0.216 m | 200 |
| 6 | 10/10 / 67.40 s / 0.174 m | 10/10 / 66.69 s / 0.247 m | 10/10 / 64.57 s / 0.173 m | 204 |
| 7 | 10/10 / 74.15 s / 0.187 m | 10/10 / 67.61 s / 0.183 m | 10/10 / 67.61 s / 0.186 m | 172 |
| 8 | 10/10 / 65.73 s / 0.213 m | 10/10 / 64.00 s / 0.194 m | 10/10 / 63.81 s / 0.194 m | 213 |
| 9 | 10/10 / 76.54 s / 0.183 m | 10/10 / 75.69 s / 0.174 m | 10/10 / 72.91 s / 0.214 m | 203 |
| 10 | 9/10 / 89.91 s / 0.182 m | 9/10 / 85.73 s / 0.021 m | 9/10 / 84.60 s / 0.178 m | 233 |

시간은 timeout/HUNG 행을 포함한 맵별 평균이다. 성공행만의 전체 평균은
Full/Sector/Adaptive 66.00/64.73/63.23초다. 0.20 m 미만 clearance는 각각
6/11/8행이었다. 따라서 세 모드 모두 contact-free이지만 0.20 m clearance
contract는 만족하지 않는다.

| 지표 | Full | Sector | Adaptive | Adaptive vs Full | Adaptive vs Sector |
|---|---:|---:|---:|---:|---:|
| 완주 / 충돌 | 99/100 / 0 | 99/100 / 0 | 99/100 / 0 | 동률 | 동률 |
| 종료시간 평균±SD, s | 67.36±15.79 | 65.88±13.70 | 64.47±14.11 | 4.281% 감소 | 2.143% 감소 |
| 성공행 시간 평균, s | 66.00 | 64.73 | 63.23 | 4.207% 감소 | 2.323% 감소 |
| clearance 평균/최저, m | 0.270/0.174 | 0.261/0.021 | 0.258/0.169 | 평균 0.013 m 낮음 | 평균 0.003 m 낮음 |
| logical planner ingress, MiB/s | 9.343 | 2.832 | 2.251 | 75.903% 감소 | 20.502% 감소 |
| external DDS, MiB/s | 0 | 2.832 | 2.254 | 비교 불가 | 20.405% 감소 |
| map update, Hz | 10.088 | 10.279 | 5.437 | 46.109% 감소 | 47.112% 감소 |
| ROG ms/frame | 36.993 | 10.423 | 22.384 | 39.491% 감소 | 114.747% 증가 |
| map-compute core equivalent | 0.372 | 0.107 | 0.122 | 67.254% 감소 | 13.556% 증가 |
| end-to-end mean cores | 1.543 | 1.259 | 1.337 | 13.362% 감소 | 6.175% 증가 |
| end-to-end core·s | 108.503 | 84.858 | 90.114 | 16.948% 감소 | 6.193% 증가 |
| peak E2E PSS 평균, MiB | 3475.89 | 3425.39 | 3467.01 | 0.255% 감소 | 1.215% 증가 |

Adaptive effective Full-open은 총 2,009회, 평균 20.09회/run이다. 겹칠 수 있는
원인 계수는 stall-open 발생 run 23개, replan-guard open 2,591회,
trajectory-guard open 390회다. Future-tail/current-body OCCUPIED verdict는
35/6회다.

### 세 실패와 memory-pressure 교란

Map 10 run 4 Sector 실패는 n=5에서 분석한 동일한 topology/liveness trap이다.
4/5 waypoint, 180초, clearance +0.021 m였고 PSI/OOM/retry는 모두 0이었다.
같은 pair의 Full/Adaptive는 완주했으므로 Adaptive가 Sector 실패를 회복한
discordant pair 한 건이다.

Map 10 run 8은 Sector가 85.50초에 완주한 반면 Adaptive가 3/5 waypoint에서
187.70초 timeout, Full이 2/5 waypoint에서 201.20초 monitor HUNG으로 끝났다.
충돌은 없고 clearance는 Adaptive/Full +0.231/+0.275 m였다. 두 행의 system
available 최저는 약 249 MiB, swap은 2.0 GiB로 포화됐고 memory PSI
some/full 최대가 Adaptive 55.87/52.89, Full 64.26/60.66이었다. Full은 시작부터
PSI some 28.43이었으며 약 90초 이후 planner stack 출력도 멎었다. OOM kill은
없었지만 정상적인 독립 planner liveness 관측으로 보기 어려운 심한 host-memory
교란이다. Adaptive 로그에는 같은 정지점에서 A* timeout과 optimizer overtime이
반복돼 planner trap과 자원 압박이 서로 증폭된 흔적도 있다. 어느 하나를 유일
원인으로 확정하지 않는다.

자원 회복 후 Map 10에서 Full/Adaptive를 각 2회 clean audit했다. 네 행 모두
PSI 0, retry/OOM 0, 충돌 0으로 완주했다. Full은 72.16/79.43초,
Adaptive는 76.88/75.28초였다. 이는 run 8 동시 실패가 재현되지 않았다는 보조
근거지만 n=2라서 원인을 확정하거나 공식 300행 실패를 대체하지 않는다.

대화 세션 중단으로 공식 runner가 Map 10 run 9 Adaptive 시작 직후 사라지고 ROS
child만 고아가 된 infrastructure-interrupted attempt도 별도 보존했다. 그 monitor는
0/5, 180.88초 결과를 남겼지만 CPU/메모리 집계와 CSV finalize가 없고 launch가
3시간 이상 남았으므로 공식 cohort에서 제외했다. 고아 process group을 정리한 뒤
`--resume-existing`으로 미기록 여섯 키를 다시 실행했고 모두 정상 완료됐다.
선택적 성공 재시도가 아니라 incomplete harness row의 재수집이며, 원 attempt
파일도 artifact에 남겼다.

명목 Adaptive 대 Sector discordance는 각 방향 한 건이므로 two-sided exact
McNemar p=1.0이다. 세 모드의 99/100 Wilson 95% 완주율 하한은 94.55%다.
따라서 n=10은 Full/Adaptive의 population-level 100%를 입증하지 않으며,
Adaptive가 Sector 성공률을 개선했다는 주장도 지지하지 않는다. 다만 Full 대비
planner ingress/map compute/동일 end-to-end CPU 감소는 n=100에서도 유지됐다.

최종 자료:

- `results/full_control_three_mode_map1_10_n10_raw_20260903.csv`
- `results/full_control_three_mode_map1_10_n10_summary_20260903.csv`
- `results/full_control_three_mode_map1_10_n10_reductions_20260903.csv`
- `results/full_control_map10_resource_clean_audit_full_adaptive_n2_raw_20260904.csv`

## 완주 실패 원인 재분류와 재발 방지 (2026-09-04)

기존 n=10 러너는 메모리와 PSI를 CSV에 측정하면서도 `run_valid` 판정이나 재시도
조건에는 사용하지 않았다. 따라서 Map 10 run 8의 두 행이 `run_valid=True`로
기록된 것은 planner 유효성의 증거가 아니라 당시 스키마의 결함이다. 원자료는
소급 변경하지 않고 아래처럼 해석을 정정한다.

| 사건 | 직접 관측 | 분류 | 근거 |
|---|---|---|---|
| Map 10 run 4 Sector | 4/5 waypoint, 180 s, clearance +0.021 m | 유효한 Sector topology/liveness 실패 | available 2.12 GiB, PSI 0, OOM/retry 0; exclusion zone 6개 포화 뒤 같은 candidate/CIRI OCCUPIED를 100회 이상 반복 |
| Map 10 run 8 Adaptive | 3/5 waypoint, 187.70 s | resource-confounded, planner 성공률 분모에서 제외해야 할 시도 | available 최저 249 MiB, swap 포화, PSI some/full 55.87/52.89; A-star timeout/optimizer overtime 반복 |
| Map 10 run 8 Full | 2/5 waypoint, 201.20 s monitor HUNG | resource-confounded, planner 성공률 분모에서 제외해야 할 시도 | available 최저 249 MiB, swap 포화, 시작 PSI 28.43/26.79, 최대 64.26/60.66; 후반 planner 로그 정지 |
| Map 10 run 9 Adaptive 고아 attempt | runner 없이 ROS child가 3시간 이상 잔존 | 불완전 infrastructure attempt | CPU/메모리 집계와 CSV finalize가 없으므로 공식 행이 될 수 없음 |

이 사후 분류만 적용하면 비교 가능한 planner-valid 관측은 Full 99/99 완주,
Sector 99/100, Adaptive 99/99가 된다. 그러나 제외 기준이 campaign 뒤에 도입된
post-hoc 분석이므로 이를 새 논문 headline 성공률로 바꾸지 않는다. 새 gate를
처음부터 켠 prospective 반복으로 확인해야 한다.

Sector run 8도 available 최저 340 MiB였지만 PSI 최대는 1.89였고 완주했다. 따라서
`MemAvailable`만을 실패의 인과 임계값으로 해석할 수는 없다. Run 8 Full/Adaptive
실패를 구분하는 강한 동시 관측은 50%를 넘은 PSI이며, clean audit 네 행이
available 최저 6.42--6.54 GiB, PSI 0에서 모두 완주한 점도 자원 교란 설명을
지지한다. 다만 Adaptive 로그에 실제 recovery loop가 함께 있었으므로 자원 압박이
유일 원인이라고 단정하지 않는다. 깨끗한 자원 조건에서 다시 재현될 때만
Full/Adaptive planner 결함으로 승격한다.

재발 방지를 위해 `scripts/native_campaign/native_campaign.py`에 다음을 기본값으로
구현했다.

1. 각 attempt 전에 `MemAvailable >= 8192 MiB`, PSI some/full avg10 `<= 10/5`가
   5초 연속 유지돼야 launch한다.
2. 실행 중 available 2048 MiB 미만 또는 PSI 임계 초과가 5초 지속되면 즉시
   process group을 종료하고 infrastructure attempt로 보존한 뒤 재시도한다.
3. 600초 안에 preflight가 회복되지 않으면 pending row를 쓰지 않고 campaign을
   중단한다. 자원을 정리한 뒤 같은 파일에 `--resume-existing`으로 이어간다.
4. CSV에 `resource_valid`, `infrastructure_failure`, gate 임계값/대기시간/abort
   횟수/이유를 기록하고 `run_valid`와 결합한다.
5. 모든 launch를 등록된 독립 process group으로 만들고 SIGINT/SIGTERM/SIGHUP 및
   정상 종료에서 전부 정리해, runner 중단 후 고아 ROS stack이 남지 않게 했다.

2 GiB runtime floor는 과거 성공/실패를 가르는 통계적 인과 경계가 아니라, 새
cohort를 저자원 조건에서 계속 수집하지 않기 위한 보수적 실험 품질 정책이다.
임계값을 다른 머신에서 바꿔야 한다면 첫 실험 전에 고정하고 모든 모드에 동일하게
적용해야 한다. `--no-resource-guard`는 과거 명령 재현 전용이며 새 결과에는 쓰지
않는다.

검증은 native-campaign pytest 33개 통과, 강제 저자원 preflight 시험에서 launch
전 non-zero 종료 및 결과 행 0개를 확인했다. 현재 작업 세션은 VS Code extension
host가 약 6.3 GiB RSS를 점유해 available이 약 5.0 GiB이므로 새 기본 gate가 실제
Map 10 launch를 의도대로 차단한다. 메모리를 회수한 뒤 Map 10 Full/Adaptive를
동일 gate로 재시험해야 하며, 그 전에는 planner 파라미터를 추가 변경하지 않는다.

## Resource-valid Map 10 prospective 재시험 (2026-09-04)

VS Code extension host를 시험 동안 분리해 launch 전 available 약 9 GiB, swap 0,
PSI 0인 상태를 만들고, 새 기본 resource gate를 첫 행부터 적용해 Map 10 Full과
Adaptive를 모드당 3회 회전 순서로 재시험했다. Planner/config/filter parameter는
바꾸지 않았다. 6행 모두 first-attempt, run/resource/speed/performance/cgroup-valid,
완주 및 static-PCD 무접촉이었다. Resource abort, retry, OOM은 모두 0이다.

| run | Full 시간 / clearance / available 최저 / PSI 최대 | Adaptive 시간 / clearance / available 최저 / PSI 최대 | Adaptive effective-open |
|---:|---:|---:|---:|
| 1 | 63.64 s / 0.284 m / 5876.75 MiB / 0.18 | 66.28 s / 0.254 m / 5765.79 MiB / 0 | 18 |
| 2 | 69.90 s / 0.270 m / 5850.75 MiB / 0 | 63.35 s / 0.261 m / 5830.97 MiB / 0 | 17 |
| 3 | 66.93 s / 0.270 m / 5853.91 MiB / 0 | 66.66 s / 0.254 m / 5679.31 MiB / 0 | 13 |
| **합계/평균** | **3/3, 66.82 s, 0.275 m** | **3/3, 65.43 s, 0.256 m** | **48** |

Adaptive는 Full 대비 logical planner ingress 75.175%, map-update cadence 48.526%,
ROG map compute per frame 29.627%, 공통 end-to-end mean cores 10.799%, core-seconds
13.431%를 줄였다. Peak PSS는 오히려 1.990% 높아 메모리 절감 주장은 하지 않는다.

이 prospective 결과는 resource-invalid run 8 실패가 깨끗한 조건에서 재현되지
않았다는 근거를 n=2 clean audit에서 n=5/mode 누적으로 강화한다. 따라서 현재
Full/Adaptive 코드를 바꾸지 않는 판단을 유지한다. 다만 이번 새 cohort 자체는
n=3/mode이므로 population-level 100% 보장이 아니며, 후속 공식 성공률 추정에는
resource gate를 처음부터 적용한 더 큰 반복이 필요하다.

자료:

- `results/map10_resource_guard_prospective_full_adaptive_n3_raw_20260904.csv`
- `results/map10_resource_guard_prospective_full_adaptive_n3_summary_20260904.csv`
- `results/map10_resource_guard_prospective_full_adaptive_n3_reductions_20260904.csv`

## Prospective resource-gated 10맵 3모드 n=10 최종 결과 (2026-09-05)

Map 10 3모드 n=10 gate 30/30 통과 후 같은 frozen profile과 gate로 Map 1--10 ×
Full/Sector/Adaptive × n=10, 총 300개 고유 row를 새로 수집했다. 모두 첫
attempt였고 resource abort/retry/OOM/static-PCD 충돌은 0이다. Full과 Adaptive는
100/100 완주·유효, Sector는 100/100 완주지만 Map 9 run 2의 10.95563 m/s
flag-3 overspeed 때문에 99/100 유효다. 따라서 전체 strict validation은 한 개의
quality failure로 FAIL이며, 실패를 재시험 성공으로 대체하지 않았다.

Adaptive는 Full 대비 평균시간 3.247%, map compute/frame 38.599%, 공통 E2E
mean cores 13.709%, core·s 16.574%, planner ingress 75.632%를 줄였다. Peak PSS는
0.328% 높았다. Adaptive effective-open은 1,904회(19.04/run)다. Full raw DDS는
in-process이므로 DDS의 Full 대비 감소율을 내지 않고, algorithm CPU도 scope가
다르므로 공통 E2E cgroup만 비교한다. Sector가 포함된 pooled reduction은 한
invalid row 때문에 공식 비교에서 제외한다.

Map 9 failure는 brake reject 뒤 EMER_STOP에서도 ordinary command를 허용하는
`pubCmdTimerCallback`, PerfectDrone의 command-state 직접 대입, 위치 차분 속도
추정, `max(v7, initial speed)` brake cap이 이어진 공통 guard 결함으로 분석됐다.
다음 변경은 guard-enabled EMER_STOP ordinary command 차단과 continuity-qualified
velocity, reject→retry 회귀시험이다. 세부 맵별 표, clearance, resource/swap 및
통계 한계는 `docs/resource_guard_campaign_final_20260905.md`와 viability §8.59를
기준으로 한다.
