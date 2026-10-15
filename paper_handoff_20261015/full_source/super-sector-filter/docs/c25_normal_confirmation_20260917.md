# C25: 고정 C24 후보의 Normal 독립 20회 반복 검증 (2026-09-17)

## 목적과 동결 범위

사용자가 다음 단계 중 1번(현재 수정본 고정)과 2번(Normal 300회)을 승인했다.
완료된 C24 OFF75와 ON15를 보존하고, 같은 runtime source/binary/config/map와
옵션을 사용한 새 독립 OFF300을 수행한다. planner/알고리즘/맵 튜닝, Stress
탐색, 40%를 맞추기 위한 추가 최적화, GitHub push는 이번 범위에 없다.
실행기 추가만으로 C24의 기존 파일·동결 해시를 변경하지 않는다.

C24 frozen inventory 전체의 현존 파일 해시 및 새 재계산 ON/OFF gate와
저장 gate의 일치를 admission에서 확인한다. 불일치하면 비행을 시작하지
않는다. 후보 식별자는 C24와 동일하다. C24 OFF75는 이번 300회에 합산하지
않고, 사전시험 ON15도 본시험 비용 통계와 분리한다. 과거 실패는 보존한다.

## 맵과 표본

| 맵 | 물리 설정 | 새 ON 사전시험 | 새 OFF 본시험 |
|---|---|---:|---:|
| N1 | seed1.yaml / seed1.pcd | 모드당 1회 | 모드당 20회 |
| N2 | seed3.yaml / seed3.pcd | 모드당 1회 | 모드당 20회 |
| N3 | seed5.yaml / seed5.pcd | 모드당 1회 | 모드당 20회 |
| N4 | seed7.yaml / seed7.pcd | 모드당 1회 | 모드당 20회 |
| N5 | seed9.yaml / seed9.pcd | 모드당 1회 | 모드당 20회 |
| 합계 | Full / Fixed Sector / Adaptive | 15회 | 300회 |

먼저 새 static DDS30건과 실제 RViz late/reconnect5건, manifest5개를 확인한다.
새 ON15의 실제 FSM/command callback, 소스 획득·맵 ACK·복구·속도·자원·
계측 gate를 확인한 뒤 OFF300으로 넘어간다. 총 비행315회이고 정적35건은
비행 횟수가 아니다. 예상 전체 약6~8시간이며 실패/자원 대기로 달라진다.

공통 side worker3, dispatch lease0.25초, v7, Sector±45도, event Adaptive
body-heading ON, 명시적 async-certified-recovery ON을 유지한다. runtime
옵션 기본값은 변경하지 않는다. Adaptive는 소스 좁은 획득이 기본이며,
복구 중 Full의 새 관측·exact map ACK·새 경로 인증을 확인해야 Sector로
돌아간다. raw-cloud CIRI shadow는 기존 default false를 유지한다.

반복별 맵 순서는 repeat modulo5로 순환한다. 20반복에서 각 맵은 다섯 실행
위치마다 정확히4회 배치한다. 모드 순서는 기존 여섯 permutation을 순환하며
각 맵의 permutation당3~4회다. 완벽한 모드 순서 균형이라고 표현하지 않는다.

## 수락·중단 및 실패 보존

C24와 같은 엄격한 계측·소스·static 전달·복구·속도·주기·자원 gate를 적용한다.
Full/Adaptive는 완주·관측 접촉0을 요구한다. Sector 완주·접촉은 비교 결과로
보존하며, 건강한 재계획 기회 없음과 실제 측정/계약 오류를 구분한다.
시간은 결과 지표이고 과거+10% gate는 적용하지 않는다. 평균 CPU 감소율은
선택 gate가 아니며 최초40% 목표를 35.53% 달성으로 재정의하지 않는다.

하위 실행기는 세 모드 한 triplet을 수행한다. 측정·소스·복구·자원 오류는
하위 실행기에서 즉시 중단하고, Full/Adaptive 결과 실패는 현재 triplet을
마친 뒤 중단한다(최대 두 모드 추가 실행 가능). 다음 triplet은 시작하지
않는다. 자동 재시도/성공 대체/실패 제거는 없다. 사용자는 이번 요청에서
고정·검증만 승인했으므로 실패 시 고정 코드 자동 수정 없이 진단 상태로
종료한다. runtime 수정은 다른 버전과 Normal 재검증이 필요하다.

소유한 composed node RSS>4608MiB는 C24의 bounded gdb20초 stack 채집과
오염 marker를 그대로 적용하고 소유 child process group만 종료한다.
원자료·시도·확인된 결과는 보존하고 해당 triplet 비용 지표는 N/A 처리한다.
스택 미확보/재현 없음은 과거 메모리 급증 원인 해결의 증거가 아니다.

## 기록과 집계

원자료 CSV·mode summary·실행 로그·interval·ACK/복구 audit·자원/CPU/GPU
표본을 기존 runner대로 모두 남긴다. 맵·모드별 정확한20회와 run identity,
재시도0, 새 audit와 저장 audit 일치, 동결 파일 불변을 최종 gate로 확인한다.

- 평균 CPU: 실험 cgroup 전체 cores(시뮬레이터 포함, 외부 observer 제외).
- 누적 CPU: 같은 cgroup 측정 구간의 core-s/run. 주행시간과 구간이 조금 다름.
- 논리 맵 입력 payload MiB/s와 MiB/run, 포인트·프레임 수; 물리 NIC 대역폭 아님.
- 맵 갱신 elapsed ms/frame; CPU시간 아님, 중첩 stage 합산 금지.
- 시간, odometry/header/receipt cadence·p99/max 및 ON 실제 FSM/command 주파수.
- RSS/PSS·GPU 장치 전체·host CPU/baseline·swap 등 원시/집계 가용 지표.
- Adaptive 양방향 전환·복구 cycle·미완료 복구; 초기 복구 포함, 충돌 회피 횟수 아님.
- 평균/표준편차·p95/max 등 기존 전체 지표를 결측 수와 함께 보고한다.

기본 실행 경로는 `results/c25_normal_confirmation_20260917/iteration01/`이다.
`status.json`의 COMPLETE 전에는 300회 완료라고 표시하지 않는다.
`report_confirmation20/`가 본시험, `report_preflight/`가 별도 ON 결과다.
실행기: `scripts/native_campaign/run_c25_normal_confirmation.py`.

```bash
cd /root/super-sector-filter
PYTHONNOUSERSITE=1 python3 -u scripts/native_campaign/run_c25_normal_confirmation.py \
  --output results/c25_normal_confirmation_20260917/iteration01 --base-run 21000
```

이미 살아 있는 캠페인이 있으면 중복 실행하지 않는다. 시험 중 빌드/맵 생성/
계측 소스 수정/대규모 git 작업을 하지 않는다. 관측100%는 이 정적 시뮬레이션
표본에 한정하며 모집단100%나 실제 비행 보장으로 표현하지 않는다.
