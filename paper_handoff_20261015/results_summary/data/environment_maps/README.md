# 최종 실험 맵별 지도 이미지

2026-10-10에 현재 동결 V6 본실험의 맵 1~5·도심지·숲 총 7개를 시각화했다. 새 맵을 만들거나 장애물 배치를 변경한 것이 아니라, 실제 실험에 사용한 정적 장애물 형상과 웨이포인트를 평면도로 표시한 자료다.

| 환경 | PNG | 실제 맵 ID |
|---|---|---|
| 맵 1 | [map1.png](map1.png) | gapfree_d1_m01 |
| 맵 2 | [map2.png](map2.png) | gapfree_d1_m02 |
| 맵 3 | [map3.png](map3.png) | gapfree_d1_m03 |
| 맵 4 | [map4.png](map4.png) | gapfree_d1_m04 |
| 맵 5 수정본 R2 | [map5_r2.png](map5_r2.png) | gapfree_d1_m05r2 |
| 도심지 | [urban.png](urban.png) | urban_blocks_u01 |
| 숲 | [forest.png](forest.png) | forest_cluster_f01 |
| 전체 비교 | [all_maps_overview.png](all_maps_overview.png) | 위 7개 전체 |

모든 그림은 PNG·SVG·PDF로 제공한다. 개별 PNG는 1920×2112 픽셀이며, 전체 비교 PNG는 4320×2496 픽셀이다. SVG와 PDF는 확대·논문 편집용 벡터 형식이다. 그림 내부는 영어로 표시했다.

## 그림 읽는 방법

- 회색 도형: 실제 정적 원기둥 또는 건물의 수평 단면. 모든 장애물이 미션 고도 1.5 m에 걸쳐 존재하므로 해당 고도에서의 실체 단면과 일치한다.
- 파란 번호: 웨이포인트 1~5.
- 주황 별: 초기 위치 (0, 0), 마지막 웨이포인트 5와 같은 위치.
- 파란 점선: 목표 방문 순서. 실제 비행 궤적이나 무충돌 경로가 아니며 장애물을 가로지를 수 있다.
- 도심지 건물 번호: 사용자 지정 표시 번호. 왼쪽 위 1, 오른쪽 위 4, 왼쪽 아래 13, 오른쪽 아래 16이다. 원본 geometry ID와는 다르다.
- 모든 맵: 동일한 world-frame 축, x·y 각각 -32~32 m, 가로세로 같은 축척. 기체 반경 또는 안전 여유만큼 장애물을 팽창시킨 지도가 아니다.

이 그림은 전역 정적 geometry의 시각화이며, 플래너가 실제 관측한 occupancy map, LiDAR 가림 영역 또는 누적 시야를 나타내지 않는다. 모드별 장애물 배치는 같으므로 맵마다 공통 지도 한 장을 제공한다.

## 출처와 검증

`map_sources.json`에 실제 장애물 좌표·크기·고도, 초기 위치와 웨이포인트, 입력 파일 및 출력 이미지의 SHA-256, 검증 항목을 저장했다. 입력 geometry·미션의 해시는 맵 등록부 및 `results/v6_frozen_20261008/source_manifest.json`과 대조했다. 동결 본실험 210행의 맵 ID 및 맵·모드당 10회도 확인했다. 원시 비행 로그를 새로 읽거나 시뮬레이션을 실행하지 않았다.

원본 지도·미션·플래너·동결 결과는 변경하지 않았다. `generate_maps.py`는 결과 그림을 재현하는 분석 스크립트이며 기존 그림은 덮어쓰지 않는다. 다시 생성하려면 비어 있는 새 출력 디렉터리를 지정한다.

```bash
/usr/bin/python3 -s /root/super-sector-filter/results/map_visualizations_20261010/generate_maps.py \
  --output /root/super-sector-filter/results/map_visualizations_recheck
```
