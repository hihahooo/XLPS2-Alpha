/* XLPS2-Alpha CFW — L1 ILaser interface (RS485 laser rangefinder) */
#ifndef HAL_LASER_H
#define HAL_LASER_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LASER_DEV_OK = 0,
    LASER_DEV_TRIGGERED = 1,
    LASER_DEV_ERROR = 2
} hal_laser_status_t;

typedef struct hal_laser_ops {
    cfw_err_t (*read_distance)(void* dev, int32_t* distance_mm); /* <0 if invalid */
    cfw_err_t (*read_status)(void* dev, hal_laser_status_t* st);
} hal_laser_ops_t;

typedef struct {
    void*               dev;
    const hal_laser_ops_t* ops;
} hal_laser_t;

static inline cfw_err_t hal_laser_read_distance(const hal_laser_t* l, int32_t* d)
{ return l->ops->read_distance(l->dev, d); }
static inline cfw_err_t hal_laser_read_status(const hal_laser_t* l, hal_laser_status_t* s)
{ return l->ops->read_status(l->dev, s); }

#ifdef __cplusplus
}
#endif
#endif /* HAL_LASER_H */
