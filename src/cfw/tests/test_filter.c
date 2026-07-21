/* Host test: ambient-light self-learning interference filter */
#include "cfw_test.h"
#include "svc/filter.h"

int g_tests = 0, g_fail = 0;

int main(void)
{
    filt_ctx_t f;
    filt_init(&f);

    /* consistent readings */
    TASSERT_EQ(filt_classify(&f, true,  true,  100), FILT_OBSTACLE);
    TASSERT_EQ(filt_classify(&f, false, false, 500), FILT_CLEAR);

    /* single-route anomaly => interference (ADR-006) */
    TASSERT_EQ(filt_classify(&f, true,  false, 500), FILT_INTERFERENCE);
    TASSERT_EQ(filt_classify(&f, false, true,  100), FILT_INTERFERENCE);

    /* ambient learning reaches "learned" after goal samples */
    for (uint8_t i = 0; i < FILT_AMBIENT_LEARN_GOAL; i++) filt_learn_ambient(&f, 80);
    TASSERT(f.learned);
    TASSERT(f.ambient_avg > 7000);  /* ~80% scaled */

    printf("[filter] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
