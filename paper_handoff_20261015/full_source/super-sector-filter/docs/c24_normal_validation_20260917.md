# C24 Normal 5맵 재검증 프로토콜 및 완료 기록 (2026-09-17)

## 1. 현재 상태와 목적

이 문서는 C23의 미완료·실패를 보존한 채, 수정 후보를 별도 버전으로 고정하고
Normal 5맵 × Full/Sector/Adaptive × 모드당 5회, 총 75회를 새로 검증하기 위한 기록이다.
개별 callback 계측을 켠 ON 사전시험 15회는 OFF 본시험 75회와 분리한다.

현재 `results/c24_normal_validation_20260917/iteration01/status.json`은 COMPLETE다.
Release 빌드(2 packages, 6분19초), Python169 검사, 새 정적 DDS30/RViz5,
ON15 및 독립 OFF75를 모두 통과했다. 기준 실행 ID는18000, async-certified-recovery 후보다.
OFF는 맵별·모드별 정확히5회이며 총75/75완주·접촉0, 재시도·대체·계측오염0이다.
정적+ON+OFF 실제 실행시간은116.36분이다. 현재 비행/캠페인 프로세스는 없다.
맵별 최종표: [C24 결과](c24_normal_results_20260917.md).
앞서 수행한 두 개의 메모리 진단 probe는 별도 탐색 증거이고, 아래의 15회/75회 실적에 넣지 않는다.
관측한75회의 접촉은0이지만 모집단 안전 보장이 아니며, 과거 메모리 급증의 원인이
확정된 것도 아니다. 평균CPU35.5253%·누적CPU33.1255%감소로 최초40%목표에는 미달했다.

목표는 Full/Adaptive의 관측된 완주·접촉 결과와 측정 품질을 함께 확인하면서,
Sector와의 차이 및 실제 연산 비용을 맵별로 비교하는 것이다. Sector의 실패나 접촉은
선택적으로 지우거나 안전한 회차로 교체하지 않는다. 원본 SUPER 논문 구현 그대로가 아닌,
guard와 최적화 및 명시적 복구 후보가 적용된 SUPER 기반 구현의 결과임을 유지한다.

## 2. 이전 C23의 실패를 삭제하지 않는 이유

원본 기록: [C23 비교 기록](c23_normal_comparison_20260916.md),
`results/c23_normal_n5_comparison_20260916/`.

- 먼저 N5(seed9) ON 시험에서 Full의 실제 main FSM callback 평균이 97.5864 Hz로
  기존 98–102 Hz 조건을 통과하지 못했다. 이때 Full/Adaptive는 완주·접촉 0이었지만
  주기 조건은 별도 실패였으며, N5 ON 2회는 본시험 횟수에 포함되지 않는다.
- 이후 분리된 N1–N4 본시험은 17시도에서 중단했다. 16회 완주와 자원 보호 중단 1회가
  있었으며, 요청된 75회 중 58회는 미실행이다. 16회만을 전체 성적처럼 제시하지 않는다.
- N3(seed5) Sector run16112는 44.04초에 완주했지만 static-PCD 기준 접촉이 1회 있었다.
  이 결과는 유효한 비교 관측값이며 보존한다.
- 같은 run의 Adaptive는 메모리 증가 후 자원 보호로 중단했다. 해당 composed process의
  RSS는 약 3179 MiB에서 최대 약 7357 MiB까지 증가했고, 종료 후 host 가용 메모리가
  회복되었다. `infrastructure_failure=True`라는 분류명만으로 외부 환경 탓이라고 해석하지 않는다.
  그 회차의 접촉 결과는 확인되지 않았으므로 0으로 채우지 않는다.

중단 시점의 진행 로그·메모리·CPU 관측은 남아 있지만 당시 실행 중 stack은 확보하지 못했다.
따라서 원래 메모리 증가의 원인 함수는 아직 확정되지 않았다. C24가 통과하더라도
그 사실만으로 특정 함수가 C23 메모리 급증의 원인이었다고 소급 확정하지 않는다.

## 3. 선행 진단 probe와 새 후보의 구분

보존 위치: `results/c24_normal_validation_20260916/`.

| 진단 | 맵/모드 | 계측 | 완주 | 접촉 | 시간 (s) |
|---|---|---|---:|---:|---:|
| memory_probe01 / run17000 | N3 / Full | CPU profile OFF | 1/1 | 0 | 41.24 |
| memory_probe01 / run17000 | N3 / Sector | CPU profile OFF | 1/1 | 0 | 42.91 |
| memory_probe01 / run17000 | N3 / Adaptive | CPU profile OFF | 1/1 | 0 | 37.69 |
| memory_probe02 / run17001 | N3 / Adaptive | CPU profile ON + callback trace | 1/1 | 0 | 44.83 |

두 probe 모두 `ENDED_NO_CAPTURE`, return code 0으로 끝났고 메모리 증가 중 stack을
채집하지 못했다. 당시 진단 계획의 RSS trigger는 4096 MiB였으며, 아래 새 캠페인의
4608 MiB 중단/stack 채집 규칙과 동일한 프로토콜이라고 쓰지 않는다.
정상 종료한 이 네 비행은 C23 실패를 대체하지 않으며 새 후보의 반복 검증 결과도 아니다.
특히 probe02는 계측 조건이 다르므로 probe01과 CPU 주 비교 표본으로 합치지 않는다.

새 후보의 구분은 다음과 같다.

1. **동기 복구가 main FSM을 지연시킬 가능성에 대한 비동기 certified-recovery 후보**:
   `--async-certified-recovery`로 명시적으로 선택한다. runtime과 실행기 기본값은 OFF를 유지한다.
   검증 캠페인에서는 같은 후보를 Full/Sector/Adaptive 모두에 적용한다. 기존 replan callback에서
   복구 계산을 수행하고 main 쪽의 최신 상태·인증 확인을 거치는 설계이며, 새 주기/안전성 수치는
   빌드 후 실제 ON/OFF 증거로 확인해야 한다. 후보를 넣었다는 사실은 안전성 증명이 아니다.
2. **A* parent-chain 복원 방어**: 순환과 node 수 한계를 검사한 뒤 경로를 복사하고,
   비정상 chain은 no-path로 처리하는 구조적 방어가 추가되는 후보이다. 가능한 무한 누적 경로를
   방어하지만, 기존 실패 stack에서 그 경로가 관측된 것은 아니다. 정상 chain 결과의 보존과
   거절 경로는 단위 시험으로, 실제 비행 영향은 새 캠페인으로 각각 확인해야 한다.
3. **관측 강화**: 메모리 급증이 다시 나타나면 자원 보호 종료 전에 소유한 실행의 stack을
   채집한다. 채집으로 계측이 오염된 회차는 비용 비교에 사용하지 않는다.

각 후보 변경은 동일 버전의 source/config/binary 해시로 고정한다. C23 또는 과거 Normal의
완료 회차를 새 후보의 유효 횟수에 더하지 않는다. 변경 전 자료와 runtime 보존본도 유지한다.

## 4. 맵, 횟수와 순서

물리 맵은 기존 Normal 중 seed1/3/5/7/9를 그대로 사용한다. 새 장애물 배치나 맵 선별을
이번 검증 중에 수행하지 않는다. N1–N5는 아래 물리 맵을 뜻하며 과거 다른 번호 체계와 혼동하지 않는다.

| 표시 | 실제 config / PCD | 새 ON 사전시험 | 새 OFF 본시험 |
|---|---|---:|---:|
| N1 | seed1.yaml / seed1.pcd | 모드별 1회 = 3회 | 모드별 5회 = 15회 |
| N2 | seed3.yaml / seed3.pcd | 모드별 1회 = 3회 | 모드별 5회 = 15회 |
| N3 | seed5.yaml / seed5.pcd | 모드별 1회 = 3회 | 모드별 5회 = 15회 |
| N4 | seed7.yaml / seed7.pcd | 모드별 1회 = 3회 | 모드별 5회 = 15회 |
| N5 | seed9.yaml / seed9.pcd | 모드별 1회 = 3회 | 모드별 5회 = 15회 |
| 합계 | 5개 물리 맵 | 15회, 비용 주 결과와 분리 | 75회, 독립 본시험 |

실행 순서는 다음과 같이 사전 고정한다.

1. 맵별 새 static-PCD 전달 시험: standalone/full/adaptive × reader-first/late = 6건,
   실제 RViz late/reconnect = 1건. 총 DDS 30건 + RViz 5건이며 manifest 생성 명령 5개는
   추가 비행이나 별도 성능 시험 횟수로 세지 않는다.
2. 모든 맵의 새로운 시간 참고 파일을 만든다. 과거 자료의 시간은 문맥을 위한 참고값일 뿐
   이번 후보의 CPU control·안전성 수락 증거가 아니다.
3. ON 15회를 새로 수행하고 맵·모드·runtime이 일치하는 주기·소스·복구 증거를 고정한다.
   이전 C22/C23의 통과한 ON 회차를 가져와 신규 사전시험으로 계산하지 않는다.
4. ON 측정 조건을 통과한 뒤 독립 OFF 75회를 수행한다. 반복별 맵 순서와 모드 순서를
   순환한다. n=5에서 위치를 완벽히 균형화했다고 주장하지 않는다.
5. 모든 원자료와 실패를 남긴 채 맵별 집계한다. 자동 n20 확장·재시도·성공 회차 대체는 없다.

공통 side worker 수는 3, dispatch lease는 0.25초, event Adaptive body-heading은 ON이다.
센서·속도·map·경로 등 실제 유효 입력은 각 `plan.json` 및 해시를 기준으로 확인한다.

## 5. 사전 명시한 수락·중단 기준

- 모든 모드에서 run/resource/speed, 소스 획득, static 전달, 복구 인증, 센서·odom 및 FSM
  계측 조건을 유지한다. 잘못된 map/run/mode, 누락·중복·재시도, false/missing check는 통과시키지 않는다.
- Full/Adaptive는 ON과 OFF에서 완주와 확인된 접촉 0을 요구한다. 실패하면 원자료를 보존하고
  원인을 조사한다. 수정이 필요하면 새 iteration으로 처음부터 시작하고 기존 실패 iteration은 유지한다.
- Sector의 완주·접촉은 **ON과 OFF 모두 비교 결과**이다. 안전한 Sector 표본만 사전시험으로
  고르는 편향을 피하기 위해 `--sector-outcomes-as-metrics`를 시작 전에 명시한다.
  이는 알고리즘 수정이나 측정·주기 조건 완화가 아니다. Sector 측정/계약 오류는 여전히 중단 사유다.
  Sector가 막혀 건강한 재계획 생략/goal coalescing 기회가 없었던 것은 계측 오류와 구분한다.
  기존 strict valid/exercised 값은 보존하고, 실제 producer/receiver 설정·발행 goal의 일관성과
  관측된 모든 coalescing 기록의 연결/순서를 별도로 요구한다. 누락/손상 증거는 통과시키지 않는다.
  이 분리는 명시적 Sector 비교 옵션에만 적용하며 Full/Adaptive 및 기본 strict 정책은 그대로다.
- `--mission-time-as-metric`으로 시간과 Full 대비 시간비를 계속 보고하되, 과거 Adaptive/Full
  시간비 1.10 이하 조건을 이번 비교의 수락 gate로 사용하지 않는다. 기존 시간 실패 기록을
  뒤집거나 지우지 않는다.
- 평균 CPU 30%/40% 같은 절감률은 결과로 보고하며 본 캠페인의 회차 선택 기준으로 사용하지 않는다.
  최초의 40% 목표를 달성했다고 소급 표현하지 않는다.
- 하위 실행기는 세 모드를 하나의 triplet으로 수행한다. 측정·소스 오류는 하위 실행기에서
  즉시 중단하지만, Full/Adaptive 결과 실패에 대한 상위 실행기의 중단 경계는 해당 triplet 종료이다.
  따라서 결과 실패 후 같은 triplet에서 최대 두 번의 추가 시뮬레이션이 실행될 수 있으며,
  그것도 보존한다. 해당 이후 triplet이나 새로운 반복으로 확장하지 않는다.

## 6. 메모리 급증 stack 채집과 비용 무효화

새 실행기의 규칙은 다음과 같다.

- 1초마다 현재 실행기가 생성한 child의 실제 후손을 읽기 전용으로 확인한다.
  실행 파일/argv 이름이 정확히 `perfect_drone_full_node` 또는 `perfect_drone_adaptive_node`인
  프로세스만 대상으로 하며, 전역 이름 검색으로 다른 실험이나 사용자 프로그램을 중단하지 않는다.
- RSS가 **4608 MiB 초과**이면 PID와 생성 시각을 재확인한다. 임계값을 건드려 완료 회차를
  만드는 방식으로 운용하지 않는다.
- ptrace 전에 해당 triplet 폴더에 `diagnostic_contamination.json`을 기록한다.
  schema는 `c24-diagnostic-contamination-v1`, `contaminated=true`,
  `cpu_performance_valid=false`, 원인은 `memory_runaway_stack_capture`이다.
- gdb의 `thread apply all bt 24`를 한 번만 시도하고 timeout은 20초로 제한한다.
  debugger 부재·권한 오류·PID 종료·timeout도 진단 결과에 남긴다.
- 이후 소유한 child process group에 SIGINT로 정리를 요청하고, 필요한 경우 한정된 대기와
  종료 절차를 거쳐 캠페인을 중단한다. 실패 회차를 자동 재실행하지 않는다.
- ptrace는 실행을 일시 정지시키므로 해당 triplet의 비교용 CPU/시간/성능 수치는 N/A 처리한다.
  **시도 수와 확인된 완주·접촉 결과는 남긴다.** 원본 CSV/log는 수정하지 않는다.
  실패나 미확인 접촉을 없애거나 0으로 채워 성적을 올리지 않는다.

4608 MiB 방어가 작동했다는 사실은 원래 C23 급증의 원인을 알아냈다는 뜻이 아니다.
실제 stack, 증가 구간과 코드 경로가 연결되는 증거가 확보되어야 원인 결론을 갱신한다.

## 7. 연산량 비교 범위와 산출물

집계기는 `scripts/native_campaign/summarize_cpu_validation.py`, JSON schema는
`cpu-validation-comparison-v1`이다. ON은 `profiled_supplement`, OFF는
`unprofiled_primary`로 분리하며 서로 또는 이전 후보와 합산하지 않는다.

| 구분 | 기록·비교 항목 | 해석 한계 |
|---|---|---|
| 임무·안전 | 완주/시도, 유효 횟수, 접촉/미확인, 시간, 경로 길이, static clearance, 속도 | 유한 시뮬레이션 관측; 모집단 100% 보장 아님 |
| 실험 CPU | 평균 사용 코어, 전체 CPU 용량 기준 %, 측정 구간 누적 core-s, 1초 표본 p95/max | simulator+frontend/planner+mission+launcher 포함, 외부 observer 제외 |
| host CPU | 주행 중 컴퓨터 전체 %, 주행 전 baseline %, 논리 CPU별 관측 | 배경 포함; baseline 차감으로 알고리즘 비용의 인과적 귀속 불가 |
| 메모리·자원 | RSS/PSS/swap 표본 최대, host 가용 메모리, PSI, resource guard | 연속 최대가 아닌 표본 최대; RSS 합은 공유 페이지 중복 가능 |
| GPU | 장치 사용률·메모리 사용·메모리 activity·전력 표본 | 장치 전체/배경 포함; planner 귀속이나 실험 에너지 절감 증거 아님 |
| 맵 | total/raycast/update/inflation 경과시간, p95/max, 처리 프레임·포인트 | wall time이며 CPU time 아님; 중첩 구간을 더하지 않음 |
| 소스·payload | 관측 프레임 readback pixel·conversion ray·생성 point·bytes, 센서/맵/planner 유입량 | 명시된 logical edge; 물리 NIC/PCIe/메모리 대역폭 아님 |
| 주파수·간격 | source Hz, 수신 odom/command Hz·간격, trajectory commit Hz | 수신 지연과 의도적 command hold는 callback 자체 지연과 구분 |
| 복구·전환 | 실제 Sector→Full/Full→Sector, event cycle, map ACK·경로 인증 완료/미완료 | 초기 복구도 포함; 전환 1회를 회피한 충돌 1회로 세지 않음 |
| ON 단계별 CPU | callback/맵/검색/최적화 등 exclusive CPU·calls·Hz·CPU ms/call | 별도 profile 구간; inclusive 단계 중복 합산 금지, OFF 성적으로 대체 금지 |

이 호스트의 비교 기준은 논리 CPU 20개이다. 실험 사용 코어가 1.0이면 전체 논리 CPU 용량
기준 5%이고, 0.5이면 2.5%이다. 이는 배경 프로그램까지 합친 컴퓨터 전체 사용률과 다른 값이다.

```text
실험 평균 사용 코어 = cgroup 누적 CPU(core-s) / cgroup 측정 구간(s)
전체 논리 CPU 용량 기준 실험 사용률(%) = 평균 사용 코어 / 20 × 100
Full 대비 상대 감소율(%) = (Full 회차평균 − 비교모드 회차평균) / Full 회차평균 × 100
```

실제 논리 CPU 수는 실행 계획에 기록된 값으로 검증한다. cgroup 측정 구간은 waypoint 주행시간보다
조금 넓으므로 누적 CPU를 주행시간으로 나눠 평균 사용률을 재계산하지 않는다.
동일 프로세스에 simulator와 planner가 합성되어 있으므로 OFF에서 **순수 autonomy-only CPU는 N/A**다.
물리 wire 대역폭, CPU 에너지와 OFF 개별 planner callback latency도 미측정이면 N/A다.

평균·표본 SD·최소/최대는 회차 단위로 계산한다. 각 회차 p95의 평균을 캠페인 전체 표본의
pooled p95라고 부르지 않는다. map 프레임/payload를 주행시간으로 나눈 기존 rate에는
시작 구간 차이가 있으므로 실제 source Hz와 구분한다. 동일 cloud 버퍼가 여러 logical edge에서
계수될 수 있어 서로 더한 값으로 실제 전송·복사량을 주장하지 않는다.

자동 결과 파일은 다음과 같다.

- `summary_ko.md`: 주요 수치의 한국어 비교 표.
- `README.md`: 전체 주요 항목·범위·별도 ON 단계별 설명.
- `run_metrics.csv`: 원래 회차 ID와 회차별 수치, 실패 포함.
- `all_metrics.csv`: 모든 수집 수치의 회차 평균/SD/범위/누락 수/Full 대비 감소율.
- `metric_inventory.csv`: 관측 가능 항목과 미측정 항목 및 범위 설명.
- `profiled_stages.csv`: ON 단계의 window/calls/CPU ms/call/exclusive cores.
- `comparison.json`: 원자료 출처·cohort·경고를 포함한 기계 판독용 결과.

`report_preflight/`와 `report_validation5/`는 별도 폴더다. 중도 중단해도 남은 원자료에서
부분 보고서를 생성하며, 누락된 예정 슬롯이나 오염된 비용을 완료·0으로 위장하지 않는다.
상세 정의는 [측정 범위 감사](cpu_metric_scope_audit_20260916.md)도 참고한다.

## 8. 맵별 완료 결과

본시험 OFF만의 관측 결과이며 ON/진단/과거 회차를 더하지 않는다.
감소율은 Full의 회차 평균 대비 Adaptive의 상대 감소율이다.

| 맵 | Full 완주/접촉 | Sector 완주/접촉 | Adaptive 완주/접촉 | A 평균CPU 감소 | A 누적CPU 감소 |
|---|---:|---:|---:|---:|---:|
| N1 / seed1 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 30.95% | 29.44% |
| N2 / seed3 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 39.09% | 39.79% |
| N3 / seed5 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 37.43% | 34.34% |
| N4 / seed7 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 35.50% | 34.44% |
| N5 / seed9 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 34.05% | 28.39% |

전체25회씩 평균CPU Full/Sector/Adaptive=0.695766910/0.419272875/0.448593329코어,
누적CPU평균=30.80633612/19.10560964/20.60157584core-s다.
전체A 감소율은 각각35.5253%/33.1255%이며 맵별 감소율의 단순평균과 구분한다.
평균시간은42.0208/43.4560/43.6700초다. Sector도모두안전완주했으므로
이 Normal 결과만으로 Adaptive의 안전우위를 주장하지 않는다.

N3의 메모리급증은 미재현했고 stack sentinel은 작동하지 않았다. 코드방어 분기의 실제
거절 발동도 없으므로 과거 메모리 원인 확정/영구해결의 증거라고 쓰지 않는다.
N5 새ON Full50.23초/main·command99.998862Hz. ON15 실제main 범위99.923137–99.999579Hz,
command99.998117–99.999579Hz다. OFF의 odometry값은 실제FSM callback측정이 아니다.
시간·전환·메모리·맵 갱신·포인트·payload·주파수 및 분산은 [전체 결과](c24_normal_results_20260917.md)와
`iteration01/report_validation5/`에서 확인한다.

## 9. 실행 및 완료 판정

실행기: `scripts/native_campaign/run_c24_normal_validation.py`.
아래는 이번에 실행한 명령이며, 실제 생성된 `plan.json`이 입력·순서·해시의 기준이다.
재실행하려면 기존 결과를 덮어쓰지 않는 새 output 경로와 구분되는 base-run을 사용한다.

```bash
cd /root/super-sector-filter
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
python3 scripts/native_campaign/run_c24_normal_validation.py \
  --output results/c24_normal_validation_20260917/iteration01 \
  --base-run 18000 \
  --async-certified-recovery
```

기존 output 경로는 덮어쓰지 않는다. 최종 완료는 새 ON 15회와 OFF 75회의 정확한 슬롯,
고정 입력, 측정/복구/주기 조건 및 Full/Adaptive 완주·접촉 조건을 확인한 뒤 판단한다.
단순히 프로세스가 종료되었거나 일부 raw CSV가 존재한다는 이유로 완료라고 쓰지 않는다.
최종 두 phase gate 모두 true이며, ON15/OFF75의 전체 수량·유효성·동결 해시 검사와
과거Normal원본 보존을 확인했다. 이 결과로 n20을 자동 확장하지 않았다. push 없음.
