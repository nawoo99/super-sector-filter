# Windows Codex용 전체 소스와 최종 실험 자료

이 디렉터리는 2026년 10월 15일, 논문 작성용 코드 검토를 위해 두 작업 폴더의 소스·설정·스크립트를 별도로 복사한 자료다. 기준 결과는 **2026년 10월 8일 동결한 V6 본실험 210회**다. 이번 업로드로 알고리즘을 수정하거나 실험을 다시 실행하지 않았다.

## 바로 사용할 위치

| Item | Location |
|---|---|
| Full SUPER source, configuration, messages, launch files, shaders and tests | `full_source/super_ws/src/SUPER/` |
| Workspace-specific bridge source | `full_source/super_ws/src/gz_super_bridge/` |
| Research repository source, scripts, configuration, documentation and patch mirrors | `full_source/super-sector-filter/` |
| Current final-result summary copy | `results_summary/` |
| Original frozen result and source evidence | `../results/v6_frozen_20261008/` and downloadable complete result bundle |
| SHA256 inventory and experiment-time verification status | `provenance/` |
| Prompt for Windows Codex | `WINDOWS_CODEX_PROMPT.txt` |

`full_source`에는 Git에 추적되지 않았던 구현 파일도 포함했다. 따라서 upstream SUPER를 새로 clone하거나 기존 `super_patches/`만 읽는 것으로 이 자료를 대체하지 않는다. 두 bridge 소스는 서로 다르므로 임의로 통합하지 않는다.

## GitHub 다운로드

[전체 자료 Release](https://github.com/nawoo99/super-sector-filter/releases/tag/v6-paper-handoff-20261015)에서 다음 파일을 받는다. GitHub의 **Code → Download ZIP**에는 Release 첨부물이 자동으로 포함되지 않는다.

- `super_full_source_handoff_20261015.zip`: 이 디렉터리의 소스·설정·요약·검증 자료. Windows에서 코드와 논문을 분석하려면 이것부터 사용한다.
- `super_v6_runtime_assets_20261015.zip`: 실제 7개 맵의 PCD와 관련 런타임·시각화 자산. 실행하거나 원본 맵을 검사할 때 사용한다. 코드 검토만 할 때에는 필수가 아니다.
- `codex_final_results_20261014_all.zip`: 최종 수치·함수별 CPU 계측·전체 상세 통계·원본 기록 4,720개와 환경 지도. 본실험 210회와 별도 사전시험 30회를 구분해 보존한 최신 전체 결과 묶음이다.
- `SHA256SUMS.txt`: Release ZIP의 SHA256. 파일별 목록은 소스의 `provenance/`와 각 결과 묶음의 기존 manifest를 따른다.

권장 Windows 폴더는 `C:\research\super`처럼 짧은 경로다. 소스 ZIP과 결과 ZIP을 그 아래에 해제하고 Codex에서 두 디렉터리를 함께 읽는다. 런타임 자산 ZIP은 소스 ZIP의 `paper_handoff_20261015` 디렉터리 안에 풀면 `full_source/` 하위의 원래 상대 경로로 합쳐진다. 자세한 파일 대응은 `provenance/runtime_assets.json`에 있다.

## 먼저 읽을 자료

1. 이 문서와 `provenance/snapshot_summary.json`에서 소스 범위·제외 항목·실험 당시 검증 상태를 확인한다.
2. `results_summary/00_READ_ME_FIRST.md`와 `02_implementation_clarifications.md`에서 최종 결과와 식 (4)·(5)의 정정 사항을 확인한다.
3. `results_summary/01_final_results.md`, `08_cpu_without_simulator.md`와 `data/`의 CSV·JSON을 읽는다.
4. 실제 구현을 설명할 때 `full_source/super_ws/src/SUPER/`의 코드와 모드별 설정을 대조한다.
5. 요약으로 확인할 수 없는 항목만 전체 결과 ZIP의 원본 기록을 추가로 읽는다.

`results_summary/`는 전체 결과 묶음의 **선별 복사본**이다. 원본 기록·대용량 시계열이 모두 들어 있는 것처럼 취급하지 않는다. 원래 문서의 일부 상대 링크는 전체 결과 ZIP에서만 열린다. 이 선별본의 파일 목록과 원본 SHA256는 `provenance/result_summary_inventory.json`을 따른다.

## 실험 당시 소스와 현재 복사본의 차이

SUPER의 Git 기준 커밋은 `2ad3419c127a617c6d7df6925e81a14175a9c096`, 연구 저장소의 업로드 전 기준 커밋은 `f8668945862f71185fc695360467f148f8273d77`이다. SUPER 원격은 원본 `hku-mars/SUPER`이나 **이번 업로드는 사용자 저장소 `nawoo99/super-sector-filter`에만 수행한다**.

동결된 `source_manifest.json`은 실행 바이너리·설정·일부 직접 소스·설치 헤더·결과 기록을 고정했지만 전체 소스 파일을 모두 고정한 목록은 아니다. 현재 소스와 동결 파일의 경로 대응 및 SHA256가 일치하는 파일은 개별 검증 상태를 기록했다. 검증 표시가 없는 파일을 실험 당시 버전과 완전히 동일하다고 단정하면 안 된다. 현재 복사본 전체를 실험 시점에 생성한 완전한 Git commit이나 재빌드까지 입증된 배포본이라고 부르지 않는다.

설치된 헤더·설정에서 역으로 확인한 경우에는 그 대응 경로를 남겼다. 파일 내용의 해시가 우연히 다른 파일과 같다는 사실만으로 검증 처리하지 않는다. 실제 실행 overlay는 `/root/super_ws/forest_liveness_trial_v6_20261006/install`이었다. Windows는 코드·결과 분석 환경이며, ROS 실행은 별도 Ubuntu/ROS 2 Humble 환경과 의존성·GPU/OpenGL 설정이 필요하다. 이 업로드에서는 새 환경 재빌드를 시험하지 않았다.

## 구현을 읽는 시작점

| Concern | SUPER-relative path |
|---|---|
| Native frontend and mode handling | `mission_planner/Apps/native_sector_cpp.cpp` |
| FSM, guard and recovery integration | `super_planner/include/ros_interface/ros2/fsm_ros2.hpp` |
| Common planner and certified recovery | `super_planner/src/super_core/` |
| Simulator acquisition and composed frontend | `mars_uav_sim/perfect_drone_sim/` and `mars_uav_sim/marsim_render/` |
| Actual V6 campaign settings | `mars_uav_sim/perfect_drone_sim/scripts/scenario7_topology_liveness_v6_cpu_compare.py` |
| Campaign invocation wrapper | research repository `scripts/native_campaign/run_topology_liveness_v6_trial.sh` |

현재 소스는 이미 ROS 2용으로 선택된 상태다. `scripts/select_ros_version.sh`를 다시 실행하면 활성 CMake/package 정의를 덮어쓸 수 있으므로, 이 자료를 읽기 위해 실행하지 않는다.

소스의 모든 파일별 해시는 `full_source/source_inventory.json`, 제외 목록은 `full_source/source_exclusions.json`, Git 상태와 동일성 한계는 `full_source/source_provenance.json`에 있다. 압축 해제 후 `python provenance/verify_handoff.py`로 자료를 읽기 전용 검증할 수 있다(Python 3.9 이상). 런타임 자산도 같은 디렉터리에 해제했다면 `--with-runtime-assets`를 추가한다. 이 검증은 파일 동일성 검사이며 새 환경에서 재빌드·실행의 성공을 보장하지 않는다.

## 결과 해석의 고정 기준

- 본실험은 7개 맵 × 3개 모드 × 10회인 210회다. Full·Adaptive는 각각 70/70회 무접촉 완주했다. Active-Yaw Sector는 목표 도달 68/70, 접촉 주행 2/70, 무접촉 완주 67/70이다.
- Normal 1–5의 비용 평균은 모드당 50회, Urban과 Forest는 각각 10회로 분리한다. 별도 Forest 사전시험 30회를 합치지 않는다.
- 목표 도달, 접촉, 미완주는 별도 지표다. 접촉 없는 미완주를 충돌로 바꾸지 않는다. 관측된 100%는 모집단 보장이 아니다.
- CPU 사용량, 누적 CPU 시간, 지도 처리 경과시간, 입력량, 메모리를 구분한다. 추가된 ‘시뮬레이터 제외 CPU’는 계측 함수의 exclusive CPU 소계이며, 미계측 부분까지 포함한 완전한 자율주행 CPU가 아니다.
- Adaptive의 복구 관측은 Full 360°다. Active-Yaw Sector의 yaw 탐색과 같은 동작으로 쓰지 않는다. 식 (5)의 복귀에는 별도 탈출 해제 조건도 필요하다. 자세한 내용은 구현 정정 문서를 우선한다.
- 최종 환경은 MARSIM/PerfectDrone의 정적 시나리오다. 과거 Gazebo/PX4 설명, 다른 알고리즘, 다른 맵의 blind-zone stress 결과와 섞지 않는다.

## 제외 항목과 라이선스

빌드·install·log 캐시, 실행 바이너리, Git 내부 이력, 무관한 과거 실험, 모든 과거 PCD, 영상, 제3자 논문 PDF는 소스 복사본에서 제외했다. 기존 로컬 파일은 삭제하지 않았다. 실험 원본 기록과 7개 맵 자산은 별도 Release ZIP으로 보완한다.

SUPER 및 vendor 코드의 저작권·라이선스 표시는 각 파일·package.xml의 기존 표시를 보존했다. SUPER 루트에는 원래 LICENSE 파일이 없어 새로운 일괄 라이선스를 부여하지 않았다. 원저자 표시나 vendor 라이선스를 삭제하고 자체 독자 코드라고 주장하지 않는다.
