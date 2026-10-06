# Forest 정지 상태 복구 분기 시험 — 2026-10-06

## 결론

**완주 결함은 아직 해결되지 않았다. 대규모 캠페인은 실행하지 않았다.**
기존 c41 Full69/70·Adaptive70/70, 맵과 프로파일은 그대로 보존한다.
현재 작업 소스는 실험 후보 V4지만 기본 canonical 설치본/런처는 승격하지 않았다.

원본 run97036 정지 위치에서 새로운 LiDAR 맵을 만들고, 실제 A*·CIRI·MINCO·
안전 가드를 사용하는 별도 분기 시험을 총6회 실행했다. 가상 zone/예산 주입은
명시적 test-only 환경 변수로만 수행한다. A* 결과나 안전 인증을 강제로
성공시키지 않는다. 당시 ROG map/raw scan/CIRI/MINCO 스냅샷이 없어 원본과
**동일 상태 재생이 아니며**, 전체5-waypoint 미션 시험도 아니다.

## 보존한 V3 결과

|조건|원래 다음 목표 도달|접촉 episode|전체 진단 관측시간(s)|실제 관측|
|---|---|---:|---:|---|
|무주입 대조|예|0|12.32|local escape 없이 도달|
|zone2개, 수평 예산 남음|아니오|0|81.14|인증 수평 이동4회 후 재정체|
|zone2개, 원본처럼 예산 소진|아니오|0|9.84|3초 안정 정지 후 **다른 목표**로 재개|

마지막 조건의 `passed=true`는 정지·새 목표에 대한 latch 해제 시험의 통과다.
원래 목표 완주를 뜻하지 않는다. `source_v3/`는 후속 코드 수정 전에 보존한
소스이며, 별도 V3 integrated Full 실행 파일 해시도 그대로 유지됐다.
V4 빌드 캐시의 기존 설치 경로를 발견해 중단·재설정하는 과정에서 V3의
planner 라이브러리/FSM은 바뀌었다. 따라서 V3 prefix를 전체 캠페인 runtime으로
재사용하면 안 된다. 실제 진단에 쓴 self-contained Full 실행 파일과 결과는
보존됐고 V4는 실제 별도 설치 prefix/실행 파일 해시를 확인했다.

## V4 결과 — 연결 복구 후 정상 계획을 한 번 먼저 시도

반사실 query에서 연결이 회복되면 그 trial guide를 넘기지 않고, 같은 locked
map/flags/horizon에서 새로운 실제 A* query를 한 번 수행하도록 수정했다.
그 출력만 기존 CIRI/MINCO와 trajectory/stop-viability 인증에 전달한다.
한 번이라는 예산은 검색 상태 clear·짧은 이동 성공으로 초기화하지 않는다.
기존 수평4회/수직 예산, 안전 여유, 센싱·맵·미션은 바꾸지 않았다.

|조건(각1회)|원래 다음 목표 도달|접촉 episode|진단 관측시간(s)|fresh A* query|수평 이동 commit|
|---|---|---:|---:|---:|---:|
|무주입 대조|아니오|0|85.09|1|4|
|zone2개, 수평 예산 남음|아니오|0|75.47|1|4|
|zone2개, 원본처럼 예산 소진|아니오|0|64.39|1|0|

위 시간에는 시작 준비4초와 마지막 **60초/2cm 무진전 관찰**이 포함된다.
이는 주행시간 비교값이나 총 미션 제한시간이 아니다. 시험별 binary/config/
geometry/source SHA, 전체 odometry CSV, 접촉 감사와 자원(CPU·전체 host CPU·
RAM/swap) 관측, stack log를 각 폴더에 보존했다.

V4는 세 조건 모두 실제 `CONNECTED_RETRY`가 발동했고 A*는
`REACH_HORIZON`을 반환했다. 이후 최적화된 EXP는 생성됐으나 최종 가드가
EXP의 `CLEARANCE_MARGIN`을 거부했다. 예산 소진 조건에서는 시작 위치에
계속 안전하게 정지했다. **연결된 guide ≠ 최적화 후 인증 가능한 trajectory**다.

예시 `v4_exhausted/stack.log:463–479`:

1. 실제 A*가 연결된 guide를 찾음.
2. `GenerateExpTrajectory SUCCESS`.
3. EXP 후보가 `[8.451,19.100,2.658]`에서 margin 거부.
4. 남은 복구 예산이 없어 `RECOVERY_EXHAUSTED`로 정지 유지.

V4 대조 실패를 V3 대비 확정적인 코드 회귀라고 단정하지 않는다. 같은
정적 맵/위치여도 실제 scan/map/optimizer 입력이 동일하게 재생되지 않았다.
그러나 이번 후보가 이 밀집 정지 상태를 안정적으로 복구한다는 주장은
반증됐으므로 승격·확장시험 gate를 통과시킬 수 없다.

## 검증과 확장 gate

CTest5/5, 관련 source-contract pytest24/24 및 exact-production ASan/UBSan
fixture가 통과했다. Independent audit는 여섯 시험 모두 입력·기록·접촉
증거가 유효함을 확인했다. **실험 실패와 자료 무효를 구분**하기 위해
`evidence_valid`와 `criterion_met`를 별도 기록한다.

`audit_v3.json`, `audit_v4.json`을 볼 것. V4의 세 criterion은 모두 false다.
준비된 `topology_liveness_v4_campaign.py`가 이 조건에서 실제로 실행을
거부함을 확인했다. Forest30비행(모드당10회), 이어 새7맵210비행 계획은
**미실행**이며 기존 결과를 대체하지 않는다.

현재 프로세스는 모두 종료했다. 다음 작업은 실패 순간 ROG snapshot,
A* guide, CIRI polytope, MINCO 후보·경계 조건을 묶어 저장해 raw-point
회랑/soft optimizer/voxel guard 간 차이를 분리하는 것이다. 해당 입력으로
가드를 통과하는 다중 구간 우회·후퇴 후보를 설계·검증해야 하며, 단순
안전 여유 완화나 탈출 횟수 증가로 완주율을 맞추지 않는다.

## 읽기 전용 재감사

```bash
source /opt/ros/humble/setup.bash
python3 /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/audit_forest_stopped_topology_diagnostic.py \
  /root/super-sector-filter/results/topology_stopped_diagnostic_20261006/control \
  /root/super-sector-filter/results/topology_stopped_diagnostic_20261006/available \
  /root/super-sector-filter/results/topology_stopped_diagnostic_20261006/exhausted \
  --source-bundle /root/super-sector-filter/results/topology_stopped_diagnostic_20261006/source_v3
```

실제 실패 criterion이 있으므로 종료코드1은 예상된 판정이다. 로그/입력
손상은 `evidence_errors`로 별도 표시된다. V4 세 폴더도 동일 스크립트로
재감사할 수 있다(`--source-bundle` 불필요).
