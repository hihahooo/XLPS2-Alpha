/* XLPS2-Alpha CFW — fault tolerance implementation (ADR-006) */
#include "comm/faults/fault_tolerance.h"

void ft_state_init(ft_state_t* st)
{
    st->nudge_retry_index = 0;
    st->cross_verify_fault_ch = 0;
    st->fault_level = 0;
    st->fault_code = 0;
    st->estop = false;
    st->check_dist_count = 0;
}

cv_verdict_t ft_cross_verify(const ft_sense_t* s)
{
    bool hard = s->laser_triggered;
    if (s->laser_distance_mm < 0) {
        /* laser invalid -> trust hard trigger */
        return hard ? CV_OBSTACLE : CV_CLEAR;
    }
    bool laser_obs = (s->laser_distance_mm < (int32_t)FT_CV_NEAR_MM);
    if (laser_obs == hard) {
        return laser_obs ? CV_OBSTACLE : CV_CLEAR;   /* consistent */
    }
    return CV_INTERFERENCE;                          /* single-route anomaly */
}

bool ft_check_dist(ft_state_t* st, bool obstacle_now)
{
    if (obstacle_now) {
        if (st->check_dist_count < 0xFF) st->check_dist_count++;
    } else {
        st->check_dist_count = 0;
    }
    return st->check_dist_count >= FT_CHECK_DIST_DEBOUNCE;
}

ft_action_t ft_evaluate(ft_state_t* st, const ft_sense_t* s)
{
    /* ESTOP always wins (region 2 global capture) */
    if (st->estop) {
        st->fault_level = 4;
        st->fault_code  = 0xE570u; /* ESTOP fault code (real code set by safety FSM) */
        return FT_ACT_ESTOP;
    }

    cv_verdict_t cv = ft_cross_verify(s);
    if (cv == CV_OBSTACLE) {
        st->fault_level = (uint8_t)FT_L3_SLOW_STOP;  /* confirmed -> graded stop */
        st->fault_code  = 0x0001u;
        return FT_ACT_STOP;
    }
    if (cv == CV_INTERFERENCE) {
        /* single-route anomaly: continue, record for diag/learning */
        st->cross_verify_fault_ch++;
        st->fault_level = 0;
        st->fault_code  = 0x0000u;
        return FT_ACT_CONTINUE;
    }
    /* CV_CLEAR */
    st->fault_level = 0;
    st->fault_code  = 0x0000u;
    return FT_ACT_CONTINUE;
}
