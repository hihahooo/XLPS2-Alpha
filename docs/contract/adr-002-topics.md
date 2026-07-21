# ADR-002 扩展主题（+2）

- 状态：采纳（SSOT）
- 背景：基础 8 主题缺操作审计与诊断日志通道。
- 决策：新增 2 个主题，总计 10：

| 主题 | 方向 | 负载 |
|------|------|------|
| `audit/log` | hmi→cloud | 操作审计（audit_seq 自增） |
| `diag/log` | device→cloud | 诊断/事件日志（diag_code） |

- 结果：MQTT 主题 = 8 基础 + 2 = 10（见 MQTT 主题）。
- **约束/说明（跨模块裁定）**：
  - 任务下发通道为 **Modbus RTU（ADR-004，FC=0x10 基址 0x2000）**，**不**占用 MQTT 主题；10 主题固定，不新增 `task/cmd`。
  - `interference/sync` 负载 Envelope（`points:[position_mm, confirmed, hit_count]`）为 **MQTT 负载内部结构**，**不**进 33 字段数据字典（仅 `interference_count` 入字典），与 ADR-006「OTA 私有字段不进字典」原则一致。
