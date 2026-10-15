# Speed-gated nearest-face 후보 최종 n=10, cgroup 연산량, 실패 포렌식 (2026-08-31)

## 1. 목적과 고정 조건

2026-08-30의 speed-gated nearest-face clearance 후보를 같은 바이너리로
Map 1~10, Full/Sector/Adaptive, 모드당 map별 10회씩 총 300회 검증했다.
모드 순서는 run마다 회전했다. 속도는 7 m/s이고 source static PCD를 권위 있는
충돌 판정으로 사용했다.

- Full profile: `static_seedmaps_guard_viability_tight_v7.yaml`
- Sector/Adaptive profile:
  `static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml`
- static-PCD monitor, reliable filtered-map generation/ACK, slowdown Full refresh
  `1.5/3.0 m/s`를 유지했다.
- raw-cloud CIRI는 계속 disabled/non-authoritative다.
- timeout은 180 s이며 startup retry 정책은 유지했다.

## 2. 새 cgroup 계측의 범위

Runner에 `--cgroup-cpu-accounting`을 추가했다. cgroup v2의 hierarchical
`cpu.stat:usage_usec`를 사용하므로 기존 `mission_time × process CPU%` 근사와
달리 계측 창 전체의 실제 CPU 시간을 직접 합산한다.

- Algorithm cgroup: `fsm_node` + 해당되는 경우 native C++ filter
- Stack cgroup: launch wrapper + simulator + waypoint mission
- End-to-end: 위 두 child를 포함하는 parent cgroup의 hierarchical CPU
- 보고 단위: core·s/attempt, 평균 cores, interval-weighted p95 cores

호스트 root cgroup에는 memory controller가 위임되지 않아 `memory.current`는
사용할 수 없었다. 메모리는 10초마다 cgroup member PID의 `/proc` RSS/PSS/swap을
합산했다. 따라서 CPU는 cgroup-native이고, 메모리는 process-PSS 기반이다.
Full과 동일 시점의 비-cgroup Map 10 대조 1회도 99.41 s였고 cgroup Full
smoke는 111.26 s였다. cgroup에는 CPU quota/weight가 없고 sampling은
`cpu.stat` 1초, PSS 10초 cadence이므로 이 차이는 단일-run trajectory 변동으로
분류했다.

## 3. 캠페인 무결성

- 300 rows / 300 unique `(map, run, mode)`
- first attempt, run-valid, speed-valid, perf-valid: 각각 300/300
- cgroup accounting 성공: 300/300
- retry / OOM kill / speed violation: 0 / 0 / 0
- source static-PCD enabled: 300/300
- 잔류 process/cgroup: 0

중요: `collisions`는 live-cloud 후보도 포함한다. 최종 안전 판정은
`safety_collisions`이며, static-PCD와 일치한 접촉만 센다.

## 4. 전체 결과

| Mode | Completion | Safety-qualified | Joint | Mean time | Worst static clearance | Algorithm core·s | End-to-end core·s | Payload | Points/update | Map time/update |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 100/100 | 99/100 | 99/100 | 73.892 s | -0.144 m | 90.175 | 106.278 | 6.268 MiB/s | 29,643.5 | 42.932 ms |
| Sector | 99/100 | 100/100 | 99/100 | 72.723 s | +0.047 m | 75.633 | 91.946 | 2.040 MiB/s | 15,682.6 | 15.469 ms |
| Adaptive | 100/100 | 100/100 | 100/100 | 73.815 s | +0.106 m | 78.249 | 94.226 | 2.736 MiB/s | 24,461.6 | 31.945 ms |

Adaptive의 Full 대비 paired run-mean 변화:

- Algorithm CPU: **-13.226%**, 차이 95% CI `[-13.674, -10.179] core·s`
- End-to-end CPU: **-11.340%**, 차이 95% CI `[-14.218, -9.885] core·s`
- Processed application payload: **-56.346%**
- Points/update: **-17.481%**
- Map time/update: **-25.591%**
- Mission time: **-0.104%**, 차이 95% CI `[-2.664, +2.510] s`

`processed payload`는 ROG-Map application payload이며 NIC/DDS/RTPS wire
bandwidth가 아니다.

## 5. CPU 동시성 및 메모리

| Mode | Algorithm mean cores | Algorithm p95 | End-to-end mean cores | End-to-end p95 | Algorithm peak-PSS p95 | End-to-end peak-PSS p95 |
|---|---:|---:|---:|---:|---:|---:|
| Full | 1.180 | 1.611 | 1.391 | 1.824 | 3,234.6 MiB | 3,609.6 MiB |
| Sector | 1.006 | 1.301 | 1.223 | 1.522 | 3,220.7 MiB | 3,592.4 MiB |
| Adaptive | 1.025 | 1.359 | 1.234 | 1.572 | 3,252.2 MiB | 3,618.7 MiB |

평균 cores는 mode별 총 core·s / 총 cgroup duration이다. p95는 trace interval을
실제 duration으로 가중했다. Filtered mode는 CPU를 줄였지만 process PSS는
약 3.2/3.6 GiB로 Full과 실질적으로 같았다. 즉 이번 최적화의 이득은 CPU와
처리량이고 메모리 절감은 아니다.

Adaptive는 effective Full-view open 1,736회, 평균 17.36회/run이었다.
Slowdown Full-refresh trigger는 4,778회다.

## 6. Map별 결과

각 셀은 `completion · safety · time(s) · algorithm core·s · payload(MiB/s)`다.
Adaptive 셀의 마지막 값은 10회 합산 effective Full opens다.

| Map | Full | Sector | Adaptive |
|---|---|---|---|
| Map 1 | 10/10 · 10/10 · 65.86 · 96.62 · 4.80 | 10/10 · 10/10 · 64.32 · 75.80 · 1.45 | 10/10 · 10/10 · 64.00 · 77.65 · 1.61 · 204 |
| Map 2 | 10/10 · 10/10 · 61.08 · 91.04 · 4.87 | 10/10 · 10/10 · 60.26 · 72.61 · 1.36 | 10/10 · 10/10 · 60.52 · 73.51 · 1.53 · 204 |
| Map 3 | 10/10 · 10/10 · 64.70 · 94.04 · 6.13 | 9/10 · 10/10 · 77.97 · 88.85 · 1.84 | 10/10 · 10/10 · 63.89 · 76.56 · 2.19 · 213 |
| Map 4 | 10/10 · 10/10 · 70.32 · 83.18 · 5.23 | 10/10 · 10/10 · 69.59 · 71.87 · 1.76 | 10/10 · 10/10 · 68.17 · 75.76 · 2.50 · 186 |
| Map 5 | 10/10 · 10/10 · 72.37 · 85.77 · 5.65 | 10/10 · 10/10 · 68.47 · 71.37 · 1.91 | 10/10 · 10/10 · 67.73 · 72.79 · 2.54 · 189 |
| Map 6 | 10/10 · 10/10 · 75.18 · 83.97 · 5.74 | 10/10 · 10/10 · 73.74 · 73.09 · 2.02 | 10/10 · 10/10 · 78.91 · 79.15 · 2.87 · 144 |
| Map 7 | 10/10 · 9/10 · 89.91 · 91.01 · 6.62 | 10/10 · 10/10 · 76.39 · 74.28 · 2.34 | 10/10 · 10/10 · 80.52 · 78.91 · 3.35 · 151 |
| Map 8 | 10/10 · 10/10 · 71.60 · 82.82 · 6.45 | 10/10 · 10/10 · 70.89 · 70.06 · 2.13 | 10/10 · 10/10 · 72.50 · 73.81 · 3.07 · 152 |
| Map 9 | 10/10 · 10/10 · 84.65 · 99.98 · 9.08 | 10/10 · 10/10 · 83.90 · 79.17 · 2.78 | 10/10 · 10/10 · 90.48 · 88.09 · 3.95 · 158 |
| Map 10 | 10/10 · 10/10 · 83.26 · 93.31 · 8.10 | 10/10 · 10/10 · 81.70 · 79.22 · 2.83 | 10/10 · 10/10 · 91.42 · 86.27 · 3.75 · 135 |

## 7. 통계 경계

Wilson 95% interval:

- Adaptive completion/safety/joint 100/100: `96.301%~100%`
- Full safety/joint 99/100: `94.551%~99.823%`
- Sector completion/joint 99/100: `94.551%~99.823%`

Matched exact two-sided McNemar:

- Adaptive vs Full safety: discordance `1:0`, `p=1.0`
- Adaptive vs Sector completion: discordance `1:0`, `p=1.0`
- Adaptive vs Full completion: discordance 없음, `p=1.0`
- Full vs Sector joint: discordance `1:1`, `p=1.0`

따라서 Adaptive의 관측 결과는 가장 좋지만 safety/completion 우위를 통계적으로
입증한 것은 아니다. Population 100%나 formal collision freedom도 아니다.

## 8. 실패/이상 사례 포렌식

### 8.1 Map 3 run 7 Sector: 인프라 메모리 stall

Raw 결과는 207.36 s, waypoint 3/5, static collision 0, clearance +0.304 m다.
동일 run만 다음 상태를 기록했다.

- FSM/Algorithm peak PSS: 8,220/8,246.8 MiB
- End-to-end peak PSS: 8,483.7 MiB
- Host available minimum: 461.7 MiB
- Host swap peak: 2,047.99 MiB
- memory PSI avg10 some/full: 93.34/87.66%
- OOM kill과 runner retry는 없었지만, cgroup trace sampling도 138.6 s에서
  211.0 s로 건너뛸 만큼 system-wide reclaim stall이 컸다.

건강한 메모리 상태의 targeted replay는 61.20 s, 5/5 waypoint, collision 0,
clearance +0.269 m였다. Algorithm/end-to-end PSS는 3,189/3,487 MiB,
available minimum 4,577 MiB, PSI 0.18/0.18%였다. 따라서 raw 99/100은 그대로
보존하지만 원인 분류는 planner liveness가 아니라 infrastructure-contaminated
run이다. 이 outlier를 CPU 평균에서 임의로 제거하지 않았다.

### 8.2 Map 7 run 4 Full: 실제 저속 blind-footprint 접촉

이 run은 79.52 s에 완주했지만 static-PCD 접촉 1회가 있었다.

- 최초 접촉: elapsed 6.1214 s, waypoint 0
- 속도: 0.01155 m/s
- 위치: `[13.6500, 11.2499, 1.9500]`
- nearest static point distance/clearance: `0.0563/-0.1437 m`
- speed violation, OOM, retry, memory PSI: 모두 0
- 접촉 21 ms 전 `ReplanOnce/no_backup` generation 6의 짧은 tail이 commit됨
- guard는 map 42에서 `SAFE`를 반환함

Seed7 LiDAR `sensing_blind`는 0.1 m다. 실제 장애물이 0.056 m까지 들어오면 센서
blind-footprint 안이고, local ROG/CIRI에 obstacle face가 없으면 low-speed에서
최대 가중치인 nearest-face soft clearance도 비용을 만들 수 없다. 즉 이번
반례는 clearance weight가 꺼진 것이 아니라 **penalize할 관측 face가 사라진
것**이다. Soft objective는 near-field observation memory의 hard gate를 대체하지
못한다.

Targeted Full replay는 82.69 s, collision 0, clearance +0.277 m라 동일 접촉은
즉시 재현되지 않았다. 원 캠페인의 관측 빈도는 1/10이며 timing/path-dependent
반례로 보존해야 한다.

### 8.3 Map 9 run 9 Sector: live-cloud contact 오탐

`collisions=1`이지만 authoritative `safety_collisions=0`이다. Live point까지
0.188 m였으나 같은 순간 static-PCD distance/clearance는 0.294/+0.094 m이고
`live_only_contact_event_count=1`이다. 안전 실패로 세지 않는다. 이 사례는
`collisions`와 `safety_collisions`를 혼용하면 안 되는 이유다.

## 9. 연구 목표 대비 판정

1. Adaptive는 이 cohort에서 100/100 completion, 100/100 safety와 Full 대비
   13.23% algorithm CPU, 11.34% end-to-end CPU, 56.35% payload 절감을 달성했다.
2. Full은 completion 100/100이지만 실제 static contact 1회라 목표인
   `100% completion / collision 0`을 달성하지 못했다.
3. Sector는 raw completion 99/100이지만 유일한 미완주는 메모리 stall로
   오염됐다. Authoritative safety는 100/100이다. 따라서 이번 n=10만으로
   “시야 절단 때문에 Sector 안전/완주가 유의하게 나빠진다”는 기대는 재현되지
   않았다. 과거 n=3 결과와 하나의 cohort로 합치면 안 된다.
4. Adaptive의 계산량 이득은 명확하지만 안전 우위는 one-discordance이고
   McNemar p=1.0이라 아직 final claim이 아니다.

## 10. 다음 구현 방향

Full의 Map 7 반례부터 해결해야 한다.

1. 최근 1~2초 raw hit를 world frame의 bounded near-field witness로 유지하는
   shadow 계측을 먼저 추가한다. static PCD oracle은 planner 입력으로 쓰지 않는다.
2. 현재 body/짧은 tail이 최근 hit의 `robot_r` 안으로 들어가면 commit을
   hard-reject하고 certified hold/reroute로 연결한다.
3. 이미 footprint 안인 경우에는 정지 반복을 막기 위해 최근 hit와의 거리가
   단조 증가하는 bounded egress만 허용한다.
4. Map 7 Full focused n>=20으로 false reject/liveness와 접촉을 검증한 뒤,
   three-mode n=3 gate, 마지막으로 300-row n=10을 다시 수행한다.
5. 별도로 Map 3의 단발 8.2 GiB PSS 재발을 추적하고, memory PSI threshold를
   넘은 run을 자동 infrastructure retry로 분류하는 runner 정책을 추가한다.

Raw-cloud CIRI의 operational 연결은 이 작업과 분리하며 기본값 false를 유지한다.

## 11. 결과 파일과 검증

- Raw 300 rows:
  `results/final_speedgated_cgroup_3mode_seed1_10_n10_raw_20260831.csv`
- Map/mode summary:
  `results/final_speedgated_cgroup_3mode_seed1_10_n10_summary_20260831.csv`
- Targeted replays:
  `results/forensic_replay_seed{3_sector,7_full}_n1_raw_20260831.csv`
- Tests: native campaign `23 passed`, Python compile and `git diff --check` pass

Raw mirror SHA-256:
`65c73f392e39e04401c54d713c266d976077a53c3e4511103ab88e32d65057ed`.
