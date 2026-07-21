/* XLPS2-Alpha CFW — L4 application state tree (3-region HSM wiring)
 *
 * Region 0 主业务 : BOOTING→IDLE→TASK_RUNNING(FIND_ZERO→TRACK_IDENTIFY→
 *                   DISPATCHING→TRAVELING(ACCEL/CRUISE/CHECK_DIST/DECEL/
 *                   POSITIONING+NUDGE_RETRY+CROSS_VERIFY)→LOADING/UNLOADING/
 *                   RETURNING)
 * Region 1 能源    : POWER_NORMAL↔LOW_BATTERY→CHARGING (history)
 * Region 2 安全    : SAFE_OK↔WARNING→ESTOP (global capture)
 *
 * The HSM is driven by hsm_dispatch(), separate from the event bus. A bridge
 * subscriber forwards every published event into hsm_dispatch(). */
#include "app/app_states.h"
#include "app/task_fsm.h"
#include "hal/hal.h"
#include "svc/kinematics.h"
#include <string.h>

/* ---- app state ids ---- */
#define S_BOOT HSM_ID(REGION_MAIN, MAIN_BOOTING,        SUB_CONTAINER)
#define S_IDLE HSM_ID(REGION_MAIN, MAIN_IDLE,           SUB_CONTAINER)
#define S_TR   HSM_ID(REGION_MAIN, MAIN_TASK_RUNNING,   SUB_CONTAINER)
#define S_FZ   HSM_ID(REGION_MAIN, MAIN_FIND_ZERO,      SUB_CONTAINER)
#define S_FZD  HSM_ID(REGION_MAIN, MAIN_FIND_ZERO,      FZ_DEBOUNCE)
#define S_FZL  HSM_ID(REGION_MAIN, MAIN_FIND_ZERO,      FZ_LOCKED)
#define S_TI   HSM_ID(REGION_MAIN, MAIN_TRACK_IDENTIFY, SUB_CONTAINER)
#define S_TIR  HSM_ID(REGION_MAIN, MAIN_TRACK_IDENTIFY, TI_READ)
#define S_TII  HSM_ID(REGION_MAIN, MAIN_TRACK_IDENTIFY, TI_IDENTIFIED)
#define S_TIA  HSM_ID(REGION_MAIN, MAIN_TRACK_IDENTIFY, TI_ANONYMOUS)
#define S_DISP HSM_ID(REGION_MAIN, MAIN_DISPATCHING,    SUB_BUSY)
#define S_TRAV HSM_ID(REGION_MAIN, MAIN_TRAVELING,      SUB_CONTAINER)
#define S_ACC  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_ACCEL)
#define S_CRU  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_CRUISE)
#define S_CD   HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_CHECK_DIST)
#define S_DEC  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_DECEL)
#define S_POS  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_POSITIONING)
#define S_NUD  HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_NUDGE_RETRY)
#define S_CV   HSM_ID(REGION_MAIN, MAIN_TRAVELING,      TRAV_CROSS_VERIFY)
#define S_LOAD HSM_ID(REGION_MAIN, MAIN_LOADING,        SUB_BUSY)
#define S_UNL  HSM_ID(REGION_MAIN, MAIN_UNLOADING,      SUB_BUSY)
#define S_RET  HSM_ID(REGION_MAIN, MAIN_RETURNING,      SUB_BUSY)

#define E0 HSM_ID(REGION_ENERGY, ENERGY_POWER_NORMAL, SUB_CONTAINER)
#define E1 HSM_ID(REGION_ENERGY, ENERGY_LOW_BATTERY,  SUB_CONTAINER)
#define E2 HSM_ID(REGION_ENERGY, ENERGY_CHARGING,     SUB_CONTAINER)  /* history */

#define SA HSM_ID(REGION_SAFETY, SAFETY_OK,     SUB_CONTAINER)
#define SW HSM_ID(REGION_SAFETY, SAFETY_WARNING, SUB_CONTAINER)
#define SE HSM_ID(REGION_SAFETY, SAFETY_ESTOP,   SUB_CONTAINER)

/* ---- handlers ---- */
static void st_on_entry(void* ctx)
{
    cfw_runtime_t* rt = (cfw_runtime_t*)ctx;
    evt_publish(&rt->evt, EV_STATE_CHANGED, NULL, 0);
}
static void st_on_exit(void* ctx) { (void)ctx; }

static bool gd_has_track(void* ctx) { return ((cfw_runtime_t*)ctx)->telem.track_id != 0; }
static bool gd_no_track(void* ctx)  { return ((cfw_runtime_t*)ctx)->telem.track_id == 0; }

/* bridge: every published event also drives the HSM */
static void hsm_bridge(cfw_event_type_t ev, evt_sub_id_t id,
                       const void* p, uint16_t len, void* ctx)
{
    (void)id; (void)p; (void)len;
    hsm_dispatch(&((cfw_runtime_t*)ctx)->hsm, ev);
}

/* ---- state table ---- */
const hsm_state_t g_app_states[] = {
    { S_BOOT, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_IDLE, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_TR,   HSM_ID_INVALID, S_FZ,           false, st_on_entry, st_on_exit },
    { S_FZ,   S_TR,           S_FZD,          false, st_on_entry, st_on_exit },
    { S_FZD,  S_FZ,           HSM_ID_INVALID, false, NULL,        NULL },
    { S_FZL,  S_FZ,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_TI,   S_TR,           S_TIR,          false, st_on_entry, st_on_exit },
    { S_TIR,  S_TI,           HSM_ID_INVALID, false, NULL,        NULL },
    { S_TII,  S_TI,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_TIA,  S_TI,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_DISP, S_TR,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_TRAV, S_TR,           S_ACC,          false, st_on_entry, st_on_exit },
    { S_ACC,  S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_CRU,  S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_CD,   S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_DEC,  S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_POS,  S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_NUD,  S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_CV,   S_TRAV,         HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_LOAD, S_TR,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_UNL,  S_TR,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { S_RET,  S_TR,           HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { E0, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { E1, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { E2, HSM_ID_INVALID, HSM_ID_INVALID, true,  st_on_entry, st_on_exit },
    { SA, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { SW, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
    { SE, HSM_ID_INVALID, HSM_ID_INVALID, false, st_on_entry, st_on_exit },
};
const uint16_t g_app_state_count = (uint16_t)(sizeof(g_app_states)/sizeof(g_app_states[0]));

const hsm_transition_t g_app_trans[] = {
    { S_BOOT, EV_BOOT_DONE,        NULL, S_IDLE, NULL },
    { S_IDLE, EV_TASK_RECEIVED,    NULL, S_TR,   NULL },
    { S_FZD,  EV_ZERO_FOUND,       NULL, S_FZL,  NULL },
    { S_FZL,  EV_TRACK_IDENTIFIED, NULL, S_TI,   NULL },
    { S_TIR,  EV_TRACK_IDENTIFIED, gd_has_track, S_TII, NULL },
    { S_TIR,  EV_TRACK_IDENTIFIED, gd_no_track,  S_TIA, NULL },
    { S_TII,  EV_TASK_START,       NULL, S_DISP, NULL },
    { S_TIA,  EV_TASK_START,       NULL, S_DISP, NULL },
    { S_DISP, EV_TASK_START,       NULL, S_TRAV, NULL },
    { S_ACC,  EV_SPEED_REACHED,    NULL, S_CRU,  NULL },
    { S_CRU,  EV_TARGET_NEAR,      NULL, S_DEC,  NULL },
    { S_CRU,  EV_OBSTACLE_DETECTED,NULL, S_CD,   NULL },
    { S_CD,   EV_OBSTACLE_CLEAR,   NULL, S_CRU,  NULL },
    { S_CD,   EV_NUDGE_DONE,       NULL, S_NUD,  NULL },
    { S_NUD,  EV_NUDGE_DONE,       NULL, S_CV,   NULL },
    { S_CV,   EV_OBSTACLE_CLEAR,   NULL, S_CRU,  NULL },
    { S_CV,   EV_OBSTACLE_DETECTED,NULL, S_DEC,  NULL },  /* confirmed -> slow stop */
    { S_DEC,  EV_ARRIVED,          NULL, S_POS,  NULL },
    { S_POS,  EV_OBSTACLE_CLEAR,   NULL, S_CRU,  NULL },
    { S_POS,  EV_LOAD_DONE,        NULL, S_LOAD, NULL },
    { S_LOAD, EV_UNLOAD_DONE,      NULL, S_RET,  NULL },
    { S_RET,  EV_ARRIVED,          NULL, S_IDLE, NULL },
    /* energy */
    { E0, EV_LOW_BATTERY, NULL, E1, NULL },
    { E1, EV_BATTERY_OK,  NULL, E0, NULL },
    { E1, EV_CHARGE_START,NULL, E2, NULL },
    { E2, EV_CHARGE_DONE, NULL, E0, NULL },
    /* safety (global capture) */
    { SA, EV_WARNING, NULL, SW, NULL },
    { SW, EV_WARNING_CLEAR, NULL, SA, NULL },
    { SA, EV_ESTOP, NULL, SE, NULL },
    { SW, EV_ESTOP, NULL, SE, NULL },
    { SE, EV_ESTOP_RESET, NULL, SA, NULL },
};
const uint16_t g_app_trans_count = (uint16_t)(sizeof(g_app_trans)/sizeof(g_app_trans[0]));

/* ---- global runtime ---- */
cfw_runtime_t g_rt;

/* ---- domain event handlers ---- */
void app_on_task_received(cfw_event_type_t ev, evt_sub_id_t id,
                          const void* payload, uint16_t len, void* ctx)
{
    (void)ev; (void)id;
    cfw_runtime_t* rt = (cfw_runtime_t*)ctx;
    if (payload && len >= sizeof(cfw_task_dispatch_t)) {
        const cfw_task_dispatch_t* t = (const cfw_task_dispatch_t*)payload;
        rt->telem.task_status = TASK_ST_QUEUED;
        if (t->task_axis == TASK_AXIS_WALK) {
            rt->motion_target_mm = t->task_target_pos_mm;   /* walk target (true-zero) */
        }
    }
}
void app_on_low_battery(cfw_event_type_t ev, evt_sub_id_t id,
                        const void* payload, uint16_t len, void* ctx)
{ (void)ev; (void)id; (void)payload; (void)len; /* energy region handles via HSM */ }
void app_on_estop(cfw_event_type_t ev, evt_sub_id_t id,
                 const void* payload, uint16_t len, void* ctx)
{ (void)ev; (void)id; (void)payload; (void)len; }
void app_on_factory_reset(cfw_event_type_t ev, evt_sub_id_t id,
                          const void* payload, uint16_t len, void* ctx)
{
    (void)ev; (void)id; (void)payload; (void)len;
    cfw_runtime_t* rt = (cfw_runtime_t*)ctx;
    param_factory_reset(&rt->param);   /* ADR-007: resets params + bumps revision */
    diag_push(&rt->diag, 0xAD07u, rt->uptime_s);
}

/* ---- init ---- */
cfw_err_t app_init(cfw_runtime_t* rt)
{
    memset(rt, 0, sizeof(*rt));
    evt_init(&rt->evt);
    param_init(&rt->param);
    ft_state_init(&rt->fault);
    filt_init(&rt->filt);
    diag_init(&rt->diag);
    rt->telem.task_status = TASK_ST_IDLE;
    strncpy(rt->telem.fw_version, CFW_FW_VERSION, CFW_STR_VER_LEN - 1);
    strncpy(rt->telem.smdl_version, CFW_SMDL_VERSION, CFW_STR_VER_LEN - 1);
    rt->telem.current_state = CFW_STATE_UNINIT;

    hsm_init(&rt->hsm, g_app_states, g_app_state_count, g_app_trans, g_app_trans_count, rt);
    hsm_region_add(&rt->hsm, REGION_MAIN, S_BOOT);
    hsm_region_add(&rt->hsm, REGION_ENERGY, E0);
    hsm_region_add(&rt->hsm, REGION_SAFETY, SA);
    hsm_start(&rt->hsm);

    /* domain handlers */
    evt_subscribe(&rt->evt, EV_TASK_RECEIVED, app_on_task_received, rt);
    evt_subscribe(&rt->evt, EV_LOW_BATTERY,  app_on_low_battery, rt);
    evt_subscribe(&rt->evt, EV_ESTOP,         app_on_estop, rt);
    evt_subscribe(&rt->evt, EV_FACTORY_RESET, app_on_factory_reset, rt);
    /* bridge: forward every event into the HSM */
    for (cfw_event_type_t e = 0; e < EV_COUNT; e++)
        evt_subscribe(&rt->evt, e, hsm_bridge, rt);

    return CFW_OK;
}

/* ---- per-tick application loop ---- */
void app_tick(cfw_runtime_t* rt, uint32_t now_ms)
{
    rt->uptime_s = now_ms / 1000u;

    const hal_motor_t*   m = hal_motor_stm32();
    const hal_laser_t*   l = hal_laser_stm32();
    const hal_encoder_t* e = hal_encoder_stm32();

    float cur = 0; int8_t temp = 25; int32_t enc = 0;
    if (hal_motor_get_feedback(m, HAL_AXIS_WALK, &cur, &temp, &enc) == CFW_OK) {
        rt->telem.motor_current_a = cur;
        rt->telem.motor_temp_c    = temp;
        rt->telem.encoder_position = enc;
    }
    int32_t d = -1; hal_laser_status_t ls = LASER_DEV_ERROR;
    if (hal_laser_read_distance(l, &d) == CFW_OK) rt->laser_distance_mm = d;
    if (hal_laser_read_status(l, &ls) == CFW_OK) {
        rt->telem.laser_status = (ls == LASER_DEV_TRIGGERED) ? LASER_TRIGGERED
                                : (ls == LASER_DEV_ERROR)    ? LASER_ERROR : LASER_OK;
        rt->pe_blocked = (ls == LASER_DEV_TRIGGERED);
    }
    int32_t cnt = 0;
    if (hal_encoder_read(e, &cnt) == CFW_OK)
        rt->telem.position_mm = kin_integrate(cnt, 10);   /* 10 pulses/mm (board-tuned) */

    if (rt->motion_active) task_fsm_tick(rt);

    /* ADR-006 four-level evaluation on live sensing */
    ft_sense_t sense = { rt->laser_distance_mm, rt->pe_blocked, rt->ambient_pct };
    ft_action_t act = ft_evaluate(&rt->fault, &sense);
    if (act == FT_ACT_STOP || act == FT_ACT_ESTOP) {
        hal_motor_set_velocity(m, HAL_AXIS_WALK, 0);
        if (rt->obstacle_state == 0) { rt->obstacle_state = 1; evt_publish(&rt->evt, EV_OBSTACLE_DETECTED, NULL, 0); }
    } else { /* CONTINUE (clear or interference) */
        if (rt->obstacle_state == 1) { rt->obstacle_state = 0; evt_publish(&rt->evt, EV_OBSTACLE_CLEAR, NULL, 0); }
    }
}

/* ---- telemetry sampling (dominant region: safety > main) ---- */
void app_sample_telemetry(cfw_runtime_t* rt, uint32_t now_ms)
{
    hsm_state_id_t ss = hsm_active_state(&rt->hsm, REGION_SAFETY);
    bool safety_ok = (ss == HSM_ID_INVALID) || (HSM_TOP(ss) == SAFETY_OK);
    uint8_t region = safety_ok ? (uint8_t)REGION_MAIN : (uint8_t)REGION_SAFETY;

    uint8_t top, sub;
    hsm_region_components(&rt->hsm, region, &top, &sub);
    rt->telem.region       = region;
    rt->telem.top_state    = top;
    rt->telem.sub_state    = sub;
    rt->telem.current_state = cfw_state_encode(region, top, sub);

    rt->telem.is_safe      = safety_ok;
    rt->telem.fault_level  = rt->fault.fault_level;
    rt->telem.fault_code   = rt->fault.fault_code;
    rt->telem.interference_count = rt->fault.cross_verify_fault_ch;
    rt->telem.param_revision = param_revision(&rt->param);
    rt->telem.smdl_revision  = smdl_revision(&rt->param);
    rt->telem.uptime_s     = rt->uptime_s;
    rt->telem.heartbeat_ts = now_ms / 1000u;
    rt->telem.diag_code    = diag_last(&rt->diag);
}
