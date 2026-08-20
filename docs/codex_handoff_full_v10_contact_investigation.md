# Codex 인계 문서 — SUPER `full` 모드 v=10 잔여 접촉 조사 (2026-08-13)

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
