/* XLPS2-Alpha CFW — STM32 IComm (FDCAN servo bus + RS485 Modbus UART)
 * ISR/DMA RX bytes are forwarded to a registered callback (svc/ringbuf) so
 * the upper Modbus parser runs in task context (minimal ISR). */
#include "hal/hal.h"
#include "stm32h7xx_hal.h"

extern FDCAN_HandleTypeDef hfdcan1;
extern UART_HandleTypeDef   huart_rs485;

typedef struct { void (*cb)(uint8_t, void*); void* ctx; } rs485_rx_t;
static rs485_rx_t g_rx = { NULL, NULL };

static cfw_err_t c_can_send(void* d, uint32_t cob_id, const uint8_t* data, uint8_t len)
{
    (void)d;
    FDCAN_TxHeaderTypeDef tx = {0};
    tx.Identifier = cob_id; tx.IdType = FDCAN_STANDARD_ID; tx.TxFrameType = FDCAN_DATA_FRAME;
    tx.DataLength = (uint32_t)((len <= 8) ? (len << 16) : FDCAN_DLC_BYTES_8); /* simplified */
    return (HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1, &tx, (uint8_t*)data) == HAL_OK)
           ? CFW_OK : CFW_ERR_HAL;
}
static cfw_err_t c_can_recv(void* d, uint32_t* cob_id, uint8_t* data, uint8_t* len)
{
    (void)d;
    FDCAN_RxHeaderTypeDef rx = {0};
    if (HAL_FDCAN_GetRxMessage(&hfdcan1, FDCAN_RX_FIFO0, &rx, data) != HAL_OK) return CFW_ERR_HAL;
    *cob_id = rx.Identifier; *len = (uint8_t)(rx.DataLength >> 16);
    return CFW_OK;
}
static cfw_err_t c_uart_send(void* d, hal_chan_t ch, const uint8_t* data, uint16_t len)
{
    (void)d; (void)ch;
    return (HAL_UART_Transmit(&huart_rs485, (uint8_t*)data, len, 100) == HAL_OK) ? CFW_OK : CFW_ERR_HAL;
}
static cfw_err_t c_uart_recv(void* d, hal_chan_t ch, uint8_t* data, uint16_t* len)
{
    (void)d; (void)ch; (void)data; (void)len;
    return CFW_ERR_BUSY; /* RX is interrupt-driven via callback */
}
static cfw_err_t c_uart_set_rx_cb(void* d, hal_chan_t ch, void (*cb)(uint8_t, void*), void* ctx)
{
    (void)d; (void)ch;
    g_rx.cb = cb; g_rx.ctx = ctx;
    return CFW_OK;
}

/* UART RX ISR hook: forward each byte to the registered callback. */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef* hu)
{
    if (hu == &huart_rs485 && g_rx.cb) {
        /* byte already captured by DMA/IT into a 1-byte buffer before re-arming */
        uint8_t b = (uint8_t)(hu->Instance->RDR & 0xFFu);
        g_rx.cb(b, g_rx.ctx);
    }
}

static const hal_comm_ops_t C_OPS = { c_can_send, c_can_recv, c_uart_send, c_uart_recv, c_uart_set_rx_cb };
static hal_comm_t C_INST = { NULL, &C_OPS };

const hal_comm_t* hal_comm_stm32(void) { return &C_INST; }
