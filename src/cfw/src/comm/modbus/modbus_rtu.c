/* XLPS2-Alpha CFW — Modbus RTU implementation */
#include "comm/modbus/modbus_rtu.h"

uint16_t modbus_crc16(const uint8_t* data, uint16_t len)
{
    uint16_t crc = 0xFFFFu;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 1u) ? (uint16_t)((crc >> 1) ^ 0xA001u) : (uint16_t)(crc >> 1);
    }
    return crc;
}

cfw_err_t modbus_rtu_process(const uint8_t* frame, uint16_t len,
                             mb_dispatch_t cb, void* ctx)
{
    if (len < 4u) return CFW_ERR_PROTOCOL;
    uint16_t crc_calc = modbus_crc16(frame, (uint16_t)(len - 2u));
    uint16_t crc_recv = (uint16_t)((frame[len - 1] << 8) | frame[len - 2]);
    if (crc_calc != crc_recv) return CFW_ERR_CRC;

    uint8_t  slave = frame[0];
    uint8_t  func  = frame[1];
    const uint8_t* pdu = &frame[2];
    uint16_t pdu_len = (uint16_t)(len - 4u);
    if (cb) cb(slave, func, pdu, pdu_len, ctx);
    return CFW_OK;
}
