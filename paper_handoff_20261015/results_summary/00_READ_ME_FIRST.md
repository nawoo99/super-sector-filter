# SUPER 최종 실험 결과 전체 기록과 Codex 전달 안내

이 자료는 SUPER 기반 Adaptive Sector Filtering 연구의 최종 수치, 함수별 CPU 계측, 프로세스·스레드·GPU 상세 통계와 시계열, 원본 로그, 지표 정의, 7개 환경 지도를 함께 제공한다. 결과는 2026년 10월 8일 동결한 V6 실험이며, 전체 기록 전달 자료 정리일은 2026년 10월 14일이다. 새 실험을 실행하거나 기존 판정을 변경하지 않았다.

이름이 `_all`로 끝나는 이 묶음을 최신 전달본으로 사용한다. 이전 14.5 MiB 묶음의 누락 항목을 보완했으며, 본실험 210회와 별도 사전시험 30회의 원본 기록 파일 **4,720개 전체**를 `recorded_trials/`에 보존했다. 함수별 CPU를 포함한 로그 값과 상세 JSON·JSONL 수치를 원본 CSV 686개 항목만으로 대체하지 않는다.

본실험은 맵 1~5, 도심지, 숲의 7개 맵에서 Full, Active-Yaw Sector, Adaptive를 맵·모드당 10회씩 실행한 210회다. Full과 Adaptive는 각각 70회 모두 무접촉 완주했다. Active-Yaw Sector는 목표 도달 68회, 접촉 주행 2회, 무접촉 완주 67회다.

| Mode | Runs | Goal complete | Contact runs | Contact-free complete | Mission failures |
|---|---:|---:|---:|---:|---:|
| Full | 70 | 70 | 0 | 70 | 0 |
| Active-Yaw Sector | 70 | 68 | 2 | 67 | 3 |
| Adaptive | 70 | 70 | 0 | 70 | 0 |

미션 실패는 접촉 또는 미완주의 합집합이다. 접촉 없이 미완주한 숲 Sector 1회는 실패지만 충돌로 바꾸지 않는다. 목표 도달을 무접촉 성공과 같은 뜻으로 사용하지 않는다.

## 읽는 순서

1. `00_READ_ME_FIRST.md`: 최종 결과의 범위와 파일 선택.
2. `02_implementation_clarifications.md`: 식 (4)의 적용 범위, 식 (5)의 별도 탈출 해제 조건과 실제 구현.
3. `01_final_results.md`: 전체 판정, 맵별 주행시간·연산량, 환경별 평균·감소율, Adaptive 전환 횟수.
4. `08_cpu_without_simulator.md`: 시뮬레이터 포함 실험 CPU와 시뮬레이터 콜백 제외 계측 함수 CPU 소계의 구분, 누적값과 계측 구간.
5. `data/08_metric_definitions.md`: 기존 지표 정의. sensor_hz 설명의 정정은 02 문서를 따른다.
6. `cpu_analysis/summary_by_map_21.csv`, `cpu_analysis/summary_by_environment_9.csv`와 `measurement_details/`에서 필요한 상세 통계를 선택한다. 요약에서 확인할 수 없는 값은 `recorded_trials/`의 원자료를 확인한다.

`01_final_results.md`의 기존 본실험 수치는 검증된 10월 12일 정리본과 같으며, 이번 전달본에는 원래 로그의 함수별 CPU 사후 집계를 추가했다. 날짜를 새로운 실험일로 쓰지 않는다. 구현 설명은 `02_implementation_clarifications.md`, 추가 CPU 지표는 `08_cpu_without_simulator.md`를 기준으로 한다.

## 최종 수치 파일

| File | Contents |
|---|---|
| `data/02_summary_by_map.csv` | 7 maps × 3 modes, 21 rows; outcomes, time, CPU, input, mapping, memory, frequency and transitions |
| `data/03_summary_by_environment.csv` | Normal1–5, Urban and Forest separately; 9 rows |
| `data/04_run_level_210.csv` | All 210 main runs; compact values, derived metrics and cumulative mapping time |
| `data/05_all_recorded_fields_210.csv` | All 686 original raw fields per run, plus provenance fields; unavailable entries preserved |
| `data/06_metric_availability.csv` | Availability, types and missing counts for the original fields |
| `data/07_supplementary_numeric_summary.csv` | Mean, median, sample SD, minimum, maximum and available N by map or environment |
| `data/11_map_conditions.csv` | Obstacle count, size, height, spacing, density and mission conditions |
| `data/12_failure_runs.csv` | Three main runs with contact or incomplete missions |
| `data/13_full_baseline_reductions.csv` | Environment-specific reductions relative to Full, including cumulative mapping |
| `data/14_adaptive_cycles_509.csv` | All 509 Adaptive Full recovery cycles in the main experiment |
| `data/15_overall_outcome_counts.csv` | Outcome counts for 70 runs per mode; not a pooled cost-comparison baseline |
| `data/16_result_bundle.json` | Structured summaries, outcomes, reductions and map conditions |
| `data/17_mapping_evidence.json` | Source hashes and valid frame windows for cumulative mapping calculations |
| `data/mapping_performance/` | Original per-frame mapping CSVs; use the evidence windows, not entire files indiscriminately |

표시용 반올림 값이 아니라 CSV·JSON의 반올림 전 값으로 재계산한다.

## 함수별 CPU 결과

| File | Contents |
|---|---|
| `cpu_analysis/run_cpu_210.csv` | Every main run; original experiment CPU plus instrumented functional, simulator and diagnostic CPU, exact windows and coverage |
| `cpu_analysis/stage_cpu_210.csv` | 8,190 run-stage rows; calls, inclusive/exclusive CPU, boundary counters, deltas, errors and availability |
| `cpu_analysis/raw_profile_reports.csv` | All 88,136 original periodic CPU counter records; outside-flight records retained and labeled |
| `cpu_analysis/thread_roles.csv` | All 770 original role markers, source lines and timestamps when available |
| `cpu_analysis/thread_role_cpu_210.csv` | Role-associated thread diagnostics; not interchangeable with exclusive function ownership |
| `cpu_analysis/summary_by_map_21.csv` | Mean, median, sample SD, min/max, p05/p95 and available N for each map-mode |
| `cpu_analysis/summary_by_environment_9.csv` | Same statistics with Normal1–5, Urban and Forest separate |
| `cpu_analysis/full_baseline_reductions.csv` | Mean-cores and profile-window core-s comparisons; ratios of means and paired-run statistics separated |
| `cpu_analysis/result.json` | Structured additional CPU results and exact definitions |
| `cpu_analysis/coverage_evidence.json` | Source hashes, window boundaries, scope coverage and availability |
| `cpu_analysis/validation.json` and `independent_validation.json` | Builder and independent checks of the added CPU values |

추가 CPU 값은 시뮬레이터를 제외한 완전한 자율주행 CPU 총량이 아니라, 계측된 함수의 소계다.

## 전체 기록의 저장 위치

`recorded_trials/run_index.csv`에서 본실험과 별도 사전시험의 원래 디렉터리 및 복사 위치를 확인할 수 있다. `file_index.csv`는 전체 4,720개 파일의 경로·크기·SHA256와 원본 동결 목록과의 일치를 나타낸다.

본실험 원자료는 `recorded_trials/main/<map>/rNN/<mode>/`, 별도 숲 사전시험은 `recorded_trials/separate_gate/<map>/rNN/<mode>/`에 있다. summary, mode_summary, plan, status, raw, telemetry, odometry, memory, cgroup, performance, 관측기 JSON, 접촉 감사, mission·stack 로그를 그대로 저장했다. `*.stack.log`와 `*.attempt1.stack.log`는 보존용 별명일 수 있으므로 다른 실험으로 세지 않는다.

상세 JSON과 시계열에는 프로세스·스레드 CPU, 논리 코어별 CPU, 호스트 CPU, GPU 사용률·메모리·전력, 관측기 CPU, cgroup, 실험 단계와 측정 시각이 있다. 계측 구간과 배경을 포함하는 호스트·GPU 범위를 구분한다. `measurement_details/`는 저장된 mode_summary를 검색·표 작성에 사용할 수 있게 펼친 자료다.

기록되지 않은 물리 LiDAR 전력, GPU 커널 단독 시간, 완전한 자율주행 소유 CPU, 연속 충돌 보장 등을 만들어 넣지 않는다. 실제로 기록한 최종 실험 자료를 보존하며, 플래너 실행 파일·외부 정적 PCD의 중복·무관한 과거 실험·영상 촬영 기록은 포함하지 않는다.

## 환경 지도와 그림

`data/environment_maps/`에 맵 1~4, 맵 5 R2, 도심지, 숲 및 7개 전체 비교 지도를 PNG·SVG·PDF로 넣었다. 점선은 웨이포인트 방문 순서이며 실제 주행 궤적이 아니다. 실제 기하와 미션의 경로·해시는 `map_sources.json`에 있다.

`data/figures/`에는 맵별 누적 지도 처리시간 비교 그림이 있다. 기존 판정·비용 비교와 실패 사례 그림은 `data/source_frozen/`에 보존했다. 원본 동결 자료나 그림의 내용을 수정하지 않았다.

## 집계와 해석 기준

- Normal 맵 1~5는 모드당 50회로 묶는다. 도심지와 숲은 각각 모드당 10회로 별도 평균을 낸다. 7개 맵을 섞은 비용 평균을 주 비교값으로 만들지 않는다.
- 평균 CPU는 실험 cgroup의 `cores`, 누적 CPU는 `core-s/run`이다. 호스트 전체 CPU 사용률, GPU 사용률 및 지도 처리 경과시간과 구분한다.
- 추가 함수 CPU 소계는 map/frontend/FSM/guard/planner 계측 범위의 exclusive CPU 시간만 합산한다. 측정된 시뮬레이터 콜백과 계측·시각화 함수를 제외하며, 미계측 실행기·DDS와 별도 미션 CPU는 포함하지 않는다. 이 계측 구간의 core-s를 전체 주행 누적 CPU로 바꾸지 않는다.
- GPU는 장치 전체 사용률·메모리·전력이며 배경 작업도 포함할 수 있다. 특정 자율주행 알고리즘에 귀속된 GPU 비용으로 설명하지 않는다.
- 입력 대역폭은 `MiB/s`, 실행당 입력 데이터량은 `MiB/run`이다. 실제 네트워크 wire bandwidth 또는 메모리 사용량으로 부르지 않는다.
- 지도 처리시간은 `ms/frame`, 누적 지도 처리시간은 동일 주행의 유효 프레임에 대한 `sum(Total)`, 즉 `s/run`이다. 중첩 단계 시간을 더해 Total을 대체하지 않는다.
- 감소율은 같은 환경의 Full 평균을 기준으로 `100 × (1 − candidate_mean / full_mean)`이다. 음수는 증가다.
- 센서 명목 설정은 10 Hz이지만, 원자료의 `sensor_hz`는 `(sensor_frames − 1) / sensor_span_s`로 계산한 로그 기반 소스 생성 주파수다. 복사된 `data/08_metric_definitions.md`에서 이 필드를 명목 주파수라고 부른 설명은 이 정정으로 대체한다. 측정된 지도 처리 주파수와도 구분한다.
- 비용 평균은 접촉·미완주를 포함한다. 완료 주행 시간과 무접촉 완료 주행 시간은 별도 분모를 사용한다.
- Adaptive 전환은 맵 1~5에서 각각 85, 54, 80, 69, 72회, 도심지 61회, 숲 88회이며 본실험 합계 509회다. 위험 탐지율이나 recall로 해석하지 않는다.
- 접촉 판정은 수신 위치 표본에서 기체 구체와 정적 실체의 교차다. 실제 충격·추락이나 연속 swept-volume 충돌을 측정한 것은 아니다. 관측된 100%를 모집단 보장으로 확대하지 않는다.
- 현재 비교군은 Active-Yaw Sector다. 과거 yaw 탐색이 없는 Fixed Sector 또는 다른 Adaptive의 결과와 합치지 않는다.

## 본실험에서 제외하는 자료

별도 숲 사전시험 30회는 `data/separate_gate/`와 `recorded_trials/separate_gate/`에 보존했지만 본실험 210회와 합산하지 않는다. 사전시험 Adaptive 전환 109회도 본실험 509회와 합치지 않는다. 이번 함수 CPU 요약은 본실험 210회이며, 사전시험 함수 CPU 원자료는 별도 사전시험 로그에 그대로 있다.

과거 600회 자료, 폐기한 탐색 맵과 다른 구현의 stress 실험은 이 최종 본실험의 수치가 아니다. 10월 12일 영상 촬영용 6회도 제외한다. 현행 도심지·숲을 이름만 바꾸어 통제된 blind-zone stress로 설명하지 않는다.

맵 5 R2는 개발 중 원기둥 1개를 옮긴 수정본이다. 독립적인 미튜닝 blind test라고 설명하지 않는다. 같은 맵의 반복 실행은 독립적인 새 환경을 추가한 것이 아니다. 현재 본실험에 수행하지 않은 통계 검정이나 실제 비행 실험을 만들어 넣지 않는다.

## 검증 자료와 전달 프롬프트

`04_independent_validation.json`은 전달 묶음의 복사본을 원본 동결 결과·raw 항목·프레임 로그와 다시 대조한 보고서다. 원본 패키지의 `data/release_manifest.json`과 동결본의 `data/source_frozen/freeze_manifest.json`은 변경하지 않았다. `05_package_manifest.json`은 이 새 전달 묶음의 파일 해시다.

`06_validation_summary.json`은 현재 전달 묶음의 간단한 검증 요약이며, `07_implementation_evidence.json`에는 식 (4)·(5)와 미션 정의의 코드 발췌·해시 및 실제 본실험 모드 로그가 있다. 외부 환경에서 원래 코드 경로를 열 수 없을 때도 이 발췌를 읽을 수 있다. 동결 목록에 직접 포함되지 않은 설명용 소스는 그 범위를 별도로 표시한다.

`data/build_complete.json`의 `BUILT_AWAITING_INDEPENDENT_VALIDATION`은 과거 생성 단계의 기록이다. 현재 검증 상태는 `data/release_manifest.json`의 `VALIDATED`, 새 독립 검증 보고서와 `05_package_manifest.json`을 기준으로 한다. 역사 기록을 바꾸어 검증 완료를 표현하지 않았다.

추가 원자료 전체의 검증은 `recorded_trials/recording_coverage.json`, 상세 통계와 CPU의 검증은 각 하위 폴더의 검증 보고서를 따른다. `previous_release/`의 보고서는 이전 부분 전달본의 역사 기록이며 현재 상태를 대신하지 않는다.

Codex에 보낼 문장은 `03_codex_prompt.txt`에 있다. ZIP 전체 또는 이 폴더 경로를 전달하고 해당 문장을 붙여 넣는다. 큰 원자료 때문에 읽기 비용이 높을 수 있으므로 먼저 요약·정의·추가 CPU 자료를 읽고 필요한 원자료만 확인한다. 원자료를 읽지 않은 항목을 측정 완료 또는 0으로 추정하지 않는다.
