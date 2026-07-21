/* XLPS2-Alpha CFW — parameter layer (L2/L5, ADR-007)
 *
 * - Hot-tune (param/set) => param_revision++ (monotonic, no rollback).
 * - factory_reset_req   => reset param layer to defaults + param_revision++.
 * - config/smdl         => smdl_revision++ (independent counter).
 * All values static (no malloc); persisted to Flash/FRAM by L1 IStorage. */
#ifndef SVC_PARAM_H
#define SVC_PARAM_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PARAM_KP             = 0,
    PARAM_KI             = 1,
    PARAM_KD             = 2,
    PARAM_FIND_ZERO_SPEED= 3,   /* find_zero_speed (ADR-001) */
    PARAM_PREVIEW_MM     = 4,   /* preview_mm (ADR-001) */
    PARAM_NUDGE_STEP_MM  = 5,   /* nudge retry step */
    PARAM_INTERFERENCE_TH= 6,   /* cross-verify confidence threshold */
    PARAM_COUNT          = 7
} param_id_t;

typedef struct {
    param_id_t id;
    int32_t    value;
    int32_t    def;
    int32_t    min;
    int32_t    max;
} param_entry_t;

typedef struct {
    param_entry_t entries[PARAM_COUNT];
    uint32_t      param_revision;  /* ADR-007, monotonic */
    uint32_t      smdl_revision;   /* independent counter */
} cfw_param_store_t;

cfw_err_t param_init(cfw_param_store_t* s);
cfw_err_t param_set(cfw_param_store_t* s, param_id_t id, int32_t v); /* clamps + rev++ */
int32_t    param_get(const cfw_param_store_t* s, param_id_t id);
cfw_err_t param_factory_reset(cfw_param_store_t* s);   /* defaults + rev++ (ADR-007) */
cfw_err_t param_set_smdl_rev(cfw_param_store_t* s, uint32_t rev); /* smdl_revision = rev */
uint32_t   param_revision(const cfw_param_store_t* s);
uint32_t   smdl_revision(const cfw_param_store_t* s);

#ifdef __cplusplus
}
#endif
#endif /* SVC_PARAM_H */
