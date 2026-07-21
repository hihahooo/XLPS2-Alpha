/* XLPS2-Alpha CFW — compile-time configuration (SSOT-aligned constants)
 *
 * All runtime pools are static (no malloc). Sizes are derived from the SSOT:
 *  - CFW_EVENT_PAYLOAD_MAX = 1024 == ADR-005 CHUNK_SIZE  (P0-2: payloads >= 1024B)
 *  - OTA constants pulled verbatim from ADR-005
 */
#ifndef CFW_CONFIG_H
#define CFW_CONFIG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- HSM engine limits ---- */
#define CFW_HSM_MAX_REGIONS      3u      /* 主业务 / 能源 / 安全 (ADR-003) */
#define CFW_HSM_MAX_STATES       160u
#define CFW_HSM_MAX_TRANSITIONS  320u

/* ---- Event bus (L2) limits ---- */
#define CFW_EVENT_MAX_SUBSCRIBERS 48u
#define CFW_EVENT_PAYLOAD_MAX     1024u  /* P0-2: must carry >= ADR-005 CHUNK_SIZE */
#define CFW_EVENT_PAYLOAD_SLOTS   4u     /* in-flight payload slots (no malloc) */
#define CFW_EVENT_QUEUE_DEPTH     16u    /* deferred events posted from ISR */

/* ---- Telemetry / timing ---- */
#define CFW_TELEMETRY_PERIOD_MS   100u
#define CFW_HEARTBEAT_PERIOD_MS   1000u
#define CFW_WATCHDOG_TIMEOUT_MS   1500u   /* IWDG, must exceed worst task tick */

/* ---- ADR-005 OTA A/B dual partition (verbatim from SSOT) ---- */
#define OTA_SLOT_A_BASE     0x08020000u
#define OTA_SLOT_B_BASE     0x08100000u
#define OTA_SLOT_CAPACITY   0x000E0000u   /* <= 0.9MB per partition */
#define OTA_FLAG_SECTOR     0x081E0000u
#define OTA_FLAG_PRIMARY    0x000u        /* primary backup offset */
#define OTA_FLAG_SECONDARY  0x200u        /* secondary backup offset */
#define OTA_CHUNK_SIZE      1024u         /* ADR-005 CHUNK_SIZE; P0-2 boundary */
#define OTA_HEALTH_WINDOW_S 300u          /* ADR-005 HEALTH_WINDOW_S */
#define OTA_FLAG_CRC32_LEN  4u

/* ---- Interference library ---- */
#define CFW_INTERFERENCE_MAX_POINTS 256u

/* ---- Version (firmware). SSOT fw_version string. ---- */
#define CFW_FW_VERSION       "XLPS2-CFW-0.1.0"
#define CFW_PARAM_VERSION    1u           /* monotonic; ADR-007 */
#define CFW_SMDL_VERSION     "SMDL-0.1.0"

/* ---- Board / MCU identity (EHW provides pin map; CFW stays pin-agnostic) ---- */
#define CFW_MCU_ID           "STM32H743IIT6"

#ifdef __cplusplus
}
#endif
#endif /* CFW_CONFIG_H */
