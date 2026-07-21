/* XLPS2-Alpha CFW — diagnostic log implementation (L2) */
#include "svc/diag.h"

void diag_init(diag_log_t* d)
{
    d->wr = 0; d->count = 0;
    for (uint8_t i = 0; i < DIAG_LOG_DEPTH; i++) { d->codes[i] = 0; d->ts[i] = 0; }
}

void diag_push(diag_log_t* d, uint16_t code, uint32_t ts)
{
    d->codes[d->wr] = code;
    d->ts[d->wr]   = ts;
    d->wr = (uint8_t)((d->wr + 1u) % DIAG_LOG_DEPTH);
    if (d->count < DIAG_LOG_DEPTH) d->count++;
}

uint16_t diag_last(const diag_log_t* d)
{
    if (d->count == 0) return 0;
    uint8_t idx = (d->wr == 0) ? (DIAG_LOG_DEPTH - 1u) : (uint8_t)(d->wr - 1u);
    return d->codes[idx];
}

uint8_t diag_count(const diag_log_t* d) { return d->count; }
