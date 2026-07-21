/* XLPS2-Alpha CFW — system bring-up (HAL, clocks, IWDG, CANopen, app) */
#include "sys/system.h"
#include "hal/hal.h"
#include "comm/canopen/co_wrapper.h"
#include "stm32h7xx_hal.h"

/* CubeMX-generated peripherals (strong defs override these weak stubs). */
__attribute__((weak)) void SystemClock_Config(void) { }
__attribute__((weak)) void MX_GPIO_Init(void) { }
__attribute__((weak)) void MX_FDCAN1_Init(void) { }
__attribute__((weak)) void MX_USART_RS485_Init(void) { }
__attribute__((weak)) void MX_TIM_Encoder_Init(void) { }
__attribute__((weak)) void MX_IWDG_Init(void) { }

static IWDG_HandleTypeDef hiwdg;

void iwdg_refresh(void) { HAL_IWDG_Refresh(&hiwdg); }

void hw_init(void)
{
    HAL_Init();
    SystemClock_Config();          /* 480 MHz M7 */
    MX_GPIO_Init();
    MX_FDCAN1_Init();              /* internal CANopen servo bus */
    MX_USART_RS485_Init();         /* local Modbus RTU */
    MX_TIM_Encoder_Init();         /* true-zero odometry */
    MX_IWDG_Init();                /* safety watchdog */
    co_init();                     /* CANopenNode stack */
}

ota_local_t g_ota;

/* Called from main() before the scheduler starts. */
void cfw_board_early_init(void)
{
    hw_init();
    app_init(&g_rt);
    ota_local_init(&g_ota, hal_storage_stm32());
    /* signal boot complete -> HSM BOOTING->IDLE */
    evt_publish(&g_rt.evt, EV_BOOT_DONE, NULL, 0);
}
