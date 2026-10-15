#!/usr/bin/env bash
# Separate candidate pilot; never overwrites frozen campaign results.
set -e -o pipefail
if (( $# < 4 )); then
  echo "Usage: bash $0 OUTPUT_DIRECTORY MAP RUN_ID MODE [MODE ...]" >&2
  exit 2
fi
trial_output=$1
trial_map=$2
trial_run=$3
shift 3
if [[ -e "$trial_output" ]]; then
  echo "Refusing existing output: $trial_output" >&2
  exit 2
fi
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
cd /root/super-sector-filter
exec python3 -u /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts/scenario7_topology_liveness_trial_cpu_compare.py \
  --output "$trial_output" --run "$trial_run" \
  --candidate topology_liveness_trial_v2_20261006 \
  --map "$trial_map" --modes "$@" \
  --mean-cpu-reduction-target-pct 30 --compose --profile-cpu \
  --skip-backup-diagnostic-replay --skip-unobserved-path-publication \
  --fast-occupied-box-scan --snapshot-line-query --snapshot-neighbor-cache \
  --side-executor-threads 3 --monitor-intervals --guarded-demand-replan \
  --goal-retransmit-identity --headless-parameter-services \
  --dedicated-static-pc-executor --no-optimizer-phase-memory-trace \
  --optimizer-clearance-gate-first --mission-time-as-metric \
  --sector-outcomes-as-metrics --async-certified-recovery \
  --full-config static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml \
  --sector-config static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearhit_v3.yaml \
  --adaptive-config static_seedmaps_guard_viability_tight_v7_event_recovery_v1_nearhit_v3.yaml
