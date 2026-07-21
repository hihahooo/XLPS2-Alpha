# XLPS2-Alpha CFW toolchain file (arm-none-eabi-gcc)
# Usage: cmake -B build -DCMAKE_TOOLCHAIN_FILE=tools/toolchain.cmake
set(CMAKE_SYSTEM_NAME      Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(TOOLCHAIN_PREFIX arm-none-eabi-)
set(CMAKE_C_COMPILER   ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_OBJCOPY      ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_SIZE         ${TOOLCHAIN_PREFIX}size)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# Cortex-M7, no float ABI hard in baseline (FPU double-precision; keep softfp for portability)
set(MCPU cortex-m7)
set(FPU  fpv5-d16)
add_compile_options(
  -mcpu=${MCPU} -mfpu=${FPU} -mfloat-abi=hard
  -mthumb -ffunction-sections -fdata-sections
  -Wall -Wextra -Wno-unused-parameter
  -fno-builtin -ffreestanding
  -O2 -g
)
add_compile_definitions(STM32H743xx ARM_MATH_CM7)

set(CMAKE_EXE_LINKER_FLAGS_INIT
  "-mcpu=${MCPU} -mfpu=${FPU} -mfloat-abi=hard -mthumb -T${CMAKE_CURRENT_LIST_DIR}/../ldscripts/STM32H743IITx_FLASH.ld -specs=nano.specs -specs=nosys.specs -Wl,--gc-sections")
