/* XLPS2-Alpha CFW — CANopenNode CiA402 wrapper (internal servo bus)
 *
 * Drives the step-k (步科 FD135) servos: D_00 = 行走 (node 1), D_01 = 顶升 (node 2).
 * Velocity in mm/s; the wrapper converts to the servo's internal units and
 * maps CiA402 PDOs (controlword 0x6040, target velocity 0x6042, statusword
 * 0x6041, actual current 0x6078, ...). Real CANopenNode calls are enabled when
 * CFW_HAS_CANOPEN is defined (CANopenNode vendored under third_party/). */
#ifndef COMM_CO_WRAPPER_H
#define COMM_CO_WRAPPER_H

#include <stdint.h>
#include "common/cfw_errors.h"
#include "common/cfw_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* node ids: D_00 walk = 1, D_01 lift = 2 (matches TASK_AXIS_* convention) */
#define CO_NODE_WALK 1u
#define CO_NODE_LIFT 2u

cfw_err_t co_init(void);
cfw_err_t co_servo_enable(uint8_t axis, bool on);
cfw_err_t co_servo_set_velocity(uint8_t axis, int16_t mm_s);
cfw_err_t co_servo_set_position(uint8_t axis, int32_t target_mm);
cfw_err_t co_servo_get_feedback(uint8_t axis, float* current_a, int8_t* temp_c, int32_t* enc_cnt);
cfw_err_t co_servo_is_ready(uint8_t axis, bool* ready);

#ifdef __cplusplus
}
#endif
#endif /* COMM_CO_WRAPPER_H */
