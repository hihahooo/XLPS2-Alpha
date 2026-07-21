/* XLPS2-Alpha CFW — minimal startup for STM32H743 (skeleton)
 *
 * NOTE: In a real bring-up this file is replaced by ST's
 * startup_stm32h743xx.s / system_stm32h7xx.c. Provided here so the CMake
 * image links (Reset_Handler + .isr_vector + data/bss copy). */
#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sdata, _edata, _sidata;
extern uint32_t _sbss, _ebss;

void Reset_Handler(void);
void Default_Handler(void);

#define WEAK_DEFAULT(n) void n(void) __attribute__((weak, alias("Default_Handler")));
WEAK_DEFAULT(NMI_Handler)
WEAK_DEFAULT(HardFault_Handler)
WEAK_DEFAULT(MemManage_Handler)
WEAK_DEFAULT(BusFault_Handler)
WEAK_DEFAULT(UsageFault_Handler)
WEAK_DEFAULT(SVC_Handler)
WEAK_DEFAULT(DebugMon_Handler)
WEAK_DEFAULT(PendSV_Handler)
WEAK_DEFAULT(SysTick_Handler)
WEAK_DEFAULT(FDCAN1_IT0_IRQHandler)
WEAK_DEFAULT(USARTx_IRQHandler)
WEAK_DEFAULT(TIMx_IRQHandler)
WEAK_DEFAULT(IWDG_IRQHandler)

void Default_Handler(void) { for (;;) { __asm volatile ("nop"); } }

void Reset_Handler(void)
{
    /* copy .data from Flash to RAM */
    uint32_t* src = &_sidata;
    for (uint32_t* dst = &_sdata; dst < &_edata; ) *dst++ = *src++;
    /* zero .bss */
    for (uint32_t* dst = &_sbss; dst < &_ebss; ) *dst++ = 0;

    extern void SystemInit(void);
    extern int main(void);
    SystemInit();
    main();
    for (;;) { __asm volatile ("nop"); }
}

__attribute__((section(".isr_vector")))
const void* g_pfnVectors[] = {
    &_estack,
    (void*)Reset_Handler,
    (void*)NMI_Handler,
    (void*)HardFault_Handler,
    (void*)MemManage_Handler,
    (void*)BusFault_Handler,
    (void*)UsageFault_Handler,
    0, 0, 0, 0,
    (void*)SVC_Handler,
    (void*)DebugMon_Handler,
    0,
    (void*)PendSV_Handler,
    (void*)SysTick_Handler,
    (void*)FDCAN1_IT0_IRQHandler,
    (void*)USARTx_IRQHandler,
    (void*)TIMx_IRQHandler,
    (void*)IWDG_IRQHandler,
};
