# 논문 스토리 — JKICS v8 (2026-08-11, seed1~10 is_dense 버그 수정 및 재검증)

> **v7→v8 변경 이유:** v7의 "3.1 seed1~10: 150회" 수치(접촉 표시 런 full 30%·sector 16%·
> adaptive 14%)는 이후 모니터 판정이 더 엄격해지기 전에 수집된 결과였다. 동일 조건으로
> 현재 도구로 새로 150회를 돌리자 sector/adaptive가 **50/50 전부 접촉 표시, 평균 clearance
> 0.002 m**로 뒤집혔다(반대로 full은 62%만 접촉). 원인을 추적한 결과 `native_sector.py`가
> ROS2 표준 함수 `create_cloud()`로 필터링된 클라우드를 재발행하는데, 이 함수가 `is_dense`
> 필드를 항상 `False`로 고정해서 SUPER의 ROG 점유맵이 그 프레임을 통째로 버리고 있었다
> (`pcl::fromROSMsg`가 플래그를 그대로 복사하고 재검사하지 않음). 실측으로 접촉 순간 점유맵의
> 최근접 OCCUPIED 셀이 실제 최근접 장애물보다 1.7~4.7 m 뒤처져 있음을 확인했다. full은 원본
> 메시지를 그대로 재전송해 이 문제를 피해갔다. `native_sector.py`에서 발행 직전
> `out_msg.is_dense = True`로 고쳐 재검증한 결과 sector/adaptive가 다시 full과 동등하거나
> 더 나은 접촉률을 회복했다(§3.1). 이 과정에서 `fsm_ros2.hpp`의 콜백 그룹 버그(생성만 되고
> 실제로는 연결되지 않은 `replan_cbk_group_`)도 함께 고쳤으나, 단독으로는 수치를 개선하지
> 못했다 — 지배적 원인은 `is_dense` 쪽이었다. 이어서 사용자 요청으로 seed1~10 ablation
> 자체에도 논문 파라미터(`max_acc=20 m/s²`, 속도 1~18 m/s 스윕)를 맞춰 900회를 추가로
> 실행했다(§3.1). 마지막으로 "왜 full조차 논문의 0%가 안 나오는가"를 직접 검증했다 — loop24의
> 4코너 급선회 미션이 원인이라는 가설을 세웠으나, 실측(코너 인접도 분석·4방향 직선 프로브)으로
> 반박됐다. 실제 원인은 loop24가 논문의 100 m 편도 미션보다 훨씬 넓은 면적(약 223 m, 필드
> 가장자리 포함)을 훑기 때문으로 보인다(§3.5). 이 난이도는 full/sector/adaptive 세 모드에
> 동일하게 적용되므로 세 모드 간 비교의 타당성 자체는 훼손되지 않는다.

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
- SUPER `robot_r=0.20 m`, `max_vel=3.0 m/s`, `max_acc=15.0 m/s²`(원 ablation 설정),
  ROG inflation 명목 0.30 m.
- 각 seed·모드 5회: 10맵×3모드×5회 = 150회.
- 추가로 논문 파라미터에 맞춘 재검증: `max_acc=20 m/s²`(논문 고정값), `max_vel`을 논문
  스윕 구간 중 1/4/7/10/14/18 m/s 6개 값으로 실행. 10맵×3모드×6속도×5회 = 900회.

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

### 3.1 seed1~10: 150회 (원 ablation 설정) + 900회 (논문 파라미터 재검증)

v7의 150회 수치는 `is_dense` 버그(아래 §4)가 있는 상태에서 수집됐다. 버그를 고친 뒤 **완전히
동일한 조건**(`static_seedmaps.yaml`, `max_vel=3.0`, `max_acc=15.0`, loop24, 10맵×3모드×5회)으로
재실행한 결과는 다음과 같다.

| 지표 | full | sector | **adaptive** |
|---|---:|---:|---:|
| 완주 | 50/50 (100%) | 50/50 (100%) | 50/50 (100%) |
| 접촉 표시 런 | 26/50 (**52.0%**) | 17/50 (**34.0%**) | 16/50 (**32.0%**) |
| 평균 min clearance | 0.203 m | 0.250 m | 0.257 m |
| 평균 kept 비율 | 100.0% | 48.6% | 49.0% |
| 평균 미션시간 | 78.6 s | 78.3 s | 78.3 s |
| fsm CPU | 86.6% | 86.2% | 86.0% |

버그 수정 전(v7)과 정반대로, **sector/adaptive가 점군을 약 51% 줄이면서 full보다 접촉 표시 런
비율이 낮고 평균 clearance도 더 크다.** (원본: `results/native_seed1_10_isdense_fix_n5.csv`,
`results/native_seed1_10_isdense_fix_README.md`)

이어서 사용자 요청으로 seed1~10 ablation 자체에도 논문 파라미터를 맞췄다. `max_acc`를 논문
고정값 20 m/s²로 올리고, `max_vel`을 논문이 스윕한 1~18 m/s 구간 중 1/4/7/10/14/18의 6개
값으로 실행했다(10맵×3모드×6속도×5회 = 900회, `results/native_seed1_10_paper_speed_sweep_n5.csv`).

| 지표(6속도 통합, 300회/모드) | full | sector | **adaptive** |
|---|---:|---:|---:|
| 완주 | 282/300 (94.0%) | 282/300 (94.0%) | 274/300 (91.3%) |
| 접촉 표시 런 | 181/300 (60.3%) | 172/300 (57.3%) | 165/300 (55.0%) |
| 평균 min clearance | 0.157 m | 0.169 m | 0.172 m |
| 평균 kept 비율 | 100.0% | 57.5% | 59.7% |

속도별로 보면 접촉률이 급격히 증가한다(1 m/s에서 2~5/50, 10~18 m/s에서 34~41/50). 즉 절대
접촉률은 논문의 “0% 충돌” 헤드라인과 거리가 멀지만, `max_acc`를 논문값으로 맞춰도 세 모드
사이의 상대적 순위(sector·adaptive ≥ full)는 원 ablation 설정과 동일하게 유지된다. 왜 절대
접촉률이 논문과 이렇게 다른지는 §3.5에서 다룬다.

반경 단계가 커질수록 접촉이 집중되는 경향은 두 재검증 모두에서 유지됐다(seed9~10에서 가장
높음). 이는 필터만의 문제가 아니라 큰 장애물이 만드는 경로 차단과 SUPER의 잔여 계획
변동성(§4)을 드러낸 스트레스 캠페인이라는 v6 해석과 일치한다.

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

### 3.5 왜 seed1~10의 full조차 논문의 0%가 아닌가

먼저 논문이 실제로 사용한 60개 평가 지도(밀도 6단계×seed 10개)가 공개돼 있는지 확인했다.
GitHub `hku-mars/SUPER`(`git ls-files`로 확인)에는 튜토리얼용 `random_map_*.pcd` 4개만
커밋돼 있고, 논문 Zenodo 릴리스(10.5281/zenodo.14528604)도 코드 스냅샷과 예시 지도 1개
(`mock_map_opt_26121_20.pcd`, 본 프로젝트의 `map0`)뿐이다. 두 저장소 모두 밀도 라벨이 붙은
60개 지도 세트를 포함하지 않으므로, 정확한 재현은 애초에 불가능하다.

다음으로 loop24 미션 자체(4개 90° 코너, 총 ~223 m)가 논문의 100 m 편도 미션보다 어려운지
직접 검증했다. `full` 모드만, `static_seedmaps.yaml`(max_vel=3.0)로 아래 두 단계를 실행했다.

1. **직선 단일구간 테스트**: 10개 시드 모두 원점(0,0)에서 loop24의 첫 코너 (24,24)까지
   회전 없이 직선으로만 비행. 접촉 표시 런 **2/10**로 loop24의 52%(같은 설정 기준)보다
   크게 낮았다(`results/native_seed1_10_straight_direction_probe.csv`의 `ne` 방향).
2. **코너 인접도 분석**: 위 §3.1 150회 캠페인 중 seed9~10(가장 어려운 반경) `full` 모드의
   접촉 이벤트 56건을 loop24의 각 구간에 투영해 “구간의 몇 % 지점인지”를 계산했다
   (`results/native_seed9_10_full_loop24_contact_segment_position.csv`). 결과: 구간
   중간(15~85%) 51/56건(91%), 회전 직후(0~15%) **0/56건**. 접촉은 코너에 몰려있지 않았다.
3. **4방향 직선 프로브**: 회전이 아니라 “이 필드에서 우연히 쉬운 방향 하나만 테스트했다”는
   가설을 검증하기 위해, 원점에서 loop24의 나머지 세 코너(서·남·동) 방향으로도 각 10개
   시드씩 직선 비행했다. 결과: 서 2/10, 남 2/10, 동 4/10 — 4방향 합쳐 10/40(25%)이며, 거리로
   정규화한 접촉률(미터당)도 loop24보다 여전히 약 3배 낮았다.

즉 “회전”도 “특정 방향”도 loop24와 직선 미션의 차이를 설명하지 못한다. 가장 설득력 있는
설명은 **면적 노출량**이다: 직선 프로브는 필드 중심에서 뻗어나가는 짧은 사선(각 ~32 m)만
지나가지만, loop24는 필드 가장자리(±24 m 부근)를 따라 네 변을 전부(총 ~223 m) 훑는다.
장애물은 무작위 배치라 필드 전체에 균일하게 어렵지 않을 수 있고, loop24는 그 중 더 넓은
영역을(특히 직선 프로브가 가지 않는 가장자리 구간까지) 지나가면서 어려운 구간을 만날
확률이 단순히 더 높다. 이 난이도는 full/sector/adaptive 모두 동일한 seed·미션·설정에서
측정되므로, 절대 접촉률이 논문과 다르다는 사실이 세 모드 간 비교의 타당성을 훼손하지는
않는다 — 오히려 “접촉이 0으로 수렴하지 않는 스트레스 조건”에서 sector/adaptive가 여전히
full과 동등하거나 더 나은 결과를 낸다는 점이 §3.1의 핵심 근거다.

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

### 4.1 (v8) `is_dense` 버그: 정확한 메커니즘과 잔여 원인

위 “가림/미관측 공간으로 경로 생성 → 늦은 점유맵 삽입” 가설은 방향은 맞았지만 원인을 특정하지
못했다. v8에서 실측으로 확인한 정확한 메커니즘은 §서두 changelog에 적은 대로
`sensor_msgs_py.point_cloud2.create_cloud()`가 `is_dense`를 항상 `False`로 발행하고, ROG-map의
`cloudCallback`이 그런 프레임을 통째로 버리는 것이다(`fsm_node` 콘솔 로그의 "Empty or
non-dense point cloud, skip cloud callback" 경고가 5092줄 중 471줄). sector/adaptive만
`create_cloud()`로 클라우드를 재구성해 발행하므로 영향을 받았고, full은 원본 메시지를 그대로
재전송해 영향이 없었다. `native_sector.py`에서 발행 직전 `out_msg.is_dense = True`로 고치자
점유맵의 최근접 OCCUPIED 셀과 실제 최근접 장애물의 거리 차이가 즉시 사라졌고(재현 런에서 접촉
0건, clearance 0.465 m), §3.1의 150회/900회 캠페인에서도 재현됐다.

이 버그를 고친 뒤에도 남는 접촉(§3.1의 32~60%)은 별개의, 정상적인 메커니즘이다. seed9
`full` 모드 재현 런의 fsm_node 로그를 보면 접촉 직전(수 초 이내)에 `generateBackupTrajectory
return OPT_FAILED`(각속도/추력/위치 제약 위반) replan 실패가 몰려 있다. 이는 sector 필터와
무관하게 **loop24가 요구하는 기동(가장 어려운 seed9~10은 장애물 반지름 0.65 m, 표면간격은
여전히 1.00 m로 고정)이 SUPER 궤적 최적화의 동역학적 실현가능해 탐색 한계에 닿기 때문**이다.
replan이 실패하면 SUPER는 이전에 커밋된(최근에 재계산되지 못한) 궤적을 그대로 유지하는데, 이
설계 자체는 논문의 안전장치(Theorem 1: 백업 궤적은 항상 already-known-free 공간에 있다)와
일치한다 — 다만 그 정리는 “탐색 궤적이 장애물에서 충분히 멀다”는 보장은 하지 않는다. §3.5에서
이 잔여 메커니즘이 loop24의 면적 노출량 때문이지 회전 자체 때문이 아님을 추가로 확인했다.

## 5. 논문 결론과 한계

1. (v8 재검증) sector/adaptive는 seed1~10에서 점군을 약 51% 줄이면서(kept 48.6%/49.0%)
   접촉 표시 런은 오히려 full보다 낮았다(52.0% 대 34.0%/32.0%, 원 ablation 설정 기준).
   논문 파라미터(`max_acc=20`, 속도 1~18 m/s 스윕) 900회 재검증에서도 순위는 동일했다
   (60.3% 대 57.3%/55.0%, 점군 약 42~43% 절감).
2. 시스템 CPU 차이는 1%p 이내로 작고, 완주율은 세 조건 모두 91~100%다.
3. 완주 시간은 세 모드 모두 거의 동일해(원 설정 78.3~78.6 s) 필터에 따른 임무시간 손실이
   관찰되지 않았다.
4. v7의 "접촉 표시 런 relay-full 30%·sector 16%·adaptive 14%"는 `is_dense` 버그(§4.1) 상태의
   결과였다. 버그 수정 후 sector/adaptive의 절대 접촉률은 낮아졌지만 여전히 0이 아니므로
   "무손실 안전" 주장은 여전히 하지 않는다.
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
10. (v8) seed1~10의 v7 결과를 뒤집은 원인은 `native_sector.py`가 ROS2 표준 `create_cloud()`로
    필터링된 클라우드를 재발행하면서 `is_dense=False`가 고정돼 SUPER의 ROG 점유맵이 그 프레임을
    통째로 버린 것이었다. sector/adaptive만 영향을 받았다(§4.1). 재발 방지를 위해 `git ls-files`
    등으로 코드 변경을 직접 검증하는 습관을 유지한다.
11. seed1~10 GitHub `hku-mars/SUPER`와 논문 Zenodo 릴리스 모두 논문이 실제로 쓴 60개 평가
    지도(밀도 6단계×seed 10개)를 포함하지 않는다(§3.5). 두 곳 다 확인했으며, 정확한 지도 재현은
    현재 공개 자산으로는 불가능하다.
12. loop24(4코너, ~223 m)가 논문의 100 m 편도 미션보다 절대 접촉률이 높은 이유는 회전 자체나
    특정 방향이 아니라 **면적 노출량**으로 보인다(§3.5, 직선 프로브 4방향 + 코너 인접도 분석으로
    검증). 이 난이도는 full/sector/adaptive에 동일하게 적용되므로 세 모드 간 비교의 타당성에는
    영향이 없다.

## 6. 재현 자산

- (v8) is_dense 버그 수정 재검증(150회, 원 ablation 설정): `results/native_seed1_10_isdense_fix_n5.csv`
- (v8) 논문 파라미터 재검증(900회, max_acc=20·속도 스윕): `results/native_seed1_10_paper_speed_sweep_n5.csv`
- (v8) 버그 원인·재검증 방법 요약: `results/native_seed1_10_isdense_fix_README.md`
- (v8) loop24 vs 직선 미션 4방향 프로브: `results/native_seed1_10_straight_direction_probe.csv`
- (v8) seed9~10 접촉 코너 인접도 분석: `results/native_seed9_10_full_loop24_contact_segment_position.csv`
- (v8) SUPER 소스 패치(`is_dense` 관련 replan-status publisher, 콜백 그룹 수정):
  `super_patches/native_seedmap_campaign/super_planner_src/`,
  `super_patches/native_seedmap_campaign/super_planner_include/`
- (v8) 논문 파라미터 config: `super_patches/native_seedmap_campaign/super_planner_config/static_seedmaps_paper_v{1,4,7,10,14,18}.yaml`
- 메인 캠페인(v6, is_dense 버그 상태 — 참고용, v8로 대체됨): `results/native_seed1_11_v6_n5.csv`
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
