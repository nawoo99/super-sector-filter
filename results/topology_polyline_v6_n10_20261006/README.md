# V6 인증 다중 구간 복구 — Forest n10 후 별도7맵 n10 (2026-10-06)

상태는 `status.json`, 맵별 누적 결과는 `summary_by_map.md`를 확인한다.
기존 c41 210회와 V5/V6 진단·9회 스모크는 보존하며 이 캠페인과 섞지 않는다.
기본 canonical 설치본은 승격하지 않는다.

## 사전 정의 프로토콜

- 후보: `/root/super_ws/forest_liveness_trial_v6_20261006/install`, 앞서 실제
  진단/스모크에서 검증한 Full/Adaptive 바이너리 해시 그대로, 재빌드 없음.
- 1단계: Forest Full·기본 Active-Yaw Sector·Adaptive 각각10회, 총30회.
- 1단계 gate: Full/Adaptive는 각10회 모두 완주·접촉0, 세 모드 모두 입력·
  속도·자원·source/recovery 계약과 실제 odometry의 독립 solid 감사 유효.
  Sector의 접촉/미완주는 결과로 남기고 성공으로 바꾸지 않는다.
- gate 통과 시만2단계: Map1–5(`m05r2` 포함)·Urban·Forest의 세 모드 각10회,
  총210회. Forest 파일럿30회와 별도 cohort이며 합쳐서 Forest n20으로 쓰지 않는다.
- 개별 물리 비행마다 별도 child를 실행·감사한 후 다음 비행을 시작한다.
  Full/Adaptive 실제 실패 또는 어떤 모드의 증거/자원/속도 오류든 즉시 중단한다.
  자동 재시도·선택적 결과 대체·중단된 run의 암묵적 재개는 없다.
- mode order는 맵/반복마다 cyclic rotation. 계획된240개 고유 식별자는
  `protocol.json`에 실행 전 저장했다. Forest run99401–99410,
  별도7맵 run99501–99570. 모드별로 같은 repeat/run을 구분한다.
- `SUPER_CERTIFIED_POLYLINE_RECOVERY=1`은 이 후보 실행에서만 사용한다.
  failure-input capture와 test fault hooks는OFF. 맵·미션·안전 가드·기체 크기·
  LiDAR·CPU 계측/최적화 옵션은9회 스모크와 동일하다.
- 총 미션시간 상한 없음. 기존 관측 전용60초/2cm 무진전 종료는 유지하며,
  이 관측은 planner에 입력하지 않는다.

## 기록과 검증

각 비행의 `raw.csv`, `summary.json`, 원본 stack/mission log, performance,
cgroup/process CPU·host CPU·memory/swap, odometry 및 solid audit를 보존한다.
추가 `independent_solid_replay.json`은 모든 저장 odometry를 실제 정적 solids와
다시 계산한다. 이것은 수신 표본 감사이지 continuous swept-body 보장은 아니다.
캠페인은 CPU cores/core-s, ingress MiB/s·MiB/run, map ms/frame, Adaptive Full
전환 수, topology/disconnect/exhaustion/polyline 횟수를 맵/모드/cohort별로 집계한다.
완주 전용 시간과 실패/종료를 포함한 관측시간은 따로 표시한다.

706개 입력 해시를 동결하고 매 비행 전 다시 검사한다. 이전 세 targeted 진단과
9개 스모크의 실제 해시·품질을 재검증해 admission을 통과했다. 새 controller의
12개 orchestration fixture는240회 중복 방지, 실패 즉시 다음 비행 차단,
Sector 실패 보존, 상대 artifact 경로 해석을 검사했다. 이는 물리 비행 결과가 아니다.

## 예상 소요시간

최근 V6 주행시간과 약30초/비행의 준비·수집·종료 비용을 포함한 추정이다.
Forest30회 약50–70분, 공통7맵210회 약5–6시간, 집계 포함 총6–7시간.
실제 오류 발생 시 원인 분석/수정 시간은 별도이며 완료 시각 보장이 아니다.

준비 상태는READY, 실제 비행0회로 기록했다. 실행/완료/중단은 이후 상태를 볼 것.

실행은 source의 `topology_polyline_v6_campaign.py`를 사용한다. 새 결과 경로에서
`--background`는 프로토콜 생성 후 분리된 로컬 워커를 시작한다. 이미 준비한
READY 경로는 `--execute`로만 한 번 시작할 수 있고, 완료/중단 결과를 덮어쓰지 않는다.
이 워커는 이메일·외부 알림 발송·canonical 승격·Git push를 하지 않는다.
