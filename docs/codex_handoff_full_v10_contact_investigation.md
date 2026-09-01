# Codex 인계 문서 — SUPER `full` 모드 v=10 잔여 접촉 조사 (2026-08-13)

> [!IMPORTANT]
> **2026-09-01 sensor-front-end raw DDS 제거와 compact risk verdict gate 완료.**
> `perfect_drone_frontend_node`가 simulator와 native filter를 compose해 renderer의
> raw `PointCloud2::SharedPtr`를 직접 넘긴다. Sector/Adaptive에서는
> `/cloud_registered` publisher 자체를 만들지 않고, Sector는 filtered cloud만,
> Adaptive는 filtered cloud와 generation/freshness가 포함된 compact trajectory-
> risk verdict만 DDS로 보낸다. 실제 직렬화 verdict는 정확히 180 bytes/message다.
> Angular filter와 risk check는 각각 독립 latest-only worker라 sensor callback과
> planner callback을 동기적으로 막지 않는다.
>
> v=7 Map7/9/10 × Full/Sector/Adaptive × n=1 architecture gate의 9행은 모두
> first-attempt 완주, source-static-PCD collision 0, retry/OOM 0이었다. 세 map
> 평균에서 Adaptive의 DDS cloud rate는 Full보다 18.085% 낮고 verdict를 포함해도
> 약 0.044%만 추가됐다. 다만 **연산량 감소는 아직 성립하지 않는다.** 이 gate의
> Adaptive FSM core-seconds는 Full보다 10.677% 높았고, Full ROG 처리율
> 3.82~4.49 Hz와 front-end Sector 약 10.20~10.34 Hz의 cadence 차이가 confound다.
> 따라서 현재 contribution은 raw sensor DDS의 구조적 제거와 작은 검증 계약이며,
> computation 절감은 동일 accepted-generation/sensor cadence에서 재검증해야 한다.
>
> 표준 `tight_v7` profile은 변경하지 않았고 verdict enforcement는 default false다.
> 다음은 안전 threshold가 아니라 front-end publish/ROG commit cadence를 정합한 뒤
> completion/contact를 유지하는 최소 callback rate를 찾는 단계다. 상세는 viability
> §8.47과 `docs/sensor_frontend_risk_verdict_20260901.md`, 원자료는
> `results/frontend_risk_shadow_maps7_9_10_three_mode_n1_raw_20260901.csv` 및
> `results/frontend_risk_cpu_map7_three_mode_n1_raw_20260901.csv`다.

> [!IMPORTANT]
> **2026-09-01 C++ 동일 프로세스 zero-copy raw guard handoff 완료.**
> 외부 bounded witness는 8m에서 점 약 93.5%, 5m에서도 약 80.7%를 남겨
> 대용량 side-channel을 충분히 줄이지 못했다. 최종 구조는 native filter와
> FSM을 compose하고, filter가 받은 raw `PointCloud2::SharedPtr` 자체를 Adaptive
> FSM raw-window ingest에 직접 넘긴다. Injection mode에서는 FSM의 별도 full-raw
> subscriber를 만들지 않고, 외부 witness도 publish하지 않는다. 무거운 검사는
> 기존 async latest-only worker에 남는다. Sector에는 observer를 연결하지 않아
> 순수 angular-cut ablation을 유지한다.
>
> 최초 rotating campaign 뒤 witness YAML 끝의 `p_hit/p_max/unk_thresh` 누락을
> 발견해 복원했다. Full/Sector 18행은 영향이 없고, Adaptive는 완전한 기존
> raw-enforce profile+동일 injection으로 Map7/9/10 각 3회를 다시 실행했다.
> 결합한 최종 27행은 모두 first-attempt, run/perf/cgroup-valid이고
> retry/OOM/speed violation 0이었다. Completion은 모두
> 9/9, source-static-PCD safety는 9/9, 8/9, 9/9이다. Sector Map10 run3만
> clearance -0.065m 접촉 1회였고 Full/Adaptive는 충돌 0이다. 평균시간은
> 93.802/93.427/104.551초다. Adaptive는 Full 대비 ROG payload 48.107%, algorithm
> mean core 22.492%, core·s 13.003%, end-to-end core·s 7.842% 감소했고 시간은
> 11.459% 늘었다. Effective Full-open 42회, direct SharedPtr handoff 3,764회,
> external witness publish 0회다.
>
> DDS cloud rate는 표본상 16.575% 낮지만 raw bytes/scan은 거의 같고 simulator
> cadence 영향을 받는다. 주장 가능한 것은 두 번째 full-raw DDS hop 제거와
> ROG/CPU 감소이지 sensor wire bytes/scan 감소가 아니다. Logical planner
> ingress는 zero-copy 소비까지 합산해 오히려 35.465% 높으므로 wire bandwidth로
> 해석하면 안 된다. Adaptive 127.39초 tail은 recovery 73회·active 83.615초였고,
> n=9에서 시간과 recovery-active 누적의 상관은 0.978이었다. 다음은 안전 gate를
> 약화하지 않는 same-obstacle/generation recovery coalescing과 Map1-10 n=10이다.
> 상세는 viability §8.46 및
> `docs/inprocess_raw_guard_handoff_20260901.md`다. Full/Sector raw와 combined
> summary는 `results/inprocess_raw_handoff_seed7_9_10_three_mode_n3_{raw,summary}_20260901.csv`,
> corrected Adaptive raw는
> `results/inprocess_raw_handoff_corrected_adaptive_seed7_9_10_n3_raw_20260901.csv`다.

> [!IMPORTANT]
> **2026-09-01 pre-filter raw witness enforce와 최종 n=10 완료.**
> Map7 Sector run7 포렌식에서 장애물 방향이 속도 기준 약 +92.2도, live
> candidate가 +70.1도로 ±60도 sector 밖임을 확인했다. Passage soft cost가
> 아니라 lateral raw witness 누락이 우선 원인이었다.
>
> 새 `fsm/trajectory_guard/raw_cloud/source_topic`으로 실험용 filtered profile의
> ROG-Map은 `/cloud_sector`, 비동기 recent-hit worker는 `/cloud_registered`를
> 받는다. 표준 tight_v7은 그대로고 raw CIRI/passage cost는 off다. Map7 Full
> enforce n=20은 20/20 완주·safe, brake 0이었고 maps7/9/10 3모드 n=3은
> 27/27 완주·safe, retry 0이었다. Sector는 OCCUPIED 18건을 brake했다.
>
> 최종 rotating Map1-10 × Full/Sector/Adaptive × n=10은 completion
> 100/99/100, source-static-PCD safety 100/98/100이다. Full/Adaptive는 각
> 100/100 완주·충돌 0이다. Sector는 Map7/10 접촉 각 1회와 Map8 timeout
> 1회가 나왔다. 평균시간은 78.640/77.061/81.769초, worst clearance는
> +0.101/-0.168/+0.117m다. Adaptive는 Full 대비 ROG payload 45.746%,
> 평균 algorithm CPU core 8.962%, algorithm core·s 5.086%를 줄였고 시간은
> 3.979% 늘었다. Effective Full-open은 999회다.
>
> Map5 Adaptive 첫 attempt는 global OOM으로 종료 후 retry 성공했다(FSM anon
> RSS 약 6.60GiB, swap 포화, 외부 Node 약 4.9GiB). 따라서 최종 planner 행은
> 300개지만 infrastructure first-attempt 안정성은 299/300이다.
>
> **대역폭 주의:** 위 payload는 ROG-Map 입력만 포함한다. FSM이 full raw를
> 별도 구독하므로 전체 통신량 감소는 아직 주장할 수 없다. 다음은 bounded
> witness side-channel/in-filter verdict로 중복 raw 구독을 제거하고 total
> subscriber bytes를 계측하는 것이다. 100/100 Wilson 하한은 96.30%,
> Sector-unsafe/Adaptive-safe 2건의 exact McNemar p=0.5라 population 보장이나
> 유의한 안전 우위도 아니다. 상세는 viability §8.45와
> `docs/nearfield_prefilter_raw_final_20260901.md`, raw/summary는
> `results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_{raw,summary}_20260901.csv`다.

> [!IMPORTANT]
> **2026-08-31 near-field hard gate 4단계와 passage 계측 완료.**
> Long-lived trajectory도 새 accepted raw scan을 0.10초 cadence로 latest-only
> 검사한다. Map7 Full smoke에서 331건(NEW_SCAN 183, NEW_GENERATION 148)을
> skip 없이 처리했고 worker 평균/최대는 5.601/23.933ms였다.
>
> Worker-private deterministic replay로 r=0.20 future-tail OCCUPIED를 정확히
> 1건 검출했다. Default-off hard gate는 committed generation 일치,
> result age<=0.20초, cloud-seq lag<=1, checked time-range 포함을 모두 요구한다.
> Entry replay는 brake 1회 뒤 안전 완주했고, current-body replay는 내부 거리
> 증가·0.02m progress·exit·no-reentry 조건을 만족해 EGRESS로 brake 없이
> 완주했다. Replay 없는 enforce smoke도 NO_HIT 308, false brake 0이었다.
> 이는 Map7 n=1 기능 증명이지 실제 contact-correlated 검출이나 population
> 안전 보장이 아니다.
>
> RViz 왼쪽 치우침은 CIRI face의 obstacle/boundary provenance를 추가해 실제
> obstacle-derived 양측 통로만 계측하도록 고쳤다. Exp/Backup 양쪽에 passage
> balance를 구현했지만 Exp+Backup 2e6/2e5는 180초 timeout으로 기각했다.
> Exp-only 2e4는 기능상 완주하고 독립 baseline 대비 평균 imbalance가 약
> 13% 줄었으나 guard brake 증가와 physical clearance 저하가 함께 보여 채택하지
> 않았다. Map7 3모드 smoke는 Full/Sector/Adaptive 모두 완주, static contact
> 0/1/0, Adaptive Full-open 4회였다.
>
> 후속 Map7 세 모드 각 n=10 cgroup campaign은 30/30 first-attempt 완주,
> static-safe, speed/perf/cgroup-valid, retry 0이었다. 평균시간은
> 85.030/88.114/88.130초, worst clearance는
> +0.205/+0.000905/+0.233m다. 따라서 n=1 Sector contact는 반복되지 않았지만
> Sector run7의 거의 0인 양의 margin과 live-cloud-only 후보 2회는 위험 신호다.
> Adaptive는 Full 대비 algorithm/end-to-end CPU 8.465/6.000%, payload
> 47.538%, points/s 36.401%를 줄였고 시간은 3.646% 늘었다. Effective Full-open은
> 87회(8.7/run)다. 같은 바이너리 default-off n=10 control이 없으므로 passage
> centering 효과의 인과 증거는 아니며 후보는 계속 미채택이다.
>
> 모든 새 기능은 default off이고 표준/실사용 tight_v7 profile은 그대로다.
> Raw-cloud CIRI도 계속 false/non-authoritative다. 상세는 viability §8.44,
> `docs/near_field_hard_gate_and_passage_centering_20260831.md`, 요약 CSV는
> `results/near_field_hard_gate_and_passage_centering_summary_20260831.csv`와
> `results/passage_center_exp_w2e4_seed7_three_mode_n10_cgroup_summary_20260831.csv`다.

> [!IMPORTANT]
> **2026-08-31 Map7 recent-hit near-field shadow 구현·n=20 완료.**
> Full Map7 blind-footprint 반례를 겨냥해 최근 1.5초 raw hit와 committed
> body+1초 tail을 0.01초 간격, 반경 0.20m로 비교하는 default-off shadow를
> 추가했다. Raw window는 commit enqueue 시점으로 고정되고, 누적·변환·AABB
> crop·KD-tree는 별도 latest-only worker에서만 돈다. 실사용 tight_v7과 비행
> 결정은 바뀌지 않았고 최종 상태명도 known-free 오해를 막기 위해 `NO_HIT`다.
>
> Full Map7 n=20은 20/20 완주·static-safe, 속도 위반 0이었다. Shadow는
> 2,305건을 skip 없이 처리했고 평균/최대 9.979/42.228ms, 평균 source/crop
> point는 442,259/3,597개였다. 그러나 실제 접촉이 재현되지 않아 r=0.20
> 검출 성공은 아직 미증명이다. r=0.40 sensitivity n=1에서는 7건 OCCUPIED를
> 검출하면서 비행은 78.49초 안전 완주해 wiring과 비권위성을 확인했다.
>
> RViz의 왼쪽 장애물 치우침도 별도 원인으로 확인했다. Full은 전체 관측일
> 뿐 passage centre 목적이 아니다. 현재 clearance 비용은 v<=1.5 full,
> 1.5~2.0 fade, v>=2.0 zero라 순항 중에는 A*/CIRI의 한쪽 seed와 시간·smooth
> 목적이 그대로 남는다. 다음은 bilateral clearance 계측 후 실제 양면 통로에
> 한정한 face-balance/medial-axis 후보이며, ungated clearance 재도입은 아니다.
> 상세는 viability §8.43과
> `docs/near_field_shadow_map7_n20_and_path_bias_20260831.md`다. Hard gate 전에는
> new-scan cadence shadow와 실제 contact-correlated/deterministic replay가 먼저다.

> [!IMPORTANT]
> **2026-08-31 cgroup-accounted 최종 n=10 완료, Full blind-footprint 반례 발견.**
> Speed-gated nearest-face 후보의 Map1-10 x Full/Sector/Adaptive x n=10은
> 300/300 first-attempt·run/speed/perf/cgroup-valid, retry/OOM 0이다.
> Completion은 100/99/100, 권위 source-static-PCD safety는 99/100/100이다.
> 평균시간은 73.892/72.723/73.815초, worst clearance는
> -0.144/+0.047/+0.106m다.
>
> 새 cgroup v2 계측에서 평균 algorithm core·s는
> 90.175/75.633/78.249, end-to-end는 106.278/91.946/94.226이다. Adaptive는
> Full 대비 algorithm CPU 13.226%, end-to-end CPU 11.340%, processed payload
> 56.346%, points/update 17.481%, map time/update 25.591%를 줄였고 시간 변화는
> -0.104%다. PSS는 세 모드 모두 약 3.2/3.6GiB라 메모리 절감은 아니다.
>
> Sector Map3 run7의 207.36초 미완주는 FSM PSS 8.22GiB, available 462MiB,
> swap 포화와 PSI 93.34/87.66%가 동반된 infrastructure-contaminated run이다.
> 건강한 replay는 61.20초에 완주·충돌 0이었다. 반면 Full Map7 run4는
> 6.121초, 0.01155m/s, static clearance -0.1437m의 실제 접촉이다. 최신 map
> guard는 SAFE였지만 장애물이 LiDAR blind 0.1m 안(거리 0.0563m)이라 local
> map/CIRI face가 없었다. 저속 nearest-face 비용은 full weight였어도 입력
> face가 없어 작동할 수 없었다. Replay는 safe라 관측 빈도는 1/10이다.
>
> 다음 구현은 static-PCD oracle을 쓰지 않고 최근 1~2초 raw hit를 bounded
> near-field witness로 유지해 body/short-tail 진입을 hard gate하는 것이다.
> 이미 footprint 안이면 거리 단조 증가 egress만 허용해야 liveness를 보존할
> 수 있다. 먼저 shadow, Map7 Full n>=20, 3-mode n=3, 마지막 300회 순서다.
> Map3 같은 PSI 오염 run의 automatic infrastructure retry도 별도 필요하다.
>
> Adaptive 100/100 Wilson 하한은 96.301%이고 Full safety와의 exact McNemar는
> one discordance라 p=1.0이다. Population 100%, 유의한 안전 우위, 이번
> n=10에서 Sector 안전 저하를 주장하면 안 된다. 상세는 viability §8.42와
> `docs/final_speedgated_cgroup_n10_and_failure_forensics_20260831.md`, raw/summary는
> `results/final_speedgated_cgroup_3mode_seed1_10_n10_{raw,summary}_20260831.csv`다.
> Raw-cloud CIRI는 계속 false/non-authoritative이고 NaN, `obs_skip_num` no-op,
> `DRONE_R=robot_r` 지표 한계도 남아 있다.

> [!IMPORTANT]
> **2026-08-30 저속 nearest-face clearance shaping 후보와 90회 n=3 gate 완료.**
> 최종 n=10 Map10 Adaptive의 `+0.038m` 저여유는 freshness/ACK 문제가 아니라
> 저속 terminal/backup 구간의 trajectory preference/coverage 문제였다. 먼저
> 0.10m hard terminal gate를 시도했지만 반복 reject가 certified-stop liveness
> trap을 만들고 속도 제한형도 timeout을 내서 완전히 원복했다.
>
> 채택 후보는 CIRI 모든 face를 합산하던 기존 soft clearance를 normalized
> nearest face 하나로 바꾸고, 누락됐던 BackupTrajOpt에도 동일 비용을 적용한다.
> `penna_clr=1e6`, margin 0.10m, v<=1.5m/s full weight, 1.5~2.0m/s cubic fade,
> v>=2.0m/s zero이며 speed-envelope gradient도 포함한다. 파라미터 미지정
> 전역 동작은 off이고 tight_v7 검증 profile 두 개에 후보값을 명시했다.
>
> Speed-gated maps9-10 집중 n=3은 6/6 safe였다. 이어진 rotating-order
> map1-10 x Full/Sector/Adaptive x n=3은 90/90 first-attempt·run/speed/perf
> valid, retry/OOM 0이다. Full/Adaptive는 각각 30/30 완주·safe, Sector는
> 29/30 완주·27/30 safe다. Map7 Sector에 timeout 1회와 완주 충돌 1회,
> Map10 Sector에 완주 충돌 1회가 있었고 동일 Adaptive는 모두 safe다.
> 평균 시간은 73.33/75.64/76.02초, worst clearance는
> +0.145/-0.172/+0.153m다. Map10 Adaptive는 기존 +0.038m에서 +0.225m다.
>
> Adaptive는 Full 대비 points/update 15.79%, map Hz 28.80%, processed
> payload 52.14%, total/update 19.65%, update 13.67%, FSM CPU 16.53%를
> 줄였고 시간은 3.67% 늘었다. Effective Full open은 348회(11.6/run)다.
> Exact matched McNemar는 Full-Sector/Sector-Adaptive/Full-Adaptive가
> 0.25/0.25/1.0이고 30/30 Wilson 95% 하한은 88.65%다. 따라서 n=3 후보
> gate일 뿐이며 새 최종본 선언 전 같은 바이너리 300회 n=10이 남았다.
>
> 상세는 viability §8.41과
> `docs/speed_gated_nearest_face_clearance_n3_20260830.md`, raw/summary는
> `results/speed_gated_nearest_face_clearance_3mode_seed1_10_n3_{raw,summary}_20260830.csv`다.
> 이번에 face-summed clearance 설계와 BackupTrajOpt 미커버는 수정됐다.
> 별도 NaN 버그, `obs_skip_num` no-op, `DRONE_R=robot_r` 지표 한계는 남아
> 있고 raw-cloud CIRI는 계속 false/non-authoritative다.

> [!IMPORTANT]
> **2026-08-29 감속 one-shot Full refresh와 최종 300회 완료.**
> Seed9 잔여 접촉은 5.893초, 0.083m/s, source-PCD clearance -0.009641m에서
> 확인됐다. Sector map이 약 0.2초마다 정상 commit돼 pre-stale trigger는
> 닫혀 있었고 replan도 성공해 failure guard가 열리지 않았다. 기존 stall
> state도 너무 늦었다. 즉 원인은 ACK loss나 same-map coalescing이 아니라
> 성공 replan 뒤 high→low-speed blind-sector transition gap이다.
>
> Native C++ Adaptive filter에 3.0m/s에서 무장하고 1.5m/s 이하 감속 시
> 최신 uncropped Full scan 한 장만 uncapped로 보내는 hysteretic one-shot을
> 추가했다. 기존 generation/process ACK를 사용하며 다시 3.0m/s를 넘기 전에는
> 재무장하지 않는다. 전역 기본값은 기존 ablation 재현성을 위해 0/off이고,
> 검증 프로파일은 runner의
> `--adaptive-slowdown-full-refresh-v 1.5`와
> `--adaptive-slowdown-full-refresh-rearm-v 3.0`을 명시한다.
>
> Focused seed9 Adaptive n=10은 10/10 완주·source-static-PCD 충돌 0,
> worst +0.179m였다. 이어진 rotating-order map1-10 x 3-mode x n=10은
> 300/300 first-attempt·run/speed-valid, retry/OOM 0이었다. Full/Adaptive는
> 각각 safety-qualified 100/100이다. Sector는 100/100 완주했지만 seed9
> 충돌 1회로 safe 99/100이다. 평균 Full/Sector/Adaptive 시간은
> 70.97/71.49/75.81초, worst clearance는 +0.150/-0.175/+0.038m다.
>
> Adaptive는 Full 대비 points/update 14.94%, map Hz 30.50%, processed
> payload 52.25%, total/update 19.10%, FSM CPU 17.66%를 줄였고 시간은
> 6.81% 늘었다. Effective Full open 1,198회, slowdown trigger/frame/commit
> ACK는 4,816/4,711/4,706회다. 종료 순간 pending 5건은 모두 안전 완주한
> 마지막 frame right-censoring이며 supersede 0이다. Exact matched McNemar는
> Full-Sector/Sector-Adaptive 모두 p=1.0이고 100/100 Wilson 95% 하한은
> 96.30%라 population 100% 주장은 금지한다.
>
> 상세는 viability §8.40과
> `docs/adaptive_slowdown_full_refresh_final_n10_20260829.md`, 최종 raw/summary는
> `results/final_slowdown_refresh_3mode_seed1_10_n10_{raw,summary}_20260829.csv`다.
> Raw-cloud CIRI는 계속 false/non-authoritative이고 `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표
> 한계도 그대로다.

> [!IMPORTANT]
> **2026-08-29 bounded same-map replan coalescing은 구현/검증했지만 표준 채택 보류.**
> map commit보다 빠른 성공 `ReplanOnce` 중복을 줄이기 위해 같은 map version과
> trajectory generation을 병합했다. 새 map까지 무기한 생략한 첫 후보는 seed9
> Adaptive가 waypoint 2/5, 180초 timeout에 걸려 기각했다. 0.10초가 지나면
> same-map replan을 강제하는 제한형은 seed9 smoke 3/3, maps5/8/9 crossed A/B
> 후보 15/15, 전체 map1-10 3-mode n=3의 Adaptive 30/30을 완주했고 정적 충돌
> 0이었다.
>
> 전체 n=3은 90/90 first-attempt·run/speed-valid, retry/OOM 0이다. Full과
> Adaptive는 각각 30/30 완주·source-static-PCD 충돌 0, Sector는 30/30
> 완주지만 seed8 정적 충돌 1회였다. 평균 Full/Sector/Adaptive 시간은
> 69.86/72.19/75.21초, worst clearance는 +0.219/-0.169/+0.043m다. Adaptive는
> Full 대비 map Hz 35.08%, points/update 15.76%, total/update 20.72%, update
> 13.13%, processed payload 56.98%, FSM CPU 21.37%를 줄였지만 시간은 7.65%
> 늘었다. Effective full open은 344회다.
>
> 따라서 same-map 기능은 default false인 실험 코드로 보존하고, 검증된 표준
> `tight_v7` 프로파일은 default-off로 복원했다. 테스트한 후보는 명시적인
> `*_replan_coalesce_bounded.yaml`에만 있다. 다음 우선순위는 seed9 Adaptive의
> +0.043m 저여유와 41.3 brakes/run, 48.56초 recovery를 만드는 freshness/map
> commit cadence 분석이다. 상세는 viability §8.39와
> `docs/bounded_same_map_replan_coalesce_20260829.md`, raw는
> `results/replan_coalesce_bounded_3mode_seed1_10_n3_raw_20260829.csv`다.
> 최종본까지 최소 8~12시간의 focused n=10 + 전체 300회 재검증이 남았다.
> Raw-cloud CIRI는 계속 false/non-authoritative이며 `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표
> 한계도 그대로다.

> [!IMPORTANT]
> **2026-08-28 교차균형 n=10 300회와 ROG-Map 메모리 worker 수정 완료.**
> 최종 수정 바이너리로 map1-10 x Full/Sector/Adaptive x n=10을 실행했고
> 300/300 모두 first-attempt 완주, run/speed-valid, retry/OOM 0이었다.
> Full과 Adaptive는 각각 100/100 source-static-PCD 무충돌이었다. Sector는
> 100/100 완주했지만 map7·8·9에서 각 2회씩 정적 충돌해 safe 94/100이었다.
> 동일 6개 map/run의 Adaptive는 모두 안전했다. 전체 순서를 연속 회전해 각
> 모드의 1/2/3번째 위치가 33~34회로 균형됐고, Full-Sector 및
> Sector-Adaptive matched discordance의 exact McNemar는 각각 `p=0.03125`다.
>
> 첫 n=10은 map5 Full timeout으로 132행에서 중단했다. Degenerate
> collision-away 방향에 goal-order fallback을 넣되 기존 stop-only 8방향
> trajectory/viability certificate는 유지했고, map5 Full 집중 n=8은 8/8
> 통과했다. 다만 새 `direction_source=goal_fallback`은 자연 발생 0이므로
> 직접 인과 증거로 주장하지 않는다.
>
> 두 번째 n=10은 277행 뒤 map10 run3 Full이 3.23→8.43 GiB RSS로 증가해
> kernel OOM kill됐다. DDS cloud callback의 PCL 변환+map/COW/ACK를 executor
> thread에서 동기 수행하던 구조가 원인이었다. Callback은 latest-only
> enqueue만 하고 전용 단일 worker가 무거운 작업을 담당하도록 수정했다.
> 집중 map10 Full/Adaptive n=3+n=3은 6/6, peak RSS 3.24 GiB 이하였고, 최종
> 300회 peak RSS 3,263.95 MiB, memory PSI 0으로 OOM이 재발하지 않았다.
>
> 최종 평균 Full/Sector/Adaptive 시간은 71.61/70.05/74.33초다. Adaptive는
> Full 대비 map update frequency 33.08%, points/update 16.68%,
> total/update 20.63%, processed payload 56.08%, FSM CPU 17.05%를 줄였고
> 시간은 3.80% 늘었다. Effective full-view open은 1,160회(11.60/run)다.
> Payload는 ROG-Map processed application payload이며 NIC/무선/DDS wire
> bandwidth가 아니다. 상세는 viability §8.38 및
> `docs/counterbalanced_n5_n10_validation_20260828.md`, 최종 raw는
> `results/counterbalanced_map_worker_3mode_seed1_10_n10_raw_20260828.csv`다.
> 100/100의 Wilson 95% lower bound는 96.30%이므로 population 100% 주장은
> 금지한다. Raw-cloud CIRI default false/non-authoritative,
> `obs_skip_num` no-op, NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 base-NO_PATH 집중 n=20과 최종 payload-aware 3-mode n=3 gate 완료.**
> 수정 뒤 map9 Adaptive를 20회 추가 실행했고 20/20 first-attempt 완주,
> contact/static collision 0, speed-valid였다. 평균/범위 시간은
> 90.07/76.71~122.25초, worst clearance +0.190m였다. Natural base-NO_PATH
> local-escape arm은 0이므로 이 20회는 regression/liveness 증거이며, 직접 분기
> 증거는 앞서 default-off fault hook 두 번에서 확보한 3 NO_PATH→1 arm→
> 202-sample 0.6m commit이다.
>
> 같은 최종 바이너리 map1-10 x Full/Sector/Adaptive x n=3은 90/90
> first-attempt 완주·speed-valid, timeout/retry/OOM 0이다. Full과 Adaptive는
> safety-qualified 30/30이다. Sector는 30/30 완주했지만 map7 1회, map9 2회,
> map10 1회가 접촉해 safe 26/30, live events 9, static collision 4였다.
> 같은 map/run Adaptive는 네 번 모두 안전했다. 평균 시간은
> 71.43/71.53/74.39초, worst clearance는 +0.193/-0.181/+0.210m다.
>
> Full/Sector/Adaptive processed payload 평균은 5.069/1.569/2.351 MiB/s다.
> Map별 동일가중 Full 대비 감소율은 Sector 69.43%, Adaptive 54.24%다.
> 전체 mode 평균 비율에서 Adaptive는 points/update 15.68%, total/update
> 21.80%, update 15.09%, FSM CPU 14.62%, planner+filter core-seconds 8.65%를
> 줄였고 mission time은 4.14% 늘었다. Adaptive effective full-view open은
> 372회(12.4/run)다. 이 payload는 ROG-Map processed application payload이며
> NIC/무선/DDS wire bandwidth가 아니다.
>
> Matched safety discordance는 Full-Sector 4:0, Sector-Adaptive 0:4이고 exact
> McNemar는 둘 다 `p=0.125`다. 고정 Full→Sector→Adaptive 순서라 exploratory
> matched-block 결과다. Full/Adaptive 30/30의 Wilson 95% lower bound는
> 88.65%라 population 100% 주장은 금지한다. 상세는 viability §8.37,
> `docs/final_payload_base_no_path_n3_20260827.md`, raw는
> `results/final_base_no_path_seed9_adaptive_n10{a,b}_raw_20260827.csv`와
> `results/final_payload_base_no_path_3mode_seed1_10_n3_raw_20260827.csv`다.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 processed-payload bandwidth 계측과 base-NO_PATH 복구 완료.**
> ROG-Map update에 실제 사용된 `PointCloud2.data` bytes/point_step을 기존
> performance CSV에 기록하고 runner가 frames/s, points/s, MiB/s, Mbit/s를
> 계산한다. 이는 DDS/RTPS overhead·retransmission·latest-only overwrite를
> 제외한 processed application-payload이며 NIC/무선 대역폭이 아니다.
>
> Map1-10 x 3-mode n=1에서 Full/Sector/Adaptive 평균은
> 5.077/1.977/2.748 MiB/s였다. Map별 Full 대비 감소율 평균은 Sector 64.44%,
> Adaptive 49.02%다. Full 10/10, Sector 9/10, Adaptive 9/10 완주였고 map9
> Sector는 접촉 후 timeout, Adaptive는 contact 0인 채 waypoint2/5에서
> timeout했다. Adaptive timeout의 7.324 MiB/s는 92.19% full-open이 만든
> 결과이지 대역폭 부족의 원인이 아니다.
>
> Map9 Adaptive는 local escape 뒤 base A* `NO_PATH`, guarded vertical lift
> reject 후 남은 horizontal budget을 쓰지 않고 permanent hold에 들어가
> 같은 실패를 140초/13,355회 반복했다. Base vertical budget 소진 뒤 기존
> 8방향 certified local escape로 연결하도록 수정했다. 자연 map9 n=8은 8/8
> 완주·contact 0·speed-valid였으나 새 분기를 밟지 않았다. Default-off fault
> hook은 두 독립 smoke에서 각각 `NO_PATH` 3회 뒤 202-sample guard를 통과한
> 0.6m escape를 commit했다. 둘 다 완주/contact 0/speed-valid였고 시간은
> 65.75/60.19초, worst clearance는 +0.311m였다. v2 CSV가 injection 1,
> forced failure 3, base escape arm 1, local commit 1을 직접 보존한다.
>
> 이 절에서 예정한 **최종 바이너리 map1-10 x Full/Sector/Adaptive x n=3**은
> 위 최신 배너와 viability §8.37에서 완료됐다. 이 절의 구현 상세는 §8.36,
> `docs/payload_bandwidth_and_base_no_path_escape_20260827.md`, raw는
> `results/bandwidth_3mode_seed1_10_n1_raw_20260827.csv`와 matching
> `base_no_path_*_20260827.csv`를 볼 것. Population 100% 주장은 금지하며
> raw-cloud CIRI default false/non-authoritative와 기존 known limitations는
> 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 native C++ filter latest-only worker 최적화와 36-run 회귀 완료.**
> Maps9-10 Adaptive의 100초대 tail은 `MAP_STALE -> brake -> fresh-map replan`
> 반복에 집중됐다. Guard hold 2.5→0.5초 후보는 map9 3/3을 빠르게 끝냈지만
> map10 첫 run에서 live contact 2, static collision 1, clearance -0.157m를
> 만들어 폐기했다. Default/profile에는 반영하지 않았다.
>
> 채택 구현은 safety threshold를 전혀 바꾸지 않고 native C++ filter의 raw-cloud
> DDS callback을 enqueue-only로 만들고 point filtering + reliable publish를
> 별도 latest-only worker로 옮겼다. Filter/guard/ACK state는 mutex로 직렬화하고
> 종료 시 pending drop + join한다. Maps9-10 Adaptive n=3은 6/6 first-attempt,
> contact 0, 평균 88.01초로 직전 102.87초보다 14.45% 짧았다. Brake/run은
> 51.50→35.17, recovery active는 54.60→41.08초였다.
>
> 이어진 map1-10 x Full/Sector/Adaptive x n=1은 30/30 first-attempt 완주,
> live/static contact 0, speed-valid였다. 평균 시간은 72.08/70.85/72.86초다.
> 이 n=1에서 Adaptive는 Full 대비 points/update 13.72%, total/update 18.76%,
> update 10.49%, FSM CPU 15.23%, planner+filter core-seconds 10.92%를 줄이고
> mission time은 1.09% 늘었다. Adaptive open은 108회다.
>
> 모든 accepted filter row에서 input callback==processed frame, overwrite 0이므로
> 프레임 폐기가 개선 원인은 아니다. 이전/이후 n=3도 interleaved paired A/B가
> 아니므로 14.45%를 정밀 인과효과로 주장하지 말 것. 직전 n=3의 Sector map9
> contact는 여전히 유효하며 이번 clean n=1로 Sector를 safe로 재분류하지 않는다.
> 상세는 viability §8.35,
> `docs/native_filter_async_latest_optimization_20260827.md`, raw는
> `results/adaptive_async_latest_seed9_10_n3_raw_20260827.csv` 및
> `results/async_latest_3mode_seed1_10_n1_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 stopped-recovery tail 수정 및 현재 바이너리 3-mode n=3 gate 완료.**
> 이전 독립 n=5에서 map8 Full이 154 arm/363 search 뒤 293.79초에 끝난 원인은
> 짧은 certified escape commit마다 topology recovery 전체 상태와 예산을
> 초기화하여 같은 local/vertical 복구를 다시 허용한 것이었다. 이제
> pose-specific blocker만 지우고 episode budget은 보존하며, 같은 goal에서
> 2.0 m XY 진전 후에만 예산을 reset한다. Local escape는 8방향을 현재
> waypoint 진전 순으로 시도하고 local/vertical budget은 한 이벤트에서
> 동시에 소비하지 않는다. 기존 trajectory/stop-viability certificate는
> 약화하지 않았다.
>
> 첫 버전은 map10 Adaptive run3에서 goal 반대 방향 탈출 뒤 300.01초 timeout,
> arm/search/epoch-reset 121/357/116을 내어 폐기했다. 최종 수정 뒤 map10
> Adaptive n=5는 5/5, maps7-10 Full/Adaptive n=3는 24/24 first-attempt,
> contact 0이었다. 현재 바이너리의 map1-10 x Full/Sector/Adaptive x n=3
> 90회는 전부 first-attempt 완주·speed-valid, retry/OOM 0이다. Full과
> Adaptive는 safety-qualified 30/30, fixed Sector는 29/30이다. Sector map9
> run1만 live contact 2, static collision 1, clearance -0.107 m였다.
>
> Adaptive는 Full 대비 points/update 14.52%, total/update 21.68%, update
> time 14.60%, FSM CPU 19.48% 감소했고 mission time은 7.93% 증가했다.
> Effective full-view open은 323회(10.77/run)다. 다만 현재 n=3의 paired
> discordance는 1:0, exact McNemar `p=1.0`, Full/Adaptive 30/30의 95%
> Wilson lower bound는 88.65%이므로 population 100% 주장은 금지한다.
>
> 직전 map8 Full n=10 중 한 process가 약 3.0→9.1 GiB RSS로 증가하고 host
> swap full 상태에서 OOM-kill된 뒤 retry 1회가 성공했다. 최종 90회에는
> OOM/retry가 없었고 원인 allocation은 아직 미확정이다. 상세는 viability
> §8.34와 `docs/goal_ordered_recovery_final_n3_20260827.md`, 최종 raw는
> `results/goal_ordered_final_3mode_seed1_10_n3_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버,
> `DRONE_R=robot_r` 지표 한계도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-27 직전 바이너리 독립 n=5 일반화 gate 완료.** Fresh
> map1-10 x Full/Sector/Adaptive x n=5, order rotation 150회를 수행했다.
> Full 50/50·Adaptive 50/50은 완주, live/static contact 0, speed-valid였다.
> Fixed Sector는 49/50 완주, live contact 1 run/2 events, static collision
> 1 run/1 event, safety-qualified 48/50이었다. Map7 run1 Sector는 contact 없이
> waypoint 4/5에서 300.01초 timeout, paired Adaptive는 80.80초·contact 0으로
> 완주했다. Map8 run1 Sector는 완주했지만 live/static contact가 발생했고
> -0.170 m였으며, paired Adaptive는 69.67초·contact 0·+0.286 m였다.
>
> 유효한 50개 Full/Adaptive pair에서 Adaptive는 points/update 16.41%, map
> total/update 19.31%, update time 11.74%, FSM CPU 17.49%, time-integrated
> FSM+filter CPU work 13.33%를 줄였다. Point kept 59.73%, effective full-view
> open 534회(10.68/run)다. Trajectory-guard ACK 1,336/1,336, pre-stale ACK
> 3,656/3,656이며 retry/pending/supersede/abandon/timeout 0이다.
>
> Full은 50/50을 유지했지만 map8 run2가 guarded A* `NO_PATH` 뒤 topology
> arm/search 154/363회를 소비하고 293.79초에 끝난 liveness tail이 남았다.
> 이는 메모리 문제가 아니다: retry/OOM/FSM swap/PSI 모두 0, 최소 available
> memory 4.65 GiB였다. 다음 engineering target은 hard certificate를 약화하지
> 않고 이 stopped topology search tail을 bound/reuse하는 것이다.
>
> 이번에는 exact paired McNemar도 수행했다. 독립 n=5 safe discordance 2:0은
> `p=0.5`, same-binary n=3+n=5의 5:0도 `p=0.0625`라 아직 유의하지 않다.
> Full/Adaptive 50/50의 95% Wilson lower bound는 92.87%다. 따라서 population
> 100%/flight-ready 주장은 금지하고, 다음 실험은 같은 seed 반복이 아니라
> preregistered held-out map/noise cohort로 갈 것. 상세는 viability §8.33,
> `docs/final_generalization_n5_20260827.md`, raw는
> `results/final_generalization_3mode_seed1_10_n5_raw_20260827.csv`를 볼 것.
> Raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계도
> 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 final DDA 3-mode n=3 + 대형 맵 연산계측 race 수정 완료.**
> 최종 DDA/body-coordinate 바이너리로 map1-10 x Full/Sector/Adaptive x n=3
> (총 90회, order rotation)을 수행했다. Full 30/30·Adaptive 30/30은
> live/static contact 0, speed-valid 30/30이었다. Fixed Sector는 29/30,
> live contact 3 runs/6 events, static collision 3 runs/3 events,
> safety-qualified 27/30이었다. Map9 run2 Sector는 contact 후 300초 timeout,
> paired Adaptive는 89.74초·contact 0·+0.265 m로 완주했다.
>
> 29개 matched metric pair에서 Adaptive는 Full 대비 points/update 17.22%,
> map total/update 20.70%, update time 13.03%, FSM CPU 19.12% 감소했다. 전체
> 30회 time-integrated FSM+filter CPU work는 11.66% 감소, 평균 mission time은
> 5.91% 증가했다. Effective full-view open은 321회이며 원인별 counter는
> overlap되므로 서로 더하면 안 된다.
>
> Map10 Full run1에서 `perf_row_start=472 > perf_row_end=446`인 연산계측
> race도 발견했다. 큰 static map의 ROGMap init이 runner의 4초 대기보다 늦어
> shared performance CSV를 뒤늦게 truncate한 문제다. Runner가 새 log
> generation/header를 기다리고 positive window를 확인한 뒤, teardown 전에
> per-attempt CSV snapshot을 남기도록 고쳤다. Post-fix map10 3-mode n=1은
> generation/window valid 3/3, 완주 3/3, contact 0이다. 이 race는 기존 90회
> 중 computation 한 행만 비웠고 completion/contact/time 판정에는 영향 없다.
>
> 상세 맵별 표와 claim boundary는 viability §8.32 및
> `docs/final_dda_projection_3mode_n3_20260826.md`, raw는
> `results/final_dda_projection_3mode_seed1_10_n3_raw_20260826.csv`와
> `results/perf_generation_seed10_3mode_n1_raw_20260826.csv`를 볼 것.
> Population 100%/flight-ready 주장은 금지하며 McNemar 미검정이다.
> raw-cloud CIRI default false/non-authoritative, `obs_skip_num` no-op,
> NaN/clearance-penalty, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계
> 정정도 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 recovery branch proof + DDA/body-coordinate 후속 완료.**
> Recovery-only exact-generation ACK retry는 첫 guard full cloud를 한 번
> 강제로 drop했을 때 drop/retry 1/1, exact ACK commit 32, abandon 0으로
> 완주했고, stopped four-way local escape는 첫 방향을 강제로 skip한 뒤 다른
> 방향을 hard certificate로 commit해 완주했다. 두 fault hook은 default-off다.
>
> 이어서 동일 바이너리 map1-10 x Full/Sector/Adaptive x n=5를 수행했다.
> Full 50/50·contact 0, fixed Sector 50/50이지만 live contact 4 runs/10 events와
> static collision 3 runs/3 events, Adaptive 49/50·contact 0이었다. Adaptive
> map10 run4가 +0.041 m static clearance인데도 waypoint 0에서 240초 정지해
> liveness 결함이 남았다. Full map2 run3의 두 `no odom samples` retry는
> `/dev/shm`에 남은 Fast-DDS 파일 17,452개(약 4.5 GiB)와 host memory/swap
> pressure가 원인이었고, planner OOM/accepted-attempt FSM swap은 아니었다.
>
> Physical shell/voxel quantization을 exact occupied-centre distance로 고친
> 뒤에도 map9 Adaptive가 4/5 waypoint에서 정지했고, initial-footprint egress
> 1차안 뒤에는 map8에서 다시 정지했다. 최종 원인은 inflated-grid DDA cell
> centre를 raw physical-body 검사에서도 robot centre로 사용한 좌표 혼용이다.
> 이제 inflated query는 DDA 좌표를 유지하되 raw body distance는 polynomial
> chord 투영점을 쓴다. 초기 footprint 셀은 candidate가 그 셀에 더 가까워지지
> 않을 때만 bounded egress에서 무시하며 continuous free tail이 여전히 필수다.
>
> 최종 forced footprint 시험은 injection/commit 1/1·contact 0, map8 Adaptive
> n=5는 5/5·contact 0, 최종 map8-10 Full/Adaptive n=3은 18/18·contact 0·
> speed-valid 18/18·retry 0이다. Adaptive는 이 dense gate에서 Full 대비
> points/update 14.34%, map total/update 17.85%, FSM CPU 15.62%를 줄였고 평균
> 시간은 3.78% 길었다. Adaptive arm/open은 4/4회다. 상세는 viability §8.31,
> `docs/guard_recovery_egress_projection_v7_20260826.md`, raw는
> `results/dda_projection_dense_full_adaptive_n3_raw_20260826.csv`를 볼 것.
>
> 이것은 관측된 결함의 local regression 통과이지 population 100%나
> flight-ready 보장이 아니다. McNemar 미검정, raw-cloud CIRI default
> false/non-authoritative, `obs_skip_num` no-op, NaN/clearance-penalty 결함,
> BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계 정정은 계속 유효하다.

> [!IMPORTANT]
> **2026-08-26 v7 속도 hard bound + stopped recovery 후속 완료.** 아래
> reliable-link n=3의 Full seed7 run3 `10.027 m/s`는 planner가 실제 발행한
> 명령이었다. Guard retry가 두 odometry 위치를 표본 수신시각이 아니라 callback
> read 시각 차이(6 ms)로 나눠 가짜 `odom_motion=10.055 m/s`를 만들었다.
> `robot_state_.rcv_time`으로 시간축을 교정했고, guarded candidate exact-max
> time scaling, brake dynamics/max-velocity 검사, polynomial/PositionCommand
> publish 직전 재검사, speed-qualified `run_valid`를 추가했다. 과거 seed10
> contact를 만든 odometry twist 직접 대입은 복원하지 않았다.
>
> 첫 speed-qualified seed6-10 x 3-mode x n=3은 45/45 속도 유효였지만 Full
> seed10 timeout 1회와 Adaptive seed8 166.68초 long-tail을 드러냈다. Recovery
> active 중 exact full-generation ACK가 0.75초 안에 없을 때만 최신 full 하나를
> stop-and-wait 재전송하는 옵션을 넣었다(기본 0/off). 이후 seed8 n=5에서 모든
> ACK가 빠르게 왔는데도 151.77초가 나와, 진짜 원인을 최신 충돌점 방향이
> 뒤집히며 같은 stopped topology를 59.69초 반복한 것으로 확정했다. Local
> recovery는 수평 네 출구를 각 한 번만 검사하고 기존 hard certificate를 통과한
> 첫 candidate만 commit하도록 보완했다.
>
> 보완 후 seed8 Adaptive n=5는 5/5 완주·contact/static collision 0·속도 유효,
> 평균 81.21초, 최대 recovery 2.52초였다. 최종 동일 바이너리 map1-10 x
> Full/Sector/Adaptive x n=1은 30/30 완주, contact/static collision 0,
> speed-qualified 30/30이다. 평균 시간은 71.04/72.05/78.89초. Adaptive는
> Full 대비 points/update 12.88%, total/update 22.91%, update time 16.09%,
> FSM+filter core-seconds 8.86% 감소, 시간 +11.04%였다. Full-view 전환 123회,
> guard episode/ACK 241/241, ACK 최대 0.101465초, retry/supersede/abandon 0이다.
>
> Corridor epoch-reset은 map7 Adaptive에서 실제 1회 실행돼 약 0.64초 뒤
> 회복했다. 하지만 recovery ACK retry와 새 네 방향 local-escape는 최종 표본에서
> trigger되지 않았으므로 직접 branch proof는 아니다. Population 100%,
> flight-ready, zero-tolerance `<=7.000000`을 주장하지 말 것. McNemar 미검정,
> raw-cloud CIRI default false/non-authoritative다. `obs_skip_num` no-op,
> NaN/clearance-penalty 결함, BackupTrajOpt 미커버, `DRONE_R=robot_r` 지표 한계
> 정정도 계속 유효하다. 상세는 viability §8.30 및
> `docs/guarded_velocity_bound_v7_20260826.md`, raw는
> `results/final_multiexit_3mode_seed1_10_n1_raw_20260826.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-26 reliable-link n=3 반복·stationary-defer 기각 — 바로 아래 n=1
> 채택안을 seed6-10 x Full/Sector/Adaptive x n=3으로 반복했다.** 45/45가 current
> runner 기준 valid·first-attempt였다. Full/Adaptive는 각각 15/15 완주, contact
> 0, static-PCD collision 0이었다. Fixed Sector는 13/15 완주, contact run 3개,
> event 5회였다. 평균 시간은 84.85/101.57/82.31초이며 Sector 평균에는 seed10의
> 240초 timeout 2개가 포함된다.
>
> Adaptive는 Full 대비 points/update 14.83%, map total/update 15.15%, 전체
> mapping point/work 35.97%/36.20%, FSM+filter core-seconds 7.46%를 줄였고 이
> 표본의 평균 mission은 3.00% 짧았다. Pre-stale generation 1,274개 중 1,273개가
> exact ACK됐으며 supersede/timeout은 0, 종료 시 pending 1개다. Recovery gate
> 502/502는 모두 ACK를 받았다.
>
> 남은 brake rejection marker 906개 중 707개(78.0%)가 speed<=0.05 m/s 정지
> proxy에서 발생했다. Passive-stop 안정화 전에 zero-displacement 후보의 중복
> map/grid 검사를 미루는 fail-closed stationary-defer를 구현해 seed9 3회
> 시험했지만 평균 152.23초로 개선이 입증되지 않았다. 원복 뒤 isolated smoke도
> 213.05초여서 post-build 실행 regime 교란이 있으며 후보의 인과적 악화라고
> 단정하지 않는다. 안전하게 후보를 기각했고 planner source는 tracked baseline과
> byte-identical하게 원복·재빌드했다. Parser marker만 재현성을 위해 남겼다.
>
> 새 핵심 결함은 Full seed7 run3의 `max_speed_mps=10.027`이다. PerfectDrone은
> command velocity를 odometry로 그대로 복사하므로 monitor 노이즈만으로 볼 수
> 없다. 현재 `run_valid`는 v=7 제한을 검사하지 않으므로 15/15는 완주/contact
> 기준이지 speed-qualified 100%가 아니다. 다음은 속도 exceedance의 trajectory
> context를 저장하고 publication hard validation을 넣은 뒤 동일 3-mode gate를
> speed-qualified로 재실행하는 것이다. population 100%/flight-ready 보장이
> 아니며 McNemar 미검정, raw-cloud CIRI default false/non-authoritative다. 상세는
> viability §8.29 및
> `docs/reliable_link_n3_and_stationary_defer_rejection_20260826.md`를 볼 것.

> [!IMPORTANT]
> **2026-08-26 reliable filtered-link local gate — 아래 2026-08-25 exact ACK
> 작업의 후속 원인 제거를 완료했다.** 이전 Adaptive seed6-10 n=1의 delivered
> generation ACK는 최대 0.1034초였지만 best-effort `/cloud_sector` hop에서
> 70/582 generation이 유실되어 superseded됐고 SLA timeout이 26회 발생했다.
> guard attribution은 `main_pre MAP_STALE` 184회, recovery gate 225회,
> active 합 247.457초였다.
>
> ACK 미수신 뒤 Full을 한 번 더 보내는 후보는 5/5·contact 0이고 timeout을
> 26->5로 줄였지만 full frame 582->657, guard 225->258, stale 184->223,
> active 합 247.457->291.722초, 평균 시간 96.408->104.306초(+8.19%)로
> 악화돼 기각했다. retry age는 default 0/off이고 최종 gate에서 사용하지 않았다.
>
> 채택 후보는 native C++ filter publisher와 ROG-Map subscriber 사이 내부
> hop만 reliable depth-1로 맞춘다. 실행 파일과 ROG-Map option 기본값은 false,
> 새 `_filtered_reliable.yaml` 및 runner flag에서만 opt-in이다. 기존 프로파일,
> simulator->filter best-effort 입력, exact ACK/certified resume, raw-cloud CIRI
> default false/non-authoritative는 바뀌지 않았다.
>
> 최종 seed6-10 x Full/Sector/Adaptive x n=1은 15/15 valid, first-attempt
> 완주였다. Full/Adaptive는 각 5/5·contact 0·static-PCD collision 0이고 fixed
> Sector는 seed8에서 contact/static collision 1회가 있었다. 평균 시간은
> 84.16/83.94/86.02초다. Adaptive는 Full 대비 points/update 17.38%, map
> total/update 14.50%, 전체 mapping point/work 37.78%/35.61%, FSM+filter
> core-seconds 9.59%를 줄였고 시간 penalty는 2.21%였다.
>
> Adaptive pre-stale generation은 393/393 exact ACK, superseded/timeout/final
> pending 0이다. 이전 best-effort n=1 대비 평균 시간 -10.78%, guard gate
> 225->195, stale 184->164, recovery active 합 -16.90%다. 그러나 이는 n=1
> local regression gate라 population 100%/flight-ready 보장이 아니며 McNemar를
> 하지 않았다. 다음은 이 opt-in 프로파일의 map-labelled 반복 검증이고, 그 뒤
> 남은 brake rejection/stop-replan 비용을 분해한다. 상세는 viability §8.28 및
> `docs/reliable_filtered_link_guard_duty_v7_seed6_10_n1_20260826.md`를 볼 것.

> [!IMPORTANT]
> **2026-08-25 exact full-generation ACK + certified resume — 바로 아래
> pre-stale proxy의 다음 구현을 완료했다.** Adaptive full refresh가 reliable
> request sequence와 exact `PointCloud2` stamp를 보내고, ROG-Map이 그 scan을
> 실제 처리한 뒤 exact stamp/map-version ACK를 발행한다. guard recovery는
> post-edge full의 exact ACK, fresh map/odom, certified stop, 새 `PlanFromRest`,
> 새 trajectory certificate 뒤에만 재개한다. oldest unresolved request가
> 0.75초 SLA를 넘기면 정상 비행을 계속하지 않고 certified brake 경계로
> 들어간다. fresh candidate가 기하학적으로 거부되면 기존 topology blocker가
> 다른 homotopy를 탐색한다. ACK loss 자체로 가짜 obstacle을 만들지는 않는다.
>
> 최종 seed6-10 x Full/Sector/Adaptive x n=1 15회는 모두 valid, first attempt,
> 완주·live contact 0·static-PCD collision 0이다. retry/OOM/FSM swap/PSI도 0이다.
> Adaptive 평균 시간은 Full 84.00초 대비 96.41초(+14.77%)이고,
> update-weighted points/update 16.12%, map total/update 15.52%, observed map
> rate 32.47%, time-weighted FSM CPU 24.68%를 줄였다. 같은 5개 맵의 total
> mapping point/work는 34.99%/34.52% 감소했다.
>
> pre-stale full 582개 중 512개가 exact ACK, 70개가 superseded, final pending
> 0이다. delivered ACK latency는 평균 0.0436초, 최대 0.1034초였다. 따라서 아래
> version-proxy 최대 11.245초는 특정 full cloud 처리 latency가 아니었다. 같은
> 실행의 기존 proxy는 582/582 advance였지만 exact ACK는 512/582뿐이었다. 다만
> best-effort cloud loss는 실제이며 0.75초 SLA timeout marker가 26회 관측됐다. recovery
> gate는 225/225 exact ACK 뒤 재개했고 모든 run이 완주했다. Full/Sector는
> generation stream을 광고하지 않아 새 gate 지표가 전부 0이다.
>
> 실행 파일/planner option 기본값은 계속 off이고 strict Adaptive runner만
> 켠다. raw-cloud CIRI도 계속 default false/non-authoritative다. 이 결과는
> late-map n=1 local gate이며 population 100%/flight-ready 보장이 아니고
> McNemar 미검정이다. guard duty도 79.60-94.68%로 남았다. 다음 과제는 ACK
> threshold를 숨기는 튜닝이 아니라 repeated guard episode/stop-replan 비용을
> 원인별로 줄이는 것이다. 상세는 viability §8.27,
> `docs/generation_ack_certified_resume_v7_seed6_10_n1_20260825.md`, raw는
> `results/generation_ack_final_3mode_seed6_10_n1_raw_20260825.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-25 pre-stale full refresh n=3 gate — 바로 아래 2026-08-24
> first-brake 반례의 다음 구현을 완료했다.** Adaptive C++ filter가 map commit
> age 0.25초에서 complete scan을 한 map version당 한 번만 보내고, 이후
> `commit_version > source_version`을 version-advance ACK proxy로 기록한다.
> 실행 파일 기본값은 0/off이고 strict campaign runner만 0.25초를 쓴다. 이 ACK는
> 특정 frame content의 처리 완료 token이나 formal freshness certificate가 아니다.
>
> seed7 threshold 0.35/0.25초 각 n=3은 모두 완주·contact 0이었다. 0.25초가 실제
> trigger 0.403초, ACK 0.175초, mean mission 102.68초로 더 나아 채택했다. 이어
> order-crossed seed1-10 x n=3 x Full/Sector/Adaptive 90회는 모두 valid,
> one attempt, raw complete였다. Full/Adaptive는 각각 **30/30·contact 0**, fixed
> Sector는 **30/30이지만 seed9/10의 2 runs에서 3 contact events**였다. 이전
> Adaptive seed7 stale-map first-brake contact는 재발하지 않았다.
>
> Full 대비 Adaptive는 update-weighted points/update 18.90%, map total/update
> 23.86%, map update time 15.12%를 줄였지만 mean mission은 76.63->103.26초,
> **+34.75%** 길어졌다. pre-stale frame/version advance는 2,369/2,369, pending
> 0, 평균 trigger/ACK latency는 0.386/0.207초였지만 최대는 3.150/11.245초다.
> late seed guard duty도 80-92%다. 다음 구현은 threshold/cap 추가 튜닝이 아니라
> **content-specific request/generation ACK + fresh-map successful replan 뒤 certified
> resume**, SLA miss 시 **certified stop-and-topology-reroute 1회**다. 같은 version
> full frame flood와 blind hold 축소는 금지한다.
>
> 이 결과는 local n=3 기술 통계이며 population 100%/flight-ready 보장이 아니다.
> McNemar는 수행하지 않았다. raw-cloud CIRI는 계속 default false/non-authoritative다.
> 상세 맵별 표와 forensics는 viability §8.26 및
> `docs/pre_stale_refresh_3mode_v7_n3_20260825.md`, raw는
> `results/prestale025_order_crossed_3mode_v7_n3_raw_20260825.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-24 guard duty attribution 및 first-brake 반례 — 아래 direct
> guard refresh 배너의 “최종 contact 0” 상태를 새 n=1 gate가 반증했다.**
> C++ Adaptive 통계에 direct guard의 실제 `active`와 recovery 뒤
> `hold-only` frame/duty를 분리했다. 기존 5 Hz·2.5초 hold·6,000점 동작은
> 바꾸지 않았다. seed6-10 진단은 5/5·contact 0이었고 active/hold-only
> duty 평균은 59.42%/32.86%여서, 후반 비용은 hold만이 아니라 실제 guard
> 재발이 더 큰 원인임을 확인했다.
>
> guard active 동안만 6 Hz를 허용한 후보도 seed6-10 5/5·contact 0이었지만
> 평균 시간 133.02->163.89초(+23.20%), map total/update
> 26.26->29.45ms(+12.14%)로 악화돼 폐기했다. 옵션 기본값은 0으로, 기존
> 5 Hz를 그대로 쓴다.
>
> 이어 실행한 order-crossed seed1-10 x n=1 x 3-mode 30회는 전부 valid,
> retry/FSM swap/OOM 0이고 세 모드 모두 10/10 완주했다. 그러나 live contact
> run은 Full 0, Sector 1(seed10), Adaptive 1(seed7)이다. Adaptive seed7은
> static-PCD contact는 아니지만 static body clearance가 +0.036m뿐이었고,
> live point는 0.19861m로 0.20m body threshold 안쪽이었다. 따라서 Adaptive는
> 현재 contact-zero 목표를 충족하지 못한다.
>
> 원인은 hold가 아니다. epoch 1787565836.311에 guard가 map age 0.558초의
> `MAP_STALE`을 감지한 뒤 stale map에서 0.529초 brake를 `SAFE`로 승인했고,
> direct true-edge가 새 full scan을 요청했지만 이미 실행 중인 첫 brake의
> endpoint는 바꾸지 못했다. 0.440초 뒤 brake 끝에서 contact가 기록됐다.
> 다음 구현은 0.50-0.55초 stale threshold **이전**에 ACK/version-gated full
> refresh 1회를 보내는 bounded pre-stale 방식이다. hold 단축이나 6 Hz 재적용은
> 금지한다. 상세 맵별 표와 로그 해석은 viability §8.25 및
> `docs/guard_duty_3mode_v7_n1_20260824.md`를 볼 것. raw-cloud CIRI는 계속
> default false/non-authoritative다.

> [!IMPORTANT]
> **2026-08-24 direct trajectory-guard sensing 후속 — 아래 2026-08-23
> 배너들의 “반복 gate 필요”를 실행했다.** 먼저 bounded local horizontal
> escape를 추가했다. certified stop 뒤 A* `NO_PATH`일 때 rejected route 반대
> 방향 0.6 m 후보를 1회만 시도하고, 실패하면 기존 vertical 후보 1회 뒤 hold한다.
> 모든 후보는 기존 trajectory guard/viability를 그대로 통과해야 하며 Full seed7
> n=10은 10/10·contact 0이었지만 local branch 자체는 실행되지 않았다.
>
> 같은 코드의 seed1-10 x n=5 x 3-mode order-crossed 150회에서 Full은
> **50/50·contact 0**, fixed Sector는 **50/50·contact 3 runs**, Adaptive는
> **49/50·contact 1 run**이었다. Adaptive seed7 run2는 emergency brake 중
> 두 번 접촉한 뒤 3/5 waypoint에서 멈췄다. 기존 0.6초 replan-failure burst는
> 실제 guard brake 사이에 닫힐 수 있었다.
>
> `FsmRos2`가 이제 reliable transient-local
> `/planning/trajectory_guard_recovery_active`를 직접 발행하고 Adaptive C++
> filter만 구독한다. guard recovery 종료 후 2.5초 hold하며, 매 guard true-edge의
> 다음 cloud 한 프레임은 5 Hz cap과 6,000-point far-field limit를 모두 한 번
> 우회한다. 이후 open frame은 다시 6,000점 상한이다. true-edge가 아니라 open
> transition에 refresh를 묶었던 중간 구현은 37 guard events를 refresh 2회로
> 합쳐 seed6을 2/5에서 정지시켰으므로 폐기했다. 5 Hz cap 전체 해제도 kept
> 63.75->80.53%, FSM CPU 57.07->61.58%로 악화돼 폐기했다.
>
> 최종 edge-refresh는 seed6/7 Adaptive 각 n=5에서 **10/10·contact 0**, 별도
> Adaptive seed1-10 n=1에서 **10/10·contact 0**이다. 최종 n=1 비교는
> Full/Adaptive **10/10·contact 0**, Sector **10/10이지만 seed9/10 contact**다.
> Full 대비 Adaptive weighted reduction은 points/update 23.39%, map
> total/update 23.17%, map update 16.29%, FSM CPU 25.10%이고 mean mission은
> 71.75->80.92초(+12.78%)다. 늦은 seed의 direct-guard open duty가 83-97%라
> 다음 과제는 **hold를 맹목적으로 줄이지 않고** duty/time을 낮추는 것이다.
>
> 이 결과는 population 100%나 flight-ready 보장이 아니고 최종 3-arm n=1은
> 진단 때문에 split follow-up으로 완성했으므로 McNemar 미검정이다. raw-cloud
> CIRI는 계속 default false/non-authoritative다. 상세는 viability §8.24와
> `results/*20260824.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 endpoint hard guard + Adaptive commit-refresh 후속 — 바로 아래
> §8.22 배너의 “다음 구현”을 완료했다.** Full trajectory commit은 실제 current
> odometry pose, 첫 검사 pose, terminal pose에 대해 raw OCCUPIED voxel과
> `robot_r` body clearance를 hard invariant로 검사한다. 이 검사는 initial
> clearance escape 밖에 있어 short tail이 접촉 pose에서 stationary hold가 되는
> 경로를 닫는다. Adaptive는 ROG-Map의 `/rog_map/commit_version` ACK가 0.12초
> 이상 늦을 때 0.10초 최소 간격으로 sector-only latest refresh를 허용하고,
> full-open의 sector/near-field 밖 far-field를 프레임당 6,000점으로 제한한다.
>
> v=7, `loop24.txt`, static PCD, seed1-10 x n=1 x 3 modes에서 Full은
> **10/10**, Sector **9/10**, Adaptive **10/10** 완주했고 30/30 contact 0이다.
> 최악 static body clearance는 +0.252/+0.108/+0.174 m다. seed10 Sector만
> 4/5 waypoint에서 240.01초 timeout했고 Full/Adaptive는 85.39/118.91초로
> 완주했다. Adaptive는 실제 full-open/close 289/289회, commit refresh 309회,
> ACK 2,889회(3.364 Hz)를 기록했다.
>
> Full 대비 Adaptive는 points/update 36.30%, throughput 62.13%,
> mapping/update 47.66%, mapping work/mission 63.24%, combined CPU-work 15.08%
> 감소했고 mean mission은 18.16% 길다. 이전 n=5보다 Adaptive map commit은
> 2.944 -> 3.336 Hz, `MAP_STALE`은 70.86 -> 61.30/run, brakes는 45.84 ->
> 38.80/run으로 개선됐다. 다만 seed9/10은 topology arm/search가 계속 많아
> 늦은 시드의 시간 문제를 완전히 해소하지 못했다.
>
> 이 n=1에서 새 endpoint `OCCUPIED` reject 자체는 발생하지 않았다. 따라서
> identified code hole의 수정과 무회귀 증거이지 희귀 분기의 execution proof나
> population 100% 보장이 아니다. 모든 row retry/OOM/FSM swap 0, peak FSM RSS
> 3476.25 MiB였다. raw-cloud CIRI는 default false다. 상세는 viability §8.23,
> `docs/endpoint_guard_commit_refresh_3mode_v7_n1_20260823.md`,
> `results/endpoint_commitrefresh_3mode_strict_v7_n1_*_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 order-crossed 3-mode n=5 후속 — 아래 bounded-memory n=1
> 배너의 “broad clean campaign pending” 상태를 대체한다.** v=7,
> `loop24.txt`, static PCD, seed1-10 x n=5에서 Full/Sector/Adaptive를 한
> 캠페인 안에서 순서 교차해 150회를 실행했다. Full은 direct
> `/cloud_registered`, Sector/Adaptive는 C++ strict-burst를 거친
> `/cloud_sector`를 사용했고 150행 모두 valid/1 attempt/raw complete였다.
>
> static-safe는 **49/50, 48/50, 50/50**, live-only threshold까지 포함한
> all-detector-safe는 **49/50, 47/50, 50/50**이다. contact runs/events는
> Full 1/2, Sector 3/6, Adaptive 0/0이다. Adaptive는 관측 표본에서 Sector
> 접촉을 모두 제거했지만 Full 목표인 100%/접촉 0은 달성하지 못했다.
>
> Full 유일 접촉은 seed7 run1의 시작 배치 문제가 아니다. generation-7
> short tail이 `[11.950,12.850,1.050]`에서 끝났고 guard는 짧은 remainder와
> 두 `no_backup` tail을 `SAFE`로 commit했지만, 같은 시각 CIRI는 obstacle
> distance 0.0179 m로 corridor infeasible을 경고했다. trajectory가 그
> endpoint에서 끝난 뒤 static/live가 모두 접촉을 확인했다. 다음 코어 수정은
> topology 재시도나 필터 튜닝이 아니라 **현재 pose와 terminal stop pose의 hard
> clearance를 short-tail/stationary-hold 인증 전제조건으로 넣고, body envelope
> 진입 전에 stop하게 하는 것**이다.
>
> Adaptive 실제 출력 상태는 full-open **1518회**, close **1512회**, time-weighted
> open duty 22.43%다. Full 대비 map commit/points-update/throughput/
> mapping-update/mapping-work/combined CPU-work 감소는 각각 46.15/32.61/
> 63.71/44.23/63.25/16.13%다. mean mission time은 22.35% 길다. exact paired
> McNemar는 Full-Sector p=0.625, Sector-Adaptive p=0.250,
> Full-Adaptive p=1.000으로 유의하지 않다. Adaptive 50/50의 exact two-sided
> 95% population lower bound는 92.89%이므로 population 100% 주장은 금지한다.
>
> 전체 150회는 FSM swap/retry/OOM/PSI가 모두 0이고 peak FSM RSS 3474.36
> MiB였다. runner는 direct/filtered split config를 topic까지 검증하며, seed
> 경계에서도 순서 회전을 이어가고 sequence/order position을 CSV에 남긴다.
> raw-cloud CIRI는 계속 default false다. 상세는 viability §8.22,
> `docs/order_crossed_3mode_strict_v7_n5_20260823.md`,
> `results/order_crossed_3mode_strict_v7_n5_*_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 bounded-memory + 유효한 3-mode 후속 — 바로 아래 §8.20 배너의
> memory/swap 미해결 상태를 대체하되, n=50 liveness 결과 자체는 대체하지 않는다.**
> Full 후반 오염의 직접 원인은 (1) 모든 재계획 로그가 SFC 전체 cloud를 종료
> 때까지 보관하던 무제한 누적과 (2) `raycasting_en=false`에서도 491 x 491 x 981
> 전체 맵 크기로 잡던 두 `uint16_t` counter 배열 약 0.88 GiB였다. 일반 캠페인은
> detailed cloud를 끄고 scalar/trajectory 로그만 최근 64개로 제한했으며, no-raycast
> counter는 스캔에서 실제 건드린 voxel만 저장하는 sparse batch cache로 바꿨다.
>
> runner는 이제 attempt별 memory trace, FSM RSS/PSS/swap, host/cgroup memory/swap,
> PSI, retry reason, OOM delta를 보존한다. 동시에 이번 세션 초기 Sector/Adaptive가
> direct-Full YAML을 받아 실제로는 `/cloud_registered`를 읽은 유효성 오류를 찾았다.
> 그 행은 비교에서 전부 제외했다. 이제 Sector/Adaptive override가
> `/cloud_sector`가 아니면 실행 전에 실패하고, direct Full은 불필요한 filter를
> 띄우지 않는다.
>
> 올바른 입력으로 v=7, `loop24.txt`, static PCD, seed1-10 x n=1을 다시 실행한
> 결과 raw 완주는 Full/Sector/Adaptive 모두 **10/10**, static-safe 완주는
> **10/10, 9/10, 10/10**이다. direct/filtered 양쪽 모두 detailed SFC cloud를
> 끄고 같은 64-record bound를 사용했다. Sector seed7만 2 contact events/1 static
> episode, body clearance -0.007 m였고 Full/Adaptive는 contact 0이다. Adaptive
> 실제 출력 상태는 full-open **321회**, close **320회** 전환했고 time-weighted
> open duty는 23.38%였다. seed5가 open 상태로 종료되어 close가 하나 적다.
>
> Adaptive는 Full 대비 points/update 28.33%, throughput 57.09%, mapping/update
> 43.55%, mapping work/mission 58.64%를 줄였다. 관측 combined CPU-work도 9.74%
> 낮았지만 순차 n=1이라 broad end-to-end CPU 결론은 아니다. 최종 30회는 FSM
> swap 0, retry 0, OOM delta 0이며 peak FSM RSS는 3455.69 MiB였다. Sector seed1에서
> host-wide memory PSI 0.18이 잠깐 관측됐지만 나머지는 0이고 FSM swap/OOM은 없었다.
> 최종 최고속도는 Full/Sector/Adaptive 7.004/7.014/7.006 m/s다. 이 n=1은
> unpaired smoke이고 McNemar 미검정, population/flight-ready 보장이 아니다.
> raw-cloud CIRI는 계속 default false다.
>
> 상세는 viability §8.21,
> `docs/memory_bounded_3mode_v7_20260823.md`,
> `results/final_postopt_3mode_n1_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 stopped A* timeout 후속 — 바로 아래 native n=1 배너의 “n=5
> pending” 상태를 대체한다.** 같은 세션의 패치 전 seed1-10 x n=5에서 Full은
> 49/50, native C++ Adaptive는 48/50이었고, 세 실패 모두 seed9의 정지 상태
> `PlanFromRest -> A* TIME_OUT` 반복이었다. 기존 topology recovery가 `NO_PATH`만
> 인정하고 `PlanFromRest()` 결과는 Adaptive filter의 `/planning/replan_status`로
> 발행하지 않아 동일 topology와 sensing state를 반복했다.
>
> `fsm.cpp`는 이제 `PlanFromRest()` 성공 여부도 replan status로 발행한다.
> `super_planner.cpp`는 topology guard가 켜지고 `planning_from_rest=true`일 때만
> `TIME_OUT`을 기존 `NO_PATH`와 같은 bounded recovery evidence로 인정한다.
> 이동 중 timeout은 제외했고 clearance, 충돌 판정, sector 형상, raw-CIRI 권한은
> 바꾸지 않았다.
>
> 패치 후 seed9 targeted는 Full/Adaptive 각각 5/5, 전체 seed1-10 x n=1도 각각
> 10/10이었다. 최종 독립 n=5에서 Full과 native Adaptive가 모두 raw/static-safe
> **50/50**, live/static 접촉 **0/50**을 관측했다. 최악 static body clearance는
> Full +0.155 m, Adaptive +0.139 m이고 seed9/10도 양쪽 모두 각 5/5다. Adaptive
> 최종 로그에서는 실제 `reason=astar_timeout` recovery가 5회 실행됐고 관련 run은
> 모두 완주했다.
>
> Adaptive는 최종 Full 대비 processed points/update 25.58%, throughput 32.53%,
> mapping/update 29.62%, mapping work/mission 48.39%를 줄였다. 다만 Full arm 도중
> infrastructure retry 1회와 심한 memory/swap pressure가 관측돼 이 n=50 쌍의
> end-to-end CPU 비교는 오염됐다. 깨끗한 patched n=1에서는 Adaptive combined
> CPU-work가 15.62% 낮았지만, n=50 CPU 결론은 clean host/order-crossed 재측정 전까지
> 보류한다. 코호트는 unpaired라 McNemar를 하지 않았고 50/50은 population 보장이
> 아니다. raw-cloud CIRI는 계속 default false다.
>
> 상세는 viability §8.20,
> `docs/native_cpp_timeout_recovery_v7_20260823.md`,
> `results/full_adaptive_timeoutfix_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-23 native C++ Adaptive 후속 — Python CPU 병목은 n=1-per-seed
> smoke에서 해소됐다.** strict Adaptive 정책은 바꾸지 않고 별도 ROS2 C++ node
> `native_sector_cpp`로 옮겼다. 캠페인은 `--filter-backend cpp`로 선택하며 기본은
> 계속 Python이다. seed12-15 trap-event 계측은 아직 C++ 미지원이라 runner가 해당
> 조합을 명시적으로 거절한다.
>
> 첫 실제-cloud pilot은 MARSIM raw point stride 32 bytes를 그대로 복사해 Python
> `create_cloud()`의 packed 20-byte 출력과 달랐다. seed4에서 `fsm_node`가 약
> 9.1 GiB RSS 후 OOM-kill됐다. 선언된 field만 20 bytes로 재포장한 뒤 seed4 smoke와
> seed1-10 n=1 두 cohort에서 OOM은 재현되지 않았다. 합성 Python/C++ 출력 점·dense
> flag·통계도 일치했다. 러너는 이제 임무 중 FSM/filter 종료를 infrastructure
> retry하며 C++ CPU는 wrapper가 아닌 실제 argv0 PID를 잰다.
>
> 두 C++ cohort 모두 raw/static-safe **10/10**이었다. 첫 기능 cohort는 live/static
> 접촉 0이었다. 정확한 CPU cohort는 static 접촉 0이지만 seed10 이륙 초기에
> live-only 0.1995 m threshold event 1회가 있었고, 같은 run의 static PCD는 centre
> 0.321 m/body +0.121 m/contact 0이었다. 따라서 모든 detector 0이라고 합치지 말 것.
>
> 정확한 CPU cohort의 C++ filter는 2.522 CPU-s/mission, FSM+filter는
> 54.559 CPU-s/mission이었다. 이전 Python Adaptive n=50 대비 filter/전체 work는
> 76.17%/14.88% 감소했고, Full direct n=50보다 전체가 2.44% 낮게 관측됐다.
> mapping points/throughput/time/work도 Full 대비 26.44%/25.92%/28.67%/44.21%
> 감소했다. 그러나 C++은 seed당 1회이고 비교 cohort는 서로 unpaired다. §8.18의
> n=50 결과를 대체하거나 population/end-to-end CPU 확정으로 쓰지 말고 native n=5
> gate를 다음 단계로 수행할 것. raw-cloud CIRI는 계속 default false다.
>
> 상세는 `docs/adaptive_cpp_v7_n1_20260823.md`, viability §8.19,
> `results/adaptive_cpp_strict_v7_n1_cpu_raw_20260823.csv`,
> `results/adaptive_cpp_strict_v7_n1_summary_20260823.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-22 Adaptive liveness 후속 — 바로 아래 strict v7 배너의 Adaptive
> 49/50을 대체한다.** Full/Sector 코드는 바꾸지 않고 Adaptive filter의 replan
> recovery를 bounded one-shot으로 만들었다. 0.25 s burst/1.75 s cooldown broad
> 결과는 seed9 run5가 waypoint 3/5에서 240 s timeout되어 49/50이었으므로
> 불채택했다. 정지점 `(18.633, -24.281, 1.332)`은 static body clearance
> +0.091 m로 접촉은 아니었지만 CIRI 시작점이 infeasible해져 같은 fallback을
> 반복 거절한 liveness 실패였다.
>
> 최종 Adaptive는 replan failure 3연속마다 **0.6 s full-cloud one-shot,
> 1.4 s cooldown**을 사용하고 filtered cloud publication만 최대 5 Hz로 제한한다.
> input callback과 recovery 상태 갱신은 생략하지 않는다. 실제 관측값은 input
> 6.509 Hz, publish 4.188 Hz, map commit 3.132 Hz다. v=7, `loop24.txt`, timeout
> 240 s, static PCD, seed1-10 각 n=5의 별도 후속 cohort에서 Adaptive는 raw/safe
> **50/50**, live/static 접촉 **0/50**, 최악 body clearance **+0.100 m**를
> 관측했다. seed9은 targeted 5/5와 broad 5/5에서 각각 통과했다.
>
> 8.17의 변경 없는 Full 기준 대비 Adaptive 처리점/update **29.22% 감소**,
> 처리량 **25.55% 감소**, mapping/update **32.40% 감소**, 임무당 mapping work
> **46.29% 감소**다. 단 Python filter까지 합친 FSM+filter CPU-work는 Full보다
> **14.61% 높다**. 따라서 mapping-work 감소만 주장할 수 있고 end-to-end CPU
> 감소는 아직 아니다. Full/Sector와 새 Adaptive는 서로 다른 캠페인이어서 paired
> McNemar 대상도 아니다. 관측 50/50은 population/flight-ready 보장이 아니며
> raw-cloud CIRI는 계속 shadow-only/default false다.
>
> 상세/원시는 `docs/strict_v7_3mode_n5_20260822.md` 후속 절, viability 문서
> §8.18, `results/adaptive_replan060_cap5_strict_v7_n5_raw_20260822.csv`,
> `results/strict_v7_adaptive_recovery_n5_summary_20260822.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-22 strict v7 결과 — 아래 2026-08-21 배너의 설정과 결론을
> 대체한다.** 이전 sector/adaptive는 wall-time의 약 91% 동안 full-open이라 입력점을
> 약 3%밖에 줄이지 못해 사용자가 의도한 ablation이 아니었다. 새 `strict-burst`는
> fixed Sector를 계속 닫아 두고 Adaptive에만 0.6 s full-cloud burst/1.4 s cooldown과
> 속도 의존 near-field halo를 준다. Full은 필터를 거치지 않는 direct
> `/cloud_registered`와 전용 tight-v7 설정을 사용했다.
>
> v=7, `loop24.txt`, timeout 240 s, seed1-10 각 n=5의 유효 150회 결과는 raw
> 완주 Full **50/50**, Sector **50/50**, Adaptive **49/50**이다. static-PCD 접촉까지
> 0이어야 하는 안전 완주는 **50/50, 46/50, 49/50**이다. Full live/static 접촉은
> 모두 0이었다. Sector는 seed7 run2/run4, seed8 run3, seed10 run5에서 live와
> static 양쪽이 확인한 실제 접촉 4 run/6 live episode/4 static episode가 있었고,
> 최악 body clearance는 -0.184 m였다. Adaptive는 접촉 0, 최악 clearance
> +0.103 m였지만 seed9 run1이 waypoint 4/5에서 timeout됐다.
>
> Full 대비 Sector의 처리점/update와 mapping/update는 **52.40%/57.04% 감소**,
> Adaptive는 **40.54%/47.19% 감소**했다. Sector/Adaptive 입력점 감소는
> 46.09%/30.30%, Adaptive full-open frame duty는 15.28%다. 설정 주파수는 모두
> LiDAR 10 Hz, replan 15 Hz, FSM/command 100 Hz로 같지만 관측 map commit은
> 2.977/3.216/2.816 Hz였다. filtered cloud callback은 Sector/Adaptive
> 4.070/3.982 Hz이며 Full direct callback은 계측하지 않았다.
>
> 따라서 이 표본은 **Full 100%/충돌 0, fixed Sector의 정보 절단에 따른 안전 저하,
> Adaptive의 안전 회복과 Full 대비 연산량 절감**이라는 연구 방향을 기술적으로
> 지지한다. 다만 Adaptive raw liveness는 Sector보다 좋아지지 않았고, paired exact
> McNemar도 safe completion `p=0.375`, static contact `p=0.125`로 유의하지 않다.
> population 보장이나 flight-ready로 쓰면 안 된다. 새 saturation vertical recovery는
> marker 0회라 이 결과의 원인으로 주장할 수 없다. raw-cloud CIRI는 계속
> shadow-only/default false다.
>
> 상세/원시는 `docs/strict_v7_3mode_n5_20260822.md`,
> `results/strict_v7_full_n5_raw_20260822.csv`,
> `results/strict_v7_sector_adaptive_n5_raw_20260822.csv`,
> `results/strict_v7_3mode_n5_summary_20260822.csv` 및 viability 문서 §8.17을 볼 것.

> [!IMPORTANT]
> **2026-08-21 동일 코드 full/sector/adaptive seed1-10 각 n=5 결과 — 아래
> 2026-08-20 seed9/10 local 10/10 배너의 완주 결론을 대체한다.** 총 150회는
> 모두 valid였고 static PCD가 실제 로드됐다. 완주는 full **46/50 (92%)**,
> sector **49/50 (98%)**, adaptive **50/50 (100%)**였다. exact paired
> McNemar는 full/sector `p=0.375`, full/adaptive `p=0.125`,
> sector/adaptive `p=1.0`으로 현재 표본에서 유의한 차이는 아니다.
>
> 모든 모드의 설정 주파수는 LiDAR 10 Hz, replan 15 Hz, main FSM 100 Hz,
> command 100 Hz로 동일했다. 실제 cloud callback은 6.51/6.82/6.63 Hz,
> map commit은 3.94/4.13/4.04 Hz였다. sector/adaptive는 약 91% wall-time
> full-open이라 점을 2.97%/3.01%만 줄였지만 mapping/update는
> 131.65 ms에서 124.97/125.29 ms로 약 5% 감소했다. 전체-run 평균 시간의
> 6-7% 개선은 full의 timeout 4건 영향이 크며 성공-run끼리는 1.93%/0.94%
> 차이뿐이다.
>
> static-PCD contact는 **0/150**, 최악 body clearance는
> full/sector/adaptive **0.129/0.109/0.079 m**였다. seed5 run2 sector의
> live-cloud marker 1회는 static PCD상 centre 0.309 m, body +0.109 m,
> contact 0인 live-only marker다. adaptive 50/50을 안전 여유까지 가장 좋거나
> population 100%라는 뜻으로 쓰면 안 된다.
>
> 실패는 full seed3/6/7/9 각 1건과 sector seed9 1건이다. 세 full 실패는
> 수천 회 MINCO/EXP 반복, seed7은 수천 회 polytope 생성 실패, sector seed9는
> 38회 reroute arm/27회 `NO_PATH`/9회 epoch reset의 topology churn이었다.
> 150회 전체에서 direct-goal fallback commit/reject marker는 모두 0이라 §8.15
> branch가 이 실패들을 커버했다고 볼 수 없다. 상세 표와 원시는
> `docs/guarded_v7_3mode_recovery_n5_20260821.md`,
> `results/guarded_v7_3mode_recovery_n5_raw_20260821.csv`,
> `results/guarded_v7_3mode_recovery_n5_summary_20260821.csv` 및 §8.16을 볼 것.
> raw-cloud CIRI는 계속 shadow-only/default false다.

> [!IMPORTANT]
> **2026-08-20 seed9/10 복구 완료 — 이 배너가 아래의 “미해결” 배너들을
> 대체한다.** §8.14의 stale command 진단은 맞았지만 “실제 odom speed를 쓰면
> 된다”는 설명은 틀렸다. ROS2 ROG odom callback은 `RobotState.v/a/j`를 채운 적이
> 없었고 해당 필드는 초기화조차 안 돼 있었다. simulator twist를 전역 전달한
> 실험은 seed10 실제 접촉을 냈고 전량 되돌렸다. 최종 코드는 legacy state를 0으로
> 명시 초기화하고, brake 선택 안에서만 연속 fresh odom 위치로 motion을 추정한다.
>
> retained fix는 (1) cached command 0.10 s timestamp+position/velocity consistency
> gate, (2) brake selection 직렬화와 fresh position-motion/trajectory fallback,
> (3) 방향별 topology blocker chain + 3회 `NO_PATH` epoch reset, (4) backup/stitch
> reject를 EXP blocker로 오염시키지 않는 guarded EXP-only fallback, (5) stale
> `PlanFromRest`를 막는 map-readiness gate, (6) 센서 해상도/FoV/128-ring을 유지한
> GENERAL_360 렌더 중복계산 제거다. 마지막 waypoint 근처의 반복 MINCO 실패에는
> certified stop+3 m 이내에서만 만들고 기존 geometric guard와 sampled
> stop-viability를 전부 통과해야 하는 direct-goal fallback도 추가했다. fallback의
> local start는 mutex로 복사한 odometry에서 0.15 m 이내여야 한다. 이 branch는 최종
> 무작위 gate에서 발동하지 않았으므로 별도 실증 완료로 주장하지 말 것.
>
> 최종 동일 코드/설정(`v=7`, full, filtered tight-v7, `loop24.txt`, timeout 140 s,
> static PCD 1,042,220점)은 seed9 **5/5**, seed10 **5/5**, 총 **50/50 waypoint**,
> static/live contact **0/10**이었다. 평균 시간은 93.95/99.09 s, 최악 body
> clearance는 0.220/0.132 m였다. 이는 local regression gate이며 population 100%
> 또는 flight-ready 근거가 아니다.
> 위 0.15 m 조건을 넣고 재빌드한 뒤 별도로 돌린 seed10 smoke도 83.92 s에 5/5,
> contact 0, static-PCD body clearance 0.262 m로 통과했다. 이 1회는 n=5 표에
> 합치지 않았다.
>
> 중요한 반증: freshness를 1.50/1.25 s로 늘린 첫 반복은 완주는 빨라졌지만
> static-PCD 접촉 2회(centre 0.142 m, body clearance -0.058 m)를 냈다. 따라서
> 최종 프로파일은 안전 기준 0.75/0.55 s를 그대로 유지한다. global twist 전달,
> KD-tree 렌더 culling, replan 10 Hz도 모두 되돌렸다. 상세와 행별 결과는
> `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.15 및
> `results/guarded_v7_full_seed9_seed10_recovery_n5_20260820.csv`를 볼 것.
> raw-cloud CIRI는 계속 shadow-only/default false다.

> [!IMPORTANT]
> **2026-08-20 seed9/10 full 실패 원인 정정:** 150회 캠페인의 full 실패
> 2건은 map freeze나 단순 timeout이 아니라 certified recovery에 들어가지 못한
> 교착이다. seed9 run4는 gen177을 314회/30.614초, seed10 run2는 gen71을
> 314회/98.871초 거절했다. 둘 다 EXP `CLEARANCE_MARGIN`; 같은 구간에서 brake도
> 314회 전부 거절되어 accepted brake, recovered hold, topology arm/search가 모두
> 0이었다. 지도는 각각 317->401, 44->465로 계속 갱신됐다.
>
> 직접 원인은 `fsm_ros2.hpp`의 `last_published_cmd_`가 timestamp 없이 boolean
> valid로 영구 캐시되는 구조다. guard가 정상 command publication을 막은 뒤에도
> `activateEmergencyBrake()`가 이 stale command를 계속 우선 사용했다. 실제로
> final loop 314회 내내 brake initial speed가 seed9 2.813 m/s, seed10 0.741
> m/s로 고정됐다. brake가 인증되지 않으니 certified-stop flag가 생기지 않고,
> odom speed <=0.2 또는 certified stop을 요구하는 reroute gate도 한 번도 열리지
> 않았다. 성공한 동일 seed 런은 topology arm/search가 정상적으로 발생했다.
> seed10의 460회 replan overtime과 14회 FIRI NaN/Inf는 악화 요인이지만 seed9에
> 없이도 교착이 재현되므로 1차 원인이 아니다.
>
> 다음 수정 우선순위는 cached command timestamp/odom consistency 검사 -> fresh
> actual recovery state로 brake 구성 -> 반복 reject의 bounded fail-closed state다.
> moving brake collision로 blocker를 놓는 과거 실패안은 되살리지 말 것. 상세는
> `docs/guarded_v7_full_seed9_seed10_failure_analysis_20260820.md`와 §8.14.
> static-PCD runner는 옵션 순서와 active-index validity 검사를 고쳤고 seed1 smoke로
> 실제 로드를 확인했지만, 기존 150회의 미계측값은 여전히 무효다.

> [!IMPORTANT]
> **2026-08-20 guarded v7 full/sector/adaptive n=5 최신 결과:** seed1-10의
> 세 모드를 각 5회, 총 150회 실행했다. 완주는 full **48/50 (96%)**,
> sector **46/50 (92%)**, adaptive **47/50 (94%)**였고 exact paired
> McNemar는 각각 `p=0.6875`, `p=1.0`이라 완주율 차이를 통계적으로
> 확정할 수 없다. weighted point 감소도 sector **2.72%**, adaptive
> **2.54%**뿐이었다. replan-failure safety valve가 두 모드를 평균
> **91.5% full-open**으로 만들었기 때문이다. mapping total time은 약
> 6.4% 줄었지만 평균 mission time은 약 4.1% 늘었다. seed9는
> full/sector/adaptive가 4/5, 3/5, 2/5였고 seed10은 4/5, 4/5, 5/5였다.
> 따라서 아래 §8.12의 seed10 full 5/5는 specific deadlock 제거의 local
> gate이지 결정적 안정성 보장이 아니다.
>
> **안전 계측 정정:** 이 150회 명령의 `--static-pcd`가 argparse의 `--`
> 뒤에 놓여 monitor에서 무시됐다. raw CSV의 모든 `static_pcd_*` 0/null은
> 미계측값이며 기존 0/170에 합치거나 “접촉 0”으로 인용하면 안 된다.
> mode-dependent live cloud는 seed9 sector/adaptive에서 각각 marker 1회를
> 냈다. 실행기는 옵션 순서를 고쳤고, 앞으로
> `static_pcd_enabled=true`와 양수 point count가 아니면 run을 invalid/retry
> 처리한다. 상세 표와 원시는
> `docs/guarded_v7_full_sector_adaptive_n5_20260820.md`,
> `results/guarded_v7_full_sector_adaptive_seed1_10_n5_20260820.csv`를 볼 것.

> [!IMPORTANT]
> **2026-08-20 최신 결과 (이 배너를 가장 먼저 확인할 것):** §8.11의 유일한
> seed10 실패(2/5)는 CIRI shadow overhead가 아니라 한
> `PlanFromRest/with_backup` generation이 같은 충돌점에서 **110회/75.404초**
> 반복 거부된 same-topology deadlock이었다. 기존 회피 구는 정지점에서 약
> 6.2cm밖에 떨어지지 않았고, A*의 3-D 구와 CIRI의 희소 ring+pole 표본도 서로
> 달라 고도만 바꾸거나 표본 사이로 같은 XY 통로를 재사용할 수 있었다.
>
> 이를 **certified stop-and-reroute**로 교체했다. 기존 emergency brake가 끝나고
> fresh map/current odom/0.25초 stable hold가 확인된 뒤에만 FSM이 planner에 정지
> certificate를 전달한다. 새 generation의 첫 reject와 동일 XY collision
> cluster의 매 3번째 reject에서 정지점 앞쪽에 최대 6개의 blocker를 1m 간격으로
> 놓으며, A*는 이를 수직 XY cylinder로 검사하고 CIRI는 같은 경계를 비행 높이
> 전체의 ring들로 인코딩한다. CIRI에는 0.25m
> 이하 높이 간격의 jittered ring을 넣어 optimizer가 blocker 사이/위/아래로 새지
> 않게 했다. 같은 후보를 재수락하거나 guard 기준을 완화한 것이 아니라, 인증된
> 정지 상태에서 guide-path topology 자체를 바꾸는 복구다.
>
> 결과: seed10 연속 n=5는 **5/5 완주, 25/25 waypoint, 접촉 0/5**(평균
> 90.17초), 기존 75.404초 정체는 최장 1.755초로 줄었다. 같은 CIRI-shadow
> test profile의 seed1-10 x n=2는 **20/20 완주, 100/100 waypoint, 접촉
> 0/20**, 평균 74.35초, 최장 same-generation reject span 1.467초였다. 파라미터
> no-op을 피하려고 generic `growth_m/max_radius_m`도 실제 escalation 반경에
> 연결했고, 검증된 tight-v7은 고정 0.8m chain(`growth_m: 0`)을 명시한다.
> 상세는 `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.12와
> `results/topology_cylinder_reroute_cirishadow_n2_20260820.csv`를 볼 것.
> n=2를 100% population 성공률이나 flight-ready 근거로 확대해석하지 말 것.
> raw-cloud CIRI 결과는 여전히 shadow-only/default false이고 브레이크 판정에는
> 연결되지 않았다.

> [!IMPORTANT]
> **2026-08-19 최신 결과 (이 배너를 가장 먼저 확인할 것):** §8.10에서
> 미완이던 raw-scan 누적 CIRI shadow 계산의 **비동기 latest-only 워커 전환을
> 완료하고 검증했다.** `activateEmergencyBrake()`는 대표 후보 하나를
> overwrite 가능한 단일 슬롯에 넣고 최신 완료 결과만 읽으며, 누적 scan
> snapshot/PCL 변환/voxel downsample/CIRI decomposition/containment는 전용
> worker가 수행한다. 판정은 여전히 실제 브레이크 수락/거부에 전혀 관여하지
> 않는다. 첫 async 구현만으로는 seed5가 2/5에 머물렀고, shadow-only인데도
> 별도 `/cloud_registered` DDS 구독이 매 scan PCL 변환과 불필요한 KD-tree
> 생성까지 하던 추가 병목을 발견했다. 최종 구조는 ROG-Map이 이미 수락한
> message를 in-process observer로 넘겨 중복 delivery를 없앴다. 최종
> seed1-10 x n=2, 120초 검증은 **완주 19/20, waypoint 97/100, 접촉 0/20**;
> worker 812건의 총 계산시간은 평균 5.138ms, p95 13.628ms, 최대 22.706ms였지만
> main FSM은 이를 기다리지 않았다. 이는 기존 shadow-off 분포 수준으로의
> 회복이지 95%를 새 population 성공률로 주장할 근거는 아니다. 코드/실험
> 상세는 `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8.11과
> `results/ciri_shadow_async_n2_20260819.csv`를 볼 것.
> `trajectory_guard_raw_cloud_ciri_shadow_en`은 기본값 `false`이고
> 실사용 프로파일(`static_seedmaps_guard_viability_tight_v7.yaml`)엔 안
> 켜져 있어서 현재 baseline엔 영향 없음 — 켜져 있는 건 전용 테스트
> 프로파일(`_cirishadow.yaml`)뿐.

> [!IMPORTANT]
> **2026-08-17/18 최신 결과 (가장 먼저 확인할 것):** 이 문서와 아래 배너들이
> 다루는 seed6 gate 미통과 문제의 실제 지배적 원인은 executor 스레딩 버그
> (`perfect_drone_sim`이 단일 스레드로 돌아서 렌더 콜백이 굶주림)와, 더
> 결정적으로 `Fsm::callMainFsmOnce()`의 `EMER_STOP` 케이스가 살아있는 목표를
> 버리고 무조건 `WAIT_GOAL`로 떨어져 `mission_planner`의 1 Hz 재전송 타이머를
> 기다리던 버그였다 — seed9 한 런에서 미션 시간의 60%가 그냥 대기 상태였다.
> 두 버그 모두 수정 후 seed1-10 스윕(n=1)에서 48/50 완주, 접촉 0/10 (10개 중
> 9개 시드가 5/5). 아직 공식 5-run gate는 미통과. 전체 경위와 실패한 시도들
> (CIRI corridor 3회 시도, topology zone 확장 2회, raw-cloud 누적)은
> `docs/viability_guard_ciri_avoidance_2026-08-15.md` §8을 볼 것 — 아래의
> "occlusion" 계열 설명이나 콜백 그룹 경합 이론은 전부 낡은 것이다.

> [!IMPORTANT]
> **2026-08-14 v7 topology / certified-stop 후속 결과:** 임시 avoidance
> sphere를 A*에 주입하는 topology reroute와 선제 stop 인증을 구현했지만, seed6
> gate는 통과하지 못했다. `0.55 s` 선제 stop n=5는 완주 1/5, 접촉 run
> 1/5였고, fresh raw cloud hazard는 검출됐어도 v=7 현재 상태에서 인증 가능한
> brake 집합이 비는 사례가 확인됐다. 기본 `full_guard_v7`과 새
> `full_guard_reroute_v7`을 flight-ready로 기술하지 말 것. 상세 구현과 steps
> 26–34 원시 결과는 `docs/v7_topology_certified_stop_reroute_2026-08-14.md`를
> 최우선으로 확인할 것.

> [!IMPORTANT]
> **2026-08-14 steps 6–22 continuation:** immutable snapshot and adaptive
> recovery were implemented, but the required gate still failed. The seed6
> five-run smoke completed 2/5 and had contact in 1/5. The 1.25 s freshness
> setting caused a measured late-braking contact and was restored to 0.75 s.
> Read `docs/loop_guard_snapshot_recovery_steps_6_to_22_2026-08-14.md` before
> using any conclusion or configuration in this document.

> [!IMPORTANT]
> **2026-08-14 단계 1–5 후속 결과:** enforcement는 보고된 seed6 시도에서 접촉 0회를
> 유지했지만 5/5 완주 smoke gate를 통과하지 못했다. 따라서 5회 smoke와 50-run은
> 실행하지 않았다. `docs/loop_guard_steps_1_to_5_2026-08-14.md`를 함께 확인하고,
> guard를 flight-ready 또는 escape를 실증 완료로 기술하지 말 것.

> [!CAUTION]
> **2026-08-13 독립 코드 감사 정정 — 아래 결론을 그대로 사용하지 말 것.**
> 이 문서 작성 뒤 소스와 원시 JSON을 다시 대조한 결과, 핵심 인과 해석을 무효화하거나 제한하는
> 다음 사항이 확인됐다.
>
> 1. `obs_skip_num`은 현재 소스에서 `box_search_skip_num_`에 저장되기만 하고 실제 점군 선택에
>    사용되지 않는다. 따라서 2→1은 no-op이며, 이를 "다운샘플링 제거" 또는 corridor 정확도
>    개선으로 해석할 수 없다. baseline 41/50 대 skip1 35/50의 짝비교 exact McNemar 검정은
>    `p=0.146`이었다.
> 2. skip1 35/50 대 clearance+skip1 37/50도 유의한 악화가 아니다. 같은 seed/run 번호의
>    discordant pair는 개선 4, 악화 6이고 exact McNemar `p=0.754`다.
> 3. 추가된 `distancePointToSegment()`는 point seed(`a == b`)에서 0으로 나누어 NaN을 만들 수
>    있다. 또한 preferred plane 생성 뒤 다른 장애물점을 제거하는 기준은 `local_margin`이 아니라
>    여전히 `robot_r_`이므로, 로그의 `local_margin=0.4`는 최종 polytope 전체의 0.4 m margin을
>    보장하지 않는다.
> 4. clearance penalty의 gradient 부호와 `smooth_eps` 공유 자체는 타당하지만, 장애물 유래 면뿐
>    아니라 bounding/ceiling/floor를 포함한 모든 SFC 면의 비용을 합산한다. 0.15 m erosion의
>    feasibility도 확인하지 않고 face 수에 따라 비용이 달라지므로 physical obstacle clearance
>    비용으로는 설계 결함이 있다.
> 5. clearance penalty는 `ExpTrajOpt`에만 적용되고 `BackupTrajOpt`에는 적용되지 않는다. 원시
>    이벤트에서 skip1 접촉 런 35개 중 18개, clearance+skip1 접촉 런 37개 중 25개에 backup
>    trajectory 접촉이 포함됐다.
> 6. monitor의 `DRONE_R=0.20 m`와 planner의 `robot_r=0.20 m`가 같아 계획 여유가 0이다.
>    `min_clearance_m`도 실제 signed body clearance가 아니라 UAV 중심--표면점 거리다.
>
> 따라서 아래 §0의 "두 근본 원인 확정", `obs_skip_num=1`의 개선 효과, preferred-margin 진단과
> 조합 실험의 상호작용 해석은 **가설/관측 기록으로만 보존**한다. 다음 단계는 원본 SUPER의 0%를
> 맞추는 튜닝이 아니라, 반복 방향 전환용 SUPER 기반 planner를 공통으로 보강하고 그 위에서
> full/sector/adaptive를 비교하는 것이다.
>
> **후속 결과:** map-version shadow 재검사와 0.2 m guard margin은 20/20 접촉을 사전
> 탐지했지만, shadow 후보 중 safe 비율이 46.0%뿐이었다. 네 가지 enforcement smoke는 모두
> 접촉 0건이면서도 0/5 waypoint에서 정지했다. 따라서 현재 결론은 `keep_shadow_only`이며,
> 상세 수치와 구조적 원인은 `docs/trajectory_guard_audit_2026-08-13.md`의 마지막 두 섹션을
> 우선 참조해야 한다. 50-run enforcement는 실행하지 않았다.

이 문서는 JKICS 논문용 `super-sector-filter` 프로젝트에서, SUPER의 원본(`full`) 모드가 논문
파라미터(v=10 m/s, max_acc=20, max_omg=2.5) 조건에서 왜 접촉률 0%를 달성하지 못하는지 파고든
조사 전체를 정리한 것입니다. Codex에게 이 파일을 먼저 읽게 하고, 아래 "Codex가 참고해야 할
파일 목록" 섹션에 나열된 코드/설정/데이터 파일을 순서대로 읽게 하면 전체 맥락을 파악할 수
있습니다.

## 0. 결론 요약 (TL;DR)

- **13가지 방법을 시도**했고, `full` 모드의 잔여 접촉률을 0%로 만드는 데는 **아무도 성공하지
  못했습니다.**
- 접촉률만 보면 **`obs_skip_num=1` 단독**(다운샘플링 없이 corridor 생성)이 가장 좋았습니다
  (82% → 70%, 부작용 없음).
- 완주율/안정성까지 고려하면 **`clearance penalty`(MINCO 비용함수에 새로 추가한 항) +
  `obs_skip_num=1` 조합**이 가장 균형 잡힌 결과였습니다(완주율 96%→98%, 접촉률 82%→74%,
  타임아웃 거의 없음).
- **근본 원인은 두 가지가 겹쳐 있는 것으로 결론지었습니다**:
  1. MINCO 궤적 최적화기의 비용함수에는 "corridor(SFC) 안에만 있으면 됨"이라는 단방향
     장벽(one-sided barrier)만 있고, "장애물에서 멀어질수록 좋다"는 항이 원래 없었습니다.
     → 최적화기가 좁은 corridor 벽에 딱 붙어도 비용이 0이라, 실제 여유 공간이 있어도 안 씀.
  2. corridor(SFC) 자체가 CIRI 알고리즘이 본 (다운샘플링된) 장애물 점군을 기준으로 만들어지기
     때문에, 실제 물리적 여유 공간(1~2m)이 있어도 corridor가 그 공간까지 뻗어있지 않으면
     최적화기는 애초에 그 공간에 접근할 방법이 없습니다.
- 두 원인 중 하나만 고쳐서는(아래 실험 8, 2번 참고) 부분 개선만 있었고, 둘을 다양한 방식으로
  조합해봐도(실험 9, 10, 12, 13) obs_skip_num=1 단독보다 확실히 나은 조합은 찾지 못했습니다.
- **아직 풀리지 않은 질문**: 왜 corridor를 정확하게(obs_skip_num=1) 만들고 최적화기에게
  clearance 인센티브까지 줘도(실험 13) 접촉률이 obs_skip_num=1 단독보다 오히려 근소하게
  나쁜가(70%→74%)? 이 부분이 Codex에게 특히 물어보고 싶은 지점입니다.

---

## 1. 문제 정의

- 저장소: `github.com/nawoo99/super-sector-filter` (이 문서가 있는 곳), SUPER 원본은
  `/root/super_ws/src/SUPER` (ROS2 워크스페이스, 별도 git 상태— super-sector-filter는 이
  워크스페이스에 대한 패치/실험 기록 저장소).
- SUPER 논문은 `full`(전체 장애물 점군을 그대로 사용) 모드에서 접촉률 0%를 주장하지만, 이
  프로젝트의 조사에서는 논문과 동일한 파라미터(v=10, max_acc=20, max_omg=2.5)로 재현했을 때
  `full` 모드조차 seed1-10 × 5회(n=50) 기준 접촉률 82%가 나왔습니다(`baseline`).
- 목표: sector/adaptive(제안 기법)와 공정하게 비교하려면 `full`이 0%에 최대한 가까워야
  하는데, 그게 안 되는 이유를 찾고 가능하면 고치는 것.
- 미션: `loop24.txt` (사각형 4개 꼭짓점 + 원점 복귀, 총 5 waypoint), `switch_dist=1.5`,
  `TIMEOUT=85.0s`.
- 평가지표: `success`(완주 여부), `contact`(collisions>0인 run의 비율), `mean_clr`(run별
  `min_clearance_m`의 평균), `timeout`(mission_time_s >= 84.9s인 run 수).

## 2. 이미 확립된 배경 (이 세션 이전에 규명, `paper_story.md` §3.6 / `연구일지.md` 참고)

- `robot_r=0.2`(드론 반지름), 장애물 간 최소 보장 간격(surface-to-surface) 1.0m, 실측
  중앙값 1.24~1.73m (seed별로 다름, seed9/10이 가장 좁음).
- 접촉 시점의 순간 곡률반경(curvature radius, `R=|v|³/|v×a|`) 분석: 중앙값 11.26m로,
  대부분의 접촉이 급회전 때문이 아님(하위 10~25%만 회전반경 문제로 설명 가능).
  → **접촉의 대다수는 회전 동역학 문제가 아니라 corridor가 장애물에 너무 가깝게 만들어지는
  것 자체가 원인**이라는 결론.
- CIRI(corridor 생성 알고리즘)는 corridor를 두 장애물 사이의 중앙에 정렬하는 로직이 원래
  없음 — A*가 찾은 guide_path를 얼마나 타이트하게 감싸는지가 전부.

## 3. 이번 세션에서 시도한 13가지 방법 (전부 v=10, `full` 모드, seed1-10 × 5회 = n=50)

기준선(baseline, `super_planner/robot_r: 0.2`만, `obs_skip_num: 2`):
**완주율 96% / 접촉률 82% / 평균 clearance 0.084m**

### 3.1 Guide-path 중앙 정렬 시도 (전부 실패, 이 세션 이전 파트에서 시도 — `paper_story.md`에
이미 기록됨, 여기서는 요약만)

| # | 방법 | 접촉 | 완주 | clearance | 비고 |
|---|---|---|---|---|---|
| 1 | guide_path 점별 독립 밀기 (0.3m) | 62% | 70% | 0.126m | 완주율 붕괴 |
| 2 | 같은 방식, 0.15m | 66% | 60% | 0.115m | 더 나쁨 (크기 문제 아님을 반증) |
| 3 | 0.15m + guide_stamp(시간) 보정 | 66% | 64% | 0.126m | seed9,10 세 버전 모두 0/5 완주 |
| 4 | v3를 v=4에서 재검증 | 60%(악화) | 78% | 0.157m | v=4 baseline(52%/98%/0.178m) 대비도 악화 → 회전반경 문제 아님 확정 |
| 5 | guide_path 이동평균 스무딩 + v3 | 66% | **40%(최악)** | 0.147m | 코드 리딩으로 원인 규명: guide_path/guide_stamp가 MINCO의 초기 제어점/구간시간으로 그대로 쓰이는데, 점별로 다른 방향으로 밀면 L-BFGS 웜스타트가 톱니모양이 되어 수렴이 나빠짐. 스무딩해도 실패 |

**결론**: guide_path(궤적 최적화의 warm-start)를 건드리는 접근은 전부 net-negative.
→ 이후 corridor 생성(CIRI) 레벨과 비용함수 레벨로 방향 전환.

### 3.2 CIRI corridor 생성 레벨 (이번 세션 본 파트)

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 6 | `obs_skip_num=1` (다운샘플링 제거) | **70%** | 96% | **0.141m** | 낮음 | **유일한 순수 개선** (부작용 없음) |
| 7 | CIRI per-point 선호마진 0.4m (robot_r=0.2는 hard 유지) | 78% | 78% | 0.106m | 11 | 한 corridor 안에서 벽마다 마진이 0.2~0.4m로 비대칭 혼재 → 완주율 붕괴 |
| 8 | CIRI per-corridor **균일** 선호마진 0.4m | 86% | 98% | 0.074m | 1 | 비대칭 문제는 해결(완주율 회복)했지만 **접촉률은 오히려 baseline보다 악화** |
| 9 | `obs_skip_num=1` + 균일마진 0.4m 조합 | 84% | 92% | 0.092m | 4 | 둘 다 corridor "생성" 메커니즘이라 서로 간섭, obs_skip=1 단독보다 전부 나쁨 |
| 10 | `corridor_bound_dis` 0.8→0.4 (corridor가 뻗을 수 있는 최대폭 축소) | 80% | **70%** | 0.069m | **15** | 너무 급격 — corridor 자체를 못 찾아 재계획 실패 폭증 |
| 11 | `corridor_bound_dis` 0.8→0.6 (완만) | 88% | 88% | 0.065m | 6 | 여전히 baseline보다 전부 나쁨. 폭을 줄이는 접근 자체가 안 맞음 |

**진단 실험 (실험 8 데이터 재분석)**: 접촉 위치와 CIRI 로그를 공간 매칭한 결과, 매칭된 접촉의
**67%가 "풀 마진(0.4m)" corridor 안에서** 발생했습니다 — "갑자기 좁아지는 지점에서 부딪힌다"는
가설은 기각. 대신 corridor가 계산에 쓰는 (다운샘플링된) 점군 자체가 실제 장애물 표면을
부정확하게 대표하고 있을 가능성이 높다고 결론.

### 3.3 근본 원인 규명 — 트래킹 오차 분석

`full` 모드 seed10 단독 실행에서 15개 접촉 이벤트 전수를 `position`(실제 위치)과
`position_command.position`(계획된/명령된 위치)으로 비교:
- **10/15(67%)**: 트래킹 오차 = 0.000m (컨트롤러가 계획을 정확히 따라감)
- **5/15(33%)**: 트래킹 오차 0.09~0.10m, 그러나 명령 위치 기준으로 역산해도 대부분 여전히
  위험하게 가까움(0.16~0.23m)
- **→ 15/15 전부, 계획된 궤적 자체가 이미 위험**했습니다. 실행/트래킹 문제가 아닙니다.

MINCO 비용함수(`exp_traj_optimizer_s4.cpp`의 `constraintsFunctional`)를 직접 읽어서 확인:
위치 비용은 `violaPos = outerNormal·pos + d`가 **양수(corridor 밖)일 때만** 페널티를 주는
순수 단방향 배리어. corridor 안에 있는 한, 벽에 딱 붙어도 비용 기여가 0.
**→ 옵티마이저 입장에서 corridor 중앙에 있을 이유가 전혀 없었습니다.**

### 3.4 비용함수 레벨 수정 — Clearance Penalty (새로 구현)

`ExpTrajOpt::constraintsFunctional`에 두 번째 소프트 페널티 항 추가:
`violaClr = violaPos + clearance_margin` — 위치 비용과 동일한 단방향 배리어 모양이지만
`clearance_margin`만큼 안쪽으로 당겨서, corridor 벽에서 그 거리 이내로 들어오면(아직 안을
벗어나지 않았어도) 미리 페널티가 붙기 시작. `weightClr(penna_clr)`로 세기 조절, hard 제약
(`penna_pos`)과는 완전히 별개.

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 12 | clearance penalty 단독 (`penna_clr=1e7`, `margin=0.15m`) | **76%** | 94% | **0.111m** | 3 | **비용함수 레벨의 첫 순수 개선.** 부작용 거의 없음 |

**진단 실험 (실험 12 데이터 재분석)**: seed7/9/10의 접촉 241건 전수를 obstacle manifest CSV와
대조 — 반대쪽 두 번째로 가까운 장애물까지 거리가 **최소 0.79m, 중앙값 1.6m대**였습니다.
0.15m는커녕 1m 이상 여유가 있는 곳에서도 여전히 부딪힘. **→ 실제 물리적 공간은 충분한데,
corridor 자체가 좁게(robot_r=0.2 hard 기준) 만들어져서 최적화기가 그 공간에 접근할 방법이
없었다**는 결론 (이 실험은 `corridor_pref_margin`을 켜지 않은 상태였음).

### 3.5 조합 시도

| # | 방법 | 접촉 | 완주 | clearance | 타임아웃 | 비고 |
|---|---|---|---|---|---|---|
| 13 | clearance penalty + 균일마진 0.4m | 84% | 90% | 0.086m | 5 | **실패** — clr penalty 단독보다 전부 나쁨. 가설: 균일마진 corridor는 다운샘플링된(부정확한) 점군 기준 "여유 있음" 판단이라, 옵티마이저가 그 부정확한 여유를 믿고 더 적극적으로 움직여서 역효과 |
| 14 | clearance penalty + `obs_skip_num=1` | 74% | **98%(전체 최고)** | 0.126m | **1(최소)** | 완주율/안정성은 전체 실험 중 최고. 그러나 **접촉률은 obs_skip_num=1 단독(70%)을 못 넘음** — 오히려 근소 악화(70%→74%) |

## 4. 최종 비교표 (핵심만)

| 방법 | 완주율 | 접촉률 | 평균 clearance | 타임아웃 |
|---|---|---|---|---|
| baseline | 96% | 82% | 0.084m | ~0 |
| **obs_skip_num=1 단독** | 96% | **70%** | 0.141m | 낮음 |
| clearance penalty 단독 | 94% | 76% | 0.111m | 3 |
| clearance penalty + obs_skip_num=1 | **98%** | 74% | 0.126m | **1** |
| CIRI 균일 선호마진 단독 | 98% | 86% | 0.074m | 1 |

## 5. 코드 변경 사항 (전부 `/root/super_ws/src/SUPER/super_planner/`, 아직 미커밋)

### 5.1 CIRI corridor 균일 선호마진 (`corridor_pref_margin`)
- `include/super_core/config.hpp:81,122-124` — 새 yaml 키 `super_planner/corridor_pref_margin`
  (기본 -1 → robot_r로 clamp).
- `include/super_core/ciri.h` — `pref_margin_` 멤버, `setupParams(robot_r, iter_num, pref_margin=-1)`.
- `src/super_core/ciri.cpp:62-77` — **핵심 로직**: 코리도 세그먼트(seed line a,b) 전체에서
  가장 가까운 장애물점까지 거리(`d_min_seed`)를 먼저 스캔해서,
  `local_margin = clamp(d_min_seed, robot_r_, pref_margin_)`로 **그 코리도 전체에 통일된
  마진**을 적용 (한 코리도 안에서 벽마다 마진이 섞이는 비대칭 문제 방지).
- `src/super_core/ciri.cpp:280-317` — `logMarginDebug()`: 환경변수 `CIRI_MARGIN_DEBUG=1`일 때
  `/tmp/ciri_margin_debug.csv`에 각 코리도의 `local_margin`, fallback 여부 등을 기록하는 진단
  로그 (프로덕션에 영향 없음, `pref_margin_ <= robot_r_`이면 아예 비활성).
- `include/super_core/corridor_generator.h:85-88`, `src/super_core/corridor_generator.cpp:34-38`
  — `corridor_pref_margin` 파라미터를 CIRI까지 전달하는 배선.
- `src/super_core/super_planner.cpp:77-84` — `CorridorGenerator` 생성자 호출에
  `cfg_.corridor_pref_margin` 추가.

### 5.2 MINCO Clearance Penalty (`penna_clr`, `clearance_margin`)
- `include/traj_opt/config.hpp:70-75,121-122` — 새 yaml 키 `traj_opt/exp_traj/penna_clr`,
  `traj_opt/exp_traj/clearance_margin`.
- `include/traj_opt/exp_traj_optimizer_s4.h:79` — `OptimizationVariables`에
  `weightClr`, `clearanceMargin` 추가. `constraintsFunctional` 시그니처에 두 파라미터 추가
  (`:115-120` 근방).
- `src/traj_opt/exp_traj_optimizer_s4.cpp:125-150` — **핵심 로직**: 기존 위치 제약 루프(K개
  SFC 평면에 대해 반복하는 for문) 안에, 기존 `violaPos` 계산 바로 뒤에
  `violaClr = violaPos + clearanceMargin`을 추가하고 동일한 `smoothedL1` 페널티 형태로
  `gradPos`/`tmp_cost`에 누적. `weightClr>0 && clearanceMargin>0`일 때만 활성화.
- `src/traj_opt/exp_traj_optimizer_s4.cpp:286,337` — `costFunctional`에서 `obj.weightClr`/
  `obj.clearanceMargin`을 읽어 `constraintsFunctional` 호출부에 전달.
- `src/traj_opt/exp_traj_optimizer_s4.cpp:806-807` — 생성자에서 `cfg_.penna_clr`/
  `cfg_.clearance_margin`을 `opt_vars`에 복사.
- **참고**: `BackupTrajOpt`(`backup_traj_optimizer_s4.cpp`)는 별개 클래스라 이 변경의 영향을
  받지 않음.

### 5.3 리버트된 것
- `super_planner.cpp`의 guide_path 중앙 정렬 코드(4개 버전, §3.1)는 전부 작성 후 리버트되어
  현재 파일에 남아있지 않음. `super_planner.cpp`에는 이 세션과 무관한 (다른 세션의)
  `trajectory_guard` 관련 미커밋 diff가 이미 있었는데, 그건 건드리지 않음.

## 6. 설정 파일 (전부 `/root/super_ws/src/SUPER/super_planner/config/`, 미러본은
`/root/super-sector-filter/super_patches/native_seedmap_campaign/super_planner_config/`)

- `static_seedmaps_paper_v10.yaml` — baseline
- `static_seedmaps_skip1_v10.yaml` — 실험 6 (`obs_skip_num=1`)
- `static_seedmaps_prefmargin_v10.yaml` — 실험 7,8 (`corridor_pref_margin=0.4`)
- `static_seedmaps_skip1_prefmargin_v10.yaml` — 실험 9
- `static_seedmaps_boundhalf_v10.yaml` — 실험 10 (`corridor_bound_dis=0.4`)
- `static_seedmaps_bound06_v10.yaml` — 실험 11 (`corridor_bound_dis=0.6`)
- `static_seedmaps_clrpenalty_v10.yaml` — 실험 12 (`penna_clr=1e7, clearance_margin=0.15`)
- `static_seedmaps_clrpenalty_prefmargin_v10.yaml` — 실험 13
- `static_seedmaps_clrpenalty_skip1_v10.yaml` — 실험 14

## 7. 원시 데이터 위치 (⚠ `/tmp`라 세션 종료 시 소실될 수 있음 — Codex 세션에서 접근
불가능할 가능성이 높으므로, 이 문서의 §3~4 표를 1차 자료로 취급할 것)

- `/tmp/native_campaign/seed{1-10}_run{1-5}_<variant>_v10_full.json` — 각 run의 전체 결과
  (`success`, `collisions`, `min_clearance_m`, `contact_events`[position/position_command/
  nearest_point 포함] 등).
- `/tmp/native_campaign/ciri_margin_debug_seed{N}_*.csv` — CIRI 코리도별 마진/fallback 로그
  (실험 8 진단용).
- 이전 세션에서 이미 커밋된 관련 데이터: `results/native_seed1_10_full_v10_contact_curvature.csv`,
  `results/native_seed1_10_v10_margin_dynamics_ablation.csv`,
  `results/native_seed1_10_full_n5_contact_coordinates.csv`.

## 8. Codex에게 묻고 싶은 것

1. §3.5 실험 14 (`clearance penalty + obs_skip_num=1`)에서 완주율은 최고(98%)인데 접촉률이
   obs_skip_num=1 단독(70%)보다 근소하게 나쁜(74%) 이유가 뭘까요? 두 메커니즘이 서로 다른
   레이어(corridor 생성 정확도 vs 최적화기 행동)라 순수하게 더해질 거라 예상했는데 아니었습니다.
2. `exp_traj_optimizer_s4.cpp`의 clearance penalty 구현(§3.4, §5.2) 자체에 버그나 설계
   결함이 있는지 봐주실 수 있나요? (예: `smoothedL1`의 `smoothFactor=smooth_eps=0.01`을
   `violaPos`와 `violaClr`가 공유하는 게 맞는지, gradient 부호나 스케일이 맞는지 등)
3. `penna_clr=1e7`, `clearance_margin=0.15`는 초기 추정치였고 별도 캘리브레이션을 하지
   못했습니다. 다른 페널티 가중치(`penna_pos=5e9`, `penna_vel/acc/jerk=5e8`)와 비교했을 때
   합리적인 스케일인지, 더 나은 튜닝 방향이 있는지 의견 부탁드립니다.
4. corridor 생성(CIRI) 레벨에서, "다운샘플링 없이(`obs_skip_num=1`) 정확하게 만든 corridor"에
   대해 "균일 선호마진"이 아닌 다른 방식으로 폭을 넓히는 게 가능할지 (예: 장애물 표면까지의
  실제 최근접 거리를 더 정밀하게 재는 방법, voxel 해상도 자체를 높이는 것과의 상호작용 등).

## 9. Codex가 참고해야 할 파일 목록 (우선순위 순)

1. **이 문서** (`/root/super-sector-filter/docs/codex_handoff_full_v10_contact_investigation.md`)
2. `/root/super_ws/src/SUPER/super_planner/src/traj_opt/exp_traj_optimizer_s4.cpp` — clearance
   penalty 구현 전체 맥락 (특히 45-244줄 `constraintsFunctional`, 251-344줄 `costFunctional`)
3. `/root/super_ws/src/SUPER/super_planner/include/traj_opt/exp_traj_optimizer_s4.h`
4. `/root/super_ws/src/SUPER/super_planner/src/super_core/ciri.cpp` — CIRI 균일마진 구현
   (30-253줄 `comvexDecomposition`)
5. `/root/super_ws/src/SUPER/super_planner/include/super_core/ciri.h`
6. `/root/super_ws/src/SUPER/super_planner/src/super_core/corridor_generator.cpp`
7. `/root/super_ws/src/SUPER/super_planner/include/super_core/config.hpp` (super_core) 와
   `/root/super_ws/src/SUPER/super_planner/include/traj_opt/config.hpp` (traj_opt) — 새 yaml
   파라미터 정의
8. `/root/super_ws/src/SUPER/super_planner/config/static_seedmaps_clrpenalty_skip1_v10.yaml` —
   가장 균형 잡힌 실험(14)의 실제 설정값
9. `/root/super-sector-filter/docs/paper_story.md` §3.6 이후, `/root/super-sector-filter/docs/연구일지.md`
   최신 항목들 — 이 세션 이전에 확립된 배경(회전반경 분석, 장애물 간격 실측 등)
