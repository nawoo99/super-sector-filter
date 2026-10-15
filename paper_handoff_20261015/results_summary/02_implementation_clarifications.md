# Adaptive 구현과 논문 수식의 최종 설명

현재 V6 실험의 Adaptive는 정상 상태에서 좁은 관측을 사용하고, 정지 복구에서는 Full 수평 360° 관측으로 전환한다. 제자리 yaw 탐색은 비교 방법인 Active-Yaw Sector의 동작이다. 이 구분과 초기 위치 탈출 해제 조건은 기존 구현에 대한 설명이며, 실험 후 알고리즘을 변경한 것이 아니다.

## 식 4는 좁은 관측 상태의 중심각

Adaptive의 좁은 관측 중심은 세계 좌표계의 수평 속도 방향을 사용한다. 수평 속력이 1.5 m/s를 초과하면 저장 방향을 갱신하며, 그 이하에서는 마지막 저장 방향을 유지한다. 저장 방향이 아직 없을 때만 측정된 기체 yaw를 사용한다.

\[
\psi_k=
\begin{cases}
\operatorname{atan2}(v_{k,y},v_{k,x}),&\|\mathbf v_{k,xy}\|_2>1.5\ \mathrm{m/s},\\
\psi_{k-1}^{v},&\|\mathbf v_{k,xy}\|_2\leq1.5\ \mathrm{m/s}\ \text{and a stored heading exists},\\
\psi_k^b,&\text{otherwise}.
\end{cases}\tag{4}
\]

정지 중 기체 yaw만 바뀌어도 저장된 속도 방향은 자동으로 따라 바뀌지 않는다. 그러나 Adaptive의 복구 주기가 활성화되면 Full 관측을 사용하므로, 특정 중심각에 대한 ±45° 수평 제한을 적용하지 않는다. 이때의 다른 방향 관측을 좁은 섹터의 yaw 탐색으로 설명하지 않는다.

Active-Yaw Sector에서는 관측 중심이 측정된 기체 yaw를 따른다. 플래너가 기체 yaw를 회전시키면 좁은 수평 관측 방향도 함께 변한다. 별도의 탐색 목표 yaw 명령과 실제 관측 중심으로 사용하는 측정 yaw를 구분한다.

| Mode and phase | Observation policy |
|---|---|
| Adaptive narrow acquisition | Stored world-frame velocity heading; body yaw only before initialization |
| Adaptive recovery | Full horizontal 360-degree acquisition; no narrow-sector center restriction |
| Active-Yaw Sector recovery | Narrow acquisition follows measured body yaw during commanded yaw search |

이것은 MARSIM 획득 창의 방향 제어이며 실제 하드웨어 LiDAR나 기계식 짐벌의 구현을 검증한 결과는 아니다.

## 식 5에서 출발 허가와 탈출 해제를 구분

기존 식 (5)의 \(L_e\)는 정지 상태에서 새 경로 실행을 시작하는 출발 허가다. 초기 위치 탈출이 필요하면, 출발 허가 후에도 Full 관측을 유지한 채 인증된 탈출 구간을 실행할 수 있다. 따라서 초기 위치 탈출 처리의 완료·해제는 출발 허가와 별도인 Sector 복귀 조건 \(E_e\)로 표시한다.

\[
G_e=[n_f>n_e]\land[t_f>t_e]\land A_e(n_f,t_f,m_f)
\land[m_f>m_e]\land P_e\land V_e\land L_e\land E_e.\tag{5}
\]

| Symbol | Meaning |
|---|---|
| \(e\) | Recovery cycle |
| \(n_e,t_e,m_e\) | Input-sequence boundary, acquisition-time boundary and map version before the cycle |
| \(n_f,t_f,m_f\) | Selected fresh Full-frame sequence, acquisition time and committed map version |
| \(A_e\) | Matching selected Full frame is acknowledged as committed to the map |
| \(P_e\) | New trajectory generation is committed |
| \(V_e\) | Trajectory is revalidated for the current map, goal and recovery cycle |
| \(L_e\) | Certified stopped departure is accepted and the corresponding trajectory is released |
| \(E_e\) | No escape hold is required, or the required escape hold has been released |
| \(G_e\) | Permission to return to narrow Sector acquisition |

탈출 처리가 필요하지 않으면 \(E_e=\mathrm{true}\)로 둔다.

탈출 해제는 단순한 타이머 만료가 아니다. 인증된 탈출 구간 이후 시각에 도달하고, 현재 궤적 세대·현재 지도에 대한 유효한 안전 인증이 현재 실행 표본을 포함하며, clearance escape 또는 initial footprint egress 예외를 더 이상 사용하지 않을 때 Full 유지 상태를 해제한다. 조건을 충족하지 않으면 출발 이후라도 Full 관측을 유지한다.

출발 허가 안에는 탈출 영수증의 세대·시작 상태 일치 확인이 포함될 수 있다. 이는 탈출 구간을 실제로 실행해 완료했음을 확인하는 \(E_e\)와 다르다. \(L_e\)를 정의 변경 없이 두 조건의 동의어로 쓰지 않는다.

이 식의 보완은 원고의 조건 표기를 기존 구현과 일치시키는 정정이다. 최종 210회 결과나 관측 판정을 변경하지 않는다. 일반 복귀에 추가적인 이동 거리 조건이 있는 것은 아니며, 탈출 예외가 사용된 경로만 별도의 해제 조건을 거친다.

## 목표 고도와 목표 전환 거리

세 미션의 명목 목표 고도와 웨이포인트 전환 반경은 각각 1.5 m다. 이는 기존 미션 설정을 유지한 공통 실험 조건이지, 이론적으로 유도하거나 최적성을 입증한 값이 아니다. 실제 비행 고도를 항상 1.5 m로 강제한 것은 아니며 내부 목표는 가까운 유효 격자로 보정될 수 있다.

실제 미션 노드의 목표 전환은 기체와 원래 웨이포인트 사이의 **3차원 거리 < 1.5 m**를 사용한다. 반면 최종 결과의 독립 관측기는 **수평 XY 거리 < 1.5 m**로 목표 방문을 센다. 두 정의를 같다고 기술하지 않는다. 결과표의 목표 도달 수치는 기존 독립 관측기의 정의를 그대로 보존한다.

최대 궤적 속도 설정은 7 m/s이며 일정한 실제 주행 속도가 아니다. 센서의 명목 주기는 10 Hz다. 측정된 처리 주파수와 전환 지연은 결과 CSV의 실제 값을 사용한다.

## 센서 주파수 필드의 정의 정정

원자료의 `sensor_hz`는 설정된 명목 주파수가 아니라 시뮬레이터의 `SENSOR_CADENCE_SUMMARY`에서 읽은 실제 소스 생성 주파수다. 첫 프레임과 마지막 프레임 사이의 기간을 `sensor_span_s`, 생성 프레임 수를 `sensor_frames`라 하면 다음과 같이 계산한다.

    sensor_hz = (sensor_frames - 1) / sensor_span_s

센서 설정 10 Hz와 이 측정값을 구분한다. 이 값은 지도 처리 `map_frames_s`나 외부 구독기의 수신 주파수와도 다르다. 로그가 소수점 여섯 자리로 기록되므로 원자료에서 기간과 주파수를 재계산하면 작은 반올림 오차가 있을 수 있다.

변경 없이 복사한 `data/08_metric_definitions.md`의 "sensor_hz는 명목 주파수"라는 설명은 이 절로 정정한다. 기존 CSV·JSON 수치와 실험 결과는 그대로이며, 필드 의미만 올바르게 설명한다.

## 코드 근거

아래 경로는 분석 환경의 실제 파일이다. 논문 본문에는 내부 경로를 넣지 않고 이 근거 문서에만 둔다. 경로의 존재를 확인할 수 없는 외부 환경에서는 전달된 설명을 사용하고 새 검증을 수행했다고 주장하지 않는다.

`07_implementation_evidence.json`에는 아래 핵심 코드의 발췌, 파일 해시와 실제 본실험 모드 로그를 함께 제공한다. 동결 소스 목록과의 직접 대조 여부도 각 항목에 표시한다.

| Claim | Source location |
|---|---|
| Shared acquisition center and Full flag | `/root/super_ws/src/SUPER/mission_planner/Apps/native_sector_cpp.cpp:688` |
| Stored velocity heading or body-yaw fallback | `/root/super_ws/src/SUPER/mission_planner/include/mission_planner/sector_heading_policy.hpp:17` |
| Velocity heading updated only above threshold | `/root/super_ws/src/SUPER/mission_planner/Apps/native_sector_cpp.cpp:1205` |
| Recovery selects Full acquisition | `/root/super_ws/src/SUPER/mission_planner/Apps/native_sector_cpp.cpp:718` |
| Center steering applies only to narrow acquisition | `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp:752` |
| Active-yaw scanning excludes Adaptive event recovery | `/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:299` |
| Departure receipt and continuity checks | `/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp:3428` |
| Trajectory released before separate escape hold | `/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:4402` and `:4477` |
| Live escape-release checks | `/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:622` |
| Mission switches by strict 3D radius | `/root/super_ws/src/SUPER/mission_planner/include/waypoint_mission/ros2_waypoint_planner.hpp:67` |
| Independent observer counts strict XY radius | `/root/super-sector-filter/scripts/native_campaign/native_loop_monitor.py:949` |
| Sensor cadence is measured from generated-frame count and timestamp span | `/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp:654` |
| sensor_hz is parsed from the cadence log | `/root/super-sector-filter/scripts/native_campaign/native_campaign.py:693` |
| Retained common 1.5 m mission constants | `/root/super-sector-filter/docs/scenario7_n10_grouped_missions_20260924.md:55` |

기존 원고나 오래된 인계 설명과 위 내용이 다르면 최종 실험에 사용한 구현과 여기서 설명한 적용 범위를 우선한다. 수치는 `data/`의 검증된 최종 결과를 사용한다.
