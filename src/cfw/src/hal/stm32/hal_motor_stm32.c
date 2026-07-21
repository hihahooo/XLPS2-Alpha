/* XLPS2-Alpha CFW — STM32 IMotor (delegates to CANopen CiA402 wrapper)
 * The internal servo bus is CANopen; L1 never touches CAN registers directly. */
#include "hal/hal.h"
#include "comm/canopen/co_wrapper.h"

static cfw_err_t m_enable(void* d, uint8_t axis, bool on)        { (void)d; return co_servo_enable(axis, on); }
static cfw_err_t m_vel(void* d, uint8_t axis, int16_t mm_s)      { (void)d; return co_servo_set_velocity(axis, mm_s); }
static cfw_err_t m_pos(void* d, uint8_t axis, int32_t target_mm){ (void)d; return co_servo_set_position(axis, target_mm); }
static cfw_err_t m_fb(void* d, uint8_t axis, float* c, int8_t* t, int32_t* e)
{ (void)d; return co_servo_get_feedback(axis, c, t, e); }
static cfw_err_t m_ready(void* d, uint8_t axis, bool* r)         { (void)d; return co_servo_is_ready(axis, r); }

static const hal_motor_ops_t M_OPS = { m_enable, m_vel, m_pos, m_fb, m_ready };
static hal_motor_t M_INST = { NULL, &M_OPS };

const hal_motor_t* hal_motor_stm32(void) { return &M_INST; }
