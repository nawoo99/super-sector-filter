# Pre-filter raw witness near-field guard 최종 검증 (2026-09-01)

## 1. 결론

실험용 pre-filter raw witness를 near-field hard gate에 연결한 뒤
Map 1~10 × Full/Sector/Adaptive × 10회, 총 300회를 완료했다.

- Full: 완주 100/100, source-static-PCD 충돌 없음 100/100
- Sector: 완주 99/100, 충돌 없음 98/100
- Adaptive: 완주 100/100, 충돌 없음 100/100
- 모든 300행은 v=7.0 m/s 허용오차를 만족했다.
- 유효 최종 행은 300개지만 Map 5 Adaptive run 1의 첫 attempt가 global OOM으로
  종료되어 자동 재시도 1회가 있었다. 최종 attempt는 안전 완주했다.

관측 표본에서는 목표한 모드 관계가 나왔다. Full과 Adaptive는 모두 완주하고
충돌하지 않았고, Sector는 Map 7에서 접촉 1회, Map 8에서 timeout 1회,
Map 10에서 접촉 1회가 있었다. 다만 100/100의 Wilson 95% 하한은 약 96.30%라
population-level 100% 또는 형식적 collision freedom을 뜻하지 않는다.

## 2. 구현

`fsm/trajectory_guard/raw_cloud/source_topic`을 추가했다. 비어 있으면 기존처럼
ROG-Map이 받는 cloud를 관찰하고, 실험 프로필은 다음처럼 동작한다.

- ROG-Map 입력: `/cloud_sector`
- near-field witness 입력: `/cloud_registered`
- witness callback: 별도 MutuallyExclusive callback group
- 누적 cloud 변환, AABB crop, KD-tree query: 기존 latest-only worker
- 비행 개입: generation, result age, cloud-sequence lag, checked-time 범위를 모두
  만족한 `OCCUPIED`만 brake

새 프로필은
`static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearfield_enforce.yaml`이다.
표준 `tight_v7`과 기존 filtered 실사용 프로필은 수정하지 않았고, raw CIRI와
passage-centering은 계속 꺼져 있다. 이 프로필 자체도 실험용이다.

## 3. 순차 게이트

### 3.1 이전 Sector Map 7 run 7 포렌식

기존 접촉은 elapsed 55.228 s, 위치
`[-18.524, -22.329, 1.593]`, 속도 3.118 m/s에서 발생했다. 정적 PCD 표면까지
0.200905 m로 평가 반경 0.20 m보다 +0.000905 m였지만 live candidate는
0.19981 m였다. 장애물 방향은 속도 기준 약 +92.2도, live candidate는
약 +70.1도로 ±60도 sector 밖이었다. Passage soft cost와 Backup logging은
있었지만 실제 횡방향 raw witness가 제어 입력에 없었다. 따라서 같은 후보를
더 세게 centering하는 문제보다 pre-filter witness 누락 문제로 분류했다.

### 3.2 Map 7 Full enforce n=20

Full의 기존 map observer 경로에서 실제 raw cloud enforce를 20회 먼저 실행했다.
20/20 완주, 충돌 0, 속도 위반 0, retry 0이었고 최저 clearance는 +0.186873 m였다.
Worker 결과는 `NO_HIT` 8,152건, brake 0건이었다. 평균/p95/최대 worker 시간은
8.367/15.314/52.291 ms, 평균 queue 지연은 0.080 ms였다. 실제 위험 hit가
재현되지 않아 이 단계는 오탐과 liveness 검증이지 예방 성공 증거는 아니다.

### 3.3 Pre-filter 연결 smoke와 Map 7·9·10 n=3

Adaptive smoke log에서
`topic=/cloud_registered source=dedicated_pre_filter_subscription`을 확인했다.
이어 27회 게이트는 세 모드 모두 9/9 완주·충돌 0, retry 0이었다.
평균시간 Full/Sector/Adaptive는 91.061/88.680/88.378 s, 최저 clearance는
+0.156/+0.212/+0.089 m였다. Sector에서 18개 `OCCUPIED` 결과가 실제 brake로
연결됐고 모두 완주했다. Full/Adaptive brake는 0이었다. 전체 worker 평균/p95/
최대는 7.319/14.398/56.538 ms였다.

## 4. 최종 n=10 맵별 결과

`완주/안전`에서 안전은 `safety_collisions == 0`을 뜻한다. 시간은 timeout을
포함한 10회 평균이다. Payload는 ROG-Map이 실제 처리한 입력만 측정한다.

| 맵 | Full 완주/안전 | Sector 완주/안전 | Adaptive 완주/안전 | 평균시간 F/S/A (s) | 최저 clearance F/S/A (m) | ROG payload F/S/A (MiB/s) | Adaptive Full-open |
|---|---:|---:|---:|---:|---:|---:|---:|
| Map 1 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 64.65/64.22/64.15 | +0.213/+0.141/+0.217 | 3.402/0.923/1.536 | 170 |
| Map 2 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 59.34/59.12/61.97 | +0.285/+0.268/+0.209 | 3.495/0.993/1.554 | 160 |
| Map 3 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 68.95/68.22/75.74 | +0.254/+0.184/+0.221 | 3.792/1.125/1.985 | 88 |
| Map 4 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 78.14/71.93/77.19 | +0.101/+0.221/+0.117 | 3.970/1.272/2.142 | 100 |
| Map 5 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 76.95/71.50/80.87 | +0.225/+0.203/+0.160 | 4.026/1.476/2.398 | 105 |
| Map 6 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 77.92/73.92/88.36 | +0.223/+0.184/+0.177 | 4.726/1.670/2.510 | 73 |
| Map 7 | 10/10 · 10/10 | 10/10 · 9/10 | 10/10 · 10/10 | 89.26/81.50/88.95 | +0.207/-0.168/+0.127 | 5.548/1.947/3.078 | 84 |
| Map 8 | 10/10 · 10/10 | 9/10 · 10/10 | 10/10 · 10/10 | 82.86/90.16/85.03 | +0.181/+0.038/+0.172 | 5.168/1.990/2.795 | 69 |
| Map 9 | 10/10 · 10/10 | 10/10 · 10/10 | 10/10 · 10/10 | 91.95/90.58/98.84 | +0.201/+0.089/+0.188 | 6.537/2.240/3.644 | 73 |
| Map 10 | 10/10 · 10/10 | 10/10 · 9/10 | 10/10 · 10/10 | 96.40/99.46/96.57 | +0.182/-0.051/+0.211 | 5.817/2.239/3.575 | 77 |

구체적인 Sector 실패는 다음 세 행이다.

- Map 7 run 10: 완주, static contact 1, clearance -0.168 m
- Map 8 run 8: waypoint 1/5, 180 s timeout, contact 0, clearance +0.038 m
- Map 10 run 4: 완주, static contact 1, clearance -0.051 m

이전 포렌식의 정확한 Map 7 Sector run 7은 이번 campaign에서 85.34 s 완주,
contact 0, clearance +0.229 m였다. 즉 개별 run 번호가 결정론적 장애물 사례를
뜻하지는 않지만, Map 7 Sector의 반복 분포에는 여전히 접촉 tail이 있다.

## 5. 전체 성능

CPU core는 cgroup의 wall-time 정규화 평균이며 1.0이 CPU 한 코어를 계속 쓴
것이다. `FSM CPU %`가 100을 넘을 수 있는 것도 다중 스레드 합계이기 때문이다.

| 모드 | 완주 | 충돌 없음 | 평균시간 (s) | 최저 clearance (m) | ROG payload (MiB/s) | FSM CPU (%) | Algorithm CPU (cores) | Algorithm core·s | End-to-end CPU (cores) | Algorithm PSS (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 100/100 | 100/100 | 78.640 | +0.101 | 4.648 | 92.876 | 0.929 | 73.338 | 1.112 | 3236.8 |
| Sector | 99/100 | 98/100 | 77.061 | -0.168 | 1.588 | 82.765 | 0.856 | 65.817 | 1.041 | 3254.4 |
| Adaptive | 100/100 | 100/100 | 81.769 | +0.117 | 2.522 | 81.571 | 0.846 | 69.608 | 1.032 | 3270.0 |

Adaptive의 Full 대비 변화는 다음과 같다.

- ROG-Map 처리 payload: -45.746%
- FSM CPU: -12.172%
- 평균 algorithm CPU core: -8.962%
- algorithm core·s: -5.086%
- 평균 end-to-end CPU core: -7.215%
- end-to-end core·s: -3.271%
- 평균 mission time: +3.979%
- algorithm peak PSS 평균: +1.028%; 메모리 절감 결과가 아니다.

Adaptive의 effective Full-open은 총 999회(9.99/run), trajectory-guard open은
546회, slowdown refresh trigger는 5,101회였다.

## 6. Near-field worker와 brake

| 맵 | Full brake | Sector brake | Adaptive brake | Adaptive trajectory-guard open | Adaptive slowdown refresh |
|---|---:|---:|---:|---:|---:|
| Map 1 | 0 | 0 | 0 | 58 | 419 |
| Map 2 | 0 | 0 | 0 | 65 | 394 |
| Map 3 | 0 | 0 | 0 | 59 | 488 |
| Map 4 | 1 | 1 | 0 | 53 | 481 |
| Map 5 | 0 | 3 | 0 | 67 | 488 |
| Map 6 | 0 | 1 | 0 | 44 | 545 |
| Map 7 | 0 | 20 | 0 | 53 | 556 |
| Map 8 | 1 | 21 | 0 | 46 | 530 |
| Map 9 | 0 | 19 | 5 | 52 | 603 |
| Map 10 | 0 | 82 | 1 | 49 | 597 |

최종 accepted logs에서 Full/Sector/Adaptive의 `OCCUPIED`와 enforce brake는
각각 2/147/6건이었다. Worker 평균/p95/최대는 각각
4.091/8.511/38.632 ms, 3.831/8.049/60.550 ms,
3.776/8.173/31.380 ms다. Full과 Adaptive는 brake를 포함해 모두 완주했다.
Sector는 많은 위험 후보를 막았지만 접촉 2회와 timeout 1회를 완전히 제거하지
못했으므로 이 guard도 형식적 안전 보장은 아니다.

## 7. 대역폭 해석 제한

표의 `map_payload_mib_s`는 ROG-Map이 처리한 cloud payload다. Adaptive는 이
경로를 Full보다 45.746% 줄였다. 그러나 이번 실험 프로필은 FSM guard가
`/cloud_registered`를 별도로 직접 구독한다. Filter도 같은 raw topic을
구독하므로 추가 DDS delivery/deserialization이 생기며, 이 raw witness traffic은
`map_payload_mib_s`에 포함되지 않는다.

따라서 이번 결과로 주장할 수 있는 것은 **ROG-Map 처리 입력과 CPU의 감소**다.
전체 sensor-to-algorithm 전송량 감소는 아직 주장할 수 없다. 다음 구현은
sector filter가 작은 360도 bounded near-field witness side-channel을 내거나,
trajectory와 witness 판정을 filter 쪽에서 결합해 FSM의 full raw 구독을 없애야
한다. 동시에 source publication, subscriber delivery, serialization byte를 각각
계측해야 한다.

## 8. OOM 재시도 1회

Map 5 Adaptive run 1 attempt 1은 53.85 s에 Linux global OOM killer가
`fsm_node`를 종료했다. Kernel 기록은 anon RSS 약 6.60 GiB였고, 직전 campaign
memory trace의 FSM PSS는 6.42 GiB, system swap은 2 GiB 포화였다. 당시 별도
호스트 Node 프로세스도 약 4.9 GiB RSS를 사용했다. Attempt 2는 79.77 s에
완주·충돌 0이었다.

이는 최종 planner row의 안전/완주 실패가 아니라 infrastructure retry지만,
인프라 안정성은 299/300이다. 한 attempt에서 planner 최적화 실패와 재계획이
몰리며 FSM 메모리가 평소 약 3.2 GiB의 두 배로 증가했고, 호스트 공존 부하와
swap 포화가 겹친 것이 근접 원인이다. 현재 증거만으로 raw worker 단독 누수나
외부 프로세스 단독 원인으로 확정하지 않는다. 후속 장시간 campaign 전에는
메모리 여유가 있는 호스트 또는 격리된 cgroup에서 재검증하고 raw window의
batch/byte 상한도 별도로 계측해야 한다.

## 9. 통계와 주장 경계

- Full/Adaptive 100/100의 Wilson 95% lower bound: 약 96.30%
- paired safety discordance는 Adaptive-safe/Sector-unsafe 2건, 반대 0건;
  exact two-sided McNemar p=0.5
- completion discordance는 Adaptive-complete/Sector-incomplete 1건, 반대 0건;
  exact two-sided p=1.0
- 관측상 목표한 방향은 맞지만 표본 100회만으로 population 100%나 통계적으로
  유의한 Adaptive 안전 우위를 주장하지 않는다.
- static PCD는 평가에만 썼고 planner 입력에는 넣지 않았다.
- `obs_skip_num` no-op, 기존 NaN 결함, clearance penalty 설계 이력,
  BackupTrajOpt coverage 이력, `DRONE_R=robot_r` 평가 반경 한계는 기존 정정
  사항대로 유지한다.

## 10. 재현 경로

최종 raw/요약은 다음과 같다.

- `results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_raw_20260901.csv`
- `results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_summary_20260901.csv`
- `results/nearfield_prefilter_raw_seed7_9_10_three_mode_n3_cgroup_raw_20260831.csv`
- `results/near_field_enforce_real_seed7_full_n20_cgroup_raw_20260831.csv`

최종 command의 핵심은 `--rotate-modes`, `--seedmap-static-pcd`,
`--cgroup-cpu-accounting`, `--filter-backend cpp`,
`--filtered-reliable-map-link`, 180 s timeout과 맵당 10회다. Forensics 원본은
로컬 `results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_20260901_forensics/`
아래에 있으며 약 299 MiB라 Git에는 넣지 않는다.
