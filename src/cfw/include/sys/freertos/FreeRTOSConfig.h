/* XLPS2-Alpha CFW — FreeRTOS configuration (Cortex-M7, STM32H743) */
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#include "stm32h7xx_hal.h"   /* provides SystemCoreClock */

#define configUSE_PREEMPTION            1
#define configUSE_IDLE_HOOK             0
#define configUSE_TICK_HOOK             0
#define configCPU_CLOCK_HZ              (SystemCoreClock)
#define configTICK_RATE_HZ              (1000)
#define configMAX_PRIORITIES            (8)
#define configMINIMAL_STACK_SIZE        (256)
#define configTOTAL_HEAP_SIZE           (48 * 1024)
#define configMAX_TASK_NAME_LEN         (16)
#define configUSE_16_BIT_TICKS          0
#define configUSE_MUTEXES               1
#define configUSE_RECURSIVE_MUTEXES     1
#define configUSE_COUNTING_SEMAPHORES   1
#define configUSE_QUEUE_SETS            1
#define configUSE_TIME_SLICING          1
#define configUSE_NEWLIB_REENTRANT      0

/* Cortex-M7 (no MPU used) */
#define configPRIO_BITS                 4
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY   15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5
#define configKERNEL_INTERRUPT_PRIORITY         (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY    (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

#define INCLUDE_vTaskPrioritySet        1
#define INCLUDE_uxTaskPriorityGet       1
#define INCLUDE_vTaskDelete             1
#define INCLUDE_vTaskDelay              1
#define INCLUDE_xTaskGetIdleTaskHandle  1
#define INCLUDE_xTimerPendFunctionCall  1

#endif /* FREERTOS_CONFIG_H */
