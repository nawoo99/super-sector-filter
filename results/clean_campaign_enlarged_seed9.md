# Clean Campaign — Enlarged Field (±15) — seed9

동적 A/B/C 재실행. 확대필드(AREA 30 / obstacles ±15, gaps dense1.1/med1.4/sparse1.8,
map_size 34, max_vel 0.9)에서 SO3 자세제어 컨트롤러로 **깨끗한 비행**을 확보한 뒤
full / sector / adaptive 각 모드를 fresh bringup으로 1회씩 실행.

## 결과 (seed9, 4-corner 순회 미션)

| 모드 | 점수(pts_mean) | raycast_ms | ROG total_ms | 충돌 | 코너 | 완주 |
|------|------:|------:|------:|----:|----:|:----:|
| **full** (OFF) | 9077 | 1.98 | 7.79 | 0 | 4/4 | ✅ |
| **sector** (±60° 고정) | 3129 | 0.72 | 3.53 | 0 | 4/4 | ✅ |
| **adaptive** (±60°+full-view 복구) | 3920 | 0.84 | 4.16 | 1 | 4/4 | ✅ |

## full(OFF) 대비 맵비용 감소
- **sector**:  점 66%↓ · raycast 63%↓ · ROG total 55%↓ · **충돌 0→0**
- **adaptive**: 점 57%↓ · raycast 58%↓ · ROG total 47%↓ · 충돌 0→1

## 해석 (논문 스토리)
- **간격이 넓은 필드에서는 sector 필터가 안전 페널티 없이 맵비용만 절감**한다
  (세 모드 모두 4/4 완주, sector 충돌 0). 즉 sector의 이득(raycast 63%↓)이
  거의 무료로 회수된다.
- 이전 ±12 scrappy 필드(results/dynamic_seed9_full_vs_sector.csv)에서는
  full 8 / sector 21 / adaptive 4 충돌로, sector의 좁은-시야 안전비용이 두드러졌고
  adaptive의 full-view 복구가 그 비용을 되돌렸다.
- 두 필드를 함께 제시하면: **sector 이득은 지형-독립적(맵비용 60%+↓)이고,
  안전비용은 지형 난이도에 의존하며, adaptive가 그 안전비용을 흡수**한다는
  완결된 논거가 된다.

## 재현
- config: config/static_gazebo.yaml (max_vel 0.9, map_size 34, map_voxel_num 500)
- world: scripts/gen_world.py --seed 9 (AREA 30, gaps 1.1/1.4/1.8)
- 각 모드 fresh bringup 후 g_campaign.py --seeds 9 --runs 1 --modes {full,sector,adaptive}
