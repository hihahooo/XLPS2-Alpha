/* XLPS2-Alpha CFW — RS485 Modbus RTU parser (local HMI/sensor gateway) */
#ifndef COMM_MODBUS_RTU_H
#define COMM_MODBUS_RTU_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Modbus RTU CRC-16 (poly 0x8005, init 0xFFFF) */
uint16_t modbus_crc16(const uint8_t* data, uint16_t len);

/* Called with a COMPLETE frame [slave][func][pdu...][crc_lo][crc_hi].
 * Validates CRC and invokes cb(slave, func, pdu, pdu_len, ctx). */
typedef void (*mb_dispatch_t)(uint8_t slave, uint8_t func,
                              const uint8_t* pdu, uint16_t pdu_len, void* ctx);
cfw_err_t modbus_rtu_process(const uint8_t* frame, uint16_t len,
                             mb_dispatch_t cb, void* ctx);

#ifdef __cplusplus
}
#endif
#endif /* COMM_MODBUS_RTU_H */
