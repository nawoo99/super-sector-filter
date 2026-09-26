# Scenario-group results

본시험은 normal(G1–G4, G5-R2), urban, forest를 각각 집계한다. 세 그룹을 합친 평균은 만들지 않는다.
Normal은 선택된 normal 맵의 관측 회차를 합친다. 비용 평균은 유효 회차의 산술평균이며, 맵별 관측 수가 다르면 맵 균등 평균이 아니다.
각 값은 평균 ± 표본 표준편차 [n]다. 표본이 없으면 N/A, n=1의 표준편차도 N/A다. 누락 회차와 누락 지표를 0으로 채우지 않는다.
경유점 도달·접촉·실패 결과는 비용 유효 여부와 별도로 보존한다. profiler ON 예비주행은 본시험 평균에 포함하지 않는다.
Full 대비 감소율은 같은 그룹의 Full 평균을 기준으로 한다. detailed report는 report_test10/{normal,urban,forest}, report_preflight/{normal,urban,forest}에 분리한다.
summary_overall.csv는 summary_by_group.csv의 호환용 별칭이며 동일한 그룹별 행을 가진다.

- normal: G1, G4; 모드별 계획 2회
- urban: U1; 모드별 계획 1회

| 그룹 | 모드 | 기록/계획 | 경유점 도달 | 무접촉 완주 | 접촉 주행/확인 | 미확인 | 비용 유효 회차 |
|---|---|---:|---:|---:|---:|---:|---:|
| normal | full | 1/2 | 1 | 1 | 0/1 | 0 | 1 |
| normal | sector | 1/2 | 1 | 1 | 0/1 | 0 | 1 |
| normal | adaptive | 1/2 | 1 | 1 | 0/1 | 0 | 1 |
| urban | full | 0/1 | 0 | 0 | 0/0 | 0 | 0 |
| urban | sector | 0/1 | 0 | 0 | 0/0 | 0 | 0 |
| urban | adaptive | 0/1 | 0 | 0 | 0/0 | 0 | 0 |

| 그룹 | 모드 | 시간(s) | CPU(cores) | CPU(core-s/run) | 입력(MiB/s) | 입력(MiB/run) | 맵(ms/frame) | CPU 감소(%) | 입력률 감소(%) |
|---|---|---|---|---|---|---|---|---:|---:|
| normal | full | 50.24 ± N/A [n=1] | 0.759 ± N/A [n=1] | 41.14 ± N/A [n=1] | 10.525 ± N/A [n=1] | 528.80 ± N/A [n=1] | 32.06 ± N/A [n=1] | 0.00 | 0.00 |
| normal | sector | 56.59 ± N/A [n=1] | 0.450 ± N/A [n=1] | 27.15 ± N/A [n=1] | 3.380 ± N/A [n=1] | 191.28 ± N/A [n=1] | 9.41 ± N/A [n=1] | 40.69 | 67.89 |
| normal | adaptive | 46.32 ± N/A [n=1] | 0.417 ± N/A [n=1] | 21.23 ± N/A [n=1] | 3.477 ± N/A [n=1] | 161.07 ± N/A [n=1] | 11.40 ± N/A [n=1] | 45.06 | 66.96 |
| urban | full | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A | N/A |
| urban | sector | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A | N/A |
| urban | adaptive | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A ± N/A [n=0] | N/A | N/A |

맵별 기록 수와 비용 유효 수는 CSV의 recorded_runs_by_map / performance_valid_runs_by_map에 기록한다.
Full 전환 및 복구 횟수는 유효한 해당 관측값의 n·합계·평균·표준편차를 별도로 제공하며, 비용 유효성으로 관측된 사건을 지우지 않는다.
