# 프로세스 스레드 GPU와 원본 상세 기록

최종 본실험 210회와 별도 숲 사전시험 30회의 mode_summary와 원래 시계열을 함께 보존했다. 기존 raw CSV에 없는 프로세스·스레드 CPU, GPU 사용률·메모리·전력, 표본 수와 분포를 확인할 때 이 자료를 사용한다. 본실험과 사전시험의 집계는 분리한다.

## 상세 통계 파일

`measurement_details/`에 다음 자료가 있다.

| File | Contents |
|---|---|
| `process_profiles.csv` | Every process profile object from the 240 stored mode summaries; full object fields preserved |
| `thread_profiles.csv` | Every thread profile object with process/TID identity and recorded statistics |
| `run_summary_values.csv` | Lossless JSON-pointer, type and value export of all stored mode_summary objects, including empty containers and null |
| `run_resource_summary.csv` | Run-level host/GPU/observer/cgroup/resource statistics with availability and source identity |
| `resource_summary_by_map.csv` | 21 main map-mode resource summaries |
| `resource_summary_by_environment.csv` | 9 main environment-mode resource summaries |
| `resource_summary_separate_gate.csv` | 3 separate forest-gate mode summaries; not pooled with main |
| `coverage.json` and `validation.json` | Input hashes, counts, exact reconstruction and summary checks |

표본 수·유효 관측 수를 그대로 사용한다. 통계 필드가 없으면 결측이며, 값이 0인 기록과 다르다. 장치 전체 GPU 지표를 자율주행 단독 GPU 비용으로 바꾸지 않는다. 처리 단계 CPU의 분리는 `cpu_analysis/`와 `08_cpu_without_simulator.md`를 따른다.

## 원본 시계열과 로그

`recorded_trials/run_index.csv`로 원래 주행과 복사 경로를 대응시킨다. 각 폴더의 `telemetry.jsonl`에는 시점별 CPU·프로세스·스레드·GPU·cgroup 상태, 읽기 시각, 구간 길이 및 baseline/flight 등 실험 단계가 있다. 원래 기록 전체를 보존했다.

저장된 mode_summary의 host/GPU/observer/process/thread 통계는 활성 비행 구간으로 집계한 값이다. 원래 시계열에는 초기·종료 구간도 있으므로 `phase == flight`와 `campaign_active == true`를 함께 적용해야 같은 정의로 재계산할 수 있다. 일부 구간이 표시상 flight더라도 실제 비행 활성 상태가 아닌 경우를 합산하지 않는다.

스레드·프로세스 CPU의 `cpu_pct_one_core`는 한 논리 코어를 100%로 한 값이다. 호스트 전체 용량 대비 비율과 다르다. process 사용량을 합산할 때 cores는 `% / 100`이며, 한 프로세스에 들어 있는 시뮬레이터와 플래너를 프로세스 이름으로 분리할 수는 없다.

GPU 지표는 장치 전체의 사용률, 메모리와 전력이다. 배경 작업도 포함하며 GPU 커널 시간·에너지 또는 특정 실험 프로세스의 단독 소유 비용을 측정한 것은 아니다. CPU 사용 시간에 GPU 값을 더하지 않는다.

같은 원본 주행의 `*.stack.log`와 `*.attempt1.stack.log`, canonical JSON과 attempt JSON은 보존용 별명일 수 있다. 파일을 모두 보존했지만 독립적인 실행 수를 늘리는 근거로 사용하지 않는다. 원본 파일 수와 본실험 주행 수는 서로 다른 수치다.
