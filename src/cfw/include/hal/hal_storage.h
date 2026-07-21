/* XLPS2-Alpha CFW — L1 IStorage interface (internal Flash + external FRAM)
 *
 * Holds param layer (Flash), interference library (FRAM/FM24CLxx I2C),
 * SMDL, and the A/B firmware partitions (STM32H743 internal Flash A/B per ADR-005).
 * All access is synchronous and bounded (no malloc). */
#ifndef HAL_STORAGE_H
#define HAL_STORAGE_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    STORE_PARAM   = 0,   /* internal Flash param sector */
    STORE_SHDL    = 1,   /* SMDL (internal Flash) */
    STORE_INTERF  = 2,   /* interference library (FRAM) */
    STORE_OTA_A   = 3,   /* A partition (ADR-005) */
    STORE_OTA_B   = 4,   /* B partition (ADR-005) */
    STORE_OTA_FLAG= 5    /* FLAG sector (ADR-005) */
} hal_store_part_t;

typedef struct hal_storage_ops {
    cfw_err_t (*read)(void* dev, hal_store_part_t part, uint32_t offset,
                      uint8_t* buf, uint32_t len);
    cfw_err_t (*write)(void* dev, hal_store_part_t part, uint32_t offset,
                       const uint8_t* buf, uint32_t len);
    cfw_err_t (*erase_sector)(void* dev, hal_store_part_t part, uint32_t offset);
    cfw_err_t (*crc32)(void* dev, hal_store_part_t part, uint32_t offset,
                       uint32_t len, uint32_t* out);
} hal_storage_ops_t;

typedef struct {
    void*                 dev;
    const hal_storage_ops_t* ops;
} hal_storage_t;

#ifdef __cplusplus
}
#endif
#endif /* HAL_STORAGE_H */
