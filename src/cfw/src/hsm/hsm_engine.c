/* XLPS2-Alpha CFW — HSM engine implementation (see hsm_engine.h) */
#include "hsm/hsm_engine.h"

/* ---- internal helpers ---- */
static const hsm_state_t* find_state(const hsm_engine_t* e, hsm_state_id_t id)
{
    if (id == HSM_ID_INVALID) return NULL;
    for (uint16_t i = 0; i < e->state_count; i++) {
        if (e->states[i].id == id) return &e->states[i];
    }
    return NULL;
}

static hsm_state_id_t parent_of(const hsm_engine_t* e, hsm_state_id_t id)
{
    const hsm_state_t* s = find_state(e, id);
    return s ? s->parent : HSM_ID_INVALID;
}

static bool is_ancestor_or_self(const hsm_engine_t* e, hsm_state_id_t node,
                                hsm_state_id_t anc)
{
    hsm_state_id_t cur = node;
    while (cur != HSM_ID_INVALID) {
        if (cur == anc) return true;
        cur = parent_of(e, cur);
    }
    return false;
}

/* lowest common ancestor of a and b (inclusive) within the region tree */
static hsm_state_id_t lca(const hsm_engine_t* e, hsm_state_id_t a, hsm_state_id_t b)
{
    /* collect ancestors of b */
    hsm_state_id_t chain[CFW_HSM_MAX_STATES];
    uint16_t n = 0;
    hsm_state_id_t cur = b;
    while (cur != HSM_ID_INVALID && n < CFW_HSM_MAX_STATES) {
        chain[n++] = cur;
        cur = parent_of(e, cur);
    }
    /* walk a upward, first match is LCA */
    cur = a;
    while (cur != HSM_ID_INVALID) {
        for (uint16_t i = 0; i < n; i++) {
            if (chain[i] == cur) return cur;
        }
        cur = parent_of(e, cur);
    }
    return HSM_ID_INVALID;
}

/* record shallow history when exiting a history-flagged composite */
static void record_history_on_exit(hsm_engine_t* e, uint8_t region, hsm_state_id_t exited)
{
    const hsm_state_t* s = find_state(e, exited);
    if (s && s->history) {
        /* direct child of `exited` currently on the active path */
        hsm_state_id_t child = e->regions[region].active;
        while (child != HSM_ID_INVALID && parent_of(e, child) != exited) {
            child = parent_of(e, child);
        }
        e->regions[region].history = child;
        e->regions[region].history_set = true;
    }
}

/* enter `target` (composite or leaf) recursively via default initial_child */
static void enter_state(hsm_engine_t* e, uint8_t region, hsm_state_id_t target)
{
    hsm_state_id_t cur = target;
    while (cur != HSM_ID_INVALID) {
        const hsm_state_t* s = find_state(e, cur);
        if (!s) break;
        if (s->on_entry) s->on_entry(e->ctx);
        if (s->initial_child != HSM_ID_INVALID) {
            cur = s->initial_child;
        } else {
            break;
        }
    }
    e->regions[region].active = cur;
}

/* exit from leaf `start` up to (not including) `stop` */
static void exit_to(hsm_engine_t* e, uint8_t region, hsm_state_id_t start, hsm_state_id_t stop)
{
    hsm_state_id_t cur = start;
    while (cur != stop && cur != HSM_ID_INVALID) {
        record_history_on_exit(e, region, cur);
        const hsm_state_t* s = find_state(e, cur);
        if (s && s->on_exit) s->on_exit(e->ctx);
        cur = parent_of(e, cur);
    }
}

/* resolve history pseudo-target */
static hsm_state_id_t resolve_target(hsm_engine_t* e, uint8_t region, hsm_state_id_t tgt)
{
    if (tgt == HSM_TO_HISTORY) {
        if (e->regions[region].history_set)
            return e->regions[region].history;
        /* fall back to region initial if no history recorded */
        return e->regions[region].initial;
    }
    return tgt;
}

/* ---- public API ---- */
cfw_err_t hsm_init(hsm_engine_t* e,
                   const hsm_state_t* states, uint16_t state_count,
                   const hsm_transition_t* transitions, uint16_t trans_count,
                   void* ctx)
{
    if (!e || !states || state_count == 0) return CFW_ERR_PARAM;
    e->states = states;
    e->state_count = state_count;
    e->transitions = transitions;
    e->trans_count = trans_count;
    e->ctx = ctx;
    e->region_count = 0;
    e->last_event_handled = false;
    for (uint8_t r = 0; r < CFW_HSM_MAX_REGIONS; r++) {
        e->regions[r].region = r;
        e->regions[r].initial = HSM_ID_INVALID;
        e->regions[r].active = HSM_ID_INVALID;
        e->regions[r].history = HSM_ID_INVALID;
        e->regions[r].history_set = false;
    }
    return CFW_OK;
}

cfw_err_t hsm_region_add(hsm_engine_t* e, uint8_t region, hsm_state_id_t initial)
{
    if (!e || region >= CFW_HSM_MAX_REGIONS) return CFW_ERR_PARAM;
    if (e->region_count >= CFW_HSM_MAX_REGIONS) return CFW_ERR_NOMEM;
    e->regions[e->region_count].region = region;
    e->regions[e->region_count].initial = initial;
    e->regions[e->region_count].active = HSM_ID_INVALID;
    e->regions[e->region_count].history = HSM_ID_INVALID;
    e->regions[e->region_count].history_set = false;
    e->region_count++;
    return CFW_OK;
}

cfw_err_t hsm_start(hsm_engine_t* e)
{
    if (!e || e->region_count == 0) return CFW_ERR_UNINIT;
    for (uint8_t r = 0; r < e->region_count; r++) {
        if (e->regions[r].initial == HSM_ID_INVALID) return CFW_ERR_UNINIT;
        enter_state(e, r, e->regions[r].initial);
    }
    return CFW_OK;
}

static void dispatch_region(hsm_engine_t* e, uint8_t r, cfw_event_type_t ev)
{
    hsm_state_id_t start = e->regions[r].active;
    if (start == HSM_ID_INVALID) return;

    /* bubble up from active leaf to find a state with a matching transition */
    hsm_state_id_t src = start;
    const hsm_transition_t* hit = NULL;
    while (src != HSM_ID_INVALID) {
        for (uint16_t i = 0; i < e->trans_count; i++) {
            const hsm_transition_t* t = &e->transitions[i];
            if (t->state == src && t->event == ev) {
                if (t->guard == NULL || t->guard(e->ctx)) {
                    hit = t;
                    goto found;
                }
            }
        }
        src = parent_of(e, src);
    }
    return; /* unhandled in this region */

found:
    (void)0;
    hsm_state_id_t s = src;                 /* transition declared at s */
    hsm_state_id_t tgt = resolve_target(e, r, hit->target);
    hsm_state_id_t common = lca(e, s, tgt);

    /* exit active leaf up to (exclusive) LCA */
    exit_to(e, r, start, common);
    /* transition action */
    if (hit->action) hit->action(e->ctx);
    /* enter target (composite default-child chain) */
    enter_state(e, r, tgt);
    e->last_event_handled = true;
}

void hsm_dispatch(hsm_engine_t* e, cfw_event_type_t ev)
{
    if (!e) return;
    e->last_event_handled = false;
    for (uint8_t r = 0; r < e->region_count; r++) {
        dispatch_region(e, r, ev);
    }
}

hsm_state_id_t hsm_active_state(const hsm_engine_t* e, uint8_t region)
{
    if (!e || region >= e->region_count) return HSM_ID_INVALID;
    return e->regions[region].active;
}

bool hsm_is_in(const hsm_engine_t* e, uint8_t region, hsm_state_id_t state)
{
    if (!e || region >= e->region_count) return false;
    hsm_state_id_t cur = e->regions[region].active;
    return is_ancestor_or_self(e, cur, state);
}

void hsm_region_components(const hsm_engine_t* e, uint8_t region,
                           uint8_t* top_state, uint8_t* sub_state)
{
    if (!e || region >= e->region_count) { *top_state = 0; *sub_state = 0; return; }
    hsm_state_id_t leaf = e->regions[region].active;
    hsm_state_id_t top = leaf;
    while (parent_of(e, top) != HSM_ID_INVALID) top = parent_of(e, top);
    *top_state = HSM_TOP(top);
    *sub_state = HSM_SUB(leaf);
}

uint16_t hsm_encode_active(const hsm_engine_t* e, uint8_t region)
{
    if (!e || region >= e->region_count) return CFW_STATE_UNINIT;
    uint8_t top, sub;
    hsm_region_components(e, region, &top, &sub);
    return cfw_state_encode(region, top, sub);
}
