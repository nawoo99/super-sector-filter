# Seven-map n10: three separate reporting groups and scenario-specific missions

2026-09-24 갱신. 이전 `scenario7-n10-manual-v1`의 모든 맵loop24/전체7개 평균을
대체하는 `scenario7-n10-manual-v2`다. 아래 절차와 실제 실행 plan을 기준으로 한다.

## 실행 명령

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh --continue-after-failure
```

기존 맵1~5 + 도심 + 숲에서 Full/Sector/Adaptive를 맵·모드당10회씩 실행한다.
본시험은210회이며, 별도 profiler-ON 사전 계측21회를 포함하면 실행 계획은231회다.
사전 계측은 본시험 평균에 포함하지 않는다. 실행 순서는 기존 반복/모드 순환 규칙을
유지한다. 기존 결과를 재사용하거나 실패 회차를 재시도로 교체하지 않는다.

예상 소요시간은 약 **5~7시간**이나, 새 도심/숲의 실제 비행 시간은 아직 측정하지
않았다. 타임아웃·우회·계측 상태에 따라 더 길어질 수 있다. 터미널은 열린 상태로
두며, 종료 시 프롬프트로 돌아오고 창을 자동으로 닫지 않는다.

비행 없이 자산·미션·계획·빈 결과표 검사:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh --dry-run
```

보고서만 재생성:

```bash
bash /root/super-sector-filter/scripts/native_campaign/run_scenario7_n10.sh \
  --report /root/super-sector-filter/results/실제_scenario7_n10_결과폴더
```

## 평균과 감소율

| 집계 그룹 | 포함 맵 | 본시험 계획 수/모드 | 세 모드 합계 |
|---|---|---:|---:|
| normal | G1, G2, G3, G4, G5-R2 | 50 | 150 |
| urban | U1 | 10 | 30 |
| forest | F1 | 10 | 30 |

**7개 맵 전체를 섞은 평균은 만들지 않는다.** 각 그룹 안에서 Full/Sector/Adaptive를
각각 집계한다. 맵별21행 표도 유지한다. 그룹별 CPU/누적CPU/입력량/회당입력량/맵
시간 감소율은 해당 그룹 Full 평균을 기준으로 `100 × (1 - 대상/Full)`로 계산한다.

비용 평균은 해당 그룹의 유효 관측 회차에 대한 산술평균이다. 모든 맵에서10회가
유효하면 normal은 맵별 평균을 동일 가중치로 평균한 값과 같다. 누락/계측 무효가
있으면 유효 회차 수에 비례한 가중치가 되므로 유효n·표준편차·맵별 결과를 함께
기록한다. 누락을0으로 채우거나, 일부 성공만을 전체100%로 표현하지 않는다.
성공/실패와 접촉 결과는 비용 계측 적합성과 별도로 보존한다. 미완주로 짧아진
누적 비용을 완주 대비 효율 개선으로 해석하지 않는다.

## 적용 미션

모든 미션은 초기 `(0,0,1.5)`에서 시작한다. 각 목표의 고도는1.5m, 기존과 동일한
전환 거리1.5m다. 아래 나열에는 초기점과 마지막 복귀점을 모두 표시했다.

| 맵 | 파일 | XY 목표 순서 |
|---|---|---|
| G1~G5-R2 | `loop24.txt` 그대로 | `(0,0) → (24,24) → (-24,24) → (-24,-24) → (24,-24) → (0,0)` |
| U1 | `urban_building_corners_v3.txt` | `(0,0) → (-24,25) → (24,13) → (-24,-13) → (24,-25) → (0,0)` |
| F1 | `forest_wide_zigzag_v2.txt` | `(0,0) → (-24,22) → (24,22) → (-24,-22) → (24,-22) → (0,0)` |

도심 건물 번호는 그림에서 위쪽 행부터 왼쪽→오른쪽1~16이며, 목표는 각각
B1 왼쪽 상단/B8 오른쪽 상단/B9 왼쪽 하단/B16 오른쪽 하단 모서리에서
x/y 각각2m 바깥이다. 기존 geometry 내부 ID를 바꾼 것이 아니다.

미션 TXT, launch의 `waypoint_data`, observer-ready 후 별도로 띄우는 mission의
`data_name`, 모니터의 XY 경유점·목표 수·최종 목표가 동일 등록기를 사용한다.
미션/등록기 해시는 childplan과 ON/OFF 참조 검증, 캠페인 frozen inventory에 저장한다.
첫 목표의 음수 x좌표도 모니터 인수에서 안전하게 처리한다.

원본 맵PCD/장애물 배치/플래너/Adaptive 알고리즘/센서/프로파일/속도 상한/실행
주기/스레드 정책은 변경하지 않았다. G1~G5의 실제 미션은 이전과 같다. U1/F1은
새 미션이므로 이전 loop24 비행 결과와 같은 조건으로 합치지 않는다.
정적 연결성 검사는 실제 v7 동역학적 성공이나 무접촉 비행을 보장하지 않는다.

## 출력과 판정

저장 폴더: `results/scenario7_n10_YYYYMMDD_HHMMSS_PID/`.

| 출력 | 용도 |
|---|---|
| `summary_by_group.csv`, `.md` | normal/urban/forest ×3모드, 총9행의 그룹별 평균/감소율 |
| `summary_overall.csv` | 호환용 이름만 유지; 내용은 위와 같은 **3그룹9행**, 전체7평균 아님 |
| `summary_by_map.csv`, `.md` | 7맵×3모드의 개별 결과·기록/계획 회차 수 |
| `adaptive_transitions_by_map.csv` | 맵별 실제 Sector→Full 전환 횟수 |
| `report_test10/{normal,urban,forest}/` | 그룹별 CPU/GPU/메모리/주파수/단계별 처리 등 상세 보고서 |
| `report_preflight/{normal,urban,forest}/` | 별도 ON 사전계측 상세 보고서 |
| `plan.json`, `admission.json`, `frozen_inputs_and_evidence.json` | 실행 미션·자산·정책·집계 기준 해시 |
| `test10/맵/rNN_runNNNNN/` | 각 묶음 원본CSV·summary·로그·접촉/odometry 증거 |

접촉 여부와 경유점 도달을 분리한다. 무접촉 완주는 경유점 도달 AND 유효하게 관측된
solid 접촉0회다. 접촉 미확인은0이 아니다. 접촉은 기체 구와 고체 건물/원기둥의
수신 odometry 표본 교차이며, 표본 사이 연속 swept-volume 보장은 아니다.

CPU는 기존 실험 cgroup 평균cores·누적core-s 및 별도 컴퓨터 전체CPU를 기록한다.
입력량은 논리payload MiB/s·MiB/run, 맵 계산은ms/frame다. 세 그룹의 미션 길이가
다르므로 raw 누적비용/시간을 서로 동일 과제로 해석하지 않는다.

`--continue-after-failure`는 실패를 삭제하거나 성공으로 바꾸지 않고 다음 예정
묶음으로 진행한다. 사전 계측/소스/안전 기준은 완화하지 않으므로 기준 미달 맵은
본시험이 시작되지 않을 수 있고, 프로세스 중단이면 묶음의 일부 모드가 누락될 수
있다. 계획 수와 실제 기록 수를 구분한다. source/evidence 변경 또는 사용자 중단은
계속 진행하지 않는다. 과거 폴더의 덮어쓰기나 자동 재개는 허용하지 않는다.

## 준비 검증

이 변경의 준비 과정에서는 실제 비행을 시작하지 않았다.

- scenario7 자산/기하/미션/실행기/집계 및 기존 gapfree 실행기/관측기/집계 회귀 검사:
  **233 passed**. 단위 테스트이며 비행 성공 횟수가 아니다.
- 실행 wrapper의 `--dry-run`: ON21 + OFF210 계획 검증 통과, ROS 비행 시작0회.
- `--report`와 실제 생성된 plan/CSV 검사: 그룹별9행, 모드별 계획50/10/10,
  빈 측정값은 N/A, `summary_overall.csv`와 그룹CSV 동일. 본시험/예비시험 분리.
- 231개 예정 비행의 미션 메타데이터와 child 실행·관측 미션 바인딩 일치 검사.
  기존5맵 loop24, 도심 v3, 숲 v2. 도심/숲의 새 경유점으로 실제 비행 검증은 아직
  하지 않았으므로 완주·무접촉 또는 예상 소요시간을 보장하지 않는다.
