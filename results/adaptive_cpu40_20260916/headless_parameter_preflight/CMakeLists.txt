cmake_minimum_required(VERSION 3.16)
project(headless_parameter_policy_preflight LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(headless_parameter_policy_test
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/headless_parameter_policy_test.cpp)
target_include_directories(headless_parameter_policy_test PRIVATE
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include)
ament_target_dependencies(headless_parameter_policy_test rclcpp)
target_compile_options(headless_parameter_policy_test PRIVATE -Wall -Wextra -Wpedantic)
