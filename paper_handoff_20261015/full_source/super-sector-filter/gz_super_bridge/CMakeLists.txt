cmake_minimum_required(VERSION 3.8)
project(gz_super_bridge)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -O2)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(nav_msgs REQUIRED)

find_package(PCL REQUIRED COMPONENTS common filters)
find_package(Eigen3 REQUIRED)

add_executable(cloud_preprocessor src/cloud_preprocessor.cpp)
target_include_directories(cloud_preprocessor PUBLIC ${PCL_INCLUDE_DIRS} ${EIGEN3_INCLUDE_DIRS})
target_link_libraries(cloud_preprocessor ${PCL_LIBRARIES})
ament_target_dependencies(cloud_preprocessor
  rclcpp sensor_msgs std_msgs nav_msgs pcl_conversions)

install(TARGETS cloud_preprocessor
  DESTINATION lib/${PROJECT_NAME})

ament_package()
