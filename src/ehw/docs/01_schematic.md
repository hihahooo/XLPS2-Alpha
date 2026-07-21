# 文档① 原理图（Schematic）

> 八文档之一。设计源见 `../sch/`（`01_power_chain.md`~`04_safety.md` + `netlist.csv` + `symbols.csv`）。
> 本文档为原理图编制与审查依据，位号/封装/参数须与 `symbols.csv`、`bom/bom.csv`、其余 7 文档一致。

## 1. 图纸分页（建议 4 页）

| 页 | 标题 | 内容 |
|----|------|------|
| SCH-1 | 电源链 | J1→L30→Q10→F1→U31→U30→Buck/LDO（见 `sch/01_power_chain.md`） |
| SCH-2 | MCU 最小系统 | U1 + 时钟/复位/Boot/SWD/Flash A-B（见 `sch/02_mcu_min_system.md`） |
| SCH-3 | 接口 | CAN-FD×2 / RS485×2 / ETH / WS63 / I2C 存储（见 `sch/03_interfaces.md`） |
| SCH-4 | 安全与指示 | ESTOP/触边直切 + IWDG 心跳 + LED/蜂鸣器（见 `sch/04_safety.md`） |

## 2. 关键设计约束（原理图级）

1. **24V 链序绝对不可颠倒**：防反(Q10) → 保险(F1) → eFuse(U31) → 隔离(U30)。任何「绕过保护」的接法 QA 不通过。
2. **地分割**：NET_GND_IN（U30 前）与 NET_GND（U30 后）分割 ≥4mm；仅经 U30 隔离连接。
3. **隔离边界两道**：系统级(U30 ≥1.5kV) + 总线级(ISO1042/ADM2483 + B0505S)。
4. **Flash 分区**：A=0x08020000 / B=0x08100000 / FLAG=0x081E0000，各 ≤0x0E0000（ADR-005，内部 Flash）。
5. **eFuse 限流**：R_ILIM=6.04kΩ（≈1.95A，依 TI TPS26600 公式 11.8/R_ILIM 核算）。**✅ 主理人 #2 裁决确认目标 ≈2A，采纳 6.04kΩ**。

## 3. 审查清单（投板前）

- [ ] 链序 J1→L30→Q10→F1→U31→U30 连线无旁路
- [ ] 所有 VDD/VSS 退耦到位；VCAP 2.2µF 已接
- [ ] 隔离地 NET_GND_ISO 与 NET_GND 分割正确
- [ ] 连接器料号统一（J14=HR911105A，非 HR601680）
- [ ] 引脚分配与 `../pinmap.csv` 一致；CubeMX 终校 AF 无冲突
- [ ] 位号/封装与 `symbols.csv`/`bom/bom.csv` 逐项一致
