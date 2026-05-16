cmake_minimum_required(VERSION 3.8)
project(nisankiran_core)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

#  C++23 AYARLARI ---
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 23)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

#--- Derleyici Uyarıları ---
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
# --- BİTİŞ ---



# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(px4_msgs REQUIRED)

#targeter nodu için------------
find_package(OpenCV REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
#----------------------------

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

include_directories(include)


#burları lanunch dosyasından çıkardım silinebilir asıl dosyalar da durablri
# add_executable(nisankiran_offboard_node 
#   src/offboard_controller.cpp
# )



#targetter--------------------
#targeter nodunda opencv uyuşmazlığı var 
#vision noduna taşıdım görüntü işlemeyi
# add_executable(targeter src/targeter.cpp)
# ament_target_dependencies(targeter rclcpp sensor_msgs cv_bridge image_transport)
# target_link_libraries(targeter ${OpenCV_LIBS})
# #------------------------------



add_executable(offboard_fighter src/offboard_fighter.cpp)
ament_target_dependencies(offboard_fighter rclcpp px4_msgs geometry_msgs)


#offboard  görevleri fighter içine alındı
# ament_target_dependencies(nisankiran_offboard_node 
#   rclcpp 
#   geometry_msgs 
#   px4_msgs
# )



# yeni gelen node lar buaraya yazılacak ve burdan yayınlanacak

install(TARGETS
  #nisankiran_offboard_node
  offboard_fighter
  #targeter
  DESTINATION lib/${PROJECT_NAME}
)



ament_package()