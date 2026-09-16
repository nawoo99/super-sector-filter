# C20: 안전 인증 교체 경쟁 수정과 seed1 재검증

## 승인·보존·범위

사용자 승인: (1) 오래된 검사 결과의 최신 인증 덮어쓰기 방지,
(2) 버전 교체 시 제한된 재검사, (3) 실패·시간 초과 시 정지 유지,
(4) seed1 Full/Sector/Adaptive 반복검증까지 수행.

기존 C19 OFF n5와 CPU 계측 추가 후 ON/OFF n1은 별도 코호트로 보존한다.
수정 전 세 소스는 `results/c20_certificate_refresh_20260916/preservation/`
에 보존했다. tar SHA256:
`3cc672e97a20654689914cf0e614513823de5997df4026c129ddbd1d3abcdf16`.
과거 Normal/Stress 캠페인과 새 결과를 합산하지 않는다. 맵·센서·제어주기·
안전거리·Full 관측/맵 ACK/새 경로 복구 조건은 변경하지 않는다.

## 진단 근거와 수정

C19 OFF run9501 Adaptive의 복구4회 중 cycle1/2는 CLEARANCE_MARGIN,
cycle3/4는 VERSION_CHANGED였다. 각각 Full 체류1.503/.545/1.573/.702초.
cycle2는 UNOBSERVED/동역학 조건에 의한 제동 후보 거절도 동반했다.
cycle3/4는 검증중 trajectory generation83→84,90→91 commit과 겹쳤다.
동일 VERSION_CHANGED가 계측 추가 전 run9401 Sector에도 있었다.
기존 상태코드는 map/trajectory 버전 교체를 구별하지 않으므로 실제 두 사건의
원인을 하나로 확정하지 않는다. Full 체류시간은 전체 제동·재가속 손실이 아니다.

기존 실제 함수 추출 격리테스트에서는 SAFE 기하 검사중 commit→제동과,
늦게 끝난 옛 결과가 새 SAFE 인증을 덮는 순서를 각각100회 재현했다.
이는 fixture 기반 동시성 테스트이지 비행100회 또는 물리 충돌 판정 재현이 아니다.
실제 run9501에서 인증 덮어쓰기까지 발생했는지는 기존 로그만으로 알 수 없다.

수정 내용:

- 인증 검사 시작번호/발행번호를 safety mutex로 관리. 늦게 끝난 이전 검사가
  이후 발행된 결과를 덮지 못하며, 현재 map/generation과 맞는 결과만 발행한다.
- 더 최신인 유효 SAFE 인증이 있으면 사용한다. 최신 명시적 실패는 이전 SAFE
  결과가 지우거나 같은 호출에서 재검사로 무시하지 못한다.
- VERSION_CHANGED만 최대1회 추가 검사한다. refresh 진입 후4ms까지를 추가
  검사의 deadline으로 전달하고 샘플/DDA/맵 query 루프에서 만료를 확인한다.
  늦게 끝난 SAFE도 발행 직전 TIMEOUT 처리한다. 첫 기존 검사는 시간 제한을
  새로 걸지 않는다. OS scheduling/단일 query에 대한 hard real-time 보장은 아니다.
- mutable-map backend는 untimed read lock을 사용하므로 추가 검사를 하지 않는다.
- 실제 OCCUPIED/CLEARANCE_MARGIN/UNOBSERVED 및 timeout은 버전 변경으로
  덮어 retry하지 않는다. 실패는 기존 정지·Full 복구 경로를 유지한다.
- revalidation 요청은 검사 시작 때 소비한다. 계산 도중 도착한 요청을 종료 시
  무조건 false로 지우던 동작을 없앤다.
- command sample/certificate의 generation·map 검사와 제동 publication gate는
  변경하지 않는다. VERSION_CHANGED 자체를 SAFE로 간주하지 않는다.

## 사전 검증 계획

새 빌드의 정적 전달6조건 및 실제 RViz late/reconnect 증거를 갱신한다.
계측 ON run9600 F/S/A 각1회는 주기·계측 사전검사로만 사용한다.
본시험은 OFF run9601–9605, 모드별5회이며 순서는 기존5회 검증과 동일하게 회전한다.
실험 중 코드·설정·바이너리는 동결한다. 자동 재시도·실패 제외 없음.
완주/접촉 실패 시 중단하고 원자료를 남긴다. A/F 주행시간비1.10 기준과
평균 CPU30% 공학 기준은 그대로 보고하되, 최초40% 목표 달성으로 바꾸지 않는다.

CPU 범위는 simulator/frontend/planner/mission/launcher 전체 실험 프로세스·
thread이며 외부 관측기는 제외한다. 평균 코어와 누적 core-s를 함께 보고한다.
누적 CPU 측정창은 waypoint mission보다 조금 넓다. 계측 ON/OFF, 과거 C19,
새 C20을 합산하지 않는다. seed1은 튜닝에 사용한 맵이므로 일반화 증거가 아니다.

## 결과

**수정1–3 완료, 단계4 반복검증은 주기 품질검사 실패로 중단. 합격/완료 선언 금지.**

- Release 직렬 빌드2패키지 성공(6분47초). 기존 reorder/CMake 경고 외 오류 없음.
- 실제 함수 추출 일반/ASan+UBSan 각각1,403검사, 그중 실제 thread 교차300건 통과.
  기하 validator는 fixture이며 실제 비행/물리충돌 검증을 대신하지 않는다.
- Python135검사, 기존 command/path publication8검사, demand policy검사 통과.
- 최초 controller는 workspace setup을 source하지 않은 셸에서 시작해
  `mars_quadrotor_msgs` import 오류로 **첫 전달검사·비행 시작 전에 중단**했다.
  최상위 plan/status/controller 로그를 보존했다. 환경 source 후
  `results/c20_certificate_refresh_20260916/validation/`에 별도 사전계획을 만들고
  검증을 시작한다. 런타임 수정/비행 재시도/표본 제외가 아니다.

전달6조건·실제 RViz 재접속 모두 통과. ON 사전3회는 F/S/A 모두 완주·접촉0,
시간36.60/39.31/39.83초. 센서10Hz와 FSM/command 약100Hz 기준 통과.
별도 OFF 본시험은8회까지 실행했으며 모두 완주·접촉0이다. run9603 Full에서
odometry 최대간격 기준을 실패해 계획된15회 중 **7회 미실행** 상태로 중단했다.
해당 회차를 제외하거나 재시험으로 대체하지 않았으며, runtime hash는 전부 동일하다.

| seed1 / OFF | 수행·완주 | 접촉 | 평균 주행(s) | 평균 CPU(코어) | 회차평균 누적 CPU(core-s) |
|---|---:|---:|---:|---:|---:|
| Full | 3/3 | 0 | 38.523 | 0.523683 | 20.887109 |
| Sector | 2/2 | 0 | 39.735 | 0.350560 | 14.593530 |
| Adaptive | 3/3 | 0 | 38.390 | 0.357059 | 14.385624 |

수행된 표본의 기술통계이며 계획된 n5 최종 비교가 아니다. Full의 주기 기준 실패도
위 평균에 남아 있다. Adaptive/Full 각각3회의 관측 평균CPU 감소31.82%,
누적CPU 감소31.13%; 최초40% 목표 미달이며 품질 기준 실패로 최적화 합격값이 아니다.
Sector는 n2로 표본 수가 다르다. 원자료·전체 수치 표는 `comparison/summary_ko.md`.

| 회차 | Full(s) | Sector(s) | Adaptive(s) | Adaptive Full 복구/완료 |
|---|---:|---:|---:|---:|
| run9601 | 38.37 | 39.86 | 38.65 | 2/2 |
| run9602 | 37.70 | 39.61 | 38.56 | 1/1 |
| run9603 | 39.50(주기 기준 실패) | 미실행 | 37.96 | 1/1 |
| run9604–9605 | 미실행 | 미실행 | 미실행 | 미실행 |

실제11비행(ON3+OFF8) 로그에 최신 인증 재사용4건과 버전 변경→추가검사SAFE1건
(run9601 Adaptive의 poly_publish)이 관측됐다. 이를 회피한 충돌 수로 해석하지 않는다.
main_pre의 최종 VERSION_CHANGED/TIMEOUT은0건이다. 이전43.75초 지연은 수행된
Adaptive OFF3회에서 재현되지 않았지만, 표본 부족·중단으로 해결의 일반적 보장은 없다.

## 중단 원인: 확인된 사실과 미확정 부분

run9603 Full의 유일한 source-contract 실패 항목은 `small_pool_timing`이며,
하위 실패는 odometry header max56.987398ms, receipt max57.573880ms
(사전 상한50ms)이다. 평균99.9018Hz, header p99 10.1373ms,
receipt p99 10.6446ms였다. command max는 stamp80.17792/receipt80.407754ms이나
이는 기존 게이트가 사용하는 odometry 항목과 다르며 의도적 hold도 포함한다.

이 Full 회차에는 추가 geometry retry가0회였고 최신 인증 재사용만1회였다.
따라서 57ms를 새 추가검사1회의 비용이라고 단정할 근거가 없다. 그 밖의 변경이나
동시성 영향까지 배제한 것은 아니다. 메모리 PSI some/full avg10은 모두0,
실험 FSM swap0, MemAvailable 최소5.63GiB로 자원 기준은 통과했다.
10초 평균/주기 표본이 모든 순간 지연을 배제하는 것은 아니다.

별도 관측: replan0.824초 overtime 로그1건과 외부 Python 프로세스 CPU spike가
있다. odometry와 FSM/replan은 같은2-worker side executor를 공유한다.
하지만 관측기는 간격의 분포만 저장하고 **최대간격 발생시각을 저장하지 않는다**.
따라서 overtime/외부부하/스케줄링/DDS 중 어느 것이 해당57ms를 만들었는지
시간 정렬로 확정할 수 없다. 관측 지연을 바로 planner 계산시간으로 해석하면 안 된다.

다음 작업은 threshold를 늘리는 것이 아니라, 간격 초과 시점의 stamp/receipt,
producer callback 지연·duration, 활성 planner callback과 자원 타임라인을 묶는
진단 계측이다. 이를 먼저 확인한 뒤 별도 계획으로 반복검증을 재개해야 한다.
현재 대규모 캠페인/맵5개 비행/과거 자료 합산은 하지 않는다.
