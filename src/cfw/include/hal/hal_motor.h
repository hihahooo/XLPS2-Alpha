/* XLPS2-Alpha CFW — L1 IMotor interface (CANopen CiA402 servos D_00/D_01) */
#ifndef HAL_MOTOR_H
#define HAL_MOTOR_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct hal_motor_ops {
    cfw_err_t (*enable)(void* dev, uint8_t axis, bool on);
    cfw_err_t (*set_velocity)(void* dev, uint8_t axis, int16_t mm_s);
    cfw_err_t (*set_position)(void* dev, uint8_t axis, int32_t target_mm);
    cfw_err_t (*get_feedback)(void* dev, uint8_t axis,
                              float* current_a, int8_t* temp_c, int32_t* enc_cnt);
    cfw_err_t (*is_ready)(void* dev, uint8_t axis, bool* ready);
} hal_motor_ops_t;

typedef struct {
    void*              dev;
    const hal_motor_ops_t* ops;
} hal_motor_t;

static inline cfw_err_t hal_motor_enable(const hal_motor_t* m, uint8_t axis, bool on)
{ return m->ops->enable(m->dev, axis, on); }
static inline cfw_err_t hal_motor_set_velocity(const hal_motor_t* m, uint8_t axis, int16_t v)
{ return m->ops->set_velocity(m->dev, axis, v); }
static inline cfw_err_t hal_motor_get_feedback(const hal_motor_t* m, uint8_t axis,
                                               float* c, int8_t* t, int32_t* e)
{ return m->ops->get_feedback(m->dev, axis, c, t, e); }

#ifdef __cplusplus
}
#endif
#endif /* HAL_MOTOR_H */
