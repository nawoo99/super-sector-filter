# 원기둥 맵 전용 탐색 — 2026-09-14

> 2026-09-15 00:07 KST checkpoint: 7개 후보의 비행 17회 완료. 비교 가능한
> 5개 후보는 모든 모드가 완주/접촉 0이며, ring 2개는 Full timeout으로
> 탈락했다. **사용자가 원한 접촉률/완주율 우위는 아직 달성하지 못했다.**
> 다만 Sector의 moving-brake rejection 뒤 perfect-tracking 위치 고정이
> 안전 지표를 가리는 구체적인 기록을 찾았다. 아래 §결과/검증 공백을 우선
> 읽을 것. 런타임 변경이나 대규모 추가 캠페인을 자동으로 진행하지 않는다.

## 목적과 동결 범위

사용자는 planner/guard/Adaptive 알고리즘을 수정하지 않고 원기둥의 위치,
배열, 개수, 반경, 높이만 바꾸는 반복 실험을 요청했다. 이 기록은 **개발용
탐색**이다. 결과를 본 뒤 후보를 선택하므로 여기서 얻은 차이를 독립 검증이나
population-level 안전 보장으로 주장하지 않는다. 모든 실패 후보와 실행을
남기며, 후보 이름이나 이미 실행한 행을 덮어쓰지 않는다.

- 속도 상한 7 m/s, loop24, 180초 제한은 세 모드에 동일하게 적용한다.
- Fixed Sector ±45°, C++ frontend, strict-burst 및 기존 Adaptive 설정 유지.
- Full: `static_seedmaps_guard_viability_tight_v7.yaml`.
- Sector: `static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml`.
- Adaptive: `static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml`.
- Adaptive future risk 5 Hz, current-body clearance 0.20 m / horizon 0.15 s /
  odometry age 0.20 s. 나머지는 기존 campaign 기본값이다.
- LiDAR 10 Hz, 기존 render/downsample 설정, sensor dropout/delay 없음.
- 높이 3 m의 정적 원기둥만 사용. 현재 후보는 300개이며 구조물 외 배경은
  개발용 seed5에서 시작한다. 이 seed는 hold-out이 아니다.
- 실행은 한 번씩, 자동 retry 없음. Full의 유효한 접촉 없는 완주를 먼저
  확인해야 Sector/Adaptive로 넘어간다. 시간 제한 실패도 버리지 않는다.
- 코드/설정/바이너리 SHA-256을 후보 manifest에 저장하고 실행 전후 비교한다.
  원본 SUPER에 push하지 않는다.

## 이전 결과의 해석 정정

v1 `stress_cyl_r1..r5`는 보존한다. v1의 audit radius 1.5 m는 실제 개별
원기둥이 아니라 여러 원기둥을 둘러싼 proxy였다. 따라서 그 원판에 대한
음수 trajectory clearance를 실제 원기둥과의 trajectory 교차로 해석하면
안 된다. 실제 비행의 static-PCD 접촉 0과 Full 완주 3/5라는 결과는 별개로
유효하다. 동일 raw point replay의 synthetic trajectory 검증 역시 실제
closed-loop 궤적의 성공 증거가 아니다.

반경 증가와 scan point load 증가는 함께 관측됐지만 load만이 Full 실패의
원인이라고 분리 검증하지 않았다. 기존 배너의 인과적 표현은 과했다.
LiDAR point budget을 정규화하는 것은 이번 map-only 요청에 맞지 않으므로
센서 설정은 바꾸지 않는다. 모드 비교는 반드시 같은 맵 안에서 한다.

## 후보와 검사

1. `cyl2_a01`: 기존 corner 구조에서 진입 대각선을 막던 inner row 동쪽 연장을
   제거. 원기둥 300개, 반경 0.4 m. 진입 analytic body clearance 0.708 m,
   북쪽 bypass 0.350 m. Full/Sector/Adaptive 모두 접촉 없이 완주했으므로
   안전 완주 차이를 내는 후보는 아니다.
2. `cyl2_b01`: 대각선 진입로에 두 원기둥열과 반경 1.5 m 원기둥 3개를
   교대로 배치한 슬라럼. 배경/열 반경 0.4 m. analytic route clearance 0.787 m.
3. `cyl2_b02`: 같은 슬라럼 계열에서 큰 원기둥 반경 2.0 m, 검사용 통과선의
   좌우 offset 2.2 m. analytic route clearance 0.461 m.

초기 geometry gate는 실제 원기둥에 대한 선분 거리로 진입, 우회, 남은
loop를 모두 검사한다. 이것은 기하학적 경로 존재 검사이며 SUPER의 동적
실행 가능성 증명이 아니다. 실제 Full 비행 gate가 추가로 필요하다.
b01 이후의 읽기 전용 trajectory audit는 **실제로 존재하는 원기둥 하나**의
좌표/반경을 사용한다. 이 audit가 다른 모든 원기둥을 커버한다고 주장하지
않는다. 전체 실제 접촉은 기존 static-PCD oracle로 평가한다.

## 실행 및 산출물

```bash
cd /root/super-sector-filter
PYTHONNOUSERSITE=1 python3 scripts/native_campaign/cylinder_map_search.py create cyl2_NEW --layout slalom
PYTHONNOUSERSITE=1 python3 scripts/native_campaign/cylinder_map_search.py fly cyl2_NEW --full-gate
PYTHONNOUSERSITE=1 python3 scripts/native_campaign/analyze_cylinder_map_search.py
```

`PYTHONNOUSERSITE=1`은 사용자 NumPy 2와 시스템 matplotlib/ROS NumPy 1 ABI
충돌을 피한다. 설치된 패키지나 planner를 바꾸지는 않았다. 최초 a01 생성의
도식 출력만 이 충돌로 실패했고, 이미 생성된 동일 맵을 유지한 채 시스템
패키지로 도식만 출력했다. flight 결과를 재시도한 것이 아니다.

원본 기록: `results/cylinder_map_search_20260914/<candidate>/`의 `manifest.json`,
`cylinders.csv`, `layout.png`, `raw.csv`, `artifacts/`. 모음 표와 현 상태는
`summary.csv`, `decisions.json`에 있다. 집계는 실패를 포함하며 검정 p값은
산출하지 않는다. CPU 비교는 simulator/frontend/planner를 포괄하는 동일
범위의 end-to-end core equivalent와 core-seconds를 사용한다. planner
ingress는 논리적 입력 payload이며 물리 네트워크 대역폭과 구분한다.

## 후속 기준

개발 후보에서 Full/Adaptive 안전 완주 및 Sector 실패가 관측되면, 이름과
맵을 동결하고 같은 조건으로 새로운 반복 비행을 한다. 반복 결과에서도
차이가 남는지 확인한 뒤 독립 배치에 대한 검증 계획을 세운다. 한 번 나온
유리한 결과만 골라 최종 맵 다섯 개의 성능이라고 발표하지 않는다.

## 2026-09-15 결과

아래는 모두 first-attempt n=1이고 자동 retry 0, 기존 run/resource/speed
gate 유효다. **17개 모든 행의 static-PCD 접촉은 0**이다. 이 quality gate는
동역학적 제동 성공까지 검증하는 gate는 아니다.

| 후보 | 원기둥 구조 | Full | Sector | Adaptive | Adaptive CPU 감소 | Adaptive 입력량 감소 |
|---|---|---:|---:|---:|---:|---:|
| cyl2_a01 | 진입로 개방 corner | 완주 50.72 s | 완주 58.91 s | 완주 52.07 s | 12.27% | 82.88% |
| cyl2_b01 | 1.5 m 반경 슬라럼 | 완주 54.78 s | 완주 52.57 s | 완주 55.19 s | 19.63% | 86.56% |
| cyl2_b02 | 2.0 m 반경 슬라럼 | 완주 52.43 s | 완주 50.71 s | 완주 52.82 s | 13.25% | 83.51% |
| cyl2_c01 | b01 + 작은 side post | 완주 52.22 s | 완주 52.73 s | 완주 52.64 s | 19.03% | 81.68% |
| cyl2_a03 | 큰 원기둥 + 뒤쪽 작은 원기둥 | 완주 51.28 s | 완주 53.91 s | 완주 53.03 s | 15.29% | 83.70% |
| cyl2_d01 | 반경 4.5 m 원형 배열, 후방 출구 | 실패 180.00 s, WP 0/5 | 미실행 | 미실행 | — | — |
| cyl2_d02 | 반경 3 m 원형 배열, NW 출구 | 실패 180.01 s, WP 4/5 | 미실행 | 미실행 | — | — |

CPU는 end-to-end 평균 core equivalent, 입력량은 planner의 논리적 ingress
payload MiB/s다. 감소율은 각 맵의 Full 대비이며 n=1의 기술통계일 뿐이다.
가장 유리한 맵을 골라 전체 효과 크기로 제시하지 않는다. 센서에서 들어온
raw cloud 전체를 Adaptive가 읽는 비용은 사라지지 않으며, Full intra-process
경로의 실제 DDS cloud payload는 0이므로 이 열을 네트워크 절감률로 부르면
안 된다. Adaptive Full-open은 순서대로 22/23/23/24/23회였다.

d01은 `(2.537,2.537)` 부근에서 출발 출구를 찾지 못했고 0.1초 A* timeout
1,711회였다. d02는 처음 출구는 통과하고 네 외곽 waypoint까지 갔지만,
원점으로 돌아오는 단계에서 `(3.209,-2.266)` 부근에 멈춰 A* timeout
1,173회였다. 두 행의 host PSI some max는 0.0이고 가용 메모리 최저도
각각 4528.7/4508.9 MiB였다. 이번 실패를 메모리 부족으로 분류하지 않는다.
경로의 기하학적 존재와 현재 planner의 제한 시간 내 검색 가능성은 다르다.

`cyl2_a02`와 `cyl2_a04`는 생성/기하 검사만 완료했고 비행하지 않았다.
prepared map을 성공 결과로 포함하지 않는다. c01의 post 좌표는 b01 Sector
주행을 관찰한 뒤 선택했으므로 명백한 개발용 선택이다.

비행 전 screening: b01의 최초 rail 끝점 29 m는 outgoing route clearance가
0.207 m여서 27 m로 줄인 뒤 파일을 생성했다. a03의 analytic bypass y=25.3은
clearance 0.2 m였고, 같은 장애물에 대해 y=25.5의 검사 경로를 사용했다.
이것은 runtime waypoint 변경이 아니며, flight retry도 아니다. a01의
0.34999999999999926 계산값은 0.35 m 경계의 부동소수점 tolerance로 처리했다.

## 발견한 검증 공백: 명령 중단이 실제 제동을 대신하는 경우

`cyl2_a03_run1_sector.attempt1.stack.log`의 구체적 순서:

1. epoch 1789397757.2286: `replan_post_uncertified`, speed0=6.815 m/s,
   `TRAJ_GUARD_BRAKE_REJECTED`, `no brake command published`.
2. 약 0.11초 뒤: pose difference speed=0.000 m/s인데 odometry twist는
   6.815 m/s가 남아 있다. 새 brake command는 여전히 발행되지 않았다.
3. 약 0.44초 뒤: 정지한 위치를 기준으로 stationary hold가 인증된다.
4. 저장된 heading trace에서도 `(22.408,23.433)` 위치가 반복되며 twist-derived
   speed는 한동안 약 6.808 m/s다. 이후 우회하여 완주한다.

이 현상은 단순한 추측이 아니라 코드의 실행 방식과 일치한다.

- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`: 제동 생성 실패 시
  EMER_STOP으로 바꾸며, brake가 없을 때 ordinary command publication을
  차단한다(약 2707, 3468, 3529행).
- `mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp`:
  `cmdCallback`은 `updateFlatness`로 받은 position/velocity를 직접 대입한다
  (1045, 1143행). `publishOdom`은 그 상태를 다시 내보낸다(1073행).
  명령이 안 올 때 관성으로 위치를 적분하는 dynamics 모델이 아니다.

따라서 이 경우의 접촉 0은 **실행 가능한 제동 궤적으로 회피에 성공했다는
증거가 아니다**. 실제 동역학에서 충돌이 반드시 일어났다는 주장도 하지
않는다. 판단하려면 별도 dynamics 또는 검증된 command-loss 모델이 필요하다.
원래 데이터의 접촉 숫자를 조작하거나 실제 충돌로 재라벨링하지 않는다.

읽기 전용 `audit_cylinder_search_stops.py` 집계:

| 비교 후보 | Full 이동 중 brake-rejection 묶음 | Sector | Adaptive | Sector pose 고정/twist 잔류 로그 행 |
|---|---:|---:|---:|---:|
| a01 | 0 | 3 | 0 | 8 |
| a03 | 0 | 1 | 0 | 3 |
| b01 | 0 | 0 | 0 | 0 |
| b02 | 0 | 0 | 0 | 0 |
| c01 | 0 | 0 | 0 | 0 |

묶음은 speed0 > 0.5 m/s인 reject 로그를 인접 간격 0.75초 기준으로 합친
diagnostic이다. 정확한 물리 사고 횟수나 독립 표본 수가 아니다. 오른쪽
열도 retry 로그 행 수이지 11회의 별도 freeze 사고라는 뜻이 아니다.
정지 상태에서의 hold rejection은 별도로 제외했다. 원본과 시각은
`results/cylinder_map_search_20260914/stop_audit.json`에 보존했다.

현재 접촉/완주 기준으로 우위는 미달성이다. 동시에 이 새로운 진단 신호는
Sector에서만 2개 맵에 나타났고, 같은 5개 맵의 Full/Adaptive에는 이동 중
rejection이 없었다. 사후 발견한 n=1 신호이므로 유의성이나 일반화는 주장하지
않는다. 또한 한 원기둥에 대한 exact-risk audit가 항상 전체 위험을 커버하는
것은 아니다(a03의 해당 witness와 matched fresh OCCUPIED는 0).

## 저장 상태 및 다음 결정

Planner/guard/filter 코드, 세 mode profile, sensor 설정은 변경하지 않았다.
모든 후보의 runtime policy SHA 집계도 동일하다. 이번에 추가한 것은 맵
생성/실행 helper, 읽기 전용 분석기, 테스트, 원기둥 자산과 기록뿐이다.
275개 동결 파일의 해시, 9개 후보 manifest, 17개 고유 실행 행 및 runtime/
mirror PCD·YAML 일치를 재확인했다. 관련 pytest 14개가 통과했다. 검증 요약은
`verification.json`에 있다. 생성기는 탐색 중 확장됐으므로 재비행할 때는
최종 생성기의 default로 과거 후보를 다시 만들지 말고, manifest 해시로
고정된 기존 PCD/YAML 자산을 사용한다.

맵만 무한히 튜닝해 접촉률 차이가 나올 것이라고 보장하지 않는다. 현재는
요청 범위 밖인 simulator 동역학/command-loss 검증을 임의로 수정하지 않고
추가 비행을 멈춘 checkpoint다. 다음 결정은 planner/Adaptive를 그대로 둔
상태에서 이 검증 공백을 별도 시험으로 다뤄도 되는지 확인하는 것이다.
승인 전에는 새 dynamics 결과를 만들어 원래 nominal 결과와 섞지 않는다.
