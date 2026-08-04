#!/bin/bash
# One-command visual watch: sim + RViz + filter, all together.
# Usage: bash watch_native.sh [full|sector|velocity|adaptive|trigger] [seed1..seed15]
#   bash watch_native.sh full        # seed1, full mode (default)
#   bash watch_native.sh sector      # seed1, sector mode
#   bash watch_native.sh adaptive seed3
#   bash watch_native.sh sector seed11   # original SUPER-paper dense-forest corridor
#   bash watch_native.sh adaptive seed12 # late-appearing turn obstacle
#   bash watch_native.sh adaptive seed13 # mirrored seed12 companion map
#   bash watch_native.sh adaptive seed14 # controlled-hold recovery diagnostic
#   bash watch_native.sh adaptive seed15 # mirrored recovery diagnostic
set -u
MODE="${1:-full}"
MAP="${2:-seed1}"

set +u
source /opt/ros/humble/setup.bash 2>/dev/null
source /root/super_ws/install/setup.bash 2>/dev/null
set -u
export DISPLAY=:0
export PYTHONUNBUFFERED=1

LOCK_PATH=/tmp/super_sector_filter_native.lock
exec 9>"$LOCK_PATH"
if ! flock -n 9; then
  echo "[watch_native] another native campaign/watch process is already running"
  exit 3
fi

RVIZ_CFG=/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/rviz2/watch_sector.rviz
SECTOR_PY=/root/super-sector-filter/scripts/native_campaign/native_sector.py
SEED12_PY=/root/super-sector-filter/scripts/native_campaign/native_seed12_scenario.py
RECOVERY_PY=/root/super-sector-filter/scripts/native_campaign/native_recovery_scenario.py
RECOVERY_MISSION_PY=/root/super-sector-filter/scripts/native_campaign/native_recovery_mission.py
FOV_PY=/root/super-sector-filter/scripts/native_campaign/native_fov_marker.py

SIM_PID=""
SIM_PGID=""
RVIZ_PID=""
FILTER_PID=""
SCENARIO_PID=""
RECOVERY_MISSION_PID=""
FOV_PID=""

case "$MODE" in
  full|sector|velocity|adaptive|trigger) ;;
  *) echo "[watch_native] mode must be full|sector|velocity|adaptive|trigger"; exit 2 ;;
esac
case "$MAP" in
  seed1|seed2|seed3|seed4|seed5|seed6|seed7|seed8|seed9|seed10|seed11|seed12|seed13|seed14|seed15) ;;
  *) echo "[watch_native] map must be seed1..seed15"; exit 2 ;;
esac

cleanup() {
  echo "[watch_native] cleaning up..."
  if [ -n "$SIM_PGID" ]; then
    kill -9 -- "-$SIM_PGID" 2>/dev/null
  elif [ -n "$SIM_PID" ]; then
    kill -9 "$SIM_PID" 2>/dev/null
  fi
  [ -n "$RVIZ_PID" ] && kill -9 "$RVIZ_PID" 2>/dev/null
  [ -n "$FILTER_PID" ] && kill -9 "$FILTER_PID" 2>/dev/null
  [ -n "$SCENARIO_PID" ] && kill -9 "$SCENARIO_PID" 2>/dev/null
  [ -n "$RECOVERY_MISSION_PID" ] && kill -9 "$RECOVERY_MISSION_PID" 2>/dev/null
  [ -n "$FOV_PID" ] && kill -9 "$FOV_PID" 2>/dev/null
  pkill -9 -f perfect_drone_node 2>/dev/null
  pkill -9 -f fsm_node 2>/dev/null
  pkill -9 -f waypoint_mission 2>/dev/null
  pkill -9 -f native_sector.py 2>/dev/null
  pkill -9 -f native_seed12_scenario.py 2>/dev/null
  pkill -9 -f native_recovery_scenario.py 2>/dev/null
  pkill -9 -f native_recovery_mission.py 2>/dev/null
  pkill -9 -f native_fov_marker.py 2>/dev/null
  pkill -9 -f "rviz2 -d $RVIZ_CFG" 2>/dev/null
}
trap cleanup EXIT INT TERM

pkill -9 -f perfect_drone_node 2>/dev/null
pkill -9 -f fsm_node 2>/dev/null
pkill -9 -f waypoint_mission 2>/dev/null
pkill -9 -f native_sector.py 2>/dev/null
pkill -9 -f native_seed12_scenario.py 2>/dev/null
pkill -9 -f native_recovery_scenario.py 2>/dev/null
pkill -9 -f native_recovery_mission.py 2>/dev/null
pkill -9 -f native_fov_marker.py 2>/dev/null
sleep 1

echo "[watch_native] mode=$MODE map=$MAP"

STATS_JSON="/tmp/watch_${MAP}_${MODE}_filter_stats.json"
rm -f "$STATS_JSON"
FILTER_ARGS=("$MODE" --stats-json "$STATS_JSON")
if [ "$MAP" = "seed12" ] || [ "$MAP" = "seed13" ]; then
  EVENT_JSON="/tmp/watch_${MAP}_filter_event.json"
  SCENARIO_LOG="/tmp/watch_${MAP}_scenario.log"
  rm -f "$EVENT_JSON"
  if [ "$MAP" = "seed13" ]; then
    PREDICTION_S=0.6
    TRIGGER_DISTANCE_MAX=2.0
  else
    PREDICTION_S=0.7
    TRIGGER_DISTANCE_MAX=2.5
  fi
  python3 "$SEED12_PY" \
    --prediction-s "$PREDICTION_S" \
    --nudge-outside-sector \
    --trigger-distance-min 0.6 \
    --trigger-distance-max "$TRIGGER_DISTANCE_MAX" \
    --radius-m 0.25 \
    --rough-trap-count 3 \
    --rough-trap-start-m 0.20 \
    --rough-trap-spacing-m 0.35 \
    --hold-s 0.02 \
    > "$SCENARIO_LOG" 2>&1 &
  SCENARIO_PID=$!
  FILTER_ARGS+=(
    --input-topic /cloud_seed12
    --track-trap
    --event-json "$EVENT_JSON"
  )
  MATCHED_VAR="${MAP^^}_MATCHED_PREFIX"
  if [ "${!MATCHED_VAR:-0}" = "1" ]; then
    FILTER_ARGS+=(--sector-until-trap)
  fi
elif [ "$MAP" = "seed14" ] || [ "$MAP" = "seed15" ]; then
  RECOVERY_SIDE=left
  [ "$MAP" = "seed15" ] && RECOVERY_SIDE=right
  EVENT_JSON="/tmp/watch_${MAP}_recovery_event.json"
  SCENARIO_LOG="/tmp/watch_${MAP}_recovery.log"
  MISSION_EVENT_JSON="/tmp/watch_${MAP}_recovery_mission_event.json"
  MISSION_LOG="/tmp/watch_${MAP}_recovery_mission.log"
  rm -f "$EVENT_JSON" "$MISSION_EVENT_JSON"
  python3 "$RECOVERY_PY" \
    --side "$RECOVERY_SIDE" \
    --trigger-x 18.0 \
    --event-json "$EVENT_JSON" \
    > "$SCENARIO_LOG" 2>&1 &
  SCENARIO_PID=$!
  python3 "$RECOVERY_MISSION_PY" \
    --side "$RECOVERY_SIDE" \
    --event-json "$MISSION_EVENT_JSON" \
    > "$MISSION_LOG" 2>&1 &
  RECOVERY_MISSION_PID=$!
  FILTER_ARGS+=(--input-topic /cloud_recovery)
fi

# Subscribe before either mission driver's 3 s auto-start.
python3 "$SECTOR_PY" "${FILTER_ARGS[@]}" > /tmp/watch_filter.log 2>&1 &
FILTER_PID=$!

python3 "$FOV_PY" "$MODE" --radius 15.0 > /tmp/watch_fov.log 2>&1 &
FOV_PID=$!
sleep 1

if [ "$MAP" = "seed11" ]; then
  # seed11 = the original SUPER-paper dense-forest map (random_map_2_26609.pcd)
  stdbuf -oL -eL ros2 launch mission_planner benchmark_reference.launch.py > /tmp/watch_sim.log 2>&1 &
elif [ "$MAP" = "seed14" ] || [ "$MAP" = "seed15" ]; then
  setsid bash -c '
    set -u
    drone_pid=""
    fsm_pid=""
    cleanup_nodes() {
      [ -n "$drone_pid" ] && kill -9 "$drone_pid" 2>/dev/null
      [ -n "$fsm_pid" ] && kill -9 "$fsm_pid" 2>/dev/null
    }
    trap cleanup_nodes EXIT INT TERM

    stdbuf -oL -eL ros2 run perfect_drone_sim perfect_drone_node \
      --ros-args -p config_name:="$1" &
    drone_pid=$!
    stdbuf -oL -eL ros2 run super_planner fsm_node \
      --ros-args -p config_name:=static_recovery_viz.yaml &
    fsm_pid=$!
    wait -n "$drone_pid" "$fsm_pid"
  ' _ "${MAP}.yaml" > /tmp/watch_sim.log 2>&1 &
else
  stdbuf -oL -eL ros2 launch mission_planner benchmark_seedmap.launch.py \
    waypoint_data:=loop24.txt drone_config:="${MAP}.yaml" \
    super_config:=static_seedmaps_viz.yaml > /tmp/watch_sim.log 2>&1 &
fi
SIM_PID=$!
if [ "$MAP" = "seed14" ] || [ "$MAP" = "seed15" ]; then
  SIM_PGID=$SIM_PID
fi

sleep 4
rviz2 -d "$RVIZ_CFG" > /tmp/watch_rviz.log 2>&1 &
RVIZ_PID=$!

echo "[watch_native] running ($MODE/$MAP) -- Ctrl+C here to stop everything"
echo "[watch_native] logs: /tmp/watch_sim.log /tmp/watch_filter.log"
echo "[watch_native] filter stats: $STATS_JSON"
if [ "$MAP" = "seed12" ] || [ "$MAP" = "seed13" ]; then
  echo "[watch_native] dynamic scenario log: $SCENARIO_LOG"
  echo "[watch_native] dynamic scenario event: $EVENT_JSON"
elif [ "$MAP" = "seed14" ] || [ "$MAP" = "seed15" ]; then
  echo "[watch_native] recovery scenario log: $SCENARIO_LOG"
  echo "[watch_native] recovery scenario event: $EVENT_JSON"
  echo "[watch_native] recovery mission log: $MISSION_LOG"
  echo "[watch_native] recovery mission event: $MISSION_EVENT_JSON"
fi
wait "$SIM_PID"
