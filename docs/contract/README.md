# 跨模块契约（SSOT）

跨模块一致性由本目录统一治理，主理人（Tech Lead）为唯一维护者。任何模块改动若触及下列契约，必须同步更新此处并过 `tests/test_cross_module.py` 门禁。

## 契约 artifacts（机器可读，SSOT）

- [`../config/data_dictionary.json`](../config/data_dictionary.json) — 33 字段统一数据字典
- [`../config/mqtt_topics.json`](../config/mqtt_topics.json) — 10 个 MQTT 主题

## 文档

- [数据字典](data-dictionary.md)
- [MQTT 主题](mqtt-topics.md)
- ADR 列表：
  - [ADR-001 扩展字段](adr-001-extended-fields.md)
  - [ADR-002 扩展主题](adr-002-topics.md)
  - [ADR-003 current_state 层级编码](adr-003-current-state.md)
  - [ADR-004 任务下发 Modbus](adr-004-task-modbus.md)
  - [ADR-005 OTA A/B 双分区](adr-005-ota-ab.md)
  - [ADR-006 四级容错](adr-006-fault-tolerance.md)
  - [ADR-007 恢复出厂 / 参数版本](adr-007-factory-reset.md)

## 设计原则

1. 单一事实源：字段名、类型、主题路径只在此定义，各模块不得另立。
2. `current_state` 为层级编码（region.top_state.sub_state），HMI 按路径解析。
3. OTA 传输专有字段（seq/CRC/验签/health_deadline）不进统一字典（ADR-006），仅作 MQTT 载荷内部字段或存 FLAG 扇区。
4. 命名规范：`task_status` 禁止 `task_state` 别名；干扰点库以 `position_mm` 为索引而非轨道编号。
