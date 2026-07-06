#!/bin/bash
# ui_run.sh <seed> <mode> <fixed_yaw> <gui>
# One verification run driven by sector_ui.py: teardown -> bringup (seed) -> live
# collision monitor + RViz -> fly ONE perimeter loop. Everything logged to /tmp/sector_ui.
# g_mission holds at home after the loop (no auto-exit) so you can keep watching until Stop.
set -u
SEED="${1:-7}"; MODE="${2:-sector}"; FY="${3:-999.0}"; GUI="${4:-0}"
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
UIDIR="/tmp/sector_ui"; mkdir -p "$UIDIR"
WORLD="default_seed${SEED}"
COLL="$UIDIR/coll.log"; SUM="$UIDIR/coll_summary.txt"
: > "$COLL"; : > "$SUM"

case "$MODE" in
  full)     SEC=false; MFLAGS="--no-adaptive --sector-base off --risk-gate off --align-velocity off";;
  sector)   SEC=true;  MFLAGS="--no-adaptive --sector-base on  --risk-gate off --align-velocity off";;
  adaptive) SEC=true;  MFLAGS="--no-adaptive --sector-base on  --risk-gate off --align-velocity on";;
  *) echo "[ui_run] bad mode '$MODE'"; exit 1;;
esac

echo "=== [ui_run] PHASE=teardown ==="
bash /tmp/td.sh >/dev/null 2>&1 || true
echo "=== [ui_run] PHASE=bringup  seed=$SEED mode=$MODE fixed_yaw=$FY gui=$GUI ==="
SECTOR="$SEC" GUI="$GUI" FIXED_YAW="$FY" bash "$HERE/g_bringup.sh" "$WORLD"

set +u; source /opt/ros/humble/setup.bash 2>/dev/null; set -u
echo "=== [ui_run] PHASE=wait-cloud ==="
for i in $(seq 1 30); do
  if [ -n "$(timeout 4 ros2 topic echo /cloud_registered --once 2>/dev/null | head -1)" ]; then
    echo "  cloud flowing"; break
  fi
  sleep 3
done

echo "=== [ui_run] PHASE=monitor+rviz ==="
nohup python3 "$HERE/collision_monitor.py" --world "$WORLD" --out "$SUM" > "$COLL" 2>&1 &
export DISPLAY="${DISPLAY:-:0}"
nohup rviz2 -d "$HERE/super_watch.rviz" > "$UIDIR/rviz.log" 2>&1 &
sleep 2

echo "=== [ui_run] PHASE=flying (one loop, then holds at home) ==="
python3 "$HERE/g_mission.py" $MFLAGS --mode "$MODE"
echo "=== [ui_run] PHASE=done ==="
