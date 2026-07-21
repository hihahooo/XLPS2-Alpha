/* XLPS2-Alpha CFW — system init / task creation declarations */
#ifndef SYS_SYSTEM_H
#define SYS_SYSTEM_H

#include "cfw.h"
#include "ota/ota_local.h"

#ifdef __cplusplus
extern "C" {
#endif

extern ota_local_t g_ota;

void hw_init(void);          /* HAL + clocks + peripherals + IWDG + CANopen */
void cfw_board_early_init(void); /* hw_init + app/ota init + EV_BOOT_DONE */
void create_tasks(void);     /* FreeRTOS task creation */
void iwdg_refresh(void);     /* pet the watchdog */

#ifdef __cplusplus
}
#endif
#endif /* SYS_SYSTEM_H */
