/* XLPS2-Alpha CFW — L5 OTA A/B local receiver (SSOT: ADR-005)
 *
 * - Writes incoming chunks to the INACTIVE partition (never the running one).
 * - Version monotonic: target must be strictly greater than active (R3/R4).
 * - FLAG dual-backup (primary 0x000 / secondary 0x200, each CRC-32).
 * - Health window HEALTH_WINDOW_S=300s; if no confirmation -> auto-rollback.
 * - Chunk size == ADR-005 CHUNK_SIZE (1024) == CFW_EVENT_PAYLOAD_MAX (P0-2). */
#ifndef OTA_OTA_LOCAL_H
#define OTA_OTA_LOCAL_H

#include <stdint.h>
#include "common/cfw_config.h"
#include "common/cfw_types.h"
#include "hal/hal_storage.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    OTA_LOCAL_IDLE = 0,
    OTA_LOCAL_DOWNLOADING,
    OTA_LOCAL_FLASHING,
    OTA_LOCAL_VERIFYING,
    OTA_LOCAL_ACTIVE,
    OTA_LOCAL_ROLLBACK
} ota_local_phase_t;

typedef struct {
    const hal_storage_t* store;
    ota_local_phase_t    phase;
    uint8_t              active_slot;     /* SLOT_A / SLOT_B */
    char                 active_version[CFW_STR_VER_LEN];
    char                 target_version[CFW_STR_VER_LEN];
    uint32_t             next_seq;
    uint32_t             written_bytes;
    uint16_t             health_timer;     /* seconds remaining */
    bool                 health_confirmed;
} ota_local_t;

cfw_err_t ota_local_init(ota_local_t* o, const hal_storage_t* store);
/* Begin a session: monotonic version check; chooses inactive slot. */
cfw_err_t ota_local_cmd(ota_local_t* o, const char* target_version, uint8_t slot);
/* Store one chunk (seq + CRC). Returns CFW_ERR_CRC on mismatch. */
cfw_err_t ota_local_data(ota_local_t* o, uint16_t seq, uint16_t crc,
                         const uint8_t* chunk, uint16_t len);
/* Verify + write FLAG dual-backup + request reboot into new slot. */
cfw_err_t ota_local_verify_and_switch(ota_local_t* o);
/* Called by the device once healthy after switch. */
cfw_err_t ota_local_confirm_health(ota_local_t* o);
/* 1 Hz tick: counts down the health window; auto-rolls back on timeout. */
void       ota_local_health_tick(ota_local_t* o);

#ifdef __cplusplus
}
#endif
#endif /* OTA_OTA_LOCAL_H */
