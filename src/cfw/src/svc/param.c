/* XLPS2-Alpha CFW — parameter layer implementation (L2/L5, ADR-007) */
#include "svc/param.h"

static const param_entry_t g_defaults[PARAM_COUNT] = {
    { PARAM_KP,             100, 100, 0,    1000 },
    { PARAM_KI,             10,  10,  0,    500  },
    { PARAM_KD,             5,   5,   0,    500  },
    { PARAM_FIND_ZERO_SPEED, 50,  50,  5,    200  },
    { PARAM_PREVIEW_MM,     100, 100, 0,    2000 },
    { PARAM_NUDGE_STEP_MM,  5,   5,   1,    50   },
    { PARAM_INTERFERENCE_TH, 3,   3,   1,    20   },
};

cfw_err_t param_init(cfw_param_store_t* s)
{
    if (!s) return CFW_ERR_PARAM;
    for (int i = 0; i < (int)PARAM_COUNT; i++) s->entries[i] = g_defaults[i];
    s->param_revision = CFW_PARAM_VERSION;
    s->smdl_revision  = 1u;
    return CFW_OK;
}

cfw_err_t param_set(cfw_param_store_t* s, param_id_t id, int32_t v)
{
    if (!s || id >= PARAM_COUNT) return CFW_ERR_PARAM;
    param_entry_t* e = &s->entries[id];
    if (v < e->min) v = e->min;
    if (v > e->max) v = e->max;
    if (v != e->value) {            /* monotonic bump only on real change */
        e->value = v;
        s->param_revision++;
    }
    return CFW_OK;
}

int32_t param_get(const cfw_param_store_t* s, param_id_t id)
{
    if (!s || id >= PARAM_COUNT) return 0;
    return s->entries[id].value;
}

cfw_err_t param_factory_reset(cfw_param_store_t* s)
{
    if (!s) return CFW_ERR_PARAM;
    for (int i = 0; i < (int)PARAM_COUNT; i++) s->entries[i].value = s->entries[i].def;
    s->param_revision++;            /* ADR-007: bump on reset, never rolls back */
    return CFW_OK;
}

cfw_err_t param_set_smdl_rev(cfw_param_store_t* s, uint32_t rev)
{
    if (!s) return CFW_ERR_PARAM;
    s->smdl_revision = rev;
    return CFW_OK;
}

uint32_t param_revision(const cfw_param_store_t* s) { return s ? s->param_revision : 0u; }
uint32_t smdl_revision(const cfw_param_store_t* s)  { return s ? s->smdl_revision  : 0u; }
