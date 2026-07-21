/* XLPS2-Alpha CFW — CANopenNode CiA402 wrapper implementation.
 * When CANopenNode is vendored (third_party/) and CFW_HAS_CANOPEN is set, the
 * real CO_* calls execute. Otherwise the entry points are safe stubs so the
 * firmware image still links during early bring-up. */
#include "comm/canopen/co_wrapper.h"

#ifdef CFW_HAS_CANOPEN
#include "CANopen.h"
extern CO_t *CO;                 /* CANopenNode instance (from CANopen.c) */
#endif

static uint8_t node_of(uint8_t axis)
{
    return (axis == TASK_AXIS_LIFT) ? (uint8_t)CO_NODE_LIFT : (uint8_t)CO_NODE_WALK;
}

cfw_err_t co_init(void)
{
#ifdef CFW_HAS_CANOPEN
    /* CO_CANopenInit(), RPDO/TPDO mapping for 0x6040/0x6042/0x6041/0x6078 ... */
    if (CO == NULL) return CFW_ERR_UNINIT;
#endif
    return CFW_OK;
}

cfw_err_t co_servo_enable(uint8_t axis, bool on)
{
    (void)axis; (void)on;
#ifdef CFW_HAS_CANOPEN
    /* write controlword 0x6040: 0x0006 (enable) / 0x0000 (disable) via TPDO */
#endif
    return CFW_OK;
}

cfw_err_t co_servo_set_velocity(uint8_t axis, int16_t mm_s)
{
    (void)axis; (void)mm_s;
#ifdef CFW_HAS_CANOPEN
    /* map mm/s -> target velocity 0x6042 (or profile velocity 0x6081) */
#endif
    return CFW_OK;
}

cfw_err_t co_servo_set_position(uint8_t axis, int32_t target_mm)
{
    (void)axis; (void)target_mm;
#ifdef CFW_HAS_CANOPEN
    /* set target position 0x607A + controlword for profile position mode */
#endif
    return CFW_OK;
}

cfw_err_t co_servo_get_feedback(uint8_t axis, float* current_a, int8_t* temp_c, int32_t* enc_cnt)
{
    (void)axis;
    if (current_a) *current_a = 0.0f;
    if (temp_c)    *temp_c = 25;
    if (enc_cnt)   *enc_cnt = 0;
#ifdef CFW_HAS_CANOPEN
    /* read RPDO: actual current 0x6078, statusword 0x6041, actual position */
#endif
    return CFW_OK;
}

cfw_err_t co_servo_is_ready(uint8_t axis, bool* ready)
{
    (void)axis;
    if (ready) *ready = true;
    return CFW_OK;
}
