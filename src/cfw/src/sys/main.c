/* XLPS2-Alpha CFW — firmware entry point */
#include "sys/system.h"
#include "cfw.h"
#include "FreeRTOS.h"
#include "task.h"

int main(void)
{
    cfw_board_early_init();   /* HAL + app + OTA + EV_BOOT_DONE */
    create_tasks();           /* FreeRTOS tasks */
    vTaskStartScheduler();    /* never returns on success */
    for (;;) {                /* scheduler failed */
        __asm volatile ("nop");
    }
}
