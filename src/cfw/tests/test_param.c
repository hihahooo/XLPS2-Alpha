/* Host test: parameter layer (ADR-007) — clamp, monotonic revision, reset */
#include "cfw_test.h"
#include "svc/param.h"

int g_tests = 0, g_fail = 0;

int main(void)
{
    cfw_param_store_t s;
    TASSERT_EQ(param_init(&s), CFW_OK);
    TASSERT_EQ(param_revision(&s), CFW_PARAM_VERSION);

    /* set + clamp out of range */
    TASSERT_EQ(param_set(&s, PARAM_KP, 99999), CFW_OK);
    TASSERT_EQ(param_get(&s, PARAM_KP), 1000);   /* max */
    TASSERT_EQ(param_set(&s, PARAM_KP, -50), CFW_OK);
    TASSERT_EQ(param_get(&s, PARAM_KP), 0);       /* min */

    /* no revision bump on identical value */
    uint32_t r0 = param_revision(&s);
    TASSERT_EQ(param_set(&s, PARAM_KP, 0), CFW_OK);
    TASSERT_EQ(param_revision(&s), r0);

    /* revision bumps on real change */
    TASSERT_EQ(param_set(&s, PARAM_KI, 42), CFW_OK);
    TASSERT_EQ(param_revision(&s), (uint32_t)(r0 + 1));

    /* factory reset restores defaults + bumps revision (ADR-007) */
    uint32_t rb = param_revision(&s);
    TASSERT_EQ(param_factory_reset(&s), CFW_OK);
    TASSERT_EQ(param_get(&s, PARAM_KI), 10);
    TASSERT_EQ(param_revision(&s), (uint32_t)(rb + 1));

    /* smdl revision independent */
    TASSERT_EQ(param_set_smdl_rev(&s, 7), CFW_OK);
    TASSERT_EQ(smdl_revision(&s), 7u);

    printf("[param] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
