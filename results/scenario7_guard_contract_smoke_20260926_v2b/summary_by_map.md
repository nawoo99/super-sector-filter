# Seven-map guard-contract-v2 results

본시험만 집계: 3개 맵 × 3모드 × 1회 = 9회. profiler ON 예비주행은 별도.
경유점 도달과 무접촉 완주를 분리한다. 접촉 미확인은 안전0회가 아니다. 접촉은 수신 pose 표본의 기체 구-고체 교차다.
CPU는 실험 cgroup(시뮬레이터 포함, 외부 관측기 제외). 입력량은 논리 payload. 맵 시간은 경과시간.
각 비용은 유효한 회차의 산술평균이며 미완주 비용도 원본에 보존한다. 세부 표본수·표준편차·감소율은 CSV 참고.

| 맵 | 모드 | 기록/목표 | 경유점 도달 | 무접촉 완주 | 접촉 주행/확인 | 미확인 | 시간(s) | CPU(cores) | CPU(core-s/run) | 입력(MiB/s) | 입력(MiB/run) | 맵(ms/frame) | Full전환 합계 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | full | 1/1 | 1 | 1 | 0/1 | 0 | 50.24 | 0.759 | 41.14 | 10.525 | 528.80 | 32.06 | N/A |
| G1 | sector | 1/1 | 1 | 1 | 0/1 | 0 | 56.59 | 0.450 | 27.15 | 3.380 | 191.28 | 9.41 | N/A |
| G1 | adaptive | 1/1 | 1 | 1 | 0/1 | 0 | 46.32 | 0.417 | 21.23 | 3.477 | 161.07 | 11.40 | 3 |
| G4 | full | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| G4 | sector | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| G4 | adaptive | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| U1 | full | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| U1 | sector | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| U1 | adaptive | 0/1 | 0 | 0 | 0/0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

Full전환은 실제 source frame의 Sector→Full 관측 edge 수이며 초기 Full 상태는 전환으로 세지 않는다.
report_test10/{normal,urban,forest}에는 그룹별 GPU/메모리/수신주파수/계측 상세를 저장한다. 그 legacy 접촉값은 sampled-PCD 보조 지표다.
summary_by_group.csv/.md는 normal·urban·forest를 분리 집계한다. summary_overall.csv도 동일한 그룹별 행의 별칭이다. 7개 맵 전체 평균은 만들지 않는다.
Normal 비용은 관측된 유효 회차의 산술평균이며 맵별 표본수가 다르면 맵 균등 평균과 다를 수 있다.
