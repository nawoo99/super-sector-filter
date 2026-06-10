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
           "static_transform_publisher" "fsm_node"; do
  for pid in $(pgrep -f "$pat" 2>/dev/null); do kill -9 "$pid" 2>/dev/null; done
done
for pid in $(ss -tulnp 2>/dev/null | grep ":8888" | grep -oP 'pid=\K[0-9]+'); do kill -9 "$pid" 2>/dev/null; done
sleep 3

tmux new-session -d -s "$SESSION" -n agent
tmux send-keys -t "$SESSION:agent" "MicroXRCEAgent udp4 -p 8888" Enter
sleep 2

echo "=== PX4 + Gazebo ($WORLD) in tmux ==="
tmux new-window -t "$SESSION" -n uav
tmux send-keys -t "$SESSION:uav" "cd /root/px4/PX4-Autopilot && PX4_GZ_WORLD=$WORLD make px4_sitl gz_x500_lidar_3d" Enter

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
tmux send-keys -t "$SESSION:cpp" "source /opt/ros/humble/setup.bash && source /root/super_ws/install/local_setup.bash && ros2 run gz_super_bridge cloud_preprocessor --ros-args -p input_topic:=/points -p odom_topic:=/odometry -p sector_enable:=${SECTOR:-true}" Enter
sleep 4

echo "=== [6] SUPER fsm_node (ROG-Map + planner) ==="
tmux new-window -t "$SESSION" -n fsm
tmux send-keys -t "$SESSION:fsm" "source /opt/ros/humble/setup.bash && source /root/super_ws/install/local_setup.bash && ros2 run super_planner fsm_node --ros-args -p config_name:=static_gazebo.yaml -p use_sim_time:=true -r /lidar_slam/odom:=/odometry" Enter
sleep 10

echo "=== bringup 완료 (tmux: $SESSION) ==="
