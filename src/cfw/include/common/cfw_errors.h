/* XLPS2-Alpha CFW — unified error codes */
#ifndef CFW_ERRORS_H
#define CFW_ERRORS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CFW_OK            =  0,
    CFW_ERR_GENERIC   = -1,
    CFW_ERR_NOMEM     = -2,   /* static pool exhausted (never malloc) */
    CFW_ERR_PARAM     = -3,
    CFW_ERR_TIMEOUT   = -4,
    CFW_ERR_BUSY      = -5,
    CFW_ERR_NOT_FOUND = -6,
    CFW_ERR_CRC       = -7,
    CFW_ERR_RANGE     = -8,
    CFW_ERR_UNINIT    = -9,
    CFW_ERR_HAL       = -10,
    CFW_ERR_PROTOCOL  = -11,
    CFW_ERR_GUARD     = -12   /* HSM guard rejected transition */
} cfw_err_t;

/* Convert to a positive diagnostic code for the `diag_code` telemetry field. */
static inline uint16_t cfw_err_to_diag(cfw_err_t e) {
    return (uint16_t)(-(int)e);
}

#ifdef __cplusplus
}
#endif
#endif /* CFW_ERRORS_H */
