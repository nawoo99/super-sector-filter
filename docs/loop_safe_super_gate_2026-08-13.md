# Loop-safe SUPER: enforcement 승격 gate

현재 결정은 **shadow only**다. `results/trajectory_guard_readiness_20260813.json`이
`ready_for_enforcement: true`가 되기 전에는 trajectory rejection, command suppression,
emergency brake, 50-run enforcement 비교를 켜지 않는다.

## 현재까지 통과한 항목

- 한 validation pass의 map version 일관성: seed2 map race 67 → 0.
- 동일 관측조건 rate-limited control/shadow A/B: 4 paired runs 모두 완주·접촉 0.
- rate-limited shadow의 FSM CPU 중앙 증가: +2.67 percentage points.
- mission time 중앙 증가: +0.86 s, control 평균 대비 3.28%.
- Exp뿐 아니라 appended/carry Backup과 stitch metadata를 검사·기록.

## 아직 통과하지 못한 항목

- dense shadow 접촉 표본 최소 20건: 현재 1건.
- dense shadow contact recall 최소 95%: 현재 1/1이라 수치상 통과지만 표본 미달.
- dense control/shadow paired A/B 최소 10쌍: 아직 없음.
- dense async 비용: seed4 smoke에서 FSM process CPU 128.4%; 최적화 필요.

## 다음 실험 순서

1. dense async worker의 map-query 비용을 줄이되 spatial collision sampling 간격을
   inflation voxel보다 크게 만들지 않는다.
2. 접촉 빈도가 높은 seed4--seed10에서 dense control/shadow를 교차 순서로 최소 10쌍 실행한다.
3. 독립 contact event 20건 이상을 모아 선행 unsafe recall과 segment별 lead time을 계산한다.
4. gate JSON을 다시 생성한다.
5. gate 통과 시에만 enforcement 단일-seed smoke를 수행한다.
6. smoke에서 command starvation과 unsafe brake가 없을 때 10 maps × 5 repeats의 50-run
   control/enforcement 비교로 확대한다.

Gate 실행 예:

```bash
python3 scripts/native_campaign/evaluate_guard_readiness.py \
  --rate-ab-summary results/native_seed2_shadow_ab_n4_summary.json \
  --dense-contact-campaign results/native_seed4_shadow_dense_contact_smoke.csv \
  --dense-ab-summary results/native_dense_shadow_ab_n10_summary.json \
  --out results/trajectory_guard_readiness.json
```

현재처럼 조건이 부족하면 exit code 2와 `decision: keep_shadow_only`를 반환한다. 이는 실행
오류가 아니라 enforcement 차단이 정상 작동한 것이다.
