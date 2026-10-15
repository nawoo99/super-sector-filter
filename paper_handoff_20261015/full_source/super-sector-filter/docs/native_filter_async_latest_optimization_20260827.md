# Native C++ 필터 latest-only 워커 최적화 (2026-08-27)

## 결론

Adaptive의 맵 9·10 장기 지연은 경로 길이 자체보다
`MAP_STALE -> certified brake -> fresh-map replan` 반복에 집중돼 있었다.
안전 threshold를 줄이는 방법은 실제 접촉을 만들었으므로 폐기했고, 외부 native
C++ 필터의 raw-cloud 수신 콜백에서 point filtering과 reliable publish를 분리해
별도 latest-only 워커로 옮겼다.

최종 구현은 맵 9·10 Adaptive 집중 n=3에서 6/6 완주·접촉 0이었고, 기존 n=3과
비교한 평균 임무시간은 102.87초에서 88.01초로 14.45% 줄었다. 이어서
맵 1~10 x Full/Sector/Adaptive x n=1의 30개 run도 전부 first-attempt 완주,
live/static contact 0, speed-valid였다. 이 결과는 관측 회귀 통과이지 population
100%, 형식적 collision-free 또는 hardware flight-ready 보장은 아니다.

## 안전 threshold 단축 후보의 기각

기존 2.5초 trajectory-guard hold를 0.5초로 줄이는 후보를 먼저 시험했다.
맵 9은 3/3 완주·접촉 0이고 평균 87.76초였지만, 맵 10 첫 run은 81.43초에
완주하면서 live contact 2회, static collision 1회, static clearance -0.157m를
기록했다. 첫 접촉은 41.589초, 속도 0.617m/s였다.

Guard가 generation 96/map 135에서 해제된 1.676초 뒤 접촉했고, 다음 guard는
접촉 뒤에야 활성화됐다. 따라서 hold는 단순 성능 지연이 아니라 현재 timing
chain의 안전 여유다. 후보 캠페인은 즉시 중단했으며 0.5초 값은 어떤 실사용
프로파일이나 default에도 반영하지 않았다.

Raw: `results/adaptive_hold05_seed9_10_n3_raw_20260827.csv`

## 구현

수정 파일:

- source: `mission_planner/Apps/native_sector_cpp.cpp`
- mirror: `super_patches/native_seedmap_campaign/mission_planner_Apps/native_sector_cpp.cpp`
- runner schema: `scripts/native_campaign/native_campaign.py`

변경 경계는 다음과 같다.

1. `/cloud_registered` subscription callback은 입력 counter를 올리고 pending
   cloud 한 장을 교체한 뒤 즉시 반환한다.
2. 별도 worker가 pending cloud를 가져가 기존 filtering, state update와 reliable
   `/cloud_sector` publish를 수행한다.
3. 새 raw cloud가 worker보다 빨리 오면 pending 한 장만 최신 frame으로 교체한다.
   무제한 queue는 만들지 않는다.
4. odometry, map commit/ACK, replan, trajectory-guard와 filter state는 하나의
   mutex 아래 직렬화해 기존 state transition의 data race를 만들지 않는다.
5. 종료 시 pending을 폐기하고 worker를 join한 뒤 마지막 stats를 기록한다.
6. `cloud_input_callbacks`와 `cloud_worker_overwrites`를 JSON/CSV에 추가했다.

Reliable depth-1 filtered link, exact-generation ACK, certified resume, 2.5초
guard hold, FOV, clearance와 velocity certificate는 바꾸지 않았다. Raw-cloud
CIRI도 계속 default false, shadow-only, non-authoritative다.

## 맵 9·10 집중 n=3

| Map | 기존 Adaptive 완료/안전 | 기존 평균/최대 시간 (s) | async 완료/안전 | async 평균/최대 시간 (s) | async 최소 clearance (m) | Brake 평균 | Recovery active 평균 (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9 | 3/3 | 102.04 / 108.58 | 3/3 | 87.61 / 97.05 | +0.226 | 34.33 | 37.13 |
| 10 | 3/3 | 103.70 / 128.46 | 3/3 | 88.40 / 97.64 | +0.193 | 36.00 | 45.03 |

두 맵을 합치면 brake 성공은 run당 51.50회에서 35.17회로 31.72%, recovery
active 합은 54.60초에서 41.08초로 24.77% 줄었다. 평균 clearance는
+0.238m에서 +0.226m로 0.012m 작아졌지만 모든 run에서 양수였고 contact는 0이다.
Trajectory-guard ACK는 211/211, pre-stale ACK는 522/522였으며 timeout, abandon,
supersede와 campaign retry는 모두 0이었다.

`cloud_input_callbacks == frames == 2,764`, worker overwrite는 0이었다. 따라서
이번 표본의 개선을 “프레임을 많이 버려 연산량을 줄였다”로 설명하면 안 된다.
관측상 차이는 DDS callback/reliable publish의 scheduling 경계를 분리한 뒤
stale-brake 반복이 감소한 것이다. 또한 이전/이후 n=3은 같은 설정이지만
interleaved paired A/B가 아니므로 14.45%를 확정적 인과효과로 과장하지 않는다.

Raw: `results/adaptive_async_latest_seed9_10_n3_raw_20260827.csv`

## 맵 1~10 세 모드 n=1 회귀

모든 행은 `complete=1/1`, live/static contact 0, speed-valid다. `F/S/A`는
Full/fixed-Sector/Adaptive이며 opens는 Adaptive effective full-view open edge다.

| Map | F time | S time | A time | F/S/A clearance (m) | F/S/A points/update | F/S/A total/update (ms) | F/S/A FSM CPU (%) | A opens | A brakes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 55.14 | 56.09 | 55.84 | +0.207/+0.256/+0.233 | 15,084/7,348/13,394 | 28.47/11.62/24.79 | 115.8/103.5/110.8 | 10 | 2 |
| 2 | 58.94 | 56.12 | 63.14 | +0.303/+0.352/+0.351 | 15,510/7,006/12,641 | 32.32/11.74/24.39 | 115.1/99.2/93.2 | 17 | 13 |
| 3 | 72.93 | 71.72 | 71.07 | +0.314/+0.230/+0.323 | 22,211/10,515/18,939 | 35.93/13.57/29.35 | 90.5/79.3/79.6 | 11 | 24 |
| 4 | 68.60 | 66.50 | 69.57 | +0.237/+0.247/+0.261 | 24,934/13,955/20,970 | 36.22/13.79/30.03 | 107.3/93.8/84.4 | 12 | 22 |
| 5 | 68.43 | 71.37 | 73.11 | +0.199/+0.319/+0.266 | 28,831/12,568/24,342 | 40.59/14.76/32.36 | 103.1/77.8/78.5 | 8 | 26 |
| 6 | 86.75 | 65.49 | 74.51 | +0.145/+0.262/+0.278 | 28,160/15,823/25,170 | 37.15/14.79/32.41 | 80.6/91.7/75.7 | 7 | 31 |
| 7 | 74.40 | 86.81 | 71.24 | +0.263/+0.218/+0.283 | 36,443/20,114/30,040 | 39.41/13.72/31.53 | 100.1/67.7/91.4 | 10 | 18 |
| 8 | 64.18 | 74.08 | 81.25 | +0.249/+0.201/+0.284 | 34,034/17,724/29,062 | 42.77/14.86/32.11 | 113.2/73.4/79.2 | 10 | 27 |
| 9 | 83.51 | 81.76 | 80.45 | +0.289/+0.298/+0.241 | 42,436/24,431/35,878 | 35.97/14.27/29.55 | 85.3/81.6/89.2 | 15 | 22 |
| 10 | 87.88 | 78.53 | 88.44 | +0.212/+0.288/+0.185 | 37,937/24,231/35,956 | 38.04/14.76/31.54 | 94.8/86.4/70.4 | 8 | 40 |

| n=1 aggregate vs Full | Points/update | Map total/update | Raycast/update | Occupancy update | FSM CPU | Planner+filter core-seconds | Mission time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sector | -46.17% | -62.42% | -61.91% | -63.43% | -15.04% | -13.60% | -1.71% |
| Adaptive | -13.72% | -18.76% | -22.99% | -10.49% | -15.23% | -10.92% | +1.09% |

Adaptive의 external filter CPU는 평균 3.02%였고 effective opens는 총 108회,
10.8회/run이었다. Trajectory-guard ACK 226/226, pre-stale ACK 698/698,
timeout/abandon/supersede/final pending은 0이다. C++ filter가 실행된 broad 20개
행에서도 input callback과 processed frame 수가 같고 overwrite는 모두 0이었다.

이 n=1에서는 Sector도 10/10 안전했지만, 직전 current-binary n=3에서 Sector
map9 contact가 있었으므로 Sector가 개선됐거나 안전해졌다는 결론은 내리지 않는다.
Full에는 native filter가 개입하지 않으며 이번 Full 10/10은 회귀 기준 확인이다.

Raw: `results/async_latest_3mode_seed1_10_n1_raw_20260827.csv`

## 검증과 남은 한계

- `colcon build --packages-select mission_planner --symlink-install`: 통과
- Python/C++ synthetic geometry/stats equivalence: 통과, retained point 3개 일치
- `compileall`: 통과
- `unittest`: 13/13 통과
- `pytest`: 19/19 통과
- source/mirror C++ 파일: byte-identical
- 집중 6회 + broad 30회: first-attempt, retry 0, OOM delta 0, FSM swap 0

Host swap은 캠페인 전부터 거의 full이었지만 memory PSI는 모든 accepted run에서
0이고 cgroup peak swap은 최대 약 564MiB였다. 이번 36회에는 infrastructure retry,
OOM 또는 planner swap이 없었다.

이번 변경은 observed scheduling/liveness tail을 줄인 engineering optimization이다.
프레임 overwrite가 0이었고 interleaved paired A/B가 아니므로 CPU workload 감소의
원인으로 주장하지 않는다. 맵 8 Adaptive n=1은 Full보다 17.07초 길어 timing
분산도 완전히 사라지지 않았다. `obs_skip_num` no-op, NaN/clearance-penalty 결함,
BackupTrajOpt coverage gap과 `DRONE_R=robot_r` 접촉지표 한계는 그대로다.
