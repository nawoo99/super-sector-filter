#!/bin/bash
# Gazebo 파이프라인 bringup (tmux 기반 - PX4가 TTY 필요)
# 사용: bash g_bringup.sh <world>
WORLD="${1:-default_36}"
SESSION="gsuper"
export DISPLAY=:0

echo "=== cleanup ==="
tmux kill-session -t "$SESSION" 2>/dev/null
for pat in "cloud_preprocessor" "velodyne_3d_lidar" "px4_odometry" "pose_to_aligned" \
           "gz sim" "MicroXRCEAgent" "px4_sitl_default/bin/px4" "make px4_sitl" \
           "static_transform_publisher" "fsm_node" "cmd_bridge.py" "offboard.py"; do
  for pid in $(pgrep -f "$pat" 2>/dev/null); do kill -9 "$pid" 2>/dev/null; done
done
for pid in $(ss -tulnp 2>/dev/null | grep ":8888" | grep -oP 'pid=\K[0-9]+'); do kill -9 "$pid" 2>/dev/null; done
sleep 3

tmux new-session -d -s "$SESSION" -n agent
tmux send-keys -t "$SESSION:agent" "MicroXRCEAgent udp4 -p 8888" Enter
sleep 2

echo "=== PX4 + Gazebo ($WORLD) in tmux — HEADLESS (no GUI client) ==="
# HEADLESS=1: the gz GUI client never starts. Killing the GUI *after* start was
# corrupting the gz_bridge actuator forwarding (PX4 motor outputs never reached
# /model/.../command/motor_speed -> rotors silent -> armed-but-no-lift).
tmux new-window -t "$SESSION" -n uav
# PX4 starts the gz GUI only when HEADLESS is UNSET (`[ -z "$HEADLESS" ]` in
# px4-rc.gzsim, which then runs `gz sim -g` right after the server so the drone
# syncs). So GUI=1 must DROP the var entirely -- HEADLESS=0 would STILL be headless.
# Default keeps HEADLESS=1 (no GUI = the takeoff-stability fix).
GZ_HDL="HEADLESS=1 "; [ "${GUI:-}" = "1" ] && GZ_HDL=""
# The drone is included statically in the world SDF (so the gz GUI shows it), so PX4
# must ATTACH to it (PX4_GZ_MODEL_NAME) instead of spawning a duplicate. For a world
# made with `gen_world.py --no-drone`, set NODRONE=1 to let PX4 spawn instead.
if [ "${NODRONE:-0}" = "1" ]; then GZ_MODEL=""; else GZ_MODEL="PX4_GZ_MODEL_NAME=x500_lidar_3d_0 "; fi
tmux send-keys -t "$SESSION:uav" "cd /root/px4/PX4-Autopilot && ${GZ_HDL}${GZ_MODEL}PX4_GZ_WORLD=$WORLD make px4_sitl gz_x500_lidar_3d" Enter

echo "=== PX4 odometry 흐를 때까지 대기 ==="
source /opt/ros/humble/setup.bash 2>/dev/null
for i in $(seq 1 24); do
  sleep 5
  n=$(timeout 3 ros2 topic echo /fmu/out/vehicle_odometry --once --qos-reliability best_effort 2>/dev/null | grep -c "timestamp")
  if [ "${n:-0}" -ge 1 ]; then
    echo "  [${i}x5s] PX4 odom 흐름 확인"
    break
  fi
done

echo "=== PX4 params: allow OFFBOARD arming + hold altitude on aggressive turns ==="
# Without these, PX4 preflight blocks arming ("No connection to the GCS"):
#   COM_RCL_EXCEPT bit2(=4) exempts OFFBOARD from the RC/GCS-link requirement.
#   NAV_RCL_ACT/NAV_DLL_ACT 0 disable RC/data-link-loss failsafes for sim.
# MPC_TILTMAX_AIR 25: cap the tilt so a sharp corner turn can't pitch the drone hard
#   enough to lose vertical thrust and sink (the residual corner-sink failure mode).
# COM_DISARM_LAND -1: never auto-disarm on ground contact -- if the drone dips and
#   brushes the ground it stays armed and the z-pinned setpoint flies it back up
#   (without this PX4's land detector strands it on the floor).
# MPC_Z_VEL_MAX_UP 4: faster climb-back so an altitude dip is recovered quickly.
for p in "param set COM_RCL_EXCEPT 4" "param set NAV_RCL_ACT 0" "param set NAV_DLL_ACT 0" "param set COM_ARM_WO_GPS 0" "param set MPC_TILTMAX_AIR 25" "param set COM_DISARM_LAND -1" "param set MPC_Z_VEL_MAX_UP 4.0"; do
  tmux send-keys -t "$SESSION:uav" "$p" Enter
  sleep 1
done

echo "=== lidar bridge in tmux ==="
tmux new-window -t "$SESSION" -n lidar
tmux send-keys -t "$SESSION:lidar" "source /opt/ros/humble/setup.bash; source /root/ros_gz_ws/install/setup.bash; source /root/ws_custom_px4_sensor/install/setup.bash; ros2 launch velodyne_3d_lidar_simulation px4_3d_lidar.launch.py world_name:=$WORLD lidar_model_name:=x500_lidar_3d_0 lidar_sensor_name:=lidar_3d_v3 rviz:=false" Enter
sleep 4

echo "=== gz_odom in tmux ==="
tmux new-window -t "$SESSION" -n odom
tmux send-keys -t "$SESSION:odom" "source /opt/ros/humble/setup.bash; ros2 launch px4_odometry_remap px4_odometry_remap_sim.launch.py use_sim_time:=true" Enter
sleep 6

echo "=== 검증: TF world->lidar ==="
timeout 5 ros2 run tf2_ros tf2_echo world x500_lidar_3d_0/link/lidar_3d_v3 2>/dev/null | grep -E "Translation" | head -1 && echo "  TF OK" || echo "  TF 아직"

echo "=== [5] cloud_preprocessor (sector filter + world 변환) ==="
tmux new-window -t "$SESSION" -n cpp
tmux send-keys -t "$SESSION:cpp" "source /opt/ros/humble/setup.bash && source /root/super_ws/install/local_setup.bash && ros2 run gz_super_bridge cloud_preprocessor --ros-args -p input_topic:=/points -p odom_topic:=/odometry -p sector_enable:=${SECTOR:-true} -p risk_gate_enable:=${RISK_GATE:-false} -p risk_range:=${RISK_RANGE:-2.0} -p risk_hold_frames:=${RISK_HOLD:-5}" Enter
sleep 4

echo "=== [6] SUPER fsm_node (ROG-Map + planner) ==="
# SUPER's cmd output (mars_quadrotor_msgs) is remapped to /super/pos_cmd so it
# does NOT collide with offboard.py's /planning/pos_cmd (quadrotor_msgs);
# cmd_bridge converts mars->quadrotor onto /planning/pos_cmd.
tmux new-window -t "$SESSION" -n fsm
tmux send-keys -t "$SESSION:fsm" "source /opt/ros/humble/setup.bash && source /root/super_ws/install/local_setup.bash && ros2 run super_planner fsm_node --ros-args -p config_name:=static_gazebo.yaml -p use_sim_time:=true -r /lidar_slam/odom:=/odometry -r /planning/pos_cmd:=/super/pos_cmd" Enter
sleep 8

echo "=== [7] cmd_bridge (mars PositionCommand -> quadrotor PositionCommand) ==="
tmux new-window -t "$SESSION" -n bridge
tmux send-keys -t "$SESSION:bridge" "source /opt/ros/humble/setup.bash && source /root/super_ws/install/setup.bash && source /root/ego-planner-swarm/install/setup.bash && python3 /root/commands/super_gazebo/cmd_bridge.py" Enter
sleep 2

echo "=== [8] offboard.py (PX4 offboard controller) ==="
tmux new-window -t "$SESSION" -n offb
tmux send-keys -t "$SESSION:offb" "source /opt/ros/humble/setup.bash && source /root/px4_control_ws/install/setup.bash && source /root/ego-planner-swarm/install/setup.bash && python3 /root/px4_control_ws/src/px4_keyboard_control/px4_keyboard_control/offboard.py" Enter
sleep 3

echo "=== bringup 완료 (tmux: $SESSION) ==="
echo "    이륙+goal:  python3 /root/commands/super_gazebo/g_fly.py --goal X Y Z"
