# SUPER 최종 결과와 환경 지도 자료 안내

현재 V6 실험의 모든 주행별 기록, 맵별·환경별 요약, 주행당 누적 지도 처리시간 및 맵 1~5·도심지·숲 지도를 묶었다. 본실험은 7맵 × 3모드 × 맵·모드당 10회인 210회다. 기준 결과는 2026년 10월 8일 동결본이며, 이 묶음은 2026년 10월 12일에 기존 기록을 재정리한 자료다.

Full과 Adaptive는 각각 70/70회 무접촉 완주했다. Active-Yaw Sector는 목표 도달 68/70회, 접촉 주행 2/70회, 무접촉 완주 67/70회, 접촉 또는 미완주로 정의한 미션 실패 3/70회다. 접촉 없이 정체한 숲 주행은 미완주로 보존하며 실제 충돌로 바꾸지 않는다.

## 먼저 읽을 자료

1. `01_authoritative_result.md`: 전체 판정, 7맵별 결과, 시간, 연산량, 환경별 감소율 및 해석.
2. `02_summary_by_map.csv`: 7개 맵 × 3모드의 21개 요약 행.
3. `03_summary_by_environment.csv`: Normal1–5, Urban, Forest를 분리한 9개 요약 행.
4. `04_run_level_210.csv`: 본실험 210회 축약 기록과 누적 지도 처리시간, 보조 지표.
5. `08_metric_definitions.md`: 지표 단위, 측정 범위, 계산식, 결측값 처리.
6. `11_map_conditions.csv`와 `environment_maps/`: 실제 환경 조건, 웨이포인트 및 맵별 지도.

`01_authoritative_result.md`의 표시값은 읽기 쉽게 반올림했다. 재계산과 그래프에는 CSV 또는 `16_result_bundle.json`의 반올림하지 않은 값을 사용한다.

## 전체 기록과 상세 검증

| File or directory | Contents |
|---|---|
| `05_all_recorded_fields_210.csv` | 원본 raw CSV의 모든 항목과 값. 빈 항목도 원래대로 보존 |
| `06_metric_availability.csv` | 원본 필드별 기록 유무, 자료형, 모드별 사용 가능한 주행 수 |
| `07_supplementary_numeric_summary.csv` | 핵심 및 보조 수치의 맵별·환경별 평균, 중앙값, 표본 표준편차, 최소·최대 및 유효 표본 수 |
| `12_failure_runs.csv` | 본실험의 접촉 또는 미완주 3개 주행 |
| `13_full_baseline_reductions.csv` | Full 환경별 평균을 기준으로 한 Sector·Adaptive 감소율 |
| `14_adaptive_cycles_509.csv` | 본실험 Adaptive의 509개 전환 주기별 기록 |
| `15_overall_outcome_counts.csv` | 모드별 전체 70회 판정 및 보조 합계. 주 비용 비교는 환경별 표 사용 |
| `16_result_bundle.json` | 주요 판정, 요약, 감소율 및 맵 조건을 합친 구조화 자료 |
| `17_mapping_evidence.json` | 누적 지도 처리시간 계산에 사용한 원본·복사본 경로, 해시, 프레임 구간 |
| `mapping_performance/` | 주행별 원본 프레임 처리 CSV. 원본 그대로 복사했으며 유효 구간은 evidence에 지정 |
| `figures/cumulative_mapping_by_map.*` | 누적 지도 처리시간 맵별 비교 그림 |
| `source_frozen/` | 변경하지 않은 원본 동결 자료와 기존 결과·사례 그림·감사·코드·해시 |
| `separate_gate/` | 별도 숲 사전시험 30회의 확장 기록. 본실험에 합산하지 않음 |
| `analysis/` | 결과 생성과 독립 검증 코드 |

`10_validation.json`과 `release_manifest.json`은 이 묶음의 검증 결과와 파일 해시다. 원본 `source_frozen/freeze_manifest.json`은 10월 8일 동결 자료의 상태를 나타내며 새 묶음 때문에 변경하지 않았다.

원본 주행마다 저장된 모든 scalar CSV 값은 `05_all_recorded_fields_210.csv`에 보존했다. 실제 기록되지 않은 optimizer·별도 CPU 등 선택적 필드도 있을 수 있다. 빈 항목은 0이 아니며 지표의 이름만으로 측정 완료라고 판단하지 않는다. 모든 원시 odometry·stack 로그를 중복 복사한 것은 아니다. 기존 로그의 위치와 해시는 원본 동결 자료에 남아 있다.

## 환경 지도

- `environment_maps/map1.png` ~ `map4.png`: 일반 원기둥 맵 1~4.
- `environment_maps/map5_r2.png`: 일반 맵 5 수정본 R2.
- `environment_maps/urban.png`: 도심지.
- `environment_maps/forest.png`: 숲.
- `environment_maps/all_maps_overview.png`: 7개 맵 전체 비교.

각 지도는 PNG·SVG·PDF로 제공한다. 회색은 실제 정적 장애물, 파란 번호는 웨이포인트, 주황 별은 시작 위치다. 점선은 목표 방문 순서이며 실제 비행 궤적이나 무충돌 경로가 아니다. 전역 정적 지도와 실제 센서 관측·플래너 occupancy map도 구분한다.

## 비교 기준과 범위

Normal 맵 1~5는 모드당 50회로 묶어 평균한다. 도심지와 숲은 각각 모드당 10회로 따로 계산한다. 실패·접촉 주행도 비용 평균에는 포함하며, 목표 도달 시간과 무접촉 완주 시간은 서로 다른 분모로 표시한다.

현재 Sector는 정지 후 회전 관측을 수행하는 Active-Yaw Sector다. 방향 탐색이 없는 과거 Fixed Sector와 같은 비교군으로 설명하지 않는다. 과거 600회 자료를 이 본실험과 합산하지 않으며, 현행 도심지·숲 결과를 통제된 blind-zone stress로 이름만 바꾸지 않는다.

누적 지도 처리시간은 프레임별 ROG-Map `Total` 경과시간의 합이다. 전체 프로세스의 누적 CPU 시간이나 전체 지도 서브시스템의 CPU 시간은 아니다. 중첩되는 처리 단계의 시간을 더하지 않는다.

PerfectDrone은 이상적 궤적 추종 모델이며 충격·파손·추락을 평가하지 않는다. 접촉은 수신 위치 표본의 구체–정적 장애물 교차다. 평가한 시뮬레이션의 결과를 실제 비행 안전 보장, 모집단 100% 보장, 연속 경로 충돌 인증 또는 통계적으로 확정된 우위로 확대하지 않는다.
