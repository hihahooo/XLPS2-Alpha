/* XLPS2-Alpha CFW — L1 HAL abstraction layer (interface umbrella)
 *
 * Hardware is accessed ONLY through these interfaces; no layer above L1 may
 * touch registers. Concrete implementations live under hal/stm32/ and are
 * backed by the ST HAL library. The controller stays board-agnostic (EHW
 * owns the pin map). SSOT: docs/modules/cfw.md §L1. */
#ifndef HAL_HAL_H
#define HAL_HAL_H

#include "hal/hal_motor.h"
#include "hal/hal_laser.h"
#include "hal/hal_encoder.h"
#include "hal/hal_comm.h"
#include "hal/hal_storage.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Physical servo axes (ADR-004) */
#define HAL_AXIS_WALK 1u   /* D_00 行走伺服 */
#define HAL_AXIS_LIFT 2u   /* D_01 顶升伺服 */

/* Acquire the singleton STM32 implementations (defined in hal/stm32/). */
const hal_motor_t*   hal_motor_stm32(void);
const hal_laser_t*   hal_laser_stm32(void);
const hal_encoder_t* hal_encoder_stm32(void);
const hal_comm_t*    hal_comm_stm32(void);
const hal_storage_t* hal_storage_stm32(void);

#ifdef __cplusplus
}
#endif
#endif /* HAL_HAL_H */
