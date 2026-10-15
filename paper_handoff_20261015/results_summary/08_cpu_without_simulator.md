# 시뮬레이터 포함 CPU와 계측 자율주행 함수 CPU

최종 실험의 CPU 결과는 두 측정 범위를 함께 제공한다. 첫째는 시뮬레이터·프런트엔드·플래너·미션과 실행 보조 프로세스를 포함한 실험 cgroup CPU다. 둘째는 같은 실험의 원래 로그에서 얻은, 시뮬레이터 콜백을 제외한 계측 자율주행 함수 CPU 소계다. 후자는 전체 자율주행 CPU를 완전히 분리한 값이 아니라 명시된 계측 함수의 실제 thread CPU 시간이다.

## 기존 실험 CPU

`data/02_summary_by_map.csv`, `data/03_summary_by_environment.csv`의 `cpu_cores`와 `cpu_core_s`는 기존 주 지표다. cgroup 사용 시간 증가량으로 측정하며, 관측기·배경 프로세스를 제외한다. GPU 작업은 CPU에 합산하지 않는다. 실험 CPU 측정 기간은 미션 관측 기간과 다르므로 평균 cores × 미션시간으로 누적 CPU를 역산하지 않는다.

Full의 결합 프로세스는 simulator+planner, Sector와 Adaptive는 simulator+frontend+planner를 포함한다. 따라서 `algorithm_cpu_*`나 `fsm_cpu_pct`라는 필드명만 보고 시뮬레이터를 제외한 플래너 CPU로 해석하지 않는다. 원자료의 `algorithm_cpu_excludes_simulator`는 최종 210회 모두 false다.

## 추가 함수 CPU

계측은 `CLOCK_THREAD_CPUTIME_ID`를 사용한다. inclusive CPU는 중첩 함수 시간을 포함하며 exclusive CPU는 같은 스레드의 계측 자식 시간을 뺀다. 서로 다른 단계를 합산할 때는 **exclusive 값만** 사용한다. 지도 갱신 wall-time과 같지 않다.

| Bucket | Stage selection | Interpretation |
|---|---|---|
| Functional subtotal | map_, frontend_, fsm_, guard_, planner_ prefixes after exact exclusions | Instrumented autonomy function CPU only |
| Simulator | sim_static_cloud_callback, sim_odom_callback, sim_render_callback | Instrumented simulator and sensor callbacks |
| Diagnostic and visualization | frontend_report, frontend_stats, planner_visualize_path | Measured reporting, statistics and visualization |
| Unclassified | Any other stage name | Retained separately; no function ownership assumed |

계측 렌더링 스레드가 프런트엔드 획득·전달 작업도 실행할 수 있으므로, 렌더링 스레드 전체를 빼는 방식은 사용하지 않는다. 역할별 스레드 CPU는 별도 진단 자료로 보존하며 함수 소계를 대체하지 않는다.

각 주행의 소계는 동일 보고 구간의 누적 카운터 차이에서 계산한다.

    functional_core_s = sum(exclusive_cpu_s[end] - exclusive_cpu_s[start])
    functional_mean_cores = functional_core_s / (report_end_s - report_start_s)

구간은 해당 주행의 활성 관측 시계열 안에 있는 첫·마지막 공통 CPU 프로파일 보고 시각이다. 구간 바깥의 초기·종료 보고도 raw_profile_reports.csv에 보존하지만 소계 계산에는 넣지 않는다. 카운터가 처음 나타나는 단계의 기준값 처리는 기존 분석기의 규칙을 따르고, 그 사실을 별도 필드로 표시한다. 기록되지 않은 단계는 값이 없는 것으로 남기며 0 CPU를 측정했다고 가정하지 않는다.

## 환경별 결과

| Environment | Runs/mode | Full (cores) | Active-Yaw Sector (cores) | Adaptive (cores) | Adaptive reduction (%) |
|---|---:|---:|---:|---:|---:|
| Normal1–5 | 50 | 0.495228 | 0.233385 | 0.317182 | 35.95 |
| Urban | 10 | 0.476129 | 0.217432 | 0.314620 | 33.92 |
| Forest | 10 | 0.516241 | 0.211110 | 0.310629 | 39.83 |

각 주행의 계측 함수 mean cores를 산술평균했다. 감소율은 같은 환경 Full 평균 대비 `100 × (1 − candidate_mean / full_mean)`이다. `full_baseline_reductions.csv`의 평균 비율 감소율과 짝지은 주행별 감소율 평균은 다른 통계이며 혼용하지 않는다.

`paired_absolute_difference_*`는 이름과 달리 수학적 절대값이 아니라 원래 단위에서의 **candidate − Full 부호 있는 차이**다. 음수면 대상 모드가 낮고 양수면 높다. 감소율의 양수·음수 방향과 구분한다.

| Environment | Runs/mode | Full (core-s/profile window) | Active-Yaw Sector (core-s/profile window) | Adaptive (core-s/profile window) |
|---|---:|---:|---:|---:|
| Normal1–5 | 50 | 21.482805 | 16.194296 | 14.629291 |
| Urban | 10 | 19.304903 | 15.481996 | 15.135387 |
| Forest | 10 | 27.722656 | 21.195929 | 16.804767 |

각 누적값은 해당 주행의 실제 프로파일 구간 안에서 소비한 계측 함수 CPU 소계의 주행별 평균이다. 같은 표본 수를 사용하되 전체 비행 CPU 시간으로 해석하지 않는다.

프로파일 구간은 관측 기간의 79.15~96.74%이고, 평균 포함 비율은 Full 85.69%, Sector 90.30%, Adaptive 86.74%다. 평균적으로 시작 약 4.812초와 끝 약 2.553초가 소계 구간에서 제외됐다. 개별 경계·기간·포함 비율을 run_cpu_210.csv에 보존했다.

계측 구간의 누적 함수 CPU도 함께 저장한다. 단위는 core-s/profile window이며 전체 미션당 CPU를 뜻하지 않는다. 같은 정의의 주행별 누적값을 평균할 뿐, mean cores를 전체 미션 기간에 곱하지 않는다. 앞뒤 경계에서 미완료 함수의 카운터 보고와 실제 CPU 소비 시각이 완전히 일치한다고 가정하지 않는다.

## 제공 파일

- `run_cpu_210.csv`: 기존 실험 CPU와 새 계측 함수·시뮬레이터·진단 CPU, 경계·포함 비율·출처.
- `stage_cpu_210.csv`: 주행·단계별 호출 수, inclusive/exclusive 값과 차이, 가용성·오류·기준값 처리.
- `raw_profile_reports.csv`: 원래 보고 행 88,136개 전체. 비행 구간 밖 보고도 포함.
- `thread_roles.csv`: 역할 표식 770개 전체. 표식 자체에 없는 시각을 만들어 넣지 않는다.
- `thread_role_cpu_210.csv`: 구간 안의 실제 역할·TID 대응에 의한 스레드 CPU 진단.
- `summary_by_map_21.csv`와 `summary_by_environment_9.csv`: 가용 N, 평균·중앙값·표본 SD·범위·분위수·합계.
- `full_baseline_reductions.csv`: 같은 맵·반복 번호로 짝지은 Full 비교와 그룹 평균 비율 비교.
- `result.json`, `coverage_evidence.json`, `validation.json`, `independent_validation.json`: 구조화 결과, 근거와 검증.

이 파일들은 모두 `cpu_analysis/`에 있다. 원본 stack 로그와 telemetry도 `recorded_trials/main/`에서 다시 확인할 수 있다. 본실험 210회의 추가 지표이며 별도 사전시험 30회는 이 요약에 합산하지 않는다. 사전시험의 원래 함수 CPU 보고는 별도 원자료 경로에 그대로 보존한다.

## 논문에서 사용할 명칭

> 시뮬레이터 콜백과 계측·시각화 함수를 제외한 계측 자율주행 함수의 exclusive thread CPU 소계

실행기·DDS와 계측 범위 밖 작업, 별도 미션 프로세스가 빠져 있으므로 “시뮬레이터를 완전히 제외한 전체 자율주행 CPU”라고 부르지 않는다. 기존 실험 cgroup CPU와 함께 제시할 수 있는 보조 지표이며, 원래 실험 결과를 바꾸거나 재실험한 값이 아니다.
