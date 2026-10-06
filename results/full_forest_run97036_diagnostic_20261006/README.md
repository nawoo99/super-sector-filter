# Forest Full run97036 정지 원인 분리 진단 (2026-10-06)

> 이 문서는 수정 전의 읽기 전용 진단을 보존한다. 이후 구현 및 별도
> 파일럿 결과는 `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.131과
> `results/topology_liveness_trial_20261006/`에 기록하며, 원본 실패를 대체하지 않는다.

## 판정

이번 실패는 접촉이나 미션 제한시간 초과가 아니다. 1/5 웨이포인트 이후
`(8.675302, 18.973435, 2.685578)` m 부근에서 재계획이 진행되지 않아,
측정용 **60초/2cm 무진전 관찰자**가 104.02초에 종료한 사례다. 당시
정지 좌표에서 정적 원기둥만 고려하면 다음 웨이포인트로 이어지는 2-D
경로가 있으나, 안전 가드가 로그에 기록한 반경 0.8m 임시 차단 구역 두
개를 동시에 적용하면 출발지가 작은 연결 성분에 갇힌다. 이는 실제 로그의
A* `NO_PATH`와 일치한다. 단, 원래 ROG-Map 점유 상태·LiDAR 스캔·A*
guide path·CIRI polytope·MINCO 초기값의 스냅샷이 없어 **동일 상태
재생이나 CIRI/MINCO 단독 원인 확정은 불가능**하다.

원본 210회 결과와 코드/프로파일은 바꾸지 않았다. 새 비행도 실행하지
않았다. 이 폴더의 Python 검사는 정적 기하의 읽기 전용 반사실 실험이다.

## 증거 연쇄

| 단계 | 원본 관측 |
|---|---|
| 안전 측정 | `full_summary.json`에서 run_valid/resource_valid/speed_limit_valid 모두 true, 접촉 0, waypoint 1/5. 종결 사유 `persistent_no_progress_stall`. |
| 실제 안전 여유 | 런타임 가드 `hard_clearance=0.300m`, 물리 반경 `robot_r=0.200m`. 최종 위치에서 가장 가까운 `trunk_088` 표면까지 0.44989m(기체 표면 여유 0.24989m). 즉 접촉은 없지만 밀집된 위치다. |
| 저수준 기하 | `trunk_090`–`trunk_093` 표면 간격 0.58841m는 반경 0.3m를 양측에 적용한 0.6m보다 좁다. 이것만으로 전체 경로가 없다는 뜻은 아니다. |
| 1차 실패 | `stack.log:3276–3277`: `APPENDED_BACKUP`와 EXP가 `CLEARANCE_MARGIN`으로 거절되고 zone0 `(7.757,18.368)` 반경 0.8m가 설정된다. |
| 2차 실패 | `stack.log:3336,3356,3404`: zone0 하에서 MINCO가 반복적으로 최대 반복 횟수에 도달한다. `stack.log:3406`은 optimizer 실패를 근거로 zone1 `(7.633,19.324)` 반경 0.8m를 추가한다. |
| CIRI 상태 | 같은 런 전체에서 `maxVolInsEllipsoid failed` 39회와 `problem is not feasible` 1회(`stack.log:2037`, 최소 장애물 거리 0.17449m)가 관측됐다. 이 카운트만으로 CIRI가 최종 정체의 최초 원인인지, 거절된 guide path의 후속 증상인지는 분리할 수 없다. |
| 경로 단절 | `stack.log:3427–3428`: 두 zone을 적용한 직후 A*가 190회 탐색 후 `NO_PATH`. `astar.cpp:626–627`에서 이 반환은 일반 `NO_PATH` 경로이지 탐색 시간 초과 반환이 아니다. |
| 반복 | `stack.log:3474` 이후 같은 정지 위치에서 임시 zone을 지우고 재시도한다. 로그 총계: 임시 zone 리셋 19, A* `NO_PATH` 39, MINCO 실패 25, trajectory guard 거절 116. 센서 프레임은 1085개 기록되어 단순 LiDAR 무수신으로 설명되지 않는다. |
| 기존 복구 | 이 런은 수평 local-escape 4회(`stack.log:2203,2404,2703,2978`)와 수직 0.6m recovery 1회(`stack.log:3219`)를 실제 커밋했다. 안전하게 움직였지만 2m 진행 임계값을 넘는 탈출·완주에는 이르지 못했다. |

런 프로파일은 **Full** `static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml`
(SHA-256 `5338dbc113d017f23de477264ac58e431599943ab638925c53a06b2a7f7cce2c`)
이다. 정적 맵 geometry SHA-256은
`691d2c0aec0a015368ecd2eca9335b932e3de892123305ba05bc87f26ca7150d`.
다른 모드의 filtered 프로파일을 이 Full 실패의 설정으로 간주하면 안 된다.

## 정적 연결성 검사

`check_static_connectivity.py`는 원본 geometry JSON의 410개 원기둥,
최종 정지 좌표, 그 시점 로그의 두 zone을 사용한다. 다음 목표는 mission
waypoint 2의 실제 수신 좌표 `(24.025,22.025)` m다. 원기둥 표면에
0.3m 또는 보수적 0.4m를 더해 점유 격자를 만들고, 0.1m/0.2m 셀과
4/8방향 이동을 모두 검사했다. 임시 zone 안에서는 원본 A* 코드의
"출발지가 zone 안에 있으면 바깥쪽으로만 이동" 규칙을 반영했다.

| 장애물 조건 | 0.1m/0.2m, 4방향 | 0.1m/0.2m, 8방향 |
|---|---|---|
| 정적 원기둥만 | 4/4 조합 연결 | 4/4 조합 연결 |
| zone0만 또는 zone1만 | 일부 보수적 조합에서 불연결 | 각각 4/4 조합 연결 |
| zone0+zone1 | 0/4 조합 연결 | 0/4 조합 연결 |

여기서 각 4개 조합은 해상도 2개 × 추가 여유 2개다. 8방향은 대각
모서리 통과도 허용하므로 실제보다 관대한 검사인데도, 두 zone을
함께 두면 출발지 연결 성분이 해상도/여유에 따라 4–28셀뿐이었다.
따라서 **두 zone이 정지 위치의 출구를 봉쇄한다**는 기하 설명은
견고하다. 그러나 zone0만 두었을 때 경로 연결이 가능하다는 것은
실제 CIRI/MINCO 최적화 가능성을 보증하지 않는다.

재현 명령:

```bash
python3 /root/super-sector-filter/results/full_forest_run97036_diagnostic_20261006/check_static_connectivity.py
```

이 검사는 실제 3-D 점유맵/미관측 공간/동역학/ROS 시각을 재현하지
않으며, 2-D 격자 경로를 비행 가능한 trajectory라고 주장하지 않는다.

## 코드 수준 결함과 다음 조치

`super_planner.cpp:4775–4832` 및 `:3953–4009`의 복구 분기에서는
local-escape/vertical 예산을 다 쓰면 zone과 카운터를 비우고
`guard_corridor_retry_pending_`를 다시 켠다. 재시도 전 실제 위치,
관측 영역, 출구 연결성 또는 선택된 topology가 유의미하게 달라졌는지
확인하는 조건이 없다. 이 때문에 안전하게 정지한 채 같은 후보와
차단 구역을 재구성하는 **liveness 결함**이 생긴다. 안전 가드가 위험
trajectory를 차단한 동작 자체는 정상이며, guard를 끄거나 완주로
간주해서는 안 된다.

수정 후보의 우선순위:

1. zone을 추가하기 전에 정지 위치의 출구 연결성을 점검하고, 두
   zone이 출발지를 고립시키면 두 번째 zone을 그대로 커밋하지 않는다.
   이는 불필요한 `NO_PATH` 루프를 막는 조건이지 완주 보증은 아니다.
2. 복구 예산 소진 후 같은 정지 상태에서는 epoch를 무한 리셋하지
   않는다. 새로운 맵 관측·실제 위치 변화·별도 certified retreat
   경로 확보 중 하나를 요구하고, 없으면 `RECOVERY_EXHAUSTED`로
   명시해 안전 정지를 유지한다.
3. 진짜 완주 복구는 원본과 동일한 map snapshot/guide/CIRI/MINCO
   초기값을 남기는 계측을 추가해 분리 실험한 뒤 설계해야 한다.
   특히 서쪽 큰 우회로의 A* guide가 CIRI 및 동역학 제약 아래 실제
   최적화되는지 확인해야 한다. 현재 자료만으로 특정 해법을 단정할
   수 없다.
4. 수정 후에는 기존 c41 210회를 손대지 않고 Forest Full 파일럿,
   Forest n10, 그리고 7맵×3모드 독립 캠페인으로 회귀검증한다.

논문에서는 현재 Full 69/70, Adaptive 70/70을 그대로 보고해야 한다.
이번 진단은 Full 100%를 입증하지 않는다.
