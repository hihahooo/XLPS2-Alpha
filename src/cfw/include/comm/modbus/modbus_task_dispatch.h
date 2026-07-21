/* XLPS2-Alpha CFW — ADR-004 task dispatch over Modbus RTU
 *
 * HMI/gateway sends FC=0x10 (write multiple registers) at base 0x2000:
 *   reg 0x2000-0x2001 : task_id        (uint32)
 *   reg 0x2002        : task_type      (1=walk/2=lift ...)  (uint16)
 *   reg 0x2003-0x2004 : task_target_pos_mm (int32, 相对真0点)
 *   reg 0x2005        : task_axis      (1=D_00行走 / 2=D_01顶升)
 * On a valid frame this builds a cfw_task_dispatch_t and publishes
 * EV_TASK_RECEIVED (payload carried by the event bus; P0-2 safe). */
#ifndef COMM_MODBUS_TASK_DISPATCH_H
#define COMM_MODBUS_TASK_DISPATCH_H

#include <stdint.h>
#include "common/cfw_types.h"
#include "svc/event_bus.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MODBUS_TASK_BASE 0x2000u

/* Parse a write-multiple-registers PDU (from modbus_rtu_process) and publish
 * EV_TASK_RECEIVED on the given bus. Returns CFW_OK on successful dispatch. */
cfw_err_t modbus_handle_task_dispatch(const uint8_t* pdu, uint16_t pdu_len, evt_bus_t* bus);

#ifdef __cplusplus
}
#endif
#endif /* COMM_MODBUS_TASK_DISPATCH_H */
