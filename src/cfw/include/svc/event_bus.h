/* XLPS2-Alpha CFW — publish/subscribe event bus (L2)
 *
 * Static pool, NO malloc. Two historical止血 items are addressed here:
 *
 *  P0-1  evt_unsubscribe(sub_id)
 *        Historical bug: unsubscribing by subscription handle did not reliably
 *        remove the right entry (off-by-one / stale pointer / only-first-match),
 *        leaking callbacks and causing double-delivery after re-subscribe.
 *        Fix: subscriptions are keyed by a unique auto-assigned handle;
 *        evt_unsubscribe() deactivates EVERY active entry owning that handle
 *        and clears its payload reference, making re-use safe.
 *
 *  P0-2  payload >= 1024B
 *        Historical bug: payload copy/store capped below the ADR-005
 *        CHUNK_SIZE (1024), silently truncating OTA data chunks.
 *        Fix: payload slots are CFW_EVENT_PAYLOAD_MAX (=1024) bytes each;
 *        publish stores the FULL payload (memcpy up to len) and delivers the
 *        exact byte range to every subscriber. Lengths > MAX are rejected.
 */
#ifndef SVC_EVENT_BUS_H
#define SVC_EVENT_BUS_H

#include <stdint.h>
#include <stdbool.h>
#include "common/cfw_config.h"
#include "common/cfw_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*evt_handler_t)(cfw_event_type_t ev, evt_sub_id_t sub_id,
                              const void* payload, uint16_t len, void* ctx);

typedef struct {
    bool            active;
    cfw_event_type_t event;
    evt_sub_id_t    handle;       /* unique subscription handle (P0-1) */
    evt_handler_t   handler;
    void*           ctx;
} evt_subscriber_t;

typedef struct {
    evt_subscriber_t subs[CFW_EVENT_MAX_SUBSCRIBERS];
    uint8_t          count;             /* high-water mark of slots used */
    evt_sub_id_t     next_handle;       /* monotonic handle allocator */
    /* static payload pool (P0-2): in-flight slots, no malloc */
    uint8_t          payload_pool[CFW_EVENT_PAYLOAD_SLOTS][CFW_EVENT_PAYLOAD_MAX];
    uint8_t          payload_busy[CFW_EVENT_PAYLOAD_SLOTS];
} evt_bus_t;

cfw_err_t evt_init(evt_bus_t* bus);
evt_sub_id_t evt_subscribe(evt_bus_t* bus, cfw_event_type_t ev, evt_handler_t h, void* ctx);
cfw_err_t evt_unsubscribe(evt_bus_t* bus, evt_sub_id_t handle);   /* P0-1 */
cfw_err_t evt_unsubscribe_event(evt_bus_t* bus, cfw_event_type_t ev, evt_handler_t h);

/* Publish synchronously: copies the full payload (<= CFW_EVENT_PAYLOAD_MAX)
 * into a pool slot and delivers to all matching subscribers. A NULL payload
 * with len==0 is allowed (event-only). Returns CFW_ERR_RANGE if len too big. */
cfw_err_t evt_publish(evt_bus_t* bus, cfw_event_type_t ev,
                      const void* payload, uint16_t len);

/* Deferred publish from ISR context: enqueues; evt_drain_isr() flushes in
 * task context. Keeps ISRs minimal. */
cfw_err_t evt_publish_from_isr(evt_bus_t* bus, cfw_event_type_t ev,
                               const void* payload, uint16_t len);
void      evt_drain_isr(evt_bus_t* bus);

uint8_t   evt_subscriber_count(const evt_bus_t* bus);

#ifdef __cplusplus
}
#endif
#endif /* SVC_EVENT_BUS_H */
