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

## H05 확인 첫 묶음에서 성과 조건 탈락 (02:05 KST)

| 새 run101 모드 | 완주 | solid 접촉 | 시간 |
|---|---|---:|---:|
| Full | 실패, WP 2/5 | 0 | 180.00 s |
| Sector | 성공 | 0 | 110.15 s |
| Adaptive | 성공 | 0 | 108.46 s |

세 행 모두 quality/solid-observer 검사를 통과했다. Full 20/20이라는 목표는
이미 충족할 수 없으며 H05를 최종 성공 맵으로 채택하지 않는다. Full은
`(-15.178,-5.821,2.666)` 부근에서 종료했다. WP2→WP3의 미완료 관측 구간이
149.9초이고 pose 차분 속도 <=0.05 m/s인 시간이 128.5초다. A-star 0.1초
시간 제한과 certified local escape 반복이 나타난다. 반면 개발 Full은 그
구간을 18.7초에 통과했고, 개발 Sector가 115.4초를 보냈다. 즉 개발 단일
결과만으로 'Sector만 실패하는 배치'라고 해석할 수 없다. 경로 선택 및
공통 planner 복구 불안정성과 일치하는 관측이며 알고리즘을 수정하지 않았다.

Full run101의 최소 MemAvailable은 3490.46 MiB, memory PSI는 0,
resource_valid=True다. 인프라 retry로 지워서는 안 되는 유효한 실패다.
`audit_cylinder_flight_segments.py`는 새 실제 XYZ trace의 구간별 이동·정지
시간을 별도로 계산한다. 정지를 접촉으로 다시 세지 않는다.

중도 탈락과 남은 60회 완수 중 선호를 사용자에게 비동기 질문했다. 답변
전에는 원래 outcome-early-stop 없는 60회 실행 계획을 유지한다. 중단하더라도
그 사실과 실제 완료 횟수를 명시하며 20회 완료로 표시하지 않는다.

## 두 기준 모드의 실패 확인 후 중도 탈락 및 탐색 재개 (02:15 KST)

run102는 Sector 153.03초 완주, Adaptive 180.00초 실패, Full 180.00초
실패였으며 모두 solid 접촉 0이었다. 누적 확인 결과는 Full 0/2, Sector
2/2, Adaptive 1/2다. Adaptive도 공통 서쪽 포켓에서 실패한 추가 증거를
보고, 남은 54회의 같은 맵 반복 대신 map-only 탐색으로 돌아가도록 작업
순서를 조정했다. 비동기 질문에 사용자가 답변했다고 가정한 것은 아니다.
이것은 **원래 outcome-early-stop 없는 60회 계획을 사후에 바꾼 중단 실험**이며
사전 계획대로 완료한 n20 데이터나 최종 성과로 제시하지 않는다.

두 번째 3-mode 묶음의 CSV 행과 observer 보고가 모두 저장된 경계에서
정확한 campaign controller PID만 SIGINT로 종료했다. 진행 중인 비행을
중단하거나 실패를 retry로 대체하지 않았다. 원본 freeze/raw를 그대로
두고 `boundary_stop.json`을 추가했다. 원래 실행기의 기본 옵션으로 남은
행을 재개할 수 있다. result.json은 `STOPPED_EARLY_REFERENCE_FAILURE`다.

경계 종료 감시의 초기 구현은 약 47초 동안 1코어 기준 CPU 17.5%를 사용한
polling이었다. 이를 발견하고 파일 변경 알림 방식으로 바꿨다. 이는 마지막
Full run102의 추가 계측 부하라는 실험상 유의점이다. 그 이전에 끝난 Full
run101과 Adaptive run102의 실패는 이 감시를 시작하기 전에 확정되어 H05
목표 탈락 판단에는 영향을 주지 않는다. run102 Full의 시간 변동을 이
추가 부하와 무관한 단독 인과 증거로 해석하지 않는다.

후속 H11은 H05 원기둥 XY를 `(x,y)→(y,−x)`로 회전시킨 별도 정적 맵이다.
크기·개수·높이와 mission/초기 yaw/센서/planner는 그대로다. 공통 실패 포켓의
위치를 초기 경로와 다른 관계로 옮겨 사전 관측 가능성이 달라지는지 탐색한다.
이는 실제 cloud 가시성/인과를 확인한 결론이 아니라 배치 설계 가설이다.

향후 새 적격 후보는 개발 3묶음에서 Full/Adaptive 모두 safe-complete이고
Sector 실제 실패가 있어야 확인한다. 새 n20은 `--min-development-runs 3
--stop-on-reference-failure`로 시작 전 그 규칙을 freeze한다. 기준 모드의
실패가 나오면 현재 묶음까지 기록하고 조기 탈락하며, 실패가 없으면 원래대로
각 모드 새 20회를 채운다. 목표 조건 자체를 느슨하게 하지 않았다. H05의
과거 freeze와 재개 경로는 기본 옵션 호환으로 보존한다. 관련 21개 테스트 통과.

02:33 KST checkpoint: H11의 개발 두 묶음은 세 모드 모두 2/2 안전 완주다.
Full 86.48/153.70초, Sector 140.60/162.29초, Adaptive 106.37/119.41초다.
아직 Sector 실제 실패가 없어 목표 미달이다. `pilot_extension_declaration.json`에
세 묶음까지의 개발 변동성 확인과 기준 모드 실패 시 탈락 규칙을 기록했고,
마지막 묶음을 이어간다. 시간 차이만으로 성과 조건을 대체하지 않는다.

D07/D08도 별도 배치로 준비했다. 둘 다 300개 원기둥(반경 0.4 m, 높이 3 m),
원점 둘레 반경 5.5 m의 원기둥 링과 배경 원기둥이다. 링의 북서쪽 출구는
D07 125--165도, D08 100--130도이며 남쪽 복귀 출구 280--320도는 같다.
각도는 기둥을 제거할 구간의 명목값이며 실제 링 중심 각도는 12도 간격이다.
초기/복귀 통로를 기하학적으로 확보한 것일 뿐, Full 비행 통과는 아직 아니다.
배경 cloud와 모든 정적 원기둥은 항상 존재하며 sensor fault를 넣지 않는다.

## 후속 탈락 결과와 초기 Sector 관측 점검 (03:18 KST)

H11은 세 번째 개발 Full에서 180초/WP 0/5로 실패했다. 실제 종료 위치는
(5.554,5.655,0.790)이며 solid 최소 여유 0.253 m, 접촉 0이다. Full-first
규칙으로 run3 Sector/Adaptive는 실행하지 않았다. 앞선 두 묶음 성공을 골라
최종 성과로 쓰지 않으며 H11은 기준 모드 실패로 탈락한다.

| 후보 | Full | Sector | Adaptive | 판단 |
|---|---|---|---|---|
| D08 개발 run1 | 실패 180.01 s, WP 0/5 | 미실행 | 미실행 | Full 실패로 탈락 |
| D09 개발 run1 | 완주 60.86 s | 완주 59.34 s | 완주 55.88 s | 세 모드 모두 완주, 목표 미달 |

위 실행은 모두 유효하며 solid 접촉은 0이다. D08은 반경 5.5 m 링/기둥
반경 0.4 m, D09는 반경 4.75 m 링/기둥 반경 0.35 m다. D08 Full은
북동쪽 내부 (3.394,3.377,2.7) 부근에서 A-star timeout과 함께 정체됐다.
D09의 첫 탈출은 세 모드 모두 북서쪽(원점 기준 약 105--108도)이었다.
Sector만 다른 남쪽 출구를 택했다는 가설은 실제 경로로 뒷받침되지 않는다.

D09 Sector run201을 별도 `cylinder_perception_probe.py`로 진단했다.
이 실행은 추가 구독 계측이 있으므로 개발/확인 표본에 합치지 않는다.
55.16초 완주, solid 접촉 0. 첫 12초의 odometry 1,202개와 filtered cloud
112개를 기록했다. 초기 정지 cloud 17개 모두 근거리 1.5 m 바깥의 점 중
body yaw 기준 ±47도 밖 점은 0개였다. 이 진단에서는 초기 Full passthrough를
관측하지 않았다. 비행 중 body yaw 변화와 전방/근거리 관측으로 점진적으로
탈출하는 것과 일치하지만, 각 요인의 독립적인 인과 효과를 증명한 것은 아니다.
이동 중 bearing은 최신 수신 odometry를 이용한 근사치이며 내부 필터와 정확히
동일한 pose timestamp라고 주장하지 않는다. 원래 코드의 near-field 1.5 m와
`!drone_` passthrough 분기를 포함해 runtime은 수정하지 않았다.

주의: `frontend_in_known_free:false`여서 A-star는 unknown-as-free로 검색한다.
trajectory guard의 unknown-as-occupied와 혼동하지 않는다. 또한 simulator의
pose hold 중 twist가 이전 속도를 유지할 수 있다. 실제 이동/정지는 pose 차분으로
판정하며 frozen position의 큰 twist를 고속 이동 증거로 해석하지 않는다.

다음 F05는 원기둥 410개, 높이 3 m, rail 반경 0.4 m, 교차 큰 기둥 32개의
반경 1.9 m/축방향 간격 3.6 m/횡방향 중심 ±1.8 m다. 오프라인 certificate의
±2.8 m 횡방향 경유점은 비행 waypoint로 전달하지 않는다. 모든 원기둥이
분리돼 있고 다섯 구간의 body clearance 최소 0.3875 m를 확인했다. 변경은
오프라인 map generator의 pitch/offset 인자뿐이며 기본값은 이전과 같다.
관련 기하/정책 단위시험 13개 통과, runtime 275개 hash 동일. Full-first
비행을 시작했으며 통과/성과 여부는 아직 미정이다.

F05 개발 run1 최종: Full/Sector/Adaptive 모두 완주, solid 접촉 0,
79.00/79.52/101.61초. 따라서 목표 미달이다. Full의 첫 leg 실제 횡방향
이동 범위는 약 -0.924..0.985 m였다. 설계 certificate의 ±2.8 m가 실제
필수 이동량은 아니었고 세 모드 모두 통과할 수 있었다. Full 최고 z는
2.808 m로 높이 3 m 기둥 위를 넘은 결과도 아니다.

J01은 큰 기둥 대신 반경 0.4 m 원기둥 다섯 개로 이루어진 교차 열을
5 m 축방향 간격으로 배치한다. 다섯 leg 합계 24개 열/120개 기둥이며
rail 및 배경 포함 총 410개, 높이 3 m다. 열 안 기둥 중심 간격 1 m,
표면 간격 0.2 m로 원기둥끼리 겹치지 않는다. 모든 장애물은 처음부터
정적으로 존재하고 벽 mesh/동적 장애물/센서 fault를 쓰지 않는다.
다섯 leg certificate 최소 body clearance 0.40 m, 전체 원기둥 최소
표면 간격 0.20 m를 확인했다. 새 `loop_baffles` 오프라인 생성기와
기하 검사 포함 27개 관련 테스트가 통과했다. Full-first 개발 시험 중이다.

## J01 첫 개발 결과와 반복 계획 (03:31 KST)

| 모드 | 개발 run1 완주 | solid 접촉 | 시간 | 최소 solid 여유 |
|---|---|---:|---:|---:|
| Full | 성공 | 0 | 115.19 s | 0.232 m |
| Sector | 실패, WP3/5 | 0 | 180.00 s | 0.207 m |
| Adaptive | 성공 | 0 | 90.26 s | 0.241 m |

모두 single-attempt, quality/solid-observer valid. 요청된 실제 결과 조합을
한 번 충족했지만 반복성 확인 전의 탐색 결과다. run2와 run3을 추가하여
세 개발 묶음에서 Full/Adaptive 모두 safe-complete인지 확인한 뒤, 통과하면
새 run101--120/모드로 확인한다. 개발 표본을 20회에 합치지 않는다.
개발 및 확인에서 기준 모드 실패는 보존하고 후보를 탈락시킨다. 확인 단계
중도 종료는 사전에 동결한 묶음 경계 futility 규칙을 따르며 미완료로 표기한다.

Sector는 WP3 도착 후 (-23.975,-23.975,1.525)에서 정지했다. 네 번째
미완료 leg 관측 108.7초 중 pose-derived 정지 108.4초다. 로그에
`Empty or non-dense point cloud`와 `MAP_STALE`가 반복된다. 원기둥은
정적으로 계속 존재하며 원본 입력 처리 frame은 계속 증가한다. 필터 후
관측 부족에 따른 liveness/완주 차이로 해석할 사례이지, 이 접촉 0 결과를
충돌 예방 우위 또는 exact-risk 충돌 방지 발동 증거라고 바꾸어 부르지 않는다.
Sector memory PSI는 0, infrastructure_failure=False다. 단순 계산 지연의
마감 미스가 아니라 WP 도착 후 cloud/map 갱신 정체와 함께 발생한 실패다.
별도 개발 중 지도 생성/기하 검사도 일부 수행했으므로 확인 시험에서는
그 작업을 중단하고 동일 실행 조건에서 반복한다.

추가 해석 한계: 이 generator는 원기둥 표면만 PCD에 쓰며 바닥 평면이나
지면 반사점을 추가하지 않는다. 이는 현재 원기둥 benchmark의 조건이지
실제 LiDAR의 모든 환경을 대표하지 않는다. run1 Sector의 최종 body yaw는
-99.839도다. 그 위치에서 15 m 범위 내 원기둥 원판과 ±45도 수평 cone의
보수적인 교차 후보가 0개였다(가장 가까운 angular boundary도 약23.2도 밖).
정적 cylinder 존재와 filtered cloud 비어 있음은 양립한다. Full/Adaptive의
비행 결과 차이를 바닥 반사점이 존재하는 환경까지 일반화하지 않는다.
run1 Adaptive의 effective full-open 전환은 52회지만 이벤트별 전환 기록 없이
그중 특정 전환이 WP3 재출발을 직접 구했다고 단정하지 않는다.

## J01 개발 3묶음 통과와 새 n20 시작 (03:49 KST)

| 모드 | 개발 완주 | solid 접촉 실행 | run1 / run2 / run3 시간(s) |
|---|---:|---:|---|
| Full | 3/3 | 0/3 | 115.19 / 90.95 / 99.87 |
| Sector | 0/3 | 0/3 | 180.00 / 180.00 / 180.00 |
| Adaptive | 3/3 | 0/3 | 90.26 / 160.13 / 89.35 |

9행 모두 quality/solid-observer valid, retry 0. Sector run2는 첫 WP 전
(21.236,18.429,0.955)에서, run1/3은 WP3 부근에서 empty filtered cloud /
MAP_STALE로 정체했다. run3의 twist가 남은 정지 위치를 일시적으로 이동으로
오해한 중간 설명은 연속 pose 확인 후 정정했다. 판정/CSV/접촉 측정은 위치
기반 원자료와 최종 실제 완주 결과를 사용하며 그 오해로 행을 바꾸지 않았다.

Adaptive run2는 네 번째 leg에 95.5초를 썼고 pose-derived 정지가 81.5초였다.
A-star 0.1초 timeout과 reroute/epoch reset 뒤 회복해 실제 160.13초 완주했다.
이 시간 변동을 숨기거나 순간 정체를 최종 완주 실패로 세지 않는다. 아직
Full/Adaptive 반복 20/20을 확인한 것은 아니다.

이제 `confirm_cylinder_search_n20.py cyl2_j01 --min-development-runs 3
--stop-on-reference-failure`로 **새 run101--120/모드, 총60회**를 시작한다.
개발9행은 제외하며 모드 순서를 회전한다. 시작 전 map/runtime/개발 raw/
observer hash와 기준 모드 실패 시 묶음 종료 후 탈락 규칙을 동결한다.
별도 맵 생성/빌드/대형 git 작업을 병행하지 않는다. 예상 약2시간30분은
예상치일 뿐 완료 보고가 아니다. 현재 적격 후보는 J01 하나이며 나머지
네 성공 맵이나 완료된 n20을 만들어냈다고 주장하지 않는다.

## J01 확인 탈락 및 J02 국소 통로 완화 (2026-09-15 10:20 KST)

사용자가 성과가 나올 때까지 map-only 반복을 다시 요청했다. 먼저 실제
완료된 확인 시험을 확인했다. J01은 run106 Adaptive의 실패로 04:32 KST에
사전 규칙에 따라18/60행에서 종료됐다. Full6/6, Sector0/6, Adaptive5/6
완주이고18행 모두 실제 solid 접촉0/quality-valid/single-attempt다.
`boundary_stop.json`과 freeze/raw를 보존하며 실패를 인프라 재시도로
대체하지 않는다. `result.json`의 `all_quality_valid:false`는 기존 함수가
이 필드에60행 완결 조건까지 결합하기 때문이며18행 중 인프라 invalid가
발생했다는 뜻은 아니다. 원본 결과 파일을 고치지 않았다.

실패 Adaptive의 앞 세 leg는12.8/18.0/21.3초, 네 번째 미완료 leg는
133.4초였다. pose-derived 정지125.1초, 최장 연속 pose hold122.3초이며
최종 위치는(0.99535,-21.43023,1.72911)다. solid 최소 여유0.23567 m,
최종 여유0.63024 m로 접촉한 사례가 아니다. PSI some/full 최대0,
resource_valid=True, infrastructure_failure=False, retry0이다.

로그는 동일 포켓에서 trajectory optimization 실패/시간초과로 전방
radius0.8 m reroute zone을 만들고, A-star0.1초 timeout 후 epoch reset하는
순환을 반복한다. 마지막 epoch는240이다. 말미 재계획 시간은 약0.225--0.230초,
EXP 최적화 약137--141 ms였다. 성공한 Adaptive 확인 실행의 네 번째 leg는
16.5--46.2초였으므로 이 한 실패를 정상 반복 시간으로 숨기지 않는다.
이는 좁은 교차 열의 최적화/복구 정체와 일치하는 관측이며, planner 개입으로
독립적 인과를 입증한 결과는 아니다. 알고리즘 수정은 하지 않는다.

J02는 원본 J01에서 네 번째 leg 각 교차 열의 가장 안쪽 기둥 하나씩,
총6개만 제외했다. 제거 좌표는(-14,-25.2),(-9,-22.8),(-4,-25.2),
(1,-22.8),(6,-25.2),(11,-22.8), 반경은 모두0.4 m다. 새 맵 총404개,
나머지404개는 기존 위치/반경/role 유지, 배경을 다시 채우지 않는다.
각 열 끝과 반대 rail 사이 표면 간격은1.8→2.8 m로 넓어진다. 기하학
certificate는 부모의 것을 그대로 유지하고 body clearance 최소약0.40 m,
전체 원기둥 최소 표면 간격약0.20 m를 확인했다. 이 certificate를 mission
waypoint로 주입하지 않는다.

`refine_cylinder_map.py`는 부모 asset/policy hash를 확인하고 새 이름만
허용하며, 어떤 원기둥을 제외했는지 manifest에 parent index로 남긴다.
실행 workspace에 새 PCD/YAML을 생성한 뒤 기존 매핑대로 mirror한다.
센서 YAML은 pcd_name만 치환하며275개 runtime hash와 frozen observer는
변경하지 않는다. 원본 J01 파일을 삭제/덮어쓰지 않는다. 관련 기하/변환
테스트13개 통과. J02 Full-first 개발 시험 후 동일3묶음→새20회 규칙으로
진행한다. 어떤 후보의 긍정적 결과도 아직 확정하지 않는다.

## J02 첫 묶음 및 순차 반복 실행기 (10:33 KST)

J02 run1은 Full77.34초/Adaptive77.70초 완주, Sector180.00초 실패(WP1/5),
세 모드 모두 solid 접촉0/quality-valid다. 단일 개발 결과로 성공을 확정하지
않고 run2/3 후 새20회 확인으로 연결한다. 런타임 코드를 수정한 것이 아니라
오프라인 맵 변환과 시험 운영 스크립트를 추가했다.

`repeat_cylinder_refinements.py --target-passing-maps 5`는 다음10개 정적
기하 변형을 사전에 기록하고 순차 처리한다. 각각 부모는 **원본 J01**이며,
기존 맵/행을 덮어쓰지 않는다. J02 첫 묶음은 이 family 선언 전에 시작했음을
명시한다. 다음은 독립 hold-out 맵10개가 아니라 동일 배경의 관련 변형군이다.

| 후보 | 끝 기둥을 줄일 leg | 열당 제외 개수 |
|---|---|---:|
| J02 / J07 | 4 | 1 / 2 |
| J03 / J08 | 3,4 | 1 / 2 |
| J04 / J09 | 2,3,4 | 1 / 2 |
| J05 / J10 | 1,2,3,4 | 1 / 2 |
| J06 / J11 | 1,2,3,4,5 | 1 / 2 |

실행 순서는 J02→J03→…→J11이다. 배경/나머지 원기둥은 CSV 좌표 정밀도
기준으로 유지한다. PCD는 그 cylinder CSV에서 다시 생성하며 기존 PCD의
point bytes가 bit-identical하게 부분 복사된다고 주장하지 않는다.

- 각 후보: 기존 유효행을 읽고 중복 없이 개발3묶음을 채움.
- Full/Adaptive 유효 실패가 있으면 해당 후보를 탈락시키고 원자료·구간별
  정지 시간·로그 패턴 수를 별도 audit에 저장한 뒤 다음 기하 변형으로 진행.
- 개발 통과 시 새20회/모드. 도중 기준 모드 실패는 현재 묶음 끝에서 탈락,
  실패가 없으면60행을 모두 채워 실제 최종 조건을 판정.
- 인프라/계측 invalid, 예상 밖 자산/코드 변경, 중복행은 진단 정지.
  실패를 성공 재시도로 대체하지 않고, 개발행을 확인20회에 합치지 않음.
- 맵 생성/대형 분석은 비행 묶음 사이에 수행. 확인 캠페인 중 맵 생성,
  빌드, 대형 git 작업이나 다른 비행을 실행하지 않음.
- 목표: 실제 새20회 조건을 통과한 맵5개.10개 변형이 소진되어도 목표에
  미달하면 `RECIPE_FAMILY_EXHAUSTED_REQUIRES_NEW_DESIGN`으로 보고하며
  성공을 만들어내지 않음. 이는 다음 설계 판단이 필요한 상태다.

상태/계획/후보별 audit는 `results/cylinder_refinement_repeat_20260915/`,
개발과 확인 원자료는 기존 각 전용 폴더에 저장된다. 제어기 중복 실행은
파일 lock으로 차단하며, 제어기/변환기/확인기/solid 계측의 hash도 계획에
기록한다. 성공60행, 기준실패3행 보존, invalid 시 즉시 진단 정지를 mock
workflow로 검사했고 관련 전체36개 테스트가 통과했다. 시험 성공의 보장이나
독립적 실패 인과 규명의 자동화라고 주장하지 않는다.
