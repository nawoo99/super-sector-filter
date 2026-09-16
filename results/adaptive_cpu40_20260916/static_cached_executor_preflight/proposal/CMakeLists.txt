cmake_minimum_required(VERSION 3.16)
project(static_cached_executor_preflight LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(static_pc_cached_executor_test
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/static_pc_cached_executor_test.cpp)
target_include_directories(static_pc_cached_executor_test PRIVATE
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include
  /root/super_ws/src/SUPER/rog_map/include)
ament_target_dependencies(static_pc_cached_executor_test rclcpp std_msgs)
target_compile_options(static_pc_cached_executor_test PRIVATE -Wall -Wextra -Wpedantic)
