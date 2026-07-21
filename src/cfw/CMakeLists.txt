# XLPS2-Alpha CFW — CMake build (STM32H7 + FreeRTOS + CANopenNode)
cmake_minimum_required(VERSION 3.22)
project(xlps2_cfw C CXX ASM)

set(CFW_TARGET_ELF ${CMAKE_PROJECT_NAME}.elf)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_EXTENSIONS OFF)

# ---- Optional external dependencies (kept as submodules / vendored) ----
# FreeRTOS and CANopenNode sources are expected under third_party/ when the
# full firmware image is built. They are NOT required for the host-testable
# core library (see tests/ for the host build). This keeps the skeleton
# configurable without the heavy deps present.
option(CFW_BUILD_FULL "Build full firmware image (needs FreeRTOS + CANopenNode)" OFF)

# ---- Common include dirs (HAL-independent core) ----
set(CFW_INC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/include/common
  ${CMAKE_CURRENT_SOURCE_DIR}/include/hal
  ${CMAKE_CURRENT_SOURCE_DIR}/include/svc
  ${CMAKE_CURRENT_SOURCE_DIR}/include/hsm
  ${CMAKE_CURRENT_SOURCE_DIR}/include/app
  ${CMAKE_CURRENT_SOURCE_DIR}/include/comm
)

# ---- Core sources (no HAL / no RTOS deps; host-testable) ----
set(CFW_CORE_SRC
  src/common/cfw_config.c
  src/hsm/hsm_current_state.c
  src/hsm/hsm_engine.c
  src/hsm/hsm_states.c
  src/svc/event_bus.c
  src/svc/ringbuf.c
  src/svc/filter.c
  src/svc/kinematics.c
  src/svc/param.c
  src/svc/diag.c
  src/comm/faults/fault_tolerance.c
)

# HAL-independent core static lib (used by host tests and by the firmware)
add_library(cfw_core STATIC ${CFW_CORE_SRC})
target_include_directories(cfw_core PUBLIC ${CFW_INC})

# ---- STM32-dependent sources (require HAL + RTOS) ----
set(CFW_FW_SRC
  src/hal/stm32/hal_motor_stm32.c
  src/hal/stm32/hal_laser_stm32.c
  src/hal/stm32/hal_encoder_stm32.c
  src/hal/stm32/hal_comm_stm32.c
  src/hal/stm32/hal_storage_stm32.c
  src/comm/canopen/co_wrapper.c
  src/comm/modbus/modbus_rtu.c
  src/comm/modbus/modbus_task_dispatch.c
  src/app/app_states.c
  src/app/task_fsm.c
  src/ota/ota_local.c
  src/sys/system.c
  src/sys/tasks.c
  src/sys/main.c
  src/sys/startup_stm32h743xx.c
)

if(CFW_BUILD_FULL)
  # When third_party is present, pull in FreeRTOS + CANopenNode and link.
  add_executable(${CFW_TARGET_ELF} ${CFW_FW_SRC})
  target_include_directories(${CFW_TARGET_ELF} PUBLIC ${CFW_INC})
  target_link_libraries(${CFW_TARGET_ELF} cfw_core)
  add_custom_command(TARGET ${CFW_TARGET_ELF} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${CFW_TARGET_ELF}> ${CFW_TARGET_ELF}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${CFW_TARGET_ELF}> ${CFW_TARGET_ELF}.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${CFW_TARGET_ELF}>)
  message(STATUS "CFW_BUILD_FULL=ON — link against third_party/FreeRTOS + CANopenNode")
else()
  message(STATUS "CFW_BUILD_FULL=OFF — building cfw_core only (host tests: tests/run_tests.sh)")
endif()
