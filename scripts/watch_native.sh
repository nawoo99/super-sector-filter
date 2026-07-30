#!/bin/bash
# One-command visual watch: sim + RViz + filter, all together.
# Usage: bash watch_native.sh [full|sector|adaptive] [seed1..seed10|seed11]
#   bash watch_native.sh full        # seed1, full mode (default)
#   bash watch_native.sh sector      # seed1, sector mode
#   bash watch_native.sh adaptive seed3
#   bash watch_native.sh sector seed11   # original SUPER-paper dense-forest corridor
set -u
MODE="${1:-full}"
MAP="${2:-seed1}"

set +u
source /opt/ros/humble/setup.bash 2>/dev/null
source /root/super_ws/install/setup.bash 2>/dev/null
set -u
export DISPLAY=:0
export PYTHONUNBUFFERED=1

RVIZ_CFG=/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/rviz2/watch_sector.rviz
SECTOR_PY=/root/super-sector-filter/scripts/native_campaign/native_sector.py

SIM_PID=""
RVIZ_PID=""

cleanup() {
  echo "[watch_native] cleaning up..."
  [ -n "$SIM_PID" ] && kill -9 "$SIM_PID" 2>/dev/null
  [ -n "$RVIZ_PID" ] && kill -9 "$RVIZ_PID" 2>/dev/null
  pkill -9 -f perfect_drone_node 2>/dev/null
  pkill -9 -f fsm_node 2>/dev/null
  pkill -9 -f waypoint_mission 2>/dev/null
  pkill -9 -f native_sector.py 2>/dev/null
  pkill -9 -f "rviz2 -d $RVIZ_CFG" 2>/dev/null
}
trap cleanup EXIT INT TERM

pkill -9 -f perfect_drone_node 2>/dev/null
pkill -9 -f fsm_node 2>/dev/null
pkill -9 -f waypoint_mission 2>/dev/null
pkill -9 -f native_sector.py 2>/dev/null
sleep 1

echo "[watch_native] mode=$MODE map=$MAP"

if [ "$MAP" = "seed11" ]; then
  # seed11 = the original SUPER-paper dense-forest map (random_map_2_26609.pcd)
  stdbuf -oL -eL ros2 launch mission_planner benchmark_reference.launch.py > /tmp/watch_sim.log 2>&1 &
else
  stdbuf -oL -eL ros2 launch mission_planner benchmark_seedmap.launch.py \
    waypoint_data:=loop24.txt drone_config:="${MAP}.yaml" \
    super_config:=static_seedmaps_viz.yaml > /tmp/watch_sim.log 2>&1 &
fi
SIM_PID=$!

sleep 4
rviz2 -d "$RVIZ_CFG" > /tmp/watch_rviz.log 2>&1 &
RVIZ_PID=$!

sleep 1
echo "[watch_native] filter starting ($MODE) -- Ctrl+C here to stop everything"
python3 "$SECTOR_PY" "$MODE"
