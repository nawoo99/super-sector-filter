#!/bin/bash
# watch.sh — eyeball ONE seed run: HEADLESS sim + RViz + one perimeter loop.
# -------------------------------------------------------------------------
# The sim stays HEADLESS (Gazebo GUI off — that's the takeoff-stability fix);
# you watch in RViz instead, which actually shows MORE than the Gazebo GUI:
# the sector-filtered cloud (/cloud_registered = a +/-60 wedge, or a full ring
# at corners in adaptive mode), the ROG-Map occupancy the planner avoids, and
# SUPER's committed trajectory + A* path + goal.
#
#   bash watch.sh <seed> <mode>     mode = full | sector | adaptive   (default adaptive)
#   bash watch.sh 11 sector
#
# After the loop the stack stays up so you can keep looking / send more goals.
# Teardown:  tmux kill-server; pkill -9 -f 'gz sim'; pkill -9 -f fsm_node
# -------------------------------------------------------------------------
set -u
SEED="${1:-11}"
MODE="${2:-adaptive}"
GUIMODE="${3:-}"      # "gui" -> start Gazebo GUI WITH the server (drone visible)
WORLD="default_seed${SEED}"
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
RVIZ_CFG="$HERE/super_watch.rviz"
SDF="/root/px4/PX4-Autopilot/Tools/simulation/gz/worlds/${WORLD}.sdf"

[ -f "$SDF" ] || { echo "[watch] '$SDF' 없음 — 시드 1-12 중에서 고르세요"; exit 1; }

case "$MODE" in
  full)     SEC=false; MFLAGS="--no-adaptive --sector-base off";;
  sector)   SEC=true;  MFLAGS="--no-adaptive --sector-base on";;
  adaptive) SEC=true;  MFLAGS="--sector-base on";;
  *) echo "[watch] mode = full | sector | adaptive"; exit 1;;
esac

# HEADLESS by default (Gazebo GUI off = takeoff-stability fix). 3rd arg "gui" starts
# the Gazebo GUI WITH the server so the (runtime-spawned) drone is visible -- a late
# `gz sim -g` attach can't show it. GUI adds render load (ekf2 may lag); don't close
# the GUI alone mid-flight (corrupts the actuator bridge) -- end with super_exit.
GZGUI=0; [ "$GUIMODE" = "gui" ] && { GZGUI=1; echo "=== [watch] GUI mode: PX4 starts the Gazebo GUI (drone visible) ==="; }
echo "=== [watch] bringup $WORLD (gui=$GZGUI), sector=$SEC, mode=$MODE ==="
SECTOR="$SEC" GUI="$GZGUI" bash "$HERE/g_bringup.sh" "$WORLD"

# NOTE: ROS setup.bash references unset vars -> would abort under `set -u`; guard it.
set +u; source /opt/ros/humble/setup.bash 2>/dev/null; set -u
echo "=== [watch] /cloud_registered 흐를 때까지 대기 ==="
for i in $(seq 1 30); do
  if [ -n "$(timeout 4 ros2 topic echo /cloud_registered --once 2>/dev/null | head -1)" ]; then
    echo "  [${i}] cloud 흐름 확인"; break
  fi
  sleep 3
done

echo "=== [watch] RViz 실행 (config: $RVIZ_CFG) ==="
export DISPLAY="${DISPLAY:-:0}"
nohup rviz2 -d "$RVIZ_CFG" >/tmp/watch_rviz.log 2>&1 &
sleep 3

echo "=== [watch] 한 바퀴 비행 (mode=$MODE) — RViz로 확인하세요 ==="
# no --metrics-out: g_mission flies the loop then holds at home (does not auto-exit),
# so the stack stays up for you to keep watching.
python3 "$HERE/g_mission.py" $MFLAGS --mode "$MODE"

echo "=== [watch] 끝. 스택은 유지됩니다. 종료: tmux kill-server; pkill -9 -f 'gz sim' ==="
