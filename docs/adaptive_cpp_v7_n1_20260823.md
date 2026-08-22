# Adaptive filter C++ 전환과 seed1-10 n=1 검증 (2026-08-23)

## 결론

Python `native_sector.py`의 strict Adaptive 경로를 별도 ROS2 C++ node
`native_sector_cpp`로 옮겼다. 최종 설정은 바꾸지 않았다. 즉 velocity-aligned
60도 half-sector, 속도 의존 near-field halo, 0.6 s/1.4 s bounded one-shot
replan recovery, 5 Hz ideal-deadline publication cap을 그대로 사용한다.

두 개의 독립 seed1-10 n=1 cohort에서 모두 raw completion과 static-PCD
contact-free completion을 **10/10** 관측했다. 첫 기능 cohort는 live/static 접촉이
모두 0이었다. 실제 실행 파일 PID를 고쳐 다시 잰 CPU cohort도 static 접촉은
0이었지만 seed10 이륙 초기에 live-cloud 0.2 m threshold event가 1회 있었다.
따라서 이 결과를 모든 접촉 detector에서 0/20이라고 합치지는 않는다.

CPU cohort의 가중 평균 C++ filter work는 **2.522 CPU-s/mission**, FSM+filter는
**54.559 CPU-s/mission**이었다. 이전 Python Adaptive n=50의 10.582/64.095보다
각각 **76.17%/14.88% 감소**했다. 변경 없는 direct Full n=50의 55.922와
비교하면 전체 CPU-work도 **2.44% 낮게 관측**됐다. 그러나 서로 다른 날짜·표본
크기의 별도 cohort 비교이고 C++은 seed당 한 번뿐이다. end-to-end CPU 절감을
확정 결론으로 쓰려면 seed1-10 n=5 gate를 다시 수행해야 한다.

## 구현

- 소스: `mission_planner/Apps/native_sector_cpp.cpp`
- 빌드/설치: `mission_planner/CMakeLists.txt`의 `native_sector_cpp` executable
- 캠페인 선택: `native_campaign.py --filter-backend cpp`
- 기본 backend는 계속 `python`이므로 기존 캠페인의 의미는 바뀌지 않는다.
- seed12-15의 trap-event instrumentation은 아직 C++에 없고 runner가 이 조합을
  명시적으로 거절한다. 지원되지 않는 기능을 조용히 생략하지 않는다.
- full/sector/velocity/adaptive 상태, odometry 기반 yaw/속도, adaptive arm/stall/
  resume, bounded/sustained replan guard, near-field halo, publication deadline,
  `/sector/full_open`, `/sector/trigger_armed`, 통계 JSON을 구현했다.
- 입력/출력 cloud QoS는 Python과 같은 best-effort/depth 1 latest-only다.

합성 PointCloud2 검사는 앞/뒤 sector, near-field, NaN을 포함한 한 frame을 Python과
C++에 동시에 넣었다. 두 구현의 출력 점 집합, dense flag, frame/point 통계가
일치했다. 테스트는
`scripts/native_campaign/test_native_sector_cpp_equivalence.py`에 보존했다.

## 실제 MARSIM layout 결함과 OOM pilot

첫 C++ 버전은 선택한 point record를 원시 byte 그대로 복사했다. MARSIM 입력은
`point_step=32`지만 선언된 x/y/z/intensity 필드는 byte 20에서 끝난다. Python의
`sensor_msgs_py.create_cloud()`는 같은 field offset을 유지하면서 trailing padding을
제거해 `point_step=20`으로 재포장한다. 합성 입력은 원래부터 16-byte packed라 이
차이를 드러내지 못했다.

첫 pilot의 seed1-3은 완주했지만 seed4에서 `fsm_node` RSS가 약 9.1 GiB까지 증가해
kernel OOM-kill을 받았다. C++ 출력을 Python과 같은 20-byte packed layout으로
바꾸고 실제 MARSIM message의 `row_step == width * 20`을 확인했다. 그 뒤 seed4
단독 smoke와 두 번의 seed1-10 cohort에서는 OOM이 재현되지 않았다. 이 관측은
layout mismatch 수정 전후의 강한 진단 근거지만, 단 한 번의 OOM pilot만으로 RSS
변화 전체를 point stride 하나의 보편적 인과로 주장하지 않는다.

러너도 임무 중 `fsm_node`나 filter가 종료되면 timeout 끝까지 기다리지 않고 해당
attempt를 infrastructure retry하도록 보강했다. OOM pilot 원시는
`results/adaptive_cpp_strict_v7_n1_oom_pilot_20260823.csv`, layout 수정 seed4 smoke는
`results/adaptive_cpp_strict_v7_seed4_layoutfix_smoke_20260823.csv`다.

## seed별 CPU cohort 결과

조건은 v=7, `loop24.txt`, timeout 240 s,
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, static PCD,
`strict-burst`, C++ backend다.

| seed | raw/static-safe | 시간 | live/static episode | static body clearance | filter CPU |
|---:|---:|---:|---:|---:|---:|
| 1 | 1/1 · 1/1 | 63.83 s | 0 / 0 | +0.257 m | 2.323% |
| 2 | 1/1 · 1/1 | 67.08 s | 0 / 0 | +0.330 m | 2.308% |
| 3 | 1/1 · 1/1 | 71.21 s | 0 / 0 | +0.326 m | 2.414% |
| 4 | 1/1 · 1/1 | 86.41 s | 0 / 0 | +0.297 m | 2.505% |
| 5 | 1/1 · 1/1 | 100.94 s | 0 / 0 | +0.257 m | 2.649% |
| 6 | 1/1 · 1/1 | 100.98 s | 0 / 0 | +0.204 m | 2.784% |
| 7 | 1/1 · 1/1 | 112.40 s | 0 / 0 | +0.242 m | 2.918% |
| 8 | 1/1 · 1/1 | 93.28 s | 0 / 0 | +0.240 m | 2.873% |
| 9 | 1/1 · 1/1 | 103.94 s | 0 / 0 | +0.252 m | 3.158% |
| 10 | 1/1 · 1/1 | 113.47 s | 1 / 0 | +0.121 m | 3.151% |

seed10 live event는 mission 2.7325 s, speed 0.627 m/s에서 centre distance
0.1995 m로 0.2 m threshold를 0.5 mm 넘은 경계 사례다. 이벤트 위치는
`(5.629, 3.430, 0.878)`이다. 같은 run의 고정 static PCD 최소 centre distance는
0.321 m, body clearance는 +0.121 m, static contact는 0이다. 그래서 물리 map
침범으로 분류하지 않지만 live detector 0이라고도 기록하지 않는다. 첫 독립 C++
cohort의 seed10은 live/static 모두 0이었다.

## 가중 연산량

아래 값은 run 평균이 아니라 mission time 또는 map update 수로 가중했다.

| cohort | input/publish/map Hz | 처리점/update | 처리량 | mapping/update | mapping work/mission | FSM/filter/합계 CPU-work |
|---|---:|---:|---:|---:|---:|---:|
| Full direct n=50 | - / - / 2.977 | 27,158.8 | 80.858 kpts/s | 22.972 ms | 8.044 s | 55.922 / 0 / 55.922 s |
| Adaptive Python n=50 | 6.509 / 4.188 / 3.132 | 19,223.0 | 60.197 kpts/s | 15.528 ms | 4.320 s | 53.512 / 10.582 / 64.095 s |
| **Adaptive C++ n=10** | 5.577 / 3.725 / 2.998 | 19,978.3 | 59.900 kpts/s | 16.385 ms | 4.488 s | 52.037 / 2.522 / **54.559 s** |

C++ Adaptive의 Full 대비 변화는 처리점/update **-26.44%**, 처리량
**-25.92%**, mapping/update **-28.67%**, mission당 mapping work **-44.21%**,
FSM+filter CPU-work **-2.44%**다. Python 대비 filter work는 **-76.17%**,
전체 CPU-work는 **-14.88%**다. 이 n=10 관측은 C++ 전환 방향이 맞다는 smoke
gate이며 n=50의 분산이나 population 성능을 대신하지 않는다.

원시는 기능 cohort
`results/adaptive_cpp_strict_v7_n1_packed_raw_20260823.csv`, CPU cohort
`results/adaptive_cpp_strict_v7_n1_cpu_raw_20260823.csv`, 집계는
`results/adaptive_cpp_strict_v7_n1_summary_20260823.csv`다. 모든 CIRI raw-cloud
shadow 설정은 default false로 유지했고 실제 brake 결정에 연결하지 않았다.
