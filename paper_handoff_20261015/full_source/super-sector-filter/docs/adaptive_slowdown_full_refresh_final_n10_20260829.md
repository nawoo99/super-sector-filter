# Adaptive 감속 one-shot Full refresh와 최종 map1-10 n=10 (2026-08-29)

## 결론

맵 9의 저속 접촉은 same-map replan 중복이나 Full refresh ACK 손실이 아니라,
**성공한 replan 뒤 고속에서 저속으로 바뀌는 순간에 어떤 Adaptive open 조건도
활성화되지 않는 상태 전이 공백**이었다. 이 공백에 hysteresis를 둔 one-shot
uncropped Full scan을 넣었다.

검증된 후보는 Adaptive가 3.0 m/s 이상에서 무장되고 이후 1.5 m/s 이하로
감속하면 최신 cloud 한 장만 publication cap과 sector crop을 우회해 ROG-Map에
보낸다. 요청은 기존 generation/process ACK 경로로 확인하며, 다시 3.0 m/s를
넘기 전에는 재무장하지 않는다. 정지 jitter가 연속 Full scan을 만들지 않는다.

집중 맵 9 n=10과 최종 map1-10 x Full/Sector/Adaptive x n=10을 통과했다.
최종 300회에서 Full과 Adaptive는 각각 100/100 safety-qualified였고 정적 PCD
충돌은 0이었다. Sector는 100/100 완주했지만 맵 9에서 충돌 런 1/10,
collision event 1회가 발생해 safety-qualified 99/100이었다.

이 결과는 이번 관측 cohort의 결과다. Full/Adaptive 100/100의 Wilson 95%
하한은 96.30%이므로 population 100%, formal collision freedom 또는
flight-ready를 뜻하지 않는다.

## 원인 규명

표준 default-off 프로파일의 맵 9 Adaptive를 source-PCD 최소거리 context와
함께 다시 실행했다. 여섯 번째 실행이 5.893초에 정적 PCD 접촉을 만들었다.

- 위치: `[14.549075, 12.348940, 1.049889]`
- 속도: 0.083 m/s
- nearest source-PCD point: `[14.3689, 12.3131, 1.0]`
- center distance / body clearance: 0.190359 / -0.009641 m
- waypoint index: 0
- 실제 원통 배치 `(13.736, 12.165), r=0.650`에 대한 기하 clearance도 약
  -0.0164 m였다.

접촉 직전에는 sector map 21--25가 약 0.2초 간격으로 정상 commit됐다. 따라서
map commit age가 0.25초를 넘어야 하는 pre-stale Full refresh는 열리지 않았다.
ReplanOnce도 성공했으므로 replan-failure guard가 열리지 않았다. 기존 stall
state는 1.5 m/s 이상을 2초 유지한 뒤에야 무장하고, 0.6 m/s 이하에서 다시
1.2초를 기다리므로 이 짧은 고속→저속 전이를 덮지 못했다. Online sector map은
해당 원통을 포함하지 않았지만 source PCD는 실제 body intersection을 확인했다.

즉 ACK 유실, CIRI, same-map coalescing 또는 단순 clearance penalty가 직접 원인이
아니다. 정상 commit과 성공 replan 사이에 남은 blind-sector transition gap이다.

## 구현

`mission_planner/Apps/native_sector_cpp.cpp`에 다음 default-off 옵션을 추가했다.

```text
--slowdown-full-refresh-v 1.5
--slowdown-full-refresh-rearm-v 3.0
```

Adaptive에서만 다음 상태 기계가 동작한다.

1. 속도 `>= rearm_v`이면 one-shot을 무장한다.
2. 무장 뒤 속도 `<= trigger_v`가 되면 Full refresh 하나를 pending하고 즉시
   비무장한다.
3. 다음 최신 cloud 한 장이 publication cap과 sector crop을 우회한다.
4. request kind 3으로 generation/process ACK를 추적한다.
5. 다시 `rearm_v`를 넘기 전에는 정지·저속 jitter가 추가 Full scan을 만들지
   않는다.

Runner와 CSV에는 trigger/frame/pending/ACK/committed/supersede/ACK latency를
추가했다. Source-PCD monitor에는 최소 clearance가 갱신된 정확한 시간, 위치,
속도, nearest point와 waypoint index를 저장했다.

전역 CLI 기본값은 기존 ablation 재현성을 위해 0/off로 유지한다. 아래 두 값을
명시한 C++ strict-burst 프로파일이 이번에 검증된 후보다. Raw-cloud CIRI는 계속
default false이며 실제 의사결정에 연결되지 않는다.

## 집중 맵 9 gate

후보를 맵 9 Adaptive에 10회 적용한 결과는 다음과 같다.

- 완주 10/10, source-static-PCD 충돌 0
- speed-valid 10/10, retry/OOM 0
- 평균/범위 시간 93.01 / 81.04--114.60초
- 최저 clearance +0.179 m
- slowdown Full frame와 commit ACK 543/543
- 평균 payload 30.02 Mbit/s

같은 세션의 default-off 실행은 여섯 번째 행에서 위 접촉을 만들어 중단했다.
두 cohort는 대응 난수 실험이 아니므로 10/10 대 5/6을 인과효과 크기로 해석하지
않는다. 다만 새 trigger가 직접 누락됐던 전이를 덮고, 집중 gate에서 접촉이
재현되지 않은 것은 최종 300회로 진행할 충분한 회귀 증거였다.

## 최종 300회 결과

모드 순서는 전체 캠페인에서 계속 회전했고, 각 맵·모드당 10회씩 총 300행을
실행했다. 모든 행은 first-attempt, run-valid, speed-valid였고 timeout/retry/OOM은
0이었다.

| 맵 | Full safe | Sector safe / 충돌 런 | Adaptive safe | 평균시간 F/S/A (s) | 최저 clearance F/S/A (m) | Adaptive effective open | slowdown trigger | payload F/S/A (Mbit/s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/10 | 10/10 / 0 | 10/10 | 60.02 / 61.30 / 61.89 | .218 / .206 / .255 | 177 | 415 | 31.95 / 8.88 / 13.29 |
| 2 | 10/10 | 10/10 / 0 | 10/10 | 57.23 / 58.09 / 57.82 | .266 / .173 / .257 | 192 | 372 | 30.63 / 8.01 / 12.70 |
| 3 | 10/10 | 10/10 / 0 | 10/10 | 65.46 / 65.78 / 67.72 | .209 / .235 / .195 | 117 | 431 | 37.56 / 9.30 / 17.69 |
| 4 | 10/10 | 10/10 / 0 | 10/10 | 68.46 / 69.66 / 76.20 | .211 / .212 / .217 | 106 | 496 | 42.09 / 11.43 / 18.33 |
| 5 | 10/10 | 10/10 / 0 | 10/10 | 68.97 / 71.58 / 76.37 | .194 / .193 / .161 | 109 | 472 | 42.59 / 11.38 / 20.11 |
| 6 | 10/10 | 10/10 / 0 | 10/10 | 72.20 / 75.19 / 76.84 | .204 / .204 / .219 | 135 | 499 | 46.48 / 14.14 / 22.96 |
| 7 | 10/10 | 10/10 / 0 | 10/10 | 77.51 / 76.66 / 78.65 | .219 / .089 / .172 | 111 | 521 | 50.14 / 16.69 / 27.67 |
| 8 | 10/10 | 10/10 / 0 | 10/10 | 73.59 / 73.42 / 81.09 | .167 / .032 / .138 | 78 | 507 | 47.81 / 13.43 / 24.26 |
| 9 | 10/10 | 9/10 / 1 | 10/10 | 85.85 / 79.00 / 95.15 | .150 / -.175 / .210 | 75 | 576 | 62.27 / 23.00 / 30.24 |
| 10 | 10/10 | 10/10 / 0 | 10/10 | 80.44 / 84.26 / 86.37 | .151 / .197 / .038 | 98 | 527 | 64.02 / 21.95 / 30.27 |

전체 평균은 다음과 같다.

| 항목 | Full | Sector | Adaptive | Adaptive의 Full 대비 변화 |
|---|---:|---:|---:|---:|
| 완주 | 100/100 | 100/100 | 100/100 | 동일 |
| safety-qualified | 100/100 | 99/100 | 100/100 | 동일 |
| 충돌 런 / event | 0 / 0 | 1 / 1 | 0 / 0 | 동일 |
| 평균 mission time | 70.97 s | 71.49 s | 75.81 s | +6.81% |
| worst source-PCD clearance | +0.150 m | -0.175 m | +0.038 m | -0.112 m |
| points/update | 29,261.9 | 14,956.3 | 24,890.6 | -14.94% |
| map update frequency | 6.311 Hz | 5.989 Hz | 4.386 Hz | -30.50% |
| processed payload | 45.55 Mbit/s | 13.82 Mbit/s | 21.75 Mbit/s | -52.25% |
| map total/update | 37.56 ms | 13.67 ms | 30.39 ms | -19.10% |
| FSM CPU | 104.7% | 84.9% | 86.2% | -17.66% |

Adaptive effective Full-view open은 총 1,198회(11.98/run)였다. 새 slowdown
trigger는 4,816회, 실제 Full frame은 4,711회, commit ACK는 4,706회였다.
Trigger와 frame의 105회 차이는 mission 종료 뒤 다음 cloud가 오기 전에 끝난
one-shot이다. Frame과 ACK의 5회 차이는 seed3 run7/run10, seed4 run2, seed7
run3, seed10 run10의 마지막 frame이 통계 종료 시점에 pending이었던 경우다.
다섯 행 모두 완주·충돌 0이고 supersede는 0이었다. 이는 mission-end right
censoring으로 기록하며, runtime 중 ACK loss로 해석하지 않는다.

맵 10 Adaptive run2는 +0.038 m로 가장 가까웠다. 57.278초, waypoint 3 부근,
속도 0.063 m/s에서 center distance 0.237642 m였다. 접촉은 아니지만 다음
최적화에서 안전 margin을 늘릴 때 가장 먼저 재검증할 한계 사례다.

## 계산량과 대역폭 경계

Adaptive는 Full 대비 평균 points/update 14.94%, map Hz 30.50%, processed
payload 52.25%, map total/update 19.10%, FSM CPU 17.66%를 줄였다. 평균 mission
time은 6.81% 늘었다. 따라서 최종 후보는 안전 회복과 계산/전송량 절감을 같이
달성했지만 시간 penalty까지 제거한 것은 아니다.

`map_payload_mbps`는 ROG-Map update에 실제 투입된 `PointCloud2.data` 기반
processed application payload다. DDS/RTPS header, retransmission, NIC 또는
무선 링크의 wire bandwidth가 아니다.

## 통계와 주장 경계

Safety-qualified completion의 matched map/run discordance는 Full 대 Sector
1:0, Sector 대 Adaptive 0:1이다. 실제 exact two-sided McNemar는 두 비교 모두
`p=1.0`이고 Full 대 Adaptive도 zero discordance로 `p=1.0`이다. Sector 열화를
방향성 관측으로 보고할 수는 있지만 n=100에서 통계적으로 확정된 차이라고
주장하지 않는다.

Wilson 95% 구간은 Full/Adaptive 100/100이 96.30--100.00%, Sector 99/100이
94.55--99.82%다. 관측 100%를 population-level 100%로 확대하지 않는다.

## 인프라와 재현 경계

캠페인 전 활성 ROS 프로세스가 없는 상태에서 10분 이상 된 FastDDS 임시 파일
9,345개만 지웠다. `/dev/shm`은 2.5 GiB에서 6.6 MiB로 줄고 host available
memory는 약 9 GiB로 회복됐다.

최종 캠페인은 retry 0, attempt>1 0, `oom_kill_delta=0`, memory PSI avg10 0이었다.
최대 FSM RSS는 3,270.30 MiB, 최대 cgroup memory/swap은 6,652.22/247.02 MiB,
최소 host available memory는 4,576.53 MiB였다. Host swap peak는 캠페인 전부터
사용 중이던 1,586.67 MiB였지만 후반 OOM이나 infrastructure retry가 재발하지
않았다.

## 명령과 산출물

```bash
python3 scripts/native_campaign/native_campaign.py \
  --maps seed1 seed2 seed3 seed4 seed5 seed6 seed7 seed8 seed9 seed10 \
  --modes full sector adaptive --runs 10 --rotate-modes \
  --seedmap-full-super-config static_seedmaps_guard_viability_tight_v7.yaml \
  --seedmap-filtered-super-config static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml \
  --seedmap-static-pcd --loop-timeout 180 \
  --filter-profile strict-burst --filter-backend cpp \
  --filtered-reliable-map-link \
  --adaptive-slowdown-full-refresh-v 1.5 \
  --adaptive-slowdown-full-refresh-rearm-v 3.0
```

- 접촉 context가 포함된 중단 baseline:
  `results/map9_standard_minctx_n10_raw_20260829.csv`
- 맵 9 후보 집중 n=10:
  `results/map9_slowdown_refresh_n10_raw_20260829.csv`
- 최종 raw 300행:
  `results/final_slowdown_refresh_3mode_seed1_10_n10_raw_20260829.csv`
- 맵별/전체 요약:
  `results/final_slowdown_refresh_3mode_seed1_10_n10_summary_20260829.csv`

Raw-cloud CIRI는 default false/non-authoritative다. `obs_skip_num` no-op,
NaN/clearance-penalty 결함, BackupTrajOpt coverage gap,
`DRONE_R=robot_r` 지표 한계도 이번 변경 범위 밖이며 그대로 남아 있다.
