# 文档⑥ 测试点（Test Points）与电源链测试

> 八文档之一。测试点位置须与 `02_layout.md` 一致；HW-PWR-001~005 为电源链强制验收项。

## 1. 测试点清单（TP）

| TP | 网络 | 标称 | 用途 |
|----|------|------|------|
| TP1 | NET_24V_IN | 24V | 输入电压 |
| TP2 | NET_24V_PROT | 24V | 防反后 |
| TP3 | NET_24V_EF | 24V | eFuse 输入 |
| TP4 | NET_24V_ISO | 24V | eFuse 输出/隔离输入 |
| TP5 | NET_24V_BOARD | 24V | 隔离后板级 24V |
| TP6 | NET_5V | 5.0V | Buck 输出 |
| TP7 | NET_3V3 | 3.3V | LDO 输出 |
| TP8 | NET_GND_IN | 0V | 初级地 |
| TP9 | NET_GND | 0V | 次级地 |
| TP10 | FDCAN1/2 | 信号 | CAN  probe |
| TP11 | USART3/6 | 信号 | RS485 probe |
| TP12 | RMII_REF_CLK | 50MHz | ETH 时钟 |
| TP13 | SAFE_HEARTBEAT | 脉冲 | 安全心跳 |
| TP14 | PGOODb/FLTb | 电平 | eFuse 状态 |

## 2. 电源链测试（HW-PWR-001~005）

### HW-PWR-001 防反接（Q10）
- 步骤：J1 反接 24V（+/− 对调），限流 0.5A；测 TP5(NET_24V_BOARD)。
- 判据：TP5≈0V，Q10 无发热/无损坏；恢复正常接法后 TP5=24V 正常。

### HW-PWR-002 可复位过载（U31）
- 步骤：J1 加 24V，输出端加载至 2.2A（>I_LIM≈1.95A）。
- 判据：U31 限流至≈2A，FLTb(TP14) 拉低；撤载后自动恢复，TP5 维持。

### HW-PWR-003 短路（U31）
- 步骤：TP5 对地短路（持续）。
- 判据：电流被钳、无烧毁；移除短路后自动重试恢复；FLTb 曾拉低。

### HW-PWR-004 隔离耐压（U30）
- 步骤：初/次级间加 1.5kVdc/1min（耐压仪），测漏电流。
- 判据：无击穿/无飞弧，漏电流 <1mA；TP8 与 TP9 间阻值仍 ≥100MΩ。

### HW-PWR-005 PGOOD/FAULT（U31）
- 步骤：正常上电测 PGOODb(TP14)；人为制造过载看 FLTb。
- 判据：正常 PGOODb=高（3.3V）；过载 FLTb=低且 MCU(PB0/PB1) 可读。

## 3. 审查清单

- [ ] 测试点与 layout 标注一致
- [ ] 5 项电源链测试有步骤+判据
- [ ] 隔离耐压与地分割互证
