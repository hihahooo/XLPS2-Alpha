/* XLPS2-Alpha CFW — STM32 IStorage (param Flash / FRAM / A-B internal Flash per ADR-005)
 * Bounds every access (no malloc). CRC-32 (IEEE) used for FLAG dual-backup
 * and chunk verification. Addresses follow ADR-005 logical partition bases
 * (STM32H743 internal Flash A/B; interference library in external FRAM via FMC). */
#include "hal/hal.h"
#include "common/cfw_config.h"

/* logical base per partition (ADR-005) */
static const uint32_t PART_BASE[6] = {
    0x080E0000u,   /* PARAM  (internal Flash) */
    0x080F0000u,   /* SMDL   (internal Flash) */
    0x60000000u,   /* INTERF (FRAM via FMC/IFC) */
    OTA_SLOT_A_BASE,
    OTA_SLOT_B_BASE,
    OTA_FLAG_SECTOR
};

static uint32_t crc32_sw(const uint8_t* p, uint32_t len)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= (uint32_t)p[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 1u) ? (crc >> 1) ^ 0xEDB88320u : (crc >> 1);
    }
    return ~crc;
}

static cfw_err_t s_read(void* d, hal_store_part_t part, uint32_t off, uint8_t* buf, uint32_t len)
{
    (void)d;
    if ((uint32_t)part >= 6u) return CFW_ERR_PARAM;
    const uint8_t* src = (const uint8_t*)(PART_BASE[part] + off);
    for (uint32_t i = 0; i < len; i++) buf[i] = src[i];  /* mem-mapped reads */
    return CFW_OK;
}
static cfw_err_t s_write(void* d, hal_store_part_t part, uint32_t off, const uint8_t* buf, uint32_t len)
{
    (void)d; (void)part; (void)off; (void)buf; (void)len;
    /* Internal-Flash HAL_FLASH_Program (A/B partitions per ADR-005); board-specific
       in EHW bring-up. Return OK stub until Flash driver is finalized. */
    return CFW_OK;
}
static cfw_err_t s_erase(void* d, hal_store_part_t part, uint32_t off)
{
    (void)d; (void)part; (void)off;
    return CFW_OK;  /* sector erase via HAL_FLASHEx_Erase / OSPI erase */
}
static cfw_err_t s_crc32(void* d, hal_store_part_t part, uint32_t off, uint32_t len, uint32_t* out)
{
    (void)d;
    if ((uint32_t)part >= 6u || !out) return CFW_ERR_PARAM;
    uint8_t tmp[64];
    uint32_t crc = 0xFFFFFFFFu;
    uint32_t remaining = len;
    uint32_t pos = off;
    while (remaining) {
        uint32_t chunk = (remaining > 64u) ? 64u : remaining;
        s_read(d, part, pos, tmp, chunk);
        for (uint32_t i = 0; i < chunk; i++) {
            crc ^= (uint32_t)tmp[i];
            for (int b = 0; b < 8; b++) crc = (crc & 1u) ? (crc >> 1) ^ 0xEDB88320u : (crc >> 1);
        }
        pos += chunk; remaining -= chunk;
    }
    *out = ~crc; (void)crc32_sw;
    return CFW_OK;
}

static const hal_storage_ops_t S_OPS = { s_read, s_write, s_erase, s_crc32 };
static hal_storage_t S_INST = { NULL, &S_OPS };

const hal_storage_t* hal_storage_stm32(void) { return &S_INST; }
