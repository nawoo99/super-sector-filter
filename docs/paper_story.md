# 논문 스토리 — JKICS v7 (2026-08-05, seed11 raw/adaptive 30회 접촉 재검증)

> **v6→v7 변경 이유:** seed11의 raw-direct 1/10 대 adaptive 0/10은 실행 변동에 비해 표본이
> 작아 안전성 결론으로 쓰지 않고, 두 모드를 회차별 교차 순서로 각각 30회 재실행했다. adaptive
> 접촉이 14/30에서 재현됐으므로 “충돌 0” 표현을 폐기한다. v7의 seed11 핵심 결과는 데이터
> **66.2% 저감**, mapping **51.3% 단축**, 접촉 표시 런 raw **8/30**·adaptive **14/30**이며,
> 접촉 차이는 통계적으로 유의하지 않았다(Fisher 양측 `p=0.180`). 그러나 방향도 adaptive가
> 불리하므로 “안전성 저하 징후 미관찰”이라는 표현까지 철회한다.

> **2026-08-04 baseline 정정:** 기존 `full`은 raw LiDAR를 직접 쓰는 원 논문형 baseline이
> 아니라 Python에서 100% 점을 복사·재발행한 `relay-full`이었다. seed11 입력 경로 대조실험을
> 추가해 둘을 분리했으며, 논문 직접 비교 baseline은 앞으로 `raw-direct`로 표기한다.

> **v5→v6 변경 이유:** seed별 간격과 반경을 동시에 바꾸던 설계를 폐기하고, seed1~10의 장애물
> 표면 간 최소 간격을 1.00 m로 고정한 뒤 반경만 0.150~0.650 m로 변화시켰다. 따라서 v5 결과는
> 현재 지형의 근거로 사용하지 않으며, 아래 표와 결론은 `native_seed1_11_v6_n5.csv`의 새 165회
> 캠페인만 사용한다.

## 1. 연구 질문과 제안 기법

360° LiDAR 점군을 원격 모니터링·지도 공유에 그대로 전송하면 링크 대역폭을 크게 소모한다.
본 연구는 SUPER 앞단에서 수평 ±60° 점군만 유지하는 태스크 지향 필터를 비교한다.

- **full (`relay-full`):** 360° 점을 모두 유지하지만 Python 복사·재발행 경로를 거친다.
- **sector:** 기체 기수 기준 고정 ±60°.
- **adaptive:** 속도 방향 기준 ±60°. 회전 중 기수와 실제 진행방향의 불일치를 보상한다.

seed11 대조실험의 **raw-direct**만 `/cloud_registered`를 SUPER에 직접 연결하므로 원본 입력
baseline에 해당한다.

메인 플랫폼은 SUPER 원 논문과 같은 MARSIM perfect-drone 환경이다. PerfectDrone은 계획 명령을
그대로 상태에 반영하므로 결과는 컨트롤러 추종오차가 아니라 센싱·맵핑·계획 파이프라인을 평가한다.

## 2. v7 실험 조건

### 2.1 seed1~10

- 64×64 m 필드, 원통 장애물 410개, `(±24, ±24)` 네 코너 루프.
- 모든 지도에서 최근접 장애물 **표면 간격 ≥1.00 m**.
- seed1~2 반경 0.150 m, seed3~4 0.275 m, seed5~6 0.400 m,
  seed7~8 0.525 m, seed9~10 0.650 m.
- SUPER `robot_r=0.20 m`, `max_vel=3.0 m/s`, ROG inflation 명목 0.30 m.
- 각 seed·모드 5회: 10맵×3모드×5회 = 150회.

1.00 m는 장애물 표면 사이의 생성 제약이지 드론 안전거리나 충돌 판정값이 아니다.
충돌 모니터는 드론 중심과 최신 LiDAR 표면점의 거리가 0.20 m 미만인 런을 접촉 런으로 표시한다.

### 2.2 seed11

SUPER 공개 저장소의 `random_map_2_26609.pcd` dense-forest 예제 회랑이다. 본 논문의 1080회
평가는 **110×20 m 무작위 숲 지도 60개(밀도 6단계×seed 10개)×최고속도 1~18 m/s**였고
최대가속도는 20 m/s²였다. 따라서 seed11 하나를 “논문 1080회 원본 환경”으로 동일시하지
않는다. 이 지도는 공개 MARSIM 예제와 현 프로젝트 필터를 같은 장애물 배치에서 비교하는
외부지도 control이다.

입력 경로 효과를 분리한 선행 실험은 현재 3 m/s 설정에서 `raw-direct / relay-full / sector /
adaptive`를 각 10회 실행했다. 안전성 본 실험은 그 결과와 분리해 `raw-direct / adaptive`만
각 30회, 회차마다 실행 순서를 번갈아 배치했다. 100 Hz odometry와 최신 원본 cloud 거리뿐 아니라
정적 PCD 점을 드론 반경 0.20 m로 팽창한 보조 고체 판정을 추가했다. ROG occupied voxel 출력을
두 모드 모두 2 Hz로 켜고, 접촉 순간 위치·속도·local 원본 cloud·ROG 점유맵·A* frontend path·
committed trajectory·position command·local PCD를 런별 JSON에 기록했다. 이 시각화/계측 부하는
선행 발행-off 실험과 실행 타이밍이 달라질 수 있으므로 본 60회 안에서만 비교한다.

별도로 공개 저장소 예제형 `raw-direct, max_vel=8 m/s`도 10회 실행했지만, 이는 논문의
60-map 프로토콜 재현이 아니다.

## 3. 헤드라인 결과

### 3.1 seed1~10: 150회

| 지표 | full (`relay-full`) | sector | **adaptive** |
|---|---:|---:|---:|
| 완주 | **49/50 (98%)** | **50/50 (100%)** | **49/50 (98%)** |
| 접촉 표시 런 | **15/50 (30%)** | **8/50 (16%)** | **7/50 (14%)** |
| 평균 점/frame | 23,820 | 7,217 (**69.7%↓**) | 7,034 (**70.5%↓**) |
| 평균 kept 비율 | 100.0% | 31.15% | 30.44% |
| raycast ms/frame | 1.430 | 0.478 (**66.6%↓**) | 0.473 (**66.9%↓**) |
| ROG 총 mapping ms/frame | 5.218 | 1.935 (**62.9%↓**) | 1.975 (**62.1%↓**) |
| fsm CPU | 86.5% | 85.0% | 85.3% |
| 필터 CPU | 7.9% | 8.3% | 8.6% |
| 완주 런 평균 미션시간 | 79.05 s | 78.74 s | 78.82 s |

핵심 결론은 **adaptive가 약 70.5%의 점군을 줄이면서 세 모드 중 가장 낮은 접촉 런 비율
(14%)을 기록했다**는 것이다. 다만 full 30% 대비 표본은 각각 50회이며, 독립 seed와 반복 런을
혼합한 기술통계이므로 통계적 우월성을 확정하거나 “안전 보장”으로 표현하지 않는다. sector와
adaptive의 16% 대 14% 차이도 작아서 현재 표본만으로 차이를 주장하지 않는다.

반경 단계가 커질수록 접촉이 집중됐다. seed1~3은 전 모드 0건, seed4~6은 full에서만 4개 런,
seed7~8은 full 3·sector 2·adaptive 1개 런, seed9~10은 full 8·sector 6·adaptive 6개 런이었다.
따라서 v6는 필터만의 문제가 아니라 큰 장애물이 만드는 경로 차단과 SUPER의 잔여 계획 변동성을
드러낸 스트레스 캠페인이다.

### 3.2 seed11 안전성 본 실험: raw-direct/adaptive 각 30회

| 지표 | raw-direct | **adaptive** |
|---|---:|---:|
| 완주 | **30/30 (100%)** | **29/30 (96.7%)** |
| live-cloud 접촉 표시 런 | **8/30 (26.7%)** | **14/30 (46.7%)** |
| 접촉률 Wilson 95% CI | 14.2~44.4% | 30.2~63.9% |
| PCD 고체 보조판정 접촉 런 | 11/30 | 14/30 |
| 평균 점/frame | 65,436 | 22,136 (**66.2%↓**) |
| kept | — | 34.22% |
| raycast ms/frame | 5.188 | 2.046 (**60.6%↓**) |
| ROG 총 mapping ms/frame | 13.365 | 6.514 (**51.3%↓**) |
| 실효 ROG 갱신률 | 2.92 Hz | 2.98 Hz (**2.2%↑**) |
| fsm CPU | 91.8% | 90.1% |
| Python 필터 CPU | — | 8.9% |
| 계측 monitor CPU | 54.7% | 57.2% |
| 완주 런 평균 미션시간 | 73.47 s | 73.37 s |

adaptive 접촉은 run 2·5·7·8·9·10·14·16·18·20·22·24·28·30에서 반복 재현됐다. 따라서
선행 0/10은 **작은 표본과 실행 변동 때문에 접촉을 관찰하지 못한 결과**다. raw도 run
6·9·14·15·17·23·25·28에서 재현됐다. adaptive의 접촉 런 비율은 오히려 높았지만 Fisher 양측
검정 `p=0.180`이고 Wilson 구간이 겹쳐 통계적 열등성을 확정할 수 없다. 완주도 30/30 대
29/30(`p=1.000`)이다. 그러므로 현재 근거는 **adaptive의 안전 동등성을 입증하지 못했으며,
불리한 방향의 관찰 신호가 있다**고 표현한다. 충돌 0·안전성 무손실·저하 징후 미관찰은 모두
주장하지 않는다.

순서를 나눠 보면 raw-first 15쌍에서 raw/adaptive 접촉 런은 5/15·3/15였지만,
adaptive-first 15쌍에서는 3/15·11/15였다. 같은 run 번호를 block으로 본 discordant pair는
raw-only 5, adaptive-only 11이고 paired McNemar exact `p=0.210`이다. 총 실행 순서는 균형화됐지만
이 강한 순서 상호작용은 결과가 cold start·scheduling·planner 초기 분기에 민감하다는 뜻이다.
따라서 8 대 14를 adaptive 자체의 보편적 인과효과로 단정하지 않는다.

PCD 판정은 정적 occupied sample을 반경 0.20 m로 팽창한 보조 지표다. live 판정과 비교하면
PCD-only와 live-only 런이 모두 나왔다. renderer가 순간 생성한 표면점과 정적 PCD sample의
차이 때문에 false positive/negative가 모두 가능해 어느 한쪽을 물리 ground truth로 쓰지 않는다.
총 89개 접촉 전이에 위치·속도·근접점·local raw cloud·static PCD·ROG occupied map·A* frontend
path·committed trajectory·position command를 보존했다. 이 중 시작 0.2~1.4초의 5개 전이는 첫
2 Hz 점유맵 발행 전이라 point count 0의 빈 map 상태가 기록됐고 나머지 84개는 local 점유 voxel을
포함한다. 계측 monitor가 코어 하나의 약 55~57%를 사용했고 ROG 시각화 발행도 추가했으므로
절대 CPU·갱신률은 선행 캠페인과 직접 비교하지 않고 두 모드의 동일 계측 조건에서만 해석한다.

### 3.3 seed11 입력경로 대조: raw-direct/relay-full 각 10회

선행 input-path control에서 raw-direct와 relay-full은 같은 3 m/s 설정과 같은 입력 점수를
사용했다. relay-full은 Python 전체 cloud 복사·직렬화·재발행 때문에 필터 CPU 10.3%가 추가됐고,
mapping은 13.405→14.241 ms/frame으로 6.2% 느려졌으며 실효 갱신률은 3.26→2.60 Hz로
20.4% 낮아졌다. 이 n=10 control은 기존 `full`이 원 논문형 baseline이 아님을 보이는 용도로만
유지하며, 안전성 헤드라인에는 사용하지 않는다.

### 3.4 공개 upstream 예제형 control: raw-direct 8 m/s×10회

| 완주 | 접촉 표시 런 | 평균 최고속도 | 완주 미션시간 | 실효 ROG 갱신률 |
|---:|---:|---:|---:|---:|
| **7/10** | **10/10** | 7.96 m/s | 39.38 s | 4.38 Hz |

이 control은 upstream 예제의 raw topic·8 m/s 프로파일을 현 ROS2 포트에서 실행한 것이다. 논문은
별도로 생성한 60개 지도, 속도 1~18 m/s, 최대가속도 20 m/s²를 사용했으므로 이 단일
예제 결과로 논문의 1080회 0충돌을 재현했다거나 반박했다고 주장하지 않는다.

## 4. 충돌·미완주 해석

v6 메인 165회 캠페인의 세 미완주는 seed9 full run2(2/5 waypoint, 300 s), seed10 adaptive
run4(2/5, 300 s), seed11 full run2(0/2, 90 s)다. v7 seed11 본 실험에서는 raw-direct 30회가
모두 완주했고 adaptive run30이 0/2 waypoint에서 90 s timeout됐다. 이 런은 접촉 뒤 정체하며
full-open 상태가 유지돼 kept가 85.5%까지 상승했다. 선행 control에서는 relay-full 1회와
upstream 예제형 raw-direct 3회가 미완주했다. 단순 부팅 실패가 아니라 경로상
정체한 런이 포함되므로 완주율에서 제외하거나 “인프라 오류”로 재분류하지 않는다.

이전 1회 정밀 bag 분석에서는 실제 접촉 7건 모두 약 2.93~3.00 m/s에서 발생했고, 몸체 여유
1 m에서 접촉까지 0.34~0.38 s뿐이었다. 두 adaptive 충돌 대상은 속도 콘 안에 100% 포함돼 있어
섹터 누락이 아니었다. 현재 설정은 미관측 영역을 통과 가능하게 취급하고, 큰 full 클라우드는 실제
ROG 갱신률을 낮춘다. 가장 타당한 공통 메커니즘은 **가림/미관측 공간으로 경로 생성 → 늦은 점유맵
삽입 → 3 m/s에서 이미 커밋된 궤적을 제때 교체하지 못함**이다.

`collisions` 원시 합계는 물리 충돌 횟수로 사용하지 않는다. 모니터가 최신 표면점 거리의
false→true 전이를 세므로 반경 0.20 m보다 큰 원통 내부에서 한 관통이 두 번 이상 기록될 수 있다.
따라서 이 문서는 재현 가능한 보수 지표인 **접촉 표시 런 수**만 헤드라인으로 사용한다.

relay-full의 접촉 런이 더 많은 것은 “시야가 넓으면 항상 더 안전하다”는 이상적 가정이 현재
실시간 파이프라인에서 성립하지 않기 때문이다. `rm_performance_log.csv` 행 증가량을 미션시간으로
나눈 실효 ROG 갱신률은 seed1~10 평균 full **3.88 Hz**, sector **4.87 Hz**, adaptive
**4.89 Hz**였다. seed10에서는 1.56/2.64/3.09 Hz로 격차가 더 컸다. 3 m/s 기준 갱신 사이
이동거리는 seed10 full이 약 1.92 m, adaptive가 0.97 m다. full은 한 프레임에 더 많이 보지만
큰 메시지 처리 때문에 시간적으로 더 오래된 맵으로 계획할 수 있다. 반면 이전 정밀분석의 충돌
대상은 전부 진행방향 ±60° 안에 있었으므로, sector/adaptive가 버린 후방·측면 점은 당장의
회피에 기여하지 않았다. 즉 이 결과는 “정보가 적을수록 안전”이 아니라 **위험방향 정보는
유지하면서 처리량을 줄여 시간 신선도를 높인 효과**로 해석한다.

## 5. 논문 결론과 한계

1. adaptive는 seed1~10에서 점군 70.5%, raycast 시간 66.9%, 총 mapping 시간 62.1%를 줄였다.
2. 시스템 CPU 차이는 1~2%p로 작고 필터 CPU가 증가하므로 CPU 절감을 주장하지 않는다.
3. 완주 시간은 세 모드 모두 약 79 s로 필터에 따른 임무시간 손실이 관찰되지 않았다.
4. 접촉 표시 런은 relay-full 30%, sector 16%, adaptive 14%였다. adaptive가 최소였지만 sector 대비
   차이는 작으며, v6에서는 어떤 모드도 0충돌이 아니므로 “무손실 안전” 주장을 폐기한다.
5. seed11 30회 본 실험에서 adaptive는 점군 66.2%, raycast 60.6%, mapping 51.3%를 줄였다.
   실효 갱신률 증가는 2.2%에 그쳤고 완주 런 임무시간은 73.47/73.37 s로 같았다.
6. seed11 접촉 표시 런은 raw 8/30, adaptive 14/30이며 `p=0.180`이고 신뢰구간이 겹친다.
   통계적 열등성을 확정하지는 않지만 방향상 불리하므로 안전 동등성·충돌 0·저하 징후 미관찰을
   모두 주장하지 않는다.
7. 접촉 순간 원본 local cloud·정적 PCD·ROG occupied map·A* frontend path·committed trajectory·
   `/planning/pos_cmd`를 보존했다. 다만 시각화 발행과 monitor가 시스템 타이밍을 바꾸며,
   PCD sample 팽창과 live renderer 판정도 불일치하므로 별도의 저오버헤드 recorder와 signed
   mesh/voxel solid 판정으로 개선해야 한다.
8. 원 논문 또는 raw LiDAR와 비교할 때는 Python 릴레이를 거친 기존 full을 baseline으로 쓰지
   않는다. seed11에서 raw-direct는 relay-full보다 실효 갱신률이 20.4% 높고 접촉 표시 런이
   1/10 대 5/10이었으므로, seed1~10의 full 결과도 raw-direct 재실험 전에는 원 논문 baseline으로
   해석하지 않는다.
9. 현 공개 자산만으로는 논문의 60-map×18-speed 프로토콜을 그대로 재현하지 못했다. 공개
   dense-forest 예제 하나의 결과와 논문 1080회의 결과는 서로 다른 실험으로 보고한다.

## 6. 재현 자산

- 메인 캠페인: `results/native_seed1_11_v6_n5.csv`
- seed11 raw/adaptive 30회 본 실험: `results/native_seed11_raw_adaptive_n30.csv`
- seed11 30회 통계 요약: `results/native_seed11_raw_adaptive_n30_summary.csv`
- seed11 접촉 스냅샷 60개: `results/native_seed11_raw_adaptive_n30_forensics/`
- seed11 최종/예비 자산 구분: `results/native_seed11_raw_adaptive_n30_README.md`
- 계측 검증 smoke와 스냅샷: `results/native_seed11_raw_adaptive_n30_smoke*.csv`,
  `results/native_seed11_raw_adaptive_n30_smoke*_forensics/`
- seed11 입력 경로 대조: `results/native_seed11_pipeline_ablation_n10.csv`
- 공개 upstream 예제형 control: `results/native_seed11_upstream_example_n10.csv`
- 대조실험 통합 요약: `results/native_seed11_pipeline_ablation_summary.csv`
- 대조실험 smoke: `results/native_seed11_raw_controls_smoke.csv`
- 선행 seed11 필터 3모드 결과: `results/native_seed11_v6_n10.csv`,
  `results/native_seed11_v6_n10_summary.csv`
- 선행 1회 정밀 분석: `results/native_seed1_11_v6_forensics_{summary,episodes}.csv` 및 `.json`
- 지도 사양: `docs/native_seed1_10_v6.md`
- 지도 좌표: `scripts/native_campaign/seed1_static.csv` … `seed10_static.csv`
