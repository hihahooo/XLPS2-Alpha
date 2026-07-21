/* XLPS2-Alpha CFW — top-level runtime context (umbrella include)
 *
 * Single statically-allocated runtime (NO malloc). Aggregates telemetry, event
 * bus, param store, HSM engine, fault/interference state, diagnostics.
 * Layers strictly call downward through interfaces/events only. */
#ifndef CFW_H
#define CFW_H

#include "common/cfw_config.h"
#include "common/cfw_types.h"
#include "common/cfw_errors.h"
#include "hsm/hsm_engine.h"
#include "hsm/hsm_states.h"
#include "hsm/hsm_current_state.h"
#include "svc/event_bus.h"
#include "svc/filter.h"
#include "svc/kinematics.h"
#include "svc/param.h"
#include "svc/diag.h"
#include "comm/faults/fault_tolerance.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    cfw_telemetry_t   telem;
    evt_bus_t         evt;
    cfw_param_store_t param;
    hsm_engine_t      hsm;
    ft_state_t        fault;
    filt_ctx_t        filt;
    diag_log_t        diag;
    uint32_t          uptime_s;
    uint32_t          heartbeat_ts;
    /* non-telemetry runtime I/O (internal; NOT part of 33-field contract) */
    int32_t           laser_distance_mm;   /* RS485 laser raw (<0 invalid) */
    bool              pe_blocked;         /* photoelectric hard trigger */
    uint8_t           ambient_pct;        /* ambient light for self-learning */
    int32_t           motion_target_mm;   /* current motion target (true-zero) */
    bool              motion_active;      /* a motion profile is running */
    kin_profile_t     profile;            /* active motion profile */
    uint8_t           obstacle_state;     /* 0=clear, 1=obstacle (edge detection) */
    uint8_t           motion_flags;       /* bit0=cruise reached, bit1=near target */
} cfw_runtime_t;

/* Global runtime instance (static, no malloc). Defined in app/app_states.c. */
extern cfw_runtime_t g_rt;

/* Build the HSM engine tables and wire subscriptions (app layer). */
cfw_err_t app_init(cfw_runtime_t* rt);
/* One control tick of the application/HSM (called from HsmTask). */
void       app_tick(cfw_runtime_t* rt, uint32_t now_ms);
/* Sample telemetry fields from runtime for MQTT publish. */
void       app_sample_telemetry(cfw_runtime_t* rt, uint32_t now_ms);

#ifdef __cplusplus
}
#endif
#endif /* CFW_H */
