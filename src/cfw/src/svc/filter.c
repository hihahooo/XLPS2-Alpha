/* XLPS2-Alpha CFW — interference filter implementation (L2) */
#include "svc/filter.h"

void filt_init(filt_ctx_t* f)
{
    f->ambient_avg = 5000;   /* 50.00% scaled x100 */
    f->ambient_var = 0;
    f->learn_count = 0;
    f->learned     = false;
}

void filt_learn_ambient(filt_ctx_t* f, uint8_t ambient_pct)
{
    int32_t a = (int32_t)ambient_pct * 100;
    if (!f->learned) {
        f->ambient_avg = a;
    } else {
        f->ambient_avg = f->ambient_avg + (a - f->ambient_avg) / 8;
    }
    f->learn_count++;
    if (f->learn_count >= FILT_AMBIENT_LEARN_GOAL) f->learned = true;
}

filt_verdict_t filt_classify(filt_ctx_t* f,
                             bool pe_blocked,
                             bool laser_triggered,
                             int32_t laser_dist_mm)
{
    (void)laser_dist_mm;
    if (pe_blocked && laser_triggered)     return FILT_OBSTACLE;     /* both agree */
    if (!pe_blocked && !laser_triggered)   return FILT_CLEAR;       /* both agree */
    /* single route anomalous => interference, continue (ADR-006 CROSS_VERIFY) */
    return FILT_INTERFERENCE;
}
