/* XLPS2-Alpha CFW — L1 IEncoder interface (relative true-zero odometry) */
#ifndef HAL_ENCODER_H
#define HAL_ENCODER_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct hal_encoder_ops {
    cfw_err_t (*read_counts)(void* dev, int32_t* cnt);   /* pulses since reset */
    cfw_err_t (*reset)(void* dev);
} hal_encoder_ops_t;

typedef struct {
    void*                 dev;
    const hal_encoder_ops_t* ops;
} hal_encoder_t;

static inline cfw_err_t hal_encoder_read(const hal_encoder_t* e, int32_t* c)
{ return e->ops->read_counts(e->dev, c); }
static inline cfw_err_t hal_encoder_reset(const hal_encoder_t* e)
{ return e->ops->reset(e->dev); }

#ifdef __cplusplus
}
#endif
#endif /* HAL_ENCODER_H */
