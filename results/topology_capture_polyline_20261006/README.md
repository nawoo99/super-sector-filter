# 정지 정체 입력 캡처 및 인증 다중 구간 복구 후보 — 2026-10-06

기존 c41 210회와 v1–v4 실패 증거를 보존한다. 기본 실행본은 변경하지 않는다.
V5 실패를 보존했고 현재 후보는 `/root/super_ws/forest_liveness_trial_v6_20261006/install`이다.
캡처와 복구는 서로 다른 opt-in 옵션이다. 캡처가 켜진 비행의 CPU 수치는
성능 비교에 사용하지 않는다. 원본 run97036의 정확한 맵 재생이 아니라
동일한 정지 위치와 실제 새 LiDAR 관측으로 실행하는 진단이다.

## 사전 정의 순서

1. `capture_available`: 복구 옵션 OFF, virtual zone 2개와 남은 수평 예산을
   재구성하고 실제 A*/CIRI/MINCO/guard 입력을 저장한다. 실패도 그대로 보존한다.
2. 입력 파일과 버전 일관성 확인. 최적화 다항식의 거절 위치를 독립 재계산한다.
3. `polyline_control`, `polyline_available`, `polyline_exhausted`: 복구 옵션 ON,
   각 1회, 원래 다음 목표 도달/접촉0/실제 인증 복구 commit을 확인한다.
   Exhausted에서도 다른 reset 목표로 바꾸지 않는다. 자동 재시도는 없다.
4. 세 진단이 모두 통과하면 별도 무캡처 회귀 파일럿을 실행한다. Forest
   Full×3, Active-Yaw Sector×1, Adaptive×2, Map1 각 모드×1, 총9회.
5. Full/Adaptive 미완주, 접촉, 증거 누락이 있으면 확대를 멈추고 그 실패를
   분석한다. 단일 상태 시험의 성공을 7맵 100% 완주 검증으로 쓰지 않는다.

## 후보 설계

기존 복구 예산이 소진된 정지 상태에서 목표/진행 episode당 최대1회 실제
inflated-map A*를 새로 실행한다. 실제 장애물은 유지하고 인공 제외 zone은
그 새로운 복구 검색에만 사용하지 않는다. 경로를 inflated LOS로 단축하고,
각 직선 구간을 정지→정지 quintic으로 이어 C2 연속성을 유지한다. 최소
2m XY 진행 또는 목표 도달을 요구하고 knot 수24개로 제한한다.
V5는 horizon4m/일반 LOS였고, V6는 아래의7m/supercover 설계다.
직선 다항식은 구간 밖으로 휘지 않지만 이것만으로 비행을 승인하지 않는다.
기존 `commitTrajectoryCandidate`의 geometry/stop-viability/stopped-release
검사를 모두 통과해야 하며, 실패 시 기존 인증 정지를 유지한다.

`SUPER_CERTIFIED_POLYLINE_RECOVERY` 기본 OFF, raw-cloud CIRI shadow OFF,
기체 반경·inflation·safety margin·맵·미션·타이밍 조건 변경 없음.

## 입력 기록의 한계

`SUPER_PLANNER_FAILURE_CAPTURE_DIR` 설정 시 최대32개 정지 계획을 기록한다.
별도 IO worker, 최대4개 대기 작업. immutable map publication은 공유 포인터로
보존하고 worker에서 직렬화한다. live A*/CIRI/guard queries 자체를 한
publication으로 강제 고정하지는 않는다. 시작/끝 publication version이
같은 프레임만 coherent로 판정한다. CIRI 입력점은 해당 검색 호출의 합집합이며
개별 decomposition 호출 순서를 정확히 재생하는 기능은 아니다.

최적화 재실행이나 원본 실패의 완전 재생과 구분한다. 실패 후보 위치는
비행하지 않은 위치이므로 실제 접촉으로 세지 않는다.
현재 writer는 MINCO 실패 직후 frame을 먼저 제출하므로, 실패9프레임의
`optimizer_init_positions.csv`/초기 시간은 비어 있다. 성공 후 guard 거절
프레임에는 초기값이 있지만 실패 MINCO의 완전 입력 재생을 주장하지 않는다.

## V5 관측 결과 — 기존 실패도 보존

`capture_available`은84.34초에 무진전 종료, 접촉0이다. 실제 zone 단절6회,
fresh connected query1회, 인증 짧은 탈출4회 뒤 소진1회.7982개 수신 odometry
샘플의 독립 감사는 유효하다. 최적화/guard 입력27프레임이 기록됐고
MINCO 실패9개, geometry guard18개(SAFE2개, margin 거부16개)다.
20개 frontend 프레임이 버전 일관성을 유지했고,16개 margin 거부 중3개는
frontend부터 guard까지 같은 immutable publication이었다.

특히 frame17/version117에서 최적화 점은 CIRI 회랑 내부(최대 face violation
-0.02208m)이면서 inflated voxel은 occupied다. 실제 다항식 재계산 오차는
3.6e-15m이며 analytic body clearance는0.24847m다. frame29도 동일 버전에서
같은 불일치를 보인다. frame8은 실제 다항식 점은 free voxel에 있지만
0.06362m 떨어진 raycast voxel centre가 occupied라 거절된다. 따라서 단순한
지도 업데이트 차이만으로 이 세 사례를 설명할 수 없다. 이는 raw-point
CIRI와 inflated/supercover guard의 허용 집합 불일치에 대한 실제 입력 증거다.
MINCO의 soft corridor penalty가 이 사례의 주원인이라는 증거는 아니다.

V5 복구 ON의 control/available/exhausted 각1회는 모두 원래 다음 목표
미도달·접촉0이다. control은 `route_or_version` 사전조건에서, 나머지 둘은
그대로 유지한 geometry certificate에서 거절됐다. 자동 재시도/결과 교체는
없다. `audit_v5.json`은4개 진단 모두 evidence-valid, completion criterion은
false로 구분한다. 따라서 무캡처9회 파일럿과7맵 확대는 아직 시작하지 않았다.

## V6 사전 정의 후속

V5 실패를 그대로 남기고, 새로운 build/install 디렉터리에 V6를 빌드한다.
ROG 바이너리는 변경하지 않은 V5 underlay를 사용한다. 기존 canonical과
V5 설치본을 덮어쓰지 않는다. V6는 복구 검색에서만6-connected A*를 요청하고,
shortcut에는 폐 voxel edge/corner 접촉도 검사하는 supercover prefilter를 쓴다.
검사하지 않은 인접 경로 구간으로 무조건 fallback하던 후보 코드도 제거한다.
검색 horizon은 공통 설정의7m, knot 상한24·진행2m·episode1회 제한은 유지한다.
검색 중 정상적인 맵 publication이 갱신돼도 그 이유만으로 후보를 버리지 않고,
완성된 다항식을 기존 최신-map guard와 stopped-release 계약으로 새로 검사한다.
가드/기체 반경/안전 여유는 완화하지 않는다.

V6 control/available/exhausted 각1회. 마지막 exhausted만 추가 입력 캡처를
켜며, 이 비용은 성능 비교에서 제외한다. 세 사례가 모두 원래 목표에 도달하고,
available/exhausted는 실제 인증 복구 commit이 있어야9회 무캡처 파일럿으로
진행한다. control은 복구가 불필요하게 끝나면 그 사실을 기록한다. 하나라도
실패하면 확대를 보류하고 실제 거절 구간을 보고한다. 입력 캡처 파일은
producer 종료 후에만 분석하며, map bitsets는 원본 SHA-256을 남겨 무손실 gzip
보존한다.

## V6 실제 정지 상태 진단

|사례|원래 다음 목표|접촉 에피소드|진단 경과시간, 시작 준비 포함(s)|실제 다중 구간 인증 commit|
|---|---|---:|---:|---:|
|control: 주입 없음|도달|0|14.02|0, 기존 connected retry로 진행|
|available: zone2개·수평 예산0/4|도달|0|35.14|1|
|exhausted: zone2개·수평 예산4/4|도달|0|63.18|2, 실제2m XY 진행으로 episode 갱신|

`audit_v6.json`의 세 결과는 evidence-valid와 original-goal criterion을 모두
통과했다. exhausted는 첫 인증 복구 이후 다시 정체하고, 진행에 의해 새 episode가
열린 뒤 두 번째 인증 복구로 목표에 도달했다. 동일 상태에서 무제한 재시도한 것이
아니며, 한 번의 복구로 전체 경로가 보장됐다고 표현하지 않는다. 목표는 기존 진단의
1.5m 도달 기준이며 canonical5-waypoint 완주와 구분한다.

세 모드 프로파일·기체 크기·안전 가드는 unchanged. 실제 분기를 실행한 두 사례에서
raw footprint·geometry·stop-viability·stopped release 계약을 거쳐 commit했다.
접촉 판정은 기존 수신 odometry 표본 기준이며 연속 swept-body 보장은 아니다.
원본 run97036 맵을 정확히 재생한 것도 아니다.

세 진단 통과 후 `pilot_v6/`의 사전 정의9회 무캡처 일반 주행 스모크를 시작했다.
별도 controller `topology_polyline_v6_pilot.py`가 세 독립 감사, V6 바이너리,
fault hook/capture OFF를 요구하며 Full/Adaptive 실제 실패나 품질 오류에서 중단한다.
이는 불균등한 소규모 회귀 스모크로, 기존 c41의210회나 논문용 성능 cohort를
교체하지 않는다.

집계 원본은 첫 실제 비행 이후 비적용 Full 전환 빈칸의 숫자 변환에서 중단됐다.
첫 비행의 원본 결과/상태와 controller는 보존한다. 수정된 reader는 non-Adaptive
전환 횟수를NA로 기록하며 완료된1회 입력/품질을 재검증하고 미실행8회만
`pilot_v6_completion/`에서 이어 실행한다. 합본과 현재 상태는 이 continuation
디렉터리를 확인한다. 첫 비행을 새로 돌리거나 성공으로 대체하지 않는다.

## V6 일반 주행 스모크 최종 결과

실제9회=보존 prefix1회+새 continuation8회. `audit_pilot_v6.json`이9개 고유
비행의 입력/로그 해시, 속도·자원·source/recovery 전환 계약과 저장된 모든
실제 odometry의 solid-contact 재계산을 통과했다. 자동 재시도/대체0회다.
일반 스모크에서는 새 다중 구간 복구가0회 발동했다. 따라서 targeted 진단의
실제 commit0/1/2회와 일반 회귀 결과를 따로 해석한다.

|맵|모드|n|완주|접촉 주행|평균 시간(s)|평균 CPU(cores)|CPU(core-s/run)|입력(MiB/s)|Payload(MiB/run)|맵 갱신(ms/frame)|Adaptive Full 전환 합계|
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
|숲|Full|3|3/3|0/3|55.01|0.732|41.930|10.137|560.036|30.191|NA|
|숲|Active-Yaw Sector|1|1/1|0/1|89.24|0.444|40.734|2.435|217.294|9.836|NA|
|숲|Adaptive|2|2/2|0/2|65.59|0.530|36.017|4.695|310.144|13.315|21|
|Map1|Full|1|1/1|0/1|51.63|0.684|36.946|10.991|567.455|26.180|NA|
|Map1|Active-Yaw Sector|1|1/1|0/1|82.54|0.413|34.597|2.724|224.804|9.441|NA|
|Map1|Adaptive|1|1/1|0/1|54.05|0.522|29.272|4.192|226.578|13.507|9|

CPU는 기존 프로토콜의 실험 프로세스 합계이며 컴퓨터 전체 점유율이 아니다.
입력/Payload는 planner ingress의 application payload이고 wire-level network
traffic이 아니다. 원본에는 host CPU·memory/swap·프로세스·스레드 CPU 및
주파수/interval 정보도 보존한다. Map1은 같은 run의3모드이고 숲은 사전 정의
불균등3/1/2회이므로 paired 성능 cohort나 통계적 우위 검정으로 쓰지 않는다.

이번 스모크의 Adaptive/Full 평균 CPU 절감은 숲27.574%, Map1 23.764%,
누적 CPU 절감은14.103%/20.770%다. 숲 시간은 Adaptive65.59s>Full55.01s라
평균 CPU 감소가 누적 CPU 감소로 같은 크기로 이어지지 않는다. 입력률
절감53.682%/61.859%, payload44.621%/60.071%, 맵 갱신55.898%/48.407%.
이 작은 스모크에서30% CPU 목표는 충족하지 않았으며 기존 c41 수치를 바꾸지 않는다.

V6 exhausted 입력31프레임은 geometry SAFE8·margin 거부10·MINCO 실패6·
CIRI 실패7이다. 첫 다중 구간 인증 후보(frame3)는 SAFE·guard coherent,
frontend은 post-search 이미지라 coherent=false로 정확히 구분한다. 두 번째
commit은32 started-frame 한도 뒤여서 입력 캡처가 없다. 로그/odometry로만 확인한다.
390개 원본 내용의 해시가 무손실 압축 뒤 모두 일치했고 약3.0GiB→86MiB로
보존했다. 원본 V5 실패4회와 V6 진단3회, 스모크9회 모두 삭제하지 않는다.

**현재 판정:** 실제 재구성 정지 상태의 복구와 소규모 회귀 검증은 통과했다.
원본 run97036 exact replay, Forest n10 및 새로운 공통7맵 n10은 아직 하지 않았다.
기본OFF·canonical 미승격·논문 c41 결과 고정 유지. 다음은 후보/프로토콜을
동결한 Forest3모드 각10회, 통과 후 별도7맵×3모드×10회 재검증이다.
모든 시뮬레이션과 빌드는 종료됐다.
