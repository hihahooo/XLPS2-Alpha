/* XLPS2-Alpha CFW — kinematics basics (L2): trapezoidal motion profile */
#ifndef SVC_KINEMATICS_H
#define SVC_KINEMATICS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int32_t v_max_mm_s;   /* cruise speed */
    int32_t a_mm_s2;      /* acceleration */
} kin_profile_t;

/* Compute the velocity command (mm/s, signed) for the next control tick.
 * pos_mm/target_mm relative to true-zero; cur_v current velocity. */
int16_t kin_step_velocity(int32_t pos_mm, int32_t target_mm,
                          int16_t cur_v, const kin_profile_t* p);

/* Integrate position from encoder delta (cnt -> mm) using pulses-per-mm. */
int32_t kin_integrate(int32_t enc_delta_cnt, int32_t pulses_per_mm);

/* Deceleration distance needed to stop from v at accel a. */
int32_t kin_stop_dist(int16_t v, int32_t a);

#ifdef __cplusplus
}
#endif
#endif /* SVC_KINEMATICS_H */
