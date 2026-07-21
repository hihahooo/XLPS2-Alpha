/* Host test: table-driven HSM engine — orthogonal regions, nested entry,
 * default-child, guards, self-transition, shallow history. */
#include "cfw_test.h"
#include "hsm/hsm_engine.h"
#include "hsm/hsm_states.h"
#include "hsm/hsm_current_state.h"

int g_tests = 0, g_fail = 0;

/* ---- Region 0 (main) states ---- */
#define A   HSM_ID(REGION_MAIN, MAIN_BOOTING,        SUB_CONTAINER)
#define A1  HSM_ID(REGION_MAIN, MAIN_BOOTING,        SUB_BUSY)
#define B   HSM_ID(REGION_MAIN, MAIN_IDLE,           SUB_CONTAINER)
#define C   HSM_ID(REGION_MAIN, MAIN_TRAVELING,      SUB_CONTAINER)
#define C1  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_ACCEL)
#define C2  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_CRUISE)

/* ---- Region 1 (energy) states ---- */
#define E0  HSM_ID(REGION_ENERGY, ENERGY_POWER_NORMAL, SUB_CONTAINER)
#define E0a HSM_ID(REGION_ENERGY, ENERGY_POWER_NORMAL, SUB_BUSY)
#define E1  HSM_ID(REGION_ENERGY, ENERGY_CHARGING,     SUB_CONTAINER)
#define E1a HSM_ID(REGION_ENERGY, ENERGY_CHARGING,     SUB_BUSY)

static const hsm_state_t g_states[] = {
    { A,  HSM_ID_INVALID, A1,  false, NULL, NULL },
    { A1, A,              HSM_ID_INVALID, false, NULL, NULL },
    { B,  HSM_ID_INVALID, HSM_ID_INVALID, false, NULL, NULL },
    { C,  HSM_ID_INVALID, C1,  false, NULL, NULL },
    { C1, C,              HSM_ID_INVALID, false, NULL, NULL },
    { C2, C,              HSM_ID_INVALID, false, NULL, NULL },
    { E0, HSM_ID_INVALID, E0a, true,  NULL, NULL },
    { E0a,E0,             HSM_ID_INVALID, false, NULL, NULL },
    { E1, HSM_ID_INVALID, E1a, false, NULL, NULL },
    { E1a,E1,             HSM_ID_INVALID, false, NULL, NULL },
};

static bool guard_false(void* ctx) { (void)ctx; return false; }

static const hsm_transition_t g_trans[] = {
    { A,  EV_BOOT_DONE,        NULL,        B,  NULL },
    { B,  EV_TASK_START,       NULL,        C,  NULL },
    { C1, EV_ARRIVED,          NULL,        C2, NULL },
    { C2, EV_OBSTACLE_DETECTED, guard_false, C2, NULL }, /* must be ignored */
    { C2, EV_NUDGE_DONE,       NULL,        C2, NULL },  /* self-transition */
    { E0, EV_LOW_BATTERY,      NULL,        E1, NULL },
    { E1, EV_CHARGE_DONE,      NULL,        HSM_TO_HISTORY, NULL },
};

int main(void)
{
    hsm_engine_t e;
    TASSERT_EQ(hsm_init(&e, g_states, (uint16_t)(sizeof(g_states)/sizeof(g_states[0])),
                        g_trans, (uint16_t)(sizeof(g_trans)/sizeof(g_trans[0])), NULL),
               CFW_OK);
    TASSERT_EQ(hsm_region_add(&e, REGION_MAIN, A), CFW_OK);
    TASSERT_EQ(hsm_region_add(&e, REGION_ENERGY, E0), CFW_OK);
    TASSERT_EQ(hsm_start(&e), CFW_OK);

    /* default-child entry */
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), A1);
    TASSERT_EQ(hsm_active_state(&e, REGION_ENERGY), E0a);

    /* shallow history: E0a -> E1a, then restore to E0a (not re-enter E0) */
    hsm_dispatch(&e, EV_LOW_BATTERY);
    TASSERT_EQ(hsm_active_state(&e, REGION_ENERGY), E1a);
    hsm_dispatch(&e, EV_CHARGE_DONE);
    TASSERT_EQ(hsm_active_state(&e, REGION_ENERGY), E0a);

    /* orthogonal isolation: EV_BOOT_DONE only affects region 0 */
    hsm_dispatch(&e, EV_BOOT_DONE);
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), B);
    TASSERT_EQ(hsm_active_state(&e, REGION_ENERGY), E0a);  /* unchanged */

    /* task start -> C, default child C1 */
    hsm_dispatch(&e, EV_TASK_START);
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), C1);

    /* arrived -> C2 (sibling under C) */
    hsm_dispatch(&e, EV_ARRIVED);
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), C2);

    /* guarded false transition ignored */
    hsm_dispatch(&e, EV_OBSTACLE_DETECTED);
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), C2);

    /* self-transition keeps same active state */
    hsm_dispatch(&e, EV_NUDGE_DONE);
    TASSERT_EQ(hsm_active_state(&e, REGION_MAIN), C2);

    /* ADR-003 encoding of active main state */
    uint16_t cs = hsm_encode_active(&e, REGION_MAIN);
    uint8_t r, t, s;
    cfw_state_decode(cs, &r, &t, &s);
    TASSERT_EQ(r, REGION_MAIN);
    TASSERT_EQ(t, MAIN_TRAVELING);
    TASSERT_EQ(s, TRAV_CRUISE);
    TASSERT(cfw_state_is_valid(cs));

    /* is_in checks */
    TASSERT(hsm_is_in(&e, REGION_MAIN, C));   /* C2 is inside C */
    TASSERT(!hsm_is_in(&e, REGION_MAIN, B));

    printf("[hsm] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
