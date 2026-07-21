/* XLPS2-Alpha CFW — L1 IComm interface (CAN/FDCAN + RS485 UART)
 *
 * Internal servo bus = CANopen (CAN). Local HMI/sensor gateway = RS485 Modbus
 * RTU. Both go through this interface; the upper layers never see a register. */
#ifndef HAL_COMM_H
#define HAL_COMM_H

#include <stdint.h>
#include "common/cfw_errors.h"

#ifdef __cplusplus
extern "C" {
#endif

/* channel selector */
typedef enum {
    HAL_CHAN_CAN  = 0,   /* internal CANopen servo bus */
    HAL_CHAN_RS485 = 1   /* local Modbus RTU (laser/HMI gateway) */
} hal_chan_t;

typedef struct hal_comm_ops {
    cfw_err_t (*can_send)(void* dev, uint32_t cob_id, const uint8_t* data, uint8_t len);
    cfw_err_t (*can_recv)(void* dev, uint32_t* cob_id, uint8_t* data, uint8_t* len);
    cfw_err_t (*uart_send)(void* dev, hal_chan_t ch, const uint8_t* data, uint16_t len);
    cfw_err_t (*uart_recv)(void* dev, hal_chan_t ch, uint8_t* data, uint16_t* len);
    /* register an ISR/DMA callback that pushes bytes into a ring (see svc/ringbuf) */
    cfw_err_t (*uart_set_rx_cb)(void* dev, hal_chan_t ch, void (*cb)(uint8_t b, void* ctx), void* ctx);
} hal_comm_ops_t;

typedef struct {
    void*              dev;
    const hal_comm_ops_t* ops;
} hal_comm_t;

#ifdef __cplusplus
}
#endif
#endif /* HAL_COMM_H */
