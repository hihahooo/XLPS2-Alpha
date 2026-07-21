/* XLPS2-Alpha CFW — L4 application state tree (wires the 3-region HSM) */
#ifndef APP_APP_STATES_H
#define APP_APP_STATES_H

#include "cfw.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Compose app state ids from (region,top,sub). Mirrors hsm_states.h HSM_ID. */
#define APP_ID(region, top, sub) HSM_ID(region, top, sub)

extern const hsm_state_t  g_app_states[];
extern const uint16_t     g_app_state_count;
extern const hsm_transition_t g_app_trans[];
extern const uint16_t     g_app_trans_count;

/* Event handlers (subscribe in app_init) */
void app_on_task_received(cfw_event_type_t ev, evt_sub_id_t id,
                          const void* payload, uint16_t len, void* ctx);
void app_on_low_battery(cfw_event_type_t ev, evt_sub_id_t id,
                        const void* payload, uint16_t len, void* ctx);
void app_on_estop(cfw_event_type_t ev, evt_sub_id_t id,
                 const void* payload, uint16_t len, void* ctx);
void app_on_factory_reset(cfw_event_type_t ev, evt_sub_id_t id,
                          const void* payload, uint16_t len, void* ctx);

#ifdef __cplusplus
}
#endif
#endif /* APP_APP_STATES_H */
