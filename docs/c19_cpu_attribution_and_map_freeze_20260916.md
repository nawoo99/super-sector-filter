# C19: CPU 귀속 보완·seed1 진단·물리 맵 목록 고정

## 승인 범위와 사전 계획

사용자 승인: 다음 단계 1–3까지만 진행. 실험 CPU를 시뮬레이터/자율주행/
공통·미분류로 구분하고, seed1 세 모드에서 계측을 검증한 뒤 실제 물리 맵
목록을 고정한다. 맵당20회 캠페인이나 추가 planner 최적화는 이번 범위 밖이다.

C19의 알고리즘·안전 설정·센서/제어 주기·실행기 구조는 변경하지 않는다.
기존 OFF n5 결과와 Normal 원자료를 보존한다. 새 바이너리는 계측만 추가한
진단 버전으로, 기존 C19와 바이너리 동일성을 주장하거나 결과를 합산하지 않는다.

## 1. CPU 측정 보완

기존 stage ID 0–29는 유지하고 30–42에 map odometry와 frontend의 acquisition,
enqueue, cloud worker, odometry, replan status, map commit/ACK, guard status,
trajectory, risk worker, report, stats를 추가했다. 기존 함수 본문·주기는 그대로다.
`SUPER_CPU_PROFILE=1`에서만 thread CPU clock/counter를 사용한다. OFF는
기존 방식대로 시간 측정·counter 갱신·role 로그가 없다.

map/frontend worker의 실제 실행 TID를 worker entry에서 기록한다. 스레드 생성
순서로 pool 작업의 소유를 추정하지 않는다. simulator→frontend→map 직접호출은
중첩 scope이며 exclusive 값만 합산한다. 공유 라이브러리와 실행 파일 경계의
registry/TLS 공유 및 중첩 차감 단위검사를 OFF/ON 모두 수행했다. 실제 component와
Adaptive 실행 파일에서도 동일 크기2816 byte의 GNU UNIQUE registry/TLS 심볼을 확인했다.

측정 가능한 autonomy subtotal과 simulator callback subtotal을 따로 표시하되,
executor/DDS/미계측 callback·프로파일링 비용을 추정하여 autonomy에 몰아주지 않는다.
프로세스 누적 counter와 같은 report window로 정렬한 나머지는 accounting residual이다.
scope 종료 시점 귀속/개별 atomic 읽기 때문에 정확한 물리적 미계측 CPU 범위가 아니다.
launch/mission 등의 다른 프로세스 CPU는 실험 cgroup에 계속 포함되며 별도 정렬 근거를
남긴다. 순수 자율주행 전체 CPU가 완전히 분리됐다고 주장하지 않는다.

## 2. seed1 검증 계획

`results/c19_cpu_attribution_20260916/plan.json`에 실행 전 고정했다.

- 새 바이너리로 static transport 6조건 및 실제 RViz 늦은 접속/재접속 재검사.
- run9500: 계측 ON, Full→Sector→Adaptive 각1회.
- run9501: 계측 OFF, Adaptive→Sector→Full 각1회.
- 자동 재시도·유리한 결과 선택 없음. 실패는 남기고 중단한다.
- 기존 OFF 각5회는 주 성능 근거로 보존, 이번 ON/OFF 각1회와 합산하지 않는다.
- 단일 ON/OFF 쌍은 실행·경로 변동과 계측 오버헤드를 분리하지 못하므로
  오버헤드가 정확히 몇%라고 단정하지 않는다.

Release 빌드 4패키지는 직렬 빌드로 완료(7분42초). 첫 빌드는 병렬 옵션이 실제
make -j20으로 적용된 것을 확인해 종료한 후 -j1 환경으로 재시작했다. 이는
비행/성능 표본이 아니다. 기존 컴파일러 경고는 별도로 남기고 알고리즘은 고치지 않았다.

### 결과: 실행 완료, 확대 조건은 미통과

정적 전달6조건 및 실제RViz late/reconnect 모두 통과했고 화면도 확인했다.
ON/OFF 총6회 모두 완주·접촉0, 자동재시도0. 소스/복구/자원/속도/계측 검사 통과.
단, **OFF의 Adaptive/Full 주행시간비1.1614가 사전 기준1.10을 초과**했다.
controller의 COMPLETE는 예정된 실행 종료이지 모든 검증 합격이 아니다.
`verification.json`의 `all_verification_gates_pass=false`가 최종 판정이다.

| 계측 | 모드 | 완주 | 접촉 | 주행 초 | 실험 평균 CPU 코어 | 누적 core-s |
|---|---|---:|---:|---:|---:|---:|
| ON | Full | 1/1 | 0 | 39.41 | 0.542691 | 22.041888 |
| ON | Sector | 1/1 | 0 | 38.97 | 0.342253 | 13.896686 |
| ON | Adaptive | 1/1 | 0 | 37.45 | 0.345792 | 13.321922 |
| OFF | Full | 1/1 | 0 | 37.67 | 0.530831 | 21.012528 |
| OFF | Sector | 1/1 | 0 | 36.76 | 0.348768 | 13.456781 |
| OFF | Adaptive | 1/1 | 0 | 43.75 | 0.368413 | 16.496592 |

1코어=논리CPU1개의100%. 실험 범위는 simulator/frontend/planner/mission/launcher의
모든 thread, 외부 관측기 제외. 누적CPU는 mission보다 약간 넓은 cgroup 구간이다.
OFF n1 Adaptive는 Full 대비 평균CPU30.60%,누적21.49% 감소지만 주행16.14% 증가.
시간 조건을 실패했으므로 **최적화 합격 자료/40% 달성으로 채택하지 않는다**.
기존 OFF n5의 평균34.25%·누적32.87% 절감 자료는 그대로 별도 보존한다.

별도 ON report window의 exclusive 계측 소계:

| 모드 | 관측창 초 | 자율주행 계측 소계 코어 | simulator callback 코어 | 진단/시각화 코어 |
|---|---:|---:|---:|---:|
| Full | 30.059 | 0.387961 | 0.052925 | 0.000577 |
| Sector | 35.049 | 0.206890 | 0.026457 | 0.001442 |
| Adaptive | 30.059 | 0.209239 | 0.029530 | 0.001677 |

이 소계의 Adaptive 감소는 약46.1%지만 **전체 자율주행 CPU나 최초40% 목표 달성이
아니다**. 측정된 함수들만의 소계이며 공통/미분류 비용이 남는다. composed accounting
residual은 F0.03660–0.07053/S0.06222–0.07849/A0.04466–0.06395코어,
다른 실험 프로세스는 각각 약0.039–0.041/0.043–0.045/0.044–0.047코어다.
범위의 의미·원자료는 `attribution/alignment.json` 및 `attribution/README.md` 참조.

첫 오프라인 집계는 Fixed Sector에도 recovery ACK callback을 요구해 실패했다.
실제 소스는 Adaptive에서만 그 구독을 생성하므로, 모드별 필수 계측 검사를 수정하고
회귀 테스트를 추가했다. 초기 partial alignment는 `attribution_initial_parser_check/`에
보존했다. 비행 재실행·런타임 변경·수치 선별은 없었다. 관련 Python136검사 통과.

### 느린 OFF Adaptive의 관측된 원인과 남은 확인

- ON은 Full 복구1회/복귀1회/완료1회, OFF는 각각4회. 미완료0회.
- Full 체류 합계는 ON1.237초, OFF4.323초. 경로 길이는221.181→223.099m로
  약0.87% 증가했지만 시간은37.45→43.75초. 브레이크/복구·재가속 및 경로 변동이
  동반됐다. Full 체류 차이만으로6.30초 전부를 설명한다고 주장하지 않는다.
- OFF cycle3/4 직전에 `TRAJ_GUARD_CERT status=VERSION_CHANGED`가 기록됐고,
  검사 중 generation83→84 및90→91의 새 경로 commit과 겹친다. 그 뒤
  `main_pre_uncertified` 브레이크, 새 Full 관측→ACK→새경로→Sector복귀가 이어졌다.
- `super_planner.cpp::validateCommittedTrajectory`는 검사 도중 generation 교체 시
  VERSION_CHANGED를 반환한다. map version 교체도 같은 상태를 사용한다.
  `refreshSafetyCertificate`는 non-SAFE를 false로 돌려주고 main_pre는 브레이크로
  연결한다. 관측된 두 episode는 동시 경로 교체와 연관된 보수적 복구의 증거다.
  상태코드만으로 map/trajectory 두 원인을 완전히 분리하거나 모든 복구를 불필요한
  오탐으로 단정하지 않는다.
- cycle2에서는 브레이크 후보가 UNOBSERVED/동역학 조건으로 거절된 뒤
  emergency_stop_retry가 복구했다. 이 episode를 앞의 VERSION_CHANGED 두 건과
  동일 원인으로 뭉뚱그리지 않는다.

따라서 이번 단일 ON/OFF는 계측 오버헤드의 인과적 추정에 부적합하다.
이번에는 안전 동작을 고치지 않았으며, 다음 구현 전 generation 교체와 certificate
publication 경쟁을 재현·구분해야 한다. VERSION_CHANGED를 무조건 SAFE로 바꾸거나
안전 검사를 생략해서 시간을 줄여서는 안 된다.

## 3. 물리 맵 목록

`results/c19_map_suite_20260916/preregistration.json` 및 `manifest.json` 참조.

Normal은 각 기존 지름 조건의 첫 물리 seed1/3/5/7/9를 N1–N5로 고정한다.
과거 두 seed씩 묶은5조건과 다르며 과거 각10회 결과를 새 물리 맵20회로 바꿔
표시하지 않는다. 새 Stress는 `c19_cyl_probe_s1`–`s5`로 새 이름을 부여했다.
이름·좌표·규칙·원자료/hash를 **비행 전에** 고정하고 이번에는 기하 검사만 한다.

모든 맵은 정적 원기둥410개, 높이3m. 지름은 순서대로0.30/0.55/0.80/1.05/1.30m.
Stress는 배경이 항상 존재하고 최소 표면간 간격1m를 유지한다. S1–S3은 첫 코너
직후 분리된 원기둥3개, S4–S5는 첫/둘째 코너 직후 총6개를 배치하고 배경을
재배치하여 총410개를 유지한다. 벽 primitive·붙은 원기둥 사슬·dropout·동적
장애물은 없다. Normal 배경 seed를 활용했으므로 미지 배경 일반화 자료가 아니다.

기하 검사에서5개 모두 경로 각 구간의 연속 선분 body clearance가0.45m 이상이다.
이는 동역학/closed-loop 완주나 Sector 대비 우위를 보장하지 않는다. 계산된
기하 경로는 검사 증거일 뿐 실제 planner의 waypoint로 주지 않는다.
**Stress 5개는 성과 검증 완료 맵이 아니라 동결한 탐색 후보**다. 모든 이전 실패
맵과 로그는 보존하고, 새 후보가 실패해도 숨기거나 본시험에서만 제외하지 않는다.

다음은 우선 위 시간 초과/동시 경로 교체 검증 문제를 다루고, seed1에 결합된
geometry/hash, 전달, 계측 및 timing gate를 map-aware로 확장한 뒤 새 맵 smoke를
수행하는 단계다. 그 결과를 본 뒤 동결 버전20회 검증을
별도 승인·계획한다. 탐색 중 재설계가 필요하면 새 버전으로 구분한다.
