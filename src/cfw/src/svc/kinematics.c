/* XLPS2-Alpha CFW — kinematics implementation (L2) */
#include "svc/kinematics.h"

int32_t kin_stop_dist(int16_t v, int32_t a)
{
    if (a <= 0) return 0x7FFFFFFF;
    int32_t sv = (v >= 0) ? (int32_t)v : -(int32_t)v;
    return (sv * sv) / (2 * a);
}

int32_t kin_integrate(int32_t enc_delta_cnt, int32_t pulses_per_mm)
{
    if (pulses_per_mm == 0) return 0;
    return enc_delta_cnt / pulses_per_mm;
}

int16_t kin_step_velocity(int32_t pos_mm, int32_t target_mm,
                          int16_t cur_v, const kin_profile_t* p)
{
    int32_t d   = target_mm - pos_mm;
    int32_t dir = (d >= 0) ? 1 : -1;
    int32_t ad  = (d >= 0) ? d : -d;                 /* |distance| */
    int32_t sv  = (cur_v >= 0) ? (int32_t)cur_v : -(int32_t)cur_v; /* |v| */
    int32_t stop = kin_stop_dist((int16_t)sv, p->a_mm_s2);
    int16_t vmax = (int16_t)p->v_max_mm_s;
    int32_t nvel;

    if (ad <= stop) {
        nvel = sv - p->a_mm_s2;                      /* decelerate */
        if (nvel < 0) nvel = 0;
    } else {
        nvel = sv + p->a_mm_s2;                      /* accelerate */
        if (nvel > vmax) nvel = vmax;
    }
    return (int16_t)(dir * nvel);
}
