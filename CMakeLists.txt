cmake_minimum_required(VERSION 3.10)
project(robot_tts)
set(CMAKE_CXX_STANDARD 14)

# Try common Unitree SDK2 install locations on the robot.
if(NOT DEFINED UNITREE_SDK2_PATH)
    if(EXISTS "$ENV{HOME}/unitree_sdk2_latest")
        set(UNITREE_SDK2_PATH "$ENV{HOME}/unitree_sdk2_latest")
    elseif(EXISTS "$ENV{HOME}/unitree_sdk2")
        set(UNITREE_SDK2_PATH "$ENV{HOME}/unitree_sdk2")
    endif()
endif()

if(NOT UNITREE_SDK2_PATH)
    message(FATAL_ERROR "UNITREE_SDK2_PATH not set and no SDK found in ~/unitree_sdk2_latest or ~/unitree_sdk2")
endif()

message(STATUS "Using Unitree SDK2 path: ${UNITREE_SDK2_PATH}")

include_directories(${UNITREE_SDK2_PATH}/include)
link_directories(${UNITREE_SDK2_PATH}/lib)
link_directories(${UNITREE_SDK2_PATH}/build/lib)

add_executable(robot-tts robot-tts.cc)

# Link unitree_sdk2 if present, otherwise try common variants.
if(EXISTS "${UNITREE_SDK2_PATH}/lib/libunitree_sdk2.so" OR EXISTS "${UNITREE_SDK2_PATH}/build/lib/libunitree_sdk2.so")
    target_link_libraries(robot-tts unitree_sdk2 pthread)
else()
    target_link_libraries(robot-tts unitree_sdk2py pthread)
endif()
