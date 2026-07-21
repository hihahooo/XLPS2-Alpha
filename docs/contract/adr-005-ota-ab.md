# ADR-005 OTA A/B 双分区

- 状态：采纳（SSOT）
- 背景：固件升级须可回滚、不影响运行分区，且支持断点续传与健康确认。
- 决策：A/B 物理双分区 + FLAG 扇区（双备份 + CRC-32）。

```
Flash 物理选型 = STM32H743IIT6 **内部** Flash 2MB（单芯片内 A/B 逻辑双分区；非外部 QSPI 双芯）
A 分区基址 = 0x08020000
B 分区基址 = 0x08100000
单分区容量 ≤ 0x0E0000（~0.9MB）
FLAG_SECTOR = 0x081E0000
HEALTH_WINDOW_S = 300
CHUNK_SIZE = 1024

EMQX_BROKER_URL = mqtts://emqx.np-xltech.com:8883
FLAG 双备份：主 0x000 / 备 0x200，各带 CRC-32
```

- 流程：云端下发到**非活跃**分区 → 本地烧写校验 → 重启切换 → 健康窗口（300s）内设备上报健康 → 超时未确认则**自动回滚**到上一稳定分区。
- 异常隔离：升级失败不影响运行分区；FLAG 双备份防单点损坏。
- 版本单调：新版本号须严格大于当前（见 OTA 开发说明 P1 规则）。
- **版本号形态（裁定）**：`fw_version` / `ota_target_version` 在数据字典中为 `string` 类型，承载**十进制整数序号**（如 `"1024"`）用于单调比较；语义版本号（semver）仅作展示，不参与比较。比较语义以整数单调为准，与「单调递增整数」一致。
- 关联：数据字典 `ota_active_slot` / `ota_state` / `ota_progress_pct` / `ota_target_version` / `ota_result`。
