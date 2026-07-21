/* Host test: ADR-006 four-level fault tolerance — cross-verify + evaluate */
#include "cfw_test.h"
#include "comm/faults/fault_tolerance.h"

int g_tests = 0, g_fail = 0;

int main(void)
{
    /* ---- CROSS_VERIFY primitive ---- */
    ft_sense_t s;

    s.laser_distance_mm = -1; s.laser_triggered = true;  /* invalid laser, hard trigger */
    TASSERT_EQ(ft_cross_verify(&s), CV_OBSTACLE);

    s.laser_distance_mm = -1; s.laser_triggered = false;
    TASSERT_EQ(ft_cross_verify(&s), CV_CLEAR);

    s.laser_distance_mm = 50; s.laser_triggered = true;  /* 50<150 consistent */
    TASSERT_EQ(ft_cross_verify(&s), CV_OBSTACLE);

    s.laser_distance_mm = 50; s.laser_triggered = false; /* single-route anomaly */
    TASSERT_EQ(ft_cross_verify(&s), CV_INTERFERENCE);

    s.laser_distance_mm = 500; s.laser_triggered = false;/* 500>=150 consistent */
    TASSERT_EQ(ft_cross_verify(&s), CV_CLEAR);

    s.laser_distance_mm = 500; s.laser_triggered = true; /* single-route anomaly */
    TASSERT_EQ(ft_cross_verify(&s), CV_INTERFERENCE);

    /* ---- evaluate ---- */
    ft_state_t st; ft_state_init(&st);

    st.estop = true;
    TASSERT_EQ(ft_evaluate(&st, &s), FT_ACT_ESTOP);
    st.estop = false;

    s.laser_distance_mm = 50; s.laser_triggered = true;
    TASSERT_EQ(ft_evaluate(&st, &s), FT_ACT_STOP);
    TASSERT_EQ(st.fault_level, FT_L3_SLOW_STOP);

    s.laser_distance_mm = 50; s.laser_triggered = false; /* interference */
    uint16_t before = st.cross_verify_fault_ch;
    TASSERT_EQ(ft_evaluate(&st, &s), FT_ACT_CONTINUE);
    TASSERT_EQ(st.cross_verify_fault_ch, (uint16_t)(before + 1));

    s.laser_distance_mm = 500; s.laser_triggered = false; /* clear */
    TASSERT_EQ(ft_evaluate(&st, &s), FT_ACT_CONTINUE);

    /* L1 debounce requires consecutive reads */
    ft_state_t st2; ft_state_init(&st2);
    TASSERT(!ft_check_dist(&st2, true));
    TASSERT(!ft_check_dist(&st2, true));
    TASSERT(ft_check_dist(&st2, true));   /* 3rd consecutive confirms */
    TASSERT(ft_check_dist(&st2, false) == false); /* reset */

    printf("[fault] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
