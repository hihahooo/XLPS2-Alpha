/* Host test: ADR-003 current_state encode/decode (byte-level, cross-module) */
#include "cfw_test.h"
#include "hsm/hsm_current_state.h"

int g_tests = 0, g_fail = 0;

int main(void)
{
    uint16_t enc = cfw_state_encode(REGION_MAIN, MAIN_TRAVELING, TRAV_CRUISE);
    uint8_t r, t, s;
    cfw_state_decode(enc, &r, &t, &s);
    TASSERT_EQ(r, REGION_MAIN);
    TASSERT_EQ(t, MAIN_TRAVELING);
    TASSERT_EQ(s, TRAV_CRUISE);

    /* must match raw bit math used by HMI/OTA decoders */
    TASSERT_EQ(enc, (uint16_t)((REGION_MAIN << 14) | (MAIN_TRAVELING << 8) | TRAV_CRUISE));

    /* safety estop region */
    uint16_t e2 = cfw_state_encode(REGION_SAFETY, SAFETY_ESTOP, SUB_NONE);
    TASSERT(cfw_state_is_valid(e2));
    uint8_t r2, t2, s2;
    cfw_state_decode(e2, &r2, &t2, &s2);
    TASSERT_EQ(r2, REGION_SAFETY);
    TASSERT_EQ(t2, SAFETY_ESTOP);

    /* uninit sentinel */
    TASSERT(!cfw_state_is_valid(CFW_STATE_UNINIT));

    /* region overflow rejected */
    uint16_t bad = cfw_state_encode(3, 0, 0);
    TASSERT(!cfw_state_is_valid(bad));

    /* max valid region=2 */
    uint16_t ok = cfw_state_encode(REGION_SAFETY, SAFETY_WARNING, SUB_BUSY);
    TASSERT(cfw_state_is_valid(ok));

    printf("[current_state] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
