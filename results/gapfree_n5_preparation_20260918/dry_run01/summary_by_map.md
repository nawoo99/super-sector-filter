# G1–G5 본시험 진행/결과 (모드별 목표5회)

본시험75회만 집계. ON15는 별도 report_preflight. 접촉 횟수는 정적 원기둥/기체 구 모델의 수신 odometry 표본 기준 진입 episode 수.
CPU는 실험 cgroup 전체(시뮬레이터 포함), 평균 cores 및 측정구간 core-s. 접촉/미완료 시도도 보존. 오류/오염 회차 비용은 N/A.

| 맵 | 모드 | 수행/목표 | 완주/수행 | 접촉 주행 | 접촉 횟수 | 접촉 미확인 | 시간(s) | 평균 CPU(cores) | 누적 CPU(core-s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | full | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G1 | sector | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G1 | adaptive | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G2 | full | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G2 | sector | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G2 | adaptive | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G3 | full | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G3 | sector | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G3 | adaptive | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G4 | full | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G4 | sector | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G4 | adaptive | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G5 | full | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G5 | sector | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |
| G5 | adaptive | 0/5 | 0/0 | 0/0 | N/A | 0 | N/A | N/A | N/A |

전체 지표·분포·감소율·GPU/메모리·주파수·실제 소스 전환: report_test5/summary_ko.md 및 all_metrics.csv.
아직 실행하지 않은 slot이나 raw행 생성 전 중단은 실패0이 아니다. status.json의 상태·예정/수행 횟수를 함께 확인한다.
legacy report의 safety_collisions는 기존 sampled-PCD 지표이며 이 표의 analytic contact episode와 별도다.
