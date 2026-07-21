/* XLPS2-Alpha CFW — FreeRTOS task definitions */
#include "sys/system.h"
#include "hal/hal.h"
#include "comm/modbus/modbus_rtu.h"
#include "comm/modbus/modbus_task_dispatch.h"
#include "svc/ringbuf.h"
#include "FreeRTOS.h"
#include "task.h"

/* UART RX ring (RS485 Modbus). Fed by HAL_UART_RxCpltCallback. */
static uint8_t g_uart_buf[2048];
static ringbuf_t g_uart_rb;
static uint32_t g_last_byte_ms = 0;

static void modbus_task_dispatch_bridge(uint8_t slave, uint8_t func,
                                        const uint8_t* pdu, uint16_t pdu_len, void* ctx);

/* Called from HAL_UART_RxCpltCallback (ISR context) via registered cb. */
void cfw_uart_byte_feed(uint8_t b, void* ctx)
{
    (void)ctx;
    ringbuf_push(&g_uart_rb, b);
    g_last_byte_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;
}

/* ---- HSM / control tick (10 ms) ---- */
static void HsmTask(void* arg)
{
    (void)arg;
    uint32_t last = 0;
    for (;;) {
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        app_tick(&g_rt, now);
        if (now - last >= CFW_TELEMETRY_PERIOD_MS) { last = now; }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/* ---- Comm: drain RS485 ring, parse Modbus, dispatch (ADR-004) ---- */
static void CommTask(void* arg)
{
    (void)arg;
    static uint8_t frame[256];
    for (;;) {
        /* frame complete when 3.5-char gap elapsed (>=4 ms @ 115200) */
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        if (!ringbuf_is_empty(&g_uart_rb) && (now - g_last_byte_ms) >= 4) {
            uint16_t n = ringbuf_pop_n(&g_uart_rb, frame, (uint16_t)sizeof(frame));
            modbus_rtu_process(frame, n, modbus_task_dispatch_bridge, &g_rt);
            evt_drain_isr(&g_rt.evt);    /* flush ISR-deferred events */
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

/* bridge Modbus PDU -> ADR-004 task dispatch (passed as mb_dispatch_t) */
static void modbus_task_dispatch_bridge(uint8_t slave, uint8_t func,
                                        const uint8_t* pdu, uint16_t pdu_len, void* ctx)
{
    (void)slave;
    if (func == 0x10) modbus_handle_task_dispatch(pdu, pdu_len, &((cfw_runtime_t*)ctx)->evt);
}

/* ---- Telemetry publisher (100 ms) ---- */
static void TelemTask(void* arg)
{
    (void)arg;
    for (;;) {
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        app_sample_telemetry(&g_rt, now);
        /* publish to MQTT gateway over RS485/UART (contract: telemetry topic) */
        vTaskDelay(pdMS_TO_TICKS(CFW_TELEMETRY_PERIOD_MS));
    }
}

/* ---- OTA health watchdog (1 s) ---- */
static void OtaTask(void* arg)
{
    (void)arg;
    for (;;) {
        ota_local_health_tick(&g_ota);   /* auto-rollback if unconfirmed */
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* ---- Hardware watchdog petter ---- */
static void WatchdogTask(void* arg)
{
    (void)arg;
    for (;;) {
        iwdg_refresh();
        vTaskDelay(pdMS_TO_TICKS(CFW_WATCHDOG_TIMEOUT_MS / 2));
    }
}

void create_tasks(void)
{
    ringbuf_init(&g_uart_rb, g_uart_buf, (uint16_t)sizeof(g_uart_buf));

    /* register RS485 RX callback feeding the Modbus ring buffer */
    const hal_comm_t* c = hal_comm_stm32();
    if (c->ops->uart_set_rx_cb) c->ops->uart_set_rx_cb(c->dev, HAL_CHAN_RS485, cfw_uart_byte_feed, NULL);

    xTaskCreate(HsmTask,      "hsm",   512, NULL, 4, NULL);
    xTaskCreate(CommTask,     "comm",  512, NULL, 3, NULL);
    xTaskCreate(TelemTask,    "telem", 512, NULL, 2, NULL);
    xTaskCreate(OtaTask,      "ota",   384, NULL, 2, NULL);
    xTaskCreate(WatchdogTask, "wdog",  256, NULL, 5, NULL);
}
