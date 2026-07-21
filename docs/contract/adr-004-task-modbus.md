# ADR-004 任务下发 Modbus

- 状态：采纳（SSOT）
- 背景：HMI/网关需经 RS485 Modbus RTU 向控制器实时下发取放货任务。
- 决策：功能码 `FC=0x10`（写多个寄存器），保持寄存器基址 `0x2000`。

```
payload = task_id | task_type | task_target_pos_mm | task_axis | CRC
轴标识：1 = D_00 行走伺服, 2 = D_01 顶升伺服
```

- 通道：本地 RS485 Modbus RTU（实时轮询 + 参数读写 + 任务下发）；远程经 MQTT `telemetry`/`param/set`。
- 约束：与 CANopen 内部伺服控制解耦——Modbus 仅下发任务语义，伺服执行走内部 CAN（CANopen CiA402）。
- 关联字段：ADR-001 的 `task_id` / `task_status` / `task_target_pos_mm` / `task_axis`。
