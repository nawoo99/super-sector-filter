# Sensor-front-end cadence/enforcement final campaign (2026-09-02)

## 1. 목적과 범위

이 단계는 sensor-front-end 구조에서 다음 다섯 항목을 순서대로 검증했다.

1. simulator source, native filter input/publish, ROG commit과 trajectory generation
   cadence를 같은 run에서 계측한다.
2. Adaptive filtered-cloud publish와 heavy trajectory-risk 평가를 각각 5 Hz로
   제한한다.
3. Map7/9/10 세 모드 n=3 gate에서 완주·충돌·CPU·대역폭을 확인한다.
4. 무제한 L-BFGS가 드물게 수 GiB까지 증가하던 경로에 2,048 iteration 상한을
   둬 OOM을 bounded failure로 바꾼다.
5. compact verdict enforcement의 generation/freshness/range gate를 wrong-generation,
   stale, fresh OCCUPIED fault로 검증한 뒤 Map1-10 × 3 modes × n=10을 실행한다.

코드는 `/root/super_ws/src/SUPER`에서 변경했고 mirror만 이 저장소에 보관했다.
표준 `tight_v7` profile과 실사용 profile은 바꾸지 않았다. Enforcement는 별도
실험 profile
`static_seedmaps_guard_viability_tight_v7_frontend_risk_enforce.yaml`에서만 켰다.

## 2. 선택된 구조와 사전 gate

Sensor raw generation은 약 10 Hz로 유지한다. Sector/Adaptive는 raw cloud DDS
publisher를 만들지 않고, simulator와 native filter 사이에서 SharedPtr를 직접
넘긴다. Sector filtered map은 10 Hz, Adaptive filtered map과 무거운 future-tail
risk check는 각각 5 Hz다. Risk worker는 latest-only라 sensor callback이나 FSM
100 Hz loop를 동기적으로 막지 않는다.

4.5 Hz는 선택 gate에서 기각했고 5 Hz를 채택했다. Map7/9/10 n=3의 27행은 모두
완주·충돌 0이었다. Adaptive는 Full 대비 planner ingress를 크게 줄였지만 세 map
평균 algorithm core-seconds 감소는 일관되지 않아, 최종 campaign에서 cgroup
전체를 다시 측정했다.

Optimizer `max_iterations=256`은 정상 경로까지 자주 끊어 Map7 Full이 133.88초로
늘어 기각했다. `2048`은 드문 발산 경로만 bounded failure로 만들었고 smoke에서
PSS를 약 3.2 GiB로 유지했다. 최종 300행에서도 OOM은 0이었다.

Fault gate 결과는 다음과 같다.

- wrong generation request `9000000000`: `generation_match=false`, IGNORE, 안전 완주
- stale request `9000000000`: `fresh=false/source_fresh=false`, IGNORE, 안전 완주
- fresh request `9000000000`: BRAKE, 0.680초 certified brake 발행 후 복구·안전 완주
- natural enforce Map7/9/10 n=1: 3/3 완주·충돌 0

이는 gate 배선이 의도대로 작동한다는 기능 증명이지 모든 접촉을 제때 검출한다는
증명은 아니다.

## 3. 최종 300회 결과

조건은 v=7, loop24, source static PCD 권위 판정, 180초 timeout, rotating mode
order, cgroup v2 accounting이다. CSV는 300행, 고유 `(map, run, mode)` 300개,
campaign sequence 1--300이며 run/speed/performance/cgroup validity가 모두
300/300이다. Retry와 OOM은 각각 0이다.

| Map | Mode | 완주 | 충돌 | 평균시간(s) | 최소 clearance(m) | Adaptive Full-open | Algo core·s | planner ingress MiB/s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Full | 10/10 | 0 | 64.82 | +0.250 | - | 70.74 | 3.449 |
| 1 | Sector | 10/10 | 0 | 58.18 | +0.189 | - | 64.05 | 1.629 |
| 1 | Adaptive | 10/10 | 0 | 58.10 | +0.219 | 133 | 64.32 | 1.352 |
| 2 | Full | 10/10 | 0 | 59.80 | +0.230 | - | 67.76 | 3.519 |
| 2 | Sector | 10/10 | 0 | 54.54 | +0.201 | - | 60.76 | 1.452 |
| 2 | Adaptive | 10/10 | 0 | 54.16 | +0.246 | 212 | 59.11 | 1.128 |
| 3 | Full | 10/10 | 0 | 69.31 | +0.158 | - | 67.59 | 3.877 |
| 3 | Sector | 10/10 | 0 | 57.17 | +0.196 | - | 64.56 | 2.276 |
| 3 | Adaptive | 10/10 | 0 | 57.22 | +0.247 | 229 | 63.06 | 1.665 |
| 4 | Full | 10/10 | 0 | 80.24 | +0.217 | - | 70.67 | 3.984 |
| 4 | Sector | 10/10 | 0 | 63.86 | +0.182 | - | 70.10 | 2.640 |
| 4 | Adaptive | 10/10 | 0 | 60.26 | +0.156 | 167 | 68.09 | 2.023 |
| 5 | Full | 10/10 | 0 | 72.99 | +0.184 | - | 70.06 | 4.424 |
| 5 | Sector | 10/10 | 0 | 59.87 | +0.158 | - | 67.66 | 2.813 |
| 5 | Adaptive | 10/10 | 0 | 59.03 | +0.244 | 211 | 65.49 | 2.065 |
| 6 | Full | 10/10 | 0 | 78.94 | +0.152 | - | 72.16 | 4.644 |
| 6 | Sector | 10/10 | 0 | 65.05 | +0.151 | - | 72.91 | 3.335 |
| 6 | Adaptive | 10/10 | 0 | 63.55 | +0.174 | 198 | 70.91 | 2.438 |
| 7 | Full | 9/10 | 0 | 100.18 | +0.224 | - | 82.34 | 5.158 |
| 7 | Sector | 10/10 | 0 | 68.66 | +0.221 | - | 75.00 | 4.058 |
| 7 | Adaptive | 9/10 | 0 | 76.32 | +0.194 | 138 | 84.33 | 2.750 |
| 8 | Full | 10/10 | 0 | 82.45 | +0.193 | - | 66.23 | 4.518 |
| 8 | Sector | 10/10 | 0 | 62.49 | +0.180 | - | 69.67 | 3.503 |
| 8 | Adaptive | 10/10 | 0 | 63.01 | +0.223 | 218 | 69.46 | 2.572 |
| 9 | Full | 10/10 | 0 | 92.58 | +0.126 | - | 75.49 | 6.094 |
| 9 | Sector | 10/10 | 0 | 70.97 | +0.199 | - | 77.81 | 4.888 |
| 9 | Adaptive | 10/10 | 0 | 75.99 | +0.140 | 199 | 80.85 | 3.527 |
| 10 | Full | 10/10 | 0 | 98.20 | +0.160 | - | 77.68 | 5.912 |
| 10 | Sector | 10/10 | 0 | 70.56 | +0.157 | - | 76.81 | 4.714 |
| 10 | Adaptive | 10/10 | 1 | 72.90 | -0.149 | 195 | 79.12 | 3.476 |

전체 completion은 Full/Sector/Adaptive `99/100/99`, source-static-PCD collision은
`0/0/1`이다. Adaptive effective Full-open은 1,900회, trajectory-guard open은
320회였다. Front-end는 17개 OCCUPIED verdict를 만들었고 10회 enforcement brake가
기록됐다.

전체 평균에서 Adaptive는 Full 대비 mission time 19.883%, planner ingress
49.547%, algorithm core-seconds 2.219%를 줄였다. 반면 end-to-end core-seconds는
1.900% 증가했고 algorithm mean cores도 18.483% 높았다. 짧은 실행시간 때문에
동시에 더 많은 thread를 사용한 결과다. Map7--10에서는 algorithm core-seconds가
각각 2.424%, 4.872%, 7.098%, 1.849% 증가했다. 따라서 현재 주장 가능한 것은
약 50%의 logical planner ingress 감소와 작은 전체 algorithm work 감소이며,
모든 맵에서의 computation 감소나 end-to-end compute 감소가 아니다. PSS 감소도
0.354%라 실질적인 memory contribution이 아니다.

Full/Sector/Adaptive 평균 sensor cadence는 9.953/10.000/9.925 Hz다. Adaptive
filtered publish와 risk verdict는 5.015/4.961 Hz였고 평균 heavy-risk compute는
4.106 ms였다. 이 값은 선택한 5 Hz cap이 실제 runtime에서도 지켜졌음을 보인다.

## 4. Map7 timeout 두 건: 자원 압박이 증폭한 topology liveness trap

Map7 run1 Full과 Adaptive는 각각 waypoint 2/5에서 183.54/182.96초 timeout됐다.
충돌과 OOM은 없었다. 두 행에서 host available memory 최저는 230.75/289.13 MiB,
memory PSI full 최대는 53.55/64.20%였다. 외부 VS Code extension host가 약 8 GiB,
swap 2 GiB가 포화된 상태였다.

Full log에서는 정지점 `[-24.075,-12.975,1.625]`에서 optimization overtime,
exclusion zone 누적, A* NO_PATH, epoch reset이 반복됐다. Adaptive도 같은 waypoint에
머물며 reroute arm/search 21/52회를 기록했다. 따라서 알고리즘 liveness trap은
실재하지만 극심한 memory reclaim가 각 replan을 지연시켜 timeout까지 증폭했다.

세션 재시작 뒤 available memory가 약 3.5 GiB로 회복된 상태에서 Map7 run2--10은
Full/Sector/Adaptive 모두 9/9, 9/9, 9/9 완주했다. 원자료의 두 실패를 삭제하거나
성공으로 바꾸지 않는다. `PSI full >= 50%` sensitivity에서는 두 행만 오염으로
분류되고 resource-normal Full/Adaptive completion은 각각 99/99다. 이는 원래
300회 결과를 100%로 바꾸는 근거가 아니라 infrastructure sensitivity 분석이다.

Optimizer 2,048 cap은 목적대로 작동했다. 300행에서 cap hit는
Full/Sector/Adaptive 348/339/290회였지만 peak PSS는 평균 약 3.18--3.19 GiB,
OOM/retry는 0이었다. Cap은 memory blow-up을 막았지만 topology liveness를 보장하지
않는다.

## 5. Map10 Adaptive 접촉: 5 Hz와 generation 전환 사이의 검출 공백

Map10 run6 Adaptive는 완주했지만 static PCD 접촉 1회가 발생했다. 첫 접촉은
epoch `1788319894.081619`, 속도 0.06539 m/s, clearance -0.11906 m였고 최저값은
-0.14855 m였다. Host available memory는 2.20 GiB 이상, PSI full은 0이라
infrastructure 오염이 아니다.

접촉 직전 gen34 trajectory는 filtered map guard에서 계속 SAFE였다. CIRI는
`min dis ... 0.01089` infeasible 경고를 냈지만 endpoint에 가까운 gen35/36의 아주
짧은 잔여 segment가 commit됐다. First OCCUPIED는 contact 99 ms 뒤인
`1788319894.181045`에 gen36/cloud159/min 0.1020 m로 도착했다. 그 사이 gen37이
commit되어 이 결과는 generation mismatch/time-uncovered로 무시됐다. Gen37의
OCCUPIED는 `1788319894.415066`, enforcement는 `1788319894.421832`였으므로 이미
접촉 뒤였다. Brake/recovery는 이후 정상 작동해 추가 접촉 없이 완주했다.

이는 freshness/generation gate가 잘못 구현된 것이 아니라, 5 Hz heavy check의
최대 약 200 ms 간격과 endpoint generation churn이 합쳐진 coverage gap이다.
미래 trajectory 결과에는 exact-generation 계약이 필요하지만, source-fresh한
현재 body occupancy는 generation이 바뀌어도 위험하다. 다음 수정은 다음 두 tier로
분리해야 한다.

1. 매 sensor frame(약 10 Hz)에 current body와 매우 짧은 horizon만 검사하는
   저비용 priority verdict를 만든다. 이 결과는 source/result freshness와 witness가
   현재 footprint/short horizon 안에 있다는 조건으로 generation-independent hold를
   허용한다.
2. 기존 KD-tree future-tail 검사는 5 Hz와 exact generation/range 계약을 유지한다.
3. 현재 body tier가 OCCUPIED면 새 trajectory commit보다 먼저 certified hold를
   latch하고, fresh clear scan과 안전 egress 조건 전에는 해제하지 않는다.

단순히 heavy worker를 다시 10 Hz로 올리면 CPU contribution을 잃고 worst-case
46.4 ms 계산이 source callback backlog를 만들 수 있어 우선안이 아니다.

## 6. 결론과 주장 경계

이번 다섯 단계와 300회 campaign으로 확인된 사항은 다음과 같다.

- Sensor-front-end raw DDS 제거, compact verdict와 5 Hz cadence는 정상 작동한다.
- 300행 모두 cgroup/performance/speed-valid이고 retry/OOM은 0이다.
- Adaptive는 Full 대비 planner ingress 약 49.5%, mission time 약 19.9%, algorithm
  core-seconds 약 2.2%를 줄였다.
- Full/Adaptive 100% 완주·Adaptive 충돌 0 목표는 달성하지 못했다. 원자료에는
  memory-pressure timeout 두 건과 Adaptive endpoint 접촉 한 건이 있다.
- Sector가 이번 campaign에서 100/100·충돌 0이므로, 이 표본은 Sector 열화를
  입증하지도 않는다.

Full completion 99/100과 Adaptive completion/safety 99/100의 Wilson 95% 하한은
약 94.55%다. Sector 100/100의 하한도 약 96.30%이지 population 100% 보장이 아니다.
Full/Adaptive completion discordance는 0이고, Sector-vs-Adaptive completion 및
safety discordance는 각각 한 방향 한 건뿐이라 exact two-sided McNemar p=1.0이다.
통계적 안전 우위로 표현하면 안 된다.

근거 파일:

- raw: `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_raw_20260901.csv`
- map/mode summary:
  `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_summary_20260902.csv`
- Adaptive-vs-Full reductions:
  `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_reductions_20260902.csv`
- selected contact log:
  `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_20260901_forensics/seed10_run6_adaptive.attempt1.stack.log`
- selected contact monitor:
  `results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_20260901_forensics/seed10_run6_adaptive.json`
