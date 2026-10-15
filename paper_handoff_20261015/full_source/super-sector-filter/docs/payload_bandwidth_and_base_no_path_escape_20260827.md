# ROG-Map 처리 payload 대역폭과 base-NO_PATH 복구 (2026-08-27)

## 결론

Full/Sector/Adaptive 비교에 ROG-Map이 실제 update에 사용한
`sensor_msgs::msg::PointCloud2::data` payload를 추가했다. 각 update의 bytes와
`point_step`을 기존 performance CSV에 기록하고, runner가 mission 구간의
frames/s, points/s, MiB/s와 Mbit/s를 계산한다. 별도 subscriber를 추가하지
않았으며 planner/filter의 안전 threshold도 바꾸지 않았다.

맵 1~10 세 모드 n=1의 기술적 baseline에서 map별 Full 대비 payload MiB/s
감소율 평균은 fixed Sector 64.44%, Adaptive 49.02%였다. 그러나 map9 Sector는
접촉 후 timeout, Adaptive는 접촉 없이 timeout이므로 이 한 번의 평균을 정상
완주 성능의 확정값으로 사용하면 안 된다. Timeout Adaptive가 92.19% full-open
duty를 유지하면서 7.324 MiB/s까지 올라간 것은 높은 대역폭이 정지 원인이라는
뜻이 아니라, 장기 recovery가 full view를 계속 열어 둔 결과다.

map9 Adaptive 로그의 실제 liveness 결함은 `NO_PATH` 자체였다. 한 번의 certified
local escape 뒤 base search가 계속 `NO_PATH`였고, vertical lift도 기존 hard
guard에 거절되자 140초 동안 같은 실패를 13,355회 반복했다. 남은 horizontal
escape budget이 있어도 영구 certified hold로 바로 들어가던 연결 누락을
수정했다. Vertical budget이 소진된 base-NO_PATH는 이제 goal 방향을 순서 힌트로
기존 8방향 local-escape certificate를 재사용한다. 각 후보는 정지 상태에서만
생성되고 기존 trajectory/stop-viability guard를 그대로 통과해야 한다.

## 계측 정의와 한계

계측값은 각 ROG-Map update가 선택한 `PointCloud2` frame의 `data.size()` 합이다.
따라서 다음을 포함한다.

- Full의 XYZ+intensity payload (`point_step=32`)
- C++ Sector의 XYZ payload (`point_step=20`)
- Adaptive가 sector/full frame을 섞어 처리한 실제 평균 `point_step`
- mission 구간에서 실제 map update에 사용된 frame/point/payload 처리율

다음은 포함하지 않는다.

- `PointCloud2` metadata, CDR/DDS/RTPS header와 reliable retransmission
- latest-only pending slot에서 map update 전에 덮어쓴 frame의 bytes
- host NIC throughput

현재 Fast DDS 통신은 같은 host 안에서 이루어지므로 이 값은 wire/network
bandwidth가 아니라 **ROG-Map processed application-payload throughput**이다.
연산 입력량 비교에는 직접적인 값이지만 실제 무선 링크 요구량으로 해석하면 안
된다.

## 맵 1~10 세 모드 n=1 payload baseline

`OK`는 완주·live/static contact 0, `CONTACT`는 접촉 발생, `TIMEOUT`은 접촉 없이
미완주다. 감소율은 같은 맵 Full MiB/s 대비다. 이 캠페인은 base-NO_PATH 수정 전,
payload 계측이 들어간 바이너리에서 수행했다.

| Map | Full: 결과, s / MiB/s | Sector: 결과, s / MiB/s (감소) | Adaptive: 결과, s / MiB/s (감소), opens |
|---:|---:|---:|---:|
| 1 | OK, 58.65 / 3.466 | OK, 63.58 / 0.981 (-71.7%) | OK, 66.02 / 1.406 (-59.4%), 13 |
| 2 | OK, 54.90 / 3.707 | OK, 55.41 / 0.989 (-73.3%) | OK, 55.37 / 1.304 (-64.8%), 22 |
| 3 | OK, 74.37 / 3.727 | OK, 64.57 / 0.945 (-74.6%) | OK, 73.50 / 1.847 (-50.4%), 13 |
| 4 | OK, 69.99 / 4.358 | OK, 76.83 / 1.505 (-65.5%) | OK, 64.18 / 2.078 (-52.3%), 14 |
| 5 | OK, 70.10 / 5.518 | OK, 68.12 / 1.403 (-74.6%) | OK, 66.57 / 2.202 (-60.1%), 12 |
| 6 | OK, 78.24 / 5.003 | OK, 68.10 / 1.678 (-66.5%) | OK, 93.97 / 2.407 (-51.9%), 12 |
| 7 | OK, 81.41 / 6.033 | OK, 82.90 / 1.826 (-69.7%) | OK, 88.23 / 2.796 (-53.7%), 5 |
| 8 | OK, 72.27 / 4.976 | OK, 73.91 / 1.374 (-72.4%) | OK, 76.06 / 2.624 (-47.3%), 7 |
| 9 | OK, 72.88 / 8.396 | CONTACT, 180.01 / 6.439 (-23.3%) | TIMEOUT, 180.01 / 7.324 (-12.8%), 9 |
| 10 | OK, 89.78 / 5.583 | OK, 71.72 / 2.633 (-52.8%) | OK, 82.37 / 3.490 (-37.5%), 7 |

| Mode | Complete | Contact-free | Mean time (s) | Mean payload (MiB/s) | Mean payload (Mbit/s) | Mean point_step | Effective opens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 10/10 | 72.26 | 5.077 | 42.59 | 32.00 | 0 |
| Sector | 9/10 | 9/10 | 80.52 | 1.977 | 16.59 | 20.00 | 0 |
| Adaptive | 9/10 | 10/10 | 84.63 | 2.748 | 23.05 | 23.75 | 114 |

Arithmetic mean 기준 payload는 Full 대비 Sector 61.06%, Adaptive 45.88%
낮았다. 각 map의 paired 감소율을 동일 가중 평균하면 64.44%, 49.02%다. 성공한
row만 사용하면 69.01%, 53.05%이지만 실패를 제외한 선택 편향이 있으므로 map별
표가 주 결과다. 모든 30개 row는 retry/OOM 0이었다. Host swap은 캠페인 시작
전부터 거의 full이었지만 이 캠페인 자체의 OOM이나 infrastructure retry는
없었다.

Raw:
`results/bandwidth_3mode_seed1_10_n1_raw_20260827.csv`

## map9 Adaptive liveness 원인

실패 run은 waypoint 2/5 뒤 `[-23.059, -9.920, 1.428]`에서 정지했다. Live/static
contact는 0이고 최소 static clearance는 +0.141m였다. Full-refresh recovery
generation은 13/13 exact ACK됐고 trajectory-guard full-open duty는 90.61%, 전체
open duty는 92.19%였다. 즉 sector가 닫힌 상태나 ACK 누락이 아니었다.

마지막 복구 흐름은 다음과 같다.

1. start-adjacent reject 뒤 blocker가 있는 A*가 세 번 `NO_PATH`였다.
2. 기존 8방향 local escape 중 6개는 hard guard가 거절하고 7번째 0.6m 후보가
   202개 sample 검사 후 commit됐다.
3. 새 정지점의 base A*도 `NO_PATH`였다.
4. 한 번 허용된 +0.6m vertical lift는 `CLEARANCE_MARGIN`으로 거절됐다.
5. 종전 코드는 base vertical budget 소진 즉시 `BASE_NO_PATH_EXHAUSTED`로 바꾸고
   이후 140초 동안 동일 A* 실패를 13,355회 반복했다.

대역폭 계측은 두 숫자를 기존 CSV에 기록하는 기능이라 이 state transition을
만들지 않는다. 다만 계측 전 성공 run과 완전한 interleaved A/B가 아니므로 timing
perturbation이 해당 stochastic 경로 선택을 노출했을 가능성까지 부정하지 않는다.

## 수정과 검증

수정은 `super_planner.cpp`의 base-NO_PATH exhaustion 분기에만 적용했다.

- vertical lift budget이 남으면 기존처럼 lift를 먼저 요청한다.
- lift budget이 소진됐고 local-escape budget이 남으면 waypoint XY 방향을 seed로
  기존 8방향 certified local escape를 요청한다.
- escape budget도 없거나 goal 방향이 유효하지 않을 때만 기존 certified hold로
  들어간다.
- local escape 거리 0.6m, 최대 4회/episode, 2.0m episode reset, 모든 clearance,
  velocity, stop-viability와 commit 검사는 변경하지 않았다.

자연 map9 Adaptive post-patch n=3+n=5는 8/8 first-attempt 완주, contact/static
collision 0, speed-valid 8/8이었다. 평균/범위 시간은 87.30초 / 69.55~96.61초,
최소 static clearance는 +0.234m, 평균 payload는 3.364 MiB/s였다. 이 8회는 새
base local-escape 분기를 직접 밟지 않았으므로 회귀 안전성 증거이지 직접 branch
proof는 아니다.

기본 비활성 one-shot fault hook
`SUPER_TEST_FORCE_BASE_NO_PATH_ESCAPE_ONCE=1`로 맵1 Adaptive에 base `NO_PATH`
3회를 강제했다. 두 번의 독립 smoke가 모두 완주·contact 0이었고, 각 run에서
다음 순서가 직접 확인됐다.

- `TEST_FAULT_BASE_NO_PATH`: 3회
- `TRAJ_GUARD_BASE_NO_PATH_LOCAL_ESCAPE`: 1회
- `TRAJ_GUARD_COMMIT phase=PlanFromRest/certified_local_escape`: samples 202
- `TRAJ_GUARD_LOCAL_ESCAPE action=commit`: 0.6m, 1.0s, 1/8 방향
- 최종 5/5 waypoint, 65.75/60.19초, contact/static collision 0,
  worst clearance +0.311m, speed-valid 2/2

두 번째 run의 CSV는 fault injection 1, forced base-NO_PATH 3, base local-escape
arm 1, local-escape commit 1, rejection 0을 자체 열로 보존한다.

Raw:

- `results/base_no_path_escape_seed9_adaptive_n3_raw_20260827.csv`
- `results/base_no_path_escape_seed9_adaptive_n5_raw_20260827.csv`
- `results/base_no_path_fault_seed1_adaptive_raw_20260827.csv`
- `results/base_no_path_fault_seed1_adaptive_v2_raw_20260827.csv`

## 검증과 다음 단계

- `colcon build --packages-select rog_map super_planner --symlink-install`: 통과
- bandwidth parser pytest: 7/7 통과
- Python `compileall`: 통과
- source/mirror C++ 파일: byte-identical
- map9 natural regression: 8/8 complete/contact-free/speed-valid
- forced branch smoke: 2/2 complete/contact-free/speed-valid, branch/guard commit 확인

여기서 예정한 최종 map1~10 x Full/Sector/Adaptive x n=3은 이후 완료됐다.
Full/Adaptive는 각각 30/30 안전했고 Sector는 30/30 완주 중 4회 접촉했다.
Map별 completion/contact/time/effective opens/CPU/payload와 McNemar/Wilson 결과는
`docs/final_payload_base_no_path_n3_20260827.md`와 viability §8.37에 있다. 새 맵
일반화나 raw-cloud CIRI authoritative 연결은 이 후속 단계에도 포함하지 않았다.

이 결과는 population 100%, 형식적 collision freedom 또는 hardware flight
readiness를 보장하지 않는다. Raw-cloud CIRI는 default false/non-authoritative다.
`obs_skip_num` no-op, NaN/clearance-penalty 결함, BackupTrajOpt coverage gap과
`DRONE_R=robot_r` 지표 한계도 그대로다.
