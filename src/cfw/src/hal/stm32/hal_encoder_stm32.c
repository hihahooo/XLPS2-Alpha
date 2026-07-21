/* XLPS2-Alpha CFW — STM32 IEncoder (TIMx quadrature, true-zero odometry) */
#include "hal/hal.h"
#include "stm32h7xx_hal.h"   /* CubeMX generated handles */

extern TIM_HandleTypeDef htim_encoder;  /* provided by MX */

static cfw_err_t e_read(void* d, int32_t* cnt)
{
    (void)d;
    *cnt = (int32_t)__HAL_TIM_GET_COUNTER(&htim_encoder);
    return CFW_OK;
}
static cfw_err_t e_reset(void* d)
{
    (void)d;
    __HAL_TIM_SET_COUNTER(&htim_encoder, 0);
    return CFW_OK;
}

static const hal_encoder_ops_t E_OPS = { e_read, e_reset };
static hal_encoder_t E_INST = { NULL, &E_OPS };

const hal_encoder_t* hal_encoder_stm32(void) { return &E_INST; }
