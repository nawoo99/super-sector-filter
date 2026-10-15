# G1–G5: 지름1m, 최소1m 간격 제약을 제거한 추가 정적 원기둥 맵

## 1. 요청과 완료 범위

마지막 요청의 **일단 맵만 만들라**는 지시에 따라 생성·오프라인 기하 검증·
통계·그림·mirror까지만 수행했다. 비행0회다. 맵별 Full/Sector/Adaptive 각5회,
총75회는 후속 계획이며 이번에 시작하지 않는다. 기존 Normal/결과와 planner/
알고리즘/sensor/FSM/launch/binary는 변경하지 않았다. 새 코드는 offline
generator와 그 test뿐이다. Full/Adaptive 성공 또는 안전우위 확인 맵이 아니다.

## 2. 공통 설정과 배치

- 각410개, **지름1.00m**, 높이3.00m의 항상 존재하는 정적 원기둥.
- XY[-32,32]m, 면적4096m², 밀도0.10009765625개/m²(100m²당10.0098개).
- 비겹침 원기둥 XY 단면 합계 면적비7.8617%.
- 전체 원기둥이 범위 안에 있도록 중심은[-31.5,31.5]m에서 생성한다.
- loop24: (0,0)→(24,24)→(-24,24)→(-24,-24)→(24,-24)→(0,0).
- seed1 simulator YAML을 그대로 복사해 **pcd_name만 변경**했다. 초기 위치
  (0,0,1.5), yaw0,360도 장치, LiDAR10Hz/15m 등은 동일하다.

개수·지름·높이·면적은5맵에서 같고 난수 배치만 다르다. 밀도를 증가시키는
5단계 맵이 아니라 동일 조건의5개 서로 다른 배치다. 균일 난수 후보를 순서대로
수락하는 nonoverlap 방식으로 생성하고, 좌표6자리 반올림 후 비겹침을 검사한다.

기존 Normal과는 지름·좌표도 달라졌으므로 Normal 대비 결과 차이를 간격
제약 하나의 인과 효과라고 주장하지 않는다. 모드 비교는 동일한 새 맵 안에서 한다.

강제 최소 표면 간격은0m(비겹침)이며 기존1m 조건은 제거했다. 기존 시작점3m/
waypoint2.5m 넓은 보호 공간, nominal route 주변2m 비움, wall/baffle/corner-post
구조는 적용하지 않았다. 모든 틈이 통과 가능할 필요는 없지만, 미션 endpoint와
전체 각 leg의 안전 여유를 갖춘 연결은 offline checker로 확인한다.

## 3. 실제 간격 분포

간격은 **장애물 표면 사이 거리**다. 최근접 분포는 원기둥별410개 nearest gap이고,
서로 최근접인 pair는 양 끝 원기둥에서 각각 집계된다(고유 pair 수가 아님).

| 맵 | 실제 map name | 최소 표면 간격(m) | 최근접 평균(m) | p10(m) | 중앙값(m) | p90(m) | 최근접<1m 원기둥 수 |
|---|---|---:|---:|---:|---:|---:|---:|
| G1 | gapfree_d1_m01 | 0.004059 | 0.8731 | 0.1589 | 0.7539 | 1.7503 | 273/410 |
| G2 | gapfree_d1_m02 | 0.001694 | 0.8679 | 0.1311 | 0.7191 | 1.8360 | 260/410 |
| G3 | gapfree_d1_m03 | 0.002173 | 0.8417 | 0.1072 | 0.7577 | 1.7350 | 260/410 |
| G4 | gapfree_d1_m04 | 0.001629 | 0.8002 | 0.1080 | 0.6242 | 1.7753 | 292/410 |
| G5 | gapfree_d1_m05 | 0.001135 | 0.8915 | 0.1875 | 0.7417 | 1.7901 | 266/410 |

실제 최소값은 약1.1~4.1mm다. 이를 새 강제 spacing 설정으로 해석하지 않는다.
표준편차, p0/p5/p10/p25/p50/p75/p90/p95/p100,410개 원시 nearest gap,
[0,.1)/[.1,.25)/[.25,.5)/[.5,1)/[1,2)/[2,∞) 구간 빈도도 manifest에 있다.
맵별 nearest_gaps.csv에 cylinder index/XY/r와 최근접 간격을 저장했다.

## 4. 연결 경로와 기하 후보 선택

현재 모델 body radius0.20m와 **body 바깥 안전 여유0.35m 이상**을 기준으로
검사한다. 기존 offline checker의0.10m grid/node body margin0.45m로 A*를
수행한 뒤 모든 압축 연속 XY 선분의 여유를 analytic cylinder와 정확히 검사했다.
z1.5m는 원기둥 z0..3m 안에 있어 위로 넘는 경로가 아니다. 이 offline A*와
생성 경로는 ROS planner에 연결하지 않는다. 동역학/제동/v7 완주 보장이 아니다.

| 맵 | 연속 선분 최소 body 여유(m) | 기하 경로 총 길이(m) | 기하 후보 수 | 수락 난수 seed |
|---|---:|---:|---:|---:|
| G1 | 0.450865 | 233.32 | 14 | 2039091840 |
| G2 | 0.448600 | 228.52 | 5 | 2030091814 |
| G3 | 0.450389 | 229.10 | 1 | 2026091803 |
| G4 | 0.450500 | 229.19 | 18 | 2043091855 |
| G5 | 0.449710 | 234.63 | 13 | 2038091841 |

base seed2026091801..2026091805, 다음 기하 후보마다1000003을 더한다.
총51개 proposal layout 중5개 수락,46개 기하 탈락. 탈락 seed/사유와 수락
attempt 모두 공개했다. endpoint 검사는 grid node의 보수적0.45m margin을 쓴다.
비행 결과 기반 선별이 아니라 **기하학적으로 가능한 환경으로 조건부 선별**이다.
위 길이를 실제 비행 경로 길이나 미션 시간으로 사용하지 않는다.

## 5. 파일과 검증

runtime package: `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/`.

- `scripts/gen_gapfree_d1_maps.py`, `test/test_gen_gapfree_d1_maps.py`.
- `config/gapfree_d1_m01.yaml`부터`gapfree_d1_m05.yaml`.
- `pcd/seed_maps/gapfree_d1_mNN.pcd`와`gapfree_d1_mNN_cylinders.csv`.
- 새 YAML5개만 install/share/perfect_drone_sim/config에도 복사. 빌드하지 않았다.
- mirror: `perfect_drone_sim_scripts/`, `perfect_drone_sim_test/`,
  `perfect_drone_sim_config/`, `perfect_drone_sim_pcd/seed_maps/`.

결과: `results/gapfree_d1_maps_20260918/`의 manifest.json/summary.csv,
맵별 cylinders.csv/nearest_gaps.csv/routes.json. source/mirror/install 및 generator/
helper 해시와 기하 경로·통계·비행0회 상태를 저장했다.

[배치와 오프라인 경로 그림](../results/gapfree_d1_maps_20260918/map_overview.png),
[최근접 간격 누적분포](../results/gapfree_d1_maps_20260918/nearest_gap_cdf.png).

Python11검사 통과: 재현성, 비겹침/범위/지름/유한값,1m 조건 제거, 분포·밀도,
선분 전체 여유,5개 실제 맵의 해시·config 동일성. 각 PCD800730 points.
추가 독립 PCD 검사도5/5 통과: 실제 행 수/헤더,유한 XYZI,z0..3, 반경 오차
최대5.90e-7m(<1e-6m). 기존 C25 동결 input/evidence1396개는 생성 전후 변경0.
오프라인 검증 기록은 결과 폴더의 verification.json에도 저장했다.

생성기는 기존 source/mirror/install/output가 있으면 덮어쓰기를 거부한다.
후속 비행 runner에는 새 map identity/geometry/계측 연결을 준비해야 한다.
Normal 전용 runner에 이름만 바꿔 넣고 인증된 것으로 간주하지 않는다.

## 6. 기존 캠페인과 분리

C25 iteration02는2026-09-17 17:07KST COMPLETE, 독립 OFF300 및 ON15를 완료했다.
OFF Full/Adaptive각100/100완주·접촉0. Sector100/100완주이나 N5 r01_run22004에
접촉1관측. 기존 자료를 이번 맵 실적으로 가져오지 않는다. 한 건 차이만으로
통계적 안전우위나 모집단100% 보장을 주장하지 않는다. GitHub push는 하지 않는다.
