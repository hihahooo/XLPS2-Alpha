# ADR-006 四级容错

- 状态：采纳（SSOT）
- 背景：环境光对光电干扰、激光误触发会导致误停车/碰撞，需分级处置而非一刀切停车。
- 决策：四级容错（**级别编号 ≠ 执行顺序**）：

```
一级 CHECK_DIST    —— 软滤波：连续读数去抖，抑制瞬时干扰
二级 NUDGE_RETRY   —— 微动重试：小幅进退重新探测
四级 CROSS_VERIFY  —— 交叉验证：停车「前」先证伪干扰（双路比对）
三级 SLOW_STOP/ESTOP —— 分级停车：确认障碍后减速停 / 全局急停
```

- 交叉验证（CROSS_VERIFY，四级）：比对
  - 激光 RS485 连续读数 `laser_distance_mm`
  - 开关量硬触发 `laser_triggered`

  | 双路结果 | 判定 |
  |----------|------|
  | 一致 | 真障碍 / 真无障碍 |
  | 单路异常 | 单路干扰，继续行驶并记录 `cross_verify_fault_ch` |

- 优先级：安全监控区（region=2）最高；ESTOP 全局捕获。
- 关联字段：`fault_level` / `laser_status` / `photoelectric_state` / `cross_verify_fault_ch`（ADR-001）。
