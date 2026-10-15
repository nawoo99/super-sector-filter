# C++ 동일 프로세스 raw guard handoff와 Map7/9/10 n=3

날짜: 2026-09-01

## 1. 목적

이 단계의 목적은 filtered Adaptive가 near-field 안전 검사를 위해
`/cloud_registered`를 별도로 다시 구독하던 구조를 제거하는 것이다. 기존
pre-filter raw enforce는 Map1-10 n=10에서 Adaptive 100/100 완주·충돌 0을
달성했지만, ROG-Map용 `/cloud_sector` 외에 full raw PointCloud2가 FSM으로 한
번 더 DDS 전달되므로 전체 통신량 감소를 주장할 수 없었다.

## 2. 검토한 구조

### 2.1 외부 bounded witness — 기각

Native C++ filter에 360도 반경 crop인 `/cloud_guard_witness`를 추가하고 FSM의
recent-hit worker만 이 topic을 받게 했다. 기능과 안전은 smoke에서 확인됐지만
Map7의 8 m witness는 약 93.5%, 5 m witness도 약 80.7%의 점을 보존했다. 5 m
Adaptive smoke의 witness만 3.414 MiB/s였고, corrected Full/Sector/Adaptive
n=1에서 Adaptive logical algorithm delivery는 11.113 MiB/s로 Full
4.135 MiB/s보다 컸다. 공간 crop만으로는 near-field worker가 필요로 하는
시간창 전체의 lateral witness를 충분히 작게 만들 수 없었다.

또한 첫 3-mode 시도는 Sector에도 Adaptive 전용 witness hard gate를 연결해
순수 ablation을 훼손했다. 이어진 maps7/9/10 n=3 시도에서 Map7 Sector가 초기
brake trajectory의 측정 overspeed 7.074 m/s로 speed-invalid가 되어 즉시
중단했다. 이후 runner에 `--seedmap-adaptive-super-config`를 추가해 Sector는
`static_seedmaps_guard_viability_tight_v7_filtered_reliable.yaml`, Adaptive만
near-field raw guard profile을 쓰도록 분리했다. 이 중단 결과는 최종 성능
증거로 사용하지 않는다.

### 2.2 동일 프로세스 bounded witness — 기능 확인 후 대체

Filter와 FSM을 한 executable에 composition하여 filtered map과 witness의 추가
DDS hop을 없앴다. Map7 Adaptive smoke는 안전 완주했지만, 5 m witness 자체가
여전히 큰 logical PointCloud2였다. 복사 위치만 바뀌었을 뿐 불필요한 crop cloud
생성과 처리량은 남았다.

### 2.3 동일 SharedPtr raw handoff — 채택 후보

최종 구조는 sensor raw cloud를 받은 filter callback이 동일
`sensor_msgs::msg::PointCloud2::SharedPtr`를 FSM의 기존 bounded raw-window
ingest 함수로 직접 넘긴다.

```text
simulator --DDS raw 1회--> native C++ filter
                              |-- filtered map --> ROG-Map (intra-process)
                              `-- same SharedPtr --> FSM raw guard window
                                                    `-- async latest-only worker
```

주요 성질은 다음과 같다.

- `fsm_node_with_sector`와 native filter를 `use_intra_process_comms(true)`로 실행한다.
- Adaptive에서만 direct guard observer를 연결한다. Sector는 순수 angular-cut
  ablation으로 유지한다.
- FSM은 injection mode일 때 dedicated raw subscriber를 만들지 않는다.
- raw cloud 데이터 버퍼를 crop/repack/republish하지 않고 같은 SharedPtr로 넘긴다.
- 무거운 누적 cloud, crop, KD-tree recent-hit 계산은 기존 asynchronous
  latest-only worker가 수행하므로 planning callback을 막지 않는다.
- 외부 bounded witness publisher는 실험 옵션으로 남지만 기본값은 off이며,
  최종 n=3에서 publish frame은 0이다.
- 표준 `tight_v7`과 실사용 filtered profile은 변경하지 않았다. 새 composition과
  near-field profile은 명시적으로 선택하는 실험 경로다.

## 3. 구현과 계측

구현 파일은 다음과 같다.

- `mission_planner/Apps/native_sector_cpp.cpp`
- `mission_planner/include/mission_planner/native_sector_cpp.hpp`
- `super_planner/Apps/fsm_node_with_sector_ros2.cpp`
- `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`
- `mission_planner/launch/benchmark_seedmap.launch.py`
- `scripts/native_campaign/native_campaign.py`

Runner는 모드별 config를 분리하고 `--filter-backend cpp-intra`를 지원한다. 새
계측은 source/filter/witness payload, DDS cloud payload, intra-process logical
payload, planner logical ingress, direct handoff count를 구분한다. CPU는 기존과
동일하게 cgroup-v2의 algorithm scope(FSM+filter)와 end-to-end scope를 사용한다.

Release build와 campaign pytest 24개, standalone C++ geometry/stats/witness
equivalence test가 통과했다.

## 4. Map7/9/10 × 3 modes × n=3

조건은 v=7, loop24, source static PCD safety, 180 s timeout, cgroup-v2
accounting이다. 최초 rotating 3-mode campaign 뒤 실험용 witness YAML의 마지막
`p_hit`, `p_max`, `unk_thresh` 설정이 원본 filtered profile에서 누락된 것을
발견했다. Full과 Sector는 별도 정상 profile이어서 영향이 없었다. 누락분을
복원하고, Adaptive는 이미 검증된 완전한
`static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearfield_enforce.yaml`
및 동일 `cpp-intra` injection으로 Map7/9/10 각 3회를 다시 실행했다. Injection
mode에서는 두 config의 source topic 차이가 무시되고 direct SharedPtr가 쓰인다.
아래 최종 비교는 최초 캠페인의 Full/Sector 18행과 수정 후 Adaptive 9행을
결합한 것이다. 27개 행 모두 first-attempt, run/perf/cgroup valid였고 retry와
OOM kill은 0이었다.

| Map | Mode | 완주 | static-safe | 속도 정상 | 평균 시간(s) | 최악 clearance(m) | 평균 map MiB/s | 평균 algorithm core | 평균 core·s | Adaptive full-open |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | Full | 3/3 | 3/3 | 3/3 | 87.343 | +0.192 | 5.238 | 0.838 | 74.827 | - |
| 7 | Sector | 3/3 | 3/3 | 3/3 | 83.543 | +0.153 | 1.695 | 0.691 | 58.823 | 0 |
| 7 | Adaptive | 3/3 | 3/3 | 3/3 | 103.597 | +0.267 | 2.682 | 0.608 | 63.960 | 10 |
| 9 | Full | 3/3 | 3/3 | 3/3 | 107.017 | +0.219 | 5.266 | 0.725 | 77.015 | - |
| 9 | Sector | 3/3 | 3/3 | 3/3 | 92.980 | +0.115 | 1.797 | 0.635 | 60.071 | 0 |
| 9 | Adaptive | 3/3 | 3/3 | 3/3 | 102.143 | +0.123 | 3.284 | 0.706 | 71.720 | 21 |
| 10 | Full | 3/3 | 3/3 | 3/3 | 87.047 | +0.189 | 6.800 | 0.926 | 81.969 | - |
| 10 | Sector | 3/3 | 2/3 | 3/3 | 103.757 | -0.065 | 1.689 | 0.580 | 61.040 | 0 |
| 10 | Adaptive | 3/3 | 3/3 | 3/3 | 107.913 | +0.199 | 3.013 | 0.615 | 67.727 | 11 |

전체 Full/Sector/Adaptive는 완주 9/9, 9/9, 9/9이고 static-safe는 9/9,
8/9, 9/9이다. Sector의 Map10 run3은 완주했지만 source static PCD 최소 거리가
0.135 m로 robot radius 0.20 m 안에 들어가 clearance -0.065 m의 접촉 1회를
기록했다. Full과 Adaptive는 접촉 0이다. 모든 행은 7.0+0.01 m/s 속도 기준을
만족했다.

Adaptive는 Full 대비 다음과 같았다.

- 평균 임무 시간: 93.802 -> 104.551 s, +11.459%
- ROG-Map payload rate: 5.768 -> 2.993 MiB/s, -48.107%
- algorithm mean cores: 0.829 -> 0.643, -22.492%
- algorithm core-seconds: 77.937 -> 67.802, -13.003%
- end-to-end mean cores: 1.019 -> 0.839, -17.642%
- end-to-end core-seconds: 96.316 -> 88.763, -7.842%
- algorithm peak PSS mean: 3274.3 -> 3270.3 MiB, -0.122%; 실질적 메모리
  절감으로 주장하지 않는다.

Adaptive effective Full-open은 총 42회(Map7/9/10 10/21/11), trajectory-guard
open은 31회였다. Direct raw SharedPtr handoff는 3,764회였고 외부 witness
publish는 0회였다.

## 5. 대역폭 해석

동일 프로세스화로 사라진 것은 filter->FSM의 두 번째 full raw DDS 전송이다.
Sensor->filter의 최초 raw DDS는 여전히 필요하다. 측정된 DDS cloud rate는
Full 5.768, Adaptive 4.812 MiB/s로 표본 평균상 16.575% 낮았지만, 이는 실행별
sensor publish cadence 차이를 포함한다. 가중 source bytes/scan은 Full
1,283,985 B, Adaptive 1,251,925 B로 거의 같은 크기다. 따라서 이 구조만으로
raw sensor wire bytes/scan이 줄었다고 주장하지 않는다.

`planner_logical_ingress_mib_s`는 Full 5.768, Adaptive 7.813으로 오히려
35.465% 높다. Adaptive에서 같은 raw cloud가 safety worker에 논리적으로 한 번
소비되고 filtered map도 ROG-Map에 소비되기 때문이다. 그러나 raw 부분은
SharedPtr handoff라 추가 DDS serialization/network traffic가 아니다. 논문/발표
표에는 다음 세 항목을 섞지 않아야 한다.

1. ROG-Map processed payload: Adaptive가 48.107% 감소.
2. 실제 DDS cloud rate: 이번 n=3에서 16.575% 감소했으나 cadence 의존.
3. planner logical ingress: 35.465% 증가하지만 zero-copy 내부 소비 포함.

Raw wire bandwidth 자체를 Full보다 구조적으로 줄이려면 angular filter가
simulator/sensor publisher 앞단 또는 sensor front-end에 있어야 한다. 현재
planner-side composition의 보장 가능한 성과는 중복 DDS 제거와 ROG-Map/CPU
감소다.

## 6. Adaptive 긴 시간 꼬리

수정 후 가장 긴 행은 Map9 run3의 127.39 s였다. 이 행은 guard recovery 73회,
recovery-active 누적 83.615 s, topology reroute search 24회를 기록했다.
Adaptive 9개 표본에서 mission time과 recovery-active 누적시간의 Pearson
상관은 0.978이었다. 이 행의 algorithm core-seconds도 69.803으로 시간
증가율보다 작았으므로 긴 꼬리는 CPU starvation보다 repeated certified
stop-and-reroute의 진행성 비용으로 해석하는 것이 타당하다. n=9의 상관은
설명용 진단이며 인과 또는 population 통계로 과장하지 않는다.

## 7. 결론과 다음 단계

이 단계는 목표 방향의 작은 gate를 통과했다. Full과 Adaptive는 9/9 안전
완주했고 Sector만 실제 접촉 1회를 보였으며, Adaptive는 Full보다 ROG payload와
CPU를 줄였다. 또한 이전 raw-subscription 방식의 중복 DDS 문제를 제거했다.

다만 n=9는 population-level 100% 보장이 아니다. 다음 단계는 이 architecture를
고정한 채 Map1-10 n=10 회귀를 실행해 기존 300행과 직접 비교하는 것이다.
그 전에 긴 꼬리를 낮추려면 안전 gate를 약화하지 말고, 동일 obstacle/generation
에서 반복되는 recovery를 coalesce하고 topology search 결과를 제한된 시간 동안
재사용하는 방향을 검토해야 한다.

근거 파일:

- Full/Sector raw: `results/inprocess_raw_handoff_seed7_9_10_three_mode_n3_raw_20260901.csv`
- 수정 후 Adaptive raw: `results/inprocess_raw_handoff_corrected_adaptive_seed7_9_10_n3_raw_20260901.csv`
- `results/inprocess_raw_handoff_seed7_9_10_three_mode_n3_summary_20260901.csv`
- rejected witness/중단 요약:
  `results/inprocess_raw_guard_rejected_witness_summary_20260901.csv`
