# Near-field hard gate와 passage centering 4단계 구현 기록 (2026-08-31)

## 결론

요청한 네 단계는 모두 구현하고 Map 7에서 기능 검증했다.

1. long-lived trajectory도 새 LiDAR scan 기준 최대 10 Hz로 다시 검사한다.
2. planner 입력과 map을 건드리지 않는 deterministic replay로 반경 0.20 m
   `OCCUPIED` 검출을 증명했다.
3. 최신 generation/scan과 일치하는 결과만 hard brake하며, 이미 hit 안에서
   시작하면 재진입 없이 바깥으로 진행하는 monotonic egress를 허용한다.
4. CIRI의 실제 장애물 유래 양면만 골라 좌우 clearance를 계측하고 Exp/Backup
   optimizer에 passage-only balance 비용을 구현했다.

Near-field hard gate와 passage balance는 모두 전역 기본값이 꺼져 있다. 표준
`static_seedmaps_guard_viability_tight_v7.yaml` 및 실사용 filtered profile은
변경하지 않았다. Raw-cloud CIRI shadow도 계속 `false`다. 이번 검증은 Map 7
단일 실행들과 test-only replay이므로 population-level 안전 보장이 아니다.

## 1. New-scan cadence latest-only near-field shadow

기존 worker는 trajectory generation이 바뀔 때만 검사했다. trajectory가 오래
유지되는 동안 새 scan에서 처음 보인 가까운 점은 놓칠 수 있었다. 이제 raw
cloud window가 batch를 실제로 보유한 뒤 sequence를 publish하고, 다음 두 경우에
job을 만든다.

- 새 committed trajectory generation: rate limit을 우회해 즉시 검사
- 같은 generation의 새 accepted raw-cloud sequence: 0.10초 이상의 bounded
  cadence로 최신 job만 검사

FSM 100 Hz callback은 snapshot을 만들고 마지막 완료 결과를 읽을 뿐이다.
PointCloud 변환, window fetch, AABB crop과 KD-tree query는 별도 worker에서
실행한다. Job/result log에는 `cloud_seq`와 `NEW_SCAN`/`NEW_GENERATION` trigger를
남긴다.

Map 7 Full smoke는 99.81초에 완주했고 static contact와 속도 위반은 0이었다.
결과 331건은 `NEW_SCAN=183`, `NEW_GENERATION=148`, skip 0, 모두 `NO_HIT`였다.
Queue mean/max는 0.084/0.169 ms, worker total mean/max는 5.601/23.933 ms였다.

## 2. Deterministic raw-hit replay

`trajectory_guard_raw_cloud_near_field_test_replay_mode`를 추가했다.

- `0`: off, 전역 기본값
- `1`: 첫 job의 future-tail에 한 점을 주입
- `2`: 첫 job의 current body에 한 점을 주입

주입점은 실제 cloud의 freshness와 density 검사를 통과한 뒤 worker-private crop
복사본에만 한 번 추가된다. ROG-Map, subscribed PointCloud2, trajectory와 비행
결정에는 영향을 주지 않으며 로그에 `TEST_ONLY`가 명시된다.

Future-tail shadow run은 98.44초, 완주·static-safe였다. 총 394건 중 정확히 첫
결과 1건이 `OCCUPIED`였고 나머지 393건은 `NO_HIT`였다. 최소 KD distance는
0.1904 m로 설정 반경 0.20 m 안이었다. 이 결과는 실제 stochastic contact의
재현은 아니지만 r=0.20 검출 경로를 결정론적으로 증명한다.

## 3. Fresh matched hard gate와 monotonic egress

`trajectory_guard_raw_cloud_near_field_enforce_en`은 기본 `false`다. 명시적으로
켰을 때도 `OCCUPIED`가 다음 조건을 전부 만족해야만 brake한다.

- 현재 committed trajectory generation과 result generation이 같음
- result age가 0.20초 이하
- result cloud sequence가 현재 sequence보다 미래가 아니고 lag가 1 이하
- 현재 trajectory time이 worker가 검사한 `[from_tt, to_tt]` 안에 있음

새 `OCCUPIED` result는 main FSM이 소비하기 전에 다음 `NO_HIT`가 덮지 못하도록
latched된다. 조건 불일치 결과는 `IGNORE`로 로그만 남긴다.

Current body가 이미 witness sphere 안이면 무조건 brake하지 않는다. 내부에
있는 동안 witness까지 거리가 감소하면 차단하고, 거리 증가 방향으로 최소
0.02 m 진행해 clearance+0.005 m 밖으로 나가면 `EGRESS`로 허용한다. 한 번
나간 뒤 horizon에서 다시 sphere 안으로 들어오는 경로는 허용하지 않는다.
초기 구현은 egress 뒤의 모든 곡률에도 거리 단조성을 요구해 불필요한 brake를
냈고, 이 조건을 위의 inside-only monotonic + no-reentry 규칙으로 수정했다.

검증 결과는 다음과 같다.

| 경우 | 완주/접촉 | witness 판정 | near-field hard brake |
|---|---:|---:|---:|
| future-tail entry replay | 1/1, 0 | OCCUPIED 1 | 1 |
| current-body egress replay | 1/1, 0 | EGRESS 1 | 0 |
| replay 없는 real-cloud smoke | 1/1, 0 | NO_HIT 308 | 0 |

Entry run에서 request 1, generation 1, cloud sequence 13의 `OCCUPIED`가 완료된
뒤 약 1 ms에 brake했고 0.943초 뒤 generation 2로 복구했다. Egress 수정본은
body distance 0.0 m인 합성 hit를 `EGRESS`로 분류하고 72.90초에 brake 없이
완주했다. Real-cloud 1회에서 false brake는 없었지만, 이 n=1 결과로 false
positive rate나 실제 접촉 방지를 주장하지 않는다.

## 4. Bilateral passage clearance 계측과 비용

Full sensing이어도 optimizer에는 통로 중앙 목표가 없다. 이전 nearest-face
clearance term은 순항 속도에서 0이고, A*/CIRI seed와 time/smoothness 목적이
한쪽으로 치우친 경로를 유지할 수 있다. 이를 일반적인 bounding-box 중앙화로
바꾸면 열린 공간에서도 잘못된 힘을 만들기 때문에 다음 조건을 모두 만족하는
face pair만 passage로 정의했다.

- 두 face 모두 CIRI가 실제 obstacle point에서 만든 plane
- 두 normal의 수평 성분이 각각 0.8 이상
- 수평 normal이 cosine 0.90 이상으로 반대 방향
- 두 clearance의 합이 3.0 m 이하

이를 위해 `Polytope`에 face obstacle provenance를 보존하고 CIRI의 boundary
plane과 obstacle plane을 구분했다. 후보 pair는 polytope별로 한 번만
precompute한다. 매 적분점에서는 가장 좁은 유효 pair의 두 signed clearance를
측정한다. `|left-right|-0.15 m`가 양수일 때만 squared balance cost를 더한다.
ExpTrajOpt와 BackupTrajOpt를 모두 구현 범위에 포함했으며 `[PASSAGE_BALANCE]`
로그는 active 비율, 평균/최대 imbalance, width, min-side와 진행방향 기준
left/right 평균을 남긴다.

Provenance가 없던 첫 계측은 CIRI bounding faces까지 passage로 오인해 다수
trajectory에서 active 100%가 나왔고 기각했다. Provenance 수정 후 Map 7 Full
baseline은 Exp sample의 11.89%만 passage로 활성화됐으며 평균 absolute
imbalance는 0.3508 m였다.

비용 후보 결과는 다음과 같다.

| 후보 | Map 7 Full 결과 | 판단 |
|---|---:|---|
| Exp+Backup 2e6 | 180초, waypoint 3/5 | 기각 |
| Exp+Backup 2e5 | 180초, waypoint 2/5 | 기각 |
| Exp+Backup 2e5 + pair precompute | 180초, waypoint 3/5 | 계산량만 원인이 아님; 기각 |
| Exp 2e4, Backup off | 76.79초, 5/5, 접촉 0 | 기능 검증 통과, 실험용만 유지 |

약한 후보의 별도 1회에서는 평균 imbalance가 0.3508→0.3051 m, 약 13.0%
줄었다. 그러나 서로 다른 stochastic run이고 guard brake가 17→23, physical
최소 clearance가 +0.263→+0.198 m였으므로 개선의 인과 증거나 안전 개선으로
해석할 수 없다. 강한 후보의 liveness 회귀는 단순 O(K²) 탐색이 아니라 목적함수
상호작용 때문이었다.

같은 약한 후보의 Map 7 3모드 smoke 결과는 다음과 같다.

| 모드 | 완주 | static contact | 시간 (s) | clearance (m) | payload (MiB/s) | FSM CPU (%) | passage imbalance (m) | Adaptive full-open |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 1/1 | 0 | 99.06 | +0.268 | 5.563 | 75.40 | 0.3195 | - |
| Sector | 1/1 | 1 | 81.31 | -0.094 | 1.907 | 70.47 | 0.3546 | - |
| Adaptive | 1/1 | 0 | 103.72 | +0.264 | 2.795 | 66.71 | 0.3281 | 4 |

표는 기능 smoke일 뿐 모드 간 통계 비교가 아니다. 특히 Sector 접촉 1회가
연구 가설 방향과 맞더라도 n=1로 Sector 열위를 주장할 수 없다. 약한 centering
profile도 기본/실사용 설정에 채택하지 않는다. 계측과 default-off optimizer
기능은 후속 matched A/B에 쓸 수 있도록 보존한다.

## 변경 파일과 검증

핵심 파일은 다음과 같다.

- `super_planner/include/fsm/config.hpp`
- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`
- `super_planner/include/data_structure/base/polytope.h`
- `super_planner/src/utils/polytope.cpp`
- `super_planner/src/super_core/ciri.cpp`
- `super_planner/include/traj_opt/passage_centering.hpp`
- Exp/Backup trajectory optimizer header와 source
- `*_nearfield*.yaml`, `*_passage_*.yaml` 실험 profile

Release build는 `cmake --build ... -j4 -l4`로 통과했고 campaign pytest는
23/23 통과했다. 전체 정량 결과는
`results/near_field_hard_gate_and_passage_centering_summary_20260831.csv`에
모았다. 첫 entry profile 생성 중 YAML이 잘린 infrastructure-invalid 1회는
비행 결과로 세지 않았으며, 올바른 full profile로 다시 실행한 v2만 표에 썼다.

## 다음 판단 기준

Near-field hard gate를 실사용으로 승격하려면 Map 7을 포함한 matched shadow-on/
off 반복과 실제 contact-correlated capture가 더 필요하다. 그 뒤 enforce 후보를
Map 1-10, 세 모드, 반복 실행으로 검증해야 한다. Passage cost는 현재 채택하지
않고, 먼저 동일 trajectory/seed에 가까운 paired 계측으로 left-hugging 구간을
재현한 뒤 balance 감소와 완주·guard duty·physical clearance를 함께 만족하는
경우에만 다시 평가한다.
