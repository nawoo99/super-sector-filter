# Bounded same-map replan coalescing 실험 (2026-08-28~29)

## 결론

같은 immutable map version에서 성공한 `ReplanOnce`를 새 map commit까지
무기한 생략하는 첫 후보는 **기각**했다. seed9 run4 Adaptive가 waypoint 2/5에서
180초 timeout에 걸렸고, 정적 충돌은 없었지만 최저 여유가 +0.076 m였다. 정지 뒤
`PlanFromRest` 후보가 시작점부터 `OCCUPIED`로 판정되어 250회의 reroute search를
반복했다. 안전 정지는 작동했으나 liveness가 깨졌다.

두 번째 후보는 같은 map/version과 trajectory generation이라도 성공 replan 뒤
0.10초가 지나면 progress-driven replan을 다시 허용했다. 이 제한형은 seed9 smoke
3/3, seed5/8/9 crossed A/B 후보 15/15, map1-10 3-mode n=3의 Adaptive 30/30을
모두 완주했고 정적 충돌은 0이었다. 그러나 전체 n=3에서 Adaptive seed9 run3의
source-PCD 여유가 +0.043 m까지 내려갔고, seed9 평균 시간은 Full 83.55초 대비
Adaptive 95.62초였다. 따라서 구현은 default-off 실험 기능으로 보존하지만,
검증된 표준 `tight_v7` 프로파일에는 채택하지 않는다.

현재 관측 목표는 부분적으로 충족했다. 새 n=3에서 Full과 Adaptive는 각각
30/30 완주·정적 충돌 0이고, Sector는 30/30 완주했지만 seed8에서 정적 충돌
1회였다. Adaptive는 Full 대비 map update frequency 35.08%, points/update
15.76%, map total/update 20.72%, occupancy update 13.13%, processed application
payload 56.98%, FSM CPU 21.37%를 줄였다. 반면 평균 mission time은 7.65%
증가했다. 연산 절감과 Sector 접촉 회복은 보였지만 seed9의 시간/마진은 최종본
기준에 부족하다.

## 원인 분해

2026-08-28 최종 n=10에서 Adaptive의 Full 대비 추가 시간은 seed5/8/9에
집중됐다.

| map | Full / Adaptive 시간 (s) | Full / Adaptive brake | Full / Adaptive recovery (s) | Full / Adaptive `main_pre MAP_STALE` |
|---:|---:|---:|---:|---:|
| 5 | 66.65 / 73.85 | 15.5 / 25.5 | 15.87 / 26.24 | 11.7 / 22.5 |
| 8 | 74.08 / 82.53 | 25.9 / 37.3 | 27.91 / 37.40 | 22.2 / 32.5 |
| 9 | 80.48 / 89.15 | 21.8 / 35.6 | 27.33 / 37.77 | 13.8 / 28.2 |

Exact full-refresh ACK latency는 약 0.05초였고 timeout/loss는 없었다. 반면 성공한
same-map `ReplanOnce`가 한 map version에서 최대 8개 trajectory generation을
만들었다. run당 성공 same-map replan은 seed5 Full/Adaptive 39.1/61.1,
seed8 44.5/56.5, seed9 68.2/77.9였다. 따라서 ACK 손실이 아니라 map commit보다
빠른 replan timer의 중복 계산을 첫 최적화 대상으로 잡았다.

## 구현

`FsmRos2::replanTimerCallback()`에 다음 상태를 추가했다.

- 마지막 성공 replan의 map version, trajectory generation, steady-clock time
- same-map coalesced skip 누계
- default `false`인 `fsm/trajectory_guard/same_map_replan_coalesce_enable`
- default `0.0`인 `same_map_replan_min_interval_s`

skip 조건은 guard가 켜져 있고, map이 fresh하며, map version과 committed
trajectory generation이 직전 성공 replan과 같고, 경과 시간이 설정 interval보다
짧을 때뿐이다. 실패한 replan, guard rejection, 새 map, recovery가 만든 새
generation은 생략하지 않는다. 0.10초 후보에서는 15 Hz replan timer의 즉시 중복
tick만 줄이고 같은 map에서도 다음 progress replan을 강제로 허용한다.

표준 프로파일은 기존 default-off 상태로 복원했다. 실험 재현용 프로파일은 다음과
같다.

- `static_seedmaps_guard_viability_tight_v7_replan_coalesce_bounded.yaml`
- `static_seedmaps_guard_viability_tight_v7_filtered_reliable_replan_coalesce_bounded.yaml`

Raw-cloud CIRI shadow는 계속 false/non-authoritative다. clearance, FOV, brake,
hold, freshness threshold는 바꾸지 않았다.

## 무기한 후보 기각

중단된 raw는
`results/replan_coalesce_ab_seed5_8_9_n5_raw_20260828.csv`다. 27/30 행에서
중단했으며 baseline은 13/13, 후보는 13/14 완주였다. 후보 seed9 run4는
180초, waypoint 2/5, 정적 충돌 0, 여유 +0.076 m였다. map 193에서 마지막
성공 replan 두 번을 생략한 뒤 freshness brake가 걸렸고 stop 위치
`[-22.998,-19.346,2.267]` 부근에서 generation 87의 fallback 후보가 시작 직후
점유로 판정됐다. 이는 “새 정보가 없으니 성공 replan은 모두 무의미하다”는 가정이
차량 진행과 liveness를 무시했음을 보여준다.

## 제한형 smoke와 crossed A/B

seed9 smoke 3회는 3/3 완주·충돌 0, 시간 85.28~110.48초, 최저 여유
+0.233 m였다. raw는
`results/replan_coalesce_bounded_seed9_n3_raw_20260828.csv`다.

같은 바이너리에서 baseline과 제한형의 순서를 run마다 교차해 seed5/8/9를 각각
5회 비교했다. 양쪽 모두 15/15 완주·정적 충돌 0, retry/OOM 0이었다.

| 항목 | baseline | 제한형 | 변화 |
|---|---:|---:|---:|
| 평균 시간 (s) | 82.25 | 79.35 | -3.52% |
| 평균 / 최저 여유 (m) | 0.246 / 0.163 | 0.253 / 0.144 | +0.007 / -0.019 |
| brake / run | 34.33 | 28.93 | -15.73% |
| recovery active (s/run) | 34.06 | 30.39 | -10.79% |
| same-map skip / run | 0 | 91.4 | - |
| FSM CPU (%) | 76.56 | 73.84 | -3.55% |

paired time delta(candidate-baseline)는 평균 -2.896초, 중앙값 -0.520초였고 후보가
15쌍 중 8쌍에서 빨랐다. normal-approximation 95% interval은
[-7.072, +1.280]초로 0을 포함하므로 일관된 시간 개선이라고 주장하지 않는다.
map별 평균 delta는 seed5 -3.424초, seed8 +1.708초, seed9 -6.972초였다.
Raw는 `results/replan_coalesce_bounded_ab_seed5_8_9_n5_raw_20260828.csv`다.

## map1-10 Full/Sector/Adaptive n=3

Protocol은 v=7, `loop24.txt`, timeout 180초, source static PCD, strict-burst C++
filter, reliable depth-1 filtered link, 전역 연속 mode rotation이다. 표준 이름의
프로파일에 후보가 켜져 있던 테스트 시점의 내용은 위 두
`*_replan_coalesce_bounded.yaml`과 byte-identical하다. 캠페인 뒤 표준 프로파일은
default-off로 복원했다.

각 셀은 `완주 / 정적 충돌 event / 평균 시간 / 최저 여유`이고 마지막 열은
Adaptive effective full-open transition 총합이다.

| map | Full | Sector | Adaptive | Adaptive 전환 |
|---:|---:|---:|---:|---:|
| 1 | 3/3 / 0 / 59.47 s / +0.255 m | 3/3 / 0 / 61.05 s / +0.204 m | 3/3 / 0 / 65.03 s / +0.260 m | 43 |
| 2 | 3/3 / 0 / 56.64 s / +0.235 m | 3/3 / 0 / 56.53 s / +0.286 m | 3/3 / 0 / 58.57 s / +0.221 m | 62 |
| 3 | 3/3 / 0 / 66.58 s / +0.242 m | 3/3 / 0 / 63.38 s / +0.153 m | 3/3 / 0 / 68.94 s / +0.184 m | 39 |
| 4 | 3/3 / 0 / 68.31 s / +0.230 m | 3/3 / 0 / 71.76 s / +0.233 m | 3/3 / 0 / 74.78 s / +0.163 m | 32 |
| 5 | 3/3 / 0 / 66.61 s / +0.237 m | 3/3 / 0 / 68.52 s / +0.228 m | 3/3 / 0 / 75.37 s / +0.252 m | 29 |
| 6 | 3/3 / 0 / 69.11 s / +0.253 m | 3/3 / 0 / 75.32 s / +0.208 m | 3/3 / 0 / 76.06 s / +0.216 m | 32 |
| 7 | 3/3 / 0 / 73.72 s / +0.276 m | 3/3 / 0 / 77.83 s / +0.173 m | 3/3 / 0 / 76.84 s / +0.165 m | 37 |
| 8 | 3/3 / 0 / 75.12 s / +0.245 m | 3/3 / 1 / 76.40 s / -0.169 m | 3/3 / 0 / 75.45 s / +0.268 m | 26 |
| 9 | 3/3 / 0 / 83.55 s / +0.255 m | 3/3 / 0 / 80.06 s / +0.217 m | 3/3 / 0 / 95.62 s / +0.043 m | 18 |
| 10 | 3/3 / 0 / 79.54 s / +0.219 m | 3/3 / 0 / 91.06 s / +0.049 m | 3/3 / 0 / 85.38 s / +0.228 m | 26 |
| **전체** | **30/30 / 0 / 69.86 s / +0.219 m** | **30/30 / 1 / 72.19 s / -0.169 m** | **30/30 / 0 / 75.21 s / +0.043 m** | **344** |

Sector seed8 run1은 완주했지만 정적 충돌 1회, 여유 -0.169 m였다. 같은 block의
Adaptive는 75.88초, 충돌 0, 여유 +0.297 m로 회복했다. 그러나 discordant block이
1개뿐이므로 Full-Sector 및 Sector-Adaptive exact McNemar two-sided p-value는
각각 1.0이다. 이 n=3만으로 모드 간 population 차이를 확정하지 않는다.

Full/Adaptive 30/30의 Wilson 95% lower bound는 88.65%다. 이는 이 cohort에서
관측한 100%이지 population-level 100%나 formal collision freedom이 아니다.

## 연산량과 processed payload

값은 모드당 30 run의 run-level mean이다. payload는 ROG-Map이 실제 처리한
`PointCloud2.data` application payload이며 NIC/DDS/무선 wire bandwidth가 아니다.

| 항목 | Full | Sector | Adaptive | Sector vs Full | Adaptive vs Full |
|---|---:|---:|---:|---:|---:|
| mission time (s) | 69.86 | 72.19 | 75.21 | +3.33% | +7.65% |
| map update frequency (Hz) | 6.248 | 6.021 | 4.056 | -3.64% | -35.08% |
| points/update | 29,052 | 14,956 | 24,474 | -48.52% | -15.76% |
| map total/update (ms) | 37.451 | 13.717 | 29.692 | -63.37% | -20.72% |
| occupancy update (ms) | 13.339 | 4.732 | 11.588 | -64.52% | -13.13% |
| processed payload (Mbit/s) | 44.891 | 13.633 | 19.313 | -69.63% | -56.98% |
| FSM CPU (%) | 99.51 | 80.58 | 78.24 | -19.02% | -21.37% |
| same-map skips/run | 75.6 | 81.7 | 91.2 | - | - |
| effective full opens | 0 | 0 | 344 | - | 11.47/run |

같은 config switch가 Full/Sector에도 켜진 후보 캠페인이므로 세 모드 모두
same-map skip이 있다. 90행 모두 run/speed-valid, retry/OOM 0, ACK timeout/retry/
supersede/abandon/pending 0이었다.

## 메모리와 인프라

- max FSM RSS/PSS: 3,251.68 / 3,227.54 MiB
- FSM swap: 0 MiB
- host swap used peak: 2,048.00 MiB
- cgroup memory/swap peak: 8,195.80 / 710.13 MiB
- sampled memory PSI `some/full avg10` peak: 0.18 / 0.18
- infrastructure retry 0, OOM kill delta 0

Host swap은 캠페인 전부터 거의 찬 상태였지만 앞서 관측한 8.43 GiB FSM RSS
증가나 OOM은 재현되지 않았다. PSI 0.18은 한 Sector 행의 짧은 압박이며 캠페인
retry나 Full/Adaptive 실패로 이어지지 않았다.

## 채택 판단과 최종본까지 남은 일

제한형 same-map coalescing은 무기한 후보의 liveness 결함을 고쳤고 default-off
실험 기능으로는 보존할 가치가 있다. 그러나 표준 프로파일 채택은 보류한다.

1. seed9 Adaptive run3의 +0.043 m 구간을 source PCD/odom 시각으로 특정하고,
   same-map skip 직후인지 freshness brake/PlanFromRest 경로인지 분리한다.
2. replan 병합보다 seed9의 41.3 brakes/run, 48.56초 recovery를 만드는
   pre-stale refresh/map commit cadence를 안전 제약 안에서 줄인다.
3. 새 후보는 seed9 crossed baseline/candidate n>=10에서 완주 10/10, 충돌 0,
   worst source-PCD clearance가 최소 기존 최종 n=10 범위(+0.146 m 이상)로
   회복되는지 확인한다.
4. 통과할 때만 map1-10 Full/Sector/Adaptive n=10을 다시 실행한다.

최소 남은 machine time은 focused n=10 약 30~45분과 최종 300회 약 7~8시간,
분석/수정 시간을 합쳐 약 8~12시간이다. 설계 반복이 한 번 더 필요할 가능성을
포함하면 현실적으로 1~2 focused working day가 남았다.

최종 raw는
`results/replan_coalesce_bounded_3mode_seed1_10_n3_raw_20260829.csv`다.
`obs_skip_num` no-op, NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
`DRONE_R=robot_r` 지표 한계는 이 작업으로 해결되지 않았다.
