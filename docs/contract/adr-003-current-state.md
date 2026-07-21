# ADR-003 current_state 层级编码

- 状态：采纳（SSOT）
- 背景：HSM 为 3 个并行正交区域（主业务/能源/安全），状态需可层级解析，供 HMI 展示与云端记录。
- 决策：单字段 `current_state` 采用位域编码：

```
current_state = (region << 14) | (top_state << 8) | sub_state
0xFFFF = 未初始化
region:  0 = 主业务区, 1 = 能源管理区, 2 = 安全监控区
```

- 解码：HMI 按层级路径解析，例如 `主业务.TRAVELING.CHECK_DIST`。
- **位域布局（显式，消除重叠）**：`current_state` 为 16 位值，三段不重叠——
  - `sub_state`  = bits 0–7  （8 位，掩码 0x00FF）
  - `top_state`  = bits 8–13 （6 位，掩码 0x3F；所有命名状态编号 ≤ 0x3F）
  - `region`     = bits 14–15（2 位，掩码 0x03）
  - 编码 `top_state` 须 `& 0x3F`，`region` 须 `& 0x03`；与跨模块门禁公式 `(2<<14)|(5<<8)|3 == 0x8503` 逐字节一致。
- 对齐：`decodeCurrentState()` 在 `contract/types.ts`（HMI）与 `schema.py`（OTA/云端）中必须逐字节一致。
- 约束：`region` 为最高优先级仲裁依据——安全区（region=2）异常时全局捕获（ESTOP）。
- 数据字典字段：`current_state` / `top_state` / `sub_state` / `region` 均由此派生。
