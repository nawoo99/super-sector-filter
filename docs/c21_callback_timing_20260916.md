# C21: 50ms 초과 원인 계측과 seed1 반복검증

## 범위와 사전 계획

사용자 요청: C20의 4단계(Full/Sector/Adaptive 각5회) 결과가 제대로 나올 때까지
원인 분석·수정·재시험. 이전 C20 OFF run9603 Full의 odometry 최대간격
56.99/57.57ms 실패는 그대로 보존한다. 충돌은 없었으며50ms는 사전 선언한
실험 품질 기준이지 물리적 충돌 임계값이나 hard real-time 보장이 아니다.

1. 수신 간격 초과와 최대값의 message stamp, monotonic receipt, epoch 시각을
   저장한다. 분포 산식·기존50ms/p99 20ms 기준은 변경하지 않는다.
2. producer SimOdom 및 FsmMain/Command/Replan 콜백에 기본OFF 진단 scope를
   추가한다. `SUPER_CALLBACK_TRACE=1`일 때20ms 초과 시작간격/실행시간만
   monotonic/epoch/TID와 함께 기록한다. OFF는 clock/atomic/output 작업이 없다.
   이 계측은 스케줄링이나 안전 판정을 바꾸지 않으며 ON 자료는 CPU 본시험과
   합산하지 않는다. 정상 짧은 콜백은 출력되지 않으므로 완전한 executor trace는 아니다.
3. 새 바이너리로 정적 전달6조건·실제RViz late/reconnect 재검증 후 동일
   2-worker Full 진단3회(9700–9702). timing-only 실패여도 미리 정한 진단3회를
   계속하되 실패 자체를 합격으로 처리하지 않는다. 안전/완주/다른 계약 실패는 중단.
4. 원인에 따른 수정 또는 분리 실험 후 별도 동결 검증. trace OFF, CPU profile
   ON 사전3회와 OFF 본시험 각5회. 코드·설정·바이너리 고정 및 모드 순서 회전.
   실패를 성공 회차로 대체하거나 과거자료와 합산하지 않는다.

합격 판정은 모든 모드 완주·접촉0, source/recovery/resource/속도/주기 계약,
Adaptive/Full 시간비≤1.10 및 기존 각모드 시간 기준을 함께 확인한다.
평균 CPU30% 공학 목표와 누적CPU 감소를 별도 보고하고 최초40% 달성으로
바꾸지 않는다. CPU 범위는 simulator 포함 실험 프로세스 전체(외부관측기 제외).
맵·센서 해상도/주기·안전거리·새Full관측/맵ACK/새경로 조건 변경 없음.

## 구현·검증 기록

- 수신 long-gap 이벤트 최대128건, 최대간격 문맥은 이벤트/분포 overflow와
  무관하게 유지. 서로 다른 clock domain은 빼지 않는다.
- C++ 진단은 callback instance별 상태.20ms 초과 콜백 종료시 기록하므로
  무한히 끝나지 않는 콜백이나 모든 짧은 작업의 시계열을 제공하지 않는다.
- Python107검사 통과. C++ trace OFF/ON/clock jump/instance 분리 검사는
  일반 및 ASan+UBSan 모두 통과. 실제 인증 함수추출1,403검사(300thread교차)
  회귀 통과; geometry/time/map fixture이며 비행검증을 대신하지 않는다.

실험 원자료: `results/c21_callback_timing_20260916/`.
진단·수정·본시험 결과는 아래에 순서대로 추가한다.

## 진단 완료 및 검증 후보 결정(본시험 전)

Release 직렬3패키지 빌드8분6초 성공. 전달6조건 및 실제RViz 통과.
2-worker Full trace/profile ON 진단9700–9702는 완주3/3, 접촉0,
시간38.17/38.92/39.06초, odometry receipt max11.34/11.85/12.52ms.
이전57.57ms는 이3회에서 재현되지 않았다. 정상 odometry가 유지되는 동안에도
긴 replan span이 있어 replan duration만으로 지연 원인을 확정하지 않는다.

실제 rclcpp executor 통제실험을 추가했다. 동일한 두 blocking callback(각100ms)
및10ms odometry timer를 두고 worker수만 바꾼 결과,2-worker max110.184ms,
3-worker max10.306ms. 이는 **공유 pool 용량의 구조적 취약성 재현**이며,
옛 C20 회차의 콜백 순서를 재현하거나 그 원인을 증명한 것이 아니다.

예방적 후보: Full/Sector/Adaptive 공통 side worker2→3. 기존 환경옵션만 변경,
planner/센서/맵/안전 정책 및 timer period는 그대로. trace OFF 검증9800(ON사전),
9801–9805(OFF 각5회)를 새 사전계획으로 시작한다. CPU 증가 여부도 함께 측정한다.
합격하더라도 과거실패를 삭제하거나 hard real-time 보장으로 해석하지 않는다.

## 최종 검증 결과

**새3-worker 조건의 4단계 검증 통과.** 전달6조건·실제RViz 통과 후
ON 사전3회와 OFF 본시험15회 모두 완주·접촉0. 본시험은 최초 계획한
9801–9805 각1회이며 실패 대체·자동 재시도·중간 설정 변경이 없다.
`validation_3workers/verification.json`의 전체 품질 gate가 true다.
본시험과 별도 진단3회/ON3회/과거C20은 합산하지 않았다.

| seed1 / OFF 각5회 | Full | Sector | Adaptive |
|---|---:|---:|---:|
| 완주 | 5/5 | 5/5 | 5/5 |
| 접촉 발생 회차 | 0/5 | 0/5 | 0/5 |
| 주기 기준 통과 | 5/5 | 5/5 | 5/5 |
| 평균 주행시간(s) | 38.152 | 39.320 | 38.452 |
| 평균 실험 CPU(코어) | 0.538817 | 0.352015 | 0.370185 |
| 회차 평균 누적 CPU(core-s) | 21.415059 | 14.373238 | 14.797914 |
| Full 대비 평균 CPU 감소 | 기준 | 34.67% | **31.30%** |
| Full 대비 누적 CPU 감소 | 기준 | 32.88% | **30.90%** |
| 관측 최대 odometry header 간격(ms) | 17.575 | 11.569 | 10.677 |
| 관측 최대 odometry receipt 간격(ms) | 17.735 | 14.783 | 16.090 |
| 회차별 receipt p99 중 최댓값(ms) | 10.914 | 11.191 | 11.451 |
| Full 복구 진입/인증 완료 합계 | 0/0 | 0/0 | 7/7 |

| 회차 | Full(s) | Sector(s) | Adaptive(s) | A Full 복구/완료 | A 평균CPU 감소 |
|---|---:|---:|---:|---:|---:|
| 9801 | 38.14 | 39.11 | 39.52 | 2/2 | **27.88%** |
| 9802 | 37.89 | 40.38 | 38.27 | 1/1 | 31.84% |
| 9803 | 37.07 | 38.53 | 38.49 | 2/2 | 30.78% |
| 9804 | 38.29 | 37.85 | 37.57 | 1/1 | 34.99% |
| 9805 | 39.37 | 40.73 | 38.41 | 1/1 | 30.90% |

Adaptive/Full 시간비는 각회차0.9756–1.0383으로 모두1.10 이내이며,
기존 각모드 시간 기준도 통과. 센서 약10Hz, odometry99.9967–100.0135Hz.
실제 FSM/명령 콜백 빈도는 ON 사전검사에서 확인했고, OFF의 메시지 빈도로
콜백 빈도를 추정하지 않는다. trace OFF 로그에는 CALLBACK_TIMING 출력0건.

**평균 CPU30%는5회 집계 평균으로 충족했으나 매회 충족한 것은 아니다.**
9801의27.88%도 제외하지 않았다. 최초40% 목표는 여전히 미달이다.
시뮬레이터 포함 실험 프로세스 CPU이며 컴퓨터 전체 CPU나 순수 planner CPU
절감률이 아니다. Adaptive 평균 주행시간은 Full보다0.30초(0.79%) 길었다.
CPU 측정창은 주행창보다 조금 넓고, 누적값과 평균값은 동일 cgroup 측정창을 쓴다.

보조 관측: Adaptive 맵갱신 경과시간25.359→10.322ms/frame(59.30% 감소),
유입점수70.21% 감소, 논리 payload70.32% 감소. 경과시간은 CPU 시간과 다르며,
논리 payload는 물리 네트워크 대역폭이 아니다. 전체 수치는
`results/c21_callback_timing_20260916/comparison/summary_ko.md` 및 CSV에 있다.

최종 Python107검사 및 실제함수추출 일반/ASan+UBSan각1,403검사 통과.
trace 자체 일반/ASan+UBSan 검사 통과. 원래 Normal300행 SHA는
`b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5`로 동일.
실험 종료 후 잔여 simulator/planner 프로세스 없음. SUPER 수정분은 코드 미러에
복사하며 로컬 커밋만 한다(push 없음, Co-Authored-By 없음).

## 해석과 다음 단계

- 2-worker의 과거57.57ms 원인은 여전히 확정할 수 없다. 새 시각 계측은 이후
  재현에 대비하며, 통제실험은 worker 고갈 가능성만 입증한다.
- 3-worker는 예방적 여유 확보 후보이고 이번 seed1 각5회 품질 검증을 통과했다.
  일반 OS에서50ms 절대보장이나 모든맵100% 안전/완주 보장을 증명한 것은 아니다.
- 해당 설정은 이번 실험의 공통 `SUPER_SIDE_EXECUTOR_THREADS=3`이다.
  전역 기본값을 바꾸지 않았고, 재실행 runner에는 `--side-threads 3`을 지정한다.
- 다음은 이 후보를 동결한 채 Normal 대표5개 맵의 소규모 검증으로 확장하는 것.
  이번에는 다른맵 비행·대규모 캠페인을 시작하지 않았다. 과거 Normal/Stress와
  새 CPU 최적화 결과를 같은 알고리즘/설정의 확증자료로 합산하면 안 된다.
