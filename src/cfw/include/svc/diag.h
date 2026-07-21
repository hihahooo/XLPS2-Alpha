/* XLPS2-Alpha CFW — diagnostic log (L2): feeds `diag_code` / diag/log topic */
#ifndef SVC_DIAG_H
#define SVC_DIAG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DIAG_LOG_DEPTH 16u

typedef struct {
    uint16_t codes[DIAG_LOG_DEPTH];
    uint32_t ts[DIAG_LOG_DEPTH];
    uint8_t  wr;
    uint8_t  count;
} diag_log_t;

void    diag_init(diag_log_t* d);
void    diag_push(diag_log_t* d, uint16_t code, uint32_t ts);
uint16_t diag_last(const diag_log_t* d);
uint8_t  diag_count(const diag_log_t* d);

#ifdef __cplusplus
}
#endif
#endif /* SVC_DIAG_H */
