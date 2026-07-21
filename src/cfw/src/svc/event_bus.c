/* XLPS2-Alpha CFW — event bus implementation (P0-1 unsubscribe, P0-2 payload)
 * Static pool, no malloc. See event_bus.h for the止血 rationale. */
#include "svc/event_bus.h"
#include <string.h>

#define EVT_SUB_ID_FIRST 1u   /* handle 0 reserved as invalid */

cfw_err_t evt_init(evt_bus_t* bus)
{
    if (!bus) return CFW_ERR_PARAM;
    memset(bus, 0, sizeof(*bus));
    bus->count = 0;
    bus->next_handle = EVT_SUB_ID_FIRST;
    for (uint8_t i = 0; i < CFW_EVENT_PAYLOAD_SLOTS; i++) {
        bus->payload_busy[i] = 0;
    }
    return CFW_OK;
}

evt_sub_id_t evt_subscribe(evt_bus_t* bus, cfw_event_type_t ev,
                           evt_handler_t h, void* ctx)
{
    if (!bus || !h || ev >= EV_COUNT) return EVT_SUB_ID_INVALID;
    /* find a free slot */
    for (uint8_t i = 0; i < CFW_EVENT_MAX_SUBSCRIBERS; i++) {
        if (!bus->subs[i].active) {
            bus->subs[i].active  = true;
            bus->subs[i].event   = ev;
            bus->subs[i].handler = h;
            bus->subs[i].ctx     = ctx;
            bus->subs[i].handle  = bus->next_handle++;
            if (bus->count < i + 1) bus->count = (uint8_t)(i + 1);
            if (bus->next_handle == 0) bus->next_handle = EVT_SUB_ID_FIRST; /* wrap guard */
            return bus->subs[i].handle;
        }
    }
    return EVT_SUB_ID_INVALID; /* pool exhausted */
}

/* P0-1 fix: deactivate EVERY active entry owning the handle (not just the
 * first match), and clear its callback so a later re-subscribe cannot
 * double-deliver through a stale slot. */
cfw_err_t evt_unsubscribe(evt_bus_t* bus, evt_sub_id_t handle)
{
    if (!bus || handle == EVT_SUB_ID_INVALID) return CFW_ERR_PARAM;
    bool removed = false;
    for (uint8_t i = 0; i < CFW_EVENT_MAX_SUBSCRIBERS; i++) {
        if (bus->subs[i].active && bus->subs[i].handle == handle) {
            bus->subs[i].active  = false;
            bus->subs[i].event   = EV_COUNT;
            bus->subs[i].handler = NULL;
            bus->subs[i].ctx     = NULL;
            bus->subs[i].handle  = EVT_SUB_ID_INVALID;
            removed = true;
        }
    }
    return removed ? CFW_OK : CFW_ERR_NOT_FOUND;
}

cfw_err_t evt_unsubscribe_event(evt_bus_t* bus, cfw_event_type_t ev, evt_handler_t h)
{
    if (!bus) return CFW_ERR_PARAM;
    bool removed = false;
    for (uint8_t i = 0; i < CFW_EVENT_MAX_SUBSCRIBERS; i++) {
        if (bus->subs[i].active && bus->subs[i].event == ev &&
            (h == NULL || bus->subs[i].handler == h)) {
            bus->subs[i].active  = false;
            bus->subs[i].event   = EV_COUNT;
            bus->subs[i].handler = NULL;
            bus->subs[i].ctx     = NULL;
            bus->subs[i].handle  = EVT_SUB_ID_INVALID;
            removed = true;
        }
    }
    return removed ? CFW_OK : CFW_ERR_NOT_FOUND;
}

/* deliver to all subscribers of `ev`, payload already stored in slot `slot` */
static void deliver_from_slot(evt_bus_t* bus, cfw_event_type_t ev,
                              uint8_t slot, uint16_t len)
{
    const uint8_t* p = (len > 0) ? bus->payload_pool[slot] : NULL;
    for (uint8_t i = 0; i < CFW_EVENT_MAX_SUBSCRIBERS; i++) {
        if (bus->subs[i].active && bus->subs[i].event == ev && bus->subs[i].handler) {
            bus->subs[i].handler(ev, bus->subs[i].handle, p, len, bus->subs[i].ctx);
        }
    }
}

static uint8_t acquire_slot(evt_bus_t* bus)
{
    for (uint8_t i = 0; i < CFW_EVENT_PAYLOAD_SLOTS; i++) {
        if (bus->payload_busy[i] == 0) {
            bus->payload_busy[i] = 1;
            return i;
        }
    }
    return 0xFFu;
}

cfw_err_t evt_publish(evt_bus_t* bus, cfw_event_type_t ev,
                      const void* payload, uint16_t len)
{
    if (!bus || ev >= EV_COUNT) return CFW_ERR_PARAM;
    if (len > CFW_EVENT_PAYLOAD_MAX) return CFW_ERR_RANGE;   /* P0-2 guard */
    if (len > 0 && payload == NULL) return CFW_ERR_PARAM;

    uint8_t slot = acquire_slot(bus);
    if (slot == 0xFFu) return CFW_ERR_NOMEM;

    if (len > 0) memcpy(bus->payload_pool[slot], payload, (size_t)len);
    deliver_from_slot(bus, ev, slot, len);
    bus->payload_busy[slot] = 0;
    return CFW_OK;
}

/* ---- ISR deferred path ---- */
typedef struct { cfw_event_type_t ev; uint8_t slot; uint16_t len; bool used; } evt_isr_t;
static evt_isr_t isr_q[CFW_EVENT_QUEUE_DEPTH];
static volatile uint8_t isr_wr = 0, isr_rd = 0, isr_cnt = 0;

cfw_err_t evt_publish_from_isr(evt_bus_t* bus, cfw_event_type_t ev,
                               const void* payload, uint16_t len)
{
    if (!bus || ev >= EV_COUNT) return CFW_ERR_PARAM;
    if (len > CFW_EVENT_PAYLOAD_MAX) return CFW_ERR_RANGE;   /* P0-2 guard */
    if (len > 0 && payload == NULL) return CFW_ERR_PARAM;
    if (isr_cnt >= CFW_EVENT_QUEUE_DEPTH) return CFW_ERR_NOMEM;

    uint8_t slot = acquire_slot(bus);
    if (slot == 0xFFu) return CFW_ERR_NOMEM;

    if (len > 0) memcpy(bus->payload_pool[slot], payload, (size_t)len);

    isr_q[isr_wr].ev   = ev;
    isr_q[isr_wr].slot = slot;
    isr_q[isr_wr].len  = len;
    isr_q[isr_wr].used = true;
    isr_wr = (uint8_t)((isr_wr + 1) % CFW_EVENT_QUEUE_DEPTH);
    isr_cnt++;
    return CFW_OK;
}

void evt_drain_isr(evt_bus_t* bus)
{
    while (isr_cnt > 0) {
        evt_isr_t* e = &isr_q[isr_rd];
        if (e->used) {
            deliver_from_slot(bus, e->ev, e->slot, e->len);
            bus->payload_busy[e->slot] = 0;
            e->used = false;
        }
        isr_rd = (uint8_t)((isr_rd + 1) % CFW_EVENT_QUEUE_DEPTH);
        isr_cnt--;
    }
}

uint8_t evt_subscriber_count(const evt_bus_t* bus)
{
    if (!bus) return 0;
    uint8_t n = 0;
    for (uint8_t i = 0; i < CFW_EVENT_MAX_SUBSCRIBERS; i++) {
        if (bus->subs[i].active) n++;
    }
    return n;
}
