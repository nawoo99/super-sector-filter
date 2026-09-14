# 원기둥 내부 접촉 누락 정정과 독립 관측 — 2026-09-15

## 발견: 기존 접촉 0은 solid-volume 안전 인증이 아니다

원기둥 map-only 탐색 59회 중 H01 Full은 180.01초 timeout이며 원래
`static_pcd_collisions=0`이었다. 그러나 저장된 실제 odometry 위치는
원기둥 내부다. 원기둥 중심 `(7.989,10.233)`, 반경 0.75 m, 높이 3 m와
기체 반경 0.20 m를 사용하면 다음과 같다.

| 실제 위치 근거 | XYZ (m) | 원기둥 부피 기준 signed body clearance |
|---|---|---:|
| 기존 static-PCD 최소 거리 context | (8.0500,9.8500,1.1500) | −0.56217 m |
| 최종 odometry | (8.051,10.450,1.750) | −0.72432 m |

기존 context의 **표면 점까지 거리**는 0.365641 m여서 기체 반경을 빼도
+0.165641 m로 보고됐다. 표면 점까지의 unsigned 거리는 원기둥 안쪽/바깥쪽을
구분하지 못한다. 또한 기존 runner는 simulator 시작 후 4초를 기다린 다음
monitor를 시작하고, monitor도 PCD를 먼저 로드한 뒤 odometry를 구독한다.
따라서 초기 이동과 표면 통과를 놓치고 이미 내부인 위치에서 관측을 시작할
수 있다. **측정 결함은 확인했으나 Full이 그 원기둥에 진입한 제어 원인의
인과 분석까지 완료한 것은 아니다.**

`audit_cylinder_solid_contexts.py`로 기존 59회 모두의 저장된 실제 3D context와
최종 위치를 점검했다. H01 Full 1회에서 접촉을 확정했다. 다른 58회에서 해당
희소 context가 양수인 것은 전체 비행 안전 인증이 아니다. XY heading trace,
예정 trajectory, counterfactual 위치는 실제 3D 접촉 증거로 쓰지 않았다.
원본 CSV/JSON의 값을 덮어쓰지 않았으며 별도 `solid_context_audit.json`에
정정을 남겼다. 이전 문서의 '접촉 0'은 기존 표면 계측의 보고값으로 읽어야 한다.

## 수정 범위: 비행은 동결, 독립 관측만 추가

Planner, guard, Adaptive, 원래 monitor/runner, simulator dynamics, launch 인자,
속도, waypoint, 센서 시야/주기는 바꾸지 않았다. 동결 runtime 275개 hash를
계속 비교한다. 별도 `cylinder_solid_campaign.py`가 기존 runner의 launch 직전에
읽기 전용 `cylinder_solid_observer.py`를 시작한다. 구독 생성 완료를 확인한
뒤 simulator를 시작하며, flight-command/cloud/decision은 발행하지 않는다.

관측자는 약 100 Hz 실제 odometry에서 구(반경 0.2 m)와 capped solid cylinder의
signed distance를 계산한다. 음수/0인 실제 pose를 접촉으로 세고, 최초 위치가
정지한 `(0,0,1.5)` 부근인지, 유한 데이터인지, odometry 간격이 0.15초 이하인지,
기존 monitor와 완주 판정이 일치하는지도 검사한다. 최초 위치/전 pose CSV/
최소 여유/최초 접촉/접촉 episode를 저장한다. 이는 sampled-pose 계측이며
연속 시간의 동역학 안전 보장은 아니다. 기존 command-loss pose-hold 한계도
그대로다. 별도 observer가 연산 자원을 전혀 쓰지 않는다는 뜻은 아니며,
이후 모드 비교에는 같은 observer를 일관되게 사용한다.

새 결과 경로는 `results/cylinder_solid_map_search_20260915/<map>/`다.
과거 surface-only 결과와 섞어서 안전성 반복 횟수를 늘리지 않는다.

## 20회 진입 규칙

동일 맵에서 새 관측을 갖춘 유효한 3-mode 개발 시험이 있어야 한다.
Full/Adaptive는 모든 개발 행에서 완주와 기존/solid 접촉 0을 모두 만족해야
하고, Sector는 실제 완주 실패 또는 접촉이 있어야 한다. 구 방식의 결과만으로
20회 적격 판정을 받을 수 없도록 실행기와 회귀 테스트를 강화했다.

적격 이후에만 별도 run101--120, 모드별 새 20회(60회/맵)를 시행한다.
map/runtime뿐 아니라 observer와 wrapper의 SHA도 사전에 고정한다. 실패 행을
재시도로 교체하지 않는다. 이는 탐색으로 선택한 맵에서의 반복성 확인이며
독립 맵 일반화 또는 100% 모집단 보장은 아니다.

## 새 관측의 첫 완료 비교

F04는 F03에서 관측했던 Sector 편향 구간에 원기둥 2개를 추가한 개발 맵이다.
기존 경로를 고정한 counterfactual에서는 Sector만 접촉했지만, 실제 새 비행에서
Sector가 경로를 바꾸어 통과했다. 따라서 성공 후보로 채택하지 않는다.

| 맵/모드 | 완주 | solid 접촉 episode | 시간 (s) | 최소 solid 여유 (m) |
|---|---|---:|---:|---:|
| F04 Full | 1/1 | 0 | 65.10 | 0.311 |
| F04 Sector | 1/1 | 0 | 69.96 | 0.342 |
| F04 Adaptive | 1/1 | 0 | 72.93 | 0.252 |

세 행 모두 관측 시작/간격/완주 일치 검사를 통과했다. F04는 목표 미달이며
20회 캠페인은 시작하지 않았다. H04(분산 숲에서 H01 실패 위치 주변 기둥을
재배치한 별도 맵)의 Full-first 탐색을 이어간다. H01 실패는 보존한다.

후속 H04는 Full/Sector/Adaptive 각각 92.37/84.97/85.71초에 모두 solid 접촉
0으로 완주해 역시 적격이 아니다. H05는 source seed10의 반경을 0.85 m로
키운 후보, H08은 seed9/반경 0.85 m에서 이전 Full 실패 위치 두 곳 주변의
기둥을 재배치한 후보다. H06/H07(seed7, 반경 0.85/0.80 m)은 오프라인 여유
통로 확인에 실패해 비행하지 않았다. H09/H10은 H05 원기둥 XY만 90/180도로
회전한 배치다. Mission/초기 yaw/센서 설정을 회전시키지 않는다. 이들은 동일
원형에서 파생된 개발 변형이지 서로 독립적인 환경 일반화 표본이 아니다.

## H05 첫 적격 개발 결과와 새 n=20 시작 결정 (01:55 KST)

| 모드 | 개발 완주 | solid 접촉 | 시간 (s) | 최소 solid 여유 (m) |
|---|---|---:|---:|---:|
| Full | 1/1 | 0 | 93.49 | 0.238 |
| Sector | 0/1, WP 4/5 | 0 | 180.01 timeout | 0.177 |
| Adaptive | 1/1 | 0 | 107.71 | 0.246 |

세 행 모두 단일 시도이며 resource/speed/새 관측 검사에 유효하다. H05는
source seed10에서 만든 반경 0.85 m, 높이 3 m 원기둥 410개다. Planner/센서/
simulator/mission은 이전과 동일하다. 실제 완주 결과 차이이므로 첫 적격 맵으로
선정한다. 아직 **확인 시험에서 Full/Adaptive 20/20을 달성했다는 뜻은 아니다**.

저장된 실제 waypoint 시각에서 WP2→WP3 구간은 Full 18.72초, Sector 115.41초다.
Sector가 서쪽 leg에서 동쪽으로 벗어났다 복귀하는 경로가 보이며, 최종 XY는
(11.035,-6.220)으로 복귀 leg 도중이다. 기존 monitor 경로 길이는 Full 268.044 m,
Sector 329.550 m다(초기 monitor 이전 구간을 제외한 값). Full/Sector의 최소
MemAvailable은 4183.65/4057.55 MiB, memory PSI는 모두 0이다. 이 관측은
장거리 우회/지연과 일치하지만 FOV만의 단독 인과 효과를 증명한 개입 실험은
아니다. 개발 중 일부 geometry 생성 및 git 저장 작업도 병행했으므로 이
단일 결과를 최종 반복성 성과로 단정하지 않는다.

다음은 동일 H05에서 run101--120 각 모드 20회, 총 60회다. 탐색 run1은
포함하지 않는다. 실행기가 시작 전에 map/runtime/development row/계측 hash를
freeze.json에 저장하고, 모드 순서는 회전한다. 이 확인 캠페인 동안 별도 맵
생성/빌드/대용량 git 압축 작업을 병행하지 않는다. 실패 결과는 보존하며
관측 Full/Adaptive 20/20 safe-complete와 Sector의 실제 실패가 모두 있어야
최종 조건 통과다. H08/H09/H10의 비행은 그 이후 별도 탐색으로 미룬다.
