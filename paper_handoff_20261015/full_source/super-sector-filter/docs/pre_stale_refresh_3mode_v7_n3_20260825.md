# Adaptive pre-stale full refresh — v7, seed1-10, three-mode n=3 (2026-08-25)

## 결론

`guard true-edge` 뒤의 full refresh는 이미 stale map으로 승인되어 실행 중인 첫
brake를 바꿀 수 없었다. 이를 보완하기 위해 guard의 0.50-0.55초 stale 판정 전에
한 번의 complete scan을 보내는 `pre-stale full refresh`를 C++ native filter에
추가했다. 실행 파일 기본값은 `0`(비활성)이고 strict campaign runner만 0.25초를
사용한다.

최종 order-crossed `seed1-10 x Full/Sector/Adaptive x n=3` 90회는 모두 valid,
one attempt, raw complete였다. Full과 Adaptive는 각각 **30/30 완주, contact
0/30**이었다. fixed Sector도 30/30 완주했지만 **2/30 runs, 3 contact events**가
seed9와 seed10에서 발생했다. 따라서 이번 표본에서는 이전 Adaptive seed7
first-brake contact가 재발하지 않았고, Full/Adaptive의 관측 안전·완주 목표는
충족했다.

그러나 Adaptive 평균 mission time은 Full보다 34.75% 길었다. Full 대비
update-weighted points/update 18.90%, map total/update 23.86%, map update time
15.12%를 줄였지만, late dense maps에서 trajectory guard가 80-92% duty로 오래
열리고 version-advance ACK의 긴 꼬리가 최대 11.245초까지 생겼다. 이 결과는
안전 수정의 local regression pass이지 population 100%, flight-ready, 또는
hard real-time 보장이 아니다.

## 구현

변경 파일은 `mission_planner/Apps/native_sector_cpp.cpp`와 campaign runner다.

- 새 옵션 `--map-commit-pre-stale-full-age-s`를 추가했다. C++ 기본값은 0초다.
- Adaptive에서 마지막 map commit 수신 age가 설정값 이상이면 complete scan 한
  프레임을 publication cap과 bounded far-field filter보다 우선해 보낸다.
- `last_full_refresh_source_version`으로 동일 map version에는 한 번만 허용한다.
  map worker가 멈추면 같은 version에 full scan을 반복해서 쌓지 않는다.
- 이후 `commit_version > source_version`을 관찰하면 version-advance ACK proxy로
  기록하고 latency를 잰다. 이것은 특정 full frame의 처리 완료 token은 아니므로
  content-specific ACK 또는 formal certificate로 해석하면 안 된다.
- direct trajectory-guard true-edge refresh가 같은 version에서 먼저 실행되면
  pre-stale refresh를 중복 발행하지 않는다.
- pre-stale 기능만 켜고 기존 sector heartbeat를 꺼도 commit topic을 구독하도록
  두 옵션의 OR 조건으로 구독을 생성한다.
- frame/ACK/pending/same-version suppression/trigger age/ACK latency를 stats JSON과
  raw CSV에 추가했다.

`trajectory_guard_raw_cloud_ciri_shadow_en`은 계속 default false이며 이 변경과
무관하다. 실제 CIRI shadow 또는 authoritative brake policy를 켜지 않았다.

## seed7 threshold 선택

먼저 Adaptive seed7을 각 3회 실행했다. 둘 다 contact 0이었지만 0.35초는 실제
trigger가 평균 0.488초로 stale high-speed threshold에 너무 가까웠다. 0.25초는
full refresh가 더 많아 map total/update가 약간 늘었지만 실제 trigger와 ACK가
앞당겨지고 평균 mission time이 크게 줄어 최종 gate에 채택했다.

| configured age | completion | contact runs | mean time (s) | worst clearance (m) | pre-stale frames/run | version ACK | trigger age (s) | ACK latency (s) | map total/update (ms) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.35 s | 3/3 | 0 | 132.52 | +0.207 | 66.7 | 200/200 | 0.488 | 0.311 | 32.36 |
| 0.25 s | 3/3 | 0 | 102.68 | +0.266 | 81.7 | 244/245 | 0.403 | 0.175 | 33.84 |

0.25초 targeted gate의 마지막 pending 1건은 mission shutdown 직전 보낸 frame이다.
최종 30-run Adaptive gate에서는 pending 없이 2,369/2,369가 version advance를
관찰했다.

## 최종 실험 조건

- map: `seed1`-`seed10`
- mode: direct Full, fixed Sector, strict-burst C++ Adaptive
- repetition: map/mode당 3회, 총 90회
- order: global rotation (`Full -> Sector -> Adaptive`, 다음 run에서 회전)
- speed: v=7 m/s
- waypoint: `loop24.txt`
- timeout: 240초
- static PCD monitor 및 live-cloud contact forensics 활성
- Full config: `static_seedmaps_guard_viability_tight_v7.yaml`
- filtered config: `static_seedmaps_guard_viability_tight_v7_filtered.yaml`
- Adaptive: 5 Hz cap, 2.5초 trajectory-guard hold, far-field 6,000점 bound,
  pre-stale age 0.25초

Raw result:
`results/prestale025_order_crossed_3mode_v7_n3_raw_20260825.csv`.

## 전체 결과

`contact runs`는 `contact_event_count > 0`인 run 수다. `worst clearance`는 공통
static PCD와 0.20m body radius로 계산한 최소 여유다. compute 항목은 map update
수로 가중했다. FSM CPU는 mission time으로 가중했다.

| mode | completion | contact runs (events) | mean time (s) | worst clearance (m) | points/update | map total/update (ms) | map update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 30/30 | 0 (0) | 76.63 | +0.128 | 28,612 | 41.282 | 14.131 | 97.75 |
| fixed Sector | 30/30 | 2 (3) | 83.55 | +0.014 | 13,638 | 14.837 | 4.980 | 72.54 |
| Adaptive | 30/30 | 0 (0) | 103.26 | +0.195 | 23,204 | 31.434 | 11.994 | 62.35 |

Full 대비 fixed Sector는 points/update 52.33%, map total/update 64.06%, map update
64.76%를 줄였지만 mean mission은 9.02% 길고 두 run에서 접촉했다. Adaptive는
points/update 18.90%, map total/update 23.86%, map update 15.12%를 줄이고 이번
표본의 Sector 접촉을 회복했지만 mean mission은 34.75% 길다.

## 맵별 안전성과 시간

접촉 열은 `contact runs(events)` 형식이다.

| map | Full complete | Full contact | Full time | Full worst clr | Sector complete | Sector contact | Sector time | Sector worst clr | Adaptive complete | Adaptive contact | Adaptive time | Adaptive worst clr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed1 | 3/3 | 0(0) | 62.32 | +0.207 | 3/3 | 0(0) | 66.78 | +0.223 | 3/3 | 0(0) | 64.67 | +0.279 |
| seed2 | 3/3 | 0(0) | 59.81 | +0.243 | 3/3 | 0(0) | 57.11 | +0.289 | 3/3 | 0(0) | 60.99 | +0.222 |
| seed3 | 3/3 | 0(0) | 68.22 | +0.176 | 3/3 | 0(0) | 64.28 | +0.174 | 3/3 | 0(0) | 80.48 | +0.247 |
| seed4 | 3/3 | 0(0) | 71.55 | +0.265 | 3/3 | 0(0) | 82.68 | +0.230 | 3/3 | 0(0) | 89.42 | +0.229 |
| seed5 | 3/3 | 0(0) | 73.68 | +0.128 | 3/3 | 0(0) | 75.58 | +0.135 | 3/3 | 0(0) | 96.62 | +0.258 |
| seed6 | 3/3 | 0(0) | 85.78 | +0.212 | 3/3 | 0(0) | 92.94 | +0.189 | 3/3 | 0(0) | 119.36 | +0.225 |
| seed7 | 3/3 | 0(0) | 77.52 | +0.261 | 3/3 | 0(0) | 90.42 | +0.173 | 3/3 | 0(0) | 133.28 | +0.202 |
| seed8 | 3/3 | 0(0) | 86.95 | +0.214 | 3/3 | 0(0) | 83.30 | +0.175 | 3/3 | 0(0) | 113.02 | +0.195 |
| seed9 | 3/3 | 0(0) | 94.19 | +0.185 | 3/3 | 1(1) | 108.44 | +0.014 | 3/3 | 0(0) | 132.35 | +0.221 |
| seed10 | 3/3 | 0(0) | 86.34 | +0.202 | 3/3 | 1(2) | 113.95 | +0.045 | 3/3 | 0(0) | 142.44 | +0.256 |

## 맵별 연산량

각 모드 셀은 update-weighted `points/update`와 `map total/update`다. 마지막 두
열은 같은 맵의 Adaptive가 Full보다 줄인 비율이다.

| map | Full points | Full ms | Sector points | Sector ms | Adaptive points | Adaptive ms | Adaptive point reduction | Adaptive ms reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed1 | 15,517 | 34.62 | 6,714 | 12.46 | 12,366 | 23.84 | 20.31% | 31.14% |
| seed2 | 15,764 | 35.22 | 6,660 | 12.82 | 11,864 | 24.06 | 24.74% | 31.69% |
| seed3 | 22,628 | 40.98 | 10,286 | 15.20 | 18,769 | 32.95 | 17.05% | 19.58% |
| seed4 | 24,115 | 40.00 | 11,516 | 14.53 | 19,301 | 30.64 | 19.96% | 23.41% |
| seed5 | 27,508 | 45.71 | 12,589 | 16.21 | 21,093 | 36.39 | 23.32% | 20.40% |
| seed6 | 29,118 | 43.00 | 14,444 | 15.17 | 24,318 | 34.04 | 16.48% | 20.84% |
| seed7 | 36,620 | 44.71 | 17,542 | 15.90 | 30,243 | 33.91 | 17.42% | 24.15% |
| seed8 | 33,791 | 46.73 | 16,226 | 16.64 | 25,897 | 34.86 | 23.36% | 25.41% |
| seed9 | 42,366 | 40.94 | 22,921 | 15.43 | 34,084 | 31.65 | 19.55% | 22.70% |
| seed10 | 40,675 | 42.30 | 21,574 | 15.21 | 32,817 | 33.10 | 19.32% | 21.77% |

## Adaptive 활성화와 pre-stale telemetry

`effective open`은 최종 Adaptive full-open output의 실제 false-to-true edge다.
괄호는 run당 평균이다. duty는 mission-time weighted 값이다.

| map | effective open total (mean) | guard episodes total (mean) | full-open duty | guard duty | pre-stale frames total (mean) | version ACK | trigger age (s) | ACK latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed1 | 59 (19.7) | 16 (5.3) | 48.5% | 33.8% | 112 (37.3) | 112 | 0.325 | 0.082 |
| seed2 | 56 (18.7) | 14 (4.7) | 46.3% | 31.4% | 114 (38.0) | 114 | 0.338 | 0.092 |
| seed3 | 31 (10.3) | 21 (7.0) | 80.5% | 74.8% | 189 (63.0) | 189 | 0.343 | 0.141 |
| seed4 | 32 (10.7) | 21 (7.0) | 79.3% | 74.8% | 200 (66.7) | 200 | 0.356 | 0.204 |
| seed5 | 25 (8.3) | 18 (6.0) | 83.6% | 79.1% | 217 (72.3) | 217 | 0.400 | 0.145 |
| seed6 | 19 (6.3) | 16 (5.3) | 86.7% | 83.4% | 251 (83.7) | 251 | 0.398 | 0.294 |
| seed7 | 17 (5.7) | 12 (4.0) | 88.7% | 86.2% | 308 (102.7) | 308 | 0.417 | 0.256 |
| seed8 | 24 (8.0) | 13 (4.3) | 86.2% | 81.5% | 261 (87.0) | 261 | 0.410 | 0.237 |
| seed9 | 19 (6.3) | 15 (5.0) | 90.4% | 88.5% | 360 (120.0) | 360 | 0.387 | 0.225 |
| seed10 | 15 (5.0) | 13 (4.3) | 93.7% | 92.2% | 357 (119.0) | 357 | 0.400 | 0.211 |

전체 Adaptive에서 effective open은 297회, direct guard episode는 159회였다.
pre-stale frame은 2,369회이고 version advance도 2,369회 관측되어 종료 시 pending은
0이었다. frame-weighted trigger age는 0.386초, ACK latency는 0.207초였다. 다만
trigger max는 3.150초, ACK latency max는 11.245초였다. input callback이 없거나
map worker가 오래 응답하지 않는 구간에서는 configured 0.25초가 wall-clock
deadline을 보장하지 않는다.

## Sector contact forensics

두 contact run 모두 정상 first attempt였고 infrastructure retry와 관계없다.

- seed9 run2 Sector: mission은 114.33초에 완주했다. 103.4479초에 live point
  distance 0.18412m, 위치 `(12.915, -17.528, 0.975)`, speed 6.08093m/s에서
  1회 접촉했다. static minimum distance는 0.214m, body clearance +0.014m다.
- seed10 run2 Sector: mission은 119.46초에 완주했다. 103.8426초와
  103.8838초에 distance 0.19238/0.18471m, speed 6.98111/6.90252m/s로 두 번
  접촉했다. 첫 위치는 `(19.498, -18.735, 1.877)`이고 static minimum distance는
  0.245m, body clearance +0.045m다.

동일 paired map/run의 Full과 Adaptive는 모두 contact 0이었다. 이것은 서술적으로
연구 목표에 맞지만 discordant pair가 두 개뿐이라 검정력이 낮다. 이번 문서에서는
exact McNemar 검정을 수행하지 않았으며 안전 차이는 기술 통계로만 해석한다.

## 메모리와 infrastructure

- 90/90 one attempt, retry 0, OOM delta 0
- FSM swap 0, memory PSI some/full max 0
- peak FSM RSS: Full 3,468.35 MiB, Sector 3,334.83 MiB, Adaptive 3,482.55 MiB
- 전체 최저 host available memory: 3,050.04 MiB
- host swap used는 약 2,048 MiB, cgroup swap peak는 약 1,557 MiB로 캠페인 전부터
  차 있던 값이 유지됐다. FSM 자체 swap, PSI, OOM, retry가 없으므로 이전의
  unbounded planner log growth가 재발했다고 보지 않는다.

campaign sequence와 host available memory의 상관은 음수였지만 FSM RSS의 sequence
상관은 0.153에 불과했고 후반에도 peak가 누적 증가하지 않았다. available 감소는
page cache와 다른 host workload를 포함하므로 이 표만으로 leak을 주장할 수 없다.

## 판단과 다음 구현 방향

이번 변경은 관측된 first stale-map brake 접촉을 막고 Full/Adaptive 30/30 contact
0을 만들었다. 따라서 안전 회귀 패치로는 유지할 가치가 있다. 반면 pre-stale full
refresh를 한 version마다 허용하면서 late seeds의 guard duty가 80-92%가 되었고,
Adaptive mission time이 Full보다 34.75% 길어졌다. threshold를 더 낮추거나 cap을
올리는 단순 튜닝은 full-like workload를 더 늘릴 가능성이 크다.

다음 단계는 다음 순서가 적절하다.

1. version number 증가를 특정 refresh request ID와 연결하는 content-specific ACK
   또는 generation token을 만든다.
2. ACK가 짧은 SLA 안에 오면 fresh-map replan 성공을 확인하고 guard를 조기
   종료한다. 단순 hold 축소는 금지한다.
3. ACK가 장기 지연되면 같은 full frame을 flood하지 않고 certified stop 상태를
   유지한 뒤 topology 변경 reroute를 한 번 수행한다.
4. seed6-10에서 ACK-latency tail과 guard duty가 실제로 줄었는지 targeted gate를
   먼저 하고, 이후 동일 order-crossed three-mode n=3 이상을 반복한다.

현재 결과는 local simulator sample의 30/30일 뿐 population 100% 보장이 아니다.
raw-cloud CIRI shadow는 계속 default false/non-authoritative로 유지한다.
