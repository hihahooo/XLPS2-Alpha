/* XLPS2-Alpha CFW — table-driven Hierarchical State Machine engine (L3)
 *
 * Pure-generic, RGV-agnostic. Supports:
 *   - 3 orthogonal regions (主业务/能源/安全) ran in parallel
 *   - nested (composite) states with default-initial-child entry
 *   - shallow history (for energy CHARGING preempt/return)
 *   - event bubbling up the parent chain with guard evaluation
 *   - static tables only (no malloc); host-testable.
 *
 * SSOT: docs/overview.md §4, adr-003-current-state.md
 */
#ifndef HSM_ENGINE_H
#define HSM_ENGINE_H

#include <stdint.h>
#include <stdbool.h>
#include "common/cfw_config.h"
#include "common/cfw_errors.h"
#include "common/cfw_types.h"
#include "hsm/hsm_states.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef void  (*hsm_action_t)(void *ctx);
typedef bool  (*hsm_guard_t)(void *ctx);

#define HSM_ID_INVALID   ((hsm_state_id_t)0xFFFFu)
#define HSM_TO_HISTORY   ((hsm_state_id_t)0xFFFEu)   /* history pseudo-target */

typedef struct {
    hsm_state_id_t id;
    hsm_state_id_t parent;       /* HSM_ID_INVALID => top of region */
    hsm_state_id_t initial_child;/* default child on entry (HSM_ID_INVALID => none) */
    bool           history;      /* record shallow history when exited */
    hsm_action_t   on_entry;
    hsm_action_t   on_exit;
} hsm_state_t;

typedef struct {
    hsm_state_id_t   state;    /* source state id (transition declared here) */
    cfw_event_type_t event;
    hsm_guard_t      guard;    /* NULL => always */
    hsm_state_id_t   target;   /* destination (may be HSM_TO_HISTORY) */
    hsm_action_t     action;   /* transition action (NULL ok) */
} hsm_transition_t;

typedef struct {
    uint8_t         region;
    hsm_state_id_t  initial;
    hsm_state_id_t  active;      /* currently active leaf */
    hsm_state_id_t  history;     /* shallow history leaf */
    bool            history_set;
} hsm_region_t;

typedef struct {
    hsm_region_t           regions[CFW_HSM_MAX_REGIONS];
    uint8_t                region_count;
    const hsm_state_t*     states;
    uint16_t               state_count;
    const hsm_transition_t*transitions;
    uint16_t               trans_count;
    void*                  ctx;
    bool                   last_event_handled;
} hsm_engine_t;

cfw_err_t hsm_init(hsm_engine_t* e,
                   const hsm_state_t* states, uint16_t state_count,
                   const hsm_transition_t* transitions, uint16_t trans_count,
                   void* ctx);
cfw_err_t  hsm_region_add(hsm_engine_t* e, uint8_t region, hsm_state_id_t initial);
cfw_err_t  hsm_start(hsm_engine_t* e);

/* Dispatch one event to every orthogonal region; each region resolves
 * independently per UML semantics. */
void hsm_dispatch(hsm_engine_t* e, cfw_event_type_t ev);

hsm_state_id_t hsm_active_state(const hsm_engine_t* e, uint8_t region);
bool hsm_is_in(const hsm_engine_t* e, uint8_t region, hsm_state_id_t state);
uint16_t hsm_encode_active(const hsm_engine_t* e, uint8_t region); /* ADR-003 */

/* Build the per-region (region,top,sub) for telemetry reporting. */
void hsm_region_components(const hsm_engine_t* e, uint8_t region,
                           uint8_t* top_state, uint8_t* sub_state);

#ifdef __cplusplus
}
#endif
#endif /* HSM_ENGINE_H */
