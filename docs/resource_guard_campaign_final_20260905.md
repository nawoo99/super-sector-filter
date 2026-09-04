# Prospective resource-gated 10-map campaign final report (2026-09-05)

## 1. 결론

고정된 v7/45° profile과 동일한 resource gate를 첫 attempt부터 적용해
Map 1--10 × Full/Sector/Adaptive × 10회, 총 300개 고유 run을 완료했다.
누락·중복·예상 밖 key는 없으며 모든 run은 첫 attempt에 끝났다. Resource abort,
infrastructure retry, OOM kill, static-PCD 충돌은 모두 0이다.

- Full: 100/100 완주, 100/100 protocol-valid, 충돌 0.
- Adaptive: 100/100 완주, 100/100 protocol-valid, 충돌 0.
- Sector: 100/100 완주, 충돌 0이지만 99/100 protocol-valid. Map 9 run 2에서
  v7 속도 제한을 한 번 위반했다.
- 따라서 사용자가 정한 Full의 관측 목표와 Adaptive의 관측 목표는 이번 고정
  campaign에서 달성됐다. 그러나 이는 미관측 모집단에서의 100% 보장은 아니다.
- Sector가 완주율 또는 충돌률에서 열화되지는 않았으므로 이 두 endpoint에서
  Adaptive가 Sector를 개선했다는 주장은 이번 정적 맵으로 식별되지 않는다.
  대신 Sector의 속도 계약 실패 1건을 Adaptive가 보이지 않았다는 차이는 남는다.
- 엄격한 campaign validator는 이 Sector 품질 실패를 보존해 전체 `FAIL`을
  반환한다. 성공한 run으로 바꾸기 위한 재시험은 하지 않았다.

## 2. 시험 프로토콜

- 환경: 동일 static seed map 1--10, `loop24.txt`, 기준 속도 7 m/s.
- Full: raw cloud in-process 경로.
- Sector/Adaptive: C++ frontend, sector half-angle 45°.
- 실행 순서: 맵/run마다 모드 순서를 회전해 시간 순서 편향을 줄였다.
- preflight: `MemAvailable >= 8192 MiB`, PSI some/full avg10 `<= 10/5`가
  5초 연속 유지돼야 launch.
- runtime: `MemAvailable < 2048 MiB` 또는 PSI 초과가 5초 지속되면 해당 attempt를
  infrastructure failure로 중단·보존·재시도.
- timeout: preflight 600초. 캠페인 실행 시간은 2026-09-04 19:07부터
  2026-09-05 01:45:59 KST까지 약 398.8분이었다.

먼저 같은 gate로 Map 10 3모드 n=10을 독립 실행했다. 세 모드 모두 10/10
완주·유효·무충돌이었다. 그 gate를 통과한 뒤 10맵 300-run 본 캠페인을 새로
수집했다.

## 3. 맵별 안전·완주·시간·Adaptive 전환

`완주/유효/충돌`은 각 모드의 10회 기준이다. `clr<.20`은 static-PCD 표면
clearance가 0.20 m 미만인 run 수이며 충돌 수가 아니다. `open`은 Adaptive가
실제로 Full sensing으로 열린 횟수의 합이다.

| Map | Mode | 완주/유효/충돌 | 평균시간 (s) | 최저 clearance (m) | clr<.20 | Adaptive open |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Full | 10/10/0 | 59.003 | 0.207 | 0 | 0 |
| 1 | Sector | 10/10/0 | 59.087 | 0.213 | 0 | 0 |
| 1 | Adaptive | 10/10/0 | 58.390 | 0.192 | 1 | 194 |
| 2 | Full | 10/10/0 | 56.690 | 0.235 | 0 | 0 |
| 2 | Sector | 10/10/0 | 54.057 | 0.193 | 1 | 0 |
| 2 | Adaptive | 10/10/0 | 54.267 | 0.185 | 1 | 169 |
| 3 | Full | 10/10/0 | 59.769 | 0.228 | 0 | 0 |
| 3 | Sector | 10/10/0 | 58.453 | 0.210 | 0 | 0 |
| 3 | Adaptive | 10/10/0 | 57.270 | 0.215 | 0 | 235 |
| 4 | Full | 10/10/0 | 63.521 | 0.173 | 1 | 0 |
| 4 | Sector | 10/10/0 | 62.899 | 0.126 | 2 | 0 |
| 4 | Adaptive | 10/10/0 | 64.606 | 0.124 | 1 | 159 |
| 5 | Full | 10/10/0 | 60.491 | 0.192 | 1 | 0 |
| 5 | Sector | 10/10/0 | 58.491 | 0.222 | 0 | 0 |
| 5 | Adaptive | 10/10/0 | 59.748 | 0.201 | 0 | 190 |
| 6 | Full | 10/10/0 | 65.580 | 0.204 | 0 | 0 |
| 6 | Sector | 10/10/0 | 63.952 | 0.189 | 1 | 0 |
| 6 | Adaptive | 10/10/0 | 63.385 | 0.199 | 1 | 193 |
| 7 | Full | 10/10/0 | 68.629 | 0.194 | 1 | 0 |
| 7 | Sector | 10/10/0 | 68.383 | 0.214 | 0 | 0 |
| 7 | Adaptive | 10/10/0 | 69.070 | 0.217 | 0 | 211 |
| 8 | Full | 10/10/0 | 64.105 | 0.194 | 1 | 0 |
| 8 | Sector | 10/10/0 | 62.264 | 0.219 | 0 | 0 |
| 8 | Adaptive | 10/10/0 | 61.368 | 0.204 | 0 | 185 |
| 9 | Full | 10/10/0 | 81.814 | 0.184 | 1 | 0 |
| 9 | Sector | 10/9/0 | 73.872 | 0.197 | 1 | 0 |
| 9 | Adaptive | 10/10/0 | 72.085 | 0.195 | 1 | 158 |
| 10 | Full | 10/10/0 | 79.043 | 0.215 | 0 | 0 |
| 10 | Sector | 10/10/0 | 76.554 | 0.143 | 2 | 0 |
| 10 | Adaptive | 10/10/0 | 77.071 | 0.189 | 1 | 210 |

Adaptive effective-open은 총 1,904회, 평균 19.04회/run이다. 0.20 m 미만
surface-clearance run은 Full/Sector/Adaptive 5/7/6건이고 각 최저값은
0.173/0.126/0.124 m다. 세 모드 모두 접촉은 없지만, 별도의 0.20 m 추가 여유
계약은 어느 모드도 전 run에서 만족하지 않았다. 또한 이 값은 static PCD와 현재
robot-radius 정의로 계산한 실험 지표이지 보편적 기체 clearance 증명은 아니다.

## 4. 연산량과 대역폭

| 지표 | Full | Sector | Adaptive | Adaptive vs Full |
|---|---:|---:|---:|---:|
| 평균 임무 시간 (s) | 65.865 | 63.801 | 63.726 | 3.247% 감소 |
| map compute (ms/frame) | 37.112 | 10.362 | 22.787 | 38.599% 감소 |
| 공통 E2E 평균 CPU (cores) | 1.554 | 1.276 | 1.341 | 13.709% 감소 |
| 공통 E2E CPU (core·s/run) | 105.065 | 83.477 | 87.652 | 16.574% 감소 |
| 공통 E2E p95 CPU (cores) | 1.791 | 1.464 | 1.554 | 13.250% 감소 |
| 공통 E2E peak PSS (MiB) | 3472.33 | 3439.53 | 3483.71 | 0.328% 증가 |
| planner logical ingress (MiB/s) | 9.458 | 2.758 | 2.305 | 75.632% 감소 |
| external DDS algorithm payload (MiB/s) | N/A | 2.758 | 2.308 | 비교 불가 |

Full과 Adaptive는 모든 run이 protocol-valid라 위 `Adaptive vs Full` 감소율은
공식 비교로 사용할 수 있다. 반면 Sector가 포함된 pooled reduction은 Map 9의
invalid row가 섞이므로 validator/summarizer가 비교 불가로 출력한다. 모든 100개
행을 단순 기술 통계로만 보면 Adaptive는 Sector보다 map compute와 E2E CPU를 더
쓰고 planner ingress는 덜 쓰지만, 이를 공식 reduction claim으로 쓰지 않는다.

CPU 범위에도 주의가 필요하다. `algorithm_cpu_*`는 Full이 simulator+planner,
Sector/Adaptive가 planner-only이므로 Full과 filtered mode 사이 비교가 불가능하다.
위 CPU 주장은 세 모드에 공통인 parent end-to-end cgroup
`simulator+frontend+planner+mission`만 사용했다. Full은 raw cloud가 in-process라
external DDS가 정의되지 않으므로 DDS 감소율은 Sector↔Adaptive가 모두 유효한
cohort에서만 비교할 수 있다. Logical planner ingress는 Full과도 비교 가능하다.

## 5. Map 9 Sector 속도 실패 분석

문제 행은 Map 9 run 2 Sector다. 임무는 5/5 waypoint, 76.60초, static-PCD
clearance 0.282 m, 충돌 0으로 끝났고 자원도 유효했다. 그러나 command/odom 최대
속도가 10.95563 m/s로 v7+0.01 허용치를 넘었다. 초과 sample은 command 33개와
odom 33개, 총 66개였고 첫 초과는 20.778471초, trajectory id 48,
trajectory flag 3(guard emergency brake)였다.

로그에서 확인한 사건 순서는 다음과 같다.

1. `1788535275.415668`과 `.416040`에 brake 생성이 거절됐다. 기록된 초기 속도는
   0이고 첫 시도는 최근 command를 사용했다.
2. 약 103 ms 뒤 `.519595` retry는 위치 차분으로 계산한 `odom_motion=10.960`
   m/s를 초기 속도로 받아들였다. 최근 command와의 속도 오차는 6.613 m/s였다.
3. brake 경로 자체는 `SAFE`였고, 구현은 실제 외력으로 이미 과속했을 가능성을
   허용하려고 brake velocity limit를 `max(configured v7, initial speed)`로
   확장한다. 따라서 10.960 m/s brake가 인증·발행됐다.
4. 두 거절 사이 `cmd_age`가 0.087초에서 다음 retry의 0.090초로 다시 젊어졌다.
   중간에 ordinary command가 실제로 발행됐다는 증거다. 현재
   `pubCmdTimerCallback`은 active certified brake가 없으면 `FOLLOW_TRAJ`뿐 아니라
   `EMER_STOP`에서도 기존 인증 trajectory command를 발행할 수 있다.
5. PerfectDrone은 command callback에서 position/velocity를 그대로 simulator
   state에 대입한다. 이 시점의 trajectory generation 전환에 따른 position jump를
   odom 위치 차분기가 실제 운동으로 오인했고, 과대 속도와 확장된 brake cap이
   결합된 것으로 해석된다.

따라서 직접 원인은 Sector 필터 자체의 45° 절단이 아니라 guard fail-closed 경로의
상태 모순이다. `mainFsmTimerCallback`은 guard-enabled `EMER_STOP`에서 재계획을
막지만 `pubCmdTimerCallback`은 ordinary command를 계속 허용한다. Full/Adaptive
로그에도 7 m/s보다 큰 position-difference `odom_motion` spike가 있었으나 후보
경로가 거절돼 실제 과속 command로 나타나지 않은 사례가 있다. 즉 잠재 결함은
세 모드 공통이고 이번에는 Map 9 Sector에서만 발현됐다.

다음 코드 단계는 별도의 변경·회귀시험으로 수행한다.

1. guard-enabled `EMER_STOP`이고 active certified brake가 없을 때 ordinary
   flag 1/2 command 발행을 차단한다. Guard-disabled legacy 동작은 유지한다.
2. 위치 차분 속도는 command generation/position 연속성이 확인될 때만 사용하고,
   가능하면 직접 odom twist를 우선한다. 불연속 jump를 실제 외력 과속으로
   받아들여 brake cap을 키우지 않는다.
3. `brake reject -> EMER_STOP -> retry` 회귀시험에서 ordinary command 0개와,
   독립적으로 검증된 실제 과속이 없는 한 brake 최대속도 `<=7.01 m/s`를 단언한다.
4. 기존 로그에서 spike가 있었던 Map 5/6/7/8/9/10을 표적 재현한 뒤 Map 9
   Sector/Adaptive gate와 전체 frozen campaign 순으로 재검증한다.

## 6. 자원·swap audit

300개 run 모두 첫 attempt였고 resource abort/retry/OOM은 0이다. 정상 preflight
대기는 약 5.006초였다. Map 2 run 5 Adaptive만 host가 8 GiB 안정 조건을 회복할
때까지 113.144초 기다린 후 launch됐고 정상 완료했다. 이 대기 자체가 gate가
저자원 run 수집을 막았다는 증거다.

후반 Map 10 run 7 Adaptive에서 system swap이 99.75 MiB에서 22.954초에
444.75 MiB로 뛰고 53.366초에 504.75 MiB까지 증가했다. 그러나 해당 run의
campaign cgroup swap과 FSM swap은 전 구간 0이고, system available 최저는
4085.1 MiB, PSI some/full 최대는 0.18/0.18이었다. 따라서 약 405 MiB의 증가는
SUPER campaign cgroup 밖의 background page가 swap된 host-level 사건이다.
Planner failure, abort, retry 또는 OOM으로 이어지지 않았고 이후 available memory도
5 GiB 이상으로 회복됐다. 이번 gate는 실제 pressure 없이 남아 있는 swap 사용량을
곧바로 실패로 취급하지 않는다. 다만 논문 재현성에는 dedicated host 또는 외부
프로세스 격리를 명시하는 편이 안전하다.

## 7. 통계적 해석과 남은 한계

- Full/Adaptive의 100/100은 관측 성공률이다. 100/100에 대한 exact two-sided
  95% 성공률 하한은 약 96.38%이고, 맵별 10/10 하한은 약 69.15%다.
- 이 campaign에는 새 맵 일반화가 없으며 현재 고정 10맵/profile에 대한 결과다.
- 완주/충돌 endpoint에서 모드 간 discordant pair가 없어 성공률 우위를 검정하지
  않았다. McNemar 검정도 수행하지 않았다.
- Sector의 한 속도-invalid run 때문에 전체 strict gate는 실패다. 반면 Full과
  Adaptive 사이의 compute/ingress 결과는 양쪽 200개 row가 모두 protocol-valid다.
- 충돌 0과 0.20 m surface-margin contract는 다른 주장이다. 이번 결과는 전자는
  관측했지만 후자는 달성하지 못했다.

## 8. 보존 자료

- raw: `results/allmaps_resource_guard_prospective_three_mode_n10_raw_20260904.csv`
- map/mode summary: `results/allmaps_resource_guard_prospective_three_mode_n10_summary.csv`
- scope-aware reductions: `results/allmaps_resource_guard_prospective_three_mode_n10_reductions.csv`
- strict validation: `results/allmaps_resource_guard_prospective_three_mode_n10_validation.json`
- Map 10 gate: `results/map10_resource_guard_prospective_three_mode_n10_`
  `{raw_20260904,summary,reductions,validation}`
- 상세 attempt artifact는 로컬
  `results/allmaps_resource_guard_prospective_three_mode_n10_artifacts_20260904/`에
  보존하되 457 MiB 전체를 Git에는 올리지 않는다.
