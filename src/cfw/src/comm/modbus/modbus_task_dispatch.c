/* XLPS2-Alpha CFW — ADR-004 task dispatch implementation */
#include "comm/modbus/modbus_task_dispatch.h"
#include "comm/modbus/modbus_rtu.h"

static uint16_t rd_u16(const uint8_t* p) { return (uint16_t)((p[0] << 8) | p[1]); }
static int32_t  rd_i32(const uint8_t* p) { return (int32_t)(((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]); }

cfw_err_t modbus_handle_task_dispatch(const uint8_t* pdu, uint16_t pdu_len, evt_bus_t* bus)
{
    if (pdu_len < 7u) return CFW_ERR_PROTOCOL;        /* func+addr(2)+quant(2)+bc(1)+>=1 */
    if (pdu[0] != 0x10) return CFW_ERR_PROTOCOL;       /* only FC=0x10 */

    uint16_t start = rd_u16(&pdu[1]);
    uint16_t quant = rd_u16(&pdu[3]);
    uint8_t  bc    = pdu[5];
    if (start != MODBUS_TASK_BASE) return CFW_ERR_PARAM;
    if (bc != (quant * 2u)) return CFW_ERR_PROTOCOL;
    if (pdu_len < (uint16_t)(6u + bc)) return CFW_ERR_PROTOCOL;

    const uint8_t* regs = &pdu[6];
    if (quant < 6u) return CFW_ERR_PARAM;             /* need 6 registers */

    cfw_task_dispatch_t task;
    task.task_id           = (uint32_t)rd_u16(&regs[0]) << 16 | rd_u16(&regs[2]); /* 0x2000-0x2001 */
    task.task_type         = (cfw_task_type_t)rd_u16(&regs[4]);                    /* 0x2002 */
    task.task_target_pos_mm= rd_i32(&regs[6]);                                       /* 0x2003-0x2004 */
    task.task_axis         = regs[10];                                               /* 0x2005 */
    task.crc16             = modbus_crc16(pdu, pdu_len);

    return evt_publish(bus, EV_TASK_RECEIVED, &task, sizeof(task));
}
