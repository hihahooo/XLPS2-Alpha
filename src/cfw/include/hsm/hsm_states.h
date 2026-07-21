/* XLPS2-Alpha CFW — HSM state vocabulary (ADR-003)
 *
 * 3 orthogonal regions (主业务 / 能源 / 安全). Each region numbers its
 * top-states locally (0..N); `current_state` is encoded as
 *   (region<<14) | (top_state<<8) | sub_state
 * and decoded per-region by HMI/cloud. SSOT: docs/contract/adr-003-current-state.md
 */
#ifndef HSM_STATES_H
#define HSM_STATES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Region identifiers ---- */
typedef enum {
    REGION_MAIN   = 0,   /* 主业务区 */
    REGION_ENERGY = 1,   /* 能源管理区 */
    REGION_SAFETY = 2,   /* 安全监控区（最高优先级，ESTOP 全局捕获） */
    REGION_COUNT  = 3
} cfw_region_t;

/* ---- Top-states: Region 0 (主业务) ---- */
typedef enum {
    MAIN_BOOTING        = 0,
    MAIN_IDLE           = 1,
    MAIN_TASK_RUNNING   = 2,
    MAIN_FIND_ZERO      = 3,
    MAIN_TRACK_IDENTIFY = 4,
    MAIN_DISPATCHING    = 5,
    MAIN_TRAVELING      = 6,
    MAIN_LOADING        = 7,
    MAIN_UNLOADING      = 8,
    MAIN_RETURNING      = 9,
    MAIN_TOP_COUNT      = 10
} cfw_main_top_t;

/* ---- Top-states: Region 1 (能源) ---- */
typedef enum {
    ENERGY_POWER_NORMAL = 0,
    ENERGY_LOW_BATTERY  = 1,
    ENERGY_CHARGING     = 2,   /* supports shallow history (preempt return) */
    ENERGY_TOP_COUNT    = 3
} cfw_energy_top_t;

/* ---- Top-states: Region 2 (安全) ---- */
typedef enum {
    SAFETY_OK     = 0,
    SAFETY_WARNING = 1,
    SAFETY_ESTOP   = 2,   /* global capture */
    SAFETY_TOP_COUNT = 3
} cfw_safety_top_t;

/* ---- Sub-states: generic ---- */
typedef enum {
    SUB_NONE = 0,
    SUB_BUSY = 1,
    SUB_DONE = 2,
    SUB_FAIL = 3
} cfw_sub_t;

/* ---- Sub-states: TRAVELING (the detailed motion profile) ---- */
typedef enum {
    TRAV_ACCEL        = 0,
    TRAV_CRUISE       = 1,
    TRAV_CHECK_DIST   = 2,   /* 一级 CHECK_DIST 软滤波 */
    TRAV_DECEL        = 3,
    TRAV_POSITIONING  = 4,
    TRAV_NUDGE_RETRY  = 5,   /* 二级 NUDGE_RETRY 微动 */
    TRAV_CROSS_VERIFY = 6,   /* 四级 CROSS_VERIFY 交叉验证 */
    TRAV_SUB_COUNT    = 7
} cfw_travel_sub_t;

/* ---- Sub-states: FIND_ZERO / TRACK_IDENTIFY ---- */
typedef enum {
    FZ_APPROACH = 0,
    FZ_DEBOUNCE = 1,
    FZ_LOCKED   = 2
} cfw_findzero_sub_t;

typedef enum {
    TI_READ       = 0,
    TI_IDENTIFIED = 1,   /* 有码 */
    TI_ANONYMOUS  = 2    /* 无码 */
} cfw_trackid_sub_t;

/* ---- HSM local state id: (region<<12)|(top<<8)|sub ----
 * Region is embedded so the global state table stays unambiguous even though
 * different regions reuse the same top/sub value spaces. The ADR-003
 * current_state encoding is derived separately via cfw_state_encode(). */
typedef uint16_t hsm_state_id_t;

#define HSM_ID(region, top, sub) \
    ((hsm_state_id_t)(((uint16_t)((region) & 0x3u)  << 12) | \
                      ((uint16_t)((top)    & 0x3Fu) << 8)  | \
                      ((uint16_t)((sub)    & 0xFFu))))
#define HSM_REGION(id)    ((uint8_t)(((id) >> 12) & 0x3u))
#define HSM_TOP(id)       ((uint8_t)(((id) >> 8)  & 0x3Fu))
#define HSM_SUB(id)       ((uint8_t)((id) & 0xFFu))

/* reserved sub value for composite (container) states; leaves use real sub */
#define SUB_CONTAINER 0xFFu

#ifdef __cplusplus
}
#endif
#endif /* HSM_STATES_H */
