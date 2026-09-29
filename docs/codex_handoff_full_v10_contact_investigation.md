# Codex 인계 문서 — SUPER `full` 모드 v=10 잔여 접촉 조사 (2026-08-13)

> [!IMPORTANT]
> **2026-09-29 최신: Forest Active-Yaw Sector의 mission cutoff를 제거한 fresh n=10은 10/10 완주·접촉0.**
> run94201--94210은 비행당1회, 재시도·대체 없이 실행했고 planner/map/속도/±45도
> Sector/Active-Yaw는 그대로 두고 mission-time horizon만 무한대로 설정했다. 전 실행이
> run/resource/speed/log gate를 통과했으며 시간99.155±17.417초, 범위73.98--125.17초,
> 평균CPU0.4170코어, 누적41.962core-s, 입력2.780MiB/s, map update9.444ms/frame,
> 최소 solid clearance0.101m였다. 단, 10회 모두 종전 cutoff 180초 전에 완주했으므로
> `cutoff 제거가 실패를 구조했다`는 인과증거가 아니다. 기존 Forest cohort의6/10·접촉1은
> 삭제하거나 대체하지 않으며, 새 결과는 서로 다른 run ID의 독립·비paired 표본이다.
> 상세 §8.117과
> `results/forest_active_yaw_no_mission_timeout_n10_20260929/summary.md`.

> [!IMPORTANT]
> **2026-09-29 최신: Active-Yaw Sector를 기존 Sector 대체 후보로 6맵×10회 완주 실행했으나 승격 실패.**
> 기존 자료는 그대로 보존하고 새 run94101--94160을 맵 순환 순서, 비행당1회,
> 재시도·대체 없이 끝까지 수행했다. 60/60이 인프라·자원·속도·로그 품질 gate를
> 통과했다. Map1--5는49/50 완주·접촉1/50, Forest는6/10 완주·접촉1/10,
> 전체55/60 완주·접촉2/60이었다. Map3 run94113과 Forest run94157은 각각 약
> 4.71m/s와6.80m/s로 원기둥에 진입했으며, 새 위험을 감지한 시점의 제동 후보가
> 인증되지 않았다. Active-Yaw는 인증 정지 뒤에만 시작되므로 이 주행 중 접촉을
> 예방하지 못한다. 기존 Sector도 Map1--5에서49/50·접촉1/50이었고 새 방식은
> 76.64초로 기존54.96초보다 느리다. Forest는 기존8/10·접촉2에서 새 방식
> 6/10·접촉1로 접촉은1회 줄었지만 완주와 시간이 악화됐다. 따라서 기존 Sector를
> 이 방식으로 교체하지 말고 `Sector (Active-Yaw)` ablation으로 분리한다. 상세
> §8.116과 `results/sector_active_yaw_replacement_sixmap_n10_20260929/summary.md`.

> [!IMPORTANT]
> **2026-09-29 최신: Fixed Sector active-yaw six-map 확대 검증은 Forest 접촉으로 조기 중단.**
> Urban n=10 성공 뒤 Map1--5와 Forest에 대해 스모크 각1회는 모두 완주·접촉0이었다.
> 이어 새 run ID로 맵당10회, 첫 실패 중단 프로토콜을 시작했고 run94001--94020은
> 완주·접촉0이었으나 21번째인 Forest run94021에서 완주 중 static-PCD 접촉1회가
> 확인되어 나머지39회는 실행하지 않았다. 접촉은 waypoint2 부근
> `(-17.12,-20.90,1.65)`에서 반지름0.5m `trunk_024`에 body clearance -0.021m,
> 속도0.450m/s였다. 제동 시작 yaw133.3도 기준 나무는 body-relative -118.5도로
> ±45도 Sector 밖이어서 map에 없었고, 회전은 제동 완료 후 시작하도록 구현되어 있다.
> 따라서 active-yaw가 충돌한 것이 아니라 제한 시야 map이 blind-side 장애물이 없는
> 것으로 보고 인증한 제동 종점이 실제 장애물 안에 놓인 구조적 실패다. 이 변형은
> 경로 고착을 줄이지만 Adaptive의 Full 관측을 대체하는 안전 해법으로 승격하면 안 된다.
> 원본 Fixed Sector baseline은 유지하고 변형은 별도 ablation으로만 표기한다. 상세
> §8.115와 `results/sector_active_yaw_sixmap_n10_v2_20260929/summary.md`.

> [!IMPORTANT]
> **2026-09-29 최신: Urban Fixed Sector의 정지 고착을 active-yaw recovery로 제거, n=10 통과.**
> `SUPER_SECTOR_ACTIVE_YAW_SCAN=1`에서 Fixed Sector의 새 goal은 기존 인증 브레이크로
> 정지한 뒤 goal 방향을 관측하고 경로를 다시 만든다. 해당 관측으로 경로를 못 찾으면
> goal 기준 +90/-90/후방 순서로 추가 회전하며, 각 view마다 실제 yaw 도달·settle·새
> processed scan·fresh committed map을 요구한다. 4개 view가 모두 실패하면 주행하지 않고
> 인증 정지를 유지한다. MARSIM의 유효한 0-point frame을 ROG-Map이 센서 무응답으로
> 오인하던 문제도 `SUPER_SECTOR_EMPTY_SCAN_HEARTBEAT=1` opt-in으로 수정했다. 이 frame은
> committed no-op으로 freshness만 갱신하며 occupancy/map_version/snapshot은 바꾸지 않는다.
> 두 기능은 기본 OFF이고 Sector 전용 wrapper만 켠다. Full/Adaptive에는 적용하지 않았다.
> 최종 Urban Sector 10회는10/10 완주·접촉0, 평균75.446±7.361초였다. 기존 동일 Urban
> control은 Full48.321±1.493초/10·Adaptive51.303±4.534초/10, 모두 접촉0이다. 따라서
> 고착은 제거됐지만 회전 관측 비용으로 Sector가 Full보다56.14%, Adaptive보다47.06%
> 느리다. 상세 §8.114와
> `results/urban_sector_active_yaw_v1_n10_final5_20260929/summary.md`.

> [!IMPORTANT]
> **2026-09-27 최신: c33 stage1 Forest Full 실패에서 계획 clock 결합 결함 확인, c34로 분리.**
> c33 첫 반복은 G1--G5와 Urban triplet을 통과했으나 Forest Full이 waypoint1 뒤
> 180.01초/1·접촉0으로 중단됐다. 같은 triplet의 Sector70.48초/5·접촉0과
> Adaptive66.67초/5·접촉0은 완주했다. Full은849회 async solve를 요청했지만,
> A* 예산을0.25초로 늘린 뒤에도 전체 solve가 trajectory look-ahead인
> `replan_forward_dt=0.1초`를 deadline으로 재사용해 0.18--0.26초 정상 후보를 버렸다.
> c34는 look-ahead0.1초/A*0.25초를 유지하고 별도 공통 async compute budget0.5초를
> 추가했다. 미지정 프로파일은 기존 look-ahead 값을 fallback으로 써 호환된다.
> 독립 Forest Full run85100은64.43초/5·접촉0, clearance0.231m로 통과했다.
> c33 결과는 대체하지 않고 중단 코호트로 보존하며, c34는 새 7-map×3-mode×n=10
> 프로토콜로 처음부터 수행한다. 상세 §8.113과
> `results/scenario7_compute_budget_v9_n10_20260927/protocol.json`.

> [!IMPORTANT]
> **2026-09-27 최신: c32 Urban 실패의 Full 조기해제 원인을 c33에서 수정, 7-map n=10 후보 동결.**
> c32 캠페인은 stage1 Urban repeat2에서 Adaptive가 certified clearance-escape를
> commit하자마자 Full을 닫고, escape를 실제 실행하기 전 Sector map으로 main guard가
> 다시 fail-close해 중단됐다. c33은 escape/initial-egress certificate이면 Full을 유지하고,
> escape 종료 절대시각 이후 현재 generation/map의 일반(non-escape) certificate가 있을 때만
> Sector로 복귀한다. 고정 지연이나 같은 후보 재시도가 아니다. Urban Adaptive smoke
> run83126은87.70초,5/5,접촉0, strict recovery audit valid였고 run83127 비행도
> 56.83초,5/5,접촉0이었다(후자는 수동 실행 cwd 때문에 비행 후 CPU 요약만 실패).
> c33 코드·프로토콜은 별도 7-map×3-mode×n=10, 무재시도 2-stage 후보로 동결했다.
> 먼저 각 모드/맵 n=5가 모두 gate를 통과해야 추가 n=5를 수행한다. 상세 §8.112와
> `results/scenario7_escape_hold_v8_n10_20260927/protocol.json`.

> [!IMPORTANT]
> **2026-09-27 후속: goal-change Full-refresh v6가 bounded/Urban gate를 통과했으나 아직 탐색 결과.**
> `SUPER_GOAL_CHANGE_FULL_REFRESH_V6=1`은 FOLLOW 중 정확한 새 goal identity에만
> 정지→Full committed ACK→새 경로 인증→Sector 복귀를 강제한다. 동일 goal 재전송은
> 무시하고 Full/Sector에는 명시적으로 OFF, 기본값도 false다. 별도 overlay 빌드,
> CTest4/4와 source contract v6 4/4·v5 3/3·v4 5/5·async12/12 통과.
> Urban Adaptive 무재시도 2회는 각각51.35/67.87초, 모두5/5·접촉0이었으며 정확히
> 4개의 waypoint 변경마다 v6 요청이1회 발생하고 각각 Full ACK/새 generation 뒤 해제됐다.
> fresh 3모드에서는 Full54.74초/5·접촉0, Sector180.01초/1·접촉0,
> Adaptive67.87초/5·접촉0. Adaptive 평균 CPU31.35%, map input55.89%, map update50.77%
> 감소지만 시간23.99% 증가로 누적 CPU 감소는16.07%뿐이다. 이후 G1/G4 Adaptive도
> 각5/5·접촉0, 새 goal 요청4/ACK완료로 통과했다. 비행 전에 고정한 Urban Adaptive
> n=3(run81520--81522)도 3/3 모두5/5·접촉0, 평균54.66초이며 retry/replacement0이다.
> 최초 탐색2회와 사전고정3회를 합쳐 population100%나 최종 승격으로 해석하면 안 된다.
> 다음은 추가 튜닝 전 더 넓은 map-level 검증 범위를 먼저 동결하는 것. 상세
> `docs/scenario7_goal_change_full_refresh_v6_20260927.md`, §8.111.

> [!IMPORTANT]
> **2026-09-27 후속: stationary-hold v5는 Urban 1/2 성공, 새 분기 미발동 — 승격 금지.**
> `SUPER_STOPPED_HOLD_V5=1`은 물리적으로 정지한 후보에 한해 전체 hard-query 완료 뒤
> `CLEARANCE_MARGIN`을 허용하도록 별도 overlay에 구현했다. CTest4/4, 신규3/3,
> v4 5/5, async12/12 통과. 그러나 Urban Adaptive 무재시도 2회는 첫 회
> 71.88초/5·접촉0, 둘째 회180.01초/2·접촉1이었고 두 회 모두 새
> `publish_physically_clear_margin_hold`가0회라 첫 성공을 v5 효과로 해석할 수 없다.
> 둘째 회는 waypoint1→2의 큰 방향 변경 뒤에도45° Sector로 먼저 주행했고, guard가
> TTC 약0.48초에서 위험을 찾은 뒤에야 Full이 열려 접촉했다. 이후 Full duty87.036%와
> A* timeout1,141회는 접촉 근처 정지의 하류 결과다. 반복시험/timeout 튜닝 금지.
> 다음은 정확한 새 goal에만 정지→Full committed ACK→새 경로 인증→Sector 복귀를
> 강제하는 기본OFF 후보. 상세 `docs/scenario7_stopped_hold_v5_20260927.md`, §8.110.

> [!IMPORTANT]
> **2026-09-27 후속: v4 G4는 통과했지만 Urban Adaptive 정지 복구가 실패 — 승격 금지.**
> Fresh G4 n=1은 Full/Sector/Adaptive 모두 5/5·접촉0, Adaptive Full 전환3/복귀3,
> Full 대비 평균 CPU34.44%·누적 CPU38.22%·sensor payload67.24%·map update62.37%
> 감소로 측정 gate를 통과했다. 이어 실행한 Urban은 Full63.68초/5·접촉0인 반면
> Sector와 Adaptive 모두180초/0·접촉0이다. Adaptive는 초기 v4 certificate/release와
> 5.1m 주행 후 TTC15ms 위험에서 fail-closed 정지했고, Full 전환1회와 committed ACK1회도
> 정상이나 Full-open이95.264% 유지됐다. 정지 위치는 실제 body clearance0.061m이고
> 위치차분 속도0인데 perfect-drone odom twist가 마지막6.851m/s로 고정됐다. 핵심 blocker는
> strict stationary check가 UNOBSERVED인 뒤 unknown-relaxed check가 CLEARANCE_MARGIN을
> 반환하면 기존 분기가 SAFE만 받아들이는 것이다. 그 결과 brake retry1,663회, recovery0,
> 0/5 timeout. 단순 시간/맵/반경 튜닝이나 반복시험 금지. 다음은 full-query soft-margin
> completion proof를 요구하는 좁은 stationary-hold 재인증 수정 후 Urban Adaptive부터 재검증.
> 상세 `docs/scenario7_stopped_departure_v4_20260927.md`, §8.109와 compact G4/Urban JSON.

> [!IMPORTANT]
> **2026-09-27 후속: v3 정지출발 고착 원인 2개를 v4에서 함께 수정, G1 Full 기능 스모크 통과.**
> v3 G1 Full은 180.01초, 0/5 waypoint, 이동/PositionCommand 0, 비동기 결과
> 1,362개 전부 `POSITION_DISCONTINUITY`였다. 원인은 (1) 실제 정지 위치를 0.05m
> voxel center로 바꿔 최소43.301mm 공간 불연속을 만든 것과 (2) solve-start clock을
> release 시점에 그대로 사용한 것이다. 별도 v4 overlay에서 실제 odom 위치를 optimizer
> 경계로 보존하고 voxel은 검색 seed로만 사용하며, relative-time-zero 전체 prefix 인증 뒤
> position/yaw/EXP/backup/egress receipt를 같은 release clock으로 rebase한다. ordinary와
> emergency가 동일한 generation/map/PVA-bound release 함수를 사용한다. 기본값은 여전히
> false이고 `SUPER_STOPPED_DEPARTURE_V4=1`에서만 켜진다. CTest4/4, 신규 source5/5,
> 기존 async source12/12 통과. G1 Full n=1은 53.69초, 5/5, 접촉0, 최소 body
> clearance0.267m로 완주했고 ordinary2+emergency6 certificate/release 모두 P/V/A오차0.
> 첫 Full의 CPU postprocessor는 실행 cwd의 상대경로 문제로 비행 후 실패해 parent status를
> 보존했고 재시험으로 대체하지 않았다. 이어 repo root에서 fresh G1 3모드 n=1을 무재시도로
> 완료: Full47.61초/5·접촉0, Sector180.01초/2·접촉1, Adaptive55.00초/5·접촉0.
> Adaptive effective Full open/close6/6, 모든6 refresh ACK commit. Full 대비 평균 end-to-end
> CPU33.18%, map-update62.88%, sensor payload64.31% 감소했지만 시간15.52% 증가로 누적 CPU
> 감소는24.46%뿐이라30% 목표/mission-time gate는 실패했다. 모든 source/timing gate와
> release21회의 P/V/A오차0. 여전히 exploratory n=1이며 다음은 G4, 이후 조건부 Urban이다.
> 상세 `docs/scenario7_stopped_departure_v4_20260927.md`, §8.109.

> [!IMPORTANT]
> **2026-09-26 후속: guard-contract v2도 안전성 검증 실패 — 안정판 아님.**
> no-raycast 중복 hit의 확률 증거 손실, coarse observed-free marker의 occupied
> 삭제, 정지 검사의 조기 CLEARANCE_MARGIN 수락을 수정했다. 정지 policy revision=2는
> 전체 hard-query 검사 후에만 soft margin을 허용하며 unknown=false 정책은 여전히 남는다.
> 원본/v1 install 보존, 별도 `/root/super_ws/scenario7_guard_v2_20260926/install` 사용.
> 실제 ROG archive 회귀·C++ normal/sanitizer·Python79검사·기존 CTest3·static24 통과.
> 새 cohort `results/scenario7_guard_contract_smoke_20260926_v2b`는 ON8+OFF3=11회,
> 29분46초, `COMPLETE_WITH_RETAINED_FAILURES`. G1 ON/OFF 세 모드 모두 무접촉 완주.
> G4 ON Adaptive는 완주했지만 접촉1; Urban ON Adaptive/Sector는 접촉1씩+180초 미완주.
> Urban ON Full 및 G4/Urban OFF는 미실행이며 성공·접촉0으로 세지 말 것. 재시도 없음.
> G4/Urban 최초 접촉은 이번에는 normal EXP이고 footprint-egress 사용0회이며 SAFE가 유지됐다.
> Urban은 마지막 Full 취득 약250ms/ Sector 복귀 약200ms 뒤 건물10에 접촉했다.
> 단순 Full 전환 지연만으로 설명 불가. 센서 자세/해당 벽 voxel 증거는 아직 불충분하다.
> Sector는 접촉 후 동기 A* 약100ms 반복으로 FSMmain 평균19.76Hz(후반 약10Hz),
> command는100Hz 유지. A* 반복은 최초 접촉의 원인으로 확정된 것이 아니라 후속 병목이다.
> G1 OFF Adaptive CPU 평균45.06%/누적48.39% 감소는 n=1 관측이며 안전성 실패를 상쇄하지 않는다.
> 다음은 건물10/G4 원기둥40의 sensor→map→guard 증거 및 경로 관측 검증, 동기 A* 분리.
> 상세 `docs/scenario7_guard_v2_results_20260926.md`, §8.108. CIRI 기본false/shadow 유지.

> [!IMPORTANT]
> **2026-09-26: Scenario7 수정 후보 검증 실패 — 안정판으로 승격하지 말 것.**
> G4 SimplifySFC 무한 append, 초기 footprint 탈출의 commit/live 계약 불일치,
> 시간 재조정/EXP 재사용 경로의 불연속 거부, Urban 관측기 지연과 누락 reference
> 처리를 수정했다. 원본 install/기존 실패 결과는 보존하고 별도 repair overlay 사용.
> Python230검사+실제 PCD 검사, C++ normal/sanitizer, 전체 빌드 및 static24검사 통과.
> G1/G4/Urban 실제 ON7+OFF6=13회: G4 모든 주행 무접촉 완주, G1 Adaptive OFF는
> 완주했으나 접촉1, Urban Adaptive ON은 접촉1+180초 미완주. Urban OFF는
> BLOCKED_BY_PREFLIGHT로 비행하지 않았다. 이를 0% 완주 또는 접촉0으로 세지 말 것.
> G1에서는 부드럽게 실행되는 backup 궤적이 원기둥을 침범하는 동안 live SAFE였다.
> Urban도 건물 내부 진입 후 정지해 A*가 반복 실패했다. 미관측 정책 설정true와
> 후보/live 검사에서의 실제 false 호출은 확인됐으나 당시 voxel 상태 증거는 부족하다.
> 관측기 수신100.001Hz/p99 10.405ms는 회복; FSMmain97.525Hz와 안전 문제는 남음.
> 초기 footprint receipt는 이번 주행에서 발동0회라 실제 r06 수정 검증은 미완료.
> 상세 `docs/scenario7_repair_results_20260926.md`, §8.107. 210회 재시작보다
> backup/벽 진입 직전 sensor→map→certificate 증거 수집과 안전 계약 수정이 우선.

> [!IMPORTANT]
> **2026-09-21: Gap-free G5 관측기를 미션보다 먼저 준비하도록 수정, 새 ON 3모드 1회 완료.**
> 기존 runner는 launch 후4초 뒤 observer를 시작했지만 waypoint mission은3초 뒤
> 자동 시작해 초기 약1초를 관측하지 못했다. Gap-free 전용 경로에서는 launch 내부
> mission을 끄고, observer가 첫 유효 odometry를 원점에서 기록한 READY 파일을 만든
> 뒤 동일 waypoint_mission을 별도 시작한다. planner/센서/맵/안전판단은 변경하지 않았다.
> 새 결과 `results/gapfree_g5_observer_ready_20260921_104214/preflight`: 세 모드 모두
> 첫 pose `(0,0,1.5)`, 완주. Full/Adaptive analytic contact0, Sector contact1
> (cylinder320, 약0.220초). 이전 G5 Adaptive 접촉1은 이번 n=1에서 재현되지 않았지만
> 확률적 결과를 오류로 소급 취소하지 않는다. 첫 시도 `..._103943`은 Adaptive 안전
> 결과는 유효했으나 별도 mission 로그가 stack audit에서 빠져 중단된 진단 실행이며,
> append/tee 결합 후 재실행에서 모든 source/recovery/timing gate가 통과했다.
> 상세 §8.106. 이 1회는 population 안전성이나 최종 모드 우위를 확정하지 않는다.

> [!IMPORTANT]
> **2026-09-18: G1–G5 수동 캠페인에 실패 보존·계속 실행 모드 추가, 비행은 사용자가 실행.**
> `run_gapfree_n5.py --continue-after-failure`는 접촉·미완주·로그/계측 누락·속도/
> 자원·child 프로세스 실패를 원래 실패/무효 상태로 저장하고 다음 예정 회차로
> 진행한다. 실패를 성공이나0으로 바꾸지 않으며 retry/replacement도 하지 않는다.
> source/map/frozen-evidence 변경과 Ctrl+C/SIGTERM은 계속 중단한다. 원본 install
> 바이너리를 유지하고 앞 절의 진단 source5개 차이만 admission에 명시적으로 기록한다.
> offline37검사 및 broad-policy dry-run 통과, actual_flights=0. 사용자 명령은
> `bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh --continue-after-failure`.
> 기본 무옵션 실행의 fail-closed 의미는 유지된다. 상세 §8.105 및 수동 실행 문서.

> [!IMPORTANT]
> **2026-09-18: G1/G4 Adaptive 접촉 재현, 진단 전용 수정·별도 빌드 완료. 비행은 사용자가 실행.**
> 기존의 “새 맵 비행 0회” 배너는 더 이상 최신 상태가 아니다. 사용자가 수동 캠페인을
> 두 번 실행했다. 첫 실행 `gapfree_n5_20260918_110107_690945`은 G1 triplet에서
> Full/Sector 접촉0, Adaptive 접촉1로 중단했다. 두 번째
> `gapfree_n5_20260918_130318_768999`은 G1–G3 preflight를 통과한 뒤 G4에서
> Full0/Sector1/Adaptive1 접촉으로 중단했다. 모두 완주했지만 Adaptive zero-contact
> gate 실패이며 실행기 오류가 아니다. 실패 자료를 삭제하거나 성공으로 대체하지 말 것.
> planner 의사결정·파라미터·맵은 바꾸지 않고 기본 OFF 진단 기록만 추가했다. 렌더 원점군,
> 맵 입력, hit/miss와 snapshot delta, guard query의 effective/configured unknown 정책,
> 실제 발행 명령 및 외부 trajectory/odom을 같은 시간축으로 저장한다. G1 하드코딩을 제거해
> 환경변수로 ROI 중심을 선택한다. 기존 install은 유지하고 진단본만
> `/root/super_ws/g1_contact_diag_20260918/install`에 빌드했다. 두 패키지의 hard-coded
> CMAKE_PREFIX_PATH도 제거해 실제 overlay rog_map/super_planner가 선택됨을 확인했다.
> C++ standalone 및 Python20검사, 전체 진단 빌드 통과. G4 prepare-only는
> `results/gapfree_contact_diagnostic_g4_prepared_20260918`, actual_flights=0.
> 다음은 사용자가 아래 §8.104의 G4 Adaptive 1회 명령을 직접 실행하는 것. 자동 retry,
> 75회 재시작, 알고리즘 튜닝, 본 CPU/안전성 표 합산은 금지. 상세 §8.104.

> [!IMPORTANT]
> **2026-09-18: G1–G5 수동 한 줄 실행기 준비 완료. 새 맵 실제 비행은 아직0회.**
> 사용자가 직접 명령을 입력할 예정이므로 이번에는 시뮬레이션을 시작하지 않았다.
> `bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh`
> 새 DDS30/RViz5와 별도 ON15 확인 후 Full/Sector/Adaptive ×5맵 ×5회=본시험 OFF75.
> 실행마다 `results/gapfree_n5_날짜_시간_PID/`에 맵별 결과표/원본/전지표/접촉·odom 저장.
> Full/Adaptive 미완주·접촉은 현재 triplet 후, 계측·소스·자원 실패는 즉시 중단/보존.
> Sector 성과는 비교값으로 보존; 자동 retry/실패 대체/기존 Normal 합산/n20/push 없음.
> 원기둥 형상+기체 반지름0.2m의 수신 pose 표본 접촉 episode를 별도 기록한다.
> 기존 sampled-PCD 관측도 보존하되 재진입 횟수 한계를 구분; 연속 swept 충돌 증명 아님.
> planner/센서/알고리즘/바이너리는 변경하지 않고 hash-pinned 기존 helper를 새 adapter에서 사용.
> 최종 dry-run 통과: `results/gapfree_n5_preparation_20260918/dry_run02/status.json`.
> `DRY_RUN_ONLY`는 완주·안전 검증 결과가 아니다. 사용자가 실행하면 최신 상태를 새 폴더에서 확인.
> 상세 `docs/gapfree_n5_manual_campaign_20260918.md` 및 §8.103. 아래 맵 생성 기록은 그대로 유효.

> [!IMPORTANT]
> **2026-09-18: 지름1m·강제 minimum gap1m 제거한 G1–G5 생성 완료, 비행0회.**
> 사용자는 새5맵과 추후 모드별5회를 원하지만 이번에는 '일단 맵만' 명시. ROS 미실행.
> gapfree_d1_m01..05, 각410개·높이3m·64×64m, 균일 난수 nonoverlap 배치.
> 넓은 시작/waypoint 보호 공간 및 경로 주변 비움 없음. 실제 최소 표면 간격1.1~4.1mm.
> 최근접 분포/분위수/히스토그램·밀도 기록. body radius0.2+margin≥0.35m의
> offline 각loop24 leg/연속 선분 연결 확인, 경로는 planner에 공급하지 않음.
> 기존 generator/helper 재사용, 신규 offline script/test만 runtime에서 작성·mirror.
> Python11검사 및 독립 PCD5검사 통과; PCD800730points/map. C25동결1396파일 변경0.
> docs/gapfree_d1_maps_20260918.md, results/gapfree_d1_maps_20260918/manifest.json 및 그림.
> 이 맵의 Full/Adaptive 완주·안전이나 Sector 대비우위는 미검증. 후속75회 아직 미실행.
> **C25는 완료:** 9/17 17:07KST OFF300/ON15 완료. Full/Adaptive각100/100접촉0;
> Sector100/100완주이나 N5 r01_run22004접촉1. 아래 '진행 중'은 과거 launch checkpoint.
> 현재 추가 비행/캠페인 없음. planner/algorithm/sensor/binary 변경 및 push 없음.

> [!IMPORTANT]
> **2026-09-17 C25 진행 중: 동일 C24 후보 Normal 독립 OFF300, iteration02.**
> 범위는 현재 코드·설정·맵 고정 및 Normal N1–N5(seed1/3/5/7/9) ×3모드 ×20회뿐이다.
> C24 frozen862개 파일과 ON/OFF 새 audit/저장gate 일치 모두 확인; runtime 변경 없음.
> 새 실행기/집중 Python107검사 통과. 먼저 새 DDS30/RViz5와 ON15 후 OFF300 실행 예정.
> 기존 C24 OFF75/ON15와 합산 금지; 완료 여부는 아래 status의 실제 state로 확인한다.
> 현재 경로 `results/c25_normal_confirmation_20260917/iteration02/status.json`, base-run21000.
> iteration01은 첫 정적검사에서 workspace 미source로 mars_quadrotor_msgs import 실패;
> 비행0회, 실패/동결파일 모두 보존. source /opt/ros/humble/setup.bash 및 install/setup.bash
> 환경 설정만 로드해 iteration02를 새로 시작하며 runtime/실행기/프로토콜은 변경하지 않음.
> 10:42 KST 실제 시작, controller PID3935880 / PTY84333. 첫 standalone DDS2건 통과.
> 정적 검사 진행 중이며 아직 ON15/OFF300 완료 아님. 최신실적은 status/raw 자료를 확인.
> 자동 retry/실패 대체/Stress 탐색/추가 CPU 튜닝/push 없음. Full/Adaptive 결과 실패는
> 현재 triplet 종료 후, 계측/소스/복구/자원 오류는 즉시 중단하며 모든 기록을 보존한다.
> 기본값 OFF async 후보를 3모드 공통 명시적으로 유지. raw-cloud CIRI shadow 기본 false 유지.
> 이전 CPU35.53%/누적33.13%는 n5 결과이며 40% 달성으로 표현 금지.
> 프로토콜 `docs/c25_normal_confirmation_20260917.md`; 전체 약6~8시간 예상, 아직300회 완료 아님.

> [!IMPORTANT]
> **2026-09-17 C24 완료: 정적검증35건·ON15·OFF75 모두 통과. 실행 중 캠페인 없음.**
> 최신 요청은 질문 없이 N1–N5(seed1/3/5/7/9) × Full/Sector/Adaptive ×5를 계속 진행하는 것.
> 아래 C23의 답변 대기 상태는 해제됨. 과거 실패 기록은 그대로 보존하며 소급 합격 처리하지 않음.
> N5의 synchronous PlanFromRest가 100Hz main callback을 막는 경로를 확인하여,
> 기본 OFF `SUPER_ASYNC_CERTIFIED_RECOVERY=1` 후보를 구현. 기존 replan executor에서 계산하고
> main에서 정확한 brake/goal/Full ACK/map/generation/안전 인증을 확인한 후에만 정지를 해제함.
> Astar parent chain cycle/상한, corridor 전부점유, backup seed underflow 방어도 추가함.
> 이들은 확인된 코드 결함이나 C23 메모리 급증의 직접 원인으로 확정한 것은 아님.
> 기존 소스 보존 및 진단 4회(OFF3+ON1) 완료. 그 진단에서는 급증 미재현; 본시험에 혼합 금지.
> Release 빌드/Python169검사, 정적 DDS30/RViz5, ON15 후 독립 OFF75 완료. 실패 대체·자동 n20 없음.
> Full/Adaptive 안전·완주 실패 및 계측 실패는 진단/수정 후 새 iteration. Sector 결과는 비교값으로 보존.
> owned process RSS>4608MiB면 오염 마커 후 제한시간 stack 수집, 해당 triplet 성능값 채택 금지.
> OFF 맵별·모드별5/5 완주·접촉0, 총75/75. 모든측정/소스/복구/속도/자원gate true; retry0.
> Adaptive 평균 실험CPU35.5253%·누적CPU33.1255% 감소(Full 대비,25회씩 평균). 40%목표 미달.
> Sector도25/25·접촉0이므로 이 Normal 결과만으로 Adaptive 안전우위 주장 불가.
> 메모리급증은 미재현했지만 원인함수확정/영구해결로 표현 금지; 방어거절 분기 실제발동0.
> 상세 §8.100 및 `docs/c24_normal_results_20260917.md`, 프로토콜 `docs/c24_normal_validation_20260917.md`.
> 정적+ON+OFF 실제116.36분. 원본자료/ON·OFF 분리보존, 현재단계n20미실행. push 없음.
> 현재 `results/c24_normal_validation_20260917/iteration01/status.json`, base-run18000.
> ON15 모두 완주·접촉0; N5 Full50.23초/main·command99.998862Hz. ON/OFF 합산 금지.

> [!IMPORTANT]
> **2026-09-16 C23: 비교 중단 — N3 Adaptive 메모리 급증. 현재 실행 중 캠페인 없음.**
> N1–N5=seed1/3/5/7/9, 본시험 OFF75회만 실행; n20 자동확장 없음.
> 새 요청은 비교 실험으로 해석하고 시간 +10%는 중단 조건 대신 결과 지표로 기록한다고 안내함.
> 아래 C22의 기존 엄격 기준 실패/데이터는 소급 변경하지 않음. 런타임·맵 변경 없음.
> iteration04의 hash-valid 정적검증5맵과 ON12회 재사용, N5 ON3회 추가 후 OFF75회.
> body-heading ON, 공통3worker/0.25초 유지. 주기50ms·센서·복구·측정 검사는 유지.
> **N5 ON 중단:** A51.29/F66.71초 완주·접촉0이나 Full main FSM97.586Hz<98Hz.
> odom 최대17.97ms/command100Hz는 통과. 실패/ON2회 보존; N5 Sector와OFF15회 미실행.
> 사용자에게 FSM 미달도 결과로 기록하며 비교할지/먼저 수정할지 질문, 아직 답변 대기.
> N1–N4 OFF60회 계획도 17시도에서 중단: 완주16, N3 Adaptive 자원중단1(접촉결과미확인).
> N3 Sector 2회차 접촉1회(최소정적여유−0.175m), 완주했으며 실패/접촉 회차를 대체하지 않음.
> N3 Adaptive own composed process RSS 약3.1→7.2GiB, MemAvailable1.41GiB로 보호중단.
> 배경부하로 단정/제외 금지. 한 스레드약94% 및 FSM진행멈춤, 원인함수미확정/미수정.
> 다음은 이 자원증가/진행정지 진단·수정 후 새 독립75회 권장. N5의FSM미달도 여전히미해결.
> 현재 상태 `results/c23_normal_n5_comparison_20260916/ready_maps/status.json`, 상세 `docs/c23_normal_comparison_20260916.md`.
> 중간표 `ready_maps/report_partial/summary_ko.md`, 본시험17시도와사전ON2회 분리.
> 75회/맵당5회 완료 또는 Adaptive100% 성공으로 표기 금지. 런타임 변경 없음. push 없음.

> [!IMPORTANT]
> **2026-09-16: C22 중단 — 시간 합격기준 사용자 선택 필요. 실행 중 캠페인 없음.**
> 최신 iteration04 ON N1–N4 12회 모두완주·접촉0·주파수/속도/자원/복구통과.
> 단N4 Full39.64/A43.97초(+10.92%)로 기존쌍별+10% 기준만초과(0.366초 차이).
> N5 비행미실행, 요청OFF pilot75/confirm300은아직0회. 완료했다고표기금지.
> body축통일후에도상대시간변동남음. 새원인버그로단정하거나통과회차만골라반복금지.
> 비동기질문: +10%를필수기준으로유지할지/시간을비교지표로만기록할지. 답변미수신.
> 기준완화미승인. 승인시새프로토콜/n5로시작하고옛실패를합격으로바꾸지말것.
> 전체측정표 `results/c22_normal_five_20260916/iteration04/comparison_preflight/summary_ko.md`.
> Python119통과·런타임변경미러완료·기존Normal해시동일·비행프로세스없음. 기본옵션OFF유지.
>
> 이하 C22 진행 경과(과거시점):
> **최신: iteration03도 seed7 시간비1.1195로 중단(ON12회 모두완주·접촉0, OFF0).**
> Adaptive 관측축은 속도방향, Sector는 body방향인 비교조건 차이 발견.
> 기본OFF `SUPER_EVENT_BODY_ALIGNED_SECTOR=1` 추가: event Adaptive만 body방향으로 통일.
> 폭45도·planner·Full·제동/ACK/새경로 인증은 그대로. 기본동작과 이전자료 보존.
> seed7 ON진단 F47.30/S47.22/A43.03초·접촉0, A제동6→3관측. Full도회차변동커 인과확정아님.
> 새 전달/RViz 통과, C++일반/ASan+UBSan각60013검사·Python118통과.
> iteration04는body축+공통0.25초 후보로 전체정적/ON/n5를재시작. n20미실행.
> **갱신: iteration02 ON9회 모두완주·접촉0이나 seed5 A43.94/F37.83=1.162로 시간기준실패.**
> OFF n5/n20는0회. 원인 후보는 CLEARANCE_MARGIN 제동·재가속/경로차이;주기실패아님.
> 공통유예0.25초 진단ON3회 F40.55/S42.63/A42.75초·접촉0, A복구5→4이나 Full도느려져
> 원인해결확정아님. iteration03에서0.25초 후보 고정 후 전체 사전검사/pilot부터 재시작.
> N1–N5=seed1/3/5/7/9, 초기 후보는 C21 공통3worker 그대로. 맵·planner 변경 없음.
> 실행기/정적검증/CPU 관측기의 seed1 고정 경로를 맵별로 수정, Python116검사 통과.
> 맵별 전달6조건+실제RViz 후 ON15회, OFF pilot75회; 전부통과할때만 별도 OFF300회.
> 실패 보존·자동재시도/실패대체 금지; 수정 시 새 iteration에서 pilot부터 재시작.
> 현재 `results/c22_normal_five_20260916/iteration04/status.json` 확인.
> iteration01은 과거 시간참조 검사 오류로 시험/비행0회 종료. 과거 seed9 Sector접촉1회는
> 삭제하지 않고 시간중앙값 계산에도 포함. 현재 안전·50ms·시간비1.10 기준은 그대로.
> CPU 평균/누적, 메모리, GPU장치전체, 포인트/논리payload, 주파수, 전환/인증 모두 보존.
> 상세 `docs/c22_normal_five_20260916.md`, §8.98. 본캠페인 합격·40%달성으로 표기 금지.

> [!IMPORTANT]
> **2026-09-16: C21 3-worker seed1 각5회 검증 통과(4단계 완료).**
> C20의57.57ms 실패 보존. 시각연결계측 추가 후2-worker Full진단3회에서는 미재현.
> 통제executor시험은 두 blocking callback 동시점유시2worker110.18ms/3worker10.31ms를
> 보였으나 과거실패 원인의 확정 재현은 아님. 예방적으로 세모드 공통 side worker2→3.
> planner/맵/센서/안전/주기는 그대로. trace기본OFF,프로파일ON과OFF집계분리.
> 전달6조건+실제RViz통과. ON3회와OFF15회 모두완주·접촉0,재시도·실패대체0.
> **OFF Full/Sector/Adaptive 각각5/5; odometry max17.73/14.78/16.09ms로50ms 기준통과.**
> 평균시간38.152/39.320/38.452초,평균CPU .538817/.352015/.370185코어.
> Adaptive 평균CPU31.30%·누적30.90%감소. 9801은27.88%로매회30%충족아님;40%미달.
> A Full복구2/1/2/1/1회 총7/7인증완료;전체품질gate true,시간비모두1.10이내.
> Python107 및 인증함수추출 일반/ASan+UBSan각1403검사 통과.
> 결과 `results/c21_callback_timing_20260916/validation_3workers/verification.json`,
> 전체비교 `results/c21_callback_timing_20260916/comparison/summary_ko.md`, 상세 `docs/c21_callback_timing_20260916.md`, §8.97.
> 기존실패/Normal/Stress보존·합산금지. seed1유한표본이며hard real-time/전체맵보장아님.
> 다음은공통3worker후보동결후Normal대표5맵소규모검증. 이번엔seed1만,로컬커밋만/push없음.

> [!IMPORTANT]
> **2026-09-16: C20 인증 교체 경쟁 수정 완료, seed1 반복검증은 주기 실패로 중단.**
> 최신 인증 덮어쓰기 방지·VERSION_CHANGED 최대1회 재검사(진입후4ms 협조적예산),
> 실제 기하 실패/시간초과는 정지 유지. 첫 검사에 새 시간제한/안전완화 없음.
> 실제함수추출 일반/ASan+UBSan각1403검사(300thread교차),Python135검사 통과.
> 새 전달6조건+실제RViz통과. ON3회와OFF8회 모두완주·접촉0,비행재시도0.
> **OFF run9603 Full odometry max56.99/57.57ms >50ms로STOPPED_FOR_DIAGNOSIS.**
> 각5회계획 중Full3/Sector2/Adaptive3만실행,7회미실행. 완료·합격이라고 쓰지 말 것.
> OFF평균F38.523/S39.735/A38.390초;CPU .523683/.350560/.357059코어.
> A 평균CPU31.82%,누적31.13%감소는불완전표본의관측값이며40%달성/품질합격아님.
> 실제로그최신인증재사용4/추가검사SAFE1건;회피충돌횟수아님. A복구2/1/1회모두완료.
> 실패한Full은추가검사0회. PSI0/FSMswap0. 최대간격발생시각이기록되지않아
> executor경합/외부부하/재계획지연중원인미확정. 다음은시각연결계측후재검증.
> 결과 `results/c20_certificate_refresh_20260916/` 및 `docs/c20_certificate_refresh_20260916.md`, §8.96.
> 최상위status는ROS환경미source에따른비행전실패;실제비행status는validation/status.json.
> 기존C19/Normal/Stress보존·합산금지. 런타임C20유지,대규모시험중단,로컬커밋만/push없음.

> [!IMPORTANT]
> **2026-09-16 17:52 KST: CPU 귀속 보완·seed1 진단·맵 목록 고정(요청1–3단계) 수행.**
> planner 알고리즘/안전/주기는 그대로, 기본OFF frontend/map CPU scope만 추가.
> 새바이너리6전달조건+실제RViz통과. ON/OFF F/S/A각1회,총6회모두완주·접촉0,재시도0.
> 단OFF Adaptive43.75초/Full37.67초=1.1614로 **시간비1.10기준미통과**.
> OFF평균CPU F.530831/S.348768/A.368413코어; A평균30.60%,누적21.49%감소.
> Adaptive복구 ON1회/OFF4회(모두완료);추가2건은검증중경로commit과VERSION_CHANGED가겹침.
> 평균CPU만보고합격처리금지. 실행COMPLETE와별개로verification.json의전체검증판정false.
> 순수autonomy전체CPU는여전히독립측정불가;계측exclusive소계와공통/미분류범위를분리함.
> Normal N1–N5=seed1/3/5/7/9. 새원기둥Stress c19_cyl_probe_s1–s5는
> **기하만검사한동결탐색후보(비행0회)**,성과검증완료맵아님. 맵당20회캠페인미실행.
> 결과 `results/c19_cpu_attribution_20260916/`, 맵 `results/c19_map_suite_20260916/`.
> 상세 `docs/c19_cpu_attribution_and_map_freeze_20260916.md`, §8.95;136Python검사통과.
> 기존OFF n5/Normal자료보존·새진단과합산금지. 다음은시간초과/버전교체경쟁확인후map-aware검증.
> 런타임변경은SUPER에서수행후미러링;로컬커밋만,push없음.

> [!IMPORTANT]
> **2026-09-16 16:52 KST: C19 고정·비프로파일 seed1 3모드 각5회 검증 완료.**
> 사용자가 약30% 절감 후보의 반복검증과 전체 연산량 비교를 승인했다.
> planner/센서 코드·설정·바이너리는run9320과동일;비교실행기/집계기만보완.
> ON사전3회는별도보조자료, OFF본시험15회는 F/S/A각5/5완주·접촉0,재시도0.
> CPU평균 F.53450/S.34756/A.35144코어; Full대비Adaptive평균34.25%,
> 누적32.87%감소. 주행37.808/38.288/38.682초(A+2.31%). 맵갱신60.08%,
> 포인트70.83%,논리payload70.79%감소; GPU/메모리는뚜렷한절감없음.
> 쌍별CPU절감27.08~38.61%이므로매회30%/모집단100%보장아님. 40%달성아님.
> Adaptive매회Full활성화1/복귀1/인증복구1,미완료0. Sector도전부완주해안전성우위증거아님.
> 전체20논리CPU분모와실험범위/배경전체CPU를구분; composed이므로순수autonomy CPU는N/A.
> 결과 `results/c19_frozen_seed1_validation_20260916/comparison/`,
> 설명 `docs/c19_frozen_seed1_validation_20260916.md`;129Python검사통과.
> 옛Normal5는10seed의5쌍조건,옛Stress5는벽/dropout;새원기둥Stress5미확정.
> 확대전실제맵목록과map-aware계측·전달·timing검증필요. 과거자료합산금지;push없음.

> [!IMPORTANT]
> **2026-09-16: seed1 Adaptive CPU40% 최적화 탐색을 새로 시작함.**
> 사용자가 알고리즘/planner 수정을 허용했고, 목표는 평균 실험CPU Full대비40%
> 이상감소(누적CPU별도보고)로 명시했다. 기존v2/Normal결과는보존한다.
> 새실험은 `docs/adaptive_cpu40_seed1_20260916.md`와
> `results/adaptive_cpu40_20260916/` 참조. 첫후보는frontend→map까지 직접
> SharedPtr전달하는별도실행파일+opt-in thread CPU계측이다. C1~C18 각각
> F/A n1 완료·접촉0. C5(run9306)41.59/43.96초,평균CPU0.920618/
> 0.776242코어; 평균15.68%,누적11.58%감소. **40%미달**이다.
> C4 단일snapshot/C5 정확한이웃검사cache로 공통병목은줄었지만상대절감은제한적.
> C6 4thread/C8 static전용executor는각각14.62/18.05%절감,주행시간비1.10초과로미채택.
> C7 guarded-demand는34.34%절감관측이나 Full 초기복구표시잔존으로 Full에서
> 최적화미작동(0skip): 공정한최적화비교로채택금지. C9(run9310)수정후
> F36.88/A38.72초·접촉0,양쪽skip작동; 평균18.69/누적14.23%감소로40%미달.
> C10 2worker+static전용executor:평균26.30%,누적20.27%감소,실측주기검사통과.
> C11 선택적optimizer메모리진단OFF:평균24.88%,누적22.89%감소,두모드완주·접촉0.
> C12 공통demand최대dispatch간격0.5초: F37.48/A38.48초·접촉0,
> 평균26.29/누적26.40%감소. 매틱안전증거검증유지, **아직40%미달**.
> C13 초기5.1초1ms이후100ms:평균26.58/누적28.54%감소,정적executor약0.001코어.
> 그러나late-reader전달검사기존/후보모두실패:CPU진단전용·미채택,기본값OFF.
> C14 legacy1ms복귀+명시적동일명령ID합치기: F37.54/A39.65초,접촉0,
> 평균26.98/누적22.89%감소. F34/A33회재전송합침,모든비행/주기/복구감사통과.
> fresh사용자명령/정지·복구재시도보존. C15 headless파라미터서비스옵션:
> F37.68/A40.54초·접촉0,평균32.23/누적28.64%절감,모든검사통과·아직40%미달.
> C16 frontend전용executor: F37.82/A40.92초·접촉0,평균32.89/누적27.43%절감,
> 모든감사통과. n1에서뚜렷한개선없음·40%미달,기본OFF. 새스레드CPU도합산함.
> C17 정적맵executor만cached형식으로교체(1ms/QoS유지): F38.16/A38.42초,
> 접촉0·모든감사통과,평균28.17/누적28.20%절감. 상대성능개선못해미채택·기본OFF.
> 최고유효관측평균32.89%도계측n1탐색값일뿐40%달성/반복검증아님.
> C16복구3회는새맵CLEARANCE_MARGIN판정;인증서발행race라는근거없어guard유지.
> C18은사용자승인후static맵1회발행+실제RViz Reliable/TransientLocal동반전환을opt-in구현.
> Full첫전달검사실패원인은PCL미초기화패딩76바이트:좌표/강도동일확인후새wire꼬리만0처리,
> 원래전체SHA검사유지. 최종6전달시험+실제RViz재접속/화면검증통과,기존실패기록보존.
> run9319 F36.63/A37.82초·접촉0·모든검사통과,평균31.45/누적29.54%감소로40%미달.
> static반복호출0,새옵션/실사용프로파일기본OFF유지. 기존volatile구독자호환을주장하지않음.
> C19(run9320): CPU구간정렬분석/원시누적값·실제읽기시각추가,불필요한clearance면탐색만
> 기본OFF opt-in으로생략. Backup비활성제약미초기화진단값도별도0초기화(과거UB와동등주장금지).
> O3/ASan+UBSan각1792평가·131712출력비교통과,109Python검사/25.1초빌드/새6전달+RViz통과.
> Full37.61초/.525725코어/20.700615core-s,Adaptive39.00초/.358067코어/14.483161core-s,
> 각각1회완주·접촉0·모든감사통과. 평균31.89/누적30.04%감소,40%미달·비계측확인없음.
> C18대비+0.44%p는n1변동과분리불가. 작은계산생략만으로40%달성주장금지.
> 다음은Adaptive추가콜백·공통ROS실행/재계획비용의실제귀속확인. 안전/주파수완화금지.
> C13의100ms전환prototype은전달검사실패로사용금지;legacy기본1ms유지.
> 모든옵션기본off/원래값유지. 계측켜진후보만으로40%달성판정금지(비계측확인필수).
> Full새관측→정확한맵ACK→새안전경로gate유지.
> 새탐색결과를기존수백회검증과합산금지. 기존Stress search재개아님. push없음.

> [!IMPORTANT]
> **2026-09-16 02:30 KST: 센서 생성단 Sector/Full 전환 v2 구현·seed1 시험 완료.**
> 사용자가 요청한 것은360도 수신 후 필터링이 아니라 처음부터 Sector 스캔
> 생성/출력이었다. 아래 v1은 그 입력단 요구를 충족하지 않았으며 결과 재해석 금지.
> 새 opt-in은 렌더러 projection/viewport/readback/conversion부터 Sector225열,
> Full900열로 전환한다(센서 좌표계±45도, 근거리전방위예외0,0.4도·10Hz).
> 프런트엔드는 typed 생성모드/회차를 확인하고 그대로 전달하며, 이전모드 스캔
> 1개를 차단했다. 실제 GPU16스캔 각도/광선/맵표면검사, ROS10검사·Python24검사
> 및 C++gate검사 통과. 초기2개 renderer test 실패는 테스트 맵경로 오류로 보존.
> 새 별도 Full도 동일한 스캔 시작stamp/버퍼교환 전 readback으로 비교했다.
> **seed1/v7 F/S/A 각1회 모두완주·접촉0·retry0:60.39/65.22/66.37초.**
> A는 실제Full획득9회/새관측맵ACK·새경로검증후Sector복귀9회. 센서로그707프레임
> 중Sector630/Full77. CPU101.021/87.916/89.552core-s, A누적CPU11.35%감소이나
> 시간5.98초증가. PC전체 배경포함CPU는20.71/19.91/21.00%로 A가 줄지 않았다.
> 코드/검증저장`6a2e476`, 원자료`results/sensor_acquisition_seed1_n1_20260916/`,
> 상세`docs/sensor_acquisition_v2_20260916.md`, viability §8.92. 기존profile/data보존.
> 시뮬레이터의 가변시야 센서 모델이며 실제LiDAR 지원/지연/동역학보장 아님.
> 과거v1/Normal300과 합산 금지. 현재비행종료, Stress search중단유지, push 없음.

> [!IMPORTANT]
> **2026-09-16 01:53 KST: Event-only Adaptive 별도 구현 및 seed1 F/S/A 재시험 완료.**
> 사용자가 요청한 정상 Sector→정체/안전정지 시 Full→새 관측의 정확한
> committed ACK→새 실행궤적 안전인증→Sector 복귀를 opt-in으로 구현했다.
> 경로 미확보 시 기존 제동/terminal hold를 유지하며 타이머만으로 복귀하지 않는다.
> 기존 소스/설치 바이너리는 로컬 archive로 보존, 기존 YAML/Normal300 그대로.
> 최초 prototype은 정상 최적화 실패까지 제동하여 A80.84초/44회 전환; 코드와
> 결과를 `4cc4a0b`로 보존한 뒤, 유효한 기존 경로 진행 중 실패만으로 멈추지
> 않도록 수정했다. 별도 run9102 F/S/A 각1회 모두 완주·접촉0·retry0:
> 61.39/61.18/59.73초, CPU105.369/84.772/86.124 core-s.
> 새 A는 Full2회/Sector복귀2회 모두 정확한 맵반영·새 generation 인증 확인.
> ROS 통신10검사+순수C++ gate검사+Python24검사 통과. 실제 무경로 비행은 미시험.
> **센서360도10Hz 생성은 그대로; raw-risk 상시평가 없이 frontend 선택/전환 변경.**
> 원자료 `results/event_recovery_seed1_corrected_n1_20260916/`, 상세
> `docs/event_recovery_v1_20260916.md`, viability §8.91. n1이고 기존300회와 합산 금지.
> 현재 이 시험 종료; 이전 Stress search는 여전히 중단 상태다. upstream push 금지.

> [!IMPORTANT]
> **2026-09-16 00:15 KST: Normal seed1 CPU/GPU/스레드 진단3회 완료.**
> 사용자 요청으로 기존 설정 그대로 F/S/A 각1회(run9001), 모두 완주·접촉0,
> quality-valid·retry0. PC전체 CPU 평균21.81/19.83/20.69%, 실험 cgroup의
> 전체20논리CPU 대비 점유율8.03/6.77/7.13%를 별도로 확인했다. 독립
> 프로세스 합산과 cgroup CPU의 상대차이0.52/0.45/0.39%. GPU전체 평균
> 46.69/49.31/49.52%이나 비행 전부터45.82/49.92/49.92%여서 모두를
> 실험 GPU 부하로 귀속하면 안 된다. 기존 Normal300과 합산하지 않는다.
> 원자료 `results/normal_cpu_gpu_diagnostic_20260916/`, 해석은
> `docs/normal_cpu_gpu_diagnostic_20260916.md`. 소스/자산279해시 그대로.
> **이전 Stress 제어기는 Sep15 23:10에 L0010 A run3 메모리 부족으로 중단.**
> MemAvailable1331.7<2048MiB, infrastructure-invalid 원자료 보존. 이번
> CPU 진단에서 재시작하지 않았다. 아래 RUNNING 표시는 과거 시점이다.

> [!IMPORTANT]
> **2026-09-15 21:30 KST: 실패 후보 보존→새 설계 추가→다음 실제 비행 확인.**
> K02~K06은19:17에42행으로 끝났다. Full14/14, Sector11/14, Adaptive13/14,
> 모든 solid 접촉0. K06 Adaptive 실패로 마지막3행 미실행; 후보5개 완료를
> 전체 작업 종료로 취급한 운영을 정정한다. K02/K03/K06 Sector는 원점 근처
> 마지막 leg에서111~118초 입력 정체. K06 Adaptive는 ACK정상/A* timeout.
> **L0001=K02+원점 주변13개(총549개)** 진단9/9 정상 종료.
> Full/Sector/Adaptive 각3/3 완주·접촉0이라 차이 목표 미달로 보존·제외.
> 새로운 `cylinder_feedback_search.py`는 진단→별도표준개발→새n20를 연결하고,
> 실패/차이없음→새배치를 자동으로 계속 생성한다. 종료 목표는 적격n20맵5개,
> 후보횟수 제한 없음. 단순 빈입력 정지를 성과로 세지 않는다. 기존 결과보존.
> PID2400625/session83171이 L0001 결과 채택→L0006 변형 recipe 추가→
> L0002 생성·미러링→Full run1 실제 비행까지 자동 진행했다. 목표 맵 아직0/5.
> 후속 L0002는 F0/1·S1/1·A1/1 완주, 모두 접촉0. Full은 ACK정상이나
> (12.5034,19.1428)에서 A*timeout 반복으로180초 제한. 실패 보존 후
> 정지점 주위4 m를 여는 L0007 recipe 자동 추가. 현재 K06 실패 재설계인
> L0003(518개)의 Full run1 실제 비행 진행 중. n20 통과 맵은 여전히0/5.
> 집중45테스트 통과. 소스/완료 원자료 로컬 저장`25a9471` 및 후속 자산 커밋.
> 동시비행 금지, 취소/invalid 종료는 보존·중단. controller 실제 상태는
> `results/cylinder_feedback_search_20260915/{handoff_status,status}.json`을 볼 것.
> 상세규칙/원인: `docs/cylinder_persistent_feedback_20260915.md`.
> 알고리즘/planner/센서 변경 없음, push 없음. 아래5맵bounded 종료 규칙은 과거다.

> [!IMPORTANT]
> **2026-09-15 18:01 KST: 사용자 요청으로 배경 고정 후보5개 K02~K06 생성 완료.**
> 내부 열 복원/크기 증가/간격 축소/대형 지그재그/코너 직후 원기둥의5개
> map-only 변형이다. 외곽126개와 기존 배경·레일, runtime 정책은 유지했다.
> 원기둥 수536/536/576/440/519, 오프라인 body 여유최소0.45 m 이상.
> 미러·설정·동결hash 확인, 집중 테스트25개 통과. 아직 성과 맵5개가 아니다.
> 첫15회(각맵 F/S/A) 후 기준모드 안전 완주 후보만각3회까지, 최대45회.
> **18:05 KST 후속: PID2268162/session72038로 실제 실행 중.** K02 Full run1
> 97.17초 완주·접촉0, Sector run1 진행. 맵/실행기 저장커밋`eb792a2`, push 없음.
> 진단 전용/단일 비행/실패보존, 자동 n20 시작 없음. 이전 J/K01 실행기는 종료.
> 후속실행 여부는 `results/cylinder_background_five_20260915/status.json`과
> 실제 PID를 확인할 것. 설계/중단규칙: `docs/cylinder_background_five_maps_20260915.md`.

> [!IMPORTANT]
> **2026-09-15 17:46 KST: K01 배경 원기둥 진단9/9 완료, 현재 비행 없음.**
> Full/Sector/Adaptive 모두3/3 완주·solid 접촉0, 평균83.92/76.60/83.02초.
> J05+외곽126개 원기둥(총515개), 알고리즘/센서/정책 변경 없음. Sector의
> 목표 도착까지 ACK 최대간격은0.3434초로 장시간 입력 부족 정지는 재현되지
> 않았다. **Sector도 전부 완주하여 Stress 차이 목표는 미달**, n20로 확대하지
> 않는다. 추가 observer 진단 결과라 기존n20/CPU 비교에 합산 금지.
> 종료 꼬리를 포함한 원래 ACK 집계와 사후 도착시각 한정 집계를 모두 보존했다.
> 13테스트 통과, 동결/자산280해시 일치. 기존 J05 보존, J08은58/60 미완료.
> 이전 제어기/J08/K01 프로세스는 모두 종료, Pylance2245516만 재색인 방지
> 일시정지 상태. GitHub push 없음. 다음은 배경 고정+안쪽 원기둥 map-only
> 위험 배치 탐색이며 현재 자동 실행 중인 후속 시험은 없다.
> 결과/해석: `docs/cylinder_background_liveness_diagnostic_20260915.md` 및
> `results/cylinder_background_diagnostic_20260915/cyl2_k01/summary.json`.
> 아래 시각별 배너의 실행 중/준비 상태는 과거 기록이다.

> [!IMPORTANT]
> **2026-09-15 17:32 KST: 메모리 확보 후 K01 배경 관측 진단 실행 중.**
> 사용자 승인으로 Pylance 종료, 자동 재시작 프로세스2245516은 재색인 전
> 일시정지했다. 편집/대화/실험은 유지. J08은 resource preflight600초 timeout,
> 실제58행 보존(Full19/19, Sector0/20, Adaptive19/19), **20회 완료 아님**.
> 기존 제어기는 종료됐고 J09는 실행하지 않는다. J05는 그대로 보존.
> K01(J05+외곽126개,총515개)은 생성·미러링 완료. 진단PID2244976으로3모드
> 각3회 진행, Full run1은67.19초 완주·접촉0/ACK 최대간격0.1255초다.
> 최신 파일: `results/cylinder_background_diagnostic_20260915/cyl2_k01/status.json`.
> 추가 ACK observer가 붙은 진단 결과라 기존 n20/CPU비교에 합산하지 않는다.
> 상세: `docs/cylinder_background_liveness_diagnostic_20260915.md`.

> [!IMPORTANT]
> **2026-09-15 17:18 KST: Sector 입력 부족을 보완하는 map-only 진단으로 전환.**
> J05 보존. J08은58/60행이며 마지막2회 전 메모리 preflight 대기 중이다.
> 부모제어기1935342는 SIGSTOP 상태라 J09를 시작하지 않는다. 자식2143724는
> 현재 J08만 마무리하도록 둔다. 새 K01은 J05+외곽126개 원기둥(총515개)
> 설계이며 생성기/진단11테스트 통과, **아직 자산 생성·비행 전**이다.
> 사용 가능 메모리<7168 MiB라 Pylance 임시 종료 권한을 사용자에게 질문했다.
> 코드/센서/ACK retry 설정은 그대로다. 후속 지침과 대기 프로세스 정보:
> `docs/cylinder_background_liveness_diagnostic_20260915.md`.
> 오래된 status.json RUNNING만 보고 부모가 실행 중이라고 답하지 말 것.

> [!IMPORTANT]
> **2026-09-15 16:54 KST 사용자 결정: map-only 선정 환경 평가 유지.** J05는
> 새20회/모드에서 Full20/20·Adaptive20/20·Sector0/20 완주, 모두 접촉0으로
> 보존한다. J02/J03/J04/J06/J07은 최종 후보에서 제외하되 실패 원자료와 맵
> 자산은 삭제하지 않는다. J08은 현재 각16회(48/60행), Full/Adaptive 전부
> 완주·접촉0, Sector 전부 미완주·접촉0이며 제어기PID1935342가 계속 실행 중.
> **J07은 원점에서 exact full-refresh ACK를 받지 못한 복구 대기 실패**다.
> 재요청 옵션0/off를 포함해 코드·실행설정은 변경하지 않기로 했다. 맵 선택은
> 결과 의존적 탐색이며, 성공 맵 선정이 이 복구 한계를 해결했다는 뜻은 아니다.
> 상세 결정/한계/보존 범위: `docs/cylinder_selected_environment_protocol_20260915.md`.
> 아래의 ‘통과맵0개’/‘J03진행중’은 과거 시점이다. 최신 진행은 status.json 참조.

> [!IMPORTANT]
> **2026-09-15 후속: J03 개발3묶음 통과 → 새 n20 실행 중.** Full3/3
> (89.35/91.38/89.83초), Adaptive3/3(67.89/71.10/71.54초) 완주·접촉0,
> Sector0/3 완주·접촉0. 개발9행은 확인 표본에 합치지 않는다.
> `results/cylinder_confirmation_n20_20260915/cyl2_j03/`의 새run101--120/모드
> 확인이 시작됐다. 반복 실행기PID1935342가 살아 있으며, 기준모드 실패는
> 보존·탈락 후 다음 사전 선언 변형으로 진행한다. **n20 성공맵은 아직0개.**
> 실시간 상태는 `results/cylinder_refinement_repeat_20260915/status.json`.
> 그 파일의 run은 개발묶음 번호이고, 확인회차는 해당맵 확인raw.csv를 볼 것.

> [!IMPORTANT]
> **2026-09-15 10:46 KST: J02도 Full 접촉으로 탈락, 자동으로 J03 시험 중.**
> J02 개발run2 Full은70.96초 완주했지만 solid/static-PCD/safety 접촉이
> 각각1회라 탈락했다. odometry의 약10 ms 간격에서5.378 m 위치 불연속과
> 기둥 내부 도착(-0.247 m solid 여유)을 확인했다. 접촉을 invalid/retry로
> 지우지 않았다. 런타임/센서/시뮬레이터 동작은 수정하지 않는다.
> J03(원본J01의 leg3·4 끝 기둥1개씩 제외,398개)은 개발run1 Full89.35초/
> Adaptive67.89초 완주·접촉0, Sector180초 실패·접촉0. 현재개발run2다.
> 반복 실행기PID1935342, live상태 `results/cylinder_refinement_repeat_20260915/status.json`.
> 아직 최종20회 통과맵은0개다. 아래단일개발성공을 최종성공으로 읽지 말 것.

> [!IMPORTANT]
> **2026-09-15 10:33 KST: map-only 반복 실행기로 연결.** J02 개발run1은
> Full77.34초/Adaptive77.70초 완주·solid접촉0, Sector180초 WP1/5 실패·접촉0.
> 아직 n20 성과가 아니다. `repeat_cylinder_refinements.py`가 J02의 기존
> 개발행을 보존하면서3묶음→새20회/모드로 진행한다. 기준모드 실패 시
> 해당 맵을 탈락시키고 J03 이후 사전 선언된 기둥열 완화 배치를 시험한다.
> 목표는 새20회 조건 통과5개 맵.10개 변형 소진/계측오류는 성공이 아니라
> 진단·새 설계 필요 상태다. 단일 비행만 실행하며 알고리즘/센서/mission은
> 동결한다. live 상태: `results/cylinder_refinement_repeat_20260915/status.json`.
> J01 확인18/60 탈락을 유지한다. 상세는 viability §8.84 및 cylinder 정정 문서.

> [!IMPORTANT]
> **2026-09-15 10:20 KST: J01 확인 시험 탈락, map-only 반복 재개.** 새
> 확인18/60행에서 Full6/6, Sector0/6, Adaptive5/6 완주/전부 solid 접촉0.
> Adaptive run106의 유효한 완주 실패로 사전 선언한 묶음 경계 중단이
> 04:32 KST에 실행됐다. **n20 완료/목표 달성이 아니다.** 네 번째 leg의
> (0.995,-21.430,1.729) 부근에서 최적화 실패/시간초과와 reroute/A-star
> timeout/epoch reset이 반복됐다. J02는 해당 leg 교차 열의 끝 기둥6개만
> 제외한404개 배치다. 나머지 원기둥/센서/미션/275개 runtime hash 동일.
> 원본 J01 및 실패18행 보존, J02 Full-first 개발 시험을 시작한다.
> 상세: `docs/cylinder_solid_measurement_correction_20260915.md`.

> [!IMPORTANT]
> **2026-09-15 03:49 KST: J01 개발3묶음 통과, 새 n20 진입.** Full 3/3,
> Adaptive 3/3 완주, Sector 0/3 완주이며 9행 모두 solid 접촉0/quality-valid.
> Adaptive run2는160.13초로 변동성이 크다. **20회 결과가 아니다.** 새
> run101--120/모드 총60회를 `--min-development-runs 3
> --stop-on-reference-failure`로 실행한다. 기준 모드 실패 시 현재 묶음을
> 끝내고 탈락하며 실패 표본을 지우지 않는다. 원자료:
> `results/cylinder_confirmation_n20_20260915/cyl2_j01/`.
> J01 하나만 적격이며 5개 성공 맵을 확보한 것은 아니다. 관측된 차이는
> empty filtered cloud/MAP_STALE에 따른 완주 차이로, 충돌 방지 우위가 아니다.

> [!IMPORTANT]
> **2026-09-15 03:31 KST: J01 개발 run1에서 실제 결과 분리.** Full
> 115.19초/Adaptive 90.26초 완주·solid 접촉 0, Sector 180초 WP3/5
> 실패·접촉 0. 전부 유효한 단일 실행이다. **아직 최종 성과/n20이 아니다.**
> J01은 410개 정적 원기둥 중 교차 열 120개(24열), 모든 반경 0.4 m/
> 높이 3 m다. Sector는 WP3 도착 뒤 empty filtered cloud/MAP_STALE로
> 정지했다. 완주/liveness 차이이지 충돌 방지 우위의 증거는 아니다.
> 개발 run2/3을 추가하고 기준 모드 전부 안전 완주 시에만 새 n20을 시작한다.
> 아래 H05/H11의 실패도 보존하며 알고리즘/runtime 275개 hash는 그대로다.

> [!IMPORTANT]
> **2026-09-15 03:18 KST: 최종 성과 후보는 아직 없다.** H11도 세 번째
> 개발 Full에서 timeout으로 탈락했고 D08 Full 역시 실패했다. D09는 세
> 모드 모두 완주/solid 접촉 0이므로 목표 미달이다. 별도 초기 cloud 진단에서
> D09 Sector의 초기 정지 cloud는 실제 sector 범위 내였으며, 해당 진단은
> 비교 표본에 합치지 않는다. F05는 교차 원기둥 간격을 3.6 m로 좁힌
> map-only 후속 후보다. Planner/Adaptive/센서/미션과 275개 runtime hash는
> 그대로다. H05 확인은 여전히 **중도 탈락 6/60행**이지 n20 완료가 아니다.
> 상세/원본 경로: `docs/cylinder_solid_measurement_correction_20260915.md`.

> [!IMPORTANT]
> **02:15 KST 후속: H05는 6/60행(모드별 2회)에서 중도 탈락.** Full 0/2,
> Sector 2/2, Adaptive 1/2 완주, 전부 solid 접촉 0이다. Adaptive도 같은
> 구간에서 실패한 추가 증거를 보고 실행 계획을 변경했다. 사용자 답변을
> 받았다고 가정한 것이 아니며, 목표 충족이 불가능한 맵의 남은 확인 시험을
> 중지하고 map-only 탐색으로 돌아간 내부 작업 순서 변경이다. 진행 중인
> 비행은 끊지 않고 두 번째 3-mode 묶음이 모두 저장된 경계에서 종료했다.
> `boundary_stop.json`과 6행을 보존한다. **20회 완료/최종 성공이 아니다.**
> 원래 runner의 기본 옵션으로 같은 freeze/행에서 60회를 재개할 수 있다.
> 이후 후보는 개발 3묶음에서 Full/Adaptive 전부 안전 완주 + Sector 실제
> 실패가 있어야 새 n20에 진입한다. 향후 n20은 reference 실패 시 현재
> 묶음까지 완료 후 중도 탈락하는 규칙을 시작 전에 freeze한다.
> H11(원기둥 XY 270도 회전만 적용) Full-first 탐색을 시작했다.

> [!IMPORTANT]
> **02:05 KST 최신: H05 확인 시험에서 Full 실패.** 개발 run1의 첫 적격
> 결과가 반복 시험에서 유지되지 않았다. 새 run101은 Full 180.00초 timeout
> (WP 2/5), Sector 110.15초 완주, Adaptive 108.46초 완주이며 모두 solid
> 접촉 0/quality-valid다. H05의 요청된 Full 20/20 조건은 이미 불가능하다.
> 이 실패를 지우거나 run1 성공으로 대체하지 않는다. 원래 60회 실행기는
> 진행 중이며, 중도 탈락 후 새 배치 탐색으로 전환할지는 사용자에게 비동기
> 질문을 보냈다. 답변 전에는 원래 반복 계획을 유지한다. 현재 live 결과:
> `results/cylinder_confirmation_n20_20260915/cyl2_h05/result.json`.
> 아래 01:55 '개발 적격'은 최종 성과 달성이 아니다.

> [!IMPORTANT]
> **2026-09-15 최신 정정: 원기둥 내부 접촉 누락.** H01 Full은 기존 표면-PCD
> 계측상 접촉 0이지만 실제 저장된 위치가 원기둥 내부(부피 기준 body clearance
> −0.724 m)였다. unsigned 표면 거리와 monitor의 늦은 시작이 계측 결함이다.
> 기존 59회 raw는 보존했고 `solid_context_audit.json`에 희소 실제 3D 위치의
> 후향 점검을 별도로 기록했다. 과거의 0을 전체 비행 안전 인증으로 쓰지 말 것.
> Runtime 275개 hash/알고리즘/센서/simulator/원래 runner·monitor는 동결하고,
> 새 wrapper에서 simulator보다 먼저 읽기 전용 solid-cylinder observer를 시작한다.
> 이후 20회 진입은 **새 solid 관측이 유효한** 3-mode 실제 성과만 인정한다.
> 첫 F04는 Full/Sector/Adaptive 모두 완주·solid 접촉 0으로 목표 미달이다.
> H04도 세 모드 모두 통과해 목표 미달이다. H05 Full은 통과했고 나머지
> 모드를 시험 중이다. H08/H09/H10은 후속 후보, H06/H07은 기하학 사전
> 검사 미통과로 미비행이다. 아직 적격 맵/20회 캠페인은 없다.
> 최신 근거: `docs/cylinder_solid_measurement_correction_20260915.md`, §8.81,
> `results/cylinder_solid_map_search_20260915/`. 아래 옛 checkpoint보다 우선한다.

> **01:55 KST 후속:** H05는 Full 93.49초 완주/접촉 0, Sector 180.01초
> timeout(WP 4/5)/접촉 0, Adaptive 107.71초 완주/접촉 0으로 **첫 개발 적격**이다.
> 세 행 모두 새 solid 관측 및 quality-valid. 동일 맵의 새 run101--120,
> 각 모드 20회(60회) 확인을 시작한다. 결과는
> `results/cylinder_confirmation_n20_20260915/cyl2_h05/`에 별도 보존한다.
> 아직 n=20 성과 달성이 아니며 실패를 성공 재시도로 대체하지 않는다.

> [!IMPORTANT]
> **2026-09-15 사용자 정정 후 원기둥 map-only 탐색 재개.** 아래의 비행 중단
> checkpoint는 현재 작업 지시가 아니다. 사용자는 알고리즘과 simulator를
> 유지한 채 실제 결과로 `Full/Adaptive 완주·접촉 0, Sector 완주 실패 또는
> 접촉`이 나오는 배치를 찾으라고 명시했다. 제동 실패 로그만으로 이 조건을
> 대신하지 않는다. 적격 맵은 동결 후 각 모드 **새 20회**(60회/맵,
> run101--120)를 시험한다. 실패 행을 성공 재시도로 교체하지 않는다.
> 최신 규칙/진행은 `docs/cylinder_success_rule_n20_20260915.md`, 탐색 원본은
> `results/cylinder_map_search_20260914/`를 따른다. a02/a04도 비행을 마쳤고
> 세 모드 모두 완주·접촉 0으로 조건 미달이다. 01:09 KST checkpoint는 기존
> 포함 18개 비행 후보/48행이다. 15개 비교 맵은 모두 세 모드 안전 완주,
> d01/d02/g01은 Full timeout으로 탈락했다. f01은 원기둥 겹침으로 비행 전
> 제외했다. g02/g03 및 h01--h03의 Full-first 탐색을 이어가고 있다.
> 아직 적격 맵/20회 확인 성과는 없으며 실패·부정 결과를 모두 보존한다.
> Simulator command-loss 한계는 그대로이며 실기 동역학 안전 주장은 하지 않는다.

> [!IMPORTANT]
> **2026-09-14 후속: 사용자 요청은 원기둥 맵만 바꾸는 반복 탐색이다.**
> Planner/guard/Adaptive, v7, ±45도, loop24, nominal 10 Hz LiDAR를 동결했다.
> `cyl2_*`라는 새 이름으로 위치·배열·개수·반경만 탐색하며 기존 결과는
> 보존한다. 진행 기록은 `docs/cylinder_map_only_search_20260914.md`, 원본은
> `results/cylinder_map_search_20260914/`를 우선한다.
> 2026-09-15 checkpoint: 7개 후보/17회 완료. 5개 비교 후보는 세 모드 모두
> 완주/접촉 0, ring 2개는 Full timeout(WP 0/5 및 4/5)으로 탈락했다.
> **Sector의 두 맵에서 이동 중 brake rejection 후 명령 중단으로 simulator
> 위치가 고정되는 증거를 찾았다.** 따라서 접촉 0을 실제 제동 성공으로
> 해석하지 말 것. 알고리즘은 유지했고, simulator 동역학/command-loss 검증은
> map-only 범위 밖이므로 임의 수정 없이 추가 비행을 멈췄다. a02/a04는
> 생성만 한 미비행 후보다. 자세한 사건 시각은 `stop_audit.json`에 있다.
>
> 아래 v1 기록의 해석을 정정한다. radius 1.5 m trajectory audit는 실제
> 개별 원기둥이 아닌 cluster proxy였으므로 음수 값을 실제 충돌 궤적으로
> 해석하지 말 것. scan 부하 증가가 timeout을 야기했다는 독립적인 인과
> 검증도 없다. 센서 point-budget normalization은 이번 사용자 요청과 맞지
> 않아 시행하지 않는다. 실제 static-PCD 접촉/완주 결과는 그대로 보존한다.

> [!IMPORTANT]
> **2026-09-14 원기둥 전용 Stress 1--5 Full feasibility gate 실패.** 기존
> wall/dropout C1--C5가 사용자의 의도와 달라, planner는 동결하고 Normal처럼
> 수직 원기둥 410개만 쓰는 별도 family를 만들었다. 개발 seed5의 structure와
> 동일 raw-hash MARSIM/C++ replay는 통과했으며, 최종 짝수 seed2/4/6/8/10은
> 비행 전에 동결했다.
>
> Full first-attempt n=1에서 Stress 1--3은 접촉 0으로 완주했지만 Stress 4--5는
> 첫 waypoint 전에 정지해 180.01초 timeout이었다. 전체 접촉은 0/5, 완주는
> 3/5다. 원인은 analytic gate가 corner 이후 북쪽 bypass만 확인하고 inbound
> diagonal과 inner cylinder row의 교차를 놓친 것, radius 증가와 함께 scan
> point load가 약 16.3k에서 33k로 늘어 0.1초 A-star budget과 결합한 것이다.
> 판정은 `STOP_PAIRED_CAMPAIGN_FULL_FEASIBILITY_GATE_FAILED`; 이 이름들로
> Sector/Adaptive flight를 실행하거나 결과를 고르기 위한 Full 재시도를 하지
> 말 것. 계속하려면 새 v2 이름, inbound inflation/local-horizon route gate,
> point-budget normalization이 필요하다.
>
> 시작 전 static-PCD monitor의 XYZI→XYZ reshape 버그도 발견해 PCD
> `FIELDS`/`COUNT` 기반 loader로 수정했다. 비행 전 종료된 두 행은 별도
> infrastructure-aborted 파일로 보존했다. 최신 근거는
> `docs/cylinder_only_stress_full_gate_result_20260914.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-10 C4--C5 prospective extension 및 10조건 n=20 표 완료.** 기존
> R1--R5/C1--C3의 480행은 수정하지 않고, 결과 관측 전에 동결·push한 두 정적
> blind-fork(C4 deep mirror, C5 asymmetric offset)를 추가했다. 두 맵은
> actual-PCD structure, 동일 raw-hash paired MARSIM/C++ replay, Full feasibility
> gate를 모두 통과했다.
>
> 새 본 실험 120행은 모두 unique first attempt이고 retry/infrastructure/OOM 0,
> dropout phase/cadence/speed/resource/static-PCD gate가 유효하다. C4/C5에서
> Full과 Adaptive는 각각 맵별 20/20 안전, Sector는 4/20 및 3/20 안전이었다.
> 신규 합계는 Full/Adaptive 40/40, Sector 7/40 안전(접촉 32/40, 완주 36/40),
> paired 33:0, exact McNemar p=2.3283064365386963e-10으로
> `C4_C5_EXTENSION_OBSERVED`다.
>
> 최종 표는 10 reporting conditions x 3모드 x 20행 = 600행이다. C1--C5
> descriptive 합계는 Full/Adaptive 100/100, Sector 34/100 안전이지만 C4/C5는
> C1--C3 결과를 본 뒤 설계됐으므로 pooled 검정은 secondary다. 정상과 stress를
> 합치지 말고 100/100도 population 100%로 쓰지 말 것. 최신 근거는 viability
> §8.77 및 `docs/ten_condition_n20_result_20260910.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-10 8조건 n=20 표와 독립 stress 복제 완료.** 기존 Map1--10의
> paired layout을 절반 폐기하지 않고 장애물 반경 tier R1--R5로 묶었다(각각
> 2개 물리 맵 x 10회). Held-out C1--C3은 기존 block 1을 그대로 보존하고,
> 결과 관측 뒤 별도로 사전등록한 run11--20 block 2를 추가했다. 따라서
> 8개 reporting condition x 3모드 x 20행 = 480행이며, 8개 독립 물리 맵이라는
> 뜻은 아니다.
>
> 새 90행은 전부 unique first attempt이고 retry/infrastructure/OOM 0,
> phase/cadence/speed/resource/static-PCD gate가 모두 유효하다. Block 2에서
> Full/Adaptive는 C1/C2/C3 각각 10/10 안전, Sector는 3/10, 5/10, 6/10
> 안전이었다. Paired discordance 16:0, exact McNemar
> p=3.0517578125e-05로 `STRESS_REPLICATION_OBSERVED`. 합산 stress n=20은
> Full/Adaptive 60/60, Sector 27/60 안전이며 합산 검정은 사후 선택 때문에
> secondary다.
>
> 정상 R1--R5에서 Adaptive는 Full 대비 planner ingress 77.14%, map compute
> 39.28%, 공정한 end-to-end CPU 12.75%, core-seconds 14.45% 감소했다. Stress
> C1--C3에서는 70.70%/29.35%/6.01%/2.12% 감소하고 시간은 5.30% 늘었다.
> 정상과 stress 지표를 합치지 말고, 20/20도 population 100%로 쓰지 말 것.
> 최신 근거는 viability §8.76 및
> `docs/eight_condition_n20_result_20260910.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-10 사전등록 held-out 10 Hz burst-dropout 확인시험 통과.** H9
> 탐색 결과와 분리해, 결과 관측 전에 정적 blind-fork 3개(C1 mirror, C2
> wide-offset, C3 near-short)와 공통 10 Hz 센서의 0.5 s/2.0 s burst loss,
> 10개 paired phase를 동결했다. Planner/v7/45° Sector/Adaptive 정책은 바꾸지
> 않았고 fault injector는 기본값 false이며 DDS/direct Full/direct frontend보다
> 앞에서 동일 frame을 억제한다.
>
> Actual-PCD, 동일 raw-hash paired MARSIM/C++ replay, fault integrity, Full
> feasibility를 모두 통과했다. 새 90행에서 Full/Adaptive는 맵별 10/10,
> 합계 30/30 안전 완주했다. Sector는 맵별 안전 완주 4/10, 4/10, 5/10이고
> 접촉 6/10, 6/10, 5/10이었다. 대응쌍 discordance 17:0, exact McNemar
> p=1.52587890625e-05로 판정은 `CONFIRMATORY_TRANSFER_OBSERVED`다.
>
> Adaptive는 Full 대비 공정한 end-to-end CPU 7.44%, planner ingress 71.02%
> 감소했고 effective Full-open은 평균 1.20회였다. 단, 이는 3개 held-out
> simulation stress의 유한 표본 결과다. Population 100%, 실환경 보장,
> nominal Map1--10 효율 결과로 과장하지 말 것. 최신 근거는 viability §8.75와
> `docs/static_burst_dropout_confirmation_result_20260910.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 static heading-mismatch h9에서 첫 안전성 분리 확인.** Planner와
> 정책은 동결했고, 정적 two-branch 맵에서 공통 LiDAR만 2 Hz로 낮춘 severe
> dropout-equivalent stress다. Actual MARSIM/C++ replay에서 동일 raw hazard
> 23,167점/conflict 499점 중 Fixed Sector는 전부 제거, Adaptive는 전부 보존하고
> fresh OCCUPIED 10회 연속을 냈다.
>
> 새 rotating-order n=10에서 Full/Adaptive는 각각 10/10 안전 완주, Sector는
> 9/10 접촉(안전 완주 1/10), exact paired McNemar p=0.00390625였다. Adaptive는
> 행당 effective Full-open 1회와 pre-stale Full refresh 평균 15.9회를 사용했고
> Full 대비 algorithm CPU를 24.1% 줄였으나 planner ingress는 6.3% 증가했다.
> 따라서 이 결과는 nominal bandwidth 우위가 아니라 **severe-cadence 안전성
> stress**로만 사용한다. Population 100%나 exact-risk 단독 효과로 과장하지
> 말 것. 최신 상세는 viability §8.74 및
> `docs/static_heading_mismatch_result_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 static blind-doorway c1--c3 탐색은 안전성 분리 없이 중단.**
> Planner/정책은 동결하고 실제 L-corridor, 지속 배경 관측, 정적 원통,
> actual-PCD inflation 우회 gate, MARSIM/C++ replay와 closed-loop polynomial
> audit를 추가했다. C2 component replay는 raw conflict 50--51/50--51,
> Sector leak 0, Adaptive fresh OCCUPIED 26회로 13/13 PASS했다.
>
> 그러나 closed loop에서 c1/c2/c3 hazard Sector는 모두 첫 시도 완주·접촉 0,
> 물리 clearance +0.592/+0.780/+0.704m였다. C3 Sector는 일시적으로
> committed clearance -0.190m trajectory를 만들었지만 일반 재계획이 접촉 전
> 대체했다. C3 Adaptive의 generic exact OCCUPIED 2회는 벽 때문이었고 새
> hazard-matched count는 0회였다(c1은 단 1회). 판정은
> `STOP_C1_C3_NO_STATIC_SAFETY_SEPARATION`; 추가 원통 미세조정, Full/protected
> Adaptive 비행, 반복시험, McNemar는 금지한다.
>
> 다음 선택은 (1) 독립 replica를 둔 two-route static doorway topology를 새로
> 사전등록, (2) velocity-aligned fixed Sector baseline을 새 ablation으로 정의,
> (3) 안전성 우위 주장을 빼고 효율+비열등성으로 한정 중 하나다. 최신 상세는
> viability §8.73 및
> `docs/static_blind_doorway_exploration_result_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 v4 observed-exit 비행 gate 실패로 종료.** Full-only는 첫 시도
> 14.06s·접촉 0으로 통과했고, 이어진 3모드 n=3은 Full/Sector/Adaptive 모두
> 3/3 완주·접촉 0이었다. Observation wall이 Sector MAP_STALE를 0/3으로
> 제거했지만 Sector 저하도 0/3이 됐다. 따라서 v3 Sector timeout은 hidden
> hazard 안전성 차이가 아니라 empty-cloud liveness 교란이었다.
>
> Adaptive exact future-risk verdict 248회는 모두 FREE였고 exact brake는
> 0/3이다. 5/4/4 effective Full-open은 replan/ordinary guard 경로다. 고정
> 판정은 `STOP_V4_THREE_MODE_GATE_FAILED`; v4 재시도·튜닝·held-out 확장은
> 금지한다. 다음 탐색은 planner/알고리즘을 동결한 별도 static blind-doorway
> 계열이며, 비행 전에 closed-loop committed-trajectory audit를 통과시켜야 한다.
> 최신 근거는 viability §8.72와
> `docs/angular_blind_turn_v4_gate_result_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 v4 observed-exit 비행 전 gate 통과 및 사전등록.** v3 Sector
> MAP_STALE를 nominal outgoing replay에서 15/15 frame·총 0점으로 재현한 뒤,
> 새 `abt4_observed_exit`에는 y=29m north observation wall 하나만 추가했다.
> hazard/lower occluder/aperture/route/planner는 바꾸지 않았다.
>
> Actual-PCD ROG route gate는 최소 0.551m, local anchor 6.539m로 PASS했다.
> Actual MARSIM Sector는 outgoing x=20/12/4에서 frame당 5847/2216/2206점을
> 유지했고, corner replay도 raw conflict/Sector leak 0/Adaptive fresh OCCUPIED
> 25회로 PASS했다. 자동 test 58개도 PASS다.
>
> 다음은 사전등록 Full 1행만 실행한다. 통과할 때만 3모드 n=3이며, Sector
> 실패에 MAP_STALE가 하나라도 있으면 성과로 인정하지 않는다. Full/Adaptive
> 3/3 safe completion과 exact Adaptive risk brake 2/3도 필수다. 최신 상세는
> viability §8.71 및
> `docs/angular_blind_turn_v4_gate_preregistration_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 v3 staged flight 종료: Full/Adaptive 완주, Sector timeout,
> exact-risk gate 실패로 중단.** 사전등록 Full은 첫 시도 11.40s·2/2 waypoint·
> 접촉 0·static clearance 0.473m로 통과했다. 조건부 Sector는 target 이후
> 90.01s timeout(접촉 0), Adaptive는 11.66s 완주(접촉 0)했다.
>
> Sector는 hazard collision이 아니라 forward crop empty/non-dense → map
> version 85 정지 → age 0.507s > 0.500s → fail-closed EMER_STOP liveness
> 실패였다. Adaptive는 replan status 115/실패 67/max streak 11에 따른 bounded
> Full-open 5회(19.231% duty)로 완주했다. 그러나 raw future verdict 78회는 전부
> FREE, exact frontend risk brake는 0이었다. Probe도 early open 때 velocity
> heading 기준 9.466° 안이었다. 즉 Adaptive 개선은 replan-triggered opening
> 효과이지 exact trajectory-risk/collision-safety 증거가 아니다.
>
> 사전등록대로 `STOP_PAIRED_MECHANISM_GATE_FAILED`; 재시도나 확대시험은 하지
> 않았다. 결과를 성공으로 선택해 반복하지 말 것. 최신 근거는 viability §8.70,
> `docs/angular_blind_turn_v3_gate_result_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 v3 open-bypass route/replay gate 통과, Full-only flight
> 사전등록 완료.** 이전 실패를 덮지 않고 새 이름 `abt3_gate_open`으로 만들었고
> planner/policy는 바꾸지 않았다. v2 lower occluder/aperture/hazard는 유지하되
> local dead end의 원인이던 upper wall만 제거했다. 실제 PCD에 ROG와 같은
> 0.1m/3-cell inflation을 적용한 우회 경로 gate가 PASS했고, 첫 anchor는
> 6.539m로 7m horizon 안, sampled-surface 최소거리는 0.551m였다.
>
> 실제 MARSIM/C++ replay에서도 raw conflict 50/50, Sector leak 0,
> Adaptive fresh OCCUPIED 25회 연속으로 PASS했다. 테스트는 53개 PASS다.
> 다음 실행은 사전등록된 Full 1행뿐이다. unique first-attempt·모든 품질 gate
> 유효·접촉 0·완주일 때만 Sector/Adaptive 각 1행으로 넘어간다. 실패하면 즉시
> 중단한다. 상세 명령·hash·판정 규칙은 viability §8.69와
> `docs/angular_blind_turn_v3_gate_preregistration_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-09 deterministic actual-raycast/frontend witness 통과, 단 Full
> fixture 승격은 보류.** 더 이상 aperture를 비행으로 미세 튜닝하지
> 않고 `perfect_drone_sim/frontend_replay_witness`를 추가했다. SUPER는 실행·
> 변경하지 않고, PerfectDrone을 고정 pose/yaw/velocity에 둔 채 실제
> MARSIM raycast → direct SharedPtr → 운영 C++ frontend crop/risk 경로를
> 그대로 사용했다.
>
> `abt2_cal_t3`, pose `(24,23.5,1.5)`, yaw 90°, velocity `(0,7,0)`,
> 1.15s trajectory/운영 1.0s horizon에서 동일 raw 입력은 50/50 frame에
> hazard와 trajectory-conflict 점을 포함했다. Fixed Sector 출력은
> hazard/conflict 0점이고, Adaptive raw risk worker는 fresh OCCUPIED를 25회
> 연속 발행했다. Fail-closed gate 13/13 PASS, package build와 campaign test
> 47개도 통과했다. 반면 예전 가정 pose `(24,20)`에서는 실제 raycast
> target-cylinder point가 0이어서, 기존 비행의 risk 0회 원인을 직접
> 확인했다.
>
> 이것은 frontend mechanism 증거이지 안전성 우위나 완주 증거가 아니다.
> 기존 `abt2_cal_t3` Full은 90.01s timeout(107 reroute arm, 336 search)이므로
> evaluation fixture로 승격시키지 않았고 추가 flight/150행도 실행하지
> 않았다. 다음은 새 이름 v3에서 upper channel wall을 넓히거나 제거해
> local horizon 안의 inflation-aware forward bypass를 먼저 검증한 뒤,
> replay/route gate → 사전등록 Full-only smoke 순서로 간다. 최신 상세는
> viability §8.68과 `docs/frontend_replay_witness_result_20260909.md`를
> 우선한다.

> [!IMPORTANT]
> **2026-09-09 isolated angular blind-turn v2도 calibration gate에서 중단.**
> 이전 실패를 덮어쓰지 않고 `abt2_cal_t1..t5`를 새로 사전등록했다. `(24,0)`
> north-facing 시작, 첫 turn=목표 turn, 공통 controlled background/hazard,
> 기체 직경 0.40m보다 좁은 full-height aperture 0.38m, 벽과 분리된 surface
> probe를 사용했고 planner는 바꾸지 않았다. 실제 PCD 격자를 쓴 구조 validator는
> first ray 47.145--50.596°, 7m/s reveal lead 0.422--0.529s를 확인했다.
>
> 15행은 20.8분에 전부 unique·first-attempt·품질 유효, retry/resource abort/
> infrastructure failure/OOM/접촉 0으로 끝났다. 그러나 Full/Sector/Adaptive
> 완주는 3/5, 0/5, 3/5였다. Sector 5/5가 목표 turn 이후 timeout이라 분리
> 조건 하나는 충족했지만, Adaptive exact fresh frontend risk brake는 0/5였다.
> Raw worker 자체는 정상(약 5Hz, 행당 117--472 verdict)이지만 OCCUPIED가 단 한
> 번도 없었다. Adaptive effective-Full 124회는 replan/ordinary trajectory guard
> 계열이지 future-risk 개입이 아니다. Surface probe는 10/10 관측됐지만 실제
> 자세/경로에서 sector 밖은 6/10뿐이었다.
>
> 원인은 static line-of-sight가 실제 raycast+closed-loop state를 보장하지 못한
> 것이다. 조기 aperture가 본 것은 outgoing trajectory와 충돌하지 않는 hazard
> 북쪽 표면이었고, 실제 x 편차·선행 yaw 회전 때문에 일부 probe가 45° 안으로
> 들어왔다. Full/Adaptive timeout은 +0.45m 해석 우회가 inflation/search horizon/
> dynamics/누적 reroute zone까지 보장하지 못해 A* NO_PATH와 optimizer overtime이
> 반복된 결과다. 판정은 `STOP_CALIBRATION_GATE_FAILED`; 독립 맵/150행은 실행하지
> 않았다. 다음은 맵을 또 미세조정하기 전에 실제 simulator raycast와 C++ crop/risk를
> 쓰는 deterministic replay witness를 만들어야 한다. 최신 상세는 viability
> §8.67과 `docs/isolated_angular_blind_turn_result_20260909.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-08 90° angular blind-turn calibration gate 실패.** 기존 planner와
> Map1--10/`occ_bw` 결과를 보존한 채 별도 `abt_cal_s1..s5` 15행을 사전등록해
> 실행했다. 모든 행은 unique·first-attempt·품질 유효이고 접촉은 0이었다.
> Full/Adaptive는 5/5 완주, Sector는 4/5 완주했지만 Adaptive의 causal
> frontend future-trajectory brake는 s3/s4의 2/5뿐이라 4/5 기준에 실패했고,
> Sector degraded도 1/5라 2/5 기준에 실패했다. 유일한 Sector timeout도
> `(24.269,6.596)`, waypoint 1/6에서 발생해 목표 hazard 이전의 confound다.
> 판정은 `STOP_CALIBRATION_GATE_FAILED`; 독립 맵과 150행은 만들거나 실행하지
> 않았다.
>
> Sector 실패 원인은 약 10Hz 입력이 계속되는 중 45° crop이 1.386%만 남겨
> empty/non-dense cloud가 되고, map version 85에서 commit이 끊겨 0.558s
> MAP_STALE fail-closed가 영구화된 것이다. 또한 raw probe가 upper wall과 겹쳐
> first-visibility 측정은 무효지만 flight decision/gate에는 영향이 없다. 다음
> 버전은 `(24,0)` north-facing start, 첫 turn=hazard, 공통 controlled background,
> isolated surface probe, reveal-to-switch >=0.4s로 설계해야 한다. 최신 상세는
> viability §8.66과
> `docs/angular_blind_turn_calibration_result_20260908.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-08 wide-bypass blind-corner 보조 150행 완료.** 기존 Map1--10과
> frozen v7/45° planner를 그대로 보존하고, odd seed 1/3/5/7/9의 5개 반경 층에
> 공통 full-height L corner와 `(18.4,24.0)`, 반경 0.95 m hazard를 넣은 별도
> `occ_bw_r1..r5` 코호트를 사전등록했다. smoke 15행과 본시험 150행은 분리했다.
> 본시험은 약 174.3분에 150/150 unique·first-attempt·품질 유효로 종료됐고,
> Full/Sector/Adaptive 각각 50/50 완주, authoritative/analytic contact 0이다.
> retry/resource abort/infrastructure failure/OOM도 0이었다.
>
> Filtered probe 100/100 유효, Sector hazard centre crop 밖 50/50, 맵별 최초
> 관측거리 중앙값 4.377--4.441 m로 blind-corner geometry는 전달됐다. 그러나
> Adaptive trajectory-guard active는 맵별 7/10, 9/10, 4/10, 6/10, 4/10이라
> 사전 기준 8/10을 네 맵에서 못 넘었다. Effective Full 전환은 총 1,119회
> (22.38/run)였고 대부분 replan guard였다. Desired binary discordance는 0,
> Adaptive paired clearance 우위는 4/5였지만 중앙값 +0.0515 m로 +0.10 m 기준에
> 미달했다. 고정 판정은 `SUPPLEMENT_COMPLETE_NO_SAFETY_SEPARATION`이다.
>
> Adaptive는 Full 대비 ingress/map compute/common E2E mean cores/core-s를
> 84.141/56.558/20.541/20.906% 줄였지만 peak PSS는 0.211% 높았다. Full과
> Adaptive의 유한 코호트 신뢰도 목표는 달성했으나 Sector도 전부 안전하므로
> Adaptive 안전률 우위나 McNemar를 주장하면 안 된다. 분석 후 발견한 map-table
> field alias 문제만 raw 비변경 상태로 수정·회귀시험했다. 최신 상세는 viability
> §8.65와 `docs/static_blind_corner_wide_supplement_result_20260908.md`를
> 우선한다.

> [!IMPORTANT]
> **2026-09-08 channelized static-occlusion v2 파일럿 종료.** v1 결과를
> 설계 자료로만 닫고 independent even-seed 2/4/6/8/10 배경에 공통 L형 채널,
> `(18,24)` hazard와 nominal 수평 sensor slit/occluded solid-wall 쌍을 만들었다.
> 실행·게이트를 첫 비행 전에 커밋한 뒤 5개 층 × 2 visibility × 3모드=30행을
> 약 41분에 수행했다. 전 행 unique·first-attempt·품질 유효였고 각 모드
> 10/10 완주, authoritative/analytic hazard 접촉 0이다.
>
> Solid-wall occluded reveal은 두 정책 간 0.255 m 이내, hazard 거리
> 3.418--4.532 m로 표준화됐고 Sector crop 밖 조건도 5/5였다. 그러나 paired
> delivery gate는 실패했다. Sector의 occluded-minus-nominal delay는
> +3.029/+4.231/+0.014/-0.006/+6.294 m, Adaptive는
> +6.149/+6.422/+6.927/+10.420/+5.981 m라 양 정책·전 층 6 m 기준을 못
> 만족했다. 고정 1.45 m 검증과 달리 실제 고도가 변했고, tier 3/4 nominal
> Sector는 z=1.942/1.905 m에서 늦게 본 반면 Adaptive는 z=1.462/1.491 m로
> slit 안에서 일찍 봤다. 즉 fixed-height slit이 3D 정책 독립 가시성을
> 만들지 못했다.
>
> Desired binary discordance 0, Adaptive hazard-clearance 우위 2/5, direct
> 중앙값 -0.070 m, difference-in-differences 중앙값 -0.087 m로 안전 차별
> gate도 실패했다. 모든 occluded Adaptive 행에서 TG open 1--9회가 있어
> 비활성화 문제는 아니다. 고정 판정은
> `STOP_AFTER_CHANNEL_PILOT_NO_CONFIRMATORY_EXPANSION`이며 80환경/240행은
> 실행하지 않았다. Adaptive의 Full 대비 ingress/map/E2E mean cores/core-s
> 절감은 75.459/44.229/14.807/18.891%지만 안전 우위나 McNemar를 주장하면
> 안 된다. 최신 상세는 viability §8.64와
> `docs/static_occlusion_channel_pilot_result_20260908.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-08 balanced static-occlusion pilot 종료.** 기존 Map1--10은
> 개발/반복 신뢰도 코호트로 유지하고, 5개 반경 층 × nominal/occluded × 3모드의
> 별도 사전등록 파일럿 30행을 약 41분에 실행했다. 30/30 모두 고유·첫
> attempt·품질 유효였고 Full/Sector/Adaptive 모두 10/10 완주, authoritative
> source-PCD 접촉 0이다. C++ measurement-only raw hazard probe도 filtered
> 20/20행에서 유효했다.
>
> 가림벽은 최초 위험물 관측을 모든 반경 층에서 평균 4.416--9.665 m 늦춰
> physical-delivery gate는 통과했다. 그러나 Sector-bad/Adaptive-safe binary
> discordance는 0이고, Adaptive clearance 우위는 3/5, 중앙값 +0.011 m로
> 사전 기준 4/5와 +0.10 m에 못 미쳤다. 따라서 고정 규칙대로
> `STOP_AFTER_PILOT_NO_CONFIRMATORY_EXPANSION`이며 80맵/240행 확증시험은
> 실행하지 않았다. 이 결과를 Adaptive 안전률 우위나 McNemar 검정으로 쓰면
> 안 된다. 원인은 유한한 가림벽과 넓은 우회로가 정책 공통 reveal point를
> 강제하지 못한 설계다. Probe는 control 출력은 없지만 최초 관측까지 동기
> raw-cloud scan을 하므로 문자 그대로 timing 영향 0인 계측은 아니다. 최신
> 상세는 viability §8.63과
> `docs/static_occlusion_balanced_pilot_result_20260908.md`를 우선한다.

> [!IMPORTANT]
> **2026-09-07 Map9--10 static three-mode n=30 완료.** 사전등록한 180행을
> 약 287분에 모두 실행했다. Full/Adaptive는 각각 60/60 완주,
> authoritative source-PCD 접촉 0이어서 보호 모드 실패 시 중단/수정/처음부터
> 재시험 조건은 발생하지 않았다. Sector는 접촉 0이지만 Map10 run30 한 건이
> 180.01초에 3/5 waypoint로 timeout하여 59/60이다. 이 행은 +0.226 m
> clearance, PSI/process swap/OOM/retry 0인 안전한 liveness 실패였고,
> recovery 132.692초, topology search 195회, trajectory commit 0.600 Hz의
> stop/reroute loop였다. 고정 ablation인 Sector는 사후 튜닝하지 않았다.
>
> 180/180행은 first-attempt 및 run/resource/speed/performance-valid이고 strict
> validation은 PASS다. Adaptive는 Full 대비 ingress 74.256%, map compute
> 36.458%, 공통 E2E mean cores 14.029%, core-seconds 16.941%를 줄였으며
> effective/TG Full-open은 1,306/462회다. 모든 모드 접촉 0이므로 안전률 우위는
> 주장할 수 없고, 60/60도 population 100% 보장이 아니다. 최신 상세는
> `docs/map9_10_static_n30_final_20260907.md`와 viability §8.62를 우선한다.

> [!IMPORTANT]
> **2026-09-07 blind-zone v7 time-boxed smoke 종료.** V6 경로를 설계 데이터로
> 선언하고 Map9 `(22.50,23.05)`, 반경 0.50 m의 trajectory-intersection
> stress를 비행 전에 고정했다. Full/Sector/Adaptive n=1은 약 4.5분에 모두
> first-attempt 유효 완주·source/synthetic 접촉 0이었고 synthetic clearance는
> +0.305/+0.237/+0.199 m였다. Adaptive가 가장 가까웠고 raw-risk OCCUPIED도
> 0건이어서 사전등록한 Sector 열화 gate를 통과하지 못했다. 따라서 후보 2--6과
> 18행 확증시험은 실행하지 않았으며 추가 위치/반경 튜닝도 하지 않았다.
> Adaptive 안전률 우위나 McNemar 결과는 여전히 주장할 수 없다. 상세는
> viability §8.61과
> `docs/blind_zone_v7_stress_preregistration_20260907.md`를 우선 참조한다.

> [!IMPORTANT]
> **2026-09-07 EMER_STOP/motion-source 수정 및 blind-zone 단계 완료.**
> 아래 2026-09-05 배너의 300회는 수정 전 원인분석 결과이며 최신 결론은 이
> 배너가 우선한다. Guard-enabled EMER_STOP의 ordinary command 누출을 차단했고,
> 별도 timestamp odom twist와 same-generation pose delta가 합치할 때만 brake
> motion으로 채택하도록 수정했다. Pose `<=0.05 m/s`, twist `>0.05 m/s` 충돌은
> twist를 거부한다. 14/14 CTest와 올바른 `/root/super_ws/install` 배포를 확인했다.
>
> 배포본 최종 Map1--10 × Full/Sector/Adaptive × n=10은 300/300 고유·유효·
> first-attempt 완주다. 권위 지표 `static_pcd_collisions` 기준 Full/Adaptive는
> 0/100, Sector는 Map9 run3에서 1/100 접촉이다. Legacy `collisions` 열은 이
> 접촉을 포함하지 않으므로 안전 집계에 사용하면 안 된다. Paired Adaptive는
> 접촉 0, +0.274 m clearance, effective-open 16회였다. Adaptive는 Full 대비
> ingress 77.139%, map compute 39.276%, algorithm mean cores 29.136%, E2E mean
> cores 12.751%를 줄였다. 7,372개 motion log 중 stationary-pose/nonzero-twist
> 1,160건의 잘못된 odom-twist 채택은 0건이다.
>
> Blind-zone은 v4 처리 누락을 버리지 않고 v5 3연속-sample 설계 코호트로
> 교정한 뒤, 사전 고정 selector가 `(22.50,22.95)`를 선택했다. Frozen v6
> 확증 27회는 이벤트/완주 27/27, 모든 모드 source/side-entry 접촉 0이었다.
> 따라서 공통 blind treatment와 Full 대비 연산·통신 절감은 검증했지만
> side-entry 안전률 우위는 입증하지 못했고 McNemar 검정도 주장하지 않는다.
> 7,675개 Fast DDS zombie SHM(약 2 GiB)이 preflight 600초 timeout 원인이어서
> runner teardown에 `fastdds shm clean`을 추가했다. 상세는 viability §8.60과
> `docs/emergency_stop_motion_blind_zone_final_20260907.md`를 우선 참조한다.

> [!IMPORTANT]
> **2026-09-05 prospective resource-gated 10맵 × 3모드 × n=10 완료.**
> 고정 v7/45° profile로 300개 고유 run을 모두 첫 attempt에 완료했고 resource
> abort/retry/OOM 및 static-PCD 충돌은 0이다. Full과 Adaptive는 각각 100/100
> 완주·100/100 protocol-valid였다. Sector도 100/100 완주했지만 Map 9 run 2에서
> guard flag-3 command/odom이 10.95563 m/s까지 올라 v7 속도 계약을 위반해
> 99/100 valid다. 이 실패를 성공 재시험으로 대체하지 않았으므로 전체 strict
> validation은 의도대로 FAIL이다.
>
> Adaptive는 Full 대비 map compute/frame 38.599%, 공통 E2E mean cores 13.709%,
> core·s 16.574%, logical planner ingress 75.632%를 줄였고 평균시간은 3.247%
> 짧았다. Peak PSS는 0.328% 높아 메모리 절감 주장은 하지 않는다. Adaptive
> effective-open은 총 1,904회(19.04/run)다. Full raw cloud는 in-process라
> external DDS가 정의되지 않으며 algorithm CPU scope도 Full과 filtered mode가
> 달라, 두 항목의 Full 대비 비교는 금지한다.
>
> Map 9 속도 실패의 직접 경로는 공통 guard 결함이다. brake reject 후
> guard-enabled EMER_STOP에서도 `pubCmdTimerCallback`이 ordinary command를
> 발행했고, PerfectDrone position jump를 위치 차분 `odom_motion=10.960`으로
> 오인한 뒤 brake cap을 그 값으로 확장했다. 다음 변경은 EMER_STOP ordinary
> command 차단, continuity-qualified velocity, 회귀시험 순서다. 상세 표·자원/swap
> audit·통계 한계는 `docs/resource_guard_campaign_final_20260905.md`, viability
> §8.59에 있다. 원자료는 `results/allmaps_resource_guard_prospective_three_mode_`
> `n10_{raw_20260904,summary,reductions,validation}`이다.

> [!IMPORTANT]
> **2026-09-04 resource-valid Map10 Full/Adaptive prospective n=3 완료.**
> 시험 중 외부 VS Code extension host를 분리해 available 약 9GiB, swap/PSI 0을
> 확보하고 새 기본 resource gate를 첫 행부터 적용했다. Planner/profile 변경 없이
> 6/6 모두 first-attempt 완주, static-PCD 충돌 0, run/resource/speed/performance/
> cgroup-valid였고 abort/retry/OOM은 0이다. Full/Adaptive 평균 시간은
> 66.82/65.43초, available 최저 5850.75/5679.31MiB, PSI 최대 0.18/0이었다.
> Adaptive effective-open은 총 48회다.
>
> 이전 clean audit와 합치면 Full/Adaptive 각각 clean Map10 5/5 완주다. 이는
> resource-confounded run8 때문에 planner를 더 튜닝하지 않는 판단을 강화하지만,
> prospective n=3 자체는 population 100% 보장이 아니다. 상세는 viability §8.58,
> 자료는 `results/map10_resource_guard_prospective_full_adaptive_n3_`
> `{raw,summary,reductions}_20260904.csv`다.

> [!IMPORTANT]
> **2026-09-04 Map10 실패 재분류 및 campaign resource gate 구현.**
> 기존 n=10 러너는 메모리/PSI를 측정만 하고 `run_valid`/retry에 쓰지 않았다.
> 따라서 Map10 run8 Adaptive/Full의 legacy `run_valid=True`는 잘못된 유효성
> 해석이며, available 최저 약 249MiB, swap 포화, PSI some/full
> 55.87/52.89와 64.26/60.66인 resource-confounded attempt로 분류한다. 반면
> run4 Sector는 PSI 0에서 동일 후보를 100회 이상 거절한 유효 topology trap이다.
>
> `native_campaign.py`는 이제 기본-on으로 launch 전 available 8GiB 및 PSI
> some/full `<=10/5`의 5초 안정 구간을 요구한다. 실행 중 available 2GiB 미만
> 또는 PSI 초과가 5초 지속되면 infrastructure attempt로 중단·재시도하고,
> preflight가 600초 내 회복되지 않으면 pending row 없이 종료한다. CSV resource
> validity metadata와 SIGINT/SIGTERM/SIGHUP process-group cleanup도 추가했다.
> pytest 33개와 강제 preflight 거부 시험은 통과했다. 현재 VS Code extension
> host RSS 약 6.3GiB로 available 약 5GiB라 실제 Map10 smoke는 gate가 의도대로
> 차단했다. 메모리 회수 후 동일 profile로 Full/Adaptive를 재시험하고, 유효
> 실패가 재현될 때만 planner를 수정한다. 상세는 viability §8.57이다.

> [!IMPORTANT]
> **2026-09-04 frozen profile 10맵 3모드 paired n=10 완료.**
> 공식 cohort는 고유 300행이며 모든 행이 run/speed/performance/cgroup-valid,
> retry/OOM/충돌 0이다. 명목 완주는 Full/Sector/Adaptive 모두 99/100이고
> Map1--9는 전 모드 10/10, Map10은 각 9/10이다.
>
> Map10 run4 Sector는 PSI 0인 실제 topology/liveness trap이며 같은 paired
> Full/Adaptive는 완주했다. Map10 run8은 Sector가 완주했지만 Adaptive/Full이
> 3/5와 2/5 waypoint에서 timeout/HUNG이었다. 두 실패는 available 약 249MiB,
> swap 2GiB 포화, PSI some 55.87/64.26인 심한 host-memory pressure와 결합됐다.
> 자원 회복 후 Map10 Full/Adaptive 각 n=2 clean audit는 모두 PSI 0, 완주,
> 충돌 0이었지만 공식 실패는 대체하지 않았다.
>
> Adaptive는 Full 대비 logical ingress 75.903%, map-compute 67.254%, 동일
> end-to-end mean cores 13.362%, core·s 16.948%를 줄였다. effective-open은
> 2,009회(20.09/run)다. Adaptive 대 Sector discordance는 양방향 한 건씩으로
> exact McNemar p=1.0이며 99/100의 Wilson 95% 하한은 94.55%다. 따라서
> population-level 100% 또는 Adaptive 성공률 우위는 주장하지 않는다.
> 상세는 viability §8.56, `docs/full_inprocess_control_20260903.md`, 최종 자료는
> `results/full_control_three_mode_map1_10_n10_{raw,summary,reductions}_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-03 frozen profile 10맵 3모드 paired n=5 체크포인트.**
> run 4--5 60행을 추가해 고유 150행을 완성했다. Full/Adaptive는
> 50/50 완주, Sector는 49/50 완주, 전 모드 충돌 0이고 retry/OOM은 0이다.
> Map10 run4에서 Sector는 180초 timeout, 같은 run의 Adaptive는
> 68.96초 완주해 첫 paired Sector 열화→Adaptive 회복 사례가 되었다.
>
> 실패 Sector는 certified stop 근처에서 exclusion zone 6개를 포화시킨 뒤
> 거의 같은 짧은 후보를 반복해 CIRI에서 100회 이상 거절됐다. PSI/OOM/
> retry가 0이므로 infrastructure가 아닌 Sector topology/liveness trap이다.
> Adaptive는 Full 대비 ingress 76.220%, map-compute core equivalent 67.734%,
> mean cores 13.378%, core·s 16.323%를 줄였고 effective-open은 1,031회다.
> 현재 설정은 동결한 채 run 6--10을 추가하는 n=10 단계다. 상세는 viability
> §8.55와 `docs/full_inprocess_control_20260903.md`, 체크포인트 자료는
> `results/full_control_three_mode_map1_10_n5_{raw,summary,reductions}_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-03 frozen Full 10맵 3모드 paired n=3 완료.**
> 동일 profile/accounting으로 Map1--6/8 63행을 추가하고 앞선 hard-map 27행과
> 합쳐 고유 90행을 완성했다. Full/Sector/Adaptive 모두 30/30 완주·충돌 0,
> speed/performance/cgroup valid이며 retry/OOM은 0이다. Full은 추가 수정 없이
> 새 paired cohort에서도 30/30을 유지했다.
>
> Adaptive effective-open은 맵별 47/61/63/55/52/69/64/67/68/59회, 총 605회다.
> Full 대비 logical ingress 75.876%, map-compute core equivalent 66.862%,
> end-to-end mean cores 13.001%, core·s 15.373%가 감소했다. Sector 대비 ingress와
> external DDS는 약 19% 감소했지만 core·s는 2.879% 증가했다. Full raw DDS는
> in-process라 0이므로 Adaptive-vs-Full DDS 감소 주장은 여전히 금지한다.
>
> Adaptive 평균/최저 clearance +0.249/+0.173m는 Sector +0.262/+0.174m보다
> 좋지 않았다. Map6 Adaptive 최저는 1.46m/s 이동 중이라 0.20m margin contract를
> 만족하지 않은 관측으로 남긴다. 접촉은 없었다. Sector도 30/30 무접촉이므로
> 현재 static map은 Full 대비 효율 주장은 지지하지만 Adaptive가 Sector의
> 완주율/충돌률을 회복한다는 가설에는 식별력이 없다. 상세는 viability §8.54와
> `docs/full_inprocess_control_20260903.md`, 최종 raw/summary/reduction은
> `results/full_control_three_mode_map1_10_n3_{raw,summary,reductions}_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-03 동결 Full 기반 3모드 hard-map gate 완료 및 CPU 범위 정정.**
> Map7/9/10 × Full/Sector/Adaptive × n=3의 27개 고유 행이 모두 first-attempt
> 완주·static-PCD 충돌 0·속도/성능/cgroup valid였고 retry/OOM은 0이었다.
> Full은 잔여 liveness tail 맵에서 9/9를 유지했다. Adaptive effective-open은
> Map7/9/10에서 64/68/59회(합계 191회)였다. Adaptive worst clearance는
> +0.214m, Sector는 +0.174m였지만 Sector도 9/9 완주·무접촉이라 Adaptive의
> 성공률/충돌률 우위는 아직 주장할 수 없다.
>
> cgroup의 `algorithm_cpu_*`는 이제 교차모드 비교 금지다. 결합 Full은
> simulator+planner, cpp-frontend Sector/Adaptive는 planner-only가 들어가기
> 때문이다. 러너에 scope metadata를 추가했고 공통 parent end-to-end cgroup만
> 총 연산량 비교에 사용한다. Adaptive는 Full 대비 logical ingress 74.669%,
> map-compute core equivalent 64.857%, end-to-end mean cores 11.300%, core·s
> 16.689%를 줄였다. 새 Full은 raw DDS가 0이므로 Adaptive-vs-Full DDS 감소는
> 주장하지 않는다. 다음은 Full을 바꾸지 않고 Map1--6/8 n=3을 채우는 단계다.
> 상세는 viability §8.53과 `docs/full_inprocess_control_20260903.md`, raw/summary는
> `results/full_control_three_mode_map7_9_10_n3_{raw,summary,reductions}_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-03 Full 우선 통제: viability egress 결함 수정 및 in-process Full
> raw-map 전달 gate 완료.**
> 초기-footprint egress로 허용된 trajectory의 viability brake에 egress 문맥이
> 빠지던 결함과, 이미 늘어난 trajectory에 누적 배율을 다시 곱하던 rescale 결함을
> 수정했다. Release build, campaign pytest 29개, 강제 Map8 egress gate가 통과했다.
>
> standalone Full raw DDS를 best-effort/depth-1로 바꿔도 Map9 ROG 입력은 평균
> 2.758 Hz에 머물렀다. 보존된 유효 7행은 완주 6/7, 충돌 1, stale 평균 55.14회,
> recovery 89.61초였다. 따라서 점을 줄이지 않고 PerfectDrone과 SUPER를 compose해
> 동일 Full `PointCloud2::SharedPtr`를 기존 latest-only ROG queue에 직접 넘기는
> opt-in `perfect_drone_full_node`를 추가했다. PCL/ROG/planner/guard 계산은 그대로고
> raw DDS 경계만 제거했다. 표준 `tight_v7`과 기본 launch 경로는 변경하지 않았다.
>
> Map9 in-process n=10은 10/10 완주·충돌 0, map 10.106 Hz, stale 0, 평균시간
> 76.16초였다. 이어 Map1--10을 각각 10회로 맞춘 최종 고유 100행 모두
> 완주·충돌 0·속도위반 0·stale/retry/OOM/PSI 0이었다. Map1--10 최저
> clearance는 +0.244/+0.217/+0.218/+0.222/+0.225/+0.175/+0.247/+0.184/
> +0.232/+0.185m다. 결합 프로세스 CPU 약 1.48 cores는 simulator+planner
> 전체이며 예전 FSM-only CPU와 직접 비교하지 않는다. Full logical ingress는
> 평균 9.43MiB/s로 줄지 않았고 raw DDS만 0이다.
>
> 관측 100/100의 Wilson 95% 하한은 약 96.30%이므로 population guarantee는
> 아니다. 현재 10맵/profile의 Full은 여기서 동결한다. 다음은 Full을 paired
> control로만 사용해 세 모드를 동일 cgroup 경계로 비교하고, Adaptive의 잔여
> 실패만 분석하는 단계다. 상세는 viability §8.52와
> `docs/full_inprocess_control_20260903.md`, compact/final raw는
> `results/full_inprocess_control_map_summary_20260903.csv`와
> `results/full_intra_map1_10_n10_raw_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-03 45° 선정 근거 고정 및 common-source side-entry v4 n=3 완료.**
> 45°는 안전률 우위가 아니라 이전 탐색 실험의 secondary balance로 선택했다.
> Sector/Adaptive의 clearance 0.20 m 미만은 2/9 대 0/9, worst-clearance 차이는
> Adaptive +0.053 m, 시간 감소 5.450%, DDS 감소 21.313%였다. 별도 기록은
> `docs/half_angle_45_selection_preregistration_20260903.md`다.
>
> PerfectDrone 공통 raw source에 late stationary cylinder와 0.20 m body-sphere
> analytic collision oracle를 구현했다. V1/v2는 PVAJ centre가 mode-dependent라
> 처치가 비었고, v3는 centre `(22.5,23.0)`을 고정했지만 velocity-sector 조건
> 때문에 Sector가 no-spawn이었다. V4는 위치·크기·47° body blind 조건을 그대로
> 두고 `require_velocity_inside=false`만 적용했다. 표준 tight_v7은 변경하지
> 않았고 Release build, unit test 19개, config/source-gap 및 event validator가
> 통과했다.
>
> Map7/9/10 × Full/Sector/Adaptive × n=3에서 raw 27행, validator-passing spawn
> 26행을 얻었다. Map10 Full run1은 두 valid sample 간격 0.009911 s가 frozen
> hold 0.015 s보다 짧아 no-spawn이며 invalid다. Valid 행 기준 완주는
> Full/Sector/Adaptive 7/8, 9/9, 9/9이고 세 모드 모두 collision 0이다. Sector도
> 9/9 완주·무접촉이므로 intended primary degradation은 여전히 없다.
>
> Map9 Full run2는 waypoint 3/5에서 180 s timeout했다. side-entry clearance
> +0.720 m, OOM/PSI 없음이라 cylinder나 infrastructure 실패가 아니다. 로그는
> PlanFromRest 218회, GeneratePolytopeFromLine 193회, backup generation 190회
> 실패를 보이며 reroute/vertical recovery가 start-adjacent CIRI-infeasible
> segment를 벗어나지 못했다. 다음 우선순위는 이 certified-stop liveness loop다.
>
> 7개 valid-complete 3모드 pair에서 Adaptive는 Full 대비 DDS 29.983%, ROG
> frame compute 26.009%, 전달 point 22.093%를 줄였지만 algorithm/end-to-end
> mean CPU cores는 57.465/55.166% 증가했다. 통신/ROG 감소만 주장 가능하다.
> 상세는 viability §8.51, compact 결과는
> `results/side_entry_v4_maps7_9_10_three_mode_n3_{summary,raw}_20260903.csv`와
> `results/side_entry_v4_maps7_9_10_three_mode_n3_paired_reductions_20260903.csv`다.

> [!IMPORTANT]
> **2026-09-02 paired half-angle screen과 optimizer phase 계측 완료.**
> `native_campaign.py`에 Sector/Adaptive 공통 `--filter-half-angle-deg`
> (기본 60°)와 default-off `--optimizer-phase-memory-trace`를 추가했다. 후자는
> Exp/Backup L-BFGS의 begin/end, 시간, RSS/swap 및 RSS delta를 모든 attempt에서
> 수집하며 OOM 중단 시 unmatched begin을 남긴다. 표준 tight_v7 profile은
> 변경하지 않았다. Release build, parser pytest 8개, Map1 45° 기능 gate가
> 통과했다.
>
> 사전 고정한 60/45/30° × Map7/9/10 × Sector/Adaptive × n=3의 54행은 전부
> first-attempt 완주, source-static-PCD 충돌 0, retry/OOM 0이었다. 따라서 어느
> 각도도 완주/충돌 기준 판별 조건이 아니며 discordant primary pair가 없어
> McNemar 검정도 하지 않았다. 45°에서만 설명적 차이가 가장 컸다: Sector는
> clearance 0.20m 미만 2/9(최저 +0.173m), Adaptive는 0/9(최저 +0.226m),
> Adaptive 평균시간 5.450%, DDS 21.313% 감소. 이는 안전률 우위 증명이 아니다.
>
> 54행의 Exp begin/end는 23,847/23,847, Backup은 41,100/41,100이었다. 최고
> optimizer RSS 3,282.7MiB, end-to-end RSS 3,723.9MiB, cgroup memory
> 9,597.2MiB이며 단일 호출 RSS 증가는 Exp 7.766MiB, Backup 8.871MiB였다.
> 이전 Map6 OOM은 재현되지 않아 원인은 확정할 수 없고, 다음 재현 때 어느
> optimizer 내부인지 구분할 준비만 완료됐다. 다음 safety-ablation은 같은
> 각도를 더 튜닝하지 말고 topology 또는 sensor-latency 조건을 사전 고정해야
> 한다. 상세는 viability §8.50 및
> `docs/half_angle_operating_envelope_20260902.md`, 결과는
> `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_{summary,reductions}_20260902.csv`다.

> [!IMPORTANT]
> **2026-09-02 current-body tier와 active-brake replacement 5단계 완료.**
> 300회에서 나온 Map10 접촉의 5 Hz/generation coverage gap을 heavy worker
> 증속 없이 분리했다. Future tier는 5 Hz exact-generation을 유지하고, 새
> current-body tier는 최신 raw scan과 measured odometry의 0.15 s 선분을 sensor
> frame마다 검사한다. source/result freshness는 필수지만 generation-independent다.
> 활성 brake 도중 더 앞쪽 fresh body witness가 오면 episode당 한 번 brake를
> 교체하며, duplicate request는 idempotent하게 무시한다. 모두 default-off이고
> 표준 tight_v7 profile은 변경하지 않았다.
>
> 결정론적 gate에서 stale body는 무시됐고, 일부러 다른 generation의 fresh body가
> 기존 future brake를 정확히 한 번 교체한 뒤 정상 복구했다. 자연 검증은 Map10
> Adaptive 30/30, Map7 Full/Adaptive 각 20/20, Map1--10 × Full/Sector/Adaptive
> 각 30/30 완주·source-static-PCD 무충돌이었다. 마지막 3모드 표본의 평균시간은
> 77.908/63.625/63.270초, 최악 clearance는 +0.166/+0.180/+0.121m다.
>
> Adaptive는 Full 대비 planner DDS 49.405%, ROG input 49.464%, ROG frame compute
> 32.474%, algorithm core·s 1.975%를 줄였다. 그러나 mean algorithm cores는
> 17.122%, end-to-end core·s는 1.348% 증가했고 PSS는 같아 총연산량/메모리 감소는
> 아직 주장할 수 없다. current-body tier 자체는 약 10 Hz에서 평균 0.320ms,
> 0.00340 core, 0.001829 MiB/s였다.
>
> **Sector도 30/30 완주·무충돌**이라 현재 ±60°/10맵은 Adaptive 우위를 식별하지
> 못한다. 각 모드 30/30의 Wilson 95% 하한도 88.65%뿐이다. Sector Map6 run1
> attempt1에는 별도의 OOM 1회가 있었고 retry 후 완주했다(FSM PSS 약
> 3.14→6.31GiB, swap 포화). Sector는 body tier를 켜지 않으므로 새 tier 원인은
> 아니지만 planner/optimizer memory 문제는 남아 있다. 다음은 같은 맵에서
> 사전등록 paired half-angle operating-envelope와 OOM phase별 RSS/deadline 계측이다.
> 상세는 viability §8.49 및
> `docs/frontend_body_active_brake_final_20260902.md`, 요약은
> `results/frontend_body_map1_10_three_mode_n3_{summary,reductions}_20260902.csv`다.

> [!IMPORTANT]
> **2026-09-02 cadence/enforcement 5단계와 최종 300회 완료.**
> Sensor/filter/ROG/trajectory cadence 계측, Adaptive map+risk 5 Hz cap,
> Map7/9/10 n=3 gate, L-BFGS 2,048 iteration 상한, compact verdict
> wrong-generation/stale/fresh fault gate를 순서대로 완료했다. 표준 `tight_v7`은
> 그대로고 enforcement는 별도 실험 profile에서만 켰다. 최종 raw는 정확히
> Map1--10 × 3 modes × n=10의 300개 고유 행이며 run/speed/performance/cgroup
> validity 300/300, retry/OOM 0이다.
>
> **목표는 아직 달성되지 않았다.** Completion은 Full/Sector/Adaptive
> 99/100/99, source-static-PCD collision은 0/0/1이다. Adaptive는 Full 대비
> mission time 19.883%, planner ingress 49.547%, algorithm core·s 2.219%를
> 줄였지만 end-to-end core·s는 1.900% 늘었다. Sector도 100/100·충돌 0이라
> intended ablation degradation은 이번 표본에서 관찰되지 않았다.
>
> Map7 run1 Full/Adaptive timeout은 동일 정지점의 topology trap이 외부 VS Code
> extension host 약 8 GiB, swap 포화, PSI full 53.55/64.20%에서 증폭된 복합
> 실패다. 환경 회복 뒤 run2--10은 두 모드 모두 9/9 완주했지만 raw 실패는
> 삭제하지 않는다. Optimizer cap은 300행 OOM 0과 PSS 약 3.2 GiB를 만들었으나
> liveness 자체를 보장하지 않는다.
>
> Map10 run6 Adaptive 접촉은 infrastructure가 아니라 실제 coverage gap이다.
> 첫 접촉 99 ms 뒤 gen36 OCCUPIED가 도착했고 그 사이 gen37이 commit되어 exact-
> generation gate가 무시했다. Gen37 brake는 접촉 뒤였다. 다음 구현은 heavy
> worker 전체를 10 Hz로 되돌리는 것이 아니라, current body/very-short horizon만
> 매 sensor frame에서 검사해 source-fresh generation-independent certified hold를
> 거는 저비용 tier를 추가하고 기존 5 Hz future-tail exact-generation tier는
> 유지하는 것이다. 상세는 viability §8.48 및
> `docs/frontend_risk_enforce_final_20260902.md`, raw/summary는
> `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_{raw_20260901,summary_20260902,reductions_20260902}.csv`다.

> [!IMPORTANT]
> **2026-09-01 sensor-front-end raw DDS 제거와 compact risk verdict gate 완료.**
> `perfect_drone_frontend_node`가 simulator와 native filter를 compose해 renderer의
> raw `PointCloud2::SharedPtr`를 직접 넘긴다. Sector/Adaptive에서는
> `/cloud_registered` publisher 자체를 만들지 않고, Sector는 filtered cloud만,
> Adaptive는 filtered cloud와 generation/freshness가 포함된 compact trajectory-
> risk verdict만 DDS로 보낸다. 실제 직렬화 verdict는 정확히 180 bytes/message다.
> Angular filter와 risk check는 각각 독립 latest-only worker라 sensor callback과
> planner callback을 동기적으로 막지 않는다.
>
> v=7 Map7/9/10 × Full/Sector/Adaptive × n=1 architecture gate의 9행은 모두
> first-attempt 완주, source-static-PCD collision 0, retry/OOM 0이었다. 세 map
> 평균에서 Adaptive의 DDS cloud rate는 Full보다 18.085% 낮고 verdict를 포함해도
> 약 0.044%만 추가됐다. 다만 **연산량 감소는 아직 성립하지 않는다.** 이 gate의
> Adaptive FSM core-seconds는 Full보다 10.677% 높았고, Full ROG 처리율
> 3.82~4.49 Hz와 front-end Sector 약 10.20~10.34 Hz의 cadence 차이가 confound다.
> 따라서 현재 contribution은 raw sensor DDS의 구조적 제거와 작은 검증 계약이며,
> computation 절감은 동일 accepted-generation/sensor cadence에서 재검증해야 한다.
>
> 표준 `tight_v7` profile은 변경하지 않았고 verdict enforcement는 default false다.
> 다음은 안전 threshold가 아니라 front-end publish/ROG commit cadence를 정합한 뒤
> completion/contact를 유지하는 최소 callback rate를 찾는 단계다. 상세는 viability
> §8.47과 `docs/sensor_frontend_risk_verdict_20260901.md`, 원자료는
> `results/frontend_risk_shadow_maps7_9_10_three_mode_n1_raw_20260901.csv` 및
> `results/frontend_risk_cpu_map7_three_mode_n1_raw_20260901.csv`다.

> [!IMPORTANT]
> **2026-09-01 C++ 동일 프로세스 zero-copy raw guard handoff 완료.**
> 외부 bounded witness는 8m에서 점 약 93.5%, 5m에서도 약 80.7%를 남겨
> 대용량 side-channel을 충분히 줄이지 못했다. 최종 구조는 native filter와
> FSM을 compose하고, filter가 받은 raw `PointCloud2::SharedPtr` 자체를 Adaptive
> FSM raw-window ingest에 직접 넘긴다. Injection mode에서는 FSM의 별도 full-raw
> subscriber를 만들지 않고, 외부 witness도 publish하지 않는다. 무거운 검사는
> 기존 async latest-only worker에 남는다. Sector에는 observer를 연결하지 않아
> 순수 angular-cut ablation을 유지한다.
>
> 최초 rotating campaign 뒤 witness YAML 끝의 `p_hit/p_max/unk_thresh` 누락을
> 발견해 복원했다. Full/Sector 18행은 영향이 없고, Adaptive는 완전한 기존
> raw-enforce profile+동일 injection으로 Map7/9/10 각 3회를 다시 실행했다.
> 결합한 최종 27행은 모두 first-attempt, run/perf/cgroup-valid이고
> retry/OOM/speed violation 0이었다. Completion은 모두
> 9/9, source-static-PCD safety는 9/9, 8/9, 9/9이다. Sector Map10 run3만
> clearance -0.065m 접촉 1회였고 Full/Adaptive는 충돌 0이다. 평균시간은
> 93.802/93.427/104.551초다. Adaptive는 Full 대비 ROG payload 48.107%, algorithm
> mean core 22.492%, core·s 13.003%, end-to-end core·s 7.842% 감소했고 시간은
> 11.459% 늘었다. Effective Full-open 42회, direct SharedPtr handoff 3,764회,
> external witness publish 0회다.
>
> DDS cloud rate는 표본상 16.575% 낮지만 raw bytes/scan은 거의 같고 simulator
> cadence 영향을 받는다. 주장 가능한 것은 두 번째 full-raw DDS hop 제거와
> ROG/CPU 감소이지 sensor wire bytes/scan 감소가 아니다. Logical planner
> ingress는 zero-copy 소비까지 합산해 오히려 35.465% 높으므로 wire bandwidth로
> 해석하면 안 된다. Adaptive 127.39초 tail은 recovery 73회·active 83.615초였고,
> n=9에서 시간과 recovery-active 누적의 상관은 0.978이었다. 다음은 안전 gate를
> 약화하지 않는 same-obstacle/generation recovery coalescing과 Map1-10 n=10이다.
> 상세는 viability §8.46 및
> `docs/inprocess_raw_guard_handoff_20260901.md`다. Full/Sector raw와 combined
> summary는 `results/inprocess_raw_handoff_seed7_9_10_three_mode_n3_{raw,summary}_20260901.csv`,
> corrected Adaptive raw는
> `results/inprocess_raw_handoff_corrected_adaptive_seed7_9_10_n3_raw_20260901.csv`다.

> [!IMPORTANT]
> **2026-09-01 pre-filter raw witness enforce와 최종 n=10 완료.**
> Map7 Sector run7 포렌식에서 장애물 방향이 속도 기준 약 +92.2도, live
> candidate가 +70.1도로 ±60도 sector 밖임을 확인했다. Passage soft cost가
> 아니라 lateral raw witness 누락이 우선 원인이었다.
>
> 새 `fsm/trajectory_guard/raw_cloud/source_topic`으로 실험용 filtered profile의
> ROG-Map은 `/cloud_sector`, 비동기 recent-hit worker는 `/cloud_registered`를
> 받는다. 표준 tight_v7은 그대로고 raw CIRI/passage cost는 off다. Map7 Full
> enforce n=20은 20/20 완주·safe, brake 0이었고 maps7/9/10 3모드 n=3은
> 27/27 완주·safe, retry 0이었다. Sector는 OCCUPIED 18건을 brake했다.
>
> 최종 rotating Map1-10 × Full/Sector/Adaptive × n=10은 completion
> 100/99/100, source-static-PCD safety 100/98/100이다. Full/Adaptive는 각
> 100/100 완주·충돌 0이다. Sector는 Map7/10 접촉 각 1회와 Map8 timeout
> 1회가 나왔다. 평균시간은 78.640/77.061/81.769초, worst clearance는
> +0.101/-0.168/+0.117m다. Adaptive는 Full 대비 ROG payload 45.746%,
> 평균 algorithm CPU core 8.962%, algorithm core·s 5.086%를 줄였고 시간은
> 3.979% 늘었다. Effective Full-open은 999회다.
>
> Map5 Adaptive 첫 attempt는 global OOM으로 종료 후 retry 성공했다(FSM anon
> RSS 약 6.60GiB, swap 포화, 외부 Node 약 4.9GiB). 따라서 최종 planner 행은
> 300개지만 infrastructure first-attempt 안정성은 299/300이다.
>
> **대역폭 주의:** 위 payload는 ROG-Map 입력만 포함한다. FSM이 full raw를
> 별도 구독하므로 전체 통신량 감소는 아직 주장할 수 없다. 다음은 bounded
> witness side-channel/in-filter verdict로 중복 raw 구독을 제거하고 total
> subscriber bytes를 계측하는 것이다. 100/100 Wilson 하한은 96.30%,
> Sector-unsafe/Adaptive-safe 2건의 exact McNemar p=0.5라 population 보장이나
> 유의한 안전 우위도 아니다. 상세는 viability §8.45와
> `docs/nearfield_prefilter_raw_final_20260901.md`, raw/summary는
> `results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_{raw,summary}_20260901.csv`다.

> [!IMPORTANT]
> **2026-08-31 near-field hard gate 4단계와 passage 계측 완료.**
> Long-lived trajectory도 새 accepted raw scan을 0.10초 cadence로 latest-only
> 검사한다. Map7 Full smoke에서 331건(NEW_SCAN 183, NEW_GENERATION 148)을
> skip 없이 처리했고 worker 평균/최대는 5.601/23.933ms였다.
>
> Worker-private deterministic replay로 r=0.20 future-tail OCCUPIED를 정확히
> 1건 검출했다. Default-off hard gate는 committed generation 일치,
> result age<=0.20초, cloud-seq lag<=1, checked time-range 포함을 모두 요구한다.
> Entry replay는 brake 1회 뒤 안전 완주했고, current-body replay는 내부 거리
> 증가·0.02m progress·exit·no-reentry 조건을 만족해 EGRESS로 brake 없이
> 완주했다. Replay 없는 enforce smoke도 NO_HIT 308, false brake 0이었다.
> 이는 Map7 n=1 기능 증명이지 실제 contact-correlated 검출이나 population
> 안전 보장이 아니다.
>
> RViz 왼쪽 치우침은 CIRI face의 obstacle/boundary provenance를 추가해 실제
> obstacle-derived 양측 통로만 계측하도록 고쳤다. Exp/Backup 양쪽에 passage
> balance를 구현했지만 Exp+Backup 2e6/2e5는 180초 timeout으로 기각했다.
> Exp-only 2e4는 기능상 완주하고 독립 baseline 대비 평균 imbalance가 약
> 13% 줄었으나 guard brake 증가와 physical clearance 저하가 함께 보여 채택하지
> 않았다. Map7 3모드 smoke는 Full/Sector/Adaptive 모두 완주, static contact
> 0/1/0, Adaptive Full-open 4회였다.
>
> 후속 Map7 세 모드 각 n=10 cgroup campaign은 30/30 first-attempt 완주,
> static-safe, speed/perf/cgroup-valid, retry 0이었다. 평균시간은
> 85.030/88.114/88.130초, worst clearance는
> +0.205/+0.000905/+0.233m다. 따라서 n=1 Sector contact는 반복되지 않았지만
> Sector run7의 거의 0인 양의 margin과 live-cloud-only 후보 2회는 위험 신호다.
> Adaptive는 Full 대비 algorithm/end-to-end CPU 8.465/6.000%, payload
> 47.538%, points/s 36.401%를 줄였고 시간은 3.646% 늘었다. Effective Full-open은
> 87회(8.7/run)다. 같은 바이너리 default-off n=10 control이 없으므로 passage
> centering 효과의 인과 증거는 아니며 후보는 계속 미채택이다.
>
> 모든 새 기능은 default off이고 표준/실사용 tight_v7 profile은 그대로다.
> Raw-cloud CIRI도 계속 false/non-authoritative다. 상세는 viability §8.44,
> `docs/near_field_hard_gate_and_passage_centering_20260831.md`, 요약 CSV는
> `results/near_field_hard_gate_and_passage_centering_summary_20260831.csv`와
> `results/passage_center_exp_w2e4_seed7_three_mode_n10_cgroup_summary_20260831.csv`다.

> [!IMPORTANT]
> **2026-08-31 Map7 recent-hit near-field shadow 구현·n=20 완료.**
> Full Map7 blind-footprint 반례를 겨냥해 최근 1.5초 raw hit와 committed
> body+1초 tail을 0.01초 간격, 반경 0.20m로 비교하는 default-off shadow를
> 추가했다. Raw window는 commit enqueue 시점으로 고정되고, 누적·변환·AABB
> crop·KD-tree는 별도 latest-only worker에서만 돈다. 실사용 tight_v7과 비행
> 결정은 바뀌지 않았고 최종 상태명도 known-free 오해를 막기 위해 `NO_HIT`다.
>
> Full Map7 n=20은 20/20 완주·static-safe, 속도 위반 0이었다. Shadow는
> 2,305건을 skip 없이 처리했고 평균/최대 9.979/42.228ms, 평균 source/crop
> point는 442,259/3,597개였다. 그러나 실제 접촉이 재현되지 않아 r=0.20
> 검출 성공은 아직 미증명이다. r=0.40 sensitivity n=1에서는 7건 OCCUPIED를
> 검출하면서 비행은 78.49초 안전 완주해 wiring과 비권위성을 확인했다.
>
> RViz의 왼쪽 장애물 치우침도 별도 원인으로 확인했다. Full은 전체 관측일
> 뿐 passage centre 목적이 아니다. 현재 clearance 비용은 v<=1.5 full,
> 1.5~2.0 fade, v>=2.0 zero라 순항 중에는 A*/CIRI의 한쪽 seed와 시간·smooth
> 목적이 그대로 남는다. 다음은 bilateral clearance 계측 후 실제 양면 통로에
> 한정한 face-balance/medial-axis 후보이며, ungated clearance 재도입은 아니다.
> 상세는 viability §8.43과
> `docs/near_field_shadow_map7_n20_and_path_bias_20260831.md`다. Hard gate 전에는
> new-scan cadence shadow와 실제 contact-correlated/deterministic replay가 먼저다.

> [!IMPORTANT]
> **2026-08-31 cgroup-accounted 최종 n=10 완료, Full blind-footprint 반례 발견.**
> Speed-gated nearest-face 후보의 Map1-10 x Full/Sector/Adaptive x n=10은
> 300/300 first-attempt·run/speed/perf/cgroup-valid, retry/OOM 0이다.
> Completion은 100/99/100, 권위 source-static-PCD safety는 99/100/100이다.
> 평균시간은 73.892/72.723/73.815초, worst clearance는
> -0.144/+0.047/+0.106m다.
>
> 새 cgroup v2 계측에서 평균 algorithm core·s는
> 90.175/75.633/78.249, end-to-end는 106.278/91.946/94.226이다. Adaptive는
> Full 대비 algorithm CPU 13.226%, end-to-end CPU 11.340%, processed payload
> 56.346%, points/update 17.481%, map time/update 25.591%를 줄였고 시간 변화는
> -0.104%다. PSS는 세 모드 모두 약 3.2/3.6GiB라 메모리 절감은 아니다.
>
> Sector Map3 run7의 207.36초 미완주는 FSM PSS 8.22GiB, available 462MiB,
> swap 포화와 PSI 93.34/87.66%가 동반된 infrastructure-contaminated run이다.
> 건강한 replay는 61.20초에 완주·충돌 0이었다. 반면 Full Map7 run4는
> 6.121초, 0.01155m/s, static clearance -0.1437m의 실제 접촉이다. 최신 map
> guard는 SAFE였지만 장애물이 LiDAR blind 0.1m 안(거리 0.0563m)이라 local
> map/CIRI face가 없었다. 저속 nearest-face 비용은 full weight였어도 입력
> face가 없어 작동할 수 없었다. Replay는 safe라 관측 빈도는 1/10이다.
>
> 다음 구현은 static-PCD oracle을 쓰지 않고 최근 1~2초 raw hit를 bounded
> near-field witness로 유지해 body/short-tail 진입을 hard gate하는 것이다.
> 이미 footprint 안이면 거리 단조 증가 egress만 허용해야 liveness를 보존할
> 수 있다. 먼저 shadow, Map7 Full n>=20, 3-mode n=3, 마지막 300회 순서다.
> Map3 같은 PSI 오염 run의 automatic infrastructure retry도 별도 필요하다.
>
> Adaptive 100/100 Wilson 하한은 96.301%이고 Full safety와의 exact McNemar는
> one discordance라 p=1.0이다. Population 100%, 유의한 안전 우위, 이번
> n=10에서 Sector 안전 저하를 주장하면 안 된다. 상세는 viability §8.42와
> `docs/final_speedgated_cgroup_n10_and_failure_forensics_20260831.md`, raw/summary는
> `results/final_speedgated_cgroup_3mode_seed1_10_n10_{raw,summary}_20260831.csv`다.
> Raw-cloud CIRI는 계속 false/non-authoritative이고 NaN, `obs_skip_num` no-op,
> `DRONE_R=robot_r` 지표 한계도 남아 있다.

> [!IMPORTANT]
> **2026-08-30 저속 nearest-face clearance shaping 후보와 90회 n=3 gate 완료.**
> 최종 n=10 Map10 Adaptive의 `+0.038m` 저여유는 freshness/ACK 문제가 아니라
> 저속 terminal/backup 구간의 trajectory preference/coverage 문제였다. 먼저
> 0.10m hard terminal gate를 시도했지만 반복 reject가 certified-stop liveness
> trap을 만들고 속도 제한형도 timeout을 내서 완전히 원복했다.
>
> 채택 후보는 CIRI 모든 face를 합산하던 기존 soft clearance를 normalized
> nearest face 하나로 바꾸고, 누락됐던 BackupTrajOpt에도 동일 비용을 적용한다.
> `penna_clr=1e6`, margin 0.10m, v<=1.5m/s full weight, 1.5~2.0m/s cubic fade,
> v>=2.0m/s zero이며 speed-envelope gradient도 포함한다. 파라미터 미지정
> 전역 동작은 off이고 tight_v7 검증 profile 두 개에 후보값을 명시했다.
>
> Speed-gated maps9-10 집중 n=3은 6/6 safe였다. 이어진 rotating-order
> map1-10 x Full/Sector/Adaptive x n=3은 90/90 first-attempt·run/speed/perf
> valid, retry/OOM 0이다. Full/Adaptive는 각각 30/30 완주·safe, Sector는
> 29/30 완주·27/30 safe다. Map7 Sector에 timeout 1회와 완주 충돌 1회,
> Map10 Sector에 완주 충돌 1회가 있었고 동일 Adaptive는 모두 safe다.
> 평균 시간은 73.33/75.64/76.02초, worst clearance는
> +0.145/-0.172/+0.153m다. Map10 Adaptive는 기존 +0.038m에서 +0.225m다.
>
> Adaptive는 Full 대비 points/update 15.79%, map Hz 28.80%, processed
> payload 52.14%, total/update 19.65%, update 13.67%, FSM CPU 16.53%를
> 줄였고 시간은 3.67% 늘었다. Effective Full open은 348회(11.6/run)다.
> Exact matched McNemar는 Full-Sector/Sector-Adaptive/Full-Adaptive가
> 0.25/0.25/1.0이고 30/30 Wilson 95% 하한은 88.65%다. 따라서 n=3 후보
> gate일 뿐이며 새 최종본 선언 전 같은 바이너리 300회 n=10이 남았다.
>
> 상세는 viability §8.41과
> `docs/speed_gated_nearest_face_clearance_n3_20260830.md`, raw/summary는
> `results/speed_gated_nearest_face_clearance_3mode_seed1_10_n3_{raw,summary}_20260830.csv`다.
> 이번에 face-summed clearance 설계와 BackupTrajOpt 미커버는 수정됐다.
> 별도 NaN 버그, `obs_skip_num` no-op, `DRONE_R=robot_r` 지표 한계는 남아
> 있고 raw-cloud CIRI는 계속 false/non-authoritative다.

> [!IMPORTANT]
> **2026-08-29 감속 one-shot Full refresh와 최종 300회 완료.**
> Seed9 잔여 접촉은 5.893초, 0.083m/s, source-PCD clearance -0.009641m에서
> 확인됐다. Sector map이 약 0.2초마다 정상 commit돼 pre-stale trigger는
> 닫혀 있었고 replan도 성공해 failure guard가 열리지 않았다. 기존 stall
> state도 너무 늦었다. 즉 원인은 ACK loss나 same-map coalescing이 아니라
> 성공 replan 뒤 high→low-speed blind-sector transition gap이다.
>
> Native C++ Adaptive filter에 3.0m/s에서 무장하고 1.5m/s 이하 감속 시
> 최신 uncropped Full scan 한 장만 uncapped로 보내는 hysteretic one-shot을
> 추가했다. 기존 generation/process ACK를 사용하며 다시 3.0m/s를 넘기 전에는
> 재무장하지 않는다. 전역 기본값은 기존 ablation 재현성을 위해 0/off이고,
> 검증 프로파일은 runner의
> `--adaptive-slowdown-full-refresh-v 1.5`와
> `--adaptive-slowdown-full-refresh-rearm-v 3.0`을 명시한다.
>
> Focused seed9 Adaptive n=10은 10/10 완주·source-static-PCD 충돌 0,
> worst +0.179m였다. 이어진 rotating-order map1-10 x 3-mode x n=10은
> 300/300 first-attempt·run/speed-valid, retry/OOM 0이었다. Full/Adaptive는
> 각각 safety-qualified 100/100이다. Sector는 100/100 완주했지만 seed9
> 충돌 1회로 safe 99/100이다. 평균 Full/Sector/Adaptive 시간은
> 70.97/71.49/75.81초, worst clearance는 +0.150/-0.175/+0.038m다.
>
> Adaptive는 Full 대비 points/update 14.94%, map Hz 30.50%, processed
> payload 52.25%, total/update 19.10%, FSM CPU 17.66%를 줄였고 시간은
> 6.81% 늘었다. Effective Full open 1,198회, slowdown trigger/frame/commit
> ACK는 4,816/4,711/4,706회다. 종료 순간 pending 5건은 모두 안전 완주한
> 마지막 frame right-censoring이며 supersede 0이다. Exact matched McNemar는
> Full-Sector/Sector-Adaptive 모두 p=1.0이고 100/100 Wilson 95% 하한은
> 96.30%라 population 100% 주장은 금지한다.
>
> 상세는 viability §8.40과
> `docs/adaptive_slowdown_full_refresh_final_n10_20260829.md`, 최종 raw/summary는
> `results/final_slowdown_refresh_3mode_seed1_10_n10_{raw,summary}_20260829.csv`다.
> Raw-cloud CIRI는 계속 false/non-authoritative이고 `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표
> 한계도 그대로다.

> [!IMPORTANT]
> **2026-08-29 bounded same-map replan coalescing은 구현/검증했지만 표준 채택 보류.**
> map commit보다 빠른 성공 `ReplanOnce` 중복을 줄이기 위해 같은 map version과
> trajectory generation을 병합했다. 새 map까지 무기한 생략한 첫 후보는 seed9
> Adaptive가 waypoint 2/5, 180초 timeout에 걸려 기각했다. 0.10초가 지나면
> same-map replan을 강제하는 제한형은 seed9 smoke 3/3, maps5/8/9 crossed A/B
> 후보 15/15, 전체 map1-10 3-mode n=3의 Adaptive 30/30을 완주했고 정적 충돌
> 0이었다.
>
> 전체 n=3은 90/90 first-attempt·run/speed-valid, retry/OOM 0이다. Full과
> Adaptive는 각각 30/30 완주·source-static-PCD 충돌 0, Sector는 30/30
> 완주지만 seed8 정적 충돌 1회였다. 평균 Full/Sector/Adaptive 시간은
> 69.86/72.19/75.21초, worst clearance는 +0.219/-0.169/+0.043m다. Adaptive는
> Full 대비 map Hz 35.08%, points/update 15.76%, total/update 20.72%, update
> 13.13%, processed payload 56.98%, FSM CPU 21.37%를 줄였지만 시간은 7.65%
> 늘었다. Effective full open은 344회다.
>
> 따라서 same-map 기능은 default false인 실험 코드로 보존하고, 검증된 표준
> `tight_v7` 프로파일은 default-off로 복원했다. 테스트한 후보는 명시적인
> `*_replan_coalesce_bounded.yaml`에만 있다. 다음 우선순위는 seed9 Adaptive의
> +0.043m 저여유와 41.3 brakes/run, 48.56초 recovery를 만드는 freshness/map
> commit cadence 분석이다. 상세는 viability §8.39와
> `docs/bounded_same_map_replan_coalesce_20260829.md`, raw는
> `results/replan_coalesce_bounded_3mode_seed1_10_n3_raw_20260829.csv`다.
> 최종본까지 최소 8~12시간의 focused n=10 + 전체 300회 재검증이 남았다.
> Raw-cloud CIRI는 계속 false/non-authoritative이며 `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표
> 한계도 그대로다.

> [!IMPORTANT]
> **2026-08-28 교차균형 n=10 300회와 ROG-Map 메모리 worker 수정 완료.**
> 최종 수정 바이너리로 map1-10 x Full/Sector/Adaptive x n=10을 실행했고
> 300/300 모두 first-attempt 완주, run/speed-valid, retry/OOM 0이었다.
> Full과 Adaptive는 각각 100/100 source-static-PCD 무충돌이었다. Sector는
> 100/100 완주했지만 map7·8·9에서 각 2회씩 정적 충돌해 safe 94/100이었다.
> 동일 6개 map/run의 Adaptive는 모두 안전했다. 전체 순서를 연속 회전해 각
> 모드의 1/2/3번째 위치가 33~34회로 균형됐고, Full-Sector 및
> Sector-Adaptive matched discordance의 exact McNemar는 각각 `p=0.03125`다.
>
> 첫 n=10은 map5 Full timeout으로 132행에서 중단했다. Degenerate
> collision-away 방향에 goal-order fallback을 넣되 기존 stop-only 8방향
> trajectory/viability certificate는 유지했고, map5 Full 집중 n=8은 8/8
> 통과했다. 다만 새 `direction_source=goal_fallback`은 자연 발생 0이므로
> 직접 인과 증거로 주장하지 않는다.
>
> 두 번째 n=10은 277행 뒤 map10 run3 Full이 3.23→8.43 GiB RSS로 증가해
> kernel OOM kill됐다. DDS cloud callback의 PCL 변환+map/COW/ACK를 executor
> thread에서 동기 수행하던 구조가 원인이었다. Callback은 latest-only
> enqueue만 하고 전용 단일 worker가 무거운 작업을 담당하도록 수정했다.
> 집중 map10 Full/Adaptive n=3+n=3은 6/6, peak RSS 3.24 GiB 이하였고, 최종
> 300회 peak RSS 3,263.95 MiB, memory PSI 0으로 OOM이 재발하지 않았다.
>
> 최종 평균 Full/Sector/Adaptive 시간은 71.61/70.05/74.33초다. Adaptive는
> Full 대비 map update frequency 33.08%, points/update 16.68%,
> total/update 20.63%, processed payload 56.08%, FSM CPU 17.05%를 줄였고
> 시간은 3.80% 늘었다. Effective full-view open은 1,160회(11.60/run)다.
> Payload는 ROG-Map processed application payload이며 NIC/무선/DDS wire
> bandwidth가 아니다. 상세는 viability §8.38 및
> `docs/counterbalanced_n5_n10_validation_20260828.md`, 최종 raw는
> `results/counterbalanced_map_worker_3mode_seed1_10_n10_raw_20260828.csv`다.
> 100/100의 Wilson 95% lower bound는 96.30%이므로 population 100% 주장은
> 금지한다. Raw-cloud CIRI default false/non-authoritative,
> `obs_skip_num` no-op, NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 base-NO_PATH 집중 n=20과 최종 payload-aware 3-mode n=3 gate 완료.**
> 수정 뒤 map9 Adaptive를 20회 추가 실행했고 20/20 first-attempt 완주,
> contact/static collision 0, speed-valid였다. 평균/범위 시간은
> 90.07/76.71~122.25초, worst clearance +0.190m였다. Natural base-NO_PATH
> local-escape arm은 0이므로 이 20회는 regression/liveness 증거이며, 직접 분기
> 증거는 앞서 default-off fault hook 두 번에서 확보한 3 NO_PATH→1 arm→
> 202-sample 0.6m commit이다.
>
> 같은 최종 바이너리 map1-10 x Full/Sector/Adaptive x n=3은 90/90
> first-attempt 완주·speed-valid, timeout/retry/OOM 0이다. Full과 Adaptive는
> safety-qualified 30/30이다. Sector는 30/30 완주했지만 map7 1회, map9 2회,
> map10 1회가 접촉해 safe 26/30, live events 9, static collision 4였다.
> 같은 map/run Adaptive는 네 번 모두 안전했다. 평균 시간은
> 71.43/71.53/74.39초, worst clearance는 +0.193/-0.181/+0.210m다.
>
> Full/Sector/Adaptive processed payload 평균은 5.069/1.569/2.351 MiB/s다.
> Map별 동일가중 Full 대비 감소율은 Sector 69.43%, Adaptive 54.24%다.
> 전체 mode 평균 비율에서 Adaptive는 points/update 15.68%, total/update
> 21.80%, update 15.09%, FSM CPU 14.62%, planner+filter core-seconds 8.65%를
> 줄였고 mission time은 4.14% 늘었다. Adaptive effective full-view open은
> 372회(12.4/run)다. 이 payload는 ROG-Map processed application payload이며
> NIC/무선/DDS wire bandwidth가 아니다.
>
> Matched safety discordance는 Full-Sector 4:0, Sector-Adaptive 0:4이고 exact
> McNemar는 둘 다 `p=0.125`다. 고정 Full→Sector→Adaptive 순서라 exploratory
> matched-block 결과다. Full/Adaptive 30/30의 Wilson 95% lower bound는
> 88.65%라 population 100% 주장은 금지한다. 상세는 viability §8.37,
> `docs/final_payload_base_no_path_n3_20260827.md`, raw는
> `results/final_base_no_path_seed9_adaptive_n10{a,b}_raw_20260827.csv`와
> `results/final_payload_base_no_path_3mode_seed1_10_n3_raw_20260827.csv`다.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 processed-payload bandwidth 계측과 base-NO_PATH 복구 완료.**
> ROG-Map update에 실제 사용된 `PointCloud2.data` bytes/point_step을 기존
> performance CSV에 기록하고 runner가 frames/s, points/s, MiB/s, Mbit/s를
> 계산한다. 이는 DDS/RTPS overhead·retransmission·latest-only overwrite를
> 제외한 processed application-payload이며 NIC/무선 대역폭이 아니다.
>
> Map1-10 x 3-mode n=1에서 Full/Sector/Adaptive 평균은
> 5.077/1.977/2.748 MiB/s였다. Map별 Full 대비 감소율 평균은 Sector 64.44%,
> Adaptive 49.02%다. Full 10/10, Sector 9/10, Adaptive 9/10 완주였고 map9
> Sector는 접촉 후 timeout, Adaptive는 contact 0인 채 waypoint2/5에서
> timeout했다. Adaptive timeout의 7.324 MiB/s는 92.19% full-open이 만든
> 결과이지 대역폭 부족의 원인이 아니다.
>
> Map9 Adaptive는 local escape 뒤 base A* `NO_PATH`, guarded vertical lift
> reject 후 남은 horizontal budget을 쓰지 않고 permanent hold에 들어가
> 같은 실패를 140초/13,355회 반복했다. Base vertical budget 소진 뒤 기존
> 8방향 certified local escape로 연결하도록 수정했다. 자연 map9 n=8은 8/8
> 완주·contact 0·speed-valid였으나 새 분기를 밟지 않았다. Default-off fault
> hook은 두 독립 smoke에서 각각 `NO_PATH` 3회 뒤 202-sample guard를 통과한
> 0.6m escape를 commit했다. 둘 다 완주/contact 0/speed-valid였고 시간은
> 65.75/60.19초, worst clearance는 +0.311m였다. v2 CSV가 injection 1,
> forced failure 3, base escape arm 1, local commit 1을 직접 보존한다.
>
> 이 절에서 예정한 **최종 바이너리 map1-10 x Full/Sector/Adaptive x n=3**은
> 위 최신 배너와 viability §8.37에서 완료됐다. 이 절의 구현 상세는 §8.36,
> `docs/payload_bandwidth_and_base_no_path_escape_20260827.md`, raw는
> `results/bandwidth_3mode_seed1_10_n1_raw_20260827.csv`와 matching
> `base_no_path_*_20260827.csv`를 볼 것. Population 100% 주장은 금지하며
> raw-cloud CIRI default false/non-authoritative와 기존 known limitations는
> 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 native C++ filter latest-only worker 최적화와 36-run 회귀 완료.**
> Maps9-10 Adaptive의 100초대 tail은 `MAP_STALE -> brake -> fresh-map replan`
> 반복에 집중됐다. Guard hold 2.5→0.5초 후보는 map9 3/3을 빠르게 끝냈지만
> map10 첫 run에서 live contact 2, static collision 1, clearance -0.157m를
> 만들어 폐기했다. Default/profile에는 반영하지 않았다.
>
> 채택 구현은 safety threshold를 전혀 바꾸지 않고 native C++ filter의 raw-cloud
> DDS callback을 enqueue-only로 만들고 point filtering + reliable publish를
> 별도 latest-only worker로 옮겼다. Filter/guard/ACK state는 mutex로 직렬화하고
> 종료 시 pending drop + join한다. Maps9-10 Adaptive n=3은 6/6 first-attempt,
> contact 0, 평균 88.01초로 직전 102.87초보다 14.45% 짧았다. Brake/run은
> 51.50→35.17, recovery active는 54.60→41.08초였다.
>
> 이어진 map1-10 x Full/Sector/Adaptive x n=1은 30/30 first-attempt 완주,
> live/static contact 0, speed-valid였다. 평균 시간은 72.08/70.85/72.86초다.
> 이 n=1에서 Adaptive는 Full 대비 points/update 13.72%, total/update 18.76%,
> update 10.49%, FSM CPU 15.23%, planner+filter core-seconds 10.92%를 줄이고
> mission time은 1.09% 늘었다. Adaptive open은 108회다.
>
> 모든 accepted filter row에서 input callback==processed frame, overwrite 0이므로
> 프레임 폐기가 개선 원인은 아니다. 이전/이후 n=3도 interleaved paired A/B가
> 아니므로 14.45%를 정밀 인과효과로 주장하지 말 것. 직전 n=3의 Sector map9
> contact는 여전히 유효하며 이번 clean n=1로 Sector를 safe로 재분류하지 않는다.
> 상세는 viability §8.35,
> `docs/native_filter_async_latest_optimization_20260827.md`, raw는
> `results/adaptive_async_latest_seed9_10_n3_raw_20260827.csv` 및
> `results/async_latest_3mode_seed1_10_n1_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 stopped-recovery tail 수정 및 현재 바이너리 3-mode n=3 gate 완료.**
> 이전 독립 n=5에서 map8 Full이 154 arm/363 search 뒤 293.79초에 끝난 원인은
> 짧은 certified escape commit마다 topology recovery 전체 상태와 예산을
> 초기화하여 같은 local/vertical 복구를 다시 허용한 것이었다. 이제
> pose-specific blocker만 지우고 episode budget은 보존하며, 같은 goal에서
> 2.0 m XY 진전 후에만 예산을 reset한다. Local escape는 8방향을 현재
> waypoint 진전 순으로 시도하고 local/vertical budget은 한 이벤트에서
> 동시에 소비하지 않는다. 기존 trajectory/stop-viability certificate는
> 약화하지 않았다.
>
> 첫 버전은 map10 Adaptive run3에서 goal 반대 방향 탈출 뒤 300.01초 timeout,
> arm/search/epoch-reset 121/357/116을 내어 폐기했다. 최종 수정 뒤 map10
> Adaptive n=5는 5/5, maps7-10 Full/Adaptive n=3는 24/24 first-attempt,
> contact 0이었다. 현재 바이너리의 map1-10 x Full/Sector/Adaptive x n=3
> 90회는 전부 first-attempt 완주·speed-valid, retry/OOM 0이다. Full과
> Adaptive는 safety-qualified 30/30, fixed Sector는 29/30이다. Sector map9
> run1만 live contact 2, static collision 1, clearance -0.107 m였다.
>
> Adaptive는 Full 대비 points/update 14.52%, total/update 21.68%, update
> time 14.60%, FSM CPU 19.48% 감소했고 mission time은 7.93% 증가했다.
> Effective full-view open은 323회(10.77/run)다. 다만 현재 n=3의 paired
> discordance는 1:0, exact McNemar `p=1.0`, Full/Adaptive 30/30의 95%
> Wilson lower bound는 88.65%이므로 population 100% 주장은 금지한다.
>
> 직전 map8 Full n=10 중 한 process가 약 3.0→9.1 GiB RSS로 증가하고 host
> swap full 상태에서 OOM-kill된 뒤 retry 1회가 성공했다. 최종 90회에는
> OOM/retry가 없었고 원인 allocation은 아직 미확정이다. 상세는 viability
> §8.34와 `docs/goal_ordered_recovery_final_n3_20260827.md`, 최종 raw는
> `results/goal_ordered_final_3mode_seed1_10_n3_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 직전 바이너리 독립 n=5 일반화 gate 완료.** Fresh
> map1-10 x Full/Sector/Adaptive x n=5, order rotation 150회를 수행했다.
> Full 50/50·Adaptive 50/50은 완주, live/static contact 0, speed-valid였다.
> Fixed Sector는 49/50 완주, live contact 1 run/2 events, static collision
> 1 run/1 event, safety-qualified 48/50이었다. Map7 run1 Sector는 contact 없이
> waypoint 4/5에서 300.01초 timeout, paired Adaptive는 80.80초·contact 0으로
> 완주했다. Map8 run1 Sector는 완주했지만 live/static contact가 발생했고
> -0.170 m였으며, paired Adaptive는 69.67초·contact 0·+0.286 m였다.
>
> 유효한 50개 Full/Adaptive pair에서 Adaptive는 points/update 16.41%, map
> total/update 19.31%, update time 11.74%, FSM CPU 17.49%, time-integrated
> FSM+filter CPU work 13.33%를 줄였다. Point kept 59.73%, effective full-view
> open 534회(10.68/run)다. Trajectory-guard ACK 1,336/1,336, pre-stale ACK
> 3,656/3,656이며 retry/pending/supersede/abandon/timeout 0이다.
>
> Full은 50/50을 유지했지만 map8 run2가 guarded A* `NO_PATH` 뒤 topology
> arm/search 154/363회를 소비하고 293.79초에 끝난 liveness tail이 남았다.
> 이는 메모리 문제가 아니다: retry/OOM/FSM swap/PSI 모두 0, 최소 available
> memory 4.65 GiB였다. 다음 engineering target은 hard certificate를 약화하지
> 않고 이 stopped topology search tail을 bound/reuse하는 것이다.
>
> 이번에는 exact paired McNemar도 수행했다. 독립 n=5 safe discordance 2:0은
> `p=0.5`, same-binary n=3+n=5의 5:0도 `p=0.0625`라 아직 유의하지 않다.
> Full/Adaptive 50/50의 95% Wilson lower bound는 92.87%다. 따라서 population
> 100%/flight-ready 주장은 금지하고, 다음 실험은 같은 seed 반복이 아니라
> preregistered held-out map/noise cohort로 갈 것. 상세는 viability §8.33,
> `docs/final_generalization_n5_20260827.md`, raw는
> `results/final_generalization_3mode_seed1_10_n5_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계도
> 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 final DDA 3-mode n=3 + 대형 맵 연산계측 race 수정 완료.**
> 최종 DDA/body-coordinate 바이너리로 map1-10 x Full/Sector/Adaptive x n=3
> (총 90회, order rotation)을 수행했다. Full 30/30·Adaptive 30/30은
> live/static contact 0, speed-valid 30/30이었다. Fixed Sector는 29/30,
> live contact 3 runs/6 events, static collision 3 runs/3 events,
> safety-qualified 27/30이었다. Map9 run2 Sector는 contact 후 300초 timeout,
> paired Adaptive는 89.74초·contact 0·+0.265 m로 완주했다.
>
> 29개 matched metric pair에서 Adaptive는 Full 대비 points/update 17.22%,
> map total/update 20.70%, update time 13.03%, FSM CPU 19.12% 감소했다. 전체
> 30회 time-integrated FSM+filter CPU work는 11.66% 감소, 평균 mission time은
> 5.91% 증가했다. Effective full-view open은 321회이며 원인별 counter는
> overlap되므로 서로 더하면 안 된다.
>
> Map10 Full run1에서 `perf_row_start=472 > perf_row_end=446`인 연산계측
> race도 발견했다. 큰 static map의 ROGMap init이 runner의 4초 대기보다 늦어
> shared performance CSV를 뒤늦게 truncate한 문제다. Runner가 새 log
> generation/header를 기다리고 positive window를 확인한 뒤, teardown 전에
> per-attempt CSV snapshot을 남기도록 고쳤다. Post-fix map10 3-mode n=1은
> generation/window valid 3/3, 완주 3/3, contact 0이다. 이 race는 기존 90회
> 중 computation 한 행만 비웠고 completion/contact/time 판정에는 영향 없다.
>
> 상세 맵별 표와 claim boundary는 viability §8.32 및
> `docs/final_dda_projection_3mode_n3_20260826.md`, raw는
> `results/final_dda_projection_3mode_seed1_10_n3_raw_20260826.csv`와
> `results/perf_generation_seed10_3mode_n1_raw_20260826.csv`를 볼 것.
> Population 100%/flight-ready 주장은 금지하며 McNemar 미검정이다.
> raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계
> 정정도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 recovery branch proof + DDA/body-coordinate 후속 완료.**
> Recovery-only exact-generation ACK retry는 첫 guard full cloud를 한 번
> 강제로 drop했을 때 drop/retry 1/1, exact ACK commit 32, abandon 0으로
> 완주했고, stopped four-way local escape는 첫 방향을 강제로 skip한 뒤 다른
> 방향을 hard certificate로 commit해 완주했다. 두 fault hook은 default-off다.
>
> 이어서 동일 바이너리 map1-10 x Full/Sector/Adaptive x n=5를 수행했다.
> Full 50/50·contact 0, fixed Sector 50/50이지만 live contact 4 runs/10 events와
> static collision 3 runs/3 events, Adaptive 49/50·contact 0이었다. Adaptive
> map10 run4가 +0.041 m static clearance인데도 waypoint 0에서 240초 정지해
> liveness 결함이 남았다. Full map2 run3의 두 `no odom samples` retry는
> `/dev/shm`에 남은 Fast-DDS 파일 17,452개(약 4.5 GiB)와 host memory/swap
> pressure가 원인이었고, planner OOM/accepted-attempt FSM swap은 아니었다.
>
> Physical shell/voxel quantization을 exact occupied-centre distance로 고친
> 뒤에도 map9 Adaptive가 4/5 waypoint에서 정지했고, initial-footprint egress
> 1차안 뒤에는 map8에서 다시 정지했다. 최종 원인은 inflated-grid DDA cell
> centre를 raw physical-body 검사에서도 robot centre로 사용한 좌표 혼용이다.
> 이제 inflated query는 DDA 좌표를 유지하되 raw body distance는 polynomial
> chord 투영점을 쓴다. 초기 footprint 셀은 candidate가 그 셀에 더 가까워지지
> 않을 때만 bounded egress에서 무시하며 continuous free tail이 여전히 필수다.
>
> 최종 forced footprint 시험은 injection/commit 1/1·contact 0, map8 Adaptive
> n=5는 5/5·contact 0, 최종 map8-10 Full/Adaptive n=3은 18/18·contact 0·
> speed-valid 18/18·retry 0이다. Adaptive는 이 dense gate에서 Full 대비
> points/update 14.34%, map total/update 17.85%, FSM CPU 15.62%를 줄였고 평균
> 시간은 3.78% 길었다. Adaptive arm/open은 4/4회다. 상세는 viability §8.31,
> `docs/guard_recovery_egress_projection_v7_20260826.md`, raw는
> `results/dda_projection_dense_full_adaptive_n3_raw_20260826.csv`를 볼 것.
>
> 이것은 관측된 결함의 local regression 통과이지 population 100%나
> flight-ready 보장이 아니다. McNemar 미검정, raw-cloud CIRI default
> false/non-authoritative, `obs_skip_num` no-op, NaN/clearance-penalty 결함,
> BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계 정정은 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 v7 속도 hard bound + stopped recovery 후속 완료.** 아래
> reliable-link n=3의 Full seed7 run3 `10.027 m/s`는 planner가 실제 발행한
> 명령이었다. Guard retry가 두 odometry 위치를 표본 수신시각이 아니라 callback
> read 시각 차이(6 ms)로 나눠 가짜 `odom_motion=10.055 m/s`를 만들었다.
> `robot_state_.rcv_time`으로 시간축을 교정했고, guarded candidate exact-max
> time scaling, brake dynamics/max-velocity 검사, polynomial/PositionCommand
> publish 직전 재검사, speed-qualified `run_valid`를 추가했다. 과거 seed10
> contact를 만든 odometry twist 직접 대입은 복원하지 않았다.
>
> 첫 speed-qualified seed6-10 x 3-mode x n=3은 45/45 속도 유효였지만 Full
> seed10 timeout 1회와 Adaptive seed8 166.68초 long-tail을 드러냈다. Recovery
> active 중 exact full-generation ACK가 0.75초 안에 없을 때만 최신 full 하나를
> stop-and-wait 재전송하는 옵션을 넣었다(기본 0/off). 이후 seed8 n=5에서 모든
> ACK가 빠르게 왔는데도 151.77초가 나와, 진짜 원인을 최신 충돌점 방향이
> 뒤집히며 같은 stopped topology를 59.69초 반복한 것으로 확정했다. Local
> recovery는 수평 네 출구를 각 한 번만 검사하고 기존 hard certificate를 통과한
> 첫 candidate만 commit하도록 보완했다.
>
> 보완 후 seed8 Adaptive n=5는 5/5 완주·contact/static collision 0·속도 유효,
> 평균 81.21초, 최대 recovery 2.52초였다. 최종 동일 바이너리 map1-10 x
> Full/Sector/Adaptive x n=1은 30/30 완주, contact/static collision 0,
> speed-qualified 30/30이다. 평균 시간은 71.04/72.05/78.89초. Adaptive는
> Full 대비 points/update 12.88%, total/update 22.91%, update time 16.09%,
> FSM+filter core-seconds 8.86% 감소, 시간 +11.04%였다. Full-view 전환 123회,
> guard episode/ACK 241/241, ACK 최대 0.101465초, retry/supersede/abandon 0이다.
>
> Corridor epoch-reset은 map7 Adaptive에서 실제 1회 실행돼 약 0.64초 뒤
> 회복했다. 하지만 recovery ACK retry와 새 네 방향 local-escape는 최종 표본에서
> trigger되지 않았으므로 직접 branch proof는 아니다. Population 100%,
> flight-ready, zero-tolerance `<=7.000000`을 주장하지 말 것. McNemar 미검정,
> raw-cloud CIRI default false/non-authoritative다. `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계
> 정정도 계속 유효하다. 상세는 viability §8.30 및
> `docs/guarded_velocity_bound_v7_20260826.md`, raw는
> `results/final_multiexit_3mode_seed1_10_n1_raw_20260826.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-26 reliable-link n=3 반복·stationary-defer 기각 — 바로 아래 n=1
> 채택안을 seed6-10 x Full/Sector/Adaptive x n=3으로 반복했다.** 45/45가 current
> runner 기준 valid·first-attempt였다. Full/Adaptive는 각각 15/15 완주, contact
> 0, static-PCD collision 0이었다. Fixed Sector는 13/15 완주, contact run 3개,
> event 5회였다. 평균 시간은 84.85/101.57/82.31초이며 Sector 평균에는 seed10의
> 240초 timeout 2개가 포함된다.
>
> Adaptive는 Full 대비 points/update 14.83%, map total/update 15.15%, 전체
> mapping point/work 35.97%/36.20%, FSM+filter core-seconds 7.46%를 줄였고 이
> 표본의 평균 mission은 3.00% 짧았다. Pre-stale generation 1,274개 중 1,273개가
> exact ACK됐으며 supersede/timeout은 0, 종료 시 pending 1개다. Recovery gate
> 502/502는 모두 ACK를 받았다.
>
> 남은 brake rejection marker 906개 중 707개(78.0%)가 speed<=0.05 m/s 정지
> proxy에서 발생했다. Passive-stop 안정화 전에 zero-displacement 후보의 중복
> map/grid 검사를 미루는 fail-closed stationary-defer를 구현해 seed9 3회
> 시험했지만 평균 152.23초로 개선이 입증되지 않았다. 원복 뒤 isolated smoke도
> 213.05초여서 post-build 실행 regime 교란이 있으며 후보의 인과적 악화라고
> 단정하지 않는다. 안전하게 후보를 기각했고 planner source는 tracked baseline과
> byte-identical하게 원복·재빌드했다. Parser marker만 재현성을 위해 남겼다.
>
> 새 핵심 결함은 Full seed7 run3의 `max_speed_mps=10.027`이다. PerfectDrone은
> command velocity를 odometry로 그대로 복사하므로 monitor 노이즈만으로 볼 수
> 없다. 현재 `run_valid`는 v=7 제한을 검사하지 않으므로 15/15는 완주/contact
> 기준이지 speed-qualified 100%가 아니다. 다음은 속도 exceedance의 trajectory
> context를 저장하고 publication hard validation을 넣은 뒤 동일 3-mode gate를
> speed-qualified로 재실행하는 것이다. population 100%/flight-ready 보장이
> 아니며 McNemar 미검정, raw-cloud CIRI default false/non-authoritative다. 상세는
> viability §8.29 및
> `docs/reliable_link_n3_and_stationary_defer_rejection_20260826.md`를 볼 것.

> [!IMPORTANT]
> **2026-08-26 reliable filtered-link local gate — 아래 2026-08-25 exact ACK
> 작업의 후속 원인 제거를 완료했다.** 이전 Adaptive seed6-10 n=1의 delivered
> generation ACK는 최대 0.1034초였지만 best-effort `/cloud_sector` hop에서
> 70/582 generation이 유실되어 superseded됐고 SLA timeout이 26회 발생했다.
> guard attribution은 `main_pre MAP_STALE` 184회, recovery gate 225회,
> active 합 247.457초였다.
>
> ACK 미수신 뒤 Full을 한 번 더 보내는 후보는 5/5·contact 0이고 timeout을
> 26->5로 줄였지만 full frame 582->657, guard 225->258, stale 184->223,
> active 합 247.457->291.722초, 평균 시간 96.408->104.306초(+8.19%)로
> 악화돼 기각했다. retry age는 default 0/off이고 최종 gate에서 사용하지 않았다.
>
> 채택 후보는 native C++ filter publisher와 ROG-Map subscriber 사이 내부
> hop만 reliable depth-1로 맞춘다. 실행 파일과 ROG-Map option 기본값은 false,
> 새 `_filtered_reliable.yaml` 및 runner flag에서만 opt-in이다. 기존 프로파일,
> simulator->filter best-effort 입력, exact ACK/certified resume, raw-cloud CIRI
> default false/non-authoritative는 바뀌지 않았다.
>
> 최종 seed6-10 x Full/Sector/Adaptive x n=1은 15/15 valid, first-attempt
> 완주였다. Full/Adaptive는 각 5/5·contact 0·static-PCD collision 0이고 fixed
> Sector는 seed8에서 contact/static collision 1회가 있었다. 평균 시간은
> 84.16/83.94/86.02초다. Adaptive는 Full 대비 points/update 17.38%, map
> total/update 14.50%, 전체 mapping point/work 37.78%/35.61%, FSM+filter
> core-seconds 9.59%를 줄였고 시간 penalty는 2.21%였다.
>
> Adaptive pre-stale generation은 393/393 exact ACK, superseded/timeout/final
> pending 0이다. 이전 best-effort n=1 대비 평균 시간 -10.78%, guard gate
> 225->195, stale 184->164, recovery active 합 -16.90%다. 그러나 이는 n=1
> local regression gate라 population 100%/flight-ready 보장이 아니며 McNemar를
> 하지 않았다. 다음은 이 opt-in 프로파일의 map-labelled 반복 검증이고, 그 뒤
> 남은 brake rejection/stop-replan 비용을 분해한다. 상세는 viability §8.28 및
> `docs/reliable_filtered_link_guard_duty_v7_seed6_10_n1_20260826.md`를 볼 것.

> [!IMPORTANT]
> **2026-08-25 exact full-generation ACK + certified resume — 바로 아래
> pre-stale proxy의 다음 구현을 완료했다.** Adaptive full refresh가 reliable
> request sequence와 exact `PointCloud2` stamp를 보내고, ROG-Map이 그 scan을
> 실제 처리한 뒤 exact stamp/map-version ACK를 발행한다. guard recovery는
> post-edge full의 exact ACK, fresh map/odom, certified stop, 새 `PlanFromRest`,
> 새 trajectory certificate 뒤에만 재개한다. oldest unresolved request가
> 0.75초 SLA를 넘기면 정상 비행을 계속하지 않고 certified brake 경계로
> 들어간다. fresh candidate가 기하학적으로 거부되면 기존 topology blocker가
> 다른 homotopy를 탐색한다. ACK loss 자체로 가짜 obstacle을 만들지는 않는다.
>
> 최종 seed6-10 x Full/Sector/Adaptive x n=1 15회는 모두 valid, first attempt,
> 완주·live contact 0·static-PCD collision 0이다. retry/OOM/FSM swap/PSI도 0이다.
> Adaptive 평균 시간은 Full 84.00초 대비 96.41초(+14.77%)이고,
> update-weighted points/update 16.12%, map total/update 15.52%, observed map
> rate 32.47%, time-weighted FSM CPU 24.68%를 줄였다. 같은 5개 맵의 total
> mapping point/work는 34.99%/34.52% 감소했다.
>
> pre-stale full 582개 중 512개가 exact ACK, 70개가 superseded, final pending
> 0이다. delivered ACK latency는 평균 0.0436초, 최대 0.1034초였다. 따라서 아래
> version-proxy 최대 11.245초는 특정 full cloud 처리 latency가 아니었다. 같은
> 실행의 기존 proxy는 582/582 advance였지만 exact ACK는 512/582뿐이었다. 다만
> best-effort cloud loss는 실제이며 0.75초 SLA timeout marker가 26회 관측됐다. recovery
> gate는 225/225 exact ACK 뒤 재개했고 모든 run이 완주했다. Full/Sector는
> generation stream을 광고하지 않아 새 gate 지표가 전부 0이다.
>
> 실행 파일/planner option 기본값은 계속 off이고 strict Adaptive runner만
> 켠다. raw-cloud CIRI도 계속 default false/non-authoritative다. 이 결과는
> late-map n=1 local gate이며 population 100%/flight-ready 보장이 아니고
> McNemar 미검정이다. guard duty도 79.60-94.68%로 남았다. 다음 과제는 ACK
> threshold를 숨기는 튜닝이 아니라 repeated guard episode/stop-replan 비용을
> 원인별로 줄이는 것이다. 상세는 viability §8.27,
> `docs/generation_ack_certified_resume_v7_seed6_10_n1_20260825.md`, raw는
> `results/generation_ack_final_3mode_seed6_10_n1_raw_20260825.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-25 pre-stale full refresh n=3 gate — 바로 아래 2026-08-24
> first-brake 반례의 다음 구현을 완료했다.** Adaptive C++ filter가 map commit
> age 0.25초에서 complete scan을 한 map version당 한 번만 보내고, 이후
> `commit_version > source_version`을 version-advance ACK proxy로 기록한다.
> 실행 파일 기본값은 0/off이고 strict campaign runner만 0.25초를 쓴다. 이 ACK는
> 특정 frame content의 처리 완료 token이나 formal freshness certificate가 아니다.
>
> seed7 threshold 0.35/0.25초 각 n=3은 모두 완주·contact 0이었다. 0.25초가 실제
> trigger 0.403초, ACK 0.175초, mean mission 102.68초로 더 나아 채택했다. 이어
> order-crossed seed1-10 x n=3 x Full/Sector/Adaptive 90회는 모두 valid,
> one attempt, raw complete였다. Full/Adaptive는 각각 **30/30·contact 0**, fixed
> Sector는 **30/30이지만 seed9/10의 2 runs에서 3 contact events**였다. 이전
> Adaptive seed7 stale-map first-brake contact는 재발하지 않았다.
>
> Full 대비 Adaptive는 update-weighted points/update 18.90%, map total/update
> 23.86%, map update time 15.12%를 줄였지만 mean mission은 76.63->103.26초,
> **+34.75%** 길어졌다. pre-stale frame/version advance는 2,369/2,369, pending
> 0, 평균 trigger/ACK latency는 0.386/0.207초였지만 최대는 3.150/11.245초다.
> late seed guard duty도 80-92%다. 다음 구현은 threshold/cap 추가 튜닝이 아니라
> **content-specific request/generation ACK + fresh-map successful replan 뒤 certified
> resume**, SLA miss 시 **certified stop-and-topology-reroute 1회**다. 같은 version
> full frame flood와 blind hold 축소는 금지한다.
>
> 이 결과는 local n=3 기술 통계이며 population 100%/flight-ready 보장이 아니다.
> McNemar는 수행하지 않았다. raw-cloud CIRI는 계속 default false/non-authoritative다.
> 상세 맵별 표와 forensics는 viability §8.26 및
> `docs/pre_stale_refresh_3mode_v7_n3_20260825.md`, raw는
> `results/prestale025_order_crossed_3mode_v7_n3_raw_20260825.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-24 guard duty attribution 및 first-brake 반례 — 아래 direct
> guard refresh 배너의 “최종 contact 0” 상태를 새 n=1 gate가 반증했다.**
> C++ Adaptive 통계에 direct guard의 실제 `active`와 recovery 뒤
> `hold-only` frame/duty를 분리했다. 기존 5 Hz·2.5초 hold·6,000점 동작은
> 바꾸지 않았다. seed6-10 진단은 5/5·contact 0이었고 active/hold-only
> duty 평균은 59.42%/32.86%여서, 후반 비용은 hold만이 아니라 실제 guard
> 재발이 더 큰 원인임을 확인했다.
>
> guard active 동안만 6 Hz를 허용한 후보도 seed6-10 5/5·contact 0이었지만
> 평균 시간 133.02->163.89초(+23.20%), map total/update
> 26.26->29.45ms(+12.14%)로 악화돼 폐기했다. 옵션 기본값은 0으로, 기존
> 5 Hz를 그대로 쓴다.
>
> 이어 실행한 order-crossed seed1-10 x n=1 x 3-mode 30회는 전부 valid,
> retry/FSM swap/OOM 0이고 세 모드 모두 10/10 완주했다. 그러나 live contact
> run은 Full 0, Sector 1(seed10), Adaptive 1(seed7)이다. Adaptive seed7은
> static-PCD contact는 아니지만 static body clearance가 +0.036m뿐이었고,
> live point는 0.19861m로 0.20m body threshold 안쪽이었다. 따라서 Adaptive는
> 현재 contact-zero 목표를 충족하지 못한다.
>
> 원인은 hold가 아니다. epoch 1787565836.311에 guard가 map age 0.558초의
> `MAP_STALE`을 감지한 뒤 stale map에서 0.529초 brake를 `SAFE`로 승인했고,
> direct true-edge가 새 full scan을 요청했지만 이미 실행 중인 첫 brake의
> endpoint는 바꾸지 못했다. 0.440초 뒤 brake 끝에서 contact가 기록됐다.
> 다음 구현은 0.50-0.55초 stale threshold **이전**에 ACK/version-gated full
> refresh 1회를 보내는 bounded pre-stale 방식이다. hold 단축이나 6 Hz 재적용은
> 금지한다. 상세 맵별 표와 로그 해석은 viability §8.25 및
> `docs/guard_duty_3mode_v7_n1_20260824.md`를 볼 것. raw-cloud CIRI는 계속
> default false/non-authoritative다.

> [!IMPORTANT]
> **2026-08-24 direct trajectory-guard sensing 후속 — 아래 2026-08-23
> 배너들의 “반복 gate 필요”를 실행했다.** 먼저 bounded local horizontal
> escape를 추가했다. certified stop 뒤 A* `NO_PATH`일 때 rejected route 반대
> 방향 0.6 m 후보를 1회만 시도하고, 실패하면 기존 vertical 후보 1회 뒤 hold한다.
> 모든 후보는 기존 trajectory guard/viability를 그대로 통과해야 하며 Full seed7
> n=10은 10/10·contact 0이었지만 local branch 자체는 실행되지 않았다.
>
> 같은 코드의 seed1-10 x n=5 x 3-mode order-crossed 150회에서 Full은
> **50/50·contact 0**, fixed Sector는 **50/50·contact 3 runs**, Adaptive는
> **49/50·contact 1 run**이었다. Adaptive seed7 run2는 emergency brake 중
> 두 번 접촉한 뒤 3/5 waypoint에서 멈췄다. 기존 0.6초 replan-failure burst는
> 실제 guard brake 사이에 닫힐 수 있었다.
>
> `FsmRos2`가 이제 reliable transient-local
> `/planning/trajectory_guard_recovery_active`를 직접 발행하고 Adaptive C++
> filter만 구독한다. guard recovery 종료 후 2.5초 hold하며, 매 guard true-edge의
> 다음 cloud 한 프레임은 5 Hz cap과 6,000-point far-field limit를 모두 한 번
> 우회한다. 이후 open frame은 다시 6,000점 상한이다. true-edge가 아니라 open
> transition에 refresh를 묶었던 중간 구현은 37 guard events를 refresh 2회로
> 합쳐 seed6을 2/5에서 정지시켰으므로 폐기했다. 5 Hz cap 전체 해제도 kept
> 63.75->80.53%, FSM CPU 57.07->61.58%로 악화돼 폐기했다.
>
> 최종 edge-refresh는 seed6/7 Adaptive 각 n=5에서 **10/10·contact 0**, 별도
> Adaptive seed1-10 n=1에서 **10/10·contact 0**이다. 최종 n=1 비교는
> Full/Adaptive **10/10·contact 0**, Sector **10/10이지만 seed9/10 contact**다.
> Full 대비 Adaptive weighted reduction은 points/update 23.39%, map
> total/update 23.17%, map update 16.29%, FSM CPU 25.10%이고 mean mission은
> 71.75->80.92초(+12.78%)다. 늦은 seed의 direct-guard open duty가 83-97%라
> 다음 과제는 **hold를 맹목적으로 줄이지 않고** duty/time을 낮추는 것이다.
>
> 이 결과는 population 100%나 flight-ready 보장이 아니고 최종 3-arm n=1은
> 진단 때문에 split follow-up으로 완성했으므로 McNemar 미검정이다. raw-cloud
> CIRI는 계속 default false/non-authoritative다. 상세는 viability §8.24와
> `results/*20260824.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 endpoint hard guard + Adaptive commit-refresh 후속 — 바로 아래
> §8.22 배너의 “다음 구현”을 완료했다.** Full trajectory commit은 실제 current
> odometry pose, 첫 검사 pose, terminal pose에 대해 raw OCCUPIED voxel과
> `robot_r` body clearance를 hard invariant로 검사한다. 이 검사는 initial
> clearance escape 밖에 있어 short tail이 접촉 pose에서 stationary hold가 되는
> 경로를 닫는다. Adaptive는 ROG-Map의 `/rog_map/commit_version` ACK가 0.12초
> 이상 늦을 때 0.10초 최소 간격으로 sector-only latest refresh를 허용하고,
> full-open의 sector/near-field 밖 far-field를 프레임당 6,000점으로 제한한다.
>
> v=7, `loop24.txt`, static PCD, seed1-10 x n=1 x 3 modes에서 Full은
> **10/10**, Sector **9/10**, Adaptive **10/10** 완주했고 30/30 contact 0이다.
> 최악 static body clearance는 +0.252/+0.108/+0.174 m다. seed10 Sector만
> 4/5 waypoint에서 240.01초 timeout했고 Full/Adaptive는 85.39/118.91초로
> 완주했다. Adaptive는 실제 full-open/close 289/289회, commit refresh 309회,
> ACK 2,889회(3.364 Hz)를 기록했다.
>
> Full 대비 Adaptive는 points/update 36.30%, throughput 62.13%,
> mapping/update 47.66%, mapping work/mission 63.24%, combined CPU-work 15.08%
> 감소했고 mean mission은 18.16% 길다. 이전 n=5보다 Adaptive map commit은
> 2.944 -> 3.336 Hz, `MAP_STALE`은 70.86 -> 61.30/run, brakes는 45.84 ->
> 38.80/run으로 개선됐다. 다만 seed9/10은 topology arm/search가 계속 많아
> 늦은 시드의 시간 문제를 완전히 해소하지 못했다.
>
> 이 n=1에서 새 endpoint `OCCUPIED` reject 자체는 발생하지 않았다. 따라서
> identified code hole의 수정과 무회귀 증거이지 희귀 분기의 execution proof나
> population 100% 보장이 아니다. 모든 row retry/OOM/FSM swap 0, peak FSM RSS
> 3476.25 MiB였다. raw-cloud CIRI는 default false다. 상세는 viability §8.23,
> `docs/endpoint_guard_commit_refresh_3mode_v7_n1_20260823.md`,
> `results/endpoint_commitrefresh_3mode_strict_v7_n1_*_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 order-crossed 3-mode n=5 후속 — 아래 bounded-memory n=1
> 배너의 “broad clean campaign pending” 상태를 대체한다.** v=7,
> `loop24.txt`, static PCD, seed1-10 x n=5에서 Full/Sector/Adaptive를 한
> 캠페인 안에서 순서 교차해 150회를 실행했다. Full은 direct
> `/cloud_registered`, Sector/Adaptive는 C++ strict-burst를 거친
> `/cloud_sector`를 사용했고 150행 모두 valid/1 attempt/raw complete였다.
>
> static-safe는 **49/50, 48/50, 50/50**, live-only threshold까지 포함한
> all-detector-safe는 **49/50, 47/50, 50/50**이다. contact runs/events는
> Full 1/2, Sector 3/6, Adaptive 0/0이다. Adaptive는 관측 표본에서 Sector
> 접촉을 모두 제거했지만 Full 목표인 100%/접촉 0은 달성하지 못했다.
>
> Full 유일 접촉은 seed7 run1의 시작 배치 문제가 아니다. generation-7
> short tail이 `[11.950,12.850,1.050]`에서 끝났고 guard는 짧은 remainder와
> 두 `no_backup` tail을 `SAFE`로 commit했지만, 같은 시각 CIRI는 obstacle
> distance 0.0179 m로 corridor infeasible을 경고했다. trajectory가 그
> endpoint에서 끝난 뒤 static/live가 모두 접촉을 확인했다. 다음 코어 수정은
> topology 재시도나 필터 튜닝이 아니라 **현재 pose와 terminal stop pose의 hard
> clearance를 short-tail/stationary-hold 인증 전제조건으로 넣고, body envelope
> 진입 전에 stop하게 하는 것**이다.
>
> Adaptive 실제 출력 상태는 full-open **1518회**, close **1512회**, time-weighted
> open duty 22.43%다. Full 대비 map commit/points-update/throughput/
> mapping-update/mapping-work/combined CPU-work 감소는 각각 46.15/32.61/
> 63.71/44.23/63.25/16.13%다. mean mission time은 22.35% 길다. exact paired
> McNemar는 Full-Sector p=0.625, Sector-Adaptive p=0.250,
> Full-Adaptive p=1.000으로 유의하지 않다. Adaptive 50/50의 exact two-sided
> 95% population lower bound는 92.89%이므로 population 100% 주장은 금지한다.
>
> 전체 150회는 FSM swap/retry/OOM/PSI가 모두 0이고 peak FSM RSS 3474.36
> MiB였다. runner는 direct/filtered split config를 topic까지 검증하며, seed
> 경계에서도 순서 회전을 이어가고 sequence/order position을 CSV에 남긴다.
> raw-cloud CIRI는 계속 default false다. 상세는 viability §8.22,
> `docs/order_crossed_3mode_strict_v7_n5_20260823.md`,
> `results/order_crossed_3mode_strict_v7_n5_*_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 bounded-memory + 유효한 3-mode 후속 — 바로 아래 §8.20 배너의
> memory/swap 미해결 상태를 대체하되, n=50 liveness 결과 자체는 대체하지 않는다.**
> Full 후반 오염의 직접 원인은 (1) 모든 재계획 로그가 SFC 전체 cloud를 종료
> 때까지 보관하던 무제한 누적과 (2) `raycasting_en=false`에서도 491 x 491 x 981
> 전체 맵 크기로 잡던 두 `uint16_t` counter 배열 약 0.88 GiB였다. 일반 캠페인은
> detailed cloud를 끄고 scalar/trajectory 로그만 최근 64개로 제한했으며, no-raycast
> counter는 스캔에서 실제 건드린 voxel만 저장하는 sparse batch cache로 바꿨다.
>
> runner는 이제 attempt별 memory trace, FSM RSS/PSS/swap, host/cgroup memory/swap,
> PSI, retry reason, OOM delta를 보존한다. 동시에 이번 세션 초기 Sector/Adaptive가
> direct-Full YAML을 받아 실제로는 `/cloud_registered`를 읽은 유효성 오류를 찾았다.
> 그 행은 비교에서 전부 제외했다. 이제 Sector/Adaptive override가
> `/cloud_sector`가 아니면 실행 전에 실패하고, direct Full은 불필요한 filter를
> 띄우지 않는다.
>
> 올바른 입력으로 v=7, `loop24.txt`, static PCD, seed1-10 x n=1을 다시 실행한
> 결과 raw 완주는 Full/Sector/Adaptive 모두 **10/10**, static-safe 완주는
> **10/10, 9/10, 10/10**이다. direct/filtered 양쪽 모두 detailed SFC cloud를
> 끄고 같은 64-record bound를 사용했다. Sector seed7만 2 contact events/1 static
> episode, body clearance -0.007 m였고 Full/Adaptive는 contact 0이다. Adaptive
> 실제 출력 상태는 full-open **321회**, close **320회** 전환했고 time-weighted
> open duty는 23.38%였다. seed5가 open 상태로 종료되어 close가 하나 적다.
>
> Adaptive는 Full 대비 points/update 28.33%, throughput 57.09%, mapping/update
> 43.55%, mapping work/mission 58.64%를 줄였다. 관측 combined CPU-work도 9.74%
> 낮았지만 순차 n=1이라 broad end-to-end CPU 결론은 아니다. 최종 30회는 FSM
> swap 0, retry 0, OOM delta 0이며 peak FSM RSS는 3455.69 MiB였다. Sector seed1에서
> host-wide memory PSI 0.18이 잠깐 관측됐지만 나머지는 0이고 FSM swap/OOM은 없었다.
> 최종 최고속도는 Full/Sector/Adaptive 7.004/7.014/7.006 m/s다. 이 n=1은
> unpaired smoke이고 McNemar 미검정, population/flight-ready 보장이 아니다.
> raw-cloud CIRI는 계속 default false다.
>
> 상세는 viability §8.21,
> `docs/memory_bounded_3mode_v7_20260823.md`,
> `results/final_postopt_3mode_n1_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 stopped A* timeout 후속 — 바로 아래 native n=1 배너의 “n=5
> pending” 상태를 대체한다.** 같은 세션의 패치 전 seed1-10 x n=5에서 Full은
> 49/50, native C++ Adaptive는 48/50이었고, 세 실패 모두 seed9의 정지 상태
> `PlanFromRest -> A* TIME_OUT` 반복이었다. 기존 topology recovery가 `NO_PATH`만
> 인정하고 `PlanFromRest()` 결과는 Adaptive filter의 `/planning/replan_status`로
> 발행하지 않아 동일 topology와 sensing state를 반복했다.
>
> `fsm.cpp`는 이제 `PlanFromRest()` 성공 여부도 replan status로 발행한다.
> `super_planner.cpp`는 topology guard가 켜지고 `planning_from_rest=true`일 때만
> `TIME_OUT`을 기존 `NO_PATH`와 같은 bounded recovery evidence로 인정한다.
> 이동 중 timeout은 제외했고 clearance, 충돌 판정, sector 형상, raw-CIRI 권한은
> 바꾸지 않았다.
>
> 패치 후 seed9 targeted는 Full/Adaptive 각각 5/5, 전체 seed1-10 x n=1도 각각
> 10/10이었다. 최종 독립 n=5에서 Full과 native Adaptive가 모두 raw/static-safe
> **50/50**, live/static 접촉 **0/50**을 관측했다. 최악 static body clearance는
> Full +0.155 m, Adaptive +0.139 m이고 seed9/10도 양쪽 모두 각 5/5다. Adaptive
> 최종 로그에서는 실제 `reason=astar_timeout` recovery가 5회 실행됐고 관련 run은
> 모두 완주했다.
>
> Adaptive는 최종 Full 대비 processed points/update 25.58%, throughput 32.53%,
> mapping/update 29.62%, mapping work/mission 48.39%를 줄였다. 다만 Full arm 도중
> infrastructure retry 1회와 심한 memory/swap pressure가 관측돼 이 n=50 쌍의
> end-to-end CPU 비교는 오염됐다. 깨끗한 patched n=1에서는 Adaptive combined
> CPU-work가 15.62% 낮았지만, n=50 CPU 결론은 clean host/order-crossed 재측정 전까지
> 보류한다. 코호트는 unpaired라 McNemar를 하지 않았고 50/50은 population 보장이
> 아니다. raw-cloud CIRI는 계속 default false다.
>
> 상세는 viability §8.20,
> `docs/native_cpp_timeout_recovery_v7_20260823.md`,
> `results/full_adaptive_timeoutfix_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 native C++ Adaptive 후속 — Python CPU 병목은 n=1-per-seed
> smoke에서 해소됐다.** strict Adaptive 정책은 바꾸지 않고 별도 ROS2 C++ node
> `native_sector_cpp`로 옮겼다. 캠페인은 `--filter-backend cpp`로 선택하며 기본은
> 계속 Python이다. seed12-15 trap-event 계측은 아직 C++ 미지원이라 runner가 해당
> 조합을 명시적으로 거절한다.
>
> 첫 실제-cloud pilot은 MARSIM raw point stride 32 bytes를 그대로 복사해 Python
> `create_cloud()`의 packed 20-byte 출력과 달랐다. seed4에서 `fsm_node`가 약
> 9.1 GiB RSS 후 OOM-kill됐다. 선언된 field만 20 bytes로 재포장한 뒤 seed4 smoke와
> seed1-10 n=1 두 cohort에서 OOM은 재현되지 않았다. 합성 Python/C++ 출력 점·dense
> flag·통계도 일치했다. 러너는 이제 임무 중 FSM/filter 종료를 infrastructure
> retry하며 C++ CPU는 wrapper가 아닌 실제 argv0 PID를 잰다.
>
> 두 C++ cohort 모두 raw/static-safe **10/10**이었다. 첫 기능 cohort는 live/static
> 접촉 0이었다. 정확한 CPU cohort는 static 접촉 0이지만 seed10 이륙 초기에
> live-only 0.1995 m threshold event 1회가 있었고, 같은 run의 static PCD는 centre
> 0.321 m/body +0.121 m/contact 0이었다. 따라서 모든 detector 0이라고 합치지 말 것.
>
> 정확한 CPU cohort의 C++ filter는 2.522 CPU-s/mission, FSM+filter는
> 54.559 CPU-s/mission이었다. 이전 Python Adaptive n=50 대비 filter/전체 work는
> 76.17%/14.88% 감소했고, Full direct n=50보다 전체가 2.44% 낮게 관측됐다.
> mapping points/throughput/time/work도 Full 대비 26.44%/25.92%/28.67%/44.21%
> 감소했다. 그러나 C++은 seed당 1회이고 비교 cohort는 서로 unpaired다. §8.18의
> n=50 결과를 대체하거나 population/end-to-end CPU 확정으로 쓰지 말고 native n=5
> gate를 다음 단계로 수행할 것. raw-cloud CIRI는 계속 default false다.
>
> 상세는 `docs/adaptive_cpp_v7_n1_20260823.md`, viability §8.19,
> `results/adaptive_cpp_strict_v7_n1_cpu_raw_20260823.csv`,
> `results/adaptive_cpp_strict_v7_n1_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-22 Adaptive liveness 후속 — 바로 아래 strict v7 배너의 Adaptive
> 49/50을 대체한다.** Full/Sector 코드는 바꾸지 않고 Adaptive filter의 replan
> recovery를 bounded one-shot으로 만들었다. 0.25 s burst/1.75 s cooldown broad
> 결과는 seed9 run5가 waypoint 3/5에서 240 s timeout되어 49/50이었으므로
> 불채택했다. 정지점 `(18.633, -24.281, 1.332)`은 static body clearance
> +0.091 m로 접촉은 아니었지만 CIRI 시작점이 infeasible해져 같은 fallback을
> 반복 거절한 liveness 실패였다.
>
> 최종 Adaptive는 replan failure 3연속마다 **0.6 s full-cloud one-shot,
> 1.4 s cooldown**을 사용하고 filtered cloud publication만 최대 5 Hz로 제한한다.
> input callback과 recovery 상태 갱신은 생략하지 않는다. 실제 관측값은 input
> 6.509 Hz, publish 4.188 Hz, map commit 3.132 Hz다. v=7, `loop24.txt`, timeout
> 240 s, static PCD, seed1-10 각 n=5의 별도 후속 cohort에서 Adaptive는 raw/safe
> **50/50**, live/static 접촉 **0/50**, 최악 body clearance **+0.100 m**를
> 관측했다. seed9은 targeted 5/5와 broad 5/5에서 각각 통과했다.
>
> 8.17의 변경 없는 Full 기준 대비 Adaptive 처리점/update **29.22% 감소**,
> 처리량 **25.55% 감소**, mapping/update **32.40% 감소**, 임무당 mapping work
> **46.29% 감소**다. 단 Python filter까지 합친 FSM+filter CPU-work는 Full보다
> **14.61% 높다**. 따라서 mapping-work 감소만 주장할 수 있고 end-to-end CPU
> 감소는 아직 아니다. Full/Sector와 새 Adaptive는 서로 다른 캠페인이어서 paired
> McNemar 대상도 아니다. 관측 50/50은 population/flight-ready 보장이 아니며
> raw-cloud CIRI는 계속 shadow-only/default false다.
>
> 상세/원시는 `docs/strict_v7_3mode_n5_20260822.md` 후속 절, viability 문서
> §8.18, `results/adaptive_replan060_cap5_strict_v7_n5_raw_20260822.csv`,
> `results/strict_v7_adaptive_recovery_n5_summary_20260822.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-22 strict v7 결과 — 아래 2026-08-21 배너의 설정과 결론을
> 대체한다.** 이전 sector/adaptive는 wall-time의 약 91% 동안 full-open이라 입력점을
> 약 3%밖에 줄이지 못해 사용자가 의도한 ablation이 아니었다. 새 `strict-burst`는
> fixed Sector를 계속 닫아 두고 Adaptive에만 0.6 s full-cloud burst/1.4 s cooldown과
> 속도 의존 near-field halo를 준다. Full은 필터를 거치지 않는 direct
> `/cloud_registered`와 전용 tight-v7 설정을 사용했다.
>
> v=7, `loop24.txt`, timeout 240 s, seed1-10 각 n=5의 유효 150회 결과는 raw
> 완주 Full **50/50**, Sector **50/50**, Adaptive **49/50**이다. static-PCD 접촉까지
> 0이어야 하는 안전 완주는 **50/50, 46/50, 49/50**이다. Full live/static 접촉은
> 모두 0이었다. Sector는 seed7 run2/run4, seed8 run3, seed10 run5에서 live와
> static 양쪽이 확인한 실제 접촉 4 run/6 live episode/4 static episode가 있었고,
> 최악 body clearance는 -0.184 m였다. Adaptive는 접촉 0, 최악 clearance
> +0.103 m였지만 seed9 run1이 waypoint 4/5에서 timeout됐다.
>
> Full 대비 Sector의 처리점/update와 mapping/update는 **52.40%/57.04% 감소**,
> Adaptive는 **40.54%/47.19% 감소**했다. Sector/Adaptive 입력점 감소는
> 46.09%/30.30%, Adaptive full-open frame duty는 15.28%다. 설정 주파수는 모두
> LiDAR 10 Hz, replan 15 Hz, FSM/command 100 Hz로 같지만 관측 map commit은
> 2.977/3.216/2.816 Hz였다. filtered cloud callback은 Sector/Adaptive
> 4.070/3.982 Hz이며 Full direct callback은 계측하지 않았다.
>
> 따라서 이 표본은 **Full 100%/충돌 0, fixed Sector의 정보 절단에 따른 안전 저하,
> Adaptive의 안전 회복과 Full 대비 연산량 절감**이라는 연구 방향을 기술적으로
> 지지한다. 다만 Adaptive raw liveness는 Sector보다 좋아지지 않았고, paired exact
> McNemar도 safe completion `p=0.375`, static contact `p=0.125`로 유의하지 않다.
> population 보장이나 flight-ready로 쓰면 안 된다. 새 saturation vertical recovery는
> marker 0회라 이 결과의 원인으로 주장할 수 없다. raw-cloud CIRI는 계속
> shadow-only/default false다.
>
> 상세/원시는 `docs/strict_v7_3mode_n5_20260822.md`,
> `results/strict_v7_full_n5_raw_20260822.csv`,
> `results/strict_v7_sector_adaptive_n5_raw_20260822.csv`,
> `results/strict_v7_3mode_n5_summary_20260822.csv` 및 viability 문서 §8.17을 볼 것.

> [!IMPORTANT]
> **2026-08-21 동일 코드 full/sector/adaptive seed1-10 각 n=5 결과 — 아래
> 2026-08-20 seed9/10 local 10/10 배너의 완주 결론을 대체한다.** 총 150회는
> 모두 valid였고 static PCD가 실제 로드됐다. 완주는 full **46/50 (92%)**,
> sector **49/50 (98%)**, adaptive **50/50 (100%)**였다. exact paired
> McNemar는 full/sector `p=0.375`, full/adaptive `p=0.125`,
> sector/adaptive `p=1.0`으로 현재 표본에서 유의한 차이는 아니다.
>
> 모든 모드의 설정 주파수는 LiDAR 10 Hz, replan 15 Hz, main FSM 100 Hz,
> command 100 Hz로 동일했다. 실제 cloud callback은 6.51/6.82/6.63 Hz,
> map commit은 3.94/4.13/4.04 Hz였다. sector/adaptive는 약 91% wall-time
> full-open이라 점을 2.97%/3.01%만 줄였지만 mapping/update는
> 131.65 ms에서 124.97/125.29 ms로 약 5% 감소했다. 전체-run 평균 시간의
> 6-7% 개선은 full의 timeout 4건 영향이 크며 성공-run끼리는 1.93%/0.94%
> 차이뿐이다.
>
> static-PCD contact는 **0/150**, 최악 body clearance는
> full/sector/adaptive **0.129/0.109/0.079 m**였다. seed5 run2 sector의
> live-cloud marker 1회는 static PCD상 centre 0.309 m, body +0.109 m,
> contact 0인 live-only marker다. adaptive 50/50을 안전 여유까지 가장 좋거나
> population 100%라는 뜻으로 쓰면 안 된다.
>
> 실패는 full seed3/6/7/9 각 1건과 sector seed9 1건이다. 세 full 실패는
> 수천 회 MINCO/EXP 반복, seed7은 수천 회 polytope 생성 실패, sector seed9는
> 38회 reroute arm/27회 `NO_PATH`/9회 epoch reset의 topology churn이었다.
> 150회 전체에서 direct-goal fallback commit/reject marker는 모두 0이라 §8.15
> branch가 이 실패들을 커버했다고 볼 수 없다. 상세 표와 원시는
> `docs/guarded_v7_3mode_recovery_n5_20260821.md`,
> `results/guarded_v7_3mode_recovery_n5_raw_20260821.csv`,
> `results/guarded_v7_3mode_recovery_n5_summary_20260821.csv` 및 §8.16을 볼 것.
> raw-cloud CIRI는 계속 shadow-only/default false다.

> [!IMPORTANT]
> **2026-08-20 seed9/10 복구 완료 — 이 배너가 아래의 “미해결” 배너들을
> 대체한다.** §8.14의 stale command 진단은 맞았지만 “실제 odom speed를 쓰면
> 된다”는 설명은 틀렸다. ROS2 ROG odom callback은 `RobotState.v/a/j`를 채운 적이
> 없었고 해당 필드는 초기화조차 안 돼 있었다. simulator twist를 전역 전달한
> 실험은 seed10 실제 접촉을 냈고 전량 되돌렸다. 최종 코드는 legacy state를 0으로
> 명시 초기화하고, brake 선택 안에서만 연속 fresh odom 위치로 motion을 추정한다.
>
> retained fix는 (1) cached command 0.10 s timestamp+position/velocity consistency
> gate, (2) brake selection 직렬화와 fresh position-motion/trajectory fallback,
> (3) 방향별 topology blocker chain + 3회 `NO_PATH` epoch reset, (4) backup/stitch
> reject를 EXP blocker로 오염시키지 않는 guarded EXP-only fallback, (5) stale
> `PlanFromRest`를 막는 map-readiness gate, (6) 센서 해상도/FoV/128-ring을 유지한
> GENERAL_360 렌더 중복계산 제거다. 마지막 waypoint 근처의 반복 MINCO 실패에는
> certified stop+3 m 이내에서만 만들고 기존 geometric guard와 sampled
> stop-viability를 전부 통과해야 하는 direct-goal fallback도 추가했다. fallback의
> local start는 mutex로 복사한 odometry에서 0.15 m 이내여야 한다. 이 branch는 최종
> 무작위 gate에서 발동하지 않았으므로 별도 실증 완료로 주장하지 말 것.
>
> 최종 동일 코드/설정(`v=7`, full, filtered tight-v7, `loop24.txt`, timeout 140 s,
> static PCD 1,042,220점)은 seed9 **5/5**, seed10 **5/5**, 총 **50/50 waypoint**,
> static/live contact **0/10**이었다. 평균 시간은 93.95/99.09 s, 최악 body
> clearance는 0.220/0.132 m였다. 이는 local regression gate이며 population 100%
> 또는 flight-ready 근거가 아니다.
> 위 0.15 m 조건을 넣고 재빌드한 뒤 별도로 돌린 seed10 smoke도 83.92 s에 5/5,
> contact 0, static-PCD body clearance 0.262 m로 통과했다. 이 1회는 n=5 표에
> 합치지 않았다.
>
> 중요한 반증: freshness를 1.50/1.25 s로 늘린 첫 반복은 완주는 빨라졌지만
> static-PCD 접촉 2회(centre 0.142 m, body clearance -0.058 m)를 냈다. 따라서
> 최종 프로파일은 안전 기준 0.75/0.55 s를 그대로 유지한다. global twist 전달,
> KD-tree 렌더 culling, replan 10 Hz도 모두 되돌렸다. 상세와 행별 결과는
> `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.15 및
> `results/guarded_v7_full_seed9_seed10_recovery_n5_20260820.csv`를 볼 것.
> raw-cloud CIRI는 계속 shadow-only/default false다.

> [!IMPORTANT]
> **2026-08-20 seed9/10 full 실패 원인 정정:** 150회 캠페인의 full 실패
> 2건은 map freeze나 단순 timeout이 아니라 certified recovery에 들어가지 못한
> 교착이다. seed9 run4는 gen177을 314회/30.614초, seed10 run2는 gen71을
> 314회/98.871초 거절했다. 둘 다 EXP `CLEARANCE_MARGIN`; 같은 구간에서 brake도
> 314회 전부 거절되어 accepted brake, recovered hold, topology arm/search가 모두
> 0이었다. 지도는 각각 317->401, 44->465로 계속 갱신됐다.
>
> 직접 원인은 `fsm_ros2.hpp`의 `last_published_cmd_`가 timestamp 없이 boolean
> valid로 영구 캐시되는 구조다. guard가 정상 command publication을 막은 뒤에도
> `activateEmergencyBrake()`가 이 stale command를 계속 우선 사용했다. 실제로
> final loop 314회 내내 brake initial speed가 seed9 2.813 m/s, seed10 0.741
> m/s로 고정됐다. brake가 인증되지 않으니 certified-stop flag가 생기지 않고,
> odom speed <=0.2 또는 certified stop을 요구하는 reroute gate도 한 번도 열리지
> 않았다. 성공한 동일 seed 런은 topology arm/search가 정상적으로 발생했다.
> seed10의 460회 replan overtime과 14회 FIRI NaN/Inf는 악화 요인이지만 seed9에
> 없이도 교착이 재현되므로 1차 원인이 아니다.
>
> 다음 수정 우선순위는 cached command timestamp/odom consistency 검사 -> fresh
> actual recovery state로 brake 구성 -> 반복 reject의 bounded fail-closed state다.
> moving brake collision로 blocker를 놓는 과거 실패안은 되살리지 말 것. 상세는
> `docs/guarded_v7_full_seed9_seed10_failure_analysis_20260820.md`와 §8.14.
> static-PCD runner는 옵션 순서와 active-index validity 검사를 고쳤고 seed1 smoke로
> 실제 로드를 확인했지만, 기존 150회의 미계측값은 여전히 무효다.

> [!IMPORTANT]
> **2026-08-20 guarded v7 full/sector/adaptive n=5 최신 결과:** seed1-10의
> 세 모드를 각 5회, 총 150회 실행했다. 완주는 full **48/50 (96%)**,
> sector **46/50 (92%)**, adaptive **47/50 (94%)**였고 exact paired
> McNemar는 각각 `p=0.6875`, `p=1.0`이라 완주율 차이를 통계적으로
> 확정할 수 없다. weighted point 감소도 sector **2.72%**, adaptive
> **2.54%**뿐이었다. replan-failure safety valve가 두 모드를 평균
> **91.5% full-open**으로 만들었기 때문이다. mapping total time은 약
> 6.4% 줄었지만 평균 mission time은 약 4.1% 늘었다. seed9는
> full/sector/adaptive가 4/5, 3/5, 2/5였고 seed10은 4/5, 4/5, 5/5였다.
> 따라서 아래 §8.12의 seed10 full 5/5는 specific deadlock 제거의 local
> gate이지 결정적 안정성 보장이 아니다.
>
> **안전 계측 정정:** 이 150회 명령의 `--static-pcd`가 argparse의 `--`
> 뒤에 놓여 monitor에서 무시됐다. raw CSV의 모든 `static_pcd_*` 0/null은
> 미계측값이며 기존 0/170에 합치거나 “접촉 0”으로 인용하면 안 된다.
> mode-dependent live cloud는 seed9 sector/adaptive에서 각각 marker 1회를
> 냈다. 실행기는 옵션 순서를 고쳤고, 앞으로
> `static_pcd_enabled=true`와 양수 point count가 아니면 run을 invalid/retry
> 처리한다. 상세 표와 원시는
> `docs/guarded_v7_full_sector_adaptive_n5_20260820.md`,
> `results/guarded_v7_full_sector_adaptive_seed1_10_n5_20260820.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-20 최신 결과 (이 배너를 가장 먼저 확인할 것):** §8.11의 유일한
> seed10 실패(2/5)는 CIRI shadow overhead가 아니라 한
> `PlanFromRest/with_backup` generation이 같은 충돌점에서 **110회/75.404초**
> 반복 거부된 same-topology deadlock이었다. 기존 회피 구는 정지점에서 약
> 6.2cm밖에 떨어지지 않았고, A*의 3-D 구와 CIRI의 희소 ring+pole 표본도 서로
> 달라 고도만 바꾸거나 표본 사이로 같은 XY 통로를 재사용할 수 있었다.
>
> 이를 **certified stop-and-reroute**로 교체했다. 기존 emergency brake가 끝나고
> fresh map/current odom/0.25초 stable hold가 확인된 뒤에만 FSM이 planner에 정지
> certificate를 전달한다. 새 generation의 첫 reject와 동일 XY collision
> cluster의 매 3번째 reject에서 정지점 앞쪽에 최대 6개의 blocker를 1m 간격으로
> 놓으며, A*는 이를 수직 XY cylinder로 검사하고 CIRI는 같은 경계를 비행 높이
> 전체의 ring들로 인코딩한다. CIRI에는 0.25m
> 이하 높이 간격의 jittered ring을 넣어 optimizer가 blocker 사이/위/아래로 새지
> 않게 했다. 같은 후보를 재수락하거나 guard 기준을 완화한 것이 아니라, 인증된
> 정지 상태에서 guide-path topology 자체를 바꾸는 복구다.
>
> 결과: seed10 연속 n=5는 **5/5 완주, 25/25 waypoint, 접촉 0/5**(평균
> 90.17초), 기존 75.404초 정체는 최장 1.755초로 줄었다. 같은 CIRI-shadow
> test profile의 seed1-10 x n=2는 **20/20 완주, 100/100 waypoint, 접촉
> 0/20**, 평균 74.35초, 최장 same-generation reject span 1.467초였다. 파라미터
> no-op을 피하려고 generic `growth_m/max_radius_m`도 실제 escalation 반경에
> 연결했고, 검증된 tight-v7은 고정 0.8m chain(`growth_m: 0`)을 명시한다.
> 상세는 `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.12와
> `results/topology_cylinder_reroute_cirishadow_n2_20260820.csv`를 볼 것.
> n=2를 100% population 성공률이나 flight-ready 근거로 확대해석하지 말 것.
> raw-cloud CIRI 결과는 여전히 shadow-only/default false이고 브레이크 판정에는
> 연결되지 않았다.

> [!IMPORTANT]
> **2026-08-19 최신 결과 (이 배너를 가장 먼저 확인할 것):** §8.10에서
> 미완이던 raw-scan 누적 CIRI shadow 계산의 **비동기 latest-only 워커 전환을
> 완료하고 검증했다.** `activateEmergencyBrake()`는 대표 후보 하나를
> overwrite 가능한 단일 슬롯에 넣고 최신 완료 결과만 읽으며, 누적 scan
> snapshot/PCL 변환/voxel downsample/CIRI decomposition/containment는 전용
> worker가 수행한다. 판정은 여전히 실제 브레이크 수락/거부에 전혀 관여하지
> 않는다. 첫 async 구현만으로는 seed5가 2/5에 머물렀고, shadow-only인데도
> 별도 `/cloud_registered` DDS 구독이 매 scan PCL 변환과 불필요한 KD-tree
> 생성까지 하던 추가 병목을 발견했다. 최종 구조는 ROG-Map이 이미 수락한
> message를 in-process observer로 넘겨 중복 delivery를 없앴다. 최종
> seed1-10 x n=2, 120초 검증은 **완주 19/20, waypoint 97/100, 접촉 0/20**;
> worker 812건의 총 계산시간은 평균 5.138ms, p95 13.628ms, 최대 22.706ms였지만
> main FSM은 이를 기다리지 않았다. 이는 기존 shadow-off 분포 수준으로의
> 회복이지 95%를 새 population 성공률로 주장할 근거는 아니다. 코드/실험
> 상세는 `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.11과
> `results/ciri_shadow_async_n2_20260819.csv`를 볼 것.
> `trajectory_guard_raw_cloud_ciri_shadow_en`은 기본값 `false`이고
> 실사용 프로파일(`static_seedmaps_guard_viability_tight_v7.yaml`)엔 안
> 켜져 있어서 현재 baseline엔 영향 없음 — 켜져 있는 건 전용 테스트
> 프로파일(`_cirishadow.yaml`)뿐.

> [!IMPORTANT]
> **2026-08-17/18 최신 결과 (가장 먼저 확인할 것):** 이 문서와 아래 배너들이
> 다루는 seed6 gate 미통과 문제의 실제 지배적 원인은 executor 스레딩 버그
> (`perfect_drone_sim`이 단일 스레드로 돌아서 렌더 콜백이 굶주림)와, 더
> 결정적으로 `Fsm::callMainFsmOnce()`의 `EMER_STOP` 케이스가 살아있는 목표를
> 버리고 무조건 `WAIT_GOAL`로 떨어져 `mission_planner`의 1 Hz 재전송 타이머를
> 기다리던 버그였다 — seed9 한 런에서 미션 시간의 60%가 그냥 대기 상태였다.
> 두 버그 모두 수정 후 seed1-10 스윕(n=1)에서 48/50 완주, 접촉 0/10 (10개 중
> 9개 시드가 5/5). 아직 공식 5-run gate는 미통과. 전체 경위와 실패한 시도들
> (CIRI corridor 3회 시도, topology zone 확장 2회, raw-cloud 누적)은
> `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8을 볼 것 — 아래의
> "occlusion" 계열 설명이나 콜백 그룹 경합 이론은 전부 낡은 것이다.

> [!IMPORTANT]
> **2026-08-14 v7 topology / certified-stop 후속 결과:** 임시 avoidance
> sphere를 A*에 주입하는 topology reroute와 선제 stop 인증을 구현했지만, seed6
> gate는 통과하지 못했다. `0.55 s` 선제 stop n=5는 완주 1/5, 접촉 run
> 1/5였고, fresh raw cloud hazard는 검출됐어도 v=7 현재 상태에서 인증 가능한
> brake 집합이 비는 사례가 확인됐다. 기본 `full_guard_v7`과 새
> `full_guard_reroute_v7`을 flight-ready로 기술하지 말 것. 상세 구현과 steps
> 26–34 원시 결과는 `docs/v7_topology_certified_stop_reroute_2026-08-14.md`를
> 최우선으로 확인할 것.

> [!IMPORTANT]
> **2026-08-14 steps 6–22 continuation:** immutable snapshot and adaptive
> recovery were implemented, but the required gate still failed. The seed6
> five-run smoke completed 2/5 and had contact in 1/5. The 1.25 s freshness
> setting caused a measured late-braking contact and was restored to 0.75 s.
> Read `docs/loop_guard_snapshot_recovery_steps_6_to_22_2026-08-14.md` before
> using any conclusion or configuration in this document.

> [!IMPORTANT]
> **2026-08-14 단계 1–5 후속 결과:** enforcement는 보고된 seed6 시도에서 접촉 0회를
> 유지했지만 5/5 완주 smoke gate를 통과하지 못했다. 따라서 5회 smoke와 50-run은
> 실행하지 않았다. `docs/loop_guard_steps_1_to_5_2026-08-14.md`를 함께 확인하고,
> guard를 flight-ready 또는 escape를 실증 완료로 기술하지 말 것.

> [!CAUTION]
> **2026-08-13 독립 코드 감사 정정 — 아래 결론을 그대로 사용하지 말 것.**
> 이 문서 작성 뒤 소스와 원시 JSON을 다시 대조한 결과, 핵심 인과 해석을 무효화하거나 제한하는
> 다음 사항이 확인됐다.
>
> 1. `obs_skip_num`은 현재 소스에서 `box_search_skip_num_`에 저장되기만 하고 실제 점군 선택에
>    사용되지 않는다. 따라서 2→1은 no-op이며, 이를 "다운샘플링 제거" 또는 corridor 정확도
>    개선으로 해석할 수 없다. baseline 41/50 대 skip1 35/50의 짝비교 exact McNemar 검정은
>    `p=0.146`이었다.
> 2. skip1 35/50 대 clearance+skip1 37/50도 유의한 악화가 아니다. 같은 seed/run 번호의
>    discordant pair는 개선 4, 악화 6이고 exact McNemar `p=0.754`다.
> 3. 추가된 `distancePointToSegment()`는 point seed(`a == b`)에서 0으로 나누어 NaN을 만들 수
>    있다. 또한 preferred plane 생성 뒤 다른 장애물점을 제거하는 기준은 `local_margin`이 아니라
>    여전히 `robot_r_`이므로, 로그의 `local_margin=0.4`는 최종 polytope 전체의 0.4 m margin을
>    보장하지 않는다.
> 4. clearance penalty의 gradient 부호와 `smooth_eps` 공유 자체는 타당하지만, 장애물 유래 면뿐
>    아니라 bounding/ceiling/floor를 포함한 모든 SFC 면의 비용을 합산한다. 0.15 m erosion의
>    feasibility도 확인하지 않고 face 수에 따라 비용이 달라지므로 physical obstacle clearance
>    비용으로는 설계 결함이 있다.
> 5. clearance penalty는 `ExpTrajOpt`에만 적용되고 `BackupTrajOpt`에는 적용되지 않는다. 원시
>    이벤트에서 skip1 접촉 런 35개 중 18개, clearance+skip1 접촉 런 37개 중 25개에 backup
>    trajectory 접촉이 포함됐다.
> 6. monitor의 `DRONE_R=0.20 m`와 planner의 `robot_r=0.20 m`가 같아 계획 여유가 0이다.
>    `min_clearance_m`도 실제 signed body clearance가 아니라 UAV 중심--표면점 거리다.
>
> 따라서 아래 §0의 "두 근본 원인 확정", `obs_skip_num=1`의 개선 효과, preferred-margin 진단과
> 조합 실험의 상호작용 해석은 **가설/관측 기록으로만 보존**한다. 다음 단계는 원본 SUPER의 0%를
> 맞추는 튜닝이 아니라, 반복 방향 전환용 SUPER 기반 planner를 공통으로 보강하고 그 위에서
> full/sector/adaptive를 비교하는 것이다.
>
> **후속 결과:** map-version shadow 재검사와 0.2 m guard margin은 20/20 접촉을 사전
> 탐지했지만, shadow 후보 중 safe 비율이 46.0%뿐이었다. 네 가지 enforcement smoke는 모두
> 접촉 0건이면서도 0/5 waypoint에서 정지했다. 따라서 현재 결론은 `keep_shadow_only`이며,
> 상세 수치와 구조적 원인은 `docs/trajectory_guard_audit_2026-08-13.md`의 마지막 두 섹션을
> 우선 참조해야 한다. 50-run enforcement는 실행하지 않았다.

이 문서는 JKICS 논문용 `super-sector-filter` 프로젝트에서, SUPER의 원본(`full`) 모드가 논문
파라미터(v=10 m/s, max_acc=20, max_omg=2.5) 조건에서 왜 접촉률 0%를 달성하지 못하는지 파고든
조사 전체를 정리한 것입니다. Codex에게 이 파일을 먼저 읽게 하고, 아래 "Codex가 참고해야 할
파일 목록" 섹션에 나열된 코드/설정/데이터 파일을 순서대로 읽게 하면 전체 맥락을 파악할 수
있습니다.

## 0. 결론 요약 (TL;DR)

- **13가지 방법을 시도**했고, `full` 모드의 잔여 접촉률을 0%로 만드는 데는 **아무도 성공하지
  못했습니다.**
- 접촉률만 보면 **`obs_skip_num=1` 단독**(다운샘플링 없이 corridor 생성)이 가장 좋았습니다
  (82% → 70%, 부작용 없음).
- 완주율/안정성까지 고려하면 **`clearance penalty`(MINCO 비용함수에 새로 추가한 항) +
  `obs_skip_num=1` 조합**이 가장 균형 잡힌 결과였습니다(완주율 96%→98%, 접촉률 82%→74%,
  타임아웃 거의 없음).
- **근본 원인은 두 가지가 겹쳐 있는 것으로 결론지었습니다**:
  1. MINCO 궤적 최적화기의 비용함수에는 "corridor(SFC) 안에만 있으면 됨"이라는 단방향
     장벽(one-sided barrier)만 있고, "장애물에서 멀어질수록 좋다"는 항이 원래 없었습니다.
     → 최적화기가 좁은 corridor 벽에 딱 붙어도 비용이 0이라, 실제 여유 공간이 있어도 안 씀.
  2. corridor(SFC) 자체가 CIRI 알고리즘이 본 (다운샘플링된) 장애물 점군을 기준으로 만들어지기
     때문에, 실제 물리적 여유 공간(1~2m)이 있어도 corridor가 그 공간까지 뻗어있지 않으면
     최적화기는 애초에 그 공간에 접근할 방법이 없습니다.
- 두 원인 중 하나만 고쳐서는(아래 실험 8, 2번 참고) 부분 개선만 있었고, 둘을 다양한 방식으로
  조합해봐도(실험 9, 10, 12, 13) obs_skip_num=1 단독보다 확실히 나은 조합은 찾지 못했습니다.
- **아직 풀리지 않은 질문**: 왜 corridor를 정확하게(obs_skip_num=1) 만들고 최적화기에게
  clearance 인센티브까지 줘도(실험 13) 접촉률이 obs_skip_num=1 단독보다 오히려 근소하게
  나쁜가(70%→74%)? 이 부분이 Codex에게 특히 물어보고 싶은 지점입니다.

---

## 1. 문제 정의

- 저장소: `github.com/nawoo99/super-sector-filter` (이 문서가 있는 곳), SUPER 원본은
  `/root/super_ws/src/SUPER` (ROS2 워크스페이스, 별도 git 상태— super-sector-filter는 이
  워크스페이스에 대한 패치/실험 기록 저장소).
- SUPER 논문은 `full`(전체 장애물 점군을 그대로 사용) 모드에서 접촉률 0%를 주장하지만, 이
  프로젝트의 조사에서는 논문과 동일한 파라미터(v=10, max_acc=20, max_omg=2.5)로 재현했을 때
  `full` 모드조차 seed1-10 × 5회(n=50) 기준 접촉률 82%가 나왔습니다(`baseline`).
- 목표: sector/adaptive(제안 기법)와 공정하게 비교하려면 `full`이 0%에 최대한 가까워야
  하는데, 그게 안 되는 이유를 찾고 가능하면 고치는 것.
- 미션: `loop24.txt` (사각형 4개 꼭짓점 + 원점 복귀, 총 5 waypoint), `switch_dist=1.5`,
  `TIMEOUT=85.0s`.
- 평가지표: `success`(완주 여부), `contact`(collisions>0인 run의 비율), `mean_clr`(run별
  `min_clearance_m`의 평균), `timeout`(mission_time_s >= 84.9s인 run 수).

## 2. 이미 확립된 배경 (이 세션 이전에 규명, `paper_story.md` §3.6 / `연구일지.md` 참고)

- `robot_r=0.2`(드론 반지름), 장애물 간 최소 보장 간격(surface-to-surface) 1.0m, 실측
  중앙값 1.24~1.73m (seed별로 다름, seed9/10이 가장 좁음).
- 접촉 시점의 순간 곡률반경(curvature radius, `R=|v|³/|v×a|`) 분석: 중앙값 11.26m로,
  대부분의 접촉이 급회전 때문이 아님(하위 10~25%만 회전반경 문제로 설명 가능).
  → **접촉의 대다수는 회전 동역학 문제가 아니라 corridor가 장애물에 너무 가깝게 만들어지는
  것 자체가 원인**이라는 결론.
- CIRI(corridor 생성 알고리즘)는 corridor를 두 장애물 사이의 중앙에 정렬하는 로직이 원래
  없음 — A*가 찾은 guide_path를 얼마나 타이트하게 감싸는지가 전부.

## 3. 이번 세션에서 시도한 13가지 방법 (전부 v=10, `full` 모드, seed1-10 × 5회 = n=50)

기준선(baseline, `super_planner/robot_r: 0.2`만, `obs_skip_num: 2`):
**완주율 96% / 접촉률 82% / 평균 clearance 0.084m**

### 3.1 Guide-path 중앙 정렬 시도 (전부 실패, 이 세션 이전 파트에서 시도 — `paper_story.md`에
이미 기록됨, 여기서는 요약만)

| # | 방법 | 접촉 | 완주 | clearance | 비고 |
|---|---|---|---|---|---|
| 1 | guide_path 점별 독립 밀기 (0.3m) | 62% | 70% | 0.126m | 완주율 붕괴 |
| 2 | 같은 방식, 0.15m | 66% | 60% | 0.115m | 더 나쁨 (크기 문제 아님을 반증) |
| 3 | 0.15m + guide_stamp(시간) 보정 | 66% | 64% | 0.126m | seed9,10 세 버전 모두 0/5 완주 |
| 4 | v3를 v=4에서 재검증 | 60%(악화) | 78% | 0.157m | v=4 baseline(52%/98%/0.178m) 대비도 악화 → 회전반경 문제 아님 확정 |
| 5 | guide_path 이동평균 스무딩 + v3 | 66% | **40%(최악)** | 0.147m | 코드 리딩으로 원인 규명: guide_path/guide_stamp가 MINCO의 초기 제어점/구간시간으로 그대로 쓰이는데, 점별로 다른 방향으로 밀면 L-BFGS 웜스타트가 톱니모양이 되어 수렴이 나빠짐. 스무딩해도 실패 |

**결론**: guide_path(궤적 최적화의 warm-start)를 건드리는 접근은 전부 net-negative.
→ 이후 corridor 생성(CIRI) 레벨과 비용함수 레벨로 방향 전환.

### 3.2 CIRI corridor 생성 레벨 (이번 세션 본 파트)

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 6 | `obs_skip_num=1` (다운샘플링 제거) | **70%** | 96% | **0.141m** | 낮음 | **유일한 순수 개선** (부작용 없음) |
| 7 | CIRI per-point 선호마진 0.4m (robot_r=0.2는 hard 유지) | 78% | 78% | 0.106m | 11 | 한 corridor 안에서 벽마다 마진이 0.2~0.4m로 비대칭 혼재 → 완주율 붕괴 |
| 8 | CIRI per-corridor **균일** 선호마진 0.4m | 86% | 98% | 0.074m | 1 | 비대칭 문제는 해결(완주율 회복)했지만 **접촉률은 오히려 baseline보다 악화** |
| 9 | `obs_skip_num=1` + 균일마진 0.4m 조합 | 84% | 92% | 0.092m | 4 | 둘 다 corridor "생성" 메커니즘이라 서로 간섭, obs_skip=1 단독보다 전부 나쁨 |
| 10 | `corridor_bound_dis` 0.8→0.4 (corridor가 뻗을 수 있는 최대폭 축소) | 80% | **70%** | 0.069m | **15** | 너무 급격 — corridor 자체를 못 찾아 재계획 실패 폭증 |
| 11 | `corridor_bound_dis` 0.8→0.6 (완만) | 88% | 88% | 0.065m | 6 | 여전히 baseline보다 전부 나쁨. 폭을 줄이는 접근 자체가 안 맞음 |

**진단 실험 (실험 8 데이터 재분석)**: 접촉 위치와 CIRI 로그를 공간 매칭한 결과, 매칭된 접촉의
**67%가 "풀 마진(0.4m)" corridor 안에서** 발생했습니다 — "갑자기 좁아지는 지점에서 부딪힌다"는
가설은 기각. 대신 corridor가 계산에 쓰는 (다운샘플링된) 점군 자체가 실제 장애물 표면을
부정확하게 대표하고 있을 가능성이 높다고 결론.

### 3.3 근본 원인 규명 — 트래킹 오차 분석

`full` 모드 seed10 단독 실행에서 15개 접촉 이벤트 전수를 `position`(실제 위치)과
`position_command.position`(계획된/명령된 위치)으로 비교:
- **10/15(67%)**: 트래킹 오차 = 0.000m (컨트롤러가 계획을 정확히 따라감)
- **5/15(33%)**: 트래킹 오차 0.09~0.10m, 그러나 명령 위치 기준으로 역산해도 대부분 여전히
  위험하게 가까움(0.16~0.23m)
- **→ 15/15 전부, 계획된 궤적 자체가 이미 위험**했습니다. 실행/트래킹 문제가 아닙니다.

MINCO 비용함수(`exp_traj_optimizer_s4.cpp`의 `constraintsFunctional`)를 직접 읽어서 확인:
위치 비용은 `violaPos = outerNormal·pos + d`가 **양수(corridor 밖)일 때만** 페널티를 주는
순수 단방향 배리어. corridor 안에 있는 한, 벽에 딱 붙어도 비용 기여가 0.
**→ 옵티마이저 입장에서 corridor 중앙에 있을 이유가 전혀 없었습니다.**

### 3.4 비용함수 레벨 수정 — Clearance Penalty (새로 구현)

`ExpTrajOpt::constraintsFunctional`에 두 번째 소프트 페널티 항 추가:
`violaClr = violaPos + clearance_margin` — 위치 비용과 동일한 단방향 배리어 모양이지만
`clearance_margin`만큼 안쪽으로 당겨서, corridor 벽에서 그 거리 이내로 들어오면(아직 안을
벗어나지 않았어도) 미리 페널티가 붙기 시작. `weightClr(penna_clr)`로 세기 조절, hard 제약
(`penna_pos`)과는 완전히 별개.

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 12 | clearance penalty 단독 (`penna_clr=1e7`, `margin=0.15m`) | **76%** | 94% | **0.111m** | 3 | **비용함수 레벨의 첫 순수 개선.** 부작용 거의 없음 |

**진단 실험 (실험 12 데이터 재분석)**: seed7/9/10의 접촉 241건 전수를 obstacle manifest CSV와
대조 — 반대쪽 두 번째로 가까운 장애물까지 거리가 **최소 0.79m, 중앙값 1.6m대**였습니다.
0.15m는커녕 1m 이상 여유가 있는 곳에서도 여전히 부딪힘. **→ 실제 물리적 공간은 충분한데,
corridor 자체가 좁게(robot_r=0.2 hard 기준) 만들어져서 최적화기가 그 공간에 접근할 방법이
없었다**는 결론 (이 실험은 `corridor_pref_margin`을 켜지 않은 상태였음).

### 3.5 조합 시도

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 13 | clearance penalty + 균일마진 0.4m | 84% | 90% | 0.086m | 5 | **실패** — clr penalty 단독보다 전부 나쁨. 가설: 균일마진 corridor는 다운샘플링된(부정확한) 점군 기준 "여유 있음" 판단이라, 옵티마이저가 그 부정확한 여유를 믿고 더 적극적으로 움직여서 역효과 |
| 14 | clearance penalty + `obs_skip_num=1` | 74% | **98%(전체 최고)** | 0.126m | **1(최소)** | 완주율/안정성은 전체 실험 중 최고. 그러나 **접촉률은 obs_skip_num=1 단독(70%)을 못 넘음** — 오히려 근소 악화(70%→74%) |

## 4. 최종 비교표 (핵심만)

| 방법 | 완주율 | 접촉률 | 평균 clearance | 타임아웃 |
|---|---|---|---|---|
| baseline | 96% | 82% | 0.084m | ~0 |
| **obs_skip_num=1 단독** | 96% | **70%** | 0.141m | 낮음 |
| clearance penalty 단독 | 94% | 76% | 0.111m | 3 |
| clearance penalty + obs_skip_num=1 | **98%** | 74% | 0.126m | **1** |
| CIRI 균일 선호마진 단독 | 98% | 86% | 0.074m | 1 |

## 5. 코드 변경 사항 (전부 `/root/super_ws/src/SUPER/super_planner/`, 아직 미커밋)

### 5.1 CIRI corridor 균일 선호마진 (`corridor_pref_margin`)
- `include/super_core/config.hpp:81,122-124` — 새 yaml 키 `super_planner/corridor_pref_margin`
  (기본 -1 → robot_r로 clamp).
- `include/super_core/ciri.h` — `pref_margin_` 멤버, `setupParams(robot_r, iter_num, pref_margin=-1)`.
- `src/super_core/ciri.cpp:62-77` — **핵심 로직**: 코리도 세그먼트(seed line a,b) 전체에서
  가장 가까운 장애물점까지 거리(`d_min_seed`)를 먼저 스캔해서,
  `local_margin = clamp(d_min_seed, robot_r_, pref_margin_)`로 **그 코리도 전체에 통일된
  마진**을 적용 (한 코리도 안에서 벽마다 마진이 섞이는 비대칭 문제 방지).
- `src/super_core/ciri.cpp:280-317` — `logMarginDebug()`: 환경변수 `CIRI_MARGIN_DEBUG=1`일 때
  `/tmp/ciri_margin_debug.csv`에 각 코리도의 `local_margin`, fallback 여부 등을 기록하는 진단
  로그 (프로덕션에 영향 없음, `pref_margin_ <= robot_r_`이면 아예 비활성).
- `include/super_core/corridor_generator.h:85-88`, `src/super_core/corridor_generator.cpp:34-38`
  — `corridor_pref_margin` 파라미터를 CIRI까지 전달하는 배선.
- `src/super_core/super_planner.cpp:77-84` — `CorridorGenerator` 생성자 호출에
  `cfg_.corridor_pref_margin` 추가.

### 5.2 MINCO Clearance Penalty (`penna_clr`, `clearance_margin`)
- `include/traj_opt/config.hpp:70-75,121-122` — 새 yaml 키 `traj_opt/exp_traj/penna_clr`,
  `traj_opt/exp_traj/clearance_margin`.
- `include/traj_opt/exp_traj_optimizer_s4.h:79` — `OptimizationVariables`에
  `weightClr`, `clearanceMargin` 추가. `constraintsFunctional` 시그니처에 두 파라미터 추가
  (`:115-120` 근방).
- `src/traj_opt/exp_traj_optimizer_s4.cpp:125-150` — **핵심 로직**: 기존 위치 제약 루프(K개
  SFC 평면에 대해 반복하는 for문) 안에, 기존 `violaPos` 계산 바로 뒤에
  `violaClr = violaPos + clearanceMargin`을 추가하고 동일한 `smoothedL1` 페널티 형태로
  `gradPos`/`tmp_cost`에 누적. `weightClr>0 && clearanceMargin>0`일 때만 활성화.
- `src/traj_opt/exp_traj_optimizer_s4.cpp:286,337` — `costFunctional`에서 `obj.weightClr`/
  `obj.clearanceMargin`을 읽어 `constraintsFunctional` 호출부에 전달.
- `src/traj_opt/exp_traj_optimizer_s4.cpp:806-807` — 생성자에서 `cfg_.penna_clr`/
  `cfg_.clearance_margin`을 `opt_vars`에 복사.
- **참고**: `BackupTrajOpt`(`backup_traj_optimizer_s4.cpp`)는 별개 클래스라 이 변경의 영향을
  받지 않음.

### 5.3 리버트된 것
- `super_planner.cpp`의 guide_path 중앙 정렬 코드(4개 버전, §3.1)는 전부 작성 후 리버트되어
  현재 파일에 남아있지 않음. `super_planner.cpp`에는 이 세션과 무관한 (다른 세션의)
  `trajectory_guard` 관련 미커밋 diff가 이미 있었는데, 그건 건드리지 않음.

## 6. 설정 파일 (전부 `/root/super_ws/src/SUPER/super_planner/config/`, 미러본은
`/root/super-sector-filter/super_patches/native_seedmap_campaign/super_planner_config/`)

- `static_seedmaps_paper_v10.yaml` — baseline
- `static_seedmaps_skip1_v10.yaml` — 실험 6 (`obs_skip_num=1`)
- `static_seedmaps_prefmargin_v10.yaml` — 실험 7,8 (`corridor_pref_margin=0.4`)
- `static_seedmaps_skip1_prefmargin_v10.yaml` — 실험 9
- `static_seedmaps_boundhalf_v10.yaml` — 실험 10 (`corridor_bound_dis=0.4`)
- `static_seedmaps_bound06_v10.yaml` — 실험 11 (`corridor_bound_dis=0.6`)
- `static_seedmaps_clrpenalty_v10.yaml` — 실험 12 (`penna_clr=1e7, clearance_margin=0.15`)
- `static_seedmaps_clrpenalty_prefmargin_v10.yaml` — 실험 13
- `static_seedmaps_clrpenalty_skip1_v10.yaml` — 실험 14

## 7. 원시 데이터 위치 (⚠ `/tmp`라 세션 종료 시 소실될 수 있음 — Codex 세션에서 접근
불가능할 가능성이 높으므로, 이 문서의 §3~4 표를 1차 자료로 취급할 것)

- `/tmp/native_campaign/seed{1-10}_run{1-5}_<variant>_v10_full.json` — 각 run의 전체 결과
  (`success`, `collisions`, `min_clearance_m`, `contact_events`[position/position_command/
  nearest_point 포함] 등).
- `/tmp/native_campaign/ciri_margin_debug_seed{N}_*.csv` — CIRI 코리도별 마진/fallback 로그
  (실험 8 진단용).
- 이전 세션에서 이미 커밋된 관련 데이터: `results/native_seed1_10_full_v10_contact_curvature.csv`,
  `results/native_seed1_10_v10_margin_dynamics_ablation.csv`,
  `results/native_seed1_10_full_n5_contact_coordinates.csv`.

## 8. Codex에게 묻고 싶은 것

1. §3.5 실험 14 (`clearance penalty + obs_skip_num=1`)에서 완주율은 최고(98%)인데 접촉률이
   obs_skip_num=1 단독(70%)보다 근소하게 나쁜(74%) 이유가 뭘까요? 두 메커니즘이 서로 다른
   레이어(corridor 생성 정확도 vs 최적화기 행동)라 순수하게 더해질 거라 예상했는데 아니었습니다.
2. `exp_traj_optimizer_s4.cpp`의 clearance penalty 구현(§3.4, §5.2) 자체에 버그나 설계
   결함이 있는지 봐주실 수 있나요? (예: `smoothedL1`의 `smoothFactor=smooth_eps=0.01`을
   `violaPos`와 `violaClr`가 공유하는 게 맞는지, gradient 부호나 스케일이 맞는지 등)
3. `penna_clr=1e7`, `clearance_margin=0.15`는 초기 추정치였고 별도 캘리브레이션을 하지
   못했습니다. 다른 페널티 가중치(`penna_pos=5e9`, `penna_vel/acc/jerk=5e8`)와 비교했을 때
   합리적인 스케일인지, 더 나은 튜닝 방향이 있는지 의견 부탁드립니다.
4. corridor 생성(CIRI) 레벨에서, "다운샘플링 없이(`obs_skip_num=1`) 정확하게 만든 corridor"에
   대해 "균일 선호마진"이 아닌 다른 방식으로 폭을 넓히는 게 가능할지 (예: 장애물 표면까지의
  실제 최근접 거리를 더 정밀하게 재는 방법, voxel 해상도 자체를 높이는 것과의 상호작용 등).

## 9. Codex가 참고해야 할 파일 목록 (우선순위 순)

1. **이 문서** (`/root/super-sector-filter/docs/codex_handoff_full_v10_contact_investigation.md`)
2. `/root/super_ws/src/SUPER/super_planner/src/traj_opt/exp_traj_optimizer_s4.cpp` — clearance
   penalty 구현 전체 맥락 (특히 45-244줄 `constraintsFunctional`, 251-344줄 `costFunctional`)
3. `/root/super_ws/src/SUPER/super_planner/include/traj_opt/exp_traj_optimizer_s4.h`
4. `/root/super_ws/src/SUPER/super_planner/src/super_core/ciri.cpp` — CIRI 균일마진 구현
   (30-253줄 `comvexDecomposition`)
5. `/root/super_ws/src/SUPER/super_planner/include/super_core/ciri.h`
6. `/root/super_ws/src/SUPER/super_planner/src/super_core/corridor_generator.cpp`
7. `/root/super_ws/src/SUPER/super_planner/include/super_core/config.hpp` (super_core) 와
   `/root/super_ws/src/SUPER/super_planner/include/traj_opt/config.hpp` (traj_opt) — 새 yaml
   파라미터 정의
8. `/root/super_ws/src/SUPER/super_planner/config/static_seedmaps_clrpenalty_skip1_v10.yaml` —
   가장 균형 잡힌 실험(14)의 실제 설정값
9. `/root/super-sector-filter/docs/paper_story.md` §3.6 이후, `/root/super-sector-filter/docs/연구일지.md`
   최신 항목들 — 이 세션 이전에 확립된 배경(회전반경 분석, 장애물 간격 실측 등)
