# G1–G5 새 맵 수동 실행: 3모드 × 맵당5회 (2026-09-18)

사용자가 직접 아래 명령을 실행하는 별도 캠페인이다. 실행기 준비 및 오프라인
검사는 실제 시뮬레이션 결과가 아니다. 기존 Normal/C25 결과와 합산하지 않는다.
planner, 알고리즘, 센서 정책, 실행 바이너리 및 이전 실험 자료는 변경하지 않는다.

## 한 번에 실행

현재 선택한 **끝까지 실행·실패 보존 모드**는 다음 명령이다.

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh --continue-after-failure
```

맵 5(G5)만 각 모드5회 실행할 때는 다음 명령을 사용한다.

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh \
  --maps gapfree_d1_m05 \
  --continue-after-failure
```

이 선택 실행은 현재 source·정책으로 맵5 profiler-ON 예비3회를 새로 만든 뒤,
그 참조와 해시가 일치하는 profiler-OFF 본시험15회(3모드×5회)를 수행한다. 과거
예비시험 폴더를 재사용하지 않는다. 예비3회는 callback/실행 건전성 확인용이며
본시험 완주율·접촉률·연산량 표본 수에는 포함하지 않는다. 예상 시간은 약
25–40분이며 timeout과 실패 회차에 따라 늘어날 수 있다.

이 옵션은 접촉, 미완주, 로그/계측 누락, 속도·자원 검사 실패, child 프로세스
오류를 성공으로 바꾸지 않는다. 해당 회차를 실패/무효/N/A로 저장한 뒤 다음 예정
회차를 계속한다. source·map·동결 evidence hash가 실행 중 바뀌거나 사용자가
Ctrl+C/SIGTERM을 보내는 경우에는 계속하지 않는다. RSS guard도 비활성화하지
않으며, runaway 회차를 중단·오염 표기한 다음 다음 회차로 넘어간다.

기존 fail-closed 실행은 다음과 같다.

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh
```

ROS Humble와 현재 workspace 환경을 자동으로 source한다. 기존 시뮬레이터와
별도 캠페인은 먼저 정상 종료하고, 충분한 디스크 공간을 확보한다. 실행 터미널은
종료될 때까지 유지한다. CPU/GPU 비교를 위해 무거운 별도 작업을 피한다.
다른 실험의 프로세스를 임의로 종료하거나 결과를 삭제하지 않는다.

기본 저장 위치는 `results/gapfree_n5_YYYYMMDD_HHMMSS_PID/`이며 시작할 때 절대
경로를 출력한다. 기존 폴더 덮어쓰기 및 이어쓰기/자동재시도는 거절한다. 각 child는
독립 `/tmp/gapfree_n5_*` 경로를 사용하므로 같은 명령을 다시 실행해도 이전 실행의
동일 run 번호 파일과 충돌하지 않는다. 결과의 실험 식별자는 캠페인 폴더+맵+run+모드다.
임시 원본 파일도 자동 삭제하지 않는다.

비행 없이 환경·동결 파일·실행 계획만 확인하려면:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh --dry-run
```

맵5 선택 계획만 확인하려면 위 명령에 `--maps gapfree_d1_m05`를 추가한다.

중단된 결과의 표만 다시 만들려면(비행 미실행):

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_gapfree_n5.sh --report /root/super-sector-filter/results/실제_결과폴더
```

## 고정 조건과 실행 순서

| 항목 | 설정 |
|---|---|
| 맵 | G1–G5 = gapfree_d1_m01..05 |
| 형상 | 맵당 원기둥410개, 지름1m, 높이3m, 64×64m |
| 배치 | 비겹침만 강제; 최소 표면 간격1m 조건 없음 |
| 맵 확인 | 기존 생성 manifest SHA256 및40개 asset hash 확인 |
| 경로/속도 | 기존 loop24 및 기존 v7 프로파일 유지 |
| 모드 | Full, Fixed Sector, Adaptive |
| 후보 | C25에서 동결한 C24 async-certified-recovery 후보·공통3 worker·0.25s dispatch lease |
| 본시험 | 계측 profiler OFF, 각 맵/모드5회, 총75회 |
| 사전주행 | profiler ON, 각 맵/모드1회, 총15회; 본시험 통계와 분리 |
| 전달 사전검사 | 신규 맵별 DDS6조건+실제 RViz1조건, 총35건 및 맵별5개 acceptance 생성 |
| 실행 순서 | 회차마다 맵 순환, 맵/회차별3모드 순열 순환 |

새 맵에는 과거 정상 주행 시간 참조를 만들거나 빌려 쓰지 않는다. 주행 시간은
비교 지표로 보존하며 과거 +10% 제한은 적용하지 않는다. 기존 source/복구/주기/
속도/자원/계측 검사는 유지한다. 신규 맵 ON15의 실제 callback 검사를 통과한
동일 맵·정책만 본시험의 대응 OFF15회에 연결한다. 기존 Normal ON 결과 재사용 없음.
기존 profiler/CPU40 목표를 만족하는 회차만 골라 채택하지 않는다.

예상은 **약2–5시간**이나 신규 맵 비행 시간은 아직 모른다. 기존 Normal의 동일
규모 C24는 약116분이었다. 이 실행은 추가 원기둥 관측기를 사용하고, 회차별 최대
비행180초 및 초기화/사전검사 시간이 있으므로 timeout이 많으면5시간 이상 걸릴
수 있다. 기본 실행은 오류가 발생하면 아래 기준대로 일찍 중단한다. 선택한
`--continue-after-failure` 실행은 오류를 보존하고 다음 회차를 계속한다. 사전15회를 포함하면
실제 비행 계획은90회이며, 사용자가 요청한 주 비교 표의 분모는75회다.

## 저장 자료

| 파일/폴더 | 내용 |
|---|---|
| `summary_by_map.md`, `summary_by_map.csv` | G1–G5×3모드 수행 수/목표5, 완주 수·율, 접촉 주행·episode 수, 미확인 수, 시간, CPU, 논리 입력량, 맵 처리시간, Full 대비 감소율 |
| `report_test5/summary_ko.md` | 본시험 모드별 전체 지표 비교 및 지표 한계 |
| `report_test5/all_metrics.csv`, `comparison.json` | 수집한 수치의 평균·표준편차·분위수·유효 표본 수·Full 대비 감소율 |
| `report_preflight/` | ON15만의 프로파일 및 callback/스레드 CPU 진단; OFF 통계와 합산 금지 |
| `test5/<map>/rNN_runNNNNN/raw.csv` | 각 모드 원본 행; 실패/접촉 회차도 보존 |
| 각 triplet `*_summary.json`, `telemetry.jsonl`, `artifacts/` | CPU/GPU/메모리/주파수/소스 전환/복구 검증 및 원본 로그 |
| `artifacts/*.cylinder_audit.json`, `*.odometry.csv` | 새 맵의 기하학적 접촉 판정과 수신 odometry 전량, SHA256 연결 |
| `status.json`, `controller.log`, 단계별 `*.log`, `plan.json` | 현재 단계·중단 이유·실행 명령·동결 조건 |
| `admission.json`, `frozen_inputs_and_evidence.json` | 이전 실험 보존 및 신규 소스/맵/완료 자료 해시 |

실험 전체 CPU는 **실험 cgroup(시뮬레이터 포함)**의 평균 cores 및 측정 구간 누적
core-s가 주 지표다. 1core는 논리 CPU1개의100% 기준이며, 전체 컴퓨터 용량 기준
백분율은 논리 CPU수로 나눈 별도 지표다. observer는 실험 cgroup 밖에서 기록한다.
composed process의 CPU를 planner 단독이라고 부르지 않는다. GPU는 장치 전체
관측치이며, core-s는 에너지(J)가 아니다. 맵/소스 payload는 해당 데이터 경계의
논리량으로 물리 NIC 대역폭이 아니고, 미측정 항목은 N/A로 남긴다.
실제 callback 빈도는 ON 프로파일에서만, OFF에서는 수신 간격과 구분하여 기록한다.
adaptive 인증 완료 cycle 수와 실제 관측된 소스 전환 횟수도 서로 구분한다.

## 새 맵 접촉 판정

PCD와 동일한 원기둥410개의 중심/반지름 CSV, z범위[0,3] 및 기체 구 반지름0.2m를
사용한다. 유한 높이 원기둥과 기체 구 사이의 거리를 수신 odometry마다 계산한다.
접촉 상태 진입부터 이탈까지의 연속 구간을 episode1회로 세며, 여러 원기둥에 동시에
닿아도 같은 접촉 구간은1회다. 별도로 접촉한 주행 수/접촉 sample 수/최소 여유를 저장한다.
이 관측기는 판단/제동/경로에 정보를 전달하지 않는다.

**수신한 pose 표본 기준**이며, 표본 사이 연속 swept-volume 충돌 증명은 아니다.
전체 수신 pose와 timestamp/수신간격/최대 pose step을 기록한다. 기록 미완료·누락·
형상 hash 불일치는 접촉0으로 간주하지 않는다. JSON의 `completion`은 **관측 파일
정상 종료**를 뜻하며 미션 완주는 raw/summary의 `success`로 별도 판단한다.

기존 sampled-PCD 검사와 raw의 `safety_collisions`도 수정 없이 유지한다. 기존
관측기는 유한거리 nearest query가 None인 이탈 구간에서 접촉 플래그를 reset하지
않을 수 있어 재진입 횟수를 과소 집계할 수 있다. 따라서 새 주 표의 **횟수**는
독립 analytic episode를 사용하고, legacy 보고서의 PCD 횟수와 혼합하지 않는다.
Full/Adaptive의 기존 PCD any-contact gate도 그대로 유지한다.

## 중단·보존 원칙

`--continue-after-failure`가 없을 때 아래 fail-closed 원칙을 적용한다.

- Full/Adaptive 미완주 또는 접촉: **현재3모드 묶음 종료 후 중단**. 실패 뒤 최대2개
  모드의 시뮬레이션이 더 실행될 수 있다. 안전0/100% 달성으로 간주하지 않는다.
- Sector 미완주/접촉: 비교 결과로 기록하고 계속한다. 단 계측/소스/복구/자원 문제는
  어느 모드에서든 중단한다. 조용히 실패 회차를 삭제하거나 대체하지 않는다.
- profiler callback/수신주기·source/Full ACK/경로 복구·속도·자원 검사 실패: 중단.
  owned composed RSS>4608MiB이면 오염 표기 후 제한20초 stack 수집, 관련 CPU/시간은
  비교 지표에서 제외(N/A)하되 시도/관측 결과는 보존한다.
- Ctrl+C도 부분 결과와 로그를 보존한다. `--report`는 재집계일 뿐 재시험하지 않는다.
- 모든75회가 검증되고 보고서까지 저장되어야 `status.json`이 `COMPLETE`다.
  `DRY_RUN_ONLY`/`STOPPED_FOR_DIAGNOSIS`를 완료로 해석하지 않는다.
- 요약표와 상세표 모두 raw 품질·재시도/인프라 오류·측정기간·오염 여부로 비용
  유효성을 판정한다. 부적격 비용은 N/A와 n_missing으로 남기며 시도/안전 관측은
  보존한다. 실패해서 빨리 종료한 회차를 완주 대비 CPU 절감으로 해석하지 않는다.
- 추가 runtime 튜닝, 실패 교체, n20 확대, 자동 GitHub push는 하지 않는다.

`--continue-after-failure`에서는 위 실패도 다음 회차 실행을 막지 않는다. 다만
결과의 엄격한 `valid` 값과 원래 실패 사유는 그대로 유지한다. 하나라도 실패나
보고서 누락이 있으면 최종 상태는 `COMPLETE_WITH_RETAINED_FAILURES`이며, 이는
성공 캠페인이 아니라 **예정한 순회를 마친 불완전 캠페인**이라는 뜻이다.
실제 생성되지 않은 raw 행은 실패0이나 접촉0으로 채우지 않는다.

새 파일은 runtime의 perfect_drone_sim/scripts·test에서 작성 후 대응 mirror 및
repo 편의 launcher로 복사한다. 기존 C25 동결1396파일을 검증하며 새 어댑터는
hash-pinned 기존 실행/계측 helper를 재사용한다. 2026-09-18 진단용 C++ source5개는
별도 overlay에만 빌드되었고 이 캠페인은 원본 `/root/super_ws/install` 바이너리를
계속 사용한다. 이 source 차이는 `admission.json`에 baseline/current hash와 함께
명시하며 원본 설치 바이너리 hash 불일치는 허용하지 않는다. geometry와 실행 정책은
ON/OFF 매칭 및 보고서 fingerprint에 포함한다. child별 임시 작업 폴더 경로만
보고서 정책 fingerprint에서 제외한다.

2026-09-21 선택 실행부터 `native_campaign.py`와
`benchmark_seedmap.launch.py`의 observer-ready mission-start 오케스트레이션 변경도
현재 해시로 명시·동결한다. 이는 첫 유효 odometry 관측 후 미션을 시작하기 위한
계측 순서 변경이며 planner 알고리즘 변경이 아니다. 그 밖의 과거 동결 입력 변경은
계속 fail-closed로 거부한다.
