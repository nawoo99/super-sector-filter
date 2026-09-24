# G1–G5-R2 + Urban U1 + Forest F1: manual n10 campaign

## 실행

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh --continue-after-failure
```

7개 맵 × Full/Sector/Adaptive × 10회 = **본시험 210회**다. 새 실행의 profiler-ON
예비시험은 맵·모드당1회, **21회**이며 본시험 평균에 섞지 않는다. 실제 비행 계획은
231회다. DDS/RViz 정적 전달 검사는 비행 횟수에 포함하지 않는다.

기존 5개 맵도 이 명령에서 새로 실행한다. 과거 n5 결과를 n10의 일부로 가져오지 않는다.
예상 시간은 보통 **5–7시간**, timeout이나 예비검사 실패가 많으면 더 길어진다.
이는 G5-R2의 과거 예비3+본시험15회에 약26.4분 걸린 기록을 기준으로 한 추정이며,
새 도심/숲의 실제 주행 시간은 아직 측정하지 않았다.

프로그램 종료 후 기존 터미널의 프롬프트로 돌아온다. 터미널 창을 자동으로 닫지 않는다.
실행 중 터미널을 닫으면 종료될 수 있으므로 유지한다. 각 재실행은 새 결과 폴더를 만든다.
동시 캠페인은 잠금으로 거부하며 다른 시뮬레이션은 먼저 정상 종료한다.

비행 없이 210회 계획·파일·해시만 검사:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh --dry-run
```

추가 맵2개만 각각10회 실행하려면:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh \
  --maps urban_blocks_u01 forest_cluster_f01 --continue-after-failure
```

종료/중단된 폴더의 보고서만 재생성:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh \
  --report /root/super-sector-filter/results/실제_scenario7_n10_결과폴더
```

## 맵과 고정 조건

| 표시 | 실제 맵 | 구조 |
|---|---|---|
| G1–G4 | gapfree_d1_m01..04 | 기존 d1m×H3m 원기둥410개, 64×64m |
| G5 | gapfree_d1_m05r2 | 기존 수정 맵5; 원래 실패한 m05와 별개 |
| U1 | urban_blocks_u01 | 16개 직육면체 건물, 6×8m 바닥면, 높이6m |
| F1 | forest_cluster_f01 | d1m×H4m 원기둥410개, 군집270개(10×27)+배경140개 |

새 맵은 정적 PCD이며 obstacle가 비행 중 추가되거나 이동하지 않는다. U1은 규칙적
블록과 연결 도로로 시작하는 도심 모델이다. F1은 가지·수관 없는 단순화된 수간 숲이다.
새 맵 높이는 기존 가상 천장3.5m 위로 연장해 수평 우회 환경을 만든다. 이 높이 차이를
간격 효과 하나의 결과로 주장하지 않는다. 두 시나리오는 대표형 각1개이며 도심/숲
전체 환경으로 일반화하는 증거는 아니다.

모든 모드에 동일한 맵/loop24 경유점/기체 반경0.2m/v7 상한/LiDAR10Hz·15m/
센서 해상도를 사용한다. 기본 Adaptive와 Sector는 body-forward ±45°다.
기존 C24 실행 정책·3 worker·0.25s dispatch lease·비동기 certified recovery를 유지한다.
새 코드는 맵 생성·실험 실행·관측/집계만 담당하며 planner/Adaptive 정책을 변경하지 않는다.

기존 최소 장애물 표면 간격1m 조건을 복원하지 않는다. 원기둥 비겹침과 미션 연결을
검사한다. 맵 생성 manifest에는 배치 seed, 전체 배치 탈락 이력, 실제 최소·최근접
간격 분포, 밀도, PCD 점 간격, endpoint/연속선분 연결 검사를 저장한다.
기하 연결성은 v7 동역학적 성공이나 무접촉 주행의 보장이 아니다.

## 결과 보존과 판정

저장 위치는 `results/scenario7_n10_YYYYMMDD_HHMMSS_PID/`다. 시작/종료 시 출력한다.
`--continue-after-failure`는 접촉·미완주·로그 누락·속도/자원 오류·child 종료 오류를
원래 실패/무효/N/A로 남기고 다음 예정 묶음으로 진행한다. 성공으로 바꾸거나 재시도해
대체하지 않는다. 실행 중 source/map/evidence 변경과 사용자 중단은 계속 진행하지 않는다.
사전검사 실패로 child가 시작하지 못한 slot도 기록0/접촉0으로 채우지 않는다.
특히 profiler-ON 예비주행의 계측·소스·시간·안전 admission을 통과하지 못한 맵은
그 기준을 임의로 완화하지 않으므로 OFF 본시험이 시작되지 않을 수 있다. 해당
오류와 미실행 수를 남기고 다음 맵으로 진행한다. 이 옵션은 모든 slot의 실제
비행을 보장하거나, 예비시험 실패를 통과로 재분류하는 옵션이 아니다.

기존 실행기는 모드3개를 묶어 실행한다. 프로세스/인프라 오류로 묶음 자체가 중단되면
남은 모드의 실제 raw가 없을 수 있으며, 계획210회와 실제 기록 수를 별도로 보고한다.
성공/접촉만으로는 원본 행을 제거하지 않는다. 정상 완료 상태는 `COMPLETE`, 실패나
누락을 보존한 순회 종료는 `COMPLETE_WITH_RETAINED_FAILURES`다.

| 파일 | 내용 |
|---|---|
| summary_by_map.md / .csv | 맵·모드별 계획/기록 수, 경유점 도달, 무접촉 완주, 접촉 주행·episode·미확인, 시간·CPU·입력·맵 시간 |
| summary_overall.csv | 본시험 전체 평균·유효n·SD 및 Full 대비 감소율 |
| adaptive_transitions_by_map.csv | 실제 소스 Sector→Full 전환 합계·평균·SD·관측n, 복구 완료 수 |
| report_test10/ | CPU/GPU/메모리/수신 주파수/각 단계 연산/전환 상세 CSV·JSON·한국어 표 |
| report_preflight/ | profiler-ON 예비21회; 본시험 통계와 별도 |
| test10/맵/rNN_runNNNNN/raw.csv | 세 모드별 원본 행 |
| 각 trial/artifacts/*.solid_audit.json | 실체 장애물 접촉 판정, 원본·기하·코드 SHA256 |
| 각 trial/artifacts/*.odometry.csv | 수신 odometry 전체, pose/속도/clearance/시각 |
| status.json / controller.log / plan.json | 진행 상태·실패 이유·정확한 명령과 정책 |
| frozen_inputs_and_evidence.json | 실행 전후 보존 확인용 해시 |

**경유점 도달은 접촉 여부를 포함하지 않는다. 무접촉 완주는 경유점 도달 AND 관측이
정상 완료된 solid-contact 0회다.** 미확인 접촉은0이 아니다. 도시 내부에 들어가도
가까운 PCD 표면이 없다는 이유로 충돌이 사라지지 않도록 기체 구와 solid AABB 건물 /
유한 원기둥의 교차를 계산한다. 접촉 진입~이탈 연속 구간이 episode1회다.
수신 pose 표본 판정이며 표본 사이 swept-volume 증명은 아니다. 기존 sampled-PCD
raw 값은 보조 지표로 보존하고 주 표와 구분한다.

CPU는 실험 cgroup 전체(시뮬레이터 포함)의 평균 cores와 측정 구간 core-s다. 배경을
포함한 컴퓨터 전체 CPU도 별도로 기록한다. CPU 측정 구간은 mission 구간보다 약간
넓으므로 core-s를 mission 시간으로 나눠 CPU를 재계산하지 않는다. 입력량은 맵 입력
논리 payload의 MiB/s와 MiB/run이며 실제 NIC/메모리 대역폭은 아니다. 맵 계산은
ms/frame 경과시간이다. 비용 지표는 유효n을 함께 표시하며 오류/계측오염은 N/A다.
미완주로 짧아진 회차의 누적 비용을 완주 대비 효율 개선으로 해석하지 않는다.

## 구현/검증 기록

오프라인 코드 검사·맵 기하 검증·dry-run은 실제 비행 결과가 아니다. 본 문서의 실행
명령은 사용자가 직접 본시험을 시작하기 위한 것이며, 준비 과정에서210회 비행을
자동 시작하지 않는다. 최종 오프라인 검증 결과는 이 절 아래에 기록한다.

맵 생성 자체의 연결성 검사는 U1 최소 기체 외부 여유0.470820m, F1 0.450040m로
설계 기준0.35m를 충족했다. F1은 고정 proposal seed의 다섯 번째 배치로, 앞선 네
배치는 미션 시작/경유점의 기하 여유 부족으로 비행 전에 제외했다. 모드별 비행
성적을 보고 선택한 배치는 아니다. 기존 runtime 맵 자산397개의 해시도 그대로다.

첫 실행 계획 검사에서 admission 문서의 `Path` 직렬화 오류를 발견했다. 이는 ROS
시작 전 저장 오류였고, 해당 zero-flight 폴더는 원인 기록용으로 보존한다. 기존
캠페인 결과·플래너를 수정하지 않고 새 맵 등록기의 문서 표현을 수정했다.

최종 준비 검증(2026-09-24):

- 새 생성기/solid 관측기/어댑터/실행기 오프라인 테스트 **121개 통과**.
- 기존 gapfree 관측기·실행기·등록기·보고서 회귀 테스트 **60개 통과**.
- launcher `bash -n` 및 실제 ROS 환경을 source한 `--help` 통과.
- 실제 `--dry-run` 통과: 정적 전달 계획56개 + ON21회/OFF210회, 식별자231개 유일.
- 검증 폴더: `results/scenario7_n10_20260924_135936_1954735/`.
- 위 폴더 상태는 `DRY_RUN_ONLY`, `actual_flights_started=0`이다. DDS/RViz 검사의
  **계획**을 검증했으며, 실제 전달 검사는 사용자가 캠페인을 시작하면 수행한다.
- 최종 접촉 판정 재검증은 동일 입력의 완료된 성공 검증만 제한적으로 캐시한다.
  기록·기하·PCD·관측 코드 또는 sidecar가 바뀌거나 없어지면 캐시를 재사용하지 않는다.
- ON Full/Adaptive solid 접촉도 별도 안전 admission에 반영한다. 오래된 sampled-PCD
  지표가0이어도 solid 접촉을 본시험 기준 통과로 바꾸지 않는다.

이 준비 단계에서 실제 비행 성능·무접촉 성공률은 아직 측정하지 않았다.
