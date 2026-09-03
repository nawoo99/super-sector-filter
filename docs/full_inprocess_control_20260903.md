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
