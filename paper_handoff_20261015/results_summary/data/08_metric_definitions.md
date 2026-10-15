# SUPER 결과 지표 정의와 계산 기준

## 판정 지표

주행의 모든 목표 도달 여부를 C, 한 번 이상 기하학적 접촉 여부를 H라 하면 무접촉 완주 S = C(1−H), 미션 실패 F = 1−S다. 접촉과 미완주가 같은 주행에서 발생해도 F는 한 번만 센다. 미완주 2회 중 접촉 1회인 숲 Sector의 접촉률은 10%, 미션 실패율은 20%다. 무접촉 미완주를 실제 충돌로 변경하지 않는다.

원본 `success` 필드는 목표 도달 여부이며 안전 성공과 동일하지 않다. 확장 기록에서는 `goal_complete`, `contact_run`, `safe_complete`, `mission_failure`를 명시한다. `contacts`는 authoritative solid 접촉 episode 수다. 원본 raw의 다른 접촉·점군 지표와 이름만으로 서로 대체하지 않는다.

접촉은 반경 0.2 m 구체와 정적 원기둥·AABB의 교차를 수신 위치 표본에서 판정한 값이다. 접선도 포함하며 연속된 접촉 표본을 episode 하나로 센다. 샘플 기반이므로 연속 swept-volume 보장과 다르고 실제 충격·추락을 측정한 값도 아니다.

## 주행시간

- `time_s`: 미완주를 포함한 해당 주행 관측시간, s.
- `observed_time_s_mean`: 해당 그룹의 전체 주행 평균.
- `goal_time_s_mean`: 목표에 도달한 주행만의 평균. 접촉 후 도달도 포함.
- `safe_time_s_mean`: 접촉 없이 목표에 도달한 주행만의 평균.
- `_n`, `_median`, `_sd`, `_min`, `_max`: 해당 부분집합의 표본 수, 중앙값, 표본 표준편차(ddof=1), 최소·최대.

숲 Sector는 목표 도달 및 무접촉 완주 시간의 분모가 각각 8이다. 맵 1 Sector는 목표 도달 분모 10, 무접촉 완주 분모 9다. 관측 종료에 대한 총 미션시간 상한은 없지만 동일 waypoint의 기준 위치 반경 2 cm 안에서 60초 정체한 종료는 있다.

## CPU

| Field | Unit | Definition |
|---|---|---|
| `cpu_core_s` | core-s/run | 실험 cgroup v2 usage 증가량 / 1e6 |
| `cpu_cores` | cores | 누적 CPU / cgroup 측정기간 |
| `cgroup_cpu_duration_s` | s | cgroup CPU 측정기간. 미션 관측시간과 다름 |
| `experiment_host_capacity_pct` | % | 100 × 실험 CPU cores / 20 logical processors |
| `host_cpu_pct_mean` | % | 배경 부하까지 포함한 호스트 전체 사용률 |
| `baseline_host_cpu_pct_mean` | % | 사전 호스트 사용률. 주 CPU에서 차감하지 않음 |

주 CPU 범위는 simulator+frontend+planner+mission 및 실행 보조 프로세스이며 관측기와 배경 프로세스를 제외한다. GPU LiDAR 렌더링의 GPU 시간·전력은 CPU 값에 합산되지 않는다. 평균 CPU × 미션 시간으로 누적 CPU를 역산하지 않는다.

`algorithm_cpu_*` 및 `fsm_cpu_pct`는 원본 기록의 조합별 진단 지표다. 구성 프로세스가 모드에 따라 다르므로 고립된 플래너 또는 프런트엔드 CPU라고 해석하지 않는다. `algorithm_cpu_scope`, `end_to_end_cpu_scope`를 원래대로 보존했다. CPU `_p95_1s`, `_max_1s`는 이름과 달리 실제 샘플 간격이 항상 정확히 1초는 아닌 구간 평균 표본의 통계다.

`filter_frontend_compute_core_equivalent`는 측정한 프런트엔드 경과시간 합 / 미션 관측시간의 파생 비율이다. 고립된 프런트엔드 스레드 CPU 실측값이 아니며 주 CPU에 더하지 않는다.

## 입력량과 지도 처리

| Field | Unit | Definition |
|---|---|---|
| `input_mib_run` | MiB/run | 지도 입력 application payload 합 / 2^20 |
| `input_mib_s` | MiB/s | 해당 주행 payload / 관측시간 |
| `map_ms` | ms/frame | 유효 perf 구간의 Total 프레임 평균 × 1000 |
| `mapping_frames` | frames/run | 해당 유효 perf 구간의 실제 프레임 수 |
| `map_frames_s` | frames/s | 실제 처리 프레임 수 / 관측시간 |
| `mapping_elapsed_s` | s/run | 해당 주행의 유효 perf 구간에서 sum(Total) |
| `mapping_points_total` | points/run | 같은 구간의 PointCloudNumber 합 |
| `mapping_points_mean` | points/frame | PointCloudNumber 프레임 평균 |
| `mapping_points_s` | points/s | 입력 포인트 합 / 관측시간 |

누적 지도 처리시간의 정확한 계산식은 다음과 같다.

    mapping_elapsed_s = sum(Total[k])
                      = map_ms × mapping_frames / 1000

이 곱은 각 주행의 동일 구간 안에서만 사용한다. 그룹의 평균 map_ms × 그룹의 평균 프레임 수는 각 주행 누적값의 평균과 같지 않을 수 있다. 명목 센서 10 Hz × 주행시간으로 실제 처리 프레임 수를 대체하지 않는다.

`Total`은 `updateProbMap` 내부에서 시작하고 정지하는 경과시간이다. 이후의 선택적 ESDF·초기 unknown clearing과 외부 transaction·snapshot 작업은 이 타이머에 포함되지 않는다. 따라서 누적값은 기록된 지도 업데이트 Total 시간이지 전체 지도 처리 서브시스템의 CPU 시간이나 전체 파이프라인 시간이 아니다.

`mapping_raycast_elapsed_s`, `mapping_cache_update_elapsed_s`, `mapping_inflation_elapsed_s`는 각각 기록된 단계 경과시간의 합이다. Inflation은 다른 단계와 중첩되므로 Raycast + Update_cache + Inflation을 Total 대신 사용하지 않는다. 모든 값은 CPU core-s가 아닌 경과시간이다.

입력량은 지도 처리로 전달된 PointCloud2 application payload다. 실제 네트워크 wire bandwidth, 물리 LiDAR 전력, 센서 하드웨어 데이터량이나 프로세스 resident memory가 아니다.

## 메모리와 주파수

`end_to_end_peak_rss_mib`, `end_to_end_peak_pss_mib`, `end_to_end_peak_swap_mib`는 실험 프로세스 합계의 샘플링 peak다. 메모리 표본은 약 10초 간격과 경계 시점에 취득되므로 실제 순간 최대 메모리를 보장하지 않는다. 그룹의 peak 평균은 각 주행의 sampled peak를 평균한 값이다.

`system_*`, 메모리 PSI, `cgroup_peak_memory_mib`, `cgroup_peak_swap_mib` 등은 호스트·루트 cgroup 진단일 수 있다. 이를 실험 전용 메모리라고 부르지 않는다. 이들 필드는 전체 raw 자료에 유지한다.

`trajectory_commit_hz`는 (고유 커밋 세대 수 − 1) / 첫 커밋과 마지막 커밋 시각 사이의 기간이다. 모든 계획 시도나 플래너 루프의 주파수가 아니다. `sensor_hz`는 센서 실행 설정의 명목 주파수이며 실제 입력·발행 Hz 및 지도 처리 frames/s와 구분한다. Full에서 프런트엔드 필드가 비어 있으면 0 Hz로 대체하지 않는다.

## 환경 조건

맵의 최소 표면 간격은 모든 장애물 쌍의 표면 간격 중 최솟값이다. 최근접 표면 간격 평균은 장애물마다 가장 가까운 다른 장애물까지의 표면 간격 하나를 구해 평균한 값이며, 상호 최근접 쌍은 양쪽 끝점에서 각각 집계될 수 있다. 어느 값도 모든 실제 통로의 폭이나 기체 통과 가능성을 뜻하지 않는다.

맵 1~5는 장애물 수와 크기, 미션을 유지한 배치별 비교다. 맵 5 R2는 개발 중 접촉을 확인한 뒤 원기둥 하나를 재배치한 수정본이며 무수정 독립 시험 맵이라고 설명하지 않는다. 도심지와 숲은 장애물 높이와 미션도 달라 순수한 배치 효과만을 분리한 ablation이 아니다. 그림의 점선은 웨이포인트 순서이지 실제 실행 경로가 아니다.

## Adaptive 전환과 이벤트 지연

`full_transitions`는 본실험 Adaptive의 실제 Full 전환 주기 수다. 본실험 합계 509, 별도 숲 사전시험 합계 109를 분리한다. 주기별 원본 감사는 frame match, map ACK, path ready, Sector return을 확인했다. 이벤트 확인을 실제 위험 탐지율 또는 recall로 해석하지 않는다.

ACK latency는 각 이벤트 종류를 따로 보고한다. 대응 ACK count가 0인 주행의 저장된 0초 지연은 즉시 응답이 아니라 이벤트 없음이다. 확장 지표와 보조 요약에서는 이러한 지연을 결측 처리하되 전체 raw CSV에는 원본 0을 그대로 보존한다. 그룹의 지연 평균은 해당 이벤트가 기록된 주행별 평균의 평균이며 이벤트 수 가중 평균으로 바꾸지 않는다.

## 평균과 감소율

모든 주 처리 비용은 미완주와 접촉을 포함한 전체 주행의 산술평균이다. Normal1–5는 50회/모드, Urban과 Forest는 10회/모드다. 별도 gate는 합산하지 않는다. 보조 통계는 각 필드의 `n_available`, `n_missing`을 함께 제공하며 기록이 없는 선택적 항목을 0으로 채우지 않는다.

    reduction_pct = 100 × (1 − candidate_mean / full_mean)

같은 환경의 Full 평균이 기준이다. 양수는 감소, 음수는 증가다. 소수점 반올림 전 값으로 계산한다. 주 처리 시간이 줄었다는 이유로 전체 CPU가 같은 비율로 줄었다고 설명하지 않는다. 실패 비행은 비용 평균에 포함하지만 성공 비행과 같은 수행 성능을 보장하지 않으므로 판정 지표를 함께 보고한다.
