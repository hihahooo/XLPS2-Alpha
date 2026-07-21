/* Host test: event bus — P0-1 (evt_unsubscribe by sub_id) and
 * P0-2 (payload >= 1024B, ADR-005 CHUNK_SIZE). */
#include "cfw_test.h"
#include "svc/event_bus.h"
#include <string.h>

int g_tests = 0, g_fail = 0;

static int  hits_a = 0, hits_b = 0, last_len = 0, payload_ok = 0;

static void h_a(cfw_event_type_t ev, evt_sub_id_t id, const void* p, uint16_t len, void* ctx)
{
    (void)ev; (void)id; (void)ctx;
    hits_a++; last_len = len;
    if (len == 1024) {
        const uint8_t* b = (const uint8_t*)p;
        payload_ok = (b[0] == 0xAA && b[1023] == 0x55) ? 1 : 0;
    }
}
static void h_b(cfw_event_type_t ev, evt_sub_id_t id, const void* p, uint16_t len, void* ctx)
{
    (void)ev; (void)id; (void)p; (void)len; (void)ctx;
    hits_b++;
}

int main(void)
{
    evt_bus_t bus;
    TASSERT_EQ(evt_init(&bus), CFW_OK);

    evt_sub_id_t sa = evt_subscribe(&bus, EV_LOW_BATTERY, h_a, NULL);
    evt_sub_id_t sb = evt_subscribe(&bus, EV_LOW_BATTERY, h_b, NULL);
    TASSERT(sa != EVT_SUB_ID_INVALID);
    TASSERT(sb != EVT_SUB_ID_INVALID);
    TASSERT(sa != sb);                 /* handles are unique */
    TASSERT_EQ(evt_subscriber_count(&bus), 2);

    /* both delivered */
    TASSERT_EQ(evt_publish(&bus, EV_LOW_BATTERY, NULL, 0), CFW_OK);
    TASSERT_EQ(hits_a, 1);
    TASSERT_EQ(hits_b, 1);

    /* ---- P0-1: unsubscribe ONLY sa; h_a must stop, h_b continues ---- */
    TASSERT_EQ(evt_unsubscribe(&bus, sa), CFW_OK);
    TASSERT_EQ(evt_subscriber_count(&bus), 1);
    TASSERT_EQ(evt_publish(&bus, EV_LOW_BATTERY, NULL, 0), CFW_OK);
    TASSERT_EQ(hits_a, 1);             /* unchanged */
    TASSERT_EQ(hits_b, 2);             /* still delivered */

    /* double unsubscribe is a no-op (no stale slot, no double effect) */
    TASSERT_EQ(evt_unsubscribe(&bus, sa), CFW_ERR_NOT_FOUND);

    /* re-subscribe a fresh handle; must NOT double-deliver through old slot */
    evt_sub_id_t sa2 = evt_subscribe(&bus, EV_LOW_BATTERY, h_a, NULL);
    TASSERT(sa2 != EVT_SUB_ID_INVALID);
    TASSERT_EQ(evt_publish(&bus, EV_LOW_BATTERY, NULL, 0), CFW_OK);
    TASSERT_EQ(hits_a, 2);
    TASSERT_EQ(hits_b, 3);

    /* ---- P0-2: 1024-byte payload delivered intact ---- */
    uint8_t big[1024];
    big[0] = 0xAA; big[1023] = 0x55;
    for (int i = 1; i < 1023; i++) big[i] = (uint8_t)i;
    payload_ok = 0;
    TASSERT_EQ(evt_publish(&bus, EV_OTA_DATA, big, 1024), CFW_OK);
    TASSERT_EQ(last_len, 1024);
    TASSERT_EQ(payload_ok, 1);

    /* >1024 rejected (never truncated) */
    uint8_t over[1025];
    TASSERT_EQ(evt_publish(&bus, EV_OTA_DATA, over, 1025), CFW_ERR_RANGE);

    printf("[event_bus] %d assertions, %d failures\n", g_tests, g_fail);
    return g_fail ? 1 : 0;
}
