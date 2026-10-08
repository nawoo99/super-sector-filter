# SUPER 세모드 시뮬레이션 동결 결과

2026년10월8일 기준으로 V6의 7맵 × 3모드 × 각10회인 본실험210회를 별도 버전으로 동결한다. Full과Adaptive는 각각70/70 무접촉 완주, Active-Yaw Sector는68/70 완주·접촉 주행2/70·무접촉 완주67/70이다. CPU 목표값 추가 튜닝과Sector 비교군 개선은 종료한다. 기존 실패를 제외하거나 성공으로 대체하지 않는다.

이 동결은 결과 자료의 확정이며 기본 실행본의 교체가 아니다. 시험에 사용한 별도 V6 설치본과 기존 canonical 설치본을 구분한다. 이전 c41 210회 자료와 중단된 원본113회 상태도 그대로 보존하며, 서로 다른 버전의 결과를 합산하지 않는다. 별도 숲 사전시험30회는 본실험210회와 분리한다.

## 먼저 읽을 파일

- [최종 결과 표](summary_final.md): 7맵별 결과, 맵1~5 통합 평균, 도심지·숲 개별 평균, CPU와입력량 정의.
- [Sector 실패와 실제 복구 분석](failure_analysis.md): 실제 기록과 인과 추정을 구분한 사례 설명.
- [본실험210회 원자료 표](main_210.csv), [별도 숲 사전시험30회](forest_gate_30.csv).
- [독립 Adaptive 전환 감사](adaptive_contract_audit.json): 본실험509회와 사전시험109회 전환의 실제 로그 순서·센서 프레임·맵·경로·복귀 대조.
- [생성 완료 기록](build_complete.json), [원본 해시 목록](source_manifest.json), `freeze_manifest.json`: SHA-256으로 결과와 원본 변경을 탐지한다.

원본240회 = 보존113회 + 미실행분의 새127회이며 물리 재시도는0회다. 원본 전체 로그와odometry는 두 기존 캠페인 디렉터리에 남는다. GitHub에는 동결 표·분석·그림·해시 목록과생성 코드를 올리며, 약1.1GiB의 원본 로그 전체를 이 작은 공유 묶음에 복제하지 않는다.

## 그림

|파일|내용|
|---|---|
|`compute_comparison.png`와PDF|맵1~5·도심지·숲별 Full 정규화 CPU·입력률·입력량·맵 계산시간|
|`case_forest_r03.png`와PDF|Full에서 실제 V6 복구를 사용하고 완주한 회차의3모드 궤적|
|`case_forest_r04.png`와PDF|Sector 접촉 후 정체 종료 회차|
|`case_forest_r05.png`와PDF|Sector 후보 생성 후 맵 버전 변경으로 출발하지 못한 회차|
|`case_map1_r06.png`와PDF|Sector 접촉 후 전체 목표에 도착한 회차|

회색 장애물은 실제 정적 geometry이고, 선은 수신 odometry의 위치다. 센서 패널은 실제 로그에 남은 순간 수평 aperture metadata이며 Full360°와Sector90°를 나타낸다. 누적 시야, yaw 방향, occlusion, 장애물별 관측 여부나planner 내부 맵을 복원한 그림이 아니다. 같은 맵·회차의3모드는 각각 별도 비행이며 동일 내부 상태를 재생한 반사실 실험이 아니다.

속도 패널은odometry가 보고한 velocity의 크기다. 특히 숲 Sector4회차는 접촉으로 위치가 정체한 뒤에도 보고 velocity가 약3.9m/s라서, 위치 차분에 의한 이동속도로 해석하지 않는다. 그림은 설명용 다운샘플링이며 접촉 판정은 전체 저장 수신 표본을 사용했다.

## 결과를 사용할 때 지킬 범위

논문에는 다음처럼 쓸 수 있다.

> 평가한7개 정적 시뮬레이션 맵에서 Adaptive는 Full과동일하게70회 모두 무접촉 완주했다. Active-Yaw Sector에서는 미완주2회와접촉 주행2회가 관측됐다. Adaptive는 필요한 구간에서 Full 관측·맵 갱신·새 인증 경로 확보 후Sector로 복귀하면서 처리 비용을 줄였다.

이 결과를 모든 환경의100% 안전 보장, 통계적으로 확정된 안전성 우위, 또는 모든Sector 실패가 시야 제한만으로 발생했다는 결론으로 확대하지 않는다. 숲5회차에는 공통 맵 freshness gate와episode당1회 복구 예산의 진행성 민감도가 관여했다. 원본 과거 Full 실패의 정확한 내부 맵 재생이나 공통 planner의 모든 진행성 결함 해결을 주장하지 않는다.

## 검증 명령

```bash
/usr/bin/python3 -s /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/freeze_v6_results.py verify \
  --output /root/super-sector-filter/results/v6_frozen_20261008
```

분석 생성에는 기존 시스템 NumPy1.21.5와Matplotlib3.5.1을 사용했다. 일반 사용자-site의NumPy2와시스템Matplotlib1.x ABI 혼용을 피하도록 `-s`를 사용하며, 시뮬레이션 환경 패키지는 변경하지 않았다. 부분 생성본은 별도 분석 초안 디렉터리에 보존했다. 재생성은 새 출력 경로에만 허용하며, 봉인된 결과를 덮어쓰거나 재봉인하지 않는다.
