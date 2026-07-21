# ADR-007 恢复出厂 / 参数版本

- 状态：采纳（SSOT）
- 背景：现场需可一键恢复参数基线；参数热调需可追溯。
- 决策：

1. **恢复出厂**：HMI/云端写 `factory_reset_req = 1` → L5 复位参数层，并自增 `param_revision`。
2. **参数热调**：每次提交 `param_revision++`（单调递增，便于回滚与审计）。
3. **SMDL 版本**：SMDL 下发时 `smdl_revision++`，与 `param_revision` 独立计数。

- 约束：恢复出厂仅复位参数层，不动固件/SMDL；`param_revision` 单调，禁止回退。
- 关联：数据字典 `factory_reset_req` / `param_revision` / `smdl_revision`；MQTT `param/set` / `config/smdl`。
