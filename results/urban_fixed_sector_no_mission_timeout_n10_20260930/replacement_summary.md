# Urban Legacy Fixed Sector 무제한 재시험 — ablation only

> **비정식 결과:** 이 캠페인은 `Active-Yaw`가 꺼진 legacy body-forward
> Fixed Sector로 잘못 실행됐다. 2026-09-30 이후 기본 `Sector` 결과나 7-map
> 최종표에 사용하지 않으며, 고정 시야 ablation/실패 분석 자료로만 보존한다.
> 정식 대체 cohort는
> `results/urban_active_yaw_default_no_mission_timeout_n10_20260930/`이다.

## 감사 판정

- **PASS**: 새 Fixed Sector 10개 행, 고유 run ID 10개
- 각 비행 attempt 1회, retry 0, infrastructure failure 0
- 모든 행에서 run/resource/speed/performance/solid-audit 유효
- 플래너·알고리즘·맵은 v12와 동일하며 전체 미션 제한시간만 제거
- 비완주는 60초 연속 2 cm 이내 무이동 사건으로 종단했으며, 이는 플래너 입력을 바꾸지 않는 관측기 판정

## 도심지 결과표

| 모드 | 완주율 | 접촉 주행 | 안전 완주 | 관측시간 평균 | 완주 run 주행시간 평균 |
|---|---:|---:|---:|---:|---:|
| Full | 10/10 (100%) | 0/10 (0%) | 10/10 (100%) | 48.32 s | 48.32 s |
| Fixed Sector | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) | 76.67 s | 54.39 s |
| Adaptive | 10/10 (100%) | 0/10 (0%) | 10/10 (100%) | 51.30 s | 51.30 s |

> Fixed Sector의 전체 10회 평균 76.67초는 비행시간 평균이 아니라 완주 또는 사건 기반 stall 판정까지의 관측시간이다.

### 새 Fixed Sector 종단 구성

- 완주: 3/10
- 지속 접촉 정지: 3/10
- 비접촉 무진행 정지: 4/10

## 도심지 연산량

| 지표 | Full | Fixed Sector (새 값) | Adaptive | Sector 감소율 | Adaptive 감소율 |
|---|---:|---:|---:|---:|---:|
| mean_cpu_cores (cores) | 0.698 | 0.365 | 0.511 | 47.7% | 26.9% |
| host_capacity_pct (% of host) | 3.492 | 1.826 | 2.554 | 47.7% | 26.9% |
| total_cpu_core_s (core-s/run) | 37.023 | 27.911 | 28.627 | 24.6% | 22.7% |
| input_bandwidth_mib_s (MiB/s) | 11.638 | 3.313 | 3.358 | 71.5% | 71.1% |
| total_input_mib_run (MiB/run) | 562.314 | 246.117 | 173.131 | 56.2% | 69.2% |
| map_computation_ms_frame (ms/frame) | 27.609 | 9.107 | 11.334 | 67.0% | 58.9% |

## 교체 적용 후 전체 70회/모드 기술값

| 모드 | 완주 | 접촉 주행 | 안전 완주 |
|---|---:|---:|---:|
| Full | 70/70 | 0/70 | 70/70 |
| Fixed Sector | 60/70 | 6/70 | 60/70 |
| Adaptive | 70/70 | 0/70 | 70/70 |

## 해석 제한

- 이 표에서는 요청에 따라 기존 v12 Urban Sector를 새 무제한 cohort로 교체했다.
- Full/Adaptive는 기존 v12 run이고 Sector는 새 run이므로 세 모드가 같은 반복쌍이 아니다.
- 따라서 이 교체 표에 기존 paired McNemar p-value를 재사용하면 안 된다.
- 원본 v12 데이터와 paired 통계는 수정하지 않고 별도로 보존한다.
- 비완주 Sector의 관측시간은 주행시간 성능 비교에 사용하지 않는다.
- 결과는 이 고정 도심지 맵의 유한 반복 관측이며 population guarantee가 아니다.

## Fixed Sector 개별 실행

| run | 완주 | WP | 접촉 | 종단 | 시간(s) | 최소 clearance(m) |
|---:|---:|---:|---:|---|---:|---:|
| 94401 | O | 5/5 | 0 | mission_complete | 56.07 | 0.269 |
| 94402 | X | 0/5 | 1 | persistent_contact_stall | 64.99 | -0.050 |
| 94403 | X | 2/5 | 1 | persistent_contact_stall | 84.11 | -0.158 |
| 94404 | X | 4/5 | 0 | persistent_no_progress_stall | 106.43 | 0.398 |
| 94405 | X | 2/5 | 1 | persistent_contact_stall | 84.19 | -0.166 |
| 94406 | X | 1/5 | 0 | persistent_no_progress_stall | 79.12 | 0.352 |
| 94407 | O | 5/5 | 0 | mission_complete | 51.28 | 0.156 |
| 94408 | X | 4/5 | 0 | persistent_no_progress_stall | 106.66 | 0.132 |
| 94409 | X | 1/5 | 0 | persistent_no_progress_stall | 78.07 | 0.320 |
| 94410 | O | 5/5 | 0 | mission_complete | 55.83 | 0.246 |
