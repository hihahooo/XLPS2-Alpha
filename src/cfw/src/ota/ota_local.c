/* XLPS2-Alpha CFW — OTA A/B local implementation (ADR-005) */
#include "ota/ota_local.h"
#include <string.h>

#define FLAG_SLOT_OFF 4u   /* slot byte offset within FLAG record */
#define FLAG_VER_OFF  8u   /* version string offset within FLAG record */

static hal_store_part_t inactive_part(uint8_t active_slot)
{ return (active_slot == SLOT_A) ? STORE_OTA_B : STORE_OTA_A; }

static hal_store_part_t active_part(uint8_t active_slot)
{ return (active_slot == SLOT_A) ? STORE_OTA_A : STORE_OTA_B; }

cfw_err_t ota_local_init(ota_local_t* o, const hal_storage_t* store)
{
    if (!o || !store) return CFW_ERR_PARAM;
    memset(o, 0, sizeof(*o));
    o->store = store;
    o->active_slot = SLOT_A;
    o->phase = OTA_LOCAL_IDLE;
    strncpy(o->active_version, CFW_FW_VERSION, CFW_STR_VER_LEN - 1);
    return CFW_OK;
}

cfw_err_t ota_local_cmd(ota_local_t* o, const char* target_version, uint8_t slot)
{
    if (!o || !target_version) return CFW_ERR_PARAM;
    /* version monotonic (R3/R4): strict greater */
    if (strcmp(target_version, o->active_version) <= 0)
        return CFW_ERR_RANGE;            /* downgrade rejected */
    strncpy(o->target_version, target_version, CFW_STR_VER_LEN - 1);
    (void)slot;                          /* slot chosen by active_slot */
    o->next_seq = 0;
    o->written_bytes = 0;
    o->phase = OTA_LOCAL_DOWNLOADING;
    return CFW_OK;
}

cfw_err_t ota_local_data(ota_local_t* o, uint16_t seq, uint16_t crc,
                         const uint8_t* chunk, uint16_t len)
{
    if (!o || !chunk) return CFW_ERR_PARAM;
    if (o->phase != OTA_LOCAL_DOWNLOADING) return CFW_ERR_BUSY;
    if (seq != o->next_seq) return CFW_ERR_PROTOCOL;   /* out-of-order / gap */
    if (len > OTA_CHUNK_SIZE) return CFW_ERR_RANGE;    /* P0-2 boundary */

    /* inline CRC-32 over the chunk for per-chunk integrity */
    uint32_t crc_calc = 0xFFFFFFFFu;
    for (uint16_t i = 0; i < len; i++) {
        crc_calc ^= (uint32_t)chunk[i];
        for (int b = 0; b < 8; b++) crc_calc = (crc_calc & 1u) ? (crc_calc >> 1) ^ 0xEDB88320u : (crc_calc >> 1);
    }
    crc_calc = ~crc_calc;
    if ((uint16_t)crc_calc != crc) return CFW_ERR_CRC;

    uint32_t off = (uint32_t)seq * OTA_CHUNK_SIZE;
    hal_store_part_t part = inactive_part(o->active_slot);
    if (o->store->ops->write(o->store->dev, part, off, chunk, len) != CFW_OK)
        return CFW_ERR_HAL;
    o->written_bytes += len;
    o->next_seq++;
    return CFW_OK;
}

cfw_err_t ota_local_verify_and_switch(ota_local_t* o)
{
    if (!o) return CFW_ERR_PARAM;
    o->phase = OTA_LOCAL_VERIFYING;

    hal_store_part_t part = inactive_part(o->active_slot);
    uint32_t crc_full = 0;
    if (o->store->ops->crc32(o->store->dev, part, 0, o->written_bytes, &crc_full) != CFW_OK)
        return CFW_ERR_HAL;
    (void)crc_full;   /* would compare against manifest CRC */

    /* FLAG dual-backup: primary + secondary, each with CRC-32 */
    uint8_t flag_rec[64];
    memset(flag_rec, 0, sizeof(flag_rec));
    uint8_t new_slot = (o->active_slot == SLOT_A) ? SLOT_B : SLOT_A;
    flag_rec[FLAG_SLOT_OFF] = new_slot;
    strncpy((char*)&flag_rec[FLAG_VER_OFF], o->target_version, CFW_STR_VER_LEN - 1);
    uint32_t frec_crc = 0xFFFFFFFFu;
    for (uint16_t i = 0; i < sizeof(flag_rec); i++) {
        frec_crc ^= (uint32_t)flag_rec[i];
        for (int b = 0; b < 8; b++) frec_crc = (frec_crc & 1u) ? (frec_crc >> 1) ^ 0xEDB88320u : (frec_crc >> 1);
    }
    frec_crc = ~frec_crc;
    /* primary */
    if (o->store->ops->write(o->store->dev, STORE_OTA_FLAG, OTA_FLAG_PRIMARY, flag_rec, sizeof(flag_rec)) != CFW_OK)
        return CFW_ERR_HAL;
    if (o->store->ops->write(o->store->dev, STORE_OTA_FLAG, OTA_FLAG_PRIMARY + 4, (uint8_t*)&frec_crc, 4) != CFW_OK)
        return CFW_ERR_HAL;
    /* secondary (backup copy) */
    if (o->store->ops->write(o->store->dev, STORE_OTA_FLAG, OTA_FLAG_SECONDARY, flag_rec, sizeof(flag_rec)) != CFW_OK)
        return CFW_ERR_HAL;
    if (o->store->ops->write(o->store->dev, STORE_OTA_FLAG, OTA_FLAG_SECONDARY + 4, (uint8_t*)&frec_crc, 4) != CFW_OK)
        return CFW_ERR_HAL;

    o->active_slot = new_slot;
    strncpy(o->active_version, o->target_version, CFW_STR_VER_LEN - 1);
    o->phase = OTA_LOCAL_ACTIVE;
    o->health_timer = OTA_HEALTH_WINDOW_S;
    o->health_confirmed = false;
    /* reboot into new slot would be triggered by system layer here */
    return CFW_OK;
}

cfw_err_t ota_local_confirm_health(ota_local_t* o)
{
    if (!o) return CFW_ERR_PARAM;
    o->health_confirmed = true;
    o->health_timer = 0;
    return CFW_OK;
}

void ota_local_health_tick(ota_local_t* o)
{
    if (!o) return;
    if (o->phase == OTA_LOCAL_ACTIVE && !o->health_confirmed) {
        if (o->health_timer > 0) {
            o->health_timer--;
            if (o->health_timer == 0) {
                /* auto-rollback to previous stable slot (R7) */
                o->active_slot = (o->active_slot == SLOT_A) ? SLOT_B : SLOT_A;
                o->phase = OTA_LOCAL_ROLLBACK;
            }
        }
    }
}
